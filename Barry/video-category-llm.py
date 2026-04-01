from concurrent.futures import ThreadPoolExecutor, as_completed
from youtuber_info import Chienseating, HowHowEat
from video_type import VideoType
from database import DBManager
from datetime import datetime
import os, dotenv
import ollama
import json

dotenv.load_dotenv()

def get_video_data(channel_id, limit=10):
    # 連線到資料庫
    db = DBManager().connect_to_db()
    cursor = db.cursor(dictionary=True)
    
    # cursor.execute('SELECT video_id, title FROM videos WHERE channel_id = %s and type = %s LIMIT %s', (channel_id, VideoType.VIDEO.value, limit))
    cursor.execute('SELECT video_id, title FROM videos WHERE channel_id = %s and type = %s', (channel_id, VideoType.VIDEO.value))
    videos = cursor.fetchall()
    db.close()
    
    return videos

def classify_batch(titles: list[str]) -> list[str]:
    numbered = '\n'.join([f'{i+1}. {t}' for i, t in enumerate(titles)])
    print(numbered)
    
    response = ollama.chat(
        model='gemma3',
        options={'think': False},
        messages=[{
            'role': 'user',
            'content': f'''分類以下 YouTube 標題，每個輸出最多 10 個標籤。
只輸出 JSON 陣列，格式如下：
[["標籤1","標籤2","標籤3","標籤4","標籤5"], ["標籤1",...], ...]

標題：
{numbered}'''
        }],
        format='json'
    )
    
    text = response['message']['content'].strip()
    text = text.replace('```json', '').replace('```', '').strip()
    print(text)
    return json.loads(text)

def extract_video_tags(channel_id, limit=20):
    ollama_model = 'llama4'
    output_file = f'./Barry/video_categories_{channel_id}_qwen2532b.json'
    output_file = f'./Barry/video_categories_{channel_id}_{ollama_model}.json'
    output_file = f'./Barry/video_categories_{channel_id}_all.json'
    
    # 確保 JSON 檔案存在且初始化為空陣列
    # 如果希望每次執行都清除舊資料，直接保留 open(..., 'w') 即可
    # if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
    #     with open(output_file, 'w', encoding='utf-8') as f:
    #         json.dump([], f)
    
    # 多批次處理
    # 每批 10 部影片
    BATCH_SIZE = 10
    videos = get_video_data(channel_id, limit)
    # titles = [video['title'] for video in videos]

    # results = []
    # for i in range(0, len(titles), BATCH_SIZE):
    #     batch = titles[i:i+BATCH_SIZE]
    #     batch_results = classify_batch(batch)
    #     results.extend(batch_results)
    #     print(f'進度：{min(i+BATCH_SIZE, len(titles))}/{len(titles)}')

    # # 多批次 + 多執行緒處理
    # BATCH_SIZE = 10
    # WORKERS = 2
    # videos = get_video_data(channel_id, limit)
    # batches = [videos[i:i+BATCH_SIZE] for i in range(0, len(videos), BATCH_SIZE)]
    # results = [None] * len(batches)
    # with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    #     futures = {
    #         executor.submit(classify_batch, batch, i): i 
    #         for i, batch in enumerate(batches)
    #     }
    #     completed = 0
    #     for future in as_completed(futures):
    #         batch_id, batch_result = future.result()
    #         results[batch_id] = batch_result
    #         completed += 1
    #         print(f'完成：{completed}/{len(batches)} 批')
            
    for count, video in enumerate(videos):
        # 在發送請求前，先讀取現有資料
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            current_data = []

        # 判斷如果影片已經在 json 裡就跳過這次的迴圈
        if any(item.get('video_id') == video['video_id'] for item in current_data):
            print(f'({count + 1} / {len(videos)}) 影片已存在 JSON 中，跳過處理: {video['video_id']} - {video['title']}')
            continue
        start_time = datetime.now()
        print(f'({count + 1} / {len(videos)}) {start_time} 開始處理: {video['video_id']} - {video['title']}')
        
        title = video['title']
#         response = ollama.chat(
#             model=ollama_model,
#             messages=[{
#                 'role': 'user',
#                 'content': f'''你是一個 YouTube 影片分類專家。
# 請投過以下影片標題判斷影片主題。

# 規則：
# 1. 只回答類別名稱，不要解釋
# 2. 如果無法判斷，回答「其他」
# 3. 不要是「美食」這種分類，我要像是食物的種類、地點這種細項，例如「日式料理」、「義式料理」、「咖哩飯」、「拉麵」、「雞肉」、「牛肉」、「火鍋」、「燒肉」、「吃到飽」、「北部」、「台中」、「家樂福」。
# 4. 最多 10 個
# 5. 回答格式為陣列，例如 [日式料理, 拉麵, CP值]

# 影片標題：{title}'''
#             }],
#             # options={'think': False},
#             format='json'
#         )
        
#         category = response['message']['content']
#         print(f'標題: {title}')
#         print(f'分類: {category}')
        
        result = {
            'video_id': video['video_id'],
            'title': title,
            'category': []
        }
        # 附加新資料並寫回檔案中
        current_data.append(result)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=4)
        end_time = datetime.now()
        print(f'{end_time} 處理完成: {video['video_id']} - {video['title']}')
        print(f'處理時間: {end_time - start_time}')
        print()
    # db.close()
#     print(f'處理完成！已將 {count} 筆結果逐筆寫入 {output_file}')

if __name__ == '__main__':
    extract_video_tags(Chienseating().channel_id)
    extract_video_tags(HowHowEat().channel_id)