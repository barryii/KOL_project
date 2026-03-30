from transformers import pipeline
from database import DBManager
import os, dotenv

dotenv.load_dotenv()

# 載入支援多語言或中文的情緒分析小模型
# (初次執行會下載模型，檔案通常不到 1GB)
sentiment_pipeline = pipeline(
    'sentiment-analysis', 
    model='lxyuan/distilbert-base-multilingual-cased-sentiments-student'
)

try:
    with DBManager().connect_to_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM video_comments WHERE sentiment IS NULL LIMIT 10')
            results = cursor.fetchall()
except Exception as e:
    print(f'最終所有資料庫連線皆失敗，或執行查詢時發生錯誤: {e}')

for row in results:
    result = sentiment_pipeline(row['text_content'])
    print(f'video_id: {row['video_id']}')
    print(f'text_content: {row['text_content']}')
    print(f'author_name: {row['author_name']}')
    print(f'author_id: {row['author_id']}')
    print(f'like_count: {row['like_count']}')
    print(f'reply_count: {row['reply_count']}')
    print(f'published_at: {row['published_at']}')
    print(result) 
    print()
    # 預期輸出類似: [{'label': 'negative', 'score': 0.85}]

