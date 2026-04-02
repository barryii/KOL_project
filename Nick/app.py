import joblib
import pandas as pd
import jieba
import re
import uvicorn
import os
import numpy as np
import time as time_module
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

# ============ Sentiment Engine ============
try:
    from snownlp import SnowNLP
    HAS_SNOWNLP = True
    print("✅ SnowNLP 情緒分析引擎載入成功")
except ImportError:
    HAS_SNOWNLP = False
    print("⚠️ SnowNLP 未安裝，使用規則式情緒分析")

# ============ Database ============
HAS_DB = False
db_engine = None
try:
    from sqlalchemy import create_engine
    DB_URL = (
        f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT','3306')}/{os.getenv('DB_NAME')}"
    )
    db_engine = create_engine(DB_URL, pool_recycle=3600)
    HAS_DB = True
    print("✅ MySQL 資料庫連線就緒")
except Exception as e:
    print(f"⚠️ 資料庫連線失敗: {e}")

# ============ KOL Config ============
KOL_NAME_MAP = {
    "HowHowEat": "豪豪", "howhoweat": "豪豪",
    "Chienseating": "千千", "chienseating": "千千", "千千進食中": "千千",
}
CHANNEL_TO_KOL = {
    "UCa2YiSXNTkmOA-QTKdzzbSQ": "豪豪",
    "UC9i2Qgd5lizhVgJrdnxunKw": "千千",
}

# ============ FastAPI ============
app = FastAPI(title="KOL 流量戰略分析系統 V2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ============ Model Loading ============
MODEL_DIR = 'models'
DICT_PATH = 'dict.txt'
if os.path.exists(DICT_PATH):
    jieba.load_userdict(DICT_PATH)

MODEL_VERSION = None
model = None
vectorizer = None
model_columns = None
kol_list = None
kol_base_stats = None
exclude_words = set()

try:
    from catboost import CatBoostRegressor
    # 優先載入 V8，再 V7，最後 V6
    v8_path = os.path.join(MODEL_DIR, 'view_predictor_v8.cbm')
    v7_path = os.path.join(MODEL_DIR, 'view_predictor_v7.cbm')
    if os.path.exists(v8_path):
        model = CatBoostRegressor()
        model.load_model(v8_path)
        MODEL_VERSION = "V8"
        print("✅ V8 CatBoost 模型載入成功（含情緒特徵）！")
    elif os.path.exists(v7_path):
        model = CatBoostRegressor()
        model.load_model(v7_path)
        MODEL_VERSION = "V7"
        print("✅ V7 CatBoost 模型載入成功！")
    else:
        raise FileNotFoundError("V8/V7 not found")
except Exception as e:
    print(f"⚠️ CatBoost 失敗 ({e})，嘗試 V6...")
    try:
        model = joblib.load(os.path.join(MODEL_DIR, 'view_predictor.pkl'))
        MODEL_VERSION = "V6"
        print("✅ V6 載入成功！")
    except Exception as e2:
        print(f"❌ 模型全部載入失敗: {e2}")

try:
    vectorizer = joblib.load(os.path.join(MODEL_DIR, 'vectorizer.pkl'))
    model_columns = joblib.load(os.path.join(MODEL_DIR, 'model_columns.pkl'))
    kol_list = joblib.load(os.path.join(MODEL_DIR, 'kol_list.pkl'))
    kol_base_stats = joblib.load(os.path.join(MODEL_DIR, 'kol_base_stats.pkl'))
    exclude_words = joblib.load(os.path.join(MODEL_DIR, 'exclude_words.pkl'))
    # 美食頻道通用詞：兩位 KOL 都是美食頻道，此詞佔 15.2% 權重但無策略意義
    exclude_words.update({'美食', '食物', '吃東西'})
    print(f"📦 共用組件載入成功 (版本: {MODEL_VERSION})")
    print(f"🚫 已排除通用詞: 美食, 食物, 吃東西")
except Exception as e:
    print(f"❌ 共用組件載入失敗: {e}")

# ============ Helpers ============
def find_real_kol_name(input_name, kol_list):
    if input_name in KOL_NAME_MAP:
        return KOL_NAME_MAP[input_name]
    for real_name in kol_list:
        if input_name in real_name or real_name in input_name:
            return real_name
    return input_name

def clean_title_text(title):
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', title).lower()
    words = jieba.lcut(text)
    return " ".join([w for w in words if len(w) > 1 and w not in exclude_words])

def get_sentiment_score(text):
    """
    YouTube 標題情緒分析（混合校正版）
    
    SnowNLP 原始模型是用電商評論訓練的，對 YouTube 標題有兩大問題：
    1. Naive Bayes 在短文本上容易輸出極端值（接近 0 或 1）
    2. YouTube 的聳動用語（地獄、傷害、崩潰）在電商是負面，但 YouTube 是正面引流詞
    
    改進方案：SnowNLP 基底分 + Sigmoid 校正 + YouTube 食物頻道專屬修正
    """
    import math
    t = str(text)

    # === Step 1: 取得基底分數 ===
    if HAS_SNOWNLP:
        try:
            raw = SnowNLP(t).sentiments
        except:
            raw = 0.5
    else:
        raw = 0.5  # 無 SnowNLP 時從中性開始

    # === Step 2: Sigmoid 校正（壓縮極端值）===
    # 將 [0,1] 映射到 [-3,3]，再用更溫和的 sigmoid 收斂
    x = (raw - 0.5) * 6       # 放大到 [-3, 3]
    calibrated = 1 / (1 + math.exp(-x * 0.45))  # 較平緩的 sigmoid

    # === Step 3: YouTube 食物頻道專屬修正 ===
    # 這些詞在電商評論是負面，但在 YouTube 美食頻道是「引流/挑戰/刺激」正面訊號
    yt_engagement_words = {
        '挑戰': 0.04, '地獄': 0.04, '傷害': 0.03, '暗黑': 0.03,
        '恐怖': 0.03, '崩潰': 0.03, '超級': 0.02, '終極': 0.02,
        '史上': 0.02, '第一次': 0.02, '居然': 0.02, '竟然': 0.02,
        '瘋狂': 0.03, '爆': 0.02, '狂': 0.02, '嚇': 0.02,
    }
    # 正面食物用語
    positive_food = {
        '好吃': 0.06, '超好吃': 0.08, '美味': 0.06, '推薦': 0.05,
        '必吃': 0.06, '最愛': 0.05, '幸福': 0.05, '天堂': 0.05,
        '銷魂': 0.06, '豪華': 0.04, '頂級': 0.04, '夢幻': 0.04,
        '完美': 0.04, '驚喜': 0.04, '超讚': 0.06, '神級': 0.06,
    }
    # 真正的負面用語（即使在 YouTube 也是負面）
    negative_food = {
        '難吃': -0.08, '踩雷': -0.07, '失望': -0.06, '後悔': -0.06,
        '踩坑': -0.06, '噁心': -0.07, '最差': -0.06, '雷': -0.04,
    }

    adjustment = 0.0
    for word, delta in {**yt_engagement_words, **positive_food, **negative_food}.items():
        if word in t:
            adjustment += delta

    # === Step 4: 標題結構加分 ===
    # 驚嘆號 = 興奮/正面能量
    excl = t.count('！') + t.count('!')
    adjustment += min(excl * 0.015, 0.05)

    # === Step 5: 合成最終分數 ===
    final = calibrated + adjustment
    final = max(0.08, min(0.92, final))  # 避免極端 0/1

    return round(final, 4)

# ============ Data Cache ============
_data_cache = {"df": None, "ts": 0}

def _load_video_data():
    if not HAS_DB:
        return pd.DataFrame()
    now = time_module.time()
    if _data_cache["df"] is not None and now - _data_cache["ts"] < 300:
        return _data_cache["df"].copy()
    try:
        ids = list(CHANNEL_TO_KOL.keys())
        q = f"SELECT video_id,channel_id,title,published_at,type,duration_sec,view_count,like_count,comment_count FROM videos WHERE channel_id IN ('{ids[0]}','{ids[1]}')"
        df = pd.read_sql(q, db_engine)
        df['kol_name'] = df['channel_id'].map(CHANNEL_TO_KOL)
        df['strategic_tag'] = df.apply(
            lambda r: 'Shorts' if str(r.get('type',''))=='shorts'
            else ('Long' if int(r.get('duration_sec',0))>480 else 'Mid'), axis=1)
        df['published_at'] = pd.to_datetime(df['published_at'])
        for c in ['view_count','like_count','comment_count','duration_sec']:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
        _data_cache["df"] = df
        _data_cache["ts"] = now
        return df.copy()
    except Exception as e:
        print(f"❌ 資料載入失敗: {e}")
        import traceback; traceback.print_exc()
        return pd.DataFrame()

# ============ /predict ============
class PredictRequest(BaseModel):
    title: str
    kol_name: str
    strategic_tag: str

@app.post("/predict")
async def predict(req: PredictRequest):
    try:
        real_name = find_real_kol_name(req.kol_name, kol_list)
        base_val = kol_base_stats.get(real_name, np.median(list(kol_base_stats.values())))
        base_log = np.log1p(float(base_val))
        clean_title = clean_title_text(req.title)
        title_vec = vectorizer.transform([clean_title]).toarray()
        feat_names = vectorizer.get_feature_names_out()
        matched = [feat_names[i] for i in range(len(feat_names)) if title_vec[0][i] > 0]
        keyword_hit_count = len(matched)

        if MODEL_VERSION in ("V8", "V7"):
            input_df = pd.DataFrame(0.0, index=[0], columns=model_columns)
            input_df['kol_name'] = input_df['kol_name'].astype(object)
            input_df['strategic_tag'] = input_df['strategic_tag'].astype(object)
            for i, name in enumerate(feat_names):
                col = f"feat_{name}"
                if col in input_df.columns:
                    input_df.at[0, col] = float(title_vec[0][i])
            input_df.at[0, 'base_performance_log'] = base_log
            input_df.at[0, 'kol_name'] = real_name
            input_df.at[0, 'strategic_tag'] = req.strategic_tag

            # V8 新增特徵
            if MODEL_VERSION == "V8":
                sentiment = get_sentiment_score(req.title)
                if 'sentiment_score' in input_df.columns:
                    input_df.at[0, 'sentiment_score'] = sentiment
                if 'keyword_hit_count' in input_df.columns:
                    input_df.at[0, 'keyword_hit_count'] = float(keyword_hit_count)
                if 'title_length' in input_df.columns:
                    input_df.at[0, 'title_length'] = float(len(req.title))
                if 'has_number' in input_df.columns:
                    input_df.at[0, 'has_number'] = 1.0 if re.search(r'\d+', req.title) else 0.0
                if 'exclamation_count' in input_df.columns:
                    input_df.at[0, 'exclamation_count'] = float(req.title.count('！') + req.title.count('!'))
        else:
            input_df = pd.DataFrame(0.0, index=[0], columns=model_columns, dtype=float)
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

        log_pred = model.predict(input_df)[0]
        # V7 修補：TF-IDF L2 稀釋問題（V8 已原生支援 keyword_hit_count，不需修補）
        if MODEL_VERSION == "V7" and keyword_hit_count >= 2:
            log_pred *= 1.0 + (keyword_hit_count - 1) * 0.05
        final_view = max(0, int(round(np.expm1(log_pred))))
        sentiment = get_sentiment_score(req.title)

        return {
            "status": "success", "prediction": final_view,
            "base_value": int(base_val), "identified_as": real_name,
            "cleaned_title": clean_title, "matched": matched,
            "keyword_hit_count": keyword_hit_count,
            "sentiment_score": sentiment, "model_version": MODEL_VERSION,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e)}

# ============ /api/features/ranking ============
@app.get("/api/features/ranking")
async def get_ranking():
    try:
        if MODEL_VERSION in ("V8", "V7"):
            imp = model.get_feature_importance()
            fs = pd.Series(imp, index=model_columns)
        else:
            fs = pd.Series(model.feature_importances_, index=model_columns)
        cf = fs[[c for c in fs.index if c.startswith('feat_')]]
        # 過濾掉通用詞（美食等），讓排行顯示更有策略價值的關鍵字
        hidden_keywords = {'美食', '食物', '吃東西'}
        cf = cf[[c for c in cf.index if c.replace('feat_','') not in hidden_keywords]]
        if cf.sum() > 0:
            cf = cf / cf.sum()
        cf = cf.sort_values(ascending=False)
        ranking = [{"keyword": n.replace('feat_',''), "score": round(float(v),4)} for n,v in cf.items()]
        return {"status": "success", "top_features": ranking[:15]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============ /api/growth-stats ============
@app.get("/api/growth-stats")
async def get_growth_stats():
    try:
        df = _load_video_data()
        if df.empty:
            return {"status": "error", "message": "無法載入影片資料"}
        df['month'] = df['published_at'].dt.to_period('M').astype(str)
        all_months = sorted(df['month'].unique())
        kol_data = {}
        for kol in df['kol_name'].unique():
            kdf = df[df['kol_name'] == kol]
            m = kdf.groupby('month').agg(
                uploads=('video_id','count'),
                avg_views=('view_count','mean'),
                total_views=('view_count','sum'),
                avg_likes=('like_count','mean'),
                avg_comments=('comment_count','mean'),
            ).reindex(all_months, fill_value=0)
            m['growth_rate'] = m['avg_views'].pct_change().fillna(0).replace([np.inf, -np.inf], 0)
            m['efficiency'] = (m['avg_views'] / m['uploads'].replace(0,1))
            monthly = []
            for mo, row in m.iterrows():
                monthly.append({
                    "month": mo, "uploads": int(row['uploads']),
                    "avg_views": int(row['avg_views']), "total_views": int(row['total_views']),
                    "growth_rate": round(float(row['growth_rate']),4),
                    "efficiency": int(row['efficiency']),
                })
            tag_stats = kdf.groupby('strategic_tag').agg(
                count=('video_id','count'), avg_views=('view_count','mean')
            ).to_dict('index')
            kol_data[kol] = {
                "total_videos": int(len(kdf)),
                "avg_views": int(kdf['view_count'].mean()),
                "median_views": int(kdf['view_count'].median()),
                "total_views": int(kdf['view_count'].sum()),
                "avg_monthly_uploads": round(len(kdf)/max(len(all_months),1),1),
                "monthly": monthly,
                "by_tag": {k:{"count":int(v['count']),"avg_views":int(v['avg_views'])} for k,v in tag_stats.items()},
            }
        return {"status":"success","data":kol_data,"months":all_months}
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status":"error","message":str(e)}

# ============ /api/sentiment ============
@app.get("/api/sentiment")
async def get_sentiment():
    try:
        df = _load_video_data()
        if df.empty:
            return {"status":"error","message":"無法載入影片資料"}
        df['sentiment'] = df['title'].apply(get_sentiment_score)
        df['sentiment_cat'] = pd.cut(df['sentiment'], bins=[0,0.4,0.6,1.0],
                                      labels=['negative','neutral','positive'], include_lowest=True)
        kol_data = {}
        for kol in df['kol_name'].unique():
            kdf = df[df['kol_name']==kol]
            dist = kdf['sentiment_cat'].value_counts().to_dict()
            sv = {}
            for cat in ['positive','neutral','negative']:
                cdf = kdf[kdf['sentiment_cat']==cat]
                sv[cat] = {"count":int(len(cdf)),"avg_views":int(cdf['view_count'].mean()) if len(cdf)>0 else 0}
            tp = kdf.nlargest(5,'sentiment')[['title','sentiment','view_count']].to_dict('records')
            tn = kdf.nsmallest(5,'sentiment')[['title','sentiment','view_count']].to_dict('records')
            scatter = kdf[['sentiment','view_count','title']].to_dict('records')
            kol_data[kol] = {
                "avg_sentiment": round(float(kdf['sentiment'].mean()),4),
                "distribution": {"positive":int(dist.get('positive',0)),"neutral":int(dist.get('neutral',0)),"negative":int(dist.get('negative',0))},
                "sentiment_views": sv,
                "top_positive": [{"title":r['title'],"sentiment":round(float(r['sentiment']),4),"views":int(r['view_count'])} for r in tp],
                "top_negative": [{"title":r['title'],"sentiment":round(float(r['sentiment']),4),"views":int(r['view_count'])} for r in tn],
                "scatter": [{"x":round(float(r['sentiment']),4),"y":int(r['view_count']),"title":r['title']} for r in scatter],
            }
        return {"status":"success","data":kol_data,"engine":"snownlp" if HAS_SNOWNLP else "rule-based"}
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status":"error","message":str(e)}

# ============ /api/audience-comparison ============
@app.get("/api/audience-comparison")
async def get_audience_comparison():
    try:
        df = _load_video_data()
        if df.empty:
            return {"status":"error","message":"無法載入影片資料"}
        df['engagement_rate'] = ((df['like_count']+df['comment_count'])/df['view_count'].replace(0,1)*100).round(4)
        df['like_rate'] = (df['like_count']/df['view_count'].replace(0,1)*100).round(4)
        df['comment_rate'] = (df['comment_count']/df['view_count'].replace(0,1)*100).round(4)
        kol_data = {}
        for kol in df['kol_name'].unique():
            kdf = df[df['kol_name']==kol]
            ts = {}
            for tag in ['Long','Mid','Shorts']:
                tdf = kdf[kdf['strategic_tag']==tag]
                if len(tdf)>0:
                    ts[tag] = {"count":int(len(tdf)),"pct":round(len(tdf)/len(kdf)*100,1),
                        "avg_views":int(tdf['view_count'].mean()),"avg_likes":int(tdf['like_count'].mean()),
                        "engagement_rate":round(float(tdf['engagement_rate'].mean()),4),
                        "like_rate":round(float(tdf['like_rate'].mean()),4),
                        "comment_rate":round(float(tdf['comment_rate'].mean()),4)}
                else:
                    ts[tag] = {"count":0,"pct":0,"avg_views":0,"avg_likes":0,"engagement_rate":0,"like_rate":0,"comment_rate":0}
            all_words = []
            for title in kdf['title']:
                text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]',' ',str(title)).lower()
                words = [w for w in jieba.lcut(text) if len(w)>1 and w not in exclude_words]
                all_words.extend(words)
            top_kw = [{"word":w,"count":c} for w,c in Counter(all_words).most_common(15)]
            tv = kdf.nlargest(5,'view_count')[['title','view_count','like_count','comment_count','strategic_tag']].to_dict('records')
            kol_data[kol] = {
                "total_videos":int(len(kdf)),
                "overall_engagement":round(float(kdf['engagement_rate'].mean()),4),
                "overall_like_rate":round(float(kdf['like_rate'].mean()),4),
                "overall_comment_rate":round(float(kdf['comment_rate'].mean()),4),
                "by_type":ts, "top_keywords":top_kw,
                "top_videos":[{"title":r['title'],"views":int(r['view_count']),"likes":int(r['like_count']),"comments":int(r['comment_count']),"tag":r['strategic_tag']} for r in tv],
            }
        kol_names = list(kol_data.keys())
        shared = []
        if len(kol_names)==2:
            kw1 = {k['word'] for k in kol_data[kol_names[0]]['top_keywords']}
            kw2 = {k['word'] for k in kol_data[kol_names[1]]['top_keywords']}
            shared = list(kw1 & kw2)
        return {"status":"success","data":kol_data,"shared_keywords":shared}
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status":"error","message":str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)