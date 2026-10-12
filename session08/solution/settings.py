"""設定を読む。APIキーをこのファイルに書かない。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# 授業ごとに、起動するターミナルで設定した環境変数だけを読む。
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
DATABASE = BASE_DIR / 'classroom.db'
