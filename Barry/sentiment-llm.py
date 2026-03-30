from transformers import pipeline
from sentence_transformers import SentenceTransformer
from database import DBManager
from datetime import datetime
from youtuber_info import Chienseating, HowHowEat
import dotenv
import ollama
import json
import concurrent.futures

dotenv.load_dotenv()

def data(channel: Chienseating | HowHowEat, limit: int = 100):
    try:
        with DBManager().connect_to_db() as conn:
            with conn.cursor(dictionary=True) as cursor:
                if limit:
                    cursor.execute('SELECT * FROM video_comments WHERE channel_id = %s and sentiment IS NULL LIMIT %s', (channel.channel_id, limit))
                else:
                    cursor.execute('SELECT * FROM video_comments WHERE channel_id = %s and sentiment IS NULL', (channel.channel_id,))
                results = cursor.fetchall()
                return results
    except Exception as e:
        print(f'最終所有資料庫連線皆失敗，或執行查詢時發生錯誤: {e}')

def analyze_sentiment_batch_local(comments_chunk):
    text_lines = []
    for i, c in enumerate(comments_chunk):
        text_lines.append(f'留言 ID {i+1}：「{c['text_content']}」')
        
    messages_str = '\n'.join(text_lines)
    prompt = f'''
    你是一個網路社群的情緒分析專家。請批次分析以下 YouTube 留言的情緒。
    
    以下是留言列表：
    {messages_str}
    
    請以 JSON Array 格式回傳（必須是合法的 JSON 陣列），必須包含每一個留言的分析結果，每個陣列元素包含：
    1. 'id': 對應上方的留言 ID 整數 (1 到 {len(comments_chunk)})
    2. 'sentiment': 只能是 'Positive', 'Negative', 或 'Neutral'
    3. 'score': 1 到 5 分整數 (1為極度負面，5為極度正面)
    '''

    response = ollama.chat(
        model='qwen2.5:7b',
        messages=[{'role': 'user', 'content': prompt}],
        format='json'
    )
    
    try:
        return json.loads(response['message']['content'])
    except json.JSONDecodeError:
        return None

def process_channel(channel, limit):
    channel_name = type(channel).__name__
    comments = data(channel, limit)
    
    if not comments:
        print(f'[{channel_name}] 沒有需要處理的資料')
        return

    print(f'[{channel_name}] 開始處理 {len(comments)} 筆資料')
    start_time = datetime.now()
    last_time = None
    print(f'[{channel_name}] 開始時間: {start_time}')
    
    batch_size = 10
    for chunk_idx in range(0, len(comments), batch_size):
        chunk = comments[chunk_idx:chunk_idx + batch_size]
        results = analyze_sentiment_batch_local(chunk)
        # print(results)
        
        updates = []
        
        # 防呆機制：如果 LLM 回傳 {"data": [...]} 等字典包裝結構，嘗試把它拆出來
        if isinstance(results, dict):
            for v in results.values():
                if isinstance(v, list):
                    results = v
                    break

        # print(results)
        if results and isinstance(results, list):
            for res in results:
                try:
                    # JSON 回傳的 id (1~batch_size) 對應回 chunk 的 index (0~batch_size-1)
                    idx = int(res.get('id', 0)) - 1
                    if 0 <= idx < len(chunk):
                        target_comment = chunk[idx]
                        sentiment = res.get('sentiment')
                        score = res.get('score')
                        # print(f"對應成功: comment_id={target_comment['comment_id']}, sentiment={sentiment}, score={score}")
                        
                        if sentiment is not None:
                            updates.append((sentiment, score, target_comment['comment_id']))
                except Exception as e:
                    print(f"[{channel_name}] 解析回傳 JSON 結果時發生小錯誤: {e}")
                    
        # 寫回 MySQL (已加入 sentiment_score)
        if updates:
            try:
                with DBManager().connect_to_db() as conn:
                    with conn.cursor() as cursor:
                        sql = "UPDATE video_comments SET sentiment = %s, sentiment_score = %s WHERE comment_id = %s"
                        cursor.executemany(sql, updates)
                        conn.commit()
            except Exception as e:
                print(f"[{channel_name}] 寫入資料庫失敗: {e}")
                
        processed_count = min(chunk_idx + batch_size, len(comments))
        
        # if processed_count % 10000 == 0:
        if not last_time: last_time = start_time
        mid_time = datetime.now()
        print(f'[{channel_name}] {mid_time} - {processed_count} / {len(comments)} ({processed_count / len(comments) * 100:.4f}%) ({mid_time - last_time})')
        last_time = mid_time
        
    end_time = datetime.now()
    print(f'[{channel_name}] 開始時間: {start_time}')
    print(f'[{channel_name}] 結束時間: {end_time}')
    total_time = end_time - start_time
    print(f'[{channel_name}] 總共花費時間: {total_time}')
    print(f'[{channel_name}] 平均花費時間: {total_time / len(comments)}')

if __name__ == '__main__':
    count = None
    channels = [(Chienseating(), count), (HowHowEat(), count)]
    print('啟動多執行緒同時處理多個頻道...')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(channels)) as executor:
        futures = [executor.submit(process_channel, channel, limit) for channel, limit in channels]
        concurrent.futures.wait(futures)
        
    print('全部處理完成！')