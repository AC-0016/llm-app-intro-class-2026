"""data/ フォルダのMarp形式のスライド（*.md）を読み、ベクトルにして、スライド1枚を1行としてDBに保存する。

実行: python init_db.py
スライドを足したり直したりしたら、もう一度実行してからサーバーを再起動する。
実行するたびに、DBの資料とベクトルを全部作り直す（Embedding APIを呼ぶので、APIキーが必要）。

documents テーブル
  id      : 資料ID（1から順に付ける）
  source  : 元のファイル名（例: session01.md）
  slide   : 何枚目のスライドか（Marpの画面のページ番号と同じ）
  title   : スライド全体の題名（最初のスライドの見出し）
  heading : そのスライドの見出し
  body    : そのスライドの本文
  vector  : 本文などをベクトルにした数値のリスト。SQLiteにリストの型は無いので、JSONの文字列で保存する
  embedding_model : ベクトルを作ったモデルの名前。質問も同じモデルでベクトルにする必要がある

Marp形式のMarkdownの例:

    ---
    marp: true
    ---
    # 第1回：LLMイントロダクション

    ---
    ## LLMとは
    大規模言語モデル。…
    <!-- 発表者用のメモ -->

- 先頭の「---」から次の「---」までは、スライドの設定（フロントマター）。資料にしない。
- 「---」だけの行が、スライドの区切り。
- <!-- --> のコメント（発表者メモや出典）と画像は、画面の文章ではないので資料にしない。
"""
import json
import os
import sqlite3
from pathlib import Path
from llm import embed_texts

# ===== 設定 =====

# このファイルがあるフォルダ。
BASE_DIR = Path(__file__).resolve().parent

# スライドのMarkdownを置くフォルダ。
DATA_DIR = BASE_DIR / 'data'

# 資料を保存するSQLiteのファイル。main.py の DATABASE と同じ場所にする。Gitには入れない。
DATABASE = BASE_DIR / 'documents.db'

# 文章をベクトルにするモデル。main.py の EMBEDDING_MODEL と同じにする。
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

# 1つの資料の本文の上限。長すぎる資料はLLMに渡す文章が増えすぎる。
MAX_BODY_LENGTH = 1000


def read_all_slides(data_dir):
    """data_dir フォルダの *.md を読み、資料のリストを返す。

    1つの資料は次のような辞書になる。
    {'source': 'session01.md', 'slide': 3, 'title': '第1回：LLMイントロダクション',
     'heading': '今日の流れ', 'body': '| 内容 |…'}
    """
    documents = []
    # ファイル名の順に読む。
    for path in sorted(data_dir.glob('*.md')):
        slides = split_slides(path.read_text(encoding='utf-8'))

        # 最初のスライドの見出しを、題名にする。見出しが無いときはファイル名を使う。
        title = path.stem
        first_heading, _ = read_slide(slides[0])  # 本文はここでは使わないので _ で受ける
        if first_heading != '':
            title = first_heading

        slide_number = 0
        for lines in slides:
            slide_number += 1  # Marpの画面のページ番号と同じ、1から数えた番号
            heading, body = read_slide(lines)
            if body == '':
                continue  # 本文が無いスライドは資料にしない
            if len(body) > MAX_BODY_LENGTH:
                raise ValueError(f'{path.name} の{slide_number}枚目が長すぎます。'
                                 f'スライドを分けて{MAX_BODY_LENGTH}文字以内にしてください。')
            documents.append({
                'source': path.name,
                'slide': slide_number,
                'title': title,
                'heading': heading,
                'body': body,
            })
    return documents


def split_slides(text):
    """Markdown全体を、スライドごとの「行のリスト」に分けて返す。"""
    lines = text.splitlines()

    # 先頭が「---」なら、次の「---」までは設定なので飛ばす。
    start = 0
    if len(lines) > 0 and lines[0] == '---':
        for i in range(1, len(lines)):
            if lines[i] == '---':
                start = i + 1
                break

    slides = []
    current = []      # 今読んでいるスライドの行
    in_code = False   # ```で囲まれたコードの中かどうか
    for line in lines[start:]:
        if line.startswith('```'):
            in_code = not in_code
        if line == '---' and not in_code:
            # 区切りが来たので、ここまでを1枚のスライドにする。
            slides.append(current)
            current = []
        else:
            current.append(line)
    slides.append(current)  # 最後のスライドも忘れずに追加する
    return slides


def read_slide(lines):
    """1枚のスライドの行から、見出しと本文を取り出して返す。"""
    heading = ''
    body_lines = []
    in_code = False      # ```で囲まれたコードの中かどうか
    in_comment = False   # <!-- --> のコメントの中かどうか

    for line in lines:
        # コードの中は、そのまま本文にする（「# 」で始まる行も見出しではない）。
        if line.startswith('```'):
            in_code = not in_code
            body_lines.append(line)
            continue
        if in_code:
            body_lines.append(line)
            continue

        # コメントは飛ばす。複数行にまたがることもあるので、「-->」まで飛ばす。
        if line.strip().startswith('<!--'):
            in_comment = True
        if in_comment:
            if '-->' in line:
                in_comment = False
            continue

        # 画像（![…](…)）は飛ばす。
        if line.startswith('!['):
            continue

        # 最初の見出しを、このスライドの見出しにする。
        if heading == '' and (line.startswith('# ') or line.startswith('## ')):
            heading = line.lstrip('#').strip()
            continue

        body_lines.append(line)

    body = '\n'.join(body_lines).strip()
    return heading, body


def add_vectors(documents, embedding_model):
    """全部の資料をEmbedding APIでベクトルにし、各資料の 'vector' に入れる。"""
    texts = []
    for document in documents:
        texts.append(document['title'] + '\n' + document['heading'] + '\n' + document['body'])
    # 1回のAPI呼び出しで、全部の資料をまとめてベクトルにする。
    vectors = embed_texts(texts, embedding_model)
    for i in range(len(documents)):
        documents[i]['vector'] = vectors[i]  # 資料と同じ順番でベクトルが返ってくる


def init_db(database, documents, embedding_model):
    """documents テーブルを作り直し、資料とベクトルを全部保存する。"""
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    # 古い資料が残らないように、テーブルごと消してから作る。
    cursor.execute('DROP TABLE IF EXISTS documents')
    cursor.execute('''CREATE TABLE documents (
        id      INTEGER PRIMARY KEY,
        source  TEXT NOT NULL,
        slide   INTEGER NOT NULL,
        title   TEXT NOT NULL,
        heading TEXT NOT NULL,
        body    TEXT NOT NULL,
        vector  TEXT NOT NULL,
        embedding_model TEXT NOT NULL
    )''')
    document_id = 0
    for document in documents:
        document_id += 1
        cursor.execute(
            'INSERT INTO documents (id, source, slide, title, heading, body, vector, embedding_model)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (document_id, document['source'], document['slide'],
             document['title'], document['heading'], document['body'],
             json.dumps(document['vector']),  # 数値のリストを、JSONの文字列にして保存する
             embedding_model),
        )
    conn.commit()
    conn.close()


if __name__ == '__main__':
    # 先に全部のスライドを読み、ベクトルにする。失敗したら、DBを変える前にここで止まる。
    documents = read_all_slides(DATA_DIR)
    print(f'{len(documents)}個の資料をEmbedding APIへ送り、ベクトルにします。利用料金が発生します。')
    add_vectors(documents, EMBEDDING_MODEL)
    init_db(DATABASE, documents, EMBEDDING_MODEL)
    print(f'{len(documents)}個の資料とベクトルを {DATABASE.name} に保存しました。')
