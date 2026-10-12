# 第5回：検索してから回答する

[スライド](slides.md) / [PDF](slides.pdf)

## ゴール

検索語SQLite 保存で資料を取得でき、zzzz-no-matchなら0件になる。

## 起動方法

毎回リポジトリのルートのターミナルから始めます。既に別のフォルダにいる場合は、VS Codeの新しいターミナルを開いてください。

```bash
source .venv/bin/activate
cd session05/exercise
python init_db.py
python main.py
```

第2回以外はポート8000番をブラウザで開きます。サーバー停止はCtrl+C。
Pythonコードや環境変数を変更したら停止して再起動、JSを変更したら画面を再読み込みします。

## 演習

1. `exercise/knowledge.py` を開く。
2. search_keyword()で単語ごとの一致件数を数え、仮のraiseを削除する。
3. `exercise/worksheet.md` に比較結果・理由・疑問を書く。
4. スライドの確認問題に答える。

コメントのヒントを使って構いません。コメントを外すときはインデントもそろえます。
仮のraise/throwは、未実装部分を使ったときに明確に止めるためのものです。
`solution/` はその回だけの完成例。困った場合は差分を確認して、自分の言葉で説明します。

## デモとAPI

初期設定はDEMO_MODE=trueです。実際の生成・意味検索・関数選択は行いません。
毎回の授業開始時に、アプリを起動するターミナルで次を実行します。キーの入力は画面にもコマンド履歴にも残りません。

```bash
read -rsp "APIキー: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
export DEMO_MODE=false
```

同じターミナルからアプリを起動してください。新しいターミナルでは再設定が必要です。終了時はサーバーをCtrl+Cで停止し、`unset OPENAI_API_KEY DEMO_MODE` を実行してターミナルを閉じます。キーは `.env`、Codespaces Secrets、シェルの設定ファイルに保存しません。

生成モデルはgpt-6-luna、reasoning.effort=noneです。
第2・4回の穴埋めはAPIモードの分岐なので、デモで動くだけでは実装確認になりません。
意味検索はDEMO_MODEやEmbeddingモデルを変えたら `python build_index.py` を再実行します。
キーがない場合は講師の実演を観察し、APIで未検証と記録します。

## 提出物

- `exercise/knowledge.py`（第1回はワークシートのみ）のGitHub URL
- `exercise/worksheet.md` のGitHub URL
- 第8回は `exercise/evaluation.md` と `your-app/design.md` も提出

.env、APIキー、DB、実在の学生情報は提出しません。

```bash
git status
git add session05/exercise
git commit -m "第5回: 演習と振り返り"
git push
```
