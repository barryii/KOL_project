from mysql.connector import connect as mysql_connect
import os
import dotenv

dotenv.load_dotenv()
table_queries = [
    """
    CREATE TABLE IF NOT EXISTS channels (
        channel_id VARCHAR(24) PRIMARY KEY,
        channel_name VARCHAR(100) NOT NULL,
        subscriber_count BIGINT,
        total_view_count BIGINT,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS videos (
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
        actual_comment_count INT,
        cluster_label INT,
        INDEX idx_actual_comments ON videos(actual_comment_count),
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS video_comments (
        comment_id VARCHAR(50) PRIMARY KEY,
        video_id VARCHAR(11),
        channel_id VARCHAR(24),
        author_id VARCHAR(24),
        author_name VARCHAR(100),
        text_content TEXT,
        like_count INT,
        reply_count INT,
        sentiment VARCHAR(20),
        topic_tag VARCHAR(50),
        published_at DATETIME,
        INDEX idx_new_video_id (video_id),
        INDEX idx_new_channel_id (channel_id),
        INDEX idx_new_author_id (author_id),
        FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
    )
    """
]
config = {
    'host': 'dv108.aiturn.fun',
    'user': 'barry',
    'password': os.getenv('KOL_DB_PW'),
    'database': 'db_kol'
}
with mysql_connect(**config) as connection:
    with connection.cursor() as cursor:
        for query in table_queries:
            cursor.execute(query)
        connection.commit()

