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
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            # 撈取每月發片量與平均觀看數
            sql = """
                SELECT 
                    v.channel_id,
                    v.type AS video_type,
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
                GROUP BY v.channel_id, v.type, month
                ORDER BY month ASC
            """
            cursor.execute(sql, (channel1_id, channel2_id))
            results = cursor.fetchall()
            
            existing_months = sorted(list(set(row['month'] for row in results if row['month'])))
            if not existing_months:
                return {"months": []}
            
            all_months = generate_month_range(existing_months[0], existing_months[-1])

            processed_data = {"months": all_months}
            
            video_types = ['video', 'shorts', 'stream', 'all']
            for c_id in [channel1_id, channel2_id]:
                processed_data[c_id] = {}
                for vt in video_types:
                    processed_data[c_id][vt] = {
                        "video_counts": [], "avg_views": [], "total_views": [], 
                        "avg_likes": [], "total_likes": [], "avg_comments": [], "total_comments": []
                    }
                    
            # 建立 data_dict[month][c_id][v_type]
            from collections import defaultdict
            data_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
                "video_count": 0, "total_views": 0, "total_likes": 0, "total_comments": 0
            })))
            
            for row in results:
                m = row['month']
                c = row['channel_id']
                t = row['video_type'] or 'video' # fallback
                if m:
                    data_dict[m][c][t] = {
                        "video_count": row['video_count'],
                        "total_views": row['total_views'] or 0,
                        "total_likes": row['total_likes'] or 0,
                        "total_comments": row['total_comments'] or 0
                    }

            for m in all_months:
                for c_id in [channel1_id, channel2_id]:
                    # 計算 'all' 總和
                    total_v = sum(data_dict[m][c_id][t]["video_count"] for t in ['video', 'shorts', 'stream'])
                    total_views = sum(data_dict[m][c_id][t]["total_views"] for t in ['video', 'shorts', 'stream'])
                    total_likes = sum(data_dict[m][c_id][t]["total_likes"] for t in ['video', 'shorts', 'stream'])
                    total_comments = sum(data_dict[m][c_id][t]["total_comments"] for t in ['video', 'shorts', 'stream'])
                    
                    data_dict[m][c_id]['all'] = {
                        "video_count": total_v, "total_views": total_views, 
                        "total_likes": total_likes, "total_comments": total_comments
                    }
                    
                    for vt in video_types:
                        vd = data_dict[m][c_id][vt]
                        vc = vd["video_count"]
                        processed_data[c_id][vt]["video_counts"].append(vc)
                        processed_data[c_id][vt]["total_views"].append(vd["total_views"])
                        processed_data[c_id][vt]["total_likes"].append(vd["total_likes"])
                        processed_data[c_id][vt]["total_comments"].append(vd["total_comments"])
                        
                        # 計算平均
                        processed_data[c_id][vt]["avg_views"].append(round(vd["total_views"] / vc) if vc > 0 else 0)
                        processed_data[c_id][vt]["avg_likes"].append(round(vd["total_likes"] / vc) if vc > 0 else 0)
                        processed_data[c_id][vt]["avg_comments"].append(round(vd["total_comments"] / vc) if vc > 0 else 0)

            return processed_data

# http://localhost:8000/api/top_fans?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/top_fans")
def get_top_fans(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    top_n: int = Query(200, description="取預計算表中的前 N 名觀眾進行前端渲染")
):
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            # 從 topN_comments 取資料
            sql = """
                SELECT 
                    author_id,
                    author_name,
                    author_display_name,
                    comment_count,
                    total_likes
                FROM topN_comments
                WHERE channel_id = %s
                ORDER BY total_likes DESC, comment_count DESC
                LIMIT %s
            """
            
            cursor.execute(sql, (channel1_id, top_n))
            channel1_results = cursor.fetchall()
            
            cursor.execute(sql, (channel2_id, top_n))
            channel2_results = cursor.fetchall()
            
            # 回傳給前端
            return {
                channel1_id: channel1_results,
                channel2_id: channel2_results
            }

# http://localhost:8000/api/top_videos?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/top_videos")
def get_top_videos(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    top_n: int = Query(100, description="取歷史表現最好 (最高觀看) 的前 N 部影片")
):
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            # 依觀看數排序影片
            sql = """
                SELECT 
                    channel_id,
                    video_id,
                    title,
                    `type`,
                    view_count,
                    like_count,
                    comment_count,
                    DATE(published_at) AS published_date
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

