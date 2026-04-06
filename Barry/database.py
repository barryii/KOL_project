from mysql.connector import connect as mysql_connect
from datetime import datetime
import os, dotenv

dotenv.load_dotenv()

class DBManager:
    def __init__(self):
        self.config = {
            'host': 'dv108.aiturn.fun',
            'user': 'barry',
            'password': os.getenv('KOL_DB_PW'),
            'database': 'db_kol'
        }
        self.config_backup = {
            'host': '136.113.125.99',
            'user': 'nick',
            'password': os.getenv('KOL_DB_PW_BACKUP'),
            'database': 'db_kol'
        }

    def connect_to_db(self):
        '''
            ### 寫入時不嘗試連線備用庫，防止寫入汙染備用庫
        '''
        try:
            return mysql_connect(**self.config)
        except Exception as e:
            print(f'主資料庫連線失敗 ({e})，無法寫入')
            raise

    def connect_to_db_readonly(self):
        try:
            return mysql_connect(**self.config)
        except Exception as e:
            print(f'主資料庫連線失敗 ({e})，正在嘗試切換至備用庫...')
            return mysql_connect(**self.config_backup)

    def save_channel_data(self, channel_id: str, channel_name: str, subscriber_count: int, view_count: int) -> None:
        """
        channel_id VARCHAR(24) PRIMARY KEY,
        channel_name VARCHAR(100) NOT NULL,
        subscriber_count BIGINT,
        total_view_count BIGINT,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        """
        with self.connect_to_db() as connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO channels (channel_id, channel_name, subscriber_count, total_view_count) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (channel_id, channel_name, subscriber_count, view_count))
                connection.commit()

    def save_video_batch(self, video_data: list[tuple[str, str, str, str, datetime, str, str, int, int, int, int]]) -> None:
        """
        video_data = [
            (video_id, channel_id, title, description, published_at, type, duration, duration_sec, view_count, like_count, comment_count),
            ...
        ]
        video_id VARCHAR(11) PRIMARY KEY,
        channel_id VARCHAR(24),
        title VARCHAR(255),
        description TEXT,
        topic_tag TEXT, # 不從這存
        published_at DATETIME,
        type VARCHAR(20),
        duration TIME,
        duration_sec INT,
        view_count BIGINT,
        like_count INT,
        comment_count INT,
        actual_comment_count INT, # 不從這存
        cluster_label INT, # 不從這存
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
        """
        with self.connect_to_db() as connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO videos (
                    video_id, 
                    channel_id, 
                    title, 
                    description, 
                    published_at, 
                    `type`, 
                    duration, 
                    duration_sec, 
                    view_count, 
                    like_count, 
                    comment_count
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE 
                    view_count = VALUES(view_count),
                    like_count = VALUES(like_count),
                    comment_count = VALUES(comment_count)
                """
                cursor.executemany(sql, video_data)
                connection.commit()

    def save_video_batch_cluster(self, video_data: list[tuple[str, int]]) -> None:
        """
        video_data = [
            (video_id, cluster_label),
            ...
        ]
        video_id VARCHAR(11) PRIMARY KEY,
        cluster_label INT
        """
        with self.connect_to_db() as connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO videos (
                    video_id, 
                    cluster_label
                ) VALUES (
                    %s, %s
                ) ON DUPLICATE KEY UPDATE
                    cluster_label = VALUES(cluster_label)
                """
                cursor.executemany(sql, video_data)
                connection.commit()

    def save_comment_batch(self, comment_data: list[tuple[str, str, str, str, int, int, datetime]]) -> None:
        """
        comment_data = [
            (comment_id, video_id, channel_id, author_id, author_name, text_content, like_count, reply_count, published_at),
            ...
        ]
        comment_id VARCHAR(50) PRIMARY KEY,
        video_id VARCHAR(11),
        channel_id VARCHAR(24),
        author_id VARCHAR(24),
        author_name VARCHAR(100),
        text_content TEXT,
        like_count INT,
        reply_count INT,
        sentiment VARCHAR(20), # 留給AI填
        sentiment_score INT, # 留給AI填
        topic_tag VARCHAR(50), # 留給AI填
        published_at DATETIME,
        FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
        """
        with self.connect_to_db() as connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO video_comments (
                    comment_id, 
                    video_id, 
                    channel_id, 
                    author_id, 
                    author_name, 
                    text_content, 
                    like_count, 
                    reply_count, 
                    published_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE 
                    author_id = VALUES(author_id),
                    like_count = VALUES(like_count),
                    reply_count = VALUES(reply_count)
                """
                cursor.executemany(sql, comment_data)
                connection.commit()

    def save_topN_comment_batch(self, topN_comment_data: list[tuple[str, str, str, str, int, int]]) -> None:
        """
        topN_comment_data = [
            (channel_id, author_id, author_name, type, comment_count, total_likes),
            ...
        ]
        channel_id VARCHAR(24),
        author_id VARCHAR(24),
        author_name VARCHAR(100),
        author_display_name TEXT,        -- 不在這裡更新
        type VARCHAR(20),                -- 新增影片類型欄位
        comment_count INT,               -- 總留言數量
        total_likes INT,                 -- 獲得的總讚數
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 記錄更新時間
        PRIMARY KEY (channel_id, author_id, type)  -- 複合主鍵更新！
        """
        with self.connect_to_db() as connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO topN_comments (
                    channel_id, 
                    author_id, 
                    author_name, 
                    `type`,
                    comment_count, 
                    total_likes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    comment_count = VALUES(comment_count),
                    total_likes = VALUES(total_likes)
                """
                cursor.executemany(sql, topN_comment_data)
                connection.commit()

    def save_topN_comment_seperate_batch(self, topN_comment_data: list[tuple[str, str, str, str, int, int, datetime]]) -> None:
        """
        topN_comment_data = [
            (comment_id, video_id, channel_id, author_id, author_name, text_content, like_count, reply_count, published_at),
            ...
        ]
        comment_id VARCHAR(50) PRIMARY KEY,
        video_id VARCHAR(11),
        channel_id VARCHAR(24),
        author_id VARCHAR(24),
        author_name VARCHAR(100),
        text_content TEXT,
        like_count INT,
        reply_count INT,
        sentiment VARCHAR(20),
        sentiment_score INT,
        topic_tag VARCHAR(50),
        published_at DATETIME,
        FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
        """
        with self.connect_to_db() as connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO topN_comments_seperate (
                    comment_id, 
                    video_id, 
                    channel_id, 
                    author_id, 
                    author_name, 
                    text_content, 
                    like_count, 
                    reply_count, 
                    sentiment, 
                    sentiment_score, 
                    topic_tag, 
                    published_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    like_count = VALUES(like_count),
                    reply_count = VALUES(reply_count),
                    sentiment = VALUES(sentiment),
                    sentiment_score = VALUES(sentiment_score),
                    topic_tag = VALUES(topic_tag),
                    published_at = VALUES(published_at)
                """
                cursor.executemany(sql, topN_comment_data)
                connection.commit()

    def save_kol_data(self, kol_name: str, followers: int, engagement_rate: float) -> None:
        """存入 KOL 成效資料"""
        with self.connect_to_db() as connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO kol_stats (name, followers, engagement) VALUES (%s, %s, %s)"
                cursor.execute(sql, (kol_name, followers, engagement_rate))
                connection.commit()

    def get_db_videos(self, channel_id: str = None):
        """讀取所有影片清單"""
        with self.connect_to_db_readonly() as connection:
            with connection.cursor() as cursor:
                if channel_id:
                    sql = "SELECT * FROM videos WHERE channel_id = %s"
                    cursor.execute(sql, (channel_id,))
                else:
                    sql = "SELECT * FROM videos"
                    cursor.execute(sql)
                return cursor.fetchall()

    def get_db_video_comments(self, channel_id: str = None):
        """讀取所有影片清單"""
        with self.connect_to_db_readonly() as connection:
            with connection.cursor() as cursor:
                if channel_id:
                    sql = "SELECT * FROM video_comments WHERE channel_id = %s"
                    cursor.execute(sql, (channel_id,))
                else:
                    sql = "SELECT * FROM video_comments"
                    cursor.execute(sql)
                return cursor.fetchall()

    def get_all_kol(self):
        """讀取所有 KOL 清單"""
        with self.connect_to_db_readonly() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM kol_stats"
                cursor.execute(sql)
                return cursor.fetchall()

    def get_videos_by_channel_id(self, channel_id: str, data: str='*') -> list[tuple[str]]:
        """
        讀取所有影片清單
        data: 欲查詢的欄位，預設為*（所有欄位）
        範例: data='video_id, title, view_count'
        """
        with self.connect_to_db_readonly() as connection:
            with connection.cursor() as cursor:
                sql = f"SELECT {data} FROM videos where channel_id = %s"
                cursor.execute(sql, (channel_id,))
                return cursor.fetchall()

