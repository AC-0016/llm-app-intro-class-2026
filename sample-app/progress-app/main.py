"""制作の進捗アプリ（SQLite + Function Calling）。

実行: python main.py
ブラウザ: ポート8001番
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError
from settings import BASE_DIR
from progress_db import init_db
from llm import ask_with_tools

# 起動時にDBを準備する。すでにある進捗は上書きしない。
init_db()

app = FastAPI(title='制作の進捗アプリ')


class Question(BaseModel):
    """画面から送られてくるデータの形。"""
    question: str = Field(min_length=1, max_length=500)


@app.post('/api/ask')
def ask(request: Question):
    question = request.question.strip()
    if question == '':
        raise HTTPException(status_code=422, detail='質問を入力してください。')

    try:
        result = ask_with_tools(question)
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
    uvicorn.run(app, host='0.0.0.0', port=8001)
