"""チャットアプリ（会話の履歴をのせてLLMを呼び出す）。

実行: python main.py
ブラウザ: ポート8000番

会話の履歴はブラウザ（static/app.js の history）が持ち、質問のたびに全部送ってくる。
サーバーは履歴を保存しない。
"""
import os
from pathlib import Path
from typing import Literal
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError
from llm import ask_with_history

# ===== 設定 =====
# APIキーはここに書かず、ターミナルの環境変数 OPENAI_API_KEY で渡す。

# このファイルがあるフォルダ。画面のファイルを探すときの基準にする。
BASE_DIR = Path(__file__).resolve().parent

# 使うモデル。環境変数 OPENAI_MODEL があれば、そちらを使う。
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')

# LLMへの指示。
INSTRUCTIONS = 'あなたは授業の学習を手伝うアシスタントです。日本語で簡潔に答えてください。'

# 1つの会話で質問できる回数の上限。履歴が長いほど、送るトークン数と料金が増える。
MAX_TURNS = 10

# ===== ここからアプリ =====

app = FastAPI(title='チャットアプリ')


class Message(BaseModel):
    """会話の1件分。role は 'user'（質問）か 'assistant'（LLMの回答）。"""
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=3000)


class ChatRequest(BaseModel):
    """画面から送られてくるデータの形。これまでの会話のリスト。"""
    history: list[Message] = Field(min_length=1)


@app.post('/api/chat')
def chat(request: ChatRequest):
    # Pydanticのデータを、APIに渡せる普通の辞書のリストに直す。
    history = []
    for message in request.history:
        history.append({'role': message.role, 'content': message.content})

    # 送られてきた履歴を確かめる。
    question = history[-1]
    if question['role'] != 'user':
        raise HTTPException(status_code=400, detail='最後は質問（user）にしてください。')
    if len(question['content']) > 500:
        raise HTTPException(status_code=400, detail='質問は500文字以内で入力してください。')
    if len(history) > MAX_TURNS * 2 - 1:
        raise HTTPException(status_code=400, detail=f'質問は{MAX_TURNS}回までです。会話をリセットしてください。')

    try:
        result = ask_with_history(history, MODEL, INSTRUCTIONS)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except APITimeoutError:
        raise HTTPException(status_code=504, detail='APIの応答が遅れています。時間をおいて試してください。')
    except RateLimitError:
        raise HTTPException(status_code=429, detail='APIの利用制限です。利用枠を確認してください。')
    except APIError:
        # エラーの全文には内部の情報が含まれることがあるので、画面には決まった文だけを返す。
        raise HTTPException(status_code=502, detail='API呼び出しに失敗しました。キー・モデル・利用枠を確認してください。')
    return result


# 画面（static/ のHTML・CSS・JavaScript）を配信する。APIの定義より後に書く。
app.mount('/', StaticFiles(directory=BASE_DIR / 'static', html=True), name='static')

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
