"""data/ の追加・変更・削除をDBに反映。サーバーを止めて実行する。"""
from knowledge import init_documents
from assignment_tools import init_assignments

if __name__ == '__main__':
    count = init_documents()
    init_assignments()
    print(f'{count}個の資料を登録しました。')
