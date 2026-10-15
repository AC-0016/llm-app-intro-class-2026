# LLMアプリケーション開発 2026

**座学8回＋制作5回。gpt-6-lunaのAPIと外部知識を使い、根拠を確認できるWebアプリを作ります。**

[Webアプリケーション基礎2026](https://github.com/kappaexpress/web-app-intro-class-2026) の続編です。
HTML/CSS/JavaScript、Python・FastAPI、SQLite、fetch、Gitの基礎を既習として進めます。
参照元と同じMarpスライドとコメント付き演習を採用しています。

## 最初にすること

1. このリポジトリをForkする。
2. 自分のForkの **Code → Codespaces → Create codespace on main** を選ぶ。
3. 作成後、依存パッケージのインストール完了を待つ。
4. 新しいターミナルで次を実行する。

```bash
source .venv/bin/activate
read -rsp "APIキー: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
cd sample-app/keyword-app   # ほかのアプリは sample-app/README.md を参照
python init_db.py           # 最初の1回と、資料を直したとき
python main.py
```

VS Codeの「ポート」タブから8001番を開きます（sample-appのアプリごとの番号は [sample-app/README.md](sample-app/README.md) を参照）。**可視性はPrivateのまま**使います。
終了はCtrl+C。別のアプリを起動するときは、前のサーバーを先に止めます。
sample-appと各回のexercise・solutionは実際のAPIを使います。your-appの初期設定はデモモードです。起動前に[sample-appの手順](sample-app/README.md#起動)でAPIキーを設定してください。

## この教材のサンプル

「授業資料アシスタント」で、資料なし・資料全体・キーワード検索・意味検索・課題DB参照を比較します。
教材の授業案内と課題データは架空です。学習ノートは参照元の学習内容を踏まえ、新規に記述しています。

- **sample-app/**：完成版。LLM呼び出しの基本（llm-call）、チャットアプリ（chat-app）、キーワード検索アプリ（keyword-app）、ベクトル検索アプリ（vector-app）、制作の進捗アプリ（progress-app）
- **session01〜08/slides.md・slides.pdf**：授業資料
- **sessionXX/exercise/**：学生が編集する独立したコピー
- **sessionXX/solution/**：その回までの完成例
- **sessionXX/teacher.md**：時間配分の補足、解答・確認点
- **your-app/**：制作5回で改造する完成版のコピー、設計・評価ひな形
- **docs/**：共通の評価質問、講師向け準備、参考資料
- **scripts/build_sessions.py**：講師用。完成版をコピーし、機能の削除・コメントアウトで各回を生成

複雑なフレームワークや独自クラスを増やさず、普通の関数、if、for、リスト、辞書を中心に書いています。
各回は前回の学生の完成状況に依存せず起動できます。第1回は完成品の観察、第2回はCLI、第3回からWebです。

## 授業一覧

| 回 | テーマ | 教材 | 演習の中心 |
|---|---|---|---|
| 1 | LLMイントロ・歴史・代表モデル | [手順](session01/README.md) / [PDF](session01/slides.pdf) | 完成品の観察 |
| 2 | LLM APIの基礎 | [手順](session02/README.md) / [PDF](session02/slides.pdf) | PythonでAPIを呼ぶ |
| 3 | Webアプリへの組み込み | [手順](session03/README.md) / [PDF](session03/slides.pdf) | fetchで送信する |
| 4 | プロンプトと外部知識 | [手順](session04/README.md) / [PDF](session04/slides.pdf) | 指示・資料・質問を分ける |
| 5 | RAG・キーワード検索 | [手順](session05/README.md) / [PDF](session05/slides.pdf) | 一致する検索語を数える |
| 6 | Embedding・意味検索 | [手順](session06/README.md) / [PDF](session06/slides.pdf) | ベクトルの類似度を計算 |
| 7 | DB・APIとFunction Calling | [手順](session07/README.md) / [PDF](session07/slides.pdf) | 検証した引数でSQL検索 |
| 8 | 評価・改善・安全な運用 | [手順](session08/README.md) / [PDF](session08/slides.pdf) | 評価と利用上限 |
| 9〜13 | オリジナルアプリ制作 | [制作手順](your-app/README.md) | 企画・実装・評価・発表 |

1回90分想定。座学には講師デモと短い確認演習を含みます。
第1〜8回のスライドは各30枚、合計240枚です。
具体例・処理途中のデータ・演習の確認ページを、説明や作業中の投影に使います。
追加ページの使い方は[スライド進行ガイド](docs/slide-teaching-guide.md)を参照してください。

## APIを使う設定

生成・関数選択は **gpt-6-luna**、Responses APIを使用します。
推論設定は `reasoning={'effort':'none'}`。Embeddingには **text-embedding-3-small** を使います。

講師指定のAPI利用環境と予算を確認してください。
毎回の授業開始時に、アプリを起動するターミナルで次を実行します。キーの入力は画面にもコマンド履歴にも残りません。

```bash
read -rsp "APIキー: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
```

同じターミナルからアプリを起動してください。新しいターミナルでは再設定が必要です。終了時はサーバーをCtrl+Cで停止し、`unset OPENAI_API_KEY` を実行してターミナルを閉じます。キーは `.env`、Codespaces Secrets、シェルの設定ファイルに保存しません。
設定変更後はサーバーを起動し直します。キー、DBはGit管理しません。キーが漏れたら無効化・再発行します。
使用モデルの可否と利用料金は、開講時に講師が確認してください。

### APIで確認すること

sample-appと各回の演習・解答は、生成・意味検索・関数選択に実際のAPIを使います。
第2・4回の穴埋めもAPIで確認します。API利用不可なら講師の実演を観察し、未検証を記録します。
検索結果がない場合は回答を生成しません。第8回の利用上限はこの経路で確認できます。
your-appは引き続きデモモードを含みます。APIを使う場合だけ `export DEMO_MODE=false` を設定し、終了時に `unset DEMO_MODE` も実行します。

## よくある問題

| 症状 | 対処 |
|---|---|
| ModuleNotFoundError | `.venv` を有効化。ルートで `python -m pip install -r requirements-dev.txt` |
| ポートが使用中 | 別のターミナルのサーバーをCtrl+Cで停止 |
| 変更が反映されない | Python/環境変数は再起動、JSはブラウザ再読み込み |
| TODOエラー | 指定箇所を実装し、仮のraise/throwを削除 |
| ベクトルがない・モデルが違う | 資料登録後、現在のモードで `python build_index.py` |
| 検索結果0件 | キーワードは「SQLite 保存」のように空白で区切る |
| APIが使えない | キー・gpt-6-lunaの利用権限・利用枠を講師と確認 |
| 429 | 教材の回数制限か外部APIの制限か、表示を確認 |

## ローカルPCでのセットアップ

Python 3.12で、リポジトリのルートから実行します。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Windows PowerShellの有効化は `.venv\Scripts\Activate.ps1` です。

## 講師向け

[講師用ガイド](docs/teacher-guide.md) / [参考資料](docs/references.md) / [実装の検証](docs/validation.md)

```bash
python -m pytest -q
```

テストは外部APIを実際には呼びません。API互換の応答を与えたテストで検証します。
スライドはVS CodeのMarp拡張でプレビューできます。再出力は `scripts/export-slides.sh` を参照してください。
