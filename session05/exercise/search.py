"""Janomeで文章を単語に分け、質問に関係する資料を探す。"""
from janome.tokenizer import Tokenizer

# 辞書の読み込みに時間がかかるので、起動時に1回だけ作って使い回す。
tokenizer = Tokenizer()

# 検索に使う品詞。助詞（は・を・に）や記号（？）は使わない。
USE_PARTS = ['名詞', '動詞', '形容詞']

# 名詞のうち、意味の薄いもの。「の」は非自立、「それ」は代名詞、「提出物」の「物」は接尾。
SKIP_DETAILS = ['非自立', '代名詞', '接尾']

# どの文章にも出てくるため、検索の手がかりにならない語。
STOP_WORDS = ['する', 'ある', 'いる', 'なる', 'できる', 'れる', 'られる']


def extract_words(text):
    """文章から検索に使う単語のリストを返す。

    例: 'SQLiteに保存するには？' → ['sqlite', '保存']
    """
    words = []
    for token in tokenizer.tokenize(text):
        # part_of_speech は '名詞,サ変接続,*,*' のような文字列なので、カンマで分ける。
        parts = token.part_of_speech.split(',')
        if parts[0] not in USE_PARTS:
            continue
        if parts[1] in SKIP_DETAILS:
            continue

        # 基本形にそろえる。「閉じて」の「閉じ」→「閉じる」。
        word = token.base_form
        if word == '*':
            # 辞書に無い語は基本形が '*' になるので、文章に書かれた形を使う。
            word = token.surface
        # 'SQLite' と 'sqlite' を同じ語として扱う。
        word = word.lower()

        if word in STOP_WORDS:
            continue
        if word not in words:  # 同じ語は1回だけ入れる
            words.append(word)
    return words


def search_documents(keywords, documents, top_k):
    """検索語を多く含む資料を、多い順に top_k 件まで返す。

    資料の単語（document['words']）は、init_db.py が同じ extract_words() で作ってDBに保存したもの。
    返す資料には、一致した検索語の数を 'score' として追加する（単語のリストは返さない）。
    """
    results = []
    for document in documents:
        score = 0
        # TODO: 資料の単語に含まれる検索語の数を数える。下のコメントを外す。
        # （埋めるまでは score が 0 のままなので、どの資料も見つからない）
        # for keyword in keywords:
        #     if keyword in document['words']:
        #         score += 1

        if score > 0:
            results.append({
                'id': document['id'],
                'source': document['source'],
                'slide': document['slide'],
                'title': document['title'],
                'heading': document['heading'],
                'body': document['body'],
                'score': score,
            })

    # スコアの大きい順に並べる。同じスコアなら資料IDの小さい順のまま。
    # TODO: 並べ替えて、先頭から top_k 件だけ返す。下の2行のコメントを外し、仮の return の行を消す。
    # results.sort(key=get_score, reverse=True)
    # return results[:top_k]
    return results  # 仮。見つかった資料を、並べ替えずに全部返している


def get_score(result):
    """並べ替えで使う。資料のスコアを返す。"""
    return result['score']
