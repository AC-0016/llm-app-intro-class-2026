"""Webアプリ制作の進捗をSQLiteに保存し、読み出す。

tasks テーブル
  id   : 番号
  task : やること
  done : 完了フラグ。SQLiteには真偽値の型が無いので、1（True）と0（False）で保存する。
"""
import sqlite3

# 最初に入れておく架空の進捗。(id, やること, 完了フラグ)
FIRST_TASKS = [
    (1, '画面のHTMLとCSSを作る', 1),
    (2, 'FastAPIで質問を受け取るAPIを作る', 1),
    (3, 'SQLiteに資料を保存する', 1),
    (4, 'Janomeでキーワード検索を作る', 0),
    (5, '回答に資料IDを付ける', 0),
    (6, 'GitHubにコミットしてURLを提出する', 0),
]


def init_db(database):
    """テーブルが無ければ作り、最初の進捗を入れる。database はDBファイルの場所。"""
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task TEXT, done INTEGER)')
    # INSERT OR IGNORE は、同じidの行がすでにあれば何もしない。
    # そのため、再起動しても変更済みの進捗は上書きされない。
    cursor.executemany('INSERT OR IGNORE INTO tasks (id, task, done) VALUES (?, ?, ?)', FIRST_TASKS)
    conn.commit()
    conn.close()


def get_tasks(database, status):
    """database のDBから進捗を読み出す。

    status が 'all' なら全件、'todo' なら未完了だけ、'done' なら完了だけを返す。
    返す値の例: [{'id': 4, 'task': 'Janomeでキーワード検索を作る', 'done': False}]
    """
    # 実行するSQLは、この3つの決まった文だけ。LLMが作った文字列をSQLに入れない。
    if status == 'all':
        sql = 'SELECT id, task, done FROM tasks ORDER BY id'
    elif status == 'todo':
        sql = 'SELECT id, task, done FROM tasks WHERE done = 0 ORDER BY id'
    elif status == 'done':
        sql = 'SELECT id, task, done FROM tasks WHERE done = 1 ORDER BY id'
    else:
        raise ValueError('status は all・todo・done のどれかにしてください。')

    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        # DBの1/0を、True/Falseに直して返す。
        tasks.append({'id': row[0], 'task': row[1], 'done': row[2] == 1})
    return tasks
