from youtuber_info import Chienseating, HowHowEat
from database import DBManager

with DBManager().connect_to_db() as connection:
    with connection.cursor() as cursor:
        N = 1100
        # 單純以留言數排序的前N名
        sql = """
            SELECT 
                channel_id,
                author_id,
                MAX(author_name) AS author_name,
                COUNT(comment_id) AS comment_count,
                SUM(like_count) AS total_likes
            FROM video_comments
            WHERE channel_id = %s
            GROUP BY author_id
            ORDER BY comment_count DESC
            LIMIT %s
        """
        cursor.execute(sql, (Chienseating().channel_id, N))
        results = cursor.fetchall()
        # print(results)
        DBManager().save_topN_comment_batch(results)
        cursor.execute(sql, (HowHowEat().channel_id, N))
        results = cursor.fetchall()
        # print(results)
        DBManager().save_topN_comment_batch(results)
        
        # 以總獲得的按讚數排序的前N名
        sql = """
            SELECT 
                channel_id,
                author_id,
                MAX(author_name) AS author_name,
                COUNT(comment_id) AS comment_count,
                CAST(SUM(like_count) AS UNSIGNED) AS total_likes
            FROM video_comments
            WHERE channel_id = %s
            GROUP BY author_id
            ORDER BY total_likes DESC, comment_count DESC
            LIMIT %s
        """
        cursor.execute(sql, (Chienseating().channel_id, N))
        results = cursor.fetchall()
        # print(results)
        DBManager().save_topN_comment_batch(results)
        cursor.execute(sql, (HowHowEat().channel_id, N))
        results = cursor.fetchall()
        # print(results)
        DBManager().save_topN_comment_batch(results)

