"""資料の読み込みと検索。1つの関数を順番に追える書き方にする。"""
import sqlite3
from janome.tokenizer import Tokenizer
from settings import BASE_DIR, DATABASE

# 辞書の読み込みに時間がかかるため、起動時に1回だけ作る。
tokenizer = Tokenizer()
# 検索に使う品詞。助詞・助動詞・記号などは除く。
CONTENT_POS = ['名詞', '動詞', '形容詞']
# 内容を持たない名詞の細分類。「の」「それ」「〜物」など。
SKIP_DETAILS = ['非自立', '代名詞', '接尾']
# どの資料にも出てくるため、一致しても手がかりにならない語。
STOP_WORDS = ['する', 'ある', 'いる', 'なる', 'できる', 'れる', 'られる']


def read_documents():
    # ファイル名順に読み、## 見出しごとに分割する。
    chunks = []
    for path in sorted((BASE_DIR / 'data').glob('*.md')):
        title = path.stem
        heading = '本文'
        lines = []
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('# '):
                title = line[2:]
            elif line.startswith('## '):
                add_chunk(chunks, path.name, title, heading, lines)
                heading = line[3:]
                lines = []
            else:
                lines.append(line)
        add_chunk(chunks, path.name, title, heading, lines)
    if len(chunks) > 100:
        raise ValueError('教材では資料を100断片以内にしてください。')
    return chunks


def add_chunk(chunks, source, title, heading, lines):
    body = '\n'.join(lines).strip()
    if body:
        # 巨大な段落は見出しを追加して人が分割する。途中で黙って切らない。
        if len(body) > 1000:
            raise ValueError(source + ': 1つの見出しの本文は1000文字以内にしてください。')
        chunks.append({'source': source, 'title': title, 'heading': heading, 'body': body})


def init_documents():
    chunks = read_documents()  # 失敗する場合、元のDBを変更する前に止まる。
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY, source TEXT, title TEXT, heading TEXT, body TEXT
    )''')
    # data/ が原本。再登録時に削除した資料も反映する。
    cursor.execute('DELETE FROM chunks')
    for number, chunk in enumerate(chunks, start=1):
        cursor.execute(
            'INSERT INTO chunks (id, source, title, heading, body) VALUES (?, ?, ?, ?, ?)',
            (number, chunk['source'], chunk['title'], chunk['heading'], chunk['body']),
        )
    conn.commit()
    conn.close()
    return len(chunks)


def all_chunks():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, source, title, heading, body FROM chunks ORDER BY id')
    rows = cursor.fetchall()
    conn.close()
    chunks = []
    for row in rows:
        chunks.append({'id': row[0], 'source': row[1], 'title': row[2],
                       'heading': row[3], 'body': row[4]})
    return chunks


def extract_words(text):
    # Janomeで形態素に分け、名詞・動詞・形容詞の基本形だけを取り出す。
    # 「保存する」「保存して」はどちらも「保存」「する」になり、活用の違いを吸収できる。
    words = []
    for token in tokenizer.tokenize(text):
        pos = token.part_of_speech.split(',')
        if pos[0] not in CONTENT_POS or pos[1] in SKIP_DETAILS:
            continue
        word = token.base_form
        if word == '*':
            word = token.surface
        word = word.lower()
        if word not in STOP_WORDS and word not in words:
            words.append(word)
    return words


def search_keyword(question, top_k):
    # 質問文から検索語を自動で取り出す。空白区切りの入力は不要。
    words = extract_words(question)
    results = []
    for chunk in all_chunks():
        # 部分一致ではなく、資料側も同じ方法で単語に分けて比べる。
        chunk_words = extract_words(chunk['title'] + '\n' + chunk['heading'] + '\n' + chunk['body'])
        score = 0
        # BEGIN EXERCISE keyword
        for word in words:
            if word in chunk_words:
                score += 1
        # END EXERCISE keyword
        if score > 0:
            chunk['score'] = score
            results.append(chunk)
    results.sort(key=get_score, reverse=True)
    return results[:top_k]


def get_score(chunk):
    return chunk['score']
