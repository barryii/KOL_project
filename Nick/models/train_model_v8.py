"""
V8 CatBoost 訓練腳本
相較 V7 新增：
  1. sentiment_score  — 標題情緒分數（SnowNLP + YouTube 校正）
  2. keyword_hit_count — 關鍵字命中數量（修復 TF-IDF L2 稀釋問題）
  3. title_length      — 標題字數
  4. has_number         — 標題是否含數字（如「100」「第一」）
  5. exclamation_count  — 驚嘆號數量（引流標記）
"""
import pandas as pd
import numpy as np
import jieba
import re
import joblib
import os
import math
from catboost import CatBoostRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

# 嘗試載入 SnowNLP
try:
    from snownlp import SnowNLP
    HAS_SNOWNLP = True
    print("✅ SnowNLP 可用")
except ImportError:
    HAS_SNOWNLP = False
    print("⚠️ SnowNLP 未安裝，使用規則式情緒分析")

# 設定路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR) if "models" in BASE_DIR else BASE_DIR
DATA_PATH = os.path.join(PROJECT_ROOT, 'reports', 'combined_kol_cleaned_data.xlsx')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')
DICT_PATH = os.path.join(PROJECT_ROOT, 'dict.txt')

# ===== 停用詞表 =====
STOP_WORDS = {
    '的', '了', '在', '與', '和', '是', '就', '都', '而', '及', '著', '或', '之',
    '也', '又', '不', '很', '太', '到', '去', '來', '會', '能', '要', '讓', '把',
    '被', '從', '給', '用', '向', '對', '為', '以', '因', '但', '還', '已', '再',
    '起來', '就是', '自己', '一起', '真的', '什麼', '一個', '一次', '一口',
    '好不好', '感覺', '覺得', '一樣', '一般', '一直', '一下', '竟然', '結果',
    '原來', '特別', '多少', '如果', '只要', '怎麼', '這個', '那個', '可以',
    '沒有', '不是', '開始', '出來', '回去', '以上', '以下', '之前', '之後',
    '應該', '其實', '大家', '全部', '終於', '居然', '完全', '到底', '為什麼',
    '這樣', '那樣', '好像', '看起來', '還是', '分鐘', '小時', '而且', '不過',
    '所以', '因為', '雖然', '或是', '雖然', '然後', '接著', '最後', '首先',
    '第一', '今天', '明天', '昨天', '這次', '每次', '那次', '知道', '發現',
    '告訴', '他們', '我們', '你們', '它們', '大概', '差不多', '幾乎', '簡直',
    '影片', '挑戰', '直播', '開箱', '實測', '體驗',
    'ft', 'ep', 'vs', 'feat', 'part', 'vlog',
    '美食', '食物', '吃東西',
}

CHANNEL_BRANDS = [
    "千千進食中", "Chienseating", "chienseating",
    "水水作伙move", "HowHowEat", "howhoweat",
]
BRAND_FRAGMENTS = ["進食", "食中", "進食中", "水水", "作伙"]
COLLAB_NAMES = [
    "蔡阿嘎", "阿嘎", "蔡昌憲", "黃大謙", "大謙",
    "阿滴", "滴妹", "聖結石", "這群人", "上班不要看",
    "古娃娃", "愛莉莎莎", "小玉", "林進", "放火",
]

# ===== 情緒分析（與 app.py 一致的混合校正版）=====
def get_sentiment_score(text):
    t = str(text)
    if HAS_SNOWNLP:
        try:
            raw = SnowNLP(t).sentiments
        except:
            raw = 0.5
    else:
        raw = 0.5

    x = (raw - 0.5) * 6
    calibrated = 1 / (1 + math.exp(-x * 0.45))

    yt_engagement = {
        '挑戰': 0.04, '地獄': 0.04, '傷害': 0.03, '暗黑': 0.03,
        '恐怖': 0.03, '崩潰': 0.03, '超級': 0.02, '終極': 0.02,
        '史上': 0.02, '第一次': 0.02, '居然': 0.02, '竟然': 0.02,
        '瘋狂': 0.03, '爆': 0.02, '狂': 0.02, '嚇': 0.02,
    }
    positive_food = {
        '好吃': 0.06, '超好吃': 0.08, '美味': 0.06, '推薦': 0.05,
        '必吃': 0.06, '最愛': 0.05, '幸福': 0.05, '天堂': 0.05,
        '銷魂': 0.06, '豪華': 0.04, '頂級': 0.04, '夢幻': 0.04,
        '完美': 0.04, '驚喜': 0.04, '超讚': 0.06, '神級': 0.06,
    }
    negative_food = {
        '難吃': -0.08, '踩雷': -0.07, '失望': -0.06, '後悔': -0.06,
        '踩坑': -0.06, '噁心': -0.07, '最差': -0.06, '雷': -0.04,
    }

    adj = 0.0
    for word, delta in {**yt_engagement, **positive_food, **negative_food}.items():
        if word in t:
            adj += delta

    excl = t.count('！') + t.count('!')
    adj += min(excl * 0.015, 0.05)

    final = calibrated + adj
    return round(max(0.08, min(0.92, final)), 4)


def train_v8():
    print("🚀 啟動 V8 CatBoost 訓練（情緒特徵 + 關鍵字命中數 + 標題結構）...")

    if os.path.exists(DICT_PATH):
        jieba.load_userdict(DICT_PATH)
        print(f"📖 已載入自定義辭典: {DICT_PATH}")

    # 1. 資料讀取
    df = pd.read_excel(DATA_PATH)
    df = df[df['view_count'] > 100].dropna(subset=['title', 'kol_name']).reset_index(drop=True)

    kol_base_stats = df.groupby('kol_name')['view_count'].median().to_dict()
    df['base_log'] = df['kol_name'].map(kol_base_stats).apply(np.log1p)
    joblib.dump(kol_base_stats, os.path.join(MODEL_DIR, 'kol_base_stats.pkl'))
    print(f"📊 KOL 基數: {kol_base_stats}")

    # 2. 排除詞集
    kol_names = df['kol_name'].unique().tolist()
    exclude_words = set(STOP_WORDS)
    exclude_words.update(kol_names)
    exclude_words.update(w.lower() for w in CHANNEL_BRANDS)
    exclude_words.update(w.lower() for w in BRAND_FRAGMENTS)
    exclude_words.update(w.lower() for w in COLLAB_NAMES)
    for brand in CHANNEL_BRANDS:
        for seg in jieba.lcut(brand.lower()):
            if len(seg) > 1:
                exclude_words.add(seg)

    print(f"🚫 排除詞集 ({len(exclude_words)} 個)")
    joblib.dump(exclude_words, os.path.join(MODEL_DIR, 'exclude_words.pkl'))

    # 3. 標題清洗
    def clean_text(text):
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', str(text)).lower()
        words = jieba.lcut(text)
        return " ".join([w for w in words if len(w) > 1 and w not in exclude_words])

    df['clean_title'] = df['title'].apply(clean_text)

    # 4. TF-IDF 特徵
    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    X_tfidf = vectorizer.fit_transform(df['clean_title']).toarray()
    tfidf_cols = [f"feat_{w}" for w in vectorizer.get_feature_names_out()]
    X_df = pd.DataFrame(X_tfidf, columns=tfidf_cols)

    # ===== V8 新增特徵 =====
    print("\n🆕 計算 V8 新增特徵...")

    # 5a. 情緒分數 — 讓模型學習「不同 KOL 的情緒-觀看數關係」
    print("  → 計算標題情緒分數...")
    df['sentiment_score'] = df['title'].apply(get_sentiment_score)
    X_df['sentiment_score'] = df['sentiment_score'].values
    print(f"    平均情緒: {df['sentiment_score'].mean():.3f}, 標準差: {df['sentiment_score'].std():.3f}")

    # 5b. 關鍵字命中數 — 修復 TF-IDF L2 稀釋問題
    keyword_hits = (X_tfidf > 0).sum(axis=1)
    X_df['keyword_hit_count'] = keyword_hits
    print(f"    平均關鍵字命中: {keyword_hits.mean():.1f}")

    # 5c. 標題長度
    df['title_length'] = df['title'].str.len()
    X_df['title_length'] = df['title_length'].values
    print(f"    平均標題長度: {df['title_length'].mean():.1f} 字")

    # 5d. 是否含數字（如 100、TOP5）
    X_df['has_number'] = df['title'].str.contains(r'\d+', regex=True).astype(int).values

    # 5e. 驚嘆號數量
    X_df['exclamation_count'] = (df['title'].str.count('！') + df['title'].str.count('!')).values

    # 6. 類別 + 基數特徵
    X_df['base_performance_log'] = df['base_log'].values
    X_df['kol_name'] = df['kol_name'].values
    X_df['strategic_tag'] = df['strategic_tag'].values

    cat_feature_indices = [X_df.columns.get_loc('kol_name'), X_df.columns.get_loc('strategic_tag')]

    y = np.log1p(df['view_count'])

    # 7. 訓練 CatBoost
    X_train, X_test, y_train, y_test = train_test_split(X_df, y, test_size=0.2, random_state=42)

    model = CatBoostRegressor(
        iterations=1200,
        learning_rate=0.04,
        depth=7,
        cat_features=cat_feature_indices,
        l2_leaf_reg=5,
        verbose=100,
        random_seed=42,
    )
    model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=80)

    train_r2 = model.score(X_train, y_train)
    test_r2 = model.score(X_test, y_test)
    print(f"\n📈 訓練集 Log-R²: {train_r2:.4f}")
    print(f"📈 測試集 Log-R²: {test_r2:.4f}")

    # 8. 特徵重要性排行
    importances = model.get_feature_importance()
    feat_importance = pd.Series(importances, index=X_df.columns).sort_values(ascending=False)

    print("\n🏆 V8 完整特徵影響力排行 (Top 25):")
    print("-" * 55)
    for i, (name, score) in enumerate(feat_importance.head(25).items(), 1):
        label = name.replace('feat_', '') if name.startswith('feat_') else f"[{name}]"
        print(f"  {i:2d}. {label:<20s} {score:.2f}")

    # V8 新增特徵的權重
    print(f"\n📊 === V8 新增特徵權重 ===")
    for feat_name in ['sentiment_score', 'keyword_hit_count', 'title_length', 'has_number', 'exclamation_count']:
        print(f"  {feat_name:<22s}: {feat_importance.get(feat_name, 0):.2f}")
    print(f"\n📊 KOL 身份: {feat_importance.get('kol_name', 0):.2f}")
    print(f"📊 策略標籤: {feat_importance.get('strategic_tag', 0):.2f}")
    print(f"📊 流量基數: {feat_importance.get('base_performance_log', 0):.2f}")

    # 9. 儲存 V8 模型
    model.save_model(os.path.join(MODEL_DIR, 'view_predictor_v8.cbm'))
    joblib.dump(vectorizer, os.path.join(MODEL_DIR, 'vectorizer.pkl'))
    joblib.dump(X_df.columns.tolist(), os.path.join(MODEL_DIR, 'model_columns.pkl'))
    joblib.dump(kol_names, os.path.join(MODEL_DIR, 'kol_list.pkl'))

    # 儲存結果摘要
    summary = f"""V8 CatBoost 訓練結果
====================
訓練集 R²: {train_r2:.4f}
測試集 R²: {test_r2:.4f}

新增特徵:
  sentiment_score:    {feat_importance.get('sentiment_score', 0):.2f}
  keyword_hit_count:  {feat_importance.get('keyword_hit_count', 0):.2f}
  title_length:       {feat_importance.get('title_length', 0):.2f}
  has_number:         {feat_importance.get('has_number', 0):.2f}
  exclamation_count:  {feat_importance.get('exclamation_count', 0):.2f}

系統特徵:
  kol_name:           {feat_importance.get('kol_name', 0):.2f}
  strategic_tag:      {feat_importance.get('strategic_tag', 0):.2f}
  base_performance:   {feat_importance.get('base_performance_log', 0):.2f}
"""
    with open(os.path.join(MODEL_DIR, 'v8_results.txt'), 'w', encoding='utf-8') as f:
        f.write(summary)

    print(f"\n✅ V8 訓練完成！模型已儲存至 view_predictor_v8.cbm")


if __name__ == "__main__":
    train_v8()
