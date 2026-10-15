"""キーワード検索アプリ（Janome + LLM）。

実行: python main.py
ブラウザ: ポート8000番
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError
from settings import BASE_DIR
from documents import load_documents
from search import extract_words, search_documents
from llm import ask_with_documents

# LLMに渡す資料の最大件数。
TOP_K = 3

# 起動時に data/ の資料を読み込む。資料を直したら、サーバーを再起動する。
documents = load_documents()

app = FastAPI(title='キーワード検索アプリ')


class Question(BaseModel):
    """画面から送られてくるデータの形。"""
    question: str = Field(min_length=1, max_length=500)


@app.post('/api/ask')
def ask(request: Question):
    question = request.question.strip()
    if question == '':
        raise HTTPException(status_code=422, detail='質問を入力してください。')

    # 1. 質問から検索語を取り出す。
    keywords = extract_words(question)
    if not keywords:
        raise HTTPException(status_code=400, detail='質問から検索語を取り出せませんでした。名詞を含めて質問してください。')

    # 2. 検索語を多く含む資料を探す。
    found = search_documents(keywords, documents, TOP_K)

    # 3. 見つかった資料を渡して、LLMに回答させる。
    if not found:
        # 資料が無いときは、APIを呼ばずに知らせる（料金もかからない）。
        result = {
            'answer': '関係する資料が見つかりませんでした。言葉を変えて質問してください。',
            'input_tokens': 0,
            'output_tokens': 0,
        }
    else:
        try:
            result = ask_with_documents(question, found)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        except APITimeoutError:
            raise HTTPException(status_code=504, detail='APIの応答が遅れています。時間をおいて試してください。')
        except RateLimitError:
            raise HTTPException(status_code=429, detail='APIの利用制限です。利用枠を確認してください。')
        except APIError:
            # エラーの全文には内部の情報が含まれることがあるので、画面には決まった文だけを返す。
            raise HTTPException(status_code=502, detail='API呼び出しに失敗しました。キー・モデル・利用枠を確認してください。')

    result['keywords'] = keywords
    result['sources'] = found
    return result


# 画面（static/ のHTML・CSS・JavaScript）を配信する。APIの定義より後に書く。
app.mount('/', StaticFiles(directory=BASE_DIR / 'static', html=True), name='static')

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
