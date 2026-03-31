from youtuber_info import Chienseating, HowHowEat
from database import DBManager

with DBManager().connect_to_db() as conn:
    with conn.cursor() as cursor:
        for channel in [Chienseating(), HowHowEat()]:
            N = 20
            sql = """
                SELECT 
                    t.author_name,       -- 作者名稱
                    t.total_likes,       -- 總讚數 (從精華表拿)
                    v.text_content,      -- 留言內容
                    v.like_count,        -- 該留言本身的讚數
                    v.sentiment,         -- 你的情緒分析
                    v.sentiment_score    -- 情緒分數
                FROM (
                    -- 第一步：先用極速的子查詢，從聚合表中過濾出前 N 名神人
                    SELECT author_id, author_name, total_likes 
                    FROM topN_comments 
                    WHERE channel_id = %s
                    ORDER BY total_likes DESC 
                    LIMIT %s
                ) AS t
                -- 第二步：用這 30 個人去跟千萬筆純聊天庫 JOIN
                JOIN video_comments v 
                    ON t.author_id = v.author_id 
                AND v.channel_id = %s
                WHERE v.sentiment is null
                ORDER BY t.total_likes DESC, v.like_count DESC  -- 依人氣跟單筆讚數排序
            """
            cursor.execute(sql, (channel.channel_id, N, channel.channel_id))
            results = cursor.fetchall()
            # print(results)
            print(len(results))


