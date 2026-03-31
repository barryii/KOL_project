from youtuber_info import Chienseating, HowHowEat
from database import DBManager

with DBManager().connect_to_db() as conn:
    with conn.cursor(dictionary=True) as cursor:
        sql = """
            SELECT 
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

        cursor.execute(sql, (Chienseating().channel_id, 10))
        results = cursor.fetchall()

        print(results)

