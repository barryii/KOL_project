from youtuber_info import Chienseating, HowHowEat
from datetime import datetime
from database import DBManager

def transfer_topN_by_type():
    db = DBManager()
    channels = [Chienseating(), HowHowEat()]
    video_types = ['video', 'shorts', 'stream']
    N = 1100

    with db.connect_to_db_readonly() as connection:
        with connection.cursor() as cursor:
            start_time = datetime.now()
            type_start_time = None
            ch_start_time = None
            for v_type in video_types:
                if not type_start_time: type_start_time = start_time
                else: type_start_time = datetime.now()
                print(f'{type_start_time} --- 正在處理類型: {v_type} ---')
                for ch in channels:
                    if not ch_start_time: ch_start_time = type_start_time
                    else: ch_start_time = datetime.now()
                    print(f'{ch_start_time} --- 正在處理頻道: {ch.channel_name} - {v_type} ---')
                    # 1. 以「留言數量」排序的前 N 名
                    sql_by_comments = '''
                        SELECT 
                            vc.channel_id,
                            vc.author_id,
                            MAX(vc.author_name) AS author_name,
                            %s AS type,
                            COUNT(vc.comment_id) AS comment_count,
                            SUM(vc.like_count) AS total_likes
                        FROM video_comments vc
                        JOIN videos v ON vc.video_id = v.video_id
                        WHERE vc.channel_id = %s AND v.`type` = %s
                        GROUP BY vc.author_id
                        ORDER BY comment_count DESC
                        LIMIT %s
                    '''
                    cursor.execute(sql_by_comments, (v_type, ch.channel_id, v_type, N))
                    results = cursor.fetchall()
                    end_time = datetime.now()
                    if results:
                        db.save_topN_comment_batch(results)
                        print(f'{end_time} 頻道 {ch.channel_name} ({v_type}) - 已儲存依留言數排序的前 {len(results)} 名 花費 {end_time - ch_start_time}')

                    # 2. 以「獲得按讚數」排序的前 N 名 (加強命中權重最高的鐵粉)
                    sql_by_likes = '''
                        SELECT 
                            vc.channel_id,
                            vc.author_id,
                            MAX(vc.author_name) AS author_name,
                            %s AS type,
                            COUNT(vc.comment_id) AS comment_count,
                            CAST(SUM(vc.like_count) AS UNSIGNED) AS total_likes
                        FROM video_comments vc
                        JOIN videos v ON vc.video_id = v.video_id
                        WHERE vc.channel_id = %s AND v.`type` = %s
                        GROUP BY vc.author_id
                        ORDER BY total_likes DESC, comment_count DESC
                        LIMIT %s
                    '''
                    cursor.execute(sql_by_likes, (v_type, ch.channel_id, v_type, N))
                    results = cursor.fetchall()
                    end_time = datetime.now()
                    if results:
                        db.save_topN_comment_batch(results)
                        print(f'{end_time} 頻道 {ch.channel_name} ({v_type}) - 已儲存依獲讚數排序的前 {len(results)} 名 花費 {end_time - ch_start_time}')
                print(f'{end_time} 類型 {v_type} - 處理完成 花費 {end_time - type_start_time}')
    return end_time

if __name__ == '__main__':
    start_time = datetime.now()
    end_time = transfer_topN_by_type()
    print(f'--- 鐵粉數據分維度統計完成！總花費 {end_time - start_time} ---')
