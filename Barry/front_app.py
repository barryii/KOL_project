# main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
from database import DBManager
from youtuber_info import Chienseating, HowHowEat

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

@app.get("/api/overview")
def get_channel_overview(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID")
):
    conn = DBManager().connect_to_db()
    try:
        with conn.cursor(dictionary=True) as cursor:
            # 撈取每月發片量與平均觀看數
            sql = """
                SELECT 
                    channel_id,
                    DATE_FORMAT(published_at, '%Y-%m') AS month,
                    COUNT(video_id) AS video_count,
                    AVG(view_count) AS avg_views
                FROM videos
                WHERE channel_id IN (%s, %s)
                GROUP BY channel_id, month
                ORDER BY month ASC
            """
            cursor.execute(sql, (channel1_id, channel2_id))
            results = cursor.fetchall()
            
            # 整理數據格式給前端的 Chart.js
            # 1. 抓出所有出現過的月份並排序
            all_months = sorted(list(set(row['month'] for row in results if row['month'])))
            
            # 2. 初始化資料結構
            processed_data = {
                "months": all_months,
                channel1_id: {"video_counts": [], "avg_views": []},
                channel2_id: {"video_counts": [], "avg_views": []}
            }
            
            # 建立一個查詢字典方便填入資料
            data_dict = defaultdict(lambda: defaultdict(dict))
            for row in results:
                if row['month']:
                    data_dict[row['month']][row['channel_id']] = {
                        "video_count": row['video_count'],
                        "avg_views": round(row['avg_views'] or 0)
                    }

            # 3. 確保每個月份都有數據 (若該月沒發片則補 0)
            for m in all_months:
                for c_id in [channel1_id, channel2_id]:
                    month_data = data_dict[m].get(c_id, {"video_count": 0, "avg_views": 0})
                    processed_data[c_id]["video_counts"].append(month_data["video_count"])
                    processed_data[c_id]["avg_views"].append(month_data["avg_views"])

            return processed_data
    finally:
        conn.close()
