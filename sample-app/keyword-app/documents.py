"""data/ フォルダのMarp形式のスライド（*.md）を読み、スライド1枚を1つの資料にする。

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
- 最初のスライドの見出し（# 第1回…）を、スライド全体の題名にする。
- 各スライドの最初の見出し（## LLMとは）を、その資料の見出しにする。
- <!-- --> のコメント（発表者メモや出典）と画像は、画面の文章ではないので資料にしない。
"""

# 1つの資料の本文の上限。長すぎる資料はLLMに渡す文章が増えすぎる。
MAX_BODY_LENGTH = 1000


def load_documents(data_dir):
    """data_dir フォルダの *.md を読み、資料のリストを返す。

    1つの資料は次のような辞書になる。
    {'id': 3, 'source': 'session01.md', 'slide': 3, 'title': '第1回：LLMイントロダクション',
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
                'id': len(documents) + 1,  # 1から順に番号を付ける
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
