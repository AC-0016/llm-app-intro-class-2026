from embeddings import build_embeddings

if __name__ == '__main__':
    print('各資料をEmbedding APIへ送信します。利用料金が発生します。')
    print(f'{build_embeddings()}個のベクトルを保存しました。')
