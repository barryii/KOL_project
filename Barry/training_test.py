from google import genai
import json
import os, dotenv

dotenv.load_dotenv()

# 1. 初始化 Client
client = genai.Client()

# for m in client.models.list():
#     print(f"Model Name: {m.name}, Supported Methods: {m.supported_actions}")

def batch_classify_with_new_sdk(video_list):
    # 建立 Prompt (邏輯與之前相同)
    titles_str = "\n".join([f"{v['id']}: {v['title']}" for v in video_list])
    
    prompt = f"請將以下影片標題分類：\n{titles_str}\n請回傳 JSON 格式。"

    # 2. 呼叫生成模型 (最新 SDK 語法)
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config={
            'response_mime_type': 'application/json'
        }
    )
    
    return json.loads(response.text)

# 測試用資料
test_videos = [{"id": "v1", "title": "挑戰100支炸雞腿"}]
print(batch_classify_with_new_sdk(test_videos))

# from google import genai
# import os, dotenv

# dotenv.load_dotenv()

# # The client gets the API key from the environment variable `GEMINI_API_KEY`.
# client = genai.Client()

# response = client.models.generate_content(
#     model="gemini-3-flash-preview", contents="Explain how AI works in a few words"
# )
# print(response.text)