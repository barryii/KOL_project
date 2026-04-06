# main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
from database import DBManager
from youtuber_info import Chienseating, HowHowEat
from datetime import datetime
import os, re
import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel

try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False
    print("⚠️ Prophet 未安裝，/api/forecast 不可用。請執行: pip install prophet")

# ============ Jieba ============
try:
    import jieba
    DICT_PATH = os.path.join(os.path.dirname(__file__), '..', 'Nick', 'dict.txt')
    if os.path.exists(DICT_PATH):
        jieba.load_userdict(DICT_PATH)
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

# ============ SnowNLP ============
try:
    from snownlp import SnowNLP
    HAS_SNOWNLP = True
except ImportError:
    HAS_SNOWNLP = False

# ============ Model Loading ============
_base = os.path.dirname(os.path.abspath(__file__))
_MODEL_DIR = (
    os.path.join(_base, '..', 'Nick', 'models')   # 本機：Barry/../Nick/models
    if os.path.isdir(os.path.join(_base, '..', 'Nick', 'models'))
    else os.path.join(_base, 'Nick', 'models')     # NAS/Docker：/app/Nick/models
)
print(f"📂 MODEL_DIR = {os.path.abspath(_MODEL_DIR)}")
MODEL_VERSION = None
_model = None
_vectorizer = None
_model_columns = None
_kol_list = None
_kol_base_stats = None
_exclude_words = set()

try:
    from catboost import CatBoostRegressor
    v8 = os.path.join(_MODEL_DIR, 'view_predictor_v8.cbm')
    v7 = os.path.join(_MODEL_DIR, 'view_predictor_v7.cbm')
    if os.path.exists(v8):
        _model = CatBoostRegressor(); _model.load_model(v8); MODEL_VERSION = "V8"
    elif os.path.exists(v7):
        _model = CatBoostRegressor(); _model.load_model(v7); MODEL_VERSION = "V7"
    else:
        raise FileNotFoundError("V8/V7 not found")
except Exception as e:
    print(f"⚠️ CatBoost 載入失敗：{e}")
    try:
        _model = joblib.load(os.path.join(_MODEL_DIR, 'view_predictor.pkl')); MODEL_VERSION = "V6"
    except Exception as e2:
        print(f"⚠️ V6 pkl 載入失敗：{e2}")

try:
    _vectorizer   = joblib.load(os.path.join(_MODEL_DIR, 'vectorizer.pkl'))
    _model_columns = joblib.load(os.path.join(_MODEL_DIR, 'model_columns.pkl'))
    _kol_list     = joblib.load(os.path.join(_MODEL_DIR, 'kol_list.pkl'))
    _kol_base_stats = joblib.load(os.path.join(_MODEL_DIR, 'kol_base_stats.pkl'))
    _exclude_words  = joblib.load(os.path.join(_MODEL_DIR, 'exclude_words.pkl'))
    _exclude_words.update({'美食', '食物', '吃東西'})
    print(f"✅ 模型載入成功（{MODEL_VERSION}），KOL 數：{len(_kol_list) if _kol_list else 0}")
except Exception as e:
    print(f"⚠️ 輔助檔案載入失敗：{e}")

_KOL_NAME_MAP = {
    "HowHowEat": "豪豪", "howhoweat": "豪豪",
    "Chienseating": "千千", "chienseating": "千千", "千千進食中": "千千",
}

# ============ Predict Helpers ============
def _find_real_kol(name):
    if name in _KOL_NAME_MAP:
        return _KOL_NAME_MAP[name]
    for real in (_kol_list or []):
        if name in real or real in name:
            return real
    return name

def _clean_title(title):
    if not HAS_JIEBA:
        return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', title).lower()
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', title).lower()
    words = jieba.lcut(text)
    return " ".join(w for w in words if len(w) > 1 and w not in _exclude_words)

def _sentiment(text):
    import math
    t = str(text)
    raw = SnowNLP(t).sentiments if HAS_SNOWNLP else 0.5
    try:
        raw = float(raw)
    except Exception:
        raw = 0.5
    x = (raw - 0.5) * 6
    cal = 1 / (1 + math.exp(-x * 0.45))
    adj = 0.0
    boosts = {'挑戰':0.04,'地獄':0.04,'傷害':0.03,'暗黑':0.03,'恐怖':0.03,'崩潰':0.03,
              '超級':0.02,'終極':0.02,'史上':0.02,'第一次':0.02,'居然':0.02,'竟然':0.02,
              '瘋狂':0.03,'爆':0.02,'狂':0.02,'嚇':0.02,
              '好吃':0.06,'超好吃':0.08,'美味':0.06,'推薦':0.05,'必吃':0.06,'最愛':0.05,
              '幸福':0.05,'天堂':0.05,'銷魂':0.06,'豪華':0.04,'頂級':0.04,'夢幻':0.04,
              '完美':0.04,'驚喜':0.04,'超讚':0.06,'神級':0.06,
              '難吃':-0.08,'踩雷':-0.07,'失望':-0.06,'後悔':-0.06,
              '踩坑':-0.06,'噁心':-0.07,'最差':-0.06,'雷':-0.04}
    for word, delta in boosts.items():
        if word in t:
            adj += delta
    adj += min((t.count('！') + t.count('!')) * 0.015, 0.05)
    return round(max(0.08, min(0.92, cal + adj)), 4)

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
    video_type: str = Query("all", description="篩選特定的影片類型範疇"),
    top_n: int = Query(200, description="取預計算表中的前 N 名觀眾進行前端渲染")
):
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            # 依據 video_type 決定使用哪個查詢邏輯
            if video_type == 'all':
                # 全量：從預計算好的表中「加總」各維度的數據
                sql_all = """
                    SELECT 
                        author_id, 
                        MAX(author_name) as author_name, 
                        MAX(author_display_name) as author_display_name,
                        SUM(comment_count) as comment_count,
                        SUM(total_likes) as total_likes
                    FROM topN_comments
                    WHERE channel_id = %s
                    GROUP BY author_id
                    ORDER BY total_likes DESC, comment_count DESC
                    LIMIT %s
                """
                cursor.execute(sql_all, (channel1_id, top_n))
                channel1_results = cursor.fetchall()
                cursor.execute(sql_all, (channel2_id, top_n))
                channel2_results = cursor.fetchall()
            else:
                # 分維度：直接從整理過的 topN_comments 抓取該類型的數據
                sql_type = """
                    SELECT 
                        author_id, author_name, author_display_name,
                        comment_count, total_likes
                    FROM topN_comments
                    WHERE channel_id = %s AND `type` = %s
                    ORDER BY total_likes DESC, comment_count DESC
                    LIMIT %s
                """
                cursor.execute(sql_type, (channel1_id, video_type, top_n))
                channel1_results = cursor.fetchall()
                cursor.execute(sql_type, (channel2_id, video_type, top_n))
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
            # 原始 SQL
            sql_base = """
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
            """
            
            if top_n > 0:
                sql = sql_base + " LIMIT %s"
                cursor.execute(sql, (channel1_id, top_n))
                channel1_results = cursor.fetchall()
                cursor.execute(sql, (channel2_id, top_n))
                channel2_results = cursor.fetchall()
            else:
                # top_n <= 0 代表不限制，直接抓取全量
                cursor.execute(sql_base, (channel1_id,))
                channel1_results = cursor.fetchall()
                cursor.execute(sql_base, (channel2_id,))
                channel2_results = cursor.fetchall()
            
            return {
                channel1_id: channel1_results,
                channel2_id: channel2_results
            }

# http://localhost:8000/predict
class PredictRequest(BaseModel):
    title: str
    kol_name: str
    strategic_tag: str

@app.post("/predict")
async def predict(req: PredictRequest):
    if _model is None or _vectorizer is None:
        return {"status": "error", "message": "預測模型未載入"}
    try:
        real_name  = _find_real_kol(req.kol_name)
        base_val   = _kol_base_stats.get(real_name, np.median(list(_kol_base_stats.values())))
        base_log   = np.log1p(float(base_val))
        clean      = _clean_title(req.title)
        title_vec  = _vectorizer.transform([clean]).toarray()
        feat_names = _vectorizer.get_feature_names_out()
        matched    = [feat_names[i] for i in range(len(feat_names)) if title_vec[0][i] > 0]
        hit_count  = len(matched)

        if MODEL_VERSION in ("V8", "V7"):
            input_df = pd.DataFrame(0.0, index=[0], columns=_model_columns)
            input_df['kol_name']     = input_df['kol_name'].astype(object)
            input_df['strategic_tag'] = input_df['strategic_tag'].astype(object)
            for i, name in enumerate(feat_names):
                col = f"feat_{name}"
                if col in input_df.columns:
                    input_df.at[0, col] = float(title_vec[0][i])
            input_df.at[0, 'base_performance_log'] = base_log
            input_df.at[0, 'kol_name']     = real_name
            input_df.at[0, 'strategic_tag'] = req.strategic_tag
            if MODEL_VERSION == "V8":
                s = _sentiment(req.title)
                for col, val in [('sentiment_score', s), ('keyword_hit_count', float(hit_count)),
                                 ('title_length', float(len(req.title))),
                                 ('has_number', 1.0 if re.search(r'\d+', req.title) else 0.0),
                                 ('exclamation_count', float(req.title.count('！') + req.title.count('!')))]:
                    if col in input_df.columns:
                        input_df.at[0, col] = val
        else:
            input_df = pd.DataFrame(0.0, index=[0], columns=_model_columns, dtype=float)
            if 'base_performance_log' in input_df.columns:
                input_df.at[0, 'base_performance_log'] = base_log
            kol_col = f"kol_name_{real_name}"
            if kol_col in input_df.columns:
                input_df.at[0, kol_col] = 1.0
            tag_col = f"strategic_tag_{req.strategic_tag}"
            if tag_col in input_df.columns:
                input_df.at[0, tag_col] = 1.0
            for i, name in enumerate(feat_names):
                col = f"feat_{name}"
                if col in input_df.columns:
                    input_df.at[0, col] = float(title_vec[0][i])

        log_pred = _model.predict(input_df)[0]
        if MODEL_VERSION == "V7" and hit_count >= 2:
            log_pred *= 1.0 + (hit_count - 1) * 0.05
        final_view = max(0, int(round(np.expm1(log_pred))))
        sentiment  = _sentiment(req.title)
        return {
            "status": "success", "prediction": final_view,
            "base_value": int(base_val), "identified_as": real_name,
            "cleaned_title": clean, "matched": matched,
            "keyword_hit_count": hit_count,
            "sentiment_score": sentiment, "model_version": MODEL_VERSION,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e)}


# http://localhost:8000/api/features/ranking
@app.get("/api/features/ranking")
async def get_features_ranking():
    if _model is None or _model_columns is None:
        return {"status": "error", "message": "模型未載入"}
    try:
        if MODEL_VERSION in ("V8", "V7"):
            imp = _model.get_feature_importance()
            fs  = pd.Series(imp, index=_model_columns)
        else:
            fs = pd.Series(_model.feature_importances_, index=_model_columns)
        cf = fs[[c for c in fs.index if c.startswith('feat_')]]
        hidden = {'美食', '食物', '吃東西'}
        cf = cf[[c for c in cf.index if c.replace('feat_', '') not in hidden]]
        if cf.sum() > 0:
            cf = cf / cf.sum()
        cf = cf.sort_values(ascending=False)
        ranking = [{"keyword": n.replace('feat_', ''), "score": round(float(v), 4)} for n, v in cf.items()]
        return {"status": "success", "top_features": ranking[:15]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# http://localhost:8000/api/channel_info
@app.get("/api/channel_info")
def get_channel_info():
    c1 = Chienseating()
    c2 = HowHowEat()
    return {
        c1.channel_id: c1.channel_display_name,
        c2.channel_id: c2.channel_display_name
    }

# http://localhost:8000/api/video_clusters?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/video_clusters")
def get_video_clusters(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    video_type: str = Query("all", description="篩選特定的影片類型範疇")
):
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            type_filter = ""
            params = [channel1_id, channel2_id]
            if video_type != "all":
                type_filter = " AND `type` = %s "
                params.append(video_type)
            
            sql = f"""
                SELECT 
                    channel_id,
                    cluster_label,
                    COUNT(*) as video_count,
                    AVG(view_count) as avg_views,
                    AVG(like_count) as avg_likes,
                    AVG(comment_count) as avg_comments
                FROM videos
                WHERE channel_id IN (%s, %s) 
                  AND cluster_label IS NOT NULL
                  {type_filter}
                GROUP BY channel_id, cluster_label
                ORDER BY cluster_label ASC
            """
            cursor.execute(sql, tuple(params))
            results = cursor.fetchall()
            
            # 格式化為前端易用的結構
            data = {channel1_id: [], channel2_id: []}
            import decimal
            for row in results:
                c_id = row['channel_id']
                # 處理 Decimal 類型轉換為 float 以便 JSON 序列化
                for key in ['avg_views', 'avg_likes', 'avg_comments']:
                    if isinstance(row[key], decimal.Decimal):
                        row[key] = float(row[key])
                    data[c_id].append(row)
            
            return data

# http://localhost:8000/api/video_scatter?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
@app.get("/api/video_scatter")
def get_video_scatter(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    video_type: str = Query("all", description="篩選特定的影片類型範疇")
):
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            type_filter = ""
            params = [channel1_id, channel2_id]
            if video_type != "all":
                type_filter = " AND `type` = %s "
                params.append(video_type)
            
            sql = f"""
                SELECT 
                    channel_id,
                    video_id,
                    title,
                    view_count,
                    like_count,
                    comment_count,
                    cluster_label
                FROM videos
                WHERE channel_id IN (%s, %s) 
                  AND cluster_label IS NOT NULL
                  {type_filter}
                ORDER BY view_count DESC
            """
            cursor.execute(sql, tuple(params))
            results = cursor.fetchall()
            
            data = {channel1_id: [], channel2_id: []}
            for row in results:
                c_id = row['channel_id']
                if c_id in data:
                    data[c_id].append(row)
            
            return data


# http://localhost:8000/api/fan_sentiment_scatter?channel1_id=UC9i2Qgd5lizhVgJrdnxunKw&channel2_id=UCa2YiSXNTkmOA-QTKdzzbSQ
# http://localhost:8000/api/forecast?channel1_id=...&channel2_id=...&periods=6
@app.get("/api/forecast")
def get_forecast(
    channel1_id: str = Query(...),
    channel2_id: str = Query(...),
    periods: int = Query(6, description="預測未來幾個月"),
    metric: str = Query("avg_views", description="avg_views 或 total_views"),
    video_type: str = Query("all", description="影片類型篩選"),
):
    if not HAS_PROPHET:
        return {"status": "error", "message": "請先安裝 prophet: pip install prophet"}

    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            type_filter = "" if video_type == "all" else " AND type = %s"
            params = [channel1_id, channel2_id]
            if video_type != "all":
                params.append(video_type)
            sql = f"""
                SELECT
                    channel_id,
                    DATE_FORMAT(published_at, '%Y-%m-01') AS ds,
                    COUNT(video_id)  AS video_count,
                    AVG(view_count)  AS avg_views,
                    SUM(view_count)  AS total_views
                FROM videos
                WHERE channel_id IN (%s, %s){type_filter}
                GROUP BY channel_id, ds
                ORDER BY ds ASC
            """
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

    result = {}
    for ch_id in [channel1_id, channel2_id]:
        ch_rows = [r for r in rows if r["channel_id"] == ch_id]
        if len(ch_rows) < 3:
            result[ch_id] = {"status": "error", "message": "資料不足（該影片類型歷史資料少於 3 個月）"}
            continue

        df = pd.DataFrame(ch_rows)[["ds", metric]].rename(columns={metric: "y"})
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)

        # 歷史第 5 百分位作為輸出夾限，防止預測出不合理的極低值
        floor_val = max(1, int(df["y"].quantile(0.05)))

        m = Prophet(
            growth="linear",
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.01,  # 保守趨勢，不過度追隨短期波動
            changepoint_range=0.9,         # 允許配適到近 90% 的資料，抓到近期趨勢
        )
        m.fit(df)
        future = m.make_future_dataframe(periods=periods, freq="MS")
        forecast = m.predict(future)

        # 建立實際觀看數的查找表 (ds_str -> actual_y)
        actual_map = {row["ds"].strftime("%Y-%m"): int(round(row["y"]))
                      for _, row in df.iterrows()}
        hist_ds = set(actual_map.keys())

        out = []
        for _, row in forecast.iterrows():
            ds_str = row["ds"].strftime("%Y-%m")
            is_forecast = ds_str not in hist_ds
            out.append({
                "ds": ds_str,
                "actual":     actual_map.get(ds_str),           # 歷史點才有，預測點為 None
                "yhat":       max(floor_val, int(round(row["yhat"]))),
                "yhat_lower": max(floor_val, int(round(row["yhat_lower"]))),
                "yhat_upper": max(floor_val, int(round(row["yhat_upper"]))),
                "is_forecast": is_forecast,
            })
        result[ch_id] = {"status": "success", "data": out, "floor": floor_val}

    return result


@app.get("/api/fan_sentiment_scatter")
def get_fan_sentiment_scatter(
    channel1_id: str = Query(..., description="第一個頻道的 ID"),
    channel2_id: str = Query(..., description="第二個頻道的 ID"),
    video_type: str = Query("all", description="篩選特定的影片類型範疇")
):
    with DBManager().connect_to_db_readonly() as connection:
        with connection.cursor(dictionary=True) as cursor:
            type_filter = ""
            params = [channel1_id, channel2_id]
            if video_type != "all":
                type_filter = " AND `type` = %s "
                params.append(video_type)

            sql = f"""
                SELECT 
                    channel_id,
                    author_name,
                    text_content,
                    like_count,
                    reply_count,
                    sentiment,
                    sentiment_score
                FROM topN_comments_seperate
                WHERE channel_id IN (%s, %s)
                  AND sentiment IS NOT NULL
                  {type_filter}
            """
            cursor.execute(sql, tuple(params))
            results = cursor.fetchall()
            
            data = {channel1_id: [], channel2_id: []}
            for row in results:
                c_id = row['channel_id']
                if c_id in data:
                    data[c_id].append(row)
            
            return data
