from googleapiclient.discovery import build
from enum import Enum, auto
import os, dotenv
import csv
import isodate

dotenv.load_dotenv()

# https://developers.google.com/youtube/v3/docs

YT_API_KEY = os.getenv('YT_API_KEY')
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

class Chienseating:
	@property
	def channel_name(self) -> str:
		return 'Chienseating'
	@property
	def channel_id(self) -> str:
		return 'UC9i2Qgd5lizhVgJrdnxunKw'
	@property
	def playlist_id(self) -> str:
		return 'UU' + self.channel_id[2:]
	@property
	def playlist_id_shorts(self) -> str:
		return 'UUSH' + self.channel_id[2:]
	@property
	def playlist_id_stream(self) -> str:
		return 'UULV' + self.channel_id[2:]

class HowHowEat:
	@property
	def channel_name(self) -> str:
		return 'HowHowEat'
	@property
	def channel_id(self) -> str:
		return 'UCa2YiSXNTkmOA-QTKdzzbSQ'
	@property
	def playlist_id(self) -> str:
		return 'UU' + self.channel_id[2:]
	@property
	def playlist_id_shorts(self) -> str:
		return 'UUSH' + self.channel_id[2:]
	@property
	def playlist_id_stream(self) -> str:
		return 'UULV' + self.channel_id[2:]

class VideoType(Enum):
	video = auto()
	shorts = auto()
	stream = auto()

class KOL:
	def __init__(self, channel: Chienseating | HowHowEat):
		self.part = 'snippet'
		self.videos = {}
		self.next_page_token = None
		self.channel = channel # 傳入class

	def get_playlist(self, part: str, playlist_id: str, next_page_token: str | None) -> tuple[dict, list]:
		request = youtube.playlistItems().list(
			part=part,
			playlistId=playlist_id,
			maxResults=50, # 最大50
			pageToken=next_page_token
		)
		response = request.execute()
		playlist: list = response['items']
		playlist.reverse()
		return response, playlist

	def video_type(self, part: str, playlist: list, videos: dict, type: VideoType) -> None:
		for item in playlist:
			snippet = item[part]
			video_id = snippet['resourceId']['videoId']
			if video_id in videos:
				videos[video_id]['type'] = type.name
			else: print(f'{video_id} not in videos')

	def get_all_videos(self) -> None:
		"""
		video_id: {
			title: str,
			description: str,
			published_at: datetime,
			type: str,
			duration: datetime,
			duration_sec: int,
			stats: {
				like_count: int,
				view_count: int,
				comment_count: int
			}
		}
		"""
		# 抓所有影片
		while True:
			response, playlist = self.get_playlist(self.part, self.channel.playlist_id, self.next_page_token)
			
			video_id_list = []
			for item in playlist:
				snippet = item[self.part]
				title = snippet['title']
				description = snippet['description']
				video_id = snippet['resourceId']['videoId']
				video_id_list.append(video_id)
				published_at = snippet['publishedAt']
				self.videos[video_id] = {
					'title': title, 
					'description': description, 
					'published_at': published_at, 
					'stats': {}
				}

			part2 = 'statistics,contentDetails'
			statistics = 'statistics'
			contentDetails = 'contentDetails'
			stats_request = youtube.videos().list(part=part2, id=video_id_list)
			stats_response = stats_request.execute()
			items = stats_response['items']
			for item in items:
				video_id = item['id']
				self.videos[video_id]['stats']['view_count'] = item[statistics]['viewCount']
				self.videos[video_id]['stats']['like_count'] = item[statistics]['likeCount']
				self.videos[video_id]['stats']['comment_count'] = item[statistics]['commentCount']
				duration = item[contentDetails]['duration']
				duration = isodate.parse_duration(duration)
				self.videos[video_id]['duration'] = duration
				duration_sec = duration.total_seconds()
				self.videos[video_id]['duration_sec'] = int(duration_sec)

			self.next_page_token = response.get('nextPageToken')
			print(self.next_page_token)
			if not self.next_page_token:
				break

		# 抓短片
		while True:
			response, playlist = self.get_playlist(self.part, self.channel.playlist_id_shorts, self.next_page_token)
			self.video_type(self.part, playlist, self.videos, VideoType.shorts)
			self.next_page_token = response.get('nextPageToken')
			print(self.next_page_token)
			if not self.next_page_token:
				break

		# 抓直播
		while True:
			response, playlist = self.get_playlist(self.part, self.channel.playlist_id_stream, self.next_page_token)
			self.video_type(self.part, playlist, self.videos, VideoType.stream)
			self.next_page_token = response.get('nextPageToken')
			print(self.next_page_token)
			if not self.next_page_token:
				break

		for video_id in self.videos:
			if not self.videos[video_id].get('type'):
				self.videos[video_id]['type'] = 'video'

		print(len(self.videos))

		fieldnames = ['video_id', 'title', 'description', 'published_at', 'type', 'duration', 'duration_sec', 'like_count', 'view_count', 'comment_count']
		with open(f'./Barry/{self.channel.channel_name}.csv', 'w', newline='', encoding='utf-8-sig') as f:
			# 定義欄位名稱
			writer = csv.DictWriter(f, fieldnames=fieldnames)

			# 寫入標題列
			writer.writeheader()
			videos = sorted(self.videos.items(), key=lambda x: x[1]['published_at'])
			
			# 寫入內容
			for video_id, info in videos:
				# 建立一個基礎的 row
				row = {
					'video_id': video_id,
					'title': info['title'],
					'description': info['description'],
					'published_at': info['published_at'],
					'duration': info['duration'],
					'duration_sec': info['duration_sec'],
					'type': info['type']
				}
				
				# 2. 將 stats 字典裡的內容「扁平化」移到 row 這一層
				stats = info['stats']
				row['view_count'] = stats['view_count']
				row['like_count'] = stats['like_count']
				row['comment_count'] = stats['comment_count']
				
				writer.writerow(row)

if __name__ == '__main__':
	KOL(Chienseating()).get_all_videos()
	KOL(HowHowEat()).get_all_videos()







