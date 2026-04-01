from transformers import pipeline
from sentence_transformers import SentenceTransformer
from database import DBManager
import os, dotenv

dotenv.load_dotenv()

# 載入支援多語言或中文的情緒分析小模型
# (初次執行會下載模型，檔案通常不到 1GB)
# sentiment_pipeline = pipeline(
#     'sentiment-analysis', 
#     model='lxyuan/distilbert-base-multilingual-cased-sentiments-student'
# )
sentiment_pipeline = pipeline(
    'text-classification', 
    model='nlptown/bert-base-multilingual-uncased-sentiment'
)
# model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

try:
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM video_comments WHERE sentiment IS NULL LIMIT 20')
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
#     # embeddings = model.encode(row['text_content'])
#     # print(embeddings.shape)
#     # similarities = model.similarity(embeddings, embeddings)
#     # print(similarities)

# from transformers import AutoModelForSequenceClassification, AutoTokenizer
# import torch

# # 載入模型和分詞器
# model = AutoModelForSequenceClassification.from_pretrained("jackietung/bert-base-chinese-sentiment-finetuned")
# tokenizer = AutoTokenizer.from_pretrained("jackietung/bert-base-chinese-sentiment-finetuned")

# # 準備輸入
# for row in results:
#     text = row['text_content']
#     inputs = tokenizer(text, return_tensors="pt")

#     # 進行預測
#     with torch.no_grad():
#         outputs = model(**inputs)
#         predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
#         # 獲取預測結果
#         label_names = ["負面", "正面", "中性"]
#         predicted_class = torch.argmax(predictions, dim=1).item()
        
#         print(f"預測類別: {label_names[predicted_class]}")
#         print(f"預測分數: {predictions[0][predicted_class].item():.4f}")
        
#         print(f'video_id: {row['video_id']}')
#         print(f'text_content: {row['text_content']}')
#         print(f'author_name: {row['author_name']}')
#         print(f'author_id: {row['author_id']}')
#         print(f'like_count: {row['like_count']}')
#         print(f'reply_count: {row['reply_count']}')
#         print(f'published_at: {row['published_at']}')
#         # 顯示所有類別的分數
#         for i, label in enumerate(label_names):
#             print(f"{label} 分數: {predictions[0][i].item():.4f}")
#         print()

