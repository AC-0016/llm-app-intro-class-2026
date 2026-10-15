# Webアプリの復習ノート

## ブラウザとサーバー
ブラウザはHTMLを表示し、CSSで見た目を整え、JavaScriptで操作に反応します。FastAPIはサーバー側でリクエストを受け取り、Pythonで処理してJSONを返します。

## fetchから保存まで
JavaScriptのfetchでPOSTリクエストを送ります。FastAPIがJSONを受け取り、Pythonのsqlite3でINSERTを実行してcommitします。ブラウザはSQLiteに直接接続しません。

## SQLiteと永続化
SQLiteはファイルにデータを保存するデータベースです。Pythonのリストだけに保存した内容は、サーバーの再起動で失われます。SQL実行後にcommitして保存すれば、DBファイルを保持する限り再起動後も読み出せます。

## SQLインジェクション対策
ユーザー入力をSQLの文字列へ直接つなげません。SQLには?を書き、値は別の引数で渡すパラメータバインディングを使います。例: cursor.execute('SELECT title FROM todos WHERE id = ?', (todo_id,))。
