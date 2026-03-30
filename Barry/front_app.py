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
    conn = DBManager().connect_to_db()
    try:
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
    finally:
        conn.close()
