"""data/ フォルダのMarkdownを読み、「## 見出し」ごとに1つの資料に分ける。"""

# 1つの資料の本文の上限。長すぎる資料はLLMに渡す文章が増えすぎる。
MAX_BODY_LENGTH = 1000


def load_documents(data_dir):
    """data_dir フォルダの *.md を読み、資料のリストを返す。

    1つの資料は次のような辞書になる。
    {'id': 1, 'source': '01-web.md', 'title': 'Webアプリの復習ノート',
     'heading': 'ブラウザとサーバー', 'body': 'ブラウザはHTMLを表示し…'}
    """
    documents = []
    # ファイル名の順（01-web.md、02-course.md…）に読む。
    for path in sorted(data_dir.glob('*.md')):
        title = path.stem  # 「# 資料名」が無いときはファイル名を使う
        heading = '本文'   # 最初の「## 見出し」より前の文章に付ける見出し
        lines = []
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('# '):
                title = line[2:]
            elif line.startswith('## '):
                # 次の見出しが来たので、ここまでの文章を1つの資料にする。
                add_document(documents, path.name, title, heading, lines)
                heading = line[3:]
                lines = []
            else:
                lines.append(line)
        # ファイルの最後の見出しの文章も資料にする。
        add_document(documents, path.name, title, heading, lines)
    return documents


def add_document(documents, source, title, heading, lines):
    """行のリストを1つの本文にまとめ、資料のリストに追加する。"""
    body = '\n'.join(lines).strip()
    if body == '':
        return  # 本文が無い見出しは資料にしない
    if len(body) > MAX_BODY_LENGTH:
        raise ValueError(f'{source} の「{heading}」が長すぎます。'
                         f'見出しを増やして{MAX_BODY_LENGTH}文字以内に分けてください。')
    documents.append({
        'id': len(documents) + 1,  # 1から順に番号を付ける
        'source': source,
        'title': title,
        'heading': heading,
        'body': body,
    })
