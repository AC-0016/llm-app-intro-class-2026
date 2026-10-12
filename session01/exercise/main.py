"""授業資料アシスタント。実行: python main.py"""
import threading
import time
from typing import Literal
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError
from settings import BASE_DIR, DATABASE
from llm import ask_plain, ask_with_context, build_context
from knowledge import init_documents, all_chunks, search_keyword
from embeddings import search_vector
from assignment_tools import init_assignments, ask_assignments

# DBが無い初回だけ資料を登録。更新はサーバーを止めてinit_db.pyを実行する。
if not DATABASE.exists():
    init_documents()
init_assignments()

app = FastAPI(title='授業資料アシスタント')


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    mode: Literal['plain', 'context', 'keyword', 'vector', 'tools'] = 'keyword'
    search_text: str = Field(default='', max_length=100)
    top_k: int = Field(default=3, ge=1, le=5)


# BEGIN STAGE 8
# 1プロセスの教材用の上限。全利用者で共有し、再起動するとリセットされる。
request_times = []
request_count = 0
limit_lock = threading.Lock()


def check_limit():
    global request_count
    now = time.monotonic()
    with limit_lock:
        while request_times and request_times[0] < now - 60:
            request_times.pop(0)
        if len(request_times) >= 10 or request_count >= 100:
            raise HTTPException(status_code=429, detail='教材用の利用上限に達しました。講師に相談してください。')
        request_times.append(now)
        request_count += 1
# END STAGE 8


@app.post('/api/ask')
def ask(request: Question):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail='質問を入力してください。')
    check_limit()
    started = time.monotonic()
    chunks = []
    try:
        # ここが処理の分かれ道。選んだ方式だけを実行する。
        if request.mode == 'plain':
            result = ask_plain(question)
        elif request.mode == 'context':
            chunks = all_chunks()
            result = ask_with_context(question, chunks)
        elif request.mode == 'keyword':
            if not request.search_text.strip():
                raise ValueError('検索語を空白区切りで入力してください。例: SQLite 保存')
            chunks = search_keyword(request.search_text, request.top_k)
            result = ask_with_context(question, chunks)
        elif request.mode == 'vector':
            chunks = search_vector(question, request.top_k)
            result = ask_with_context(question, chunks)
        elif request.mode == 'tools':
            result = ask_assignments(question)
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
