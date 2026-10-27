# LLMアプリケーション開発 2026

外部の資料やDBを使って答えるLLMアプリを、FastAPIとOpenAI APIで作る授業です。全13回。
第1〜8回は講義と演習、第9〜13回は自分の題材での制作です。

## フォルダ

| フォルダ | 内容 |
|---|---|
| `sample-app/` | 完成版のアプリ5つ。演習の答えであり、制作の見本（書き換えずに残す）。詳しくは `sample-app/README.md` |
| `your-app/` | 第9〜13回の制作用。`sample-app/` と同じ5つのフォルダと `README.md`。出発点に選んだフォルダをそのまま書き換える |
| `session01/` 〜 `session09/` | 各回のスライド（`slidesNN.md`、Marp形式）と、穴あきの演習コード（`exercise/`） |

`sessionNN/exercise/` は `sample-app/` の該当アプリをコピーして、`TODO` の場所に穴を開けたものです。
第1回と第9回は演習コードがありません。第8回は記入用のテンプレートです。

| 回 | 使うアプリ | 演習で埋める場所 |
|---|---|---|
| 1 | chat-app、keyword-app | なし（Fork、Codespaces、完成版の観察） |
| 2 | llm-call | `one_shot.py` のAPI呼び出し、`chat.py` の履歴の追加 |
| 3 | chat-app | `static/app.js` の送信、`main.py` の履歴の確認 |
| 4 | keyword-app | `llm.py` の指示文と `build_context()` |
| 5 | keyword-app | `search.py` の点数の計算と並べ替え |
| 6 | vector-app | `search.py` のコサイン類似度としきい値 |
| 7 | progress-app | `progress_db.py` のSQLの選択、`llm.py` の関数の選択 |
| 8 | keyword-app、vector-app | `evaluation.md` と `design.md` の記入 |
| 9 | your-app | なし（制作の開始。`your-app/README.md` を自分のREADMEに置き換え、`session08/exercise/design.md` を仕上げる） |

## 毎回の流れ

1. `sample-app/` の完成版を動かす
2. コードの説明を聞く
3. `sessionNN/exercise/` の穴あきコードを埋めて動かす
4. コミットしてプッシュする
5. GitHubで `sessionNN/exercise` を開き、そのURLをフォームから提出する

## 準備

- 第1回に、このリポジトリを自分のアカウントにForkし、Codespacesで開きます。
- Codespacesでは `.venv` と必要なパッケージが自動で入ります。ターミナルで `source .venv/bin/activate` を実行してから作業します。
- APIキーは、アプリを起動するターミナルで毎回設定します。ファイルやCodespaces Secretsには保存しません。

```bash
export OPENAI_API_KEY=sk-********
```

終了時はサーバーをCtrl+Cで止め、`unset OPENAI_API_KEY` を実行してターミナルを閉じます。

## スライドの表示

VS Codeの拡張機能 Marp for VS Code が入っています。`slidesNN.md` を開き、右上のプレビューで表示します。
