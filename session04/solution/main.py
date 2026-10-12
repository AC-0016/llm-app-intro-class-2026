"""授業資料アシスタント。実行: python main.py"""
import time
from typing import Literal
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError
from settings import BASE_DIR, DATABASE
from llm import ask_plain, ask_with_context, build_context
from knowledge import init_documents, all_chunks

# DBが無い初回だけ資料を登録。更新はサーバーを止めてinit_db.pyを実行する。
if not DATABASE.exists():
    init_documents()

app = FastAPI(title='授業資料アシスタント')


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    mode: Literal['plain', 'context'] = 'context'
    search_text: str = Field(default='', max_length=100)
    top_k: int = Field(default=3, ge=1, le=5)




@app.post('/api/ask')
def ask(request: Question):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail='質問を入力してください。')
    started = time.monotonic()
    chunks = []
    try:
        # ここが処理の分かれ道。選んだ方式だけを実行する。
        if request.mode == 'plain':
            result = ask_plain(question)
        elif request.mode == 'context':
            chunks = all_chunks()
            result = ask_with_context(question, chunks)
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except APITimeoutError:
        raise HTTPException(status_code=504, detail='APIの応答が遅れています。時間をおいて試してください。') from None
    except RateLimitError:
        raise HTTPException(status_code=429, detail='APIの利用制限です。利用枠を確認してください。') from None
    except APIError:
        # 例外全文には内部情報が含まれる場合があるため画面へ返さない。
        raise HTTPException(status_code=502, detail='API呼び出しに失敗しました。キー・モデル・利用枠を確認してください。') from None
    result['sources'] = chunks
    result['context'] = build_context(chunks)
    result['seconds'] = round(time.monotonic() - started, 2)
    return result


# APIの定義の後に置く。アプリ全体や.envは公開しない。
app.mount('/', StaticFiles(directory=BASE_DIR / 'static', html=True), name='static')

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
