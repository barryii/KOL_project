import os
import pandas as pd
import jieba
from collections import Counter
from sqlalchemy import create_engine
from dotenv import load_dotenv
import re

# 1. 環境設定
load_dotenv()
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
engine = create_engine(f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

# 2. 初始化辭典
if os.path.exists("dict.txt"):
    jieba.load_userdict("dict.txt")
    print("✅ 成功載入自定義辭典")

STOP_WORDS = {'的', '了', '在', '與', '和', '是', '就', '都', '而', '及', '著', '或', '之', '影片', '挑戰', 'ft', 'Ep', 'ep', '真的', '什麼', '一個', '一次','一口', '一起', '好不好', '自己', '真的', '感覺', '覺得', '什麼', 
    '一樣', '一次', '一個', '一般', '一直', '一下', '竟然', '結果', 
    '原來', '特別', '豪想', '項清', '多少', '如果', '只要', '分鐘'}

def process_kol_data(target_name, channel_id):
    print(f"\n🚀 正在處理 KOL: 【{target_name}】")
    df = pd.read_sql(f"SELECT * FROM videos WHERE channel_id = '{channel_id}'", engine)
    if df.empty: return None

    df['kol_name'] = target_name
    df['clean_title'] = df['title'].str.replace(r'[【】!#]', '', regex=True).str.strip()

    # --- 第一階段：原始分詞統計 ---
    all_words = []
    for title in df['clean_title']:
        clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', '', str(title)).lower()
        words = [w for w in jieba.lcut(clean_text) if len(w) >= 2 and w not in STOP_WORDS]
        all_words.extend(words)

    raw_counts = Counter(all_words)
    
    # --- 第二階段：自動剔除冗餘碎詞 (核心邏輯) ---
    # 按照長度從長到短排序，長詞優先保留
    sorted_vocab = sorted(raw_counts.items(), key=lambda x: len(x[0]), reverse=True)
    final_vocab = {}

    for word, count in sorted_vocab:
        is_redundant = False
        # 檢查當前詞是否為已存長詞的子字串
        for existing_word in final_vocab.keys():
            # 判斷標準：如果是子字串且出現頻率跟長詞非常接近 (容許 20% 誤差)
            if word in existing_word and count <= (final_vocab[existing_word] * 1.2):
                is_redundant = True
                break
        
        if not is_redundant:
            final_vocab[word] = count

    # --- 第三階段：計算特徵影響力 (選出最強 Top 20) ---
    word_impact = []
    candidates = sorted(final_vocab.items(), key=lambda x: x[1], reverse=True)[:60]
    
    for word, _ in candidates:
        # 如果是 2 字詞，但看起來像口語 (可以手動定義或靠 STOP_WORDS)
        if len(word) < 3 and word in STOP_WORDS:
            continue
            
        mask = df['clean_title'].str.lower().str.contains(word.lower(), na=False)
        if mask.sum() >= 2:
            avg_v = df[mask]['view_count'].mean()
            word_impact.append({'word': word, 'avg_v': avg_v})
    
    # 最終選出 20 個特徵
    temp_df = pd.DataFrame(word_impact).sort_values('avg_v', ascending=False)
    top_features = temp_df.drop_duplicates('word').head(20)['word'].tolist()

    print(f"✨ {target_name} 自動優化特徵: {', '.join(top_features)}")

    # --- 第四階段：寫入特徵位 ---
    for word in top_features:
        safe_col = f"feat_{re.sub(r'\W+', '', word)}"
        df[safe_col] = df['clean_title'].str.contains(word, na=False, case=False).astype(int)

    # 基礎分類標籤
    df['strategic_tag'] = df.apply(lambda r: 'Shorts' if r['type']=='shorts' else ('Long' if r['duration_sec']>480 else 'Mid'), axis=1)
    
    return df

def run_sync_cleaning():
    kol_list = [{"name": "豪豪", "id": "UCa2YiSXNTkmOA-QTKdzzbSQ"}, {"name": "千千", "id": "UC9i2Qgd5lizhVgJrdnxunKw"}]
    
    final_dfs = []
    for kol in kol_list:
        res = process_kol_data(kol["name"], kol["id"])
        if res is not None: final_dfs.append(res)

    if not final_dfs: return
    
    # 合併並補 0 (解決不同 KOL 特徵不對稱問題)
    full_df = pd.concat(final_dfs, axis=0, ignore_index=True).fillna(0)

    # 儲存
    try:
        full_df.to_sql('video_cleaned', engine, if_exists='replace', index=False, chunksize=500)
        print(f"\n📊 處理完畢！總筆數: {len(full_df)}，總欄位: {len(full_df.columns)}")
        
        if not os.path.exists('reports'): os.makedirs('reports')
        full_df.to_excel("reports/combined_kol_cleaned_data.xlsx", index=False)
        print(f"📄 Excel 報表已更新。")
    except Exception as e:
        print(f"❌ 寫入失敗: {e}")

if __name__ == "__main__":
    run_sync_cleaning()
