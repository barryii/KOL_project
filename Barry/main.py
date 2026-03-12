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
	
	video_id_list = []
	for item in playlist:
		snippet = item[part]
		title = snippet['title']
		description = snippet['description']
		video_id = snippet['resourceId']['videoId']
		video_id_list.append(video_id)
		published_at = snippet['publishedAt']
		videos[video_id] = {'title': title, 'description': description, 'publishedAt': published_at, 'stats': {}}

	part2 = 'statistics'
	stats_request = youtube.videos().list(part=part2, id=video_id_list)
	stats_response = stats_request.execute()
	items = stats_response['items']
	for item in items:
		video_id = item['id']
		videos[video_id]['stats']['viewCount'] = item[part2]['viewCount']
		videos[video_id]['stats']['likeCount'] = item[part2]['likeCount']
		videos[video_id]['stats']['commentCount'] = item[part2]['commentCount']

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

print(len(videos))

fieldnames = ['video_id', 'title', 'description', 'publishedAt', 'type', 'likeCount', 'viewCount', 'commentCount']
with open('Chienseating.csv', 'w', newline='', encoding='utf-8-sig') as f:
	# 定義欄位名稱
	writer = csv.DictWriter(f, fieldnames=fieldnames)

	# 寫入標題列
	writer.writeheader()
	videos = sorted(videos.items(), key=lambda x: x[1]['publishedAt'])
	
	# 寫入內容
	for video_id, info in videos:
		# 建立一個基礎的 row
		row = {
			'video_id': video_id,
			'title': info['title'],
			'description': info['description'],
			'publishedAt': info['publishedAt'],
			'type': info['type']
		}
		
		# 2. 將 stats 字典裡的內容「扁平化」移到 row 這一層
		stats = info['stats']
		row['viewCount'] = stats['viewCount']
		row['likeCount'] = stats['likeCount']
		row['commentCount'] = stats['commentCount']
		
		writer.writerow(row)









