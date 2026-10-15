"""OpenAIのAPIを呼び出し、会話の履歴をのせて回答させる。llm-call/chat.py と同じ考え方。"""
import os
from openai import OpenAI


def make_client():
    """APIを呼び出すためのクライアントを作る。キーは環境変数 OPENAI_API_KEY から読まれる。"""
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError('このターミナルで環境変数 OPENAI_API_KEY を設定してから起動してください。')
    return OpenAI(timeout=30.0, max_retries=0)


def ask_with_history(history, model, instructions):
    """これまでの会話をすべて送り、最後の質問への回答とトークン数を返す。

    history の例:
    [{'role': 'user', 'content': '私の名前は佐藤です。'},
     {'role': 'assistant', 'content': 'こんにちは、佐藤さん。'},
     {'role': 'user', 'content': '私の名前は？'}]
    """
    client = make_client()
    response = client.responses.create(
        model=model,
        reasoning={'effort': 'none'},
        instructions=instructions,
        input=history,  # 今回の質問だけでなく、これまでの会話のリストを送る
        max_output_tokens=600,
        store=False,  # 送った内容をOpenAI側に保存しない。だから履歴は毎回自分で送る
    )
    # 途中で切れた回答や、空の回答は失敗として扱う。
    if response.status != 'completed' or response.output_text.strip() == '':
        raise ValueError('回答が完了しませんでした。質問を短くして試してください。')
    return {
        'answer': response.output_text,
        'input_tokens': response.usage.input_tokens,
        'output_tokens': response.usage.output_tokens,
    }
