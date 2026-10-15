"""ベクトル検索アプリ（Embedding + LLM）。

実行: python init_db.py（最初と、資料を直したとき）→ python main.py
ブラウザ: ポート8003番
"""
import json
import os
import sqlite3
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError
from search import search_documents
from llm import embed_texts, ask_with_documents

# ===== 設定 =====
# APIキーはここに書かず、ターミナルの環境変数 OPENAI_API_KEY で渡す。

# このファイルがあるフォルダ。資料や画面のファイルを探すときの基準にする。
BASE_DIR = Path(__file__).resolve().parent

# 資料とベクトルを保存したSQLiteのファイル。python init_db.py で作る。
DATABASE = BASE_DIR / 'documents.db'

# 回答に使うモデル。環境変数 OPENAI_MODEL があれば、そちらを使う。
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')

# 文章をベクトルにするモデル。資料と質問は、必ず同じモデルでベクトルにする。
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

# LLMに渡す資料の最大件数。
TOP_K = 3

# これより類似度が小さい資料は、関係が薄いとみなして渡さない。
# 目安の値なので、画面に出る類似度を見ながら調整する。
MIN_SIMILARITY = 0.3

# ===== ここからアプリ =====


def load_documents(database, embedding_model):
    """DBから資料とベクトルを全部読み、辞書のリストにして返す。"""
    if not database.exists():
        # sqlite3.connect() は、ファイルが無いと空のDBを作ってしまうので、先に確かめる。
        raise SystemExit(f'{database.name} がありません。先に python init_db.py を実行してください。')
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('SELECT id, source, slide, title, heading, body, vector, embedding_model'
                   ' FROM documents ORDER BY id')
    rows = cursor.fetchall()
    conn.close()

    documents = []
    for row in rows:
        # 別のモデルで作ったベクトルとは比べられないので、作り直してもらう。
        if row[7] != embedding_model:
            raise SystemExit(f'DBのベクトルは {row[7]} で作られています。'
                             f'python init_db.py を実行して、{embedding_model} で作り直してください。')
        documents.append({
            'id': row[0],
            'source': row[1],
            'slide': row[2],
            'title': row[3],
            'heading': row[4],
            'body': row[5],
            'vector': json.loads(row[6]),  # JSONの文字列を、数値のリストに戻す
        })
    return documents


# 起動時にDBから資料とベクトルを読み込む。資料を直したら、init_db.py を実行してからサーバーを再起動する。
documents = load_documents(DATABASE, EMBEDDING_MODEL)

app = FastAPI(title='ベクトル検索アプリ')


class Question(BaseModel):
    """画面から送られてくるデータの形。"""
    question: str = Field(min_length=1, max_length=500)


@app.post('/api/ask')
def ask(request: Question):
    question = request.question.strip()
    if question == '':
        raise HTTPException(status_code=422, detail='質問を入力してください。')

    try:
        # 1. 質問をベクトルにする。資料と同じモデルを使う。
        question_vector = embed_texts([question], EMBEDDING_MODEL)[0]

        # 2. 質問のベクトルに近い資料を探す。
        found = search_documents(question_vector, documents, TOP_K, MIN_SIMILARITY)

        # 3. 見つかった資料を渡して、LLMに回答させる。
        if not found:
            # 資料が無いときは、回答用のAPIを呼ばずに知らせる。
            result = {
                'answer': '関係する資料が見つかりませんでした。言葉を変えて質問してください。',
                'input_tokens': 0,
                'output_tokens': 0,
            }
        else:
            result = ask_with_documents(question, found, MODEL)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except APITimeoutError:
        raise HTTPException(status_code=504, detail='APIの応答が遅れています。時間をおいて試してください。')
    except RateLimitError:
        raise HTTPException(status_code=429, detail='APIの利用制限です。利用枠を確認してください。')
    except APIError:
        # エラーの全文には内部の情報が含まれることがあるので、画面には決まった文だけを返す。
        raise HTTPException(status_code=502, detail='API呼び出しに失敗しました。キー・モデル・利用枠を確認してください。')

    result['sources'] = found
    return result


# 画面（static/ のHTML・CSS・JavaScript）を配信する。APIの定義より後に書く。
app.mount('/', StaticFiles(directory=BASE_DIR / 'static', html=True), name='static')

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8003)
