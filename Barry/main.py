from googleapiclient.discovery import build
import os, dotenv
import csv

dotenv.load_dotenv()

# https://developers.google.com/youtube/v3/docs

YT_API_KEY = os.getenv('YT_API_KEY')
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

Chienseating_channel_id = 'UC9i2Qgd5lizhVgJrdnxunKw' # 千千
HowHowEat_channel_id = 'UCa2YiSXNTkmOA-QTKdzzbSQ' # 豪豪

Chienseating_playlist_id = 'UU' + Chienseating_channel_id[2:]
HowHowEat_playlist_id = 'UU' + HowHowEat_channel_id[2:]
Chienseating_shorts_playlist_id = 'UUSH' + Chienseating_channel_id[2:]
HowHowEat_shorts_playlist_id = 'UUSH' + HowHowEat_channel_id[2:]
Chienseating_stream_playlist_id = 'UULV' + Chienseating_channel_id[2:]
HowHowEat_stream_playlist_id = 'UULV' + HowHowEat_channel_id[2:]

part = 'snippet'
videos = {}
next_page_token = None

# 抓所有影片
while True:
	request = youtube.playlistItems().list(
		part=part,
		playlistId=Chienseating_playlist_id,
		maxResults=50, # 最大50
		pageToken=next_page_token
	)
	response = request.execute()
	playlist: list = response['items']
	playlist.reverse()
	
	for item in playlist:
		snippet = item[part]
		title = snippet['title']
		description = snippet['description']
		video_id = snippet['resourceId']['videoId']
		published_at = snippet['publishedAt']
		videos[video_id] = {'title': title, 'description': description, 'published_at': published_at}

	next_page_token = response.get('nextPageToken')
	print(next_page_token)
	if not next_page_token:
		break

# 抓短片
while True:
	request = youtube.playlistItems().list(
		part=part,
		playlistId=Chienseating_shorts_playlist_id,
		maxResults=50, # 最大50
		pageToken=next_page_token
	)
	response = request.execute()
	playlist: list = response['items']
	playlist.reverse()
	
	for item in playlist:
		snippet = item[part]
		video_id = snippet['resourceId']['videoId']
		if video_id in videos:
			videos[video_id]['type'] = 'shorts'
		else: print(f'{video_id} not in videos')

	next_page_token = response.get('nextPageToken')
	print(next_page_token)
	if not next_page_token:
		break

# 抓直播
while True:
	request = youtube.playlistItems().list(
		part=part,
		playlistId=Chienseating_stream_playlist_id,
		maxResults=50, # 最大50
		pageToken=next_page_token
	)
	response = request.execute()
	playlist: list = response['items']
	playlist.reverse()
	
	for item in playlist:
		snippet = item[part]
		video_id = snippet['resourceId']['videoId']
		if video_id in videos:
			videos[video_id]['type'] = 'stream'
		else: print(f'{video_id} not in videos')
		
	next_page_token = response.get('nextPageToken')
	print(next_page_token)
	if not next_page_token:
		break

for video_id in videos:
	if not videos[video_id].get('type'):
		videos[video_id]['type'] = 'video'

# print(videos)

with open('Chienseating.csv', 'w', newline='', encoding='utf-8-sig') as f:
	# 定義欄位名稱
	fieldnames = ['video_id', 'title', 'description', 'published_at', 'type']
	writer = csv.DictWriter(f, fieldnames=fieldnames)

	# 寫入標題列
	writer.writeheader()
	sorted_items = sorted(videos.items(), key=lambda x: x[1]['published_at'])
	
	# 寫入內容
	for v_id, info in sorted_items:
		row = {'video_id': v_id}
		row.update(info)
		writer.writerow(row)









