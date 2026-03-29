import joblib
import pandas as pd
import jieba
import re
import uvicorn
import os
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# KOL 名稱對照表（前端英文名 → 訓練資料中文名）
KOL_NAME_MAP = {
    "HowHowEat": "豪豪",
    "howhoweat": "豪豪",
    "Chienseating": "千千",
    "chienseating": "千千",
    "千千進食中": "千千",
}

app = FastAPI(title="KOL Predictor V7 - CatBoost Edition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 載入模型組件
MODEL_DIR = 'models'
DICT_PATH = 'dict.txt'

# 載入自定義辭典
if os.path.exists(DICT_PATH):
    jieba.load_userdict(DICT_PATH)

# 嘗試載入 V7 CatBoost 模型，失敗則回退 V6
MODEL_VERSION = None
model = None
vectorizer = None
model_columns = None
kol_list = None
kol_base_stats = None
exclude_words = set()

try:
    from catboost import CatBoostRegressor
    v7_path = os.path.join(MODEL_DIR, 'view_predictor_v7.cbm')
    if os.path.exists(v7_path):
        model = CatBoostRegressor()
        model.load_model(v7_path)
        MODEL_VERSION = "V7"
        print("✅ V7 CatBoost 模型載入成功！")
    else:
        raise FileNotFoundError("V7 模型不存在，嘗試 V6")
except Exception as e:
    print(f"⚠️ V7 載入失敗 ({e})，嘗試 V6...")
    try:
        model = joblib.load(os.path.join(MODEL_DIR, 'view_predictor.pkl'))
        MODEL_VERSION = "V6"
        print("✅ V6 Random Forest 模型載入成功！")
    except Exception as e2:
        print(f"❌ V6 也載入失敗: {e2}")

try:
    vectorizer = joblib.load(os.path.join(MODEL_DIR, 'vectorizer.pkl'))
    model_columns = joblib.load(os.path.join(MODEL_DIR, 'model_columns.pkl'))
    kol_list = joblib.load(os.path.join(MODEL_DIR, 'kol_list.pkl'))
    kol_base_stats = joblib.load(os.path.join(MODEL_DIR, 'kol_base_stats.pkl'))
    exclude_words = joblib.load(os.path.join(MODEL_DIR, 'exclude_words.pkl'))
    print(f"📦 共用組件載入成功 (模型版本: {MODEL_VERSION})")
    print(f"🚫 排除詞集: {exclude_words}")
except Exception as e:
    print(f"❌ 共用組件載入失敗: {e}")

# 【核心功能】名稱校正邏輯：先查對照表，再做模糊比對
def find_real_kol_name(input_name, kol_list):
    if input_name in KOL_NAME_MAP:
        return KOL_NAME_MAP[input_name]
    for real_name in kol_list:
        if input_name in real_name or real_name in input_name:
            return real_name
    return input_name

def clean_title_text(title):
    """清洗標題：去標點 + 分詞 + 去品牌詞"""
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', title).lower()
    words = jieba.lcut(text)
    return " ".join([w for w in words if len(w) > 1 and w not in exclude_words])

class PredictRequest(BaseModel):
    title: str
    kol_name: str
    strategic_tag: str

@app.post("/predict")
async def predict(req: PredictRequest):
    try:
        # 1. 名稱校正
        real_name = find_real_kol_name(req.kol_name, kol_list)
        print(f"👤 輸入名稱: {req.kol_name} -> 系統識別: {real_name}")
        
        # 2. 流量基數
        base_val = kol_base_stats.get(real_name, np.median(list(kol_base_stats.values())))
        base_log = np.log1p(float(base_val))
        print(f"📈 流量基數 (Log): {base_log:.4f}")
        
        # 3. 標題 TF-IDF
        clean_title = clean_title_text(req.title)
        title_vec = vectorizer.transform([clean_title]).toarray()
        
        # 收集命中的關鍵字
        feat_names = vectorizer.get_feature_names_out()
        matched = [feat_names[i] for i in range(len(feat_names)) if title_vec[0][i] > 0]
        
        if MODEL_VERSION == "V7":
            # === CatBoost：直接傳入類別字串，不需 one-hot ===
            input_df = pd.DataFrame(0.0, index=[0], columns=model_columns)
            # 類別欄位需要轉為 object 才能放字串
            input_df['kol_name'] = input_df['kol_name'].astype(object)
            input_df['strategic_tag'] = input_df['strategic_tag'].astype(object)
            
            # 填入 TF-IDF 特徵
            for i, name in enumerate(feat_names):
                col_name = f"feat_{name}"
                if col_name in input_df.columns:
                    input_df.at[0, col_name] = float(title_vec[0][i])
            
            # 填入數值與類別特徵
            input_df.at[0, 'base_performance_log'] = base_log
            input_df.at[0, 'kol_name'] = real_name
            input_df.at[0, 'strategic_tag'] = req.strategic_tag
            
            print(f"✅ CatBoost 輸入: kol={real_name}, tag={req.strategic_tag}")
        else:
            # === V6 Random Forest：使用 one-hot 編碼 ===
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
                col_name = f"feat_{name}"
                if col_name in input_df.columns:
                    input_df.at[0, col_name] = float(title_vec[0][i])

        # 4. 預測與還原
        log_pred = model.predict(input_df)[0]
        final_view = max(0, int(round(np.expm1(log_pred))))

        return {
            "status": "success",
            "prediction": final_view,
            "base_value": int(base_val),
            "identified_as": real_name,
            "cleaned_title": clean_title,
            "matched": matched,
            "model_version": MODEL_VERSION
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/api/features/ranking")
async def get_ranking():
    """取得模型特徵重要性排行（去人格化後的純內容關鍵字）"""
    try:
        if MODEL_VERSION == "V7":
            importances = model.get_feature_importance()
            feat_series = pd.Series(importances, index=model_columns)
        else:
            feat_series = pd.Series(model.feature_importances_, index=model_columns)
        
        # 只取 feat_ 開頭的（去人格化後的純內容特徵），排除 KOL 身份特徵
        content_feats = feat_series[[c for c in feat_series.index if c.startswith('feat_')]]
        # 正規化為百分比
        if content_feats.sum() > 0:
            content_feats = content_feats / content_feats.sum()
        content_feats = content_feats.sort_values(ascending=False)
        
        ranking = [{"keyword": n.replace('feat_', ''), "score": round(float(v), 4)} 
                   for n, v in content_feats.items()]
        return {"status": "success", "top_features": ranking[:15]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)