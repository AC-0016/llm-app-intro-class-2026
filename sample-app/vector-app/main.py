"""ベクトル検索アプリ（Embedding + LLM）。

実行: python main.py
ブラウザ: ポート8003番
"""
import os
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError
from documents import load_documents
from search import search_documents
from llm import embed_texts, ask_with_documents

# ===== 設定 =====
# APIキーはここに書かず、ターミナルの環境変数 OPENAI_API_KEY で渡す。

# このファイルがあるフォルダ。資料や画面のファイルを探すときの基準にする。
BASE_DIR = Path(__file__).resolve().parent

# 授業資料のMarkdownを置くフォルダ。
DATA_DIR = BASE_DIR / 'data'

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

# 起動時に data/ の資料を読み込み、全部の資料をベクトルにしておく。
# 資料を直したら、サーバーを再起動する（そのたびにEmbedding APIを呼ぶ）。
documents = load_documents(DATA_DIR)
texts = []
for document in documents:
    texts.append(document['title'] + '\n' + document['heading'] + '\n' + document['body'])
vectors = embed_texts(texts, EMBEDDING_MODEL)
for i in range(len(documents)):
    documents[i]['vector'] = vectors[i]  # 資料と同じ順番でベクトルが返ってくる

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
