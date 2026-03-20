from mysql.connector import connect as mysql_connect
from youtuber_info import Chienseating, HowHowEat
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

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
                    
                #     print(f"已更新 {cursor.rowcount} 筆...")
                    
                #     # 如果受影響的行數為 0，代表全部更新完了
                #     if cursor.rowcount == 0:
                #         break
                sql = """
                INSERT INTO video_comments_new 
                    (comment_id, video_id, channel_id, author_name, text_content, like_count, published_at)
                SELECT 
                    vc.comment_id, 
                    vc.video_id, 
                    v.channel_id, -- 從影片表拿
                    vc.author_name, 
                    vc.text_content, 
                    vc.like_count, 
                    vc.published_at
                FROM video_comments vc
                JOIN videos v ON vc.video_id = v.video_id;
                """
                cursor.execute(sql)
                connection.commit()
                
                # print(f"已更新 {cursor.rowcount} 筆...")

if __name__ == '__main__':
	# DBOps().get_video_stats()
	# DBOps().get_comment_stats(Chienseating().channel_id)
	# DBOps().get_comment_stats(HowHowEat().channel_id)
	DBOps().update_vc_channel_id()









