# main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
from database import DBManager
from youtuber_info import Chienseating, HowHowEat
from datetime import datetime

# 本機執行指令： uvicorn front_app:app --reload
# localhost:8000

app = FastAPI()

# 允許跨域請求 (CORS)，方便你本機前端與後端不同 port 測試
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 新增一個產生連續月份的輔助函式
def generate_month_range(start_month_str, end_month_str):
    if not start_month_str or not end_month_str:
        return []
        
    start = datetime.strptime(start_month_str, "%Y-%m")
    end = datetime.strptime(end_month_str, "%Y-%m")
    
    months = []
    current = start
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        # 處理進位到下個月
        year = current.year
        month = current.month + 1
        if month > 12:
            month = 1
            year += 1
        current = current.replace(year=year, month=month)
    return months

# http://localhost:8000/api/overview?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/overview")
def get_channel_overview(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    # video_type: str = Query(..., description="影片類型")
):
    with DBManager().connect_to_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            # 撈取每月發片量與平均觀看數
            sql = """
                SELECT 
                    v.channel_id,
                    DATE_FORMAT(v.published_at, '%Y-%m') AS month,
                    COUNT(v.video_id) AS video_count,
                    AVG(v.view_count) AS avg_views,
                    SUM(v.view_count) AS total_views,
                    AVG(v.like_count) AS avg_likes,
                    SUM(v.like_count) AS total_likes,
                    AVG(v.comment_count) AS avg_comments,
                    SUM(v.comment_count) AS total_comments
                FROM videos v
                WHERE v.channel_id IN (%s, %s)
                GROUP BY v.channel_id, month
                ORDER BY month ASC
            """
            cursor.execute(sql, (channel1_id, channel2_id))
            results = cursor.fetchall()
            # 1. 抓出存在的月份並找出頭尾
            existing_months = sorted(list(set(row['month'] for row in results if row['month'])))
            
            # 如果沒有任何資料，直接回傳空結構
            if not existing_months:
                return {"months": [], channel1_id: {"video_counts": [], "avg_views": []}, channel2_id: {"video_counts": [], "avg_views": []}}
            
            # 2. 生成連續的月份列表 (解決空月缺漏問題)
            all_months = generate_month_range(existing_months[0], existing_months[-1])

            # 2. 初始化資料結構
            processed_data = {
                "months": all_months,
                channel1_id: {"video_counts": [], "avg_views": [], "total_views": [], "avg_likes": [], "total_likes": [], "avg_comments": [], "total_comments": []},
                channel2_id: {"video_counts": [], "avg_views": [], "total_views": [], "avg_likes": [], "total_likes": [], "avg_comments": [], "total_comments": []}
            }
            
            # 建立一個查詢字典方便填入資料
            data_dict = defaultdict(lambda: defaultdict(dict))
            for row in results:
                if row['month']:
                    data_dict[row['month']][row['channel_id']] = {
                        "video_count": row['video_count'],
                        "avg_views": round(row['avg_views'] or 0),
                        "total_views": row['total_views'],
                        "avg_likes": round(row['avg_likes'] or 0),
                        "total_likes": row['total_likes'],
                        "avg_comments": round(row['avg_comments'] or 0),
                        "total_comments": row['total_comments']
                    }

            # 3. 確保每個月份都有數據 (若該月沒發片則補 0)
            for m in all_months:
                for c_id in [channel1_id, channel2_id]:
                    month_data = data_dict[m].get(c_id, {"video_count": 0, "avg_views": 0, "total_views": 0, "avg_likes": 0, "total_likes": 0, "avg_comments": 0, "total_comments": 0})
                    processed_data[c_id]["video_counts"].append(month_data["video_count"])
                    processed_data[c_id]["avg_views"].append(month_data["avg_views"])
                    processed_data[c_id]["total_views"].append(month_data["total_views"])
                    processed_data[c_id]["avg_likes"].append(month_data["avg_likes"])
                    processed_data[c_id]["total_likes"].append(month_data["total_likes"])
                    processed_data[c_id]["avg_comments"].append(month_data["avg_comments"])
                    processed_data[c_id]["total_comments"].append(month_data["total_comments"])

            return processed_data

# http://localhost:8000/api/top_commenters?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/top_commenters")
def get_top_commenters(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    top_n: int = Query(10, description="取前 N 名活躍觀眾") # 預設抓前 10 名
):
    with DBManager().connect_to_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            # SQL 邏輯：依 author_id 分組計算留言數，降冪排序後取前 N 筆
            # 使用 MAX(author_name) 是為了解決同一 author_id 可能有改過名字的問題
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
            
            # 查詢頻道 1 的活躍觀眾
            cursor.execute(sql, (channel1_id, top_n))
            channel1_results = cursor.fetchall()
            
            # 查詢頻道 2 的活躍觀眾
            cursor.execute(sql, (channel2_id, top_n))
            channel2_results = cursor.fetchall()
            
            # 整理成前端圖表或表格易於使用的格式
            return {
                channel1_id: {
                    "names": [row['author_name'] for row in channel1_results],
                    "counts": [row['comment_count'] for row in channel1_results],
                    "total_likes": [row['total_likes'] for row in channel1_results],
                    "details": channel1_results # 保留完整原始資料備用
                },
                channel2_id: {
                    "names": [row['author_name'] for row in channel2_results],
                    "counts": [row['comment_count'] for row in channel2_results],
                    "total_likes": [row['total_likes'] for row in channel2_results],
                    "details": channel2_results
                }
            }

# http://localhost:8000/api/top_commenters_by_likes?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/top_commenters_by_likes")
def get_top_commenters_by_likes(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    top_n: int = Query(20, description="取前 N 名獲讚最多的觀眾"),
):
    with DBManager().connect_to_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            # SQL 邏輯：加入 SUM(like_count) 計算總按讚數，並以此作為主要排序依據
            # 若按讚數相同，則以留言數較多者優先 (ORDER BY total_likes DESC, comment_count DESC)
            sql = """
                SELECT 
                    author_id,
                    MAX(author_name) AS author_name,
                    COUNT(comment_id) AS comment_count,
                    SUM(like_count) AS total_likes
                FROM video_comments
                WHERE channel_id = %s
                GROUP BY author_id
                HAVING comment_count > 20
                ORDER BY total_likes DESC, comment_count DESC
                LIMIT %s
            """
            
            cursor.execute(sql, (channel1_id, top_n))
            channel1_results = cursor.fetchall()
            
            cursor.execute(sql, (channel2_id, top_n))
            channel2_results = cursor.fetchall()
            
            # 整理結構，將 total_likes 與 comment_counts 都拉出來成獨立陣列
            return {
                channel1_id: {
                    "names": [row['author_name'] for row in channel1_results],
                    "total_likes": [int(row['total_likes'] or 0) for row in channel1_results],
                    "comment_counts": [row['comment_count'] for row in channel1_results],
                    "details": channel1_results
                },
                channel2_id: {
                    "names": [row['author_name'] for row in channel2_results],
                    "total_likes": [int(row['total_likes'] or 0) for row in channel2_results],
                    "comment_counts": [row['comment_count'] for row in channel2_results],
                    "details": channel2_results
                }
            }

# http://localhost:8000/api/top_videos?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/top_videos")
def get_top_videos(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    top_n: int = Query(5, description="取歷史表現最好 (最高觀看) 的前 N 部影片")
):
    with DBManager().connect_to_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            # 依觀看數排序影片
            sql = """
                SELECT 
                    channel_id,
                    video_id,
                    title,
                    view_count,
                    like_count,
                    comment_count,
                    DATE_FORMAT(published_at, '%%Y-%%m-%%d') AS published_date
                FROM videos
                WHERE channel_id = %s
                ORDER BY view_count DESC
                LIMIT %s
            """
            
            cursor.execute(sql, (channel1_id, top_n))
            channel1_results = cursor.fetchall()
            
            cursor.execute(sql, (channel2_id, top_n))
            channel2_results = cursor.fetchall()
            
            return {
                channel1_id: channel1_results,
                channel2_id: channel2_results
            }

# http://localhost:8000/api/channel_info
@app.get("/api/channel_info")
def get_channel_info():
    c1 = Chienseating()
    c2 = HowHowEat()
    return {
        c1.channel_id: c1.channel_display_name,
        c2.channel_id: c2.channel_display_name
    }

