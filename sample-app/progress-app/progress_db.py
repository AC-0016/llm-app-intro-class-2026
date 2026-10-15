"""Webアプリ制作の進捗をSQLiteに保存し、読み出す・追加する・完了フラグを変える。

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


# やることの文字数の上限。
MAX_TASK_LENGTH = 100


def add_task(database, task):
    """新しいやることを、未完了（done = 0）で追加する。

    返す値は、追加した行を入れたリスト。例: [{'id': 7, 'task': 'READMEを書く', 'done': False}]
    get_tasks() と同じ形にして、画面で同じように表示できるようにする。
    """
    # LLMが作った値なので、保存する前に必ず確かめる。
    if not isinstance(task, str):
        raise ValueError('やることは文字列で指定してください。')
    task = task.strip()
    if task == '' or len(task) > MAX_TASK_LENGTH:
        raise ValueError(f'やることは1〜{MAX_TASK_LENGTH}文字にしてください。')

    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    # id を書かないと、SQLiteが今ある一番大きいidの次の番号を付ける。
    # 値は ? の場所に別の引数で渡す（SQLの文字列に直接つなげない）。
    cursor.execute('INSERT INTO tasks (task, done) VALUES (?, 0)', (task,))
    new_id = cursor.lastrowid  # 今追加した行のid
    conn.commit()
    conn.close()
    return [{'id': new_id, 'task': task, 'done': False}]


def set_task_done(database, task_id, done):
    """task_id のやることの完了フラグを、done（True なら完了、False なら未完了）にする。

    返す値は、変更した後の行を入れたリスト。例: [{'id': 4, 'task': 'Janomeでキーワード検索を作る', 'done': True}]
    """
    # LLMが作った値なので、保存する前に必ず確かめる。
    # True/False は Python では整数の仲間でもあるので、先に bool かどうかを調べて除く。
    if isinstance(task_id, bool) or not isinstance(task_id, int):
        raise ValueError('task_id は整数で指定してください。')
    if not isinstance(done, bool):
        raise ValueError('done は true か false で指定してください。')

    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    # DBには1（True）か0（False）で保存する。
    done_value = 1 if done else 0
    cursor.execute('UPDATE tasks SET done = ? WHERE id = ?', (done_value, task_id))
    changed = cursor.rowcount  # 変更した行の数。そのidが無ければ0になる
    conn.commit()
    if changed == 0:
        conn.close()
        raise ValueError(f'id {task_id} のやることはありません。')
    cursor.execute('SELECT id, task, done FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return [{'id': row[0], 'task': row[1], 'done': row[2] == 1}]
