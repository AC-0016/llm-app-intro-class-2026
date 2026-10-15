"""data/ フォルダのMarp形式のスライド（*.md）を読み、Janomeで単語に分けて、スライド1枚を1行としてDBに保存する。

実行: python init_db.py
スライドを足したり直したりしたら、もう一度実行してからサーバーを再起動する。
実行するたびに、DBの資料を全部作り直す。

documents テーブル
  id      : 資料ID（1から順に付ける）
  source  : 元のファイル名（例: session01.md）
  slide   : 何枚目のスライドか（Marpの画面のページ番号と同じ）
  title   : スライド全体の題名（最初のスライドの見出し）
  heading : そのスライドの見出し
  body    : そのスライドの本文
  words   : 題名・見出し・本文から取り出した検索用の単語。SQLiteにリストの型は無いので、JSONの文字列で保存する
            （例: ["学習", "推論", "モデル"]）。質問のたびに資料を形態素解析しなくてよいように、先に作っておく

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
import sqlite3
from pathlib import Path
from search import extract_words

# ===== 設定 =====

# このファイルがあるフォルダ。
BASE_DIR = Path(__file__).resolve().parent

# スライドのMarkdownを置くフォルダ。
DATA_DIR = BASE_DIR / 'data'

# 資料を保存するSQLiteのファイル。main.py の DATABASE と同じ場所にする。Gitには入れない。
DATABASE = BASE_DIR / 'documents.db'

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


def add_words(documents):
    """全部の資料をJanomeで単語に分け、各資料の 'words' に入れる。

    質問と同じ extract_words() を使う。分け方が違うと、同じ言葉でも一致しなくなるため。
    """
    for document in documents:
        document['words'] = extract_words(
            document['title'] + '\n' + document['heading'] + '\n' + document['body'])


def init_db(database, documents):
    """documents テーブルを作り直し、資料を全部保存する。"""
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
        words   TEXT NOT NULL
    )''')
    document_id = 0
    for document in documents:
        document_id += 1
        cursor.execute(
            'INSERT INTO documents (id, source, slide, title, heading, body, words) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (document_id, document['source'], document['slide'],
             document['title'], document['heading'], document['body'],
             # 単語のリストを、JSONの文字列にして保存する。ensure_ascii=False で日本語のまま読めるようにする
             json.dumps(document['words'], ensure_ascii=False)),
        )
    conn.commit()
    conn.close()


if __name__ == '__main__':
    # 先に全部のスライドを読み、単語に分ける。失敗したら、DBを変える前にここで止まる。
    documents = read_all_slides(DATA_DIR)
    add_words(documents)
    init_db(DATABASE, documents)
    print(f'{len(documents)}個の資料を {DATABASE.name} に保存しました。')
