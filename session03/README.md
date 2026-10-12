# 第3回：Webアプリへの組み込み

[スライド](slides.md) / [PDF](slides.pdf)

## ゴール

POST /api/askが200を返し、画面に回答を表示できる。

## 起動方法

毎回リポジトリのルートのターミナルから始めます。既に別のフォルダにいる場合は、VS Codeの新しいターミナルを開いてください。

```bash
source .venv/bin/activate
cd session03/exercise
python main.py
```

第2回以外はポート8000番をブラウザで開きます。サーバー停止はCtrl+C。
Pythonコードや.envを変更したら停止して再起動、JSを変更したら画面を再読み込みします。

## 演習

1. `exercise/static/app.js` を開く。
2. askQuestion()のfetchのコメントを外し、仮のthrowを削除する。
3. `exercise/worksheet.md` に比較結果・理由・疑問を書く。
4. スライドの確認問題に答える。

コメントのヒントを使って構いません。コメントを外すときはインデントもそろえます。
仮のraise/throwは、未実装部分を使ったときに明確に止めるためのものです。
`solution/` はその回だけの完成例。困った場合は差分を確認して、自分の言葉で説明します。

## デモとAPI

初期設定はDEMO_MODE=trueです。実際の生成・意味検索・関数選択は行いません。
APIを使う場合は各フォルダで `cp .env.example .env`、DEMO_MODE=falseに変更します。
OPENAI_API_KEYはSecretsか.envに設定します。環境変数を優先します。
生成モデルはgpt-6-luna、reasoning.effort=noneです。
第2・4回の穴埋めはAPIモードの分岐なので、デモで動くだけでは実装確認になりません。
意味検索はDEMO_MODEやEmbeddingモデルを変えたら `python build_index.py` を再実行します。
キーがない場合は講師の実演を観察し、APIで未検証と記録します。

## 提出物

- `exercise/static/app.js`（第1回はワークシートのみ）のGitHub URL
- `exercise/worksheet.md` のGitHub URL
- 第8回は `exercise/evaluation.md` と `your-app/design.md` も提出

.env、APIキー、DB、実在の学生情報は提出しません。

```bash
git status
git add session03/exercise
git commit -m "第3回: 演習と振り返り"
git push
```
