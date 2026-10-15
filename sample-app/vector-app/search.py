"""ベクトルどうしの近さ（コサイン類似度）を計算し、質問に意味が近い資料を探す。"""
import math


def cosine_similarity(a, b):
    """2つのベクトルの向きがどれだけ近いかを、-1〜1の数で返す。

    1に近いほど意味が近い。同じ向きなら1、関係がなければ0に近くなる。
    計算式: (a と b の内積) ÷ (a の長さ × b の長さ)
    """
    dot = 0.0       # 内積: 同じ位置の数どうしを掛けて、全部足したもの
    a_length = 0.0  # a の長さの2乗
    b_length = 0.0  # b の長さの2乗
    for i in range(len(a)):
        dot += a[i] * b[i]
        a_length += a[i] * a[i]
        b_length += b[i] * b[i]
    if a_length == 0 or b_length == 0:
        return 0.0  # 長さ0のベクトルは向きが無いので、0とする
    return dot / (math.sqrt(a_length) * math.sqrt(b_length))


def search_documents(question_vector, documents, top_k, min_similarity):
    """質問のベクトルに近い資料を、近い順に top_k 件まで返す。

    類似度が min_similarity より小さい資料は、関係が薄いとみなして返さない。
    返す資料には、類似度を 'score' として追加する（ベクトルそのものは返さない）。
    """
    results = []
    for document in documents:
        score = cosine_similarity(question_vector, document['vector'])
        if score >= min_similarity:
            results.append({
                'id': document['id'],
                'source': document['source'],
                'title': document['title'],
                'heading': document['heading'],
                'body': document['body'],
                'score': score,
            })

    # 類似度の大きい順に並べる。
    results.sort(key=get_score, reverse=True)
    return results[:top_k]


def get_score(result):
    """並べ替えで使う。資料の類似度を返す。"""
    return result['score']
