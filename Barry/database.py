from mysql.connector import connect as mysql_connect
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

class DBManager:
    def __init__(self):
        self.config = {
            'host': 'dv108.aiturn.fun',
            'user': 'barry',
            'password': os.getenv('KOL_DB_PW'),
            'database': 'db_kol'
        }

    def save_channel_data(self, channel_id: str, channel_name: str, subscriber_count: int, view_count: int) -> None:
        """
        channel_id VARCHAR(24) PRIMARY KEY,
        channel_name VARCHAR(100) NOT NULL,
        subscriber_count BIGINT,
        total_view_count BIGINT,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        """
        with mysql_connect(**self.config) as connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO channels (channel_id, channel_name, subscriber_count, total_view_count) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (channel_id, channel_name, subscriber_count, view_count))
                connection.commit()

    def save_video_data(
        self, 
        video_id: str, 
        channel_id: str, 
        title: str, 
        description: str, 
        published_at: datetime, 
        type: str, 
        duration: str, 
        duration_sec: int, 
        view_count: int, 
        like_count: int, 
        comment_count: int
    ) -> None:
        """
        video_id VARCHAR(11) PRIMARY KEY,
        channel_id VARCHAR(24),
        title VARCHAR(255),
        description TEXT,
        published_at DATETIME,
        type VARCHAR(20),
        duration TIME,
        duration_sec INT,
        view_count BIGINT,
        like_count INT,
        comment_count INT,
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
        """
        with mysql_connect(**self.config) as connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT IGNORE INTO videos (
                    video_id, 
                    channel_id, 
                    title, 
                    description, 
                    published_at, 
                    type, 
                    duration, 
                    duration_sec, 
                    view_count, 
                    like_count, 
                    comment_count
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """
                cursor.execute(sql, (video_id, channel_id, title, description, published_at, type, duration, duration_sec, view_count, like_count, comment_count))
                connection.commit()

    def save_kol_data(self, kol_name: str, followers: int, engagement_rate: float) -> None:
        """存入 KOL 成效資料"""
        with mysql_connect(**self.config) as connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO kol_stats (name, followers, engagement) VALUES (%s, %s, %s)"
                cursor.execute(sql, (kol_name, followers, engagement_rate))
                connection.commit()

    def get_all_kol(self):
        """讀取所有 KOL 清單"""
        # ... 連線並 fetchall 的邏輯 ...
        pass