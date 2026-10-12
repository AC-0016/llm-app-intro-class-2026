# 第6回：意味で探す検索

[スライド](slides.md) / [PDF](slides.pdf)

## ゴール

同じ向きで1、直交で0。Embedding APIで作成したベクトルを使って検索できる。

## 起動方法

毎回リポジトリのルートのターミナルから始めます。既に別のフォルダにいる場合は、VS Codeの新しいターミナルを開いてください。

```bash
source .venv/bin/activate
cd session06/exercise
python init_db.py
python build_index.py
python main.py
```

第2回以外はポート8000番をブラウザで開きます。サーバー停止はCtrl+C。
Pythonコードや環境変数を変更したら停止して再起動、JSを変更したら画面を再読み込みします。

## 演習

1. `exercise/embeddings.py` を開く。
2. cosine_similarity()の計算を完成させ、仮のraiseを削除する。
3. `exercise/worksheet.md` に比較結果・理由・疑問を書く。
4. スライドの確認問題に答える。

コメントのヒントを使って構いません。コメントを外すときはインデントもそろえます。
仮のraise/throwは、未実装部分を使ったときに明確に止めるためのものです。
`solution/` はその回だけの完成例。困った場合は差分を確認して、自分の言葉で説明します。

## APIの設定

実際のAPIを使います。回答生成・意味検索・関数選択では外部APIへの通信と利用料金が発生します。
毎回の授業開始時に、アプリを起動するターミナルで次を実行します。キーの入力は画面にもコマンド履歴にも残りません。

```bash
read -rsp "APIキー: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
```

同じターミナルからアプリを起動してください。新しいターミナルでは再設定が必要です。終了時はサーバーをCtrl+Cで停止し、`unset OPENAI_API_KEY` を実行してターミナルを閉じます。キーは `.env`、Codespaces Secrets、シェルの設定ファイルに保存しません。

生成モデルはgpt-6-luna、reasoning.effort=noneです。
第2・4回の穴埋めは実際のAPIを呼び出して確認します。
意味検索はEmbeddingモデルを変えたら `python build_index.py` を再実行します。
キーがない場合は講師の実演を観察し、APIで未検証と記録します。

## 提出物

- `exercise/embeddings.py`（第1回はワークシートのみ）のGitHub URL
- `exercise/worksheet.md` のGitHub URL
- 第8回は `exercise/evaluation.md` と `your-app/design.md` も提出

.env、APIキー、DB、実在の学生情報は提出しません。

```bash
git status
git add session06/exercise
git commit -m "第6回: 演習と振り返り"
git push
```
