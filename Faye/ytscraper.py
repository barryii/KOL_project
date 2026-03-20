# 千千 Channel ID:UC9i2Qgd5lizhVgJrdnxunKw
# 需先安裝：pip install google-api-python-client
from googleapiclient.discovery import build
import json

# 設定你的 API Key
API_KEY = '你的_API_KEY_貼在這裡'

def get_channel_videos(handle):
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    # 第一步：透過 Handle 找到頻道資訊
    ch_request = youtube.channels().list(
        part="contentDetails,snippet",
        forHandle=handle
    )
    ch_response = ch_request.execute()

    if not ch_response['items']:
        print("找不到該頻道")
        return

    # 取得「所有上傳影片」的播放清單 ID (這比 search 接口省點數)
    upload_id = ch_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    channel_title = ch_response['items'][0]['snippet']['title']
    
    print(f"正在爬取頻道: {channel_title}")

    # 第二步：分頁抓取影片清單
    all_videos = []
    next_page_token = None

    while True:
        pl_request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=upload_id,
            maxResults=50, # 每次最多抓 50 筆
            pageToken=next_page_token
        )
        pl_response = pl_request.execute()

        for item in pl_response['items']:
            video_data = {
                'title': item['snippet']['title'],
                'video_id': item['contentDetails']['videoId'],
                'published_at': item['snippet']['publishedAt'],
                'thumbnail': item['snippet']['thumbnails']['high']['url']
            }
            all_videos.append(video_data)

        # 檢查是否有下一頁
        next_page_token = pl_response.get('nextPageToken')
        if not next_page_token:
            break

    return all_videos

# 執行
video_list = get_channel_videos('@Chienseating')

# 輸出結果範例
for v in video_list[:5]: # 只印出前 5 筆
    print(f"[{v['published_at']}] {v['title']} - https://www.youtube.com/watch?v={v['video_id']}")
