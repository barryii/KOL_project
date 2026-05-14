from database import DBManager
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
        topic_tag TEXT,
        published_at DATETIME,
        type VARCHAR(20),
        duration TIME,
        duration_sec INT,
        view_count BIGINT,
        like_count INT,
        comment_count INT,
        actual_comment_count INT,
        cluster_label INT,
        INDEX idx_channel_id (channel_id),
        INDEX idx_actual_comments (actual_comment_count),
        INDEX idx_v_type (`type`),
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
        sentiment_score INT,
        topic_tag VARCHAR(50),
        published_at DATETIME,
        INDEX idx_new_video_id (video_id),
        INDEX idx_new_channel_id (channel_id),
        INDEX idx_new_author_id (author_id),
        FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS topN_comments (
        channel_id VARCHAR(24),
        author_id VARCHAR(24),
        author_name VARCHAR(100),
        author_display_name TEXT,
        `type` VARCHAR(20),              -- 新增：影片類型 (video, shorts, stream)
        comment_count INT,               -- 該類型的總留言數量
        total_likes INT,                 -- 該類型獲得的總讚數
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 記錄更新時間
        PRIMARY KEY (channel_id, author_id, `type`)  -- 升級為三位一體的複合主鍵
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS topN_comments_seperate (
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
        INDEX idx_new_video_id (video_id),
        INDEX idx_new_channel_id (channel_id),
        INDEX idx_new_author_id (author_id),
        FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
    )
    """,
]
with DBManager().connect_to_db() as connection:
    with connection.cursor() as cursor:
        for query in table_queries:
            cursor.execute(query)
        connection.commit()

