"""会話の履歴をのせてLLMを呼び出す例。

実行: python chat.py
質問を続けて入力できる。何も入力せずにEnterを押すと終わる。

LLMは前の会話を覚えていない。そこで、これまでの質問と回答を
リスト（history）にためておき、毎回まとめて送る。
履歴が長くなるほど、送るトークン数と料金が増える。
"""
import os
from openai import OpenAI, APIError

# ===== 設定 =====
# APIキーはここに書かず、ターミナルの環境変数 OPENAI_API_KEY で渡す。

# 使うモデル。環境変数 OPENAI_MODEL があれば、そちらを使う。
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')

# LLMへの指示。one_shot.py と chat.py で同じ指示にして、違いを「履歴の有無」だけにする。
INSTRUCTIONS = 'あなたは授業の学習を手伝うアシスタントです。日本語で簡潔に答えてください。'

# 質問できる回数の上限。履歴が長くなりすぎないようにする。
MAX_TURNS = 10


def make_client():
    """APIを呼び出すためのクライアントを作る。キーは環境変数 OPENAI_API_KEY から読まれる。"""
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError('このターミナルで環境変数 OPENAI_API_KEY を設定してから実行してください。')
    return OpenAI(timeout=30.0, max_retries=0)


def ask_with_history(history):
    """これまでの会話をすべて送り、最後の質問への回答とトークン数を返す。

    history の例:
    [{'role': 'user', 'content': '私の名前は佐藤です。'},
     {'role': 'assistant', 'content': 'こんにちは、佐藤さん。'},
     {'role': 'user', 'content': '私の名前は？'}]
    """
    client = make_client()
    response = client.responses.create(
        model=MODEL,
        reasoning={'effort': 'none'},
        instructions=INSTRUCTIONS,
        input=history,  # 1回だけ呼ぶ例との違いは、ここで履歴のリストを送ること
        max_output_tokens=600,
        store=False,  # 送った内容をOpenAI側に保存しない。だから履歴は自分で送る
    )
    # 途中で切れた回答や、空の回答は失敗として扱う。
    if response.status != 'completed' or response.output_text.strip() == '':
        raise ValueError('回答が完了しませんでした。質問を短くして試してください。')
    return {
        'answer': response.output_text,
        'input_tokens': response.usage.input_tokens,
        'output_tokens': response.usage.output_tokens,
    }


def main():
    history = []
    print(f'質問を入力してください（最大{MAX_TURNS}回）。何も入力せずにEnterで終わります。')

    for turn in range(1, MAX_TURNS + 1):
        question = input(f'質問{turn}: ').strip()
        if question == '':
            break
        if len(question) > 500:
            print('質問は500文字以内で入力してください。')
            continue

        # 1. 今回の質問を履歴に追加する。
        history.append({'role': 'user', 'content': question})

        # 2. 履歴をまとめて送る。
        try:
            result = ask_with_history(history)
        except ValueError as error:
            print(error)
            return
        except APIError:
            # エラーの全文には内部の情報が含まれることがあるので、決まった文だけを表示する。
            print('API呼び出しに失敗しました。キー・モデル・利用枠を確認してください。')
            return

        # 3. LLMの回答も履歴に追加する。次の質問のときに一緒に送られる。
        history.append({'role': 'assistant', 'content': result['answer']})

        print('回答:', result['answer'])
        print(f"（送った履歴 {len(history) - 1} 件 / 入力 {result['input_tokens']} トークン"
              f" / 出力 {result['output_tokens']} トークン）")

    print('終わります。')


if __name__ == '__main__':
    main()
