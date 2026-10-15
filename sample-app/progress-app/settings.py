"""アプリの設定。APIキーはこのファイルに書かず、ターミナルの環境変数で渡す。"""
import os
from pathlib import Path

# このファイルがあるフォルダ。DBや画面のファイルを探すときの基準にする。
BASE_DIR = Path(__file__).resolve().parent

# 使うモデル。環境変数 OPENAI_MODEL があれば、そちらを使う。
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')

# 進捗を保存するSQLiteのファイル。Gitには入れない。
DATABASE = BASE_DIR / 'progress.db'
