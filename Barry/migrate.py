"""
資料庫遷移腳本
從舊資料庫 (dv108.aiturn.fun) 遷移全部資料到新資料庫

使用前請在 .env 補上新資料庫的設定：
    NEW_DB_HOST=你的新主機
    NEW_DB_USER=你的新帳號
    NEW_DB_PW=你的新密碼
    NEW_DB_NAME=你的新資料庫名稱
"""

import os
import dotenv
from mysql.connector import connect as mysql_connect

dotenv.load_dotenv()

# ── 舊資料庫 ──────────────────────────────────────────
OLD_CONFIG = {
    'host': 'dv108.aiturn.fun',
    'user': 'barry',
    'password': os.getenv('KOL_DB_PW'),
    'database': 'db_kol',
}

# ── 新資料庫 ──────────────────────────────────────────
NEW_CONFIG = {
    'host': os.getenv('NEW_DB_HOST'),
    'port': int(os.getenv('NEW_DB_PORT', 3306)),
    'user': os.getenv('NEW_DB_USER'),
    'password': os.getenv('NEW_DB_PW'),
    'database': os.getenv('NEW_DB_NAME'),
}

# ── 建立資料表的 SQL ──────────────────────────────────
CREATE_TABLES = [
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
        `type` VARCHAR(20),
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
        `type` VARCHAR(20),
        comment_count INT,
        total_likes INT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (channel_id, author_id, `type`)
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
        `type` VARCHAR(20),
        published_at DATETIME,
        INDEX idx_new_video_id (video_id),
        INDEX idx_new_channel_id (channel_id),
        INDEX idx_new_author_id (author_id),
        FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
    )
    """,
]

def check_env():
    missing = [k for k, v in NEW_CONFIG.items() if not v]
    if missing:
        print('FAIL: .env 缺少新資料庫設定:', missing)
        raise SystemExit(1)


def connect_new_db():
    base_config = {k: v for k, v in NEW_CONFIG.items() if k != 'database'}
    return mysql_connect(**{**base_config, 'autocommit': False})


def create_database(conn):
    db_name = NEW_CONFIG['database']
    print('── 建立資料庫 ──')
    with conn.cursor() as cur:
        cur.execute(
            f'CREATE DATABASE IF NOT EXISTS `{db_name}` '
            f'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
        )
        cur.execute(f'USE `{db_name}`')
    print(f'OK: 資料庫 `{db_name}` 就緒')


def create_tables(conn):
    print('── 建立資料表 ──')
    with conn.cursor() as cur:
        # topN_comments_seperate 先 DROP 再建，確保欄位定義正確
        cur.execute('SET FOREIGN_KEY_CHECKS=0')
        cur.execute('DROP TABLE IF EXISTS `topN_comments_seperate`')
        cur.execute('SET FOREIGN_KEY_CHECKS=1')
        for sql in CREATE_TABLES:
            cur.execute(sql)
        conn.commit()
    print('OK: 所有資料表建立完成')


def migrate_table(table: str, old_conn, new_conn):
    BATCH_SIZE = 500
    with old_conn.cursor() as old_cur:
        old_cur.execute(f'SELECT COUNT(*) FROM `{table}`')
        total = old_cur.fetchone()[0]
        if total == 0:
            print(f'  {table}: 無資料，略過')
            return
        old_cur.execute(f'SELECT * FROM `{table}`')
        cols = [d[0] for d in old_cur.description]
        placeholders = ', '.join(['%s'] * len(cols))
        col_names = ', '.join(f'`{c}`' for c in cols)
        insert_sql = f'INSERT IGNORE INTO `{table}` ({col_names}) VALUES ({placeholders})'
        inserted = 0
        while True:
            rows = old_cur.fetchmany(BATCH_SIZE)
            if not rows:
                break
            with new_conn.cursor() as new_cur:
                new_cur.executemany(insert_sql, rows)
                new_conn.commit()
            inserted += len(rows)
            print(f'  {table}: {inserted}/{total}', end='\r')
        print(f'  {table}: {inserted}/{total} 筆完成    ')


TABLES = ['channels', 'videos', 'video_comments', 'topN_comments', 'topN_comments_seperate']


def main():
    check_env()

    print('連線舊資料庫...')
    old_conn = mysql_connect(**OLD_CONFIG)
    print('連線新資料庫...')
    new_conn = connect_new_db()
    try:
        create_database(new_conn)
        create_tables(new_conn)
        print('── 開始遷移資料 ──')
        for table in TABLES:
            migrate_table(table, old_conn, new_conn)
        print('OK: 遷移完成')
    finally:
        old_conn.close()
        new_conn.close()


if __name__ == '__main__':
    main()
