from youtuber_info import Chienseating, HowHowEat
from database import DBManager

with DBManager().connect_to_db() as connection:
    with connection.cursor() as cursor:
        for channel in [Chienseating(), HowHowEat()]:
            N = 500
            # sql = """
            #     SELECT 
            #         t.author_name,       -- 作者名稱
            #         t.total_likes,       -- 總讚數 (從精華表拿)
            #         v.text_content,      -- 留言內容
            #         v.like_count,        -- 該留言本身的讚數
            #         v.sentiment,         -- 你的情緒分析
            #         v.sentiment_score    -- 情緒分數
            #     FROM (
            #         -- 第一步：先用極速的子查詢，從聚合表中過濾出前 N 名神人
            #         SELECT author_id, author_name, total_likes 
            #         FROM topN_comments 
            #         WHERE channel_id = %s
            #         ORDER BY total_likes DESC 
            #         -- LIMIT %s
            #     ) AS t
            #     -- 第二步：用這 30 個人去跟千萬筆純聊天庫 JOIN
            #     JOIN video_comments v 
            #         ON t.author_id = v.author_id 
            #     AND v.channel_id = %s
            #     -- WHERE v.sentiment is null
            #     ORDER BY t.total_likes DESC, v.like_count DESC  -- 依人氣跟單筆讚數排序
            # """
            sql = """
                SELECT 
                    vc.*
                FROM topN_comments AS topN
                JOIN video_comments vc ON topN.author_id = vc.author_id 
                AND vc.channel_id = %s
                ORDER BY topN.total_likes DESC, vc.like_count DESC  -- 依人氣跟單筆讚數排序
                limit %s
            """
            cursor.execute(sql, (channel.channel_id, N))
            results = cursor.fetchall()
            # print(results)
            print(len(results))
            DBManager().save_topN_comment_seperate_batch(results)

