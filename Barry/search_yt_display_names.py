from googleapiclient.discovery import build
from database import DBManager
import os, dotenv

dotenv.load_dotenv()

YT_API_KEY = os.getenv('YT_API_KEY')
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

def fetch_display_names(author_ids: list[str]) -> dict[str, str]:
    """
    批次呼叫 YouTube Channels API，每次最多 50 個 channel ID。
    回傳 { author_id: display_name } 的對照表。
    """
    result = {}
    # 每批最多 50 個 (YouTube API 上限)
    batch_size = 50
    for i in range(0, len(author_ids), batch_size):
        batch = author_ids[i:i + batch_size]
        ids_str = ','.join(batch)
        
        request = youtube.channels().list(
            part='snippet',
            id=ids_str,
            maxResults=batch_size
        )
        response = request.execute()
        
        for item in response.get('items', []):
            channel_id = item['id']
            title = item['snippet']['title']
            result[channel_id] = title
        print(f'  ✅ 已查詢第 {i+1}~{i+len(batch)} 筆，成功取得 {len(response.get("items", []))} 筆名稱')
    return result

def main():
    # Step 1: 從 topN_comments 撈出所有不重複的 author_id
    print('📦 Step 1: 從 topN_comments 撈取不重複的 author_id...')
    with DBManager().connect_to_db_readonly() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('''
                SELECT DISTINCT author_id 
                FROM topN_comments 
                WHERE author_display_name IS NULL OR author_display_name = ''
            ''')
            rows = cursor.fetchall()
    
    author_ids = [row['author_id'] for row in rows if row['author_id']]
    print(f'   共有 {len(author_ids)} 個待查詢的 author_id')
    
    if not author_ids:
        print('🎉 全部都已經有 display_name 了，無需更新！')
        return
    
    # Step 2: 透過 YouTube API 批次查詢
    print(f'🌐 Step 2: 呼叫 YouTube Channels API 批次查詢 (每批 50 個，共需 {len(author_ids) // 50 + 1} 批)...')
    name_map = fetch_display_names(author_ids)
    print(f'   成功取得 {len(name_map)} 筆頻道名稱')
    
    # Step 3: 寫回資料庫
    print('💾 Step 3: 將 display_name 寫回 topN_comments.author_display_name...')
    updated = 0
    with DBManager().connect_to_db() as conn:
        with conn.cursor() as cursor:
            for author_id, display_name in name_map.items():
                cursor.execute(
                    'UPDATE topN_comments SET author_display_name = %s WHERE author_id = %s',
                    (display_name, author_id)
                )
                updated += cursor.rowcount
            conn.commit()
    
    not_found = len(author_ids) - len(name_map)
    print(f'\n🎉 完成！共更新 {updated} 筆紀錄。')
    if not_found > 0:
        print(f'⚠️  有 {not_found} 個 author_id 在 YouTube 上查無結果（可能已刪除帳號）')


if __name__ == '__main__':
    main()
