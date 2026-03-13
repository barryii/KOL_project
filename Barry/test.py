from googleapiclient.discovery import build
from enum import Enum, auto
import os, dotenv
import csv
import isodate

dotenv.load_dotenv()

# https://developers.google.com/youtube/v3/docs

YT_API_KEY = os.getenv('YT_API_KEY')
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

part = 'snippet'
Chienseating_channel_id = 'UC9i2Qgd5lizhVgJrdnxunKw' # 千千
HowHowEat_channel_id = 'UCa2YiSXNTkmOA-QTKdzzbSQ' # 豪豪

Chienseating_playlist_id = 'UU' + Chienseating_channel_id[2:]
HowHowEat_playlist_id = 'UU' + HowHowEat_channel_id[2:]
Chienseating_shorts_playlist_id = 'UUSH' + Chienseating_channel_id[2:]
HowHowEat_shorts_playlist_id = 'UUSH' + HowHowEat_channel_id[2:]
Chienseating_stream_playlist_id = 'UULV' + Chienseating_channel_id[2:]
HowHowEat_stream_playlist_id = 'UULV' + HowHowEat_channel_id[2:]

# request = youtube.playlistItems().list(
#     part=part,
#     playlistId=Chienseating_playlist_id,
#     maxResults=1, # 最大50
#     # pageToken=next_page_token
# )
# response = request.execute()
# playlist: list = response['items']
# playlist.reverse()
# print(playlist)

part = 'contentDetails,statistics'
video_id = 'k-d0dKWp-X4'
request = youtube.videos().list(
    part=part,
    id=video_id,
    maxResults=1, # 最大50
    # pageToken=next_page_token
)
response = request.execute()
playlist: list = response['items']
playlist.reverse()
print(playlist)
duration = playlist[0]['contentDetails']['duration']
print(duration)
duration = isodate.parse_duration(duration)
print(duration)
print(type(duration))
duration = duration.total_seconds()
print(duration)
print(type(duration))

