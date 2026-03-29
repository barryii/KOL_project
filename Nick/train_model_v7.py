import pandas as pd
import numpy as np
import jieba
import re
import joblib
import os
from catboost import CatBoostRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

# 設定路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR) if "models" in BASE_DIR else BASE_DIR
DATA_PATH = os.path.join(PROJECT_ROOT, 'reports', 'combined_kol_cleaned_data.xlsx')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')
DICT_PATH = os.path.join(PROJECT_ROOT, 'dict.txt')

# ===== 停用詞表（虛詞、語氣詞、無內容意義的常見詞）=====
STOP_WORDS = {
    # 虛詞 / 介詞 / 連接詞
    '的', '了', '在', '與', '和', '是', '就', '都', '而', '及', '著', '或', '之',
    '也', '又', '不', '很', '太', '到', '去', '來', '會', '能', '要', '讓', '把',
    '被', '從', '給', '用', '向', '對', '為', '以', '因', '但', '還', '已', '再',
    # 常見口語 / 無意義動詞片語
    '起來', '就是', '自己', '一起', '真的', '什麼', '一個', '一次', '一口',
    '好不好', '感覺', '覺得', '一樣', '一般', '一直', '一下', '竟然', '結果',
    '原來', '特別', '多少', '如果', '只要', '怎麼', '這個', '那個', '可以',
    '沒有', '不是', '開始', '出來', '回去', '以上', '以下', '之前', '之後',
    '應該', '其實', '大家', '全部', '終於', '居然', '完全', '到底', '為什麼',
    '這樣', '那樣', '好像', '看起來', '還是', '分鐘', '小時', '而且', '不過',
    '所以', '因為', '雖然', '或是', '雖然', '然後', '接著', '最後', '首先',
    '第一', '今天', '明天', '昨天', '這次', '每次', '那次', '知道', '發現',
    '告訴', '他們', '我們', '你們', '它們', '大概', '差不多', '幾乎', '簡直',
    # 影片標題常用但無內容實質的詞
    '影片', '挑戰', '直播', '開箱', '實測', '體驗',
    'ft', 'ep', 'vs', 'feat', 'part', 'vlog',
}

# ===== 頻道品牌詞 + 手動指定碎片 =====
# (dict.txt 會讓 jieba 把品牌詞當整體，無法自動拆解出碎片，所以要手動列出)
CHANNEL_BRANDS = [
    "千千進食中", "Chienseating", "chienseating",
    "水水作伙move",
    "HowHowEat", "howhoweat",
]
BRAND_FRAGMENTS = [
    "進食", "食中", "進食中",   # 千千進食中 的碎片
    "水水", "作伙",             # 水水作伙move 的碎片
]

# ===== 合作者 / 其他 YouTuber 人名 =====
# (出現在合作影片標題中，屬於人格特徵而非內容特徵)
COLLAB_NAMES = [
    "蔡阿嘎", "阿嘎", "蔡昌憲",
    "黃大謙", "大謙",
    "阿滴", "滴妹",
    "聖結石", "這群人", "上班不要看",
    "古娃娃", "愛莉莎莎", "小玉",
    "林進", "放火",
]

def train_v7():
    print("🚀 啟動 V7 CatBoost 訓練（去人格化 + 原生類別特徵）...")
    
    # 載入自定義辭典（確保分詞一致）
    if os.path.exists(DICT_PATH):
        jieba.load_userdict(DICT_PATH)
        print(f"📖 已載入自定義辭典: {DICT_PATH}")
    
    # 1. 資料讀取與預處理
    df = pd.read_excel(DATA_PATH)
    df = df[df['view_count'] > 100].dropna(subset=['title', 'kol_name']).reset_index(drop=True)
    
    # 計算 KOL 流量基數
    kol_base_stats = df.groupby('kol_name')['view_count'].median().to_dict()
    df['base_log'] = df['kol_name'].map(kol_base_stats).apply(np.log1p)
    joblib.dump(kol_base_stats, os.path.join(MODEL_DIR, 'kol_base_stats.pkl'))
    print(f"📊 KOL 基數: {kol_base_stats}")

    # 2. 建立完整排除詞集：停用詞 + KOL 名 + 品牌詞 + 品牌碎片 + 合作者人名
    kol_names = df['kol_name'].unique().tolist()
    exclude_words = set(STOP_WORDS)
    exclude_words.update(kol_names)
    exclude_words.update(w.lower() for w in CHANNEL_BRANDS)
    exclude_words.update(w.lower() for w in BRAND_FRAGMENTS)
    exclude_words.update(w.lower() for w in COLLAB_NAMES)
    # 也嘗試 jieba 拆解品牌詞（以防萬一）
    for brand in CHANNEL_BRANDS:
        for seg in jieba.lcut(brand.lower()):
            if len(seg) > 1:
                exclude_words.add(seg)
    
    print(f"🚫 排除詞集 ({len(exclude_words)} 個)")
    joblib.dump(exclude_words, os.path.join(MODEL_DIR, 'exclude_words.pkl'))
    
    # 3. 標題清洗（去人格化：移除所有 KOL 身份標記）
    def clean_text(text):
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', str(text)).lower()
        words = jieba.lcut(text)
        return " ".join([w for w in words if len(w) > 1 and w not in exclude_words])
    
    df['clean_title'] = df['title'].apply(clean_text)

    # 4. TF-IDF 特徵提取
    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    X_tfidf = vectorizer.fit_transform(df['clean_title']).toarray()
    tfidf_cols = [f"feat_{w}" for w in vectorizer.get_feature_names_out()]
    X_df = pd.DataFrame(X_tfidf, columns=tfidf_cols)
    
    # 5. 組合特徵矩陣
    # CatBoost 原生支援類別特徵，不需要 one-hot
    X_df['base_performance_log'] = df['base_log'].values
    X_df['kol_name'] = df['kol_name'].values
    X_df['strategic_tag'] = df['strategic_tag'].values
    
    # 記錄類別特徵的欄位索引（CatBoost 需要）
    cat_feature_indices = [X_df.columns.get_loc('kol_name'), X_df.columns.get_loc('strategic_tag')]
    
    y = np.log1p(df['view_count'])
    
    # 6. 訓練 CatBoost
    X_train, X_test, y_train, y_test = train_test_split(X_df, y, test_size=0.2, random_state=42)
    
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        cat_features=cat_feature_indices,
        verbose=100,  # 每 100 輪印一次進度
        random_seed=42,
    )
    model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=50)
    
    train_r2 = model.score(X_train, y_train)
    test_r2 = model.score(X_test, y_test)
    print(f"\n📈 訓練集 Log-R²: {train_r2:.4f}")
    print(f"📈 測試集 Log-R²: {test_r2:.4f}")
    
    # 7. 印出去人格化後的關鍵字重要性排行（純內容特徵）
    importances = model.get_feature_importance()
    feat_importance = pd.Series(importances, index=X_df.columns).sort_values(ascending=False)
    
    print("\n🏆 去人格化關鍵字影響力排行 (Top 20):")
    print("-" * 50)
    content_feats = [(name, score) for name, score in feat_importance.items() 
                     if name.startswith('feat_')]
    for i, (name, score) in enumerate(content_feats[:20], 1):
        keyword = name.replace('feat_', '')
        print(f"  {i:2d}. {keyword:<15s} {score:.2f}")
    
    print(f"\n📊 KOL 身份特徵權重: {feat_importance.get('kol_name', 0):.2f}")
    print(f"📊 策略標籤特徵權重: {feat_importance.get('strategic_tag', 0):.2f}")
    print(f"📊 流量基數特徵權重: {feat_importance.get('base_performance_log', 0):.2f}")
    
    # 8. 儲存模型組件
    model.save_model(os.path.join(MODEL_DIR, 'view_predictor_v7.cbm'))
    joblib.dump(vectorizer, os.path.join(MODEL_DIR, 'vectorizer.pkl'))
    joblib.dump(X_df.columns.tolist(), os.path.join(MODEL_DIR, 'model_columns.pkl'))
    joblib.dump(kol_names, os.path.join(MODEL_DIR, 'kol_list.pkl'))

    print(f"\n✅ V7 訓練完成！模型已儲存。")

if __name__ == "__main__":
    train_v7()