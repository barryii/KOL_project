from mysql.connector import connect as mysql_connect
import os
from dotenv import load_dotenv

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