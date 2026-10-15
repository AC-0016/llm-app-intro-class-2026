"""設定。APIキーはこのファイルに書かず、ターミナルの環境変数で渡す。"""
import os

# 使うモデル。環境変数 OPENAI_MODEL があれば、そちらを使う。
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')

# LLMへの指示。2つのスクリプトで同じ指示を使い、違いを「履歴の有無」だけにする。
INSTRUCTIONS = 'あなたは授業の学習を手伝うアシスタントです。日本語で簡潔に答えてください。'
