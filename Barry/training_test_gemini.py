from google import genai
from google.genai import types
from youtuber_info import Chienseating, HowHowEat
import mysql.connector
import json, os, dotenv
import time

dotenv.load_dotenv()

# 初始化 Gemini Client
client = genai.Client()

def generate_tags_in_batches(channel_id, batch_size=30, output_file='./Barry/video_tags_result.json'):
    db = mysql.connector.connect(
        host='dv108.aiturn.fun',
        user='barry',
        password=os.getenv('KOL_DB_PW'),
        database='db_kol'
    )
    cursor = db.cursor(dictionary=True)
    # cursor.execute('SELECT video_id, title, description FROM videos WHERE channel_id = %s LIMIT %s', (channel_id, limit))
    cursor.execute('SELECT video_id, title, description FROM videos WHERE channel_id = %s', (channel_id,))
    videos = cursor.fetchall()
    db.close()

    all_videos_tags = []
    print(f"總共 {len(videos)} 筆影片，每批次處理 {batch_size} 筆...")
    for i in range(0, len(videos), batch_size):
        batch = videos[i:i+batch_size]
        print(f"正在處理第 {i + 1} 到 {i + len(batch)} 筆...")
        prompt = "你是一個專業的 YouTube 內容標籤分類員。請閱讀以下影片資料，為每部影片產生 5-8 個標籤。\n\n"
        for v in batch:
            # 說明欄一樣取前段即可，節省 Token 與避免雜訊
            desc = v['description'][:150] if v['description'] else ''
            prompt += f"影片ID: {v['video_id']}\n標題: {v['title']}\n說明: {desc}\n---\n"
        prompt += """
        規則：標籤必須是標準化的名詞（例如：拉麵、大胃王、日本），不要動詞與形容詞。
        請直接回傳純 JSON 陣列格式，不要包含任何 Markdown 標記，格式如下：
        [
            {"video_id": "ID1", "tags": ["標籤A", "標籤B"]},
            {"video_id": "ID2", "tags": ["標籤C", "標籤D"]}
        ]
        """
        try:
            # 呼叫 Gemini API
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                )
            )
            # --- 關鍵防呆：清理潛在的 Markdown 標記 ---
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            # 解析這批次的 JSON
            batch_result = json.loads(raw_text)
            # 將這批結果「擴充」進總容器中 (注意這裡是 extend 不是 append)
            all_videos_tags.extend(batch_result)
            print("✅ 本批次處理成功！")
            time.sleep(10)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗，這批次的原始回傳為：\n{raw_text}")
        except Exception as e:
            print(f"❌ 發生錯誤：{str(e)}")

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        json.dump(all_videos_tags, f, ensure_ascii=False, indent=4)
        
    print(f"\n🎉 執行完畢！結果已儲存至 {output_file}")


if __name__ == '__main__':
    generate_tags_in_batches(Chienseating().channel_id)



