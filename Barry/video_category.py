from keybert import KeyBERT
from youtuber_info import Chienseating, HowHowEat
import jieba
import mysql.connector
import re, os, dotenv

dotenv.load_dotenv()

# 1. 初始化 KeyBERT 多語言模型 (初次執行會下載約 400MB 的模型)
kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')

# 2. 針對你的 KOL 專案，強制加入一些不該被切斷的專有名詞
word_list = ['大胃王', '吃到飽', '開箱', '葉配']
for words in word_list:
    jieba.add_word(words)

def clean_text(text):
    if not text:
        return ""
    # 去除網址與常見的社群雜訊
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'(facebook|instagram|ig|fb|youtube|訂閱|按讚|分享|千千|豪豪|google)', '', text, flags=re.IGNORECASE)
    return text

def extract_video_tags(channel_id, limit=5):
    # 連線到資料庫
    db = mysql.connector.connect(
        host='dv108.aiturn.fun',
        user='barry',
        password=os.getenv('KOL_DB_PW'),
        database='db_kol'
    )
    cursor = db.cursor(dictionary=True)
    
    # 撈取測試用的影片 (先抓 5 筆測試效果)
    cursor.execute("SELECT video_id, title, description FROM videos WHERE channel_id = %s LIMIT %s", (channel_id, limit))
    videos = cursor.fetchall()
    
    for v in videos:
        # 3. 組合文字 (標題放兩次增加權重，說明欄只取前 150 字避免雜訊)
        title = clean_text(v['title'])
        raw_text = f"{title} {title} {clean_text(v['description'])[:150]}"
        raw_text = f"{title} {title} {clean_text(v['description'])}"
        
        # 4. 關鍵步驟：使用 jieba 斷詞並用空白連接
        # 過濾掉長度只有 1 的單字 (如：的、了、是)
        seg_list = [word for word in jieba.cut(raw_text) if len(word) > 1]
        spaced_text = " ".join(seg_list)
        
        # 5. 使用 KeyBERT 提取標籤
        # keyphrase_ngram_range=(1, 2) 代表允許單詞 (大胃王) 或雙詞組合 (大胃王 挑戰)
        # top_n=5 代表抓取分數最高的前 5 個標籤
        keywords = kw_model.extract_keywords(
            spaced_text, 
            keyphrase_ngram_range=(1, 1), 
            stop_words=None, 
            top_n=5,
            use_mmr=True,      # 開啟 MMR 多樣性過濾
            # diversity=0.7      # 多樣性程度 (0.0 到 1.0，數值越高標籤差異越大)
        )
        
        # keywords 的格式會是 [('大胃王', 0.85), ('拉麵', 0.72), ...]
        # 我們只需要文字部分
        tags = [kw[0] for kw in keywords]
        
        print(f"影片標題: {v['title']}")
        print(f"提取標籤: {tags}\n")
        print("-" * 40)
        
    db.close()

if __name__ == "__main__":
    extract_video_tags(Chienseating().channel_id, limit=5)