"""OpenAIのAPIを呼び出す。LLMに関数（get_tasks）を選ばせ、Pythonで実行して回答させる。

流れ
  1回目: 質問と使える関数をLLMに送る → LLMが「get_tasks を status='todo' で呼んで」と返す
  実行 : Pythonが関数名と引数を確かめてから、DBを読む
  2回目: DBの結果をLLMに送る → LLMが結果をもとに回答を書く
"""
import json
import os
from openai import OpenAI
from progress_db import get_tasks

# LLMに教える「使える関数」の説明。LLMはこの説明を読んで、呼ぶかどうかと引数を決める。
TOOLS = [{
    'type': 'function',
    'name': 'get_tasks',
    'description': 'Webアプリ制作の進捗（やることと完了フラグ）を調べる。'
                   'status は all（全件）・todo（未完了）・done（完了）。',
    'parameters': {
        'type': 'object',
        'properties': {'status': {'type': 'string', 'enum': ['all', 'todo', 'done']}},
        'required': ['status'],
        'additionalProperties': False,
    },
    'strict': True,
}]

# LLMへの指示。
INSTRUCTIONS = (
    'Webアプリ制作の進捗は、必ず get_tasks の結果だけを根拠にしてください。'
    '結果にないことは推測しないでください。日本語で簡潔に回答してください。'
)


def make_client():
    """APIを呼び出すためのクライアントを作る。キーは環境変数 OPENAI_API_KEY から読まれる。"""
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError('このターミナルで環境変数 OPENAI_API_KEY を設定してから起動してください。')
    return OpenAI(timeout=30.0, max_retries=0)


def run_tool(name, arguments, database):
    """LLMが呼びたいと言ってきた関数を、確かめてから実行する。database はDBファイルの場所。

    LLMの出力は信用せず、許可した関数名と引数の形だけを受け付ける。
    eval() や exec() は使わない。
    """
    if name != 'get_tasks':
        raise ValueError('許可していない関数です。')
    # arguments は '{"status": "todo"}' のようなJSONの文字列。
    args = json.loads(arguments)
    if not isinstance(args, dict) or list(args.keys()) != ['status']:
        raise ValueError('引数の形が正しくありません。')
    return get_tasks(database, args['status'])


def ask_with_tools(question, model, database):
    """質問に答える。必要ならLLMに get_tasks を呼ばせる。

    model は使うモデルの名前、database は進捗DBのファイルの場所。
    """
    client = make_client()
    # LLMとのやり取りを、この順番でリストにためていく。
    history = [{'role': 'user', 'content': question}]

    # 1回目: 質問と使える関数を送る。
    first = client.responses.create(
        model=model,
        reasoning={'effort': 'none'},
        instructions=INSTRUCTIONS,
        input=history,
        tools=TOOLS,
        parallel_tool_calls=False,  # 関数は1回に1つだけ呼ばせる
        max_output_tokens=600,
        store=False,  # 送った内容をOpenAI側に保存しない
    )
    if first.status != 'completed':
        raise ValueError('関数の選択が完了しませんでした。')

    # LLMの出力（関数を呼びたいという依頼）を、やり取りに追加する。
    history.extend(first.output)

    # LLMが依頼してきた関数を実行し、結果をやり取りに追加する。
    tool_results = []
    for item in first.output:
        if item.type == 'function_call':
            rows = run_tool(item.name, item.arguments, database)
            tool_results.append({'name': item.name, 'arguments': item.arguments, 'rows': rows})
            history.append({
                'type': 'function_call_output',
                'call_id': item.call_id,  # どの依頼への結果かを示す
                'output': json.dumps(rows, ensure_ascii=False),
            })

    if not tool_results:
        # 関数を使わずに答えた場合は、1回目の回答をそのまま使う。
        final = first
        input_tokens = first.usage.input_tokens
        output_tokens = first.usage.output_tokens
    else:
        # 2回目: 関数の結果を送り、回答を書かせる。tools は渡さず、これ以上関数を呼ばせない。
        final = client.responses.create(
            model=model,
            reasoning={'effort': 'none'},
            instructions=INSTRUCTIONS,
            input=history,
            max_output_tokens=600,
            store=False,
        )
        # 料金は2回分かかるので、トークン数も2回分を足す。
        input_tokens = first.usage.input_tokens + final.usage.input_tokens
        output_tokens = first.usage.output_tokens + final.usage.output_tokens

    # 途中で切れた回答や、空の回答は失敗として扱う。
    if final.status != 'completed' or final.output_text.strip() == '':
        raise ValueError('回答が完了しませんでした。質問を短くして試してください。')
    return {
        'answer': final.output_text,
        'tool_results': tool_results,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
    }
