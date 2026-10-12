"""第2回で使う最小の入り口。Webサーバーは使わない。"""
from llm import ask_plain

if __name__ == '__main__':
    question = input('質問: ').strip()
    if not question or len(question) > 500:
        raise SystemExit('質問は1〜500文字にしてください。')
    result = ask_plain(question)
    print(result['answer'])
    print('入力トークン:', result['input_tokens'])
    print('出力トークン:', result['output_tokens'])
