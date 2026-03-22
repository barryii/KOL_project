from mysql.connector import connect as mysql_connect
from youtuber_info import Chienseating, HowHowEat
from googleapiclient.discovery import build
from datetime import datetime
from decimal import Decimal
import os, dotenv, json, csv

dotenv.load_dotenv()

YT_API_KEY = os.getenv('YT_API_KEY')
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) # 將 Decimal 轉為 float
        return super(DecimalEncoder, self).default(obj)

class DBOps:
    def __init__(self):
        self.config = {
            'host': 'dv108.aiturn.fun',
            'user': 'barry',
            'password': os.getenv('KOL_DB_PW'),
            'database': 'db_kol'
        }

    def get_video_stats(self, video_type: str='video'):
        with mysql_connect(**self.config) as connection:
            with connection.cursor() as cursor:
                sql = """
                SELECT 
                    c.channel_id, 
                    v.`type`,
                    COUNT(*) as video_count,
                    AVG(v.view_count) as avg_views,
                    AVG(v.like_count / v.view_count) * 100 as avg_like_rate
                FROM channels c
                JOIN videos v ON c.channel_id = v.channel_id
                WHERE v.`type` = %s -- 'video' | 'shorts' | 'stream'
                AND v.view_count > 0
                GROUP BY c.channel_id;
                """
                cursor.execute(sql, (video_type,))
                result = cursor.fetchall()
                for name, type, video_count, avg_views, avg_like_rate in result:
                    print(f'頻道: {name}')
                    print(f'影片類別: {type}')
                    print(f'影片數量: {video_count}')
                    print(f'平均觀看次數: {avg_views:,}')
                    print(f'平均觀看次數: {avg_views:,.0f}')
                    print(f'平均按讚率: {avg_like_rate}%')
                    print(f'平均按讚率: {avg_like_rate:.2f}%')
                    print(f'=' * 20)

    def get_comment_stats(self, channel_id: Chienseating | HowHowEat):
        with mysql_connect(**self.config) as connection:
            with connection.cursor() as cursor:
                sql = """
                SELECT 
                    c.channel_id, 
                    v.title AS video_title, 
                    vc.author_name, 
                    vc.text_content, 
                    vc.like_count
                FROM video_comments vc
                JOIN videos v ON vc.video_id = v.video_id
                JOIN channels c ON v.channel_id = c.channel_id
                WHERE c.channel_id = %s
                ORDER BY vc.like_count DESC -- 按讚數最高排前面
                LIMIT 20;
                """
                cursor.execute(sql, (channel_id,))
                result = cursor.fetchall()
                print(result)
                import pprint
                pprint.pprint(result)
                # for name, type, video_count, avg_views, avg_like_rate in result:
                #     print(f'頻道: {name}')
                #     print(f'影片類別: {type}')
                #     print(f'影片數量: {video_count}')
                #     print(f'平均觀看次數: {avg_views:,}')
                #     print(f'平均觀看次數: {avg_views:,.0f}')
                #     print(f'平均按讚率: {avg_like_rate}%')
                #     print(f'平均按讚率: {avg_like_rate:.2f}%')
                #     print(f'=' * 20)

    def update_vc_channel_id(self):
        with mysql_connect(**self.config) as connection:
            with connection.cursor() as cursor:
                # while True:
                #     batch_size = 5000
                #     # 每次只更新 5000 筆 channel_id 還沒填好的資料
                #     sql = f"""
                #         UPDATE video_comments vc
                #         JOIN videos v ON vc.video_id = v.video_id
                #         SET vc.channel_id = v.channel_id
                #         WHERE vc.channel_id IS NULL
                #         LIMIT {batch_size};
                #     """
                #     sql = """
                #         -- 2. 為留言表的 video_id 建立索引 (這是最關鍵的一步)
                #         ALTER TABLE video_comments ADD INDEX idx_vc_video_id (video_id);
                #         -- 3. 為留言表的新欄位 channel_id 也建立索引 (方便以後分析)
                #         ALTER TABLE video_comments ADD INDEX idx_vc_channel_id (channel_id);
                #     """
                #     cursor.execute(sql)
                #     connection.commit()
                    
                #     print(f'已更新 {cursor.rowcount} 筆...')
                    
                #     # 如果受影響的行數為 0，代表全部更新完了
                #     if cursor.rowcount == 0:
                #         break
                limit = 5000
                offset = 0
                sql = """
                    SELECT 
                        c.channel_name,
                        v_stats.official_total AS 'API 官方留言總數',
                        vc_stats.captured_total AS '資料庫實收留言數',
                        (v_stats.official_total - vc_stats.captured_total) AS '差異數',
                        ROUND((vc_stats.captured_total / v_stats.official_total) * 100, 2) AS '抓取率%'
                    FROM channels c
                    -- 第一部分：從 videos 表加總官方紀錄的數字
                    JOIN (
                        SELECT channel_id, SUM(comment_count) AS official_total
                        FROM videos
                        GROUP BY channel_id
                    ) v_stats ON c.channel_id = v_stats.channel_id
                    -- 第二部分：從 video_comments 表計算實際存入的列數
                    JOIN (
                        SELECT channel_id, COUNT(*) AS captured_total
                        FROM video_comments
                        GROUP BY channel_id
                    ) vc_stats ON c.channel_id = vc_stats.channel_id;
                """
                cursor.execute(sql)
                result = cursor.fetchall()
                print(result)
                for name, official_total, captured_total, diff, like_rate in result:
                    print(f'頻道: {name}')
                    print(f'API 官方留言總數: {official_total}')
                    print(f'資料庫實收留言數: {captured_total}')
                    print(f'差異數: {diff}')
                    print(f'抓取率: {like_rate}%')
                    print(f'=' * 20)
                # connection.commit()
                # sql = """
                # SELECT COUNT(*) 
                # FROM video_comments vc
                # JOIN videos v ON vc.video_id = v.video_id;
                # """
                # cursor.execute(sql)
                # result = cursor.fetchall()
                # print(result)
                # connection.commit()
                
                # print(f'已更新 {cursor.rowcount} 筆...')

    def export_channel_comment_gap(self, channel_id):
        with mysql_connect(**self.config) as connection:
            with connection.cursor(dictionary=True) as cursor:
                # 先獲取頻道名稱 (確保 json 裡有名字)
                cursor.execute('SELECT channel_name FROM channels WHERE channel_id = %s', (channel_id,))
                channel_info = cursor.fetchone()

                if not channel_info:
                    print(f'❌ 找不到頻道 ID: {channel_id}，請確認資料庫是否有此頻道。')
                    return

                channel_name = channel_info['channel_name']

                # 執行影片等級的留言差異查詢
                # 使用 channel_id 過濾（效能最佳）
                sql = """
                    SELECT 
                        v.video_id,
                        v.title,
                        v.comment_count AS official_count,
                        COUNT(vc.comment_id) AS captured_count,
                        (v.comment_count - COUNT(vc.comment_id)) AS gap,
                        ROUND((COUNT(vc.comment_id) / NULLIF(v.comment_count, 0)) * 100, 2) AS capture_rate_pct
                    FROM videos v
                    LEFT JOIN video_comments vc ON v.video_id = vc.video_id
                    WHERE v.channel_id = %s
                    GROUP BY v.video_id
                    ORDER BY gap DESC;
                """
                cursor.execute(sql, (channel_id,))
                results = cursor.fetchall()
                for row in results:
                    print(row)
                    break

                # json
                report = {
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'report_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'summary': {
                        'total_videos_checked': len(results),
                        'total_official_comments': sum(row['official_count'] for row in results),
                        'total_captured_comments': sum(row['captured_count'] for row in results)
                    },
                    'details': results
                }
                json_file = f'./Barry/gap_report_{channel_name}.json'
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=4, cls=DecimalEncoder)

                # csv
                csv_file = f'./Barry/gap_report_{channel_name}.csv'
                fieldnames = ['video_id', 'title', 'official_count', 'captured_count', 'gap', 'capture_rate_pct']
                
                with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(results)

                print(f'✅ 成功導出 {channel_name} 的資料：')
                print(f'   - JSON: {json_file}')
                print(f'   - CSV: {csv_file}')

    def update_actual_comment_count(self):
        with mysql_connect(**self.config) as connection:
            with connection.cursor(dictionary=True) as cursor:
                sql = """
                    UPDATE videos v
                    SET v.actual_comment_count = (
                        SELECT COUNT(*) 
                        FROM video_comments vc 
                        WHERE vc.video_id = v.video_id
                    );
                """
                cursor.execute(sql)
                connection.commit()

    def get_topic_from_yt(self, channel_id):
        with mysql_connect(**self.config) as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT channel_name FROM channels WHERE channel_id = %s', (channel_id,))
                channel_info = cursor.fetchone()
                if not channel_info:
                    print(f'❌ 找不到頻道 ID: {channel_id}，請確認資料庫是否有此頻道。')
                    return
                channel_name = channel_info['channel_name']
                sql = """
                    select * from videos
                    where type = 'video' and channel_id = %s
                """
                cursor.execute(sql, (channel_id,))
                result = cursor.fetchall()
                # print(result)
                # connection.commit()
                # 準備取得分類資訊並導出為 JSON 與 CSV
                part = 'topicDetails'
                results_data = []

                # 一次最多傳入 50 個 IDs
                batch_size = 50
                for i in range(0, len(result), batch_size):
                    batch = result[i:i + batch_size]
                    video_ids = [row['video_id'] for row in batch]
                    video_id_str = ','.join(video_ids)
                    
                    request = youtube.videos().list(
                        part=part,
                        id=video_id_str
                    )
                    response = request.execute()
                    playlist = response.get('items', [])
                    
                    for item in playlist:
                        v_id = item['id']
                        # 從原本的查詢結果中尋找對應的標題等資訊
                        v_info = next((r for r in batch if r['video_id'] == v_id), {})
                        title = v_info.get('title', '')
                        
                        topic_details = item.get('topicDetails', {})
                        topic_categories = topic_details.get('topicCategories', [])
                        
                        results_data.append({
                            'video_id': v_id,
                            'title': title,
                            'topic_categories': topic_categories
                        })

                # --- 產生 JSON 報表 ---
                report = {
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'report_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'summary': {
                        'total_videos_checked': len(results_data),
                    },
                    'details': results_data
                }
                
                json_file = f'./Barry/topic_report_{channel_name}.json'
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=4, cls=DecimalEncoder)

                # --- 產生 CSV 報表 ---
                csv_file = f'./Barry/topic_report_{channel_name}.csv'
                fieldnames = ['video_id', 'title', 'topic_categories']
                
                with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in results_data:
                        row_to_write = {
                            'video_id': r['video_id'],
                            'title': r['title'],
                            # 將陣列轉為以逗號與換行分隔的字串，方便 CSV 閱讀
                            'topic_categories': ',\n'.join(r['topic_categories'])
                        }
                        writer.writerow(row_to_write)

                print(f'✅ 成功導出 {channel_name} 的分類資料：')
                print(f'   - JSON: {json_file}')
                print(f'   - CSV: {csv_file}')

    def tmp(self, channel_id):
        with mysql_connect(**self.config) as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT channel_name FROM channels WHERE channel_id = %s', (channel_id,))
                channel_info = cursor.fetchone()
                if not channel_info:
                    print(f'❌ 找不到頻道 ID: {channel_id}，請確認資料庫是否有此頻道。')
                    return
                channel_name = channel_info['channel_name']
                sql = """
                    select * from videos
                    where channel_id = %s
                """
                cursor.execute(sql, (channel_id,))
                result = cursor.fetchall()
                # print(result)
                # connection.commit()
                fieldnames = ['video_id', 'title', 'description', 'published_at', 'type', 'duration', 'duration_sec', 'view_count', 'like_count', 'comment_count']
                with open(f'./Barry/{channel_name}.csv', 'w', newline='', encoding='utf-8-sig') as f:
                	# 定義欄位名稱
                	writer = csv.DictWriter(f, fieldnames=fieldnames)

                	# 寫入標題列
                	writer.writeheader()
                	# 寫入內容
                	for info in result:
                		# 建立一個基礎的 row
                		row = {
                			'video_id': info['video_id'],
                			'title': info['title'],
                			'description': info['description'],
                			'published_at': info['published_at'],
                			'duration': info['duration'],
                			'duration_sec': info['duration_sec'],
                			'type': info['type'],
                			'view_count': info['view_count'],
                			'like_count': info['like_count'],
                			'comment_count': info['comment_count'],
                		}
                		writer.writerow(row)


if __name__ == '__main__':
	# DBOps().get_video_stats()
	# DBOps().get_comment_stats(Chienseating().channel_id)
	# DBOps().get_comment_stats(HowHowEat().channel_id)
	# DBOps().update_vc_channel_id()
    # DBOps().export_channel_comment_gap(Chienseating().channel_id)
    # DBOps().export_channel_comment_gap(HowHowEat().channel_id)
    # DBOps().update_actual_comment_count()
    # DBOps().get_topic_from_yt(Chienseating().channel_id)
    # DBOps().get_topic_from_yt(HowHowEat().channel_id)
    DBOps().tmp(Chienseating().channel_id)
    DBOps().tmp(HowHowEat().channel_id)









