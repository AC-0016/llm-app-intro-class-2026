"""LLMとの通信。まず ask_plain() から読む。"""
import os
from openai import OpenAI
from settings import DEMO_MODE, MODEL


def make_client():
    # APIキーはOSの環境変数からSDKが読み取る。
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError('このターミナルでOPENAI_API_KEY環境変数を設定してから起動してください。')
    return OpenAI(timeout=30.0, max_retries=0)


def response_result(response):
    # 空の回答や途中で切れた回答を成功として扱わない。
    if response.status != 'completed' or not response.output_text.strip():
        raise ValueError('回答が完了しませんでした。質問や資料を短くしてください。')
    return {
        'answer': response.output_text,
        'input_tokens': response.usage.input_tokens,
        'output_tokens': response.usage.output_tokens,
    }


def ask_plain(question):
    if DEMO_MODE:
        return {
            'answer': '【デモ・固定文】資料なしの応答です。実際の生成はAPIモードで比較します。',
            'input_tokens': 0, 'output_tokens': 0,
        }
    client = make_client()
    # BEGIN EXERCISE api
    response = client.responses.create(
        model=MODEL, reasoning={'effort': 'none'},
        instructions='あなたは授業の学習を手伝うアシスタントです。日本語で簡潔に答えてください。',
        input=question,
        max_output_tokens=600,
        store=False,
    )
    # END EXERCISE api
    return response_result(response)
