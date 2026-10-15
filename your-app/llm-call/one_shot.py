"""LLMを1回だけ呼び出す、いちばん小さな例。

実行: python one_shot.py
質問を1つ入力すると、回答とトークン数を表示して終わる。
前の質問は送らないので、LLMは前に何を聞かれたかを知らない。
"""
import os
from openai import OpenAI, APIError

# ===== 設定 =====
# APIキーはここに書かず、ターミナルの環境変数 OPENAI_API_KEY で渡す。

# 使うモデル。環境変数 OPENAI_MODEL があれば、そちらを使う。
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')

# LLMへの指示。one_shot.py と chat.py で同じ指示にして、違いを「履歴の有無」だけにする。
INSTRUCTIONS = 'あなたは授業の学習を手伝うアシスタントです。日本語で簡潔に答えてください。'


def make_client():
    """APIを呼び出すためのクライアントを作る。キーは環境変数 OPENAI_API_KEY から読まれる。"""
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError('このターミナルで環境変数 OPENAI_API_KEY を設定してから実行してください。')
    return OpenAI(timeout=30.0, max_retries=0)


def ask_once(question):
    """質問を1つだけ送り、回答とトークン数を返す。"""
    client = make_client()
    response = client.responses.create(
        model=MODEL,
        reasoning={'effort': 'none'},
        instructions=INSTRUCTIONS,
        input=question,  # 今回の質問の文字列だけを送る
        max_output_tokens=600,
        store=False,  # 送った内容をOpenAI側に保存しない
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
    question = input('質問: ').strip()
    if question == '' or len(question) > 500:
        print('質問は1〜500文字で入力してください。')
        return

    try:
        result = ask_once(question)
    except ValueError as error:
        print(error)
        return
    except APIError:
        # エラーの全文には内部の情報が含まれることがあるので、決まった文だけを表示する。
        print('API呼び出しに失敗しました。キー・モデル・利用枠を確認してください。')
        return

    print('回答:', result['answer'])
    print(f"（入力 {result['input_tokens']} トークン / 出力 {result['output_tokens']} トークン）")


if __name__ == '__main__':
    main()
