from googleapiclient.discovery import build
from enum import Enum, auto
import os, dotenv
import csv
import isodate
import pprint
import json

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
part = 'topicDetails'
part = 'statistics'
video_id = '7URYi1ULvrQ'
request = youtube.videos().list(
    part=part,
    id=video_id,
    # maxResults=1, # 最大50
    # pageToken=next_page_token
)
response = request.execute()
playlist: list = response['items']
playlist.reverse()
print(playlist)
# for item in playlist:
#     topic_catagories = item[part]['topicCategories']
#     print(topic_catagories)
#     for topic_catagory in topic_catagories:
#         print(topic_catagory)
# duration = playlist[0]['contentDetails']['duration']
# print(duration)
# duration = isodate.parse_duration(duration)
# print(duration)
# print(type(duration))
# duration = duration.total_seconds()
# print(duration)
# print(type(duration))

part = 'snippet'
# video_id = 'UWMiLBAQKgc'
# request = youtube.commentThreads().list(
#     part=part,
#     videoId=video_id,
#     maxResults=100, # 最大 100 數量暫定選10% max(100, 10%)
#     order='time'
#     # pageToken=next_page_token
# )
# response = request.execute()
# # print(response)
# # pprint.pprint(response)
# comments: list = response['items']
# total_reply_count = 0
# print(len(comments))
# for comment in comments:
#     top_level_comment = comment['snippet']['topLevelComment']
#     snippet = top_level_comment['snippet']
#     comment_id = top_level_comment['id']
#     author_display_name = snippet['authorDisplayName']
#     like_count = snippet['likeCount']
#     reply_count = comment['snippet']['totalReplyCount']
#     published_at = snippet['publishedAt']
#     comment_content = snippet['textOriginal']
#     # print(comment_id)
#     # print(author_display_name)
#     # print(like_count)
#     # print(reply_count)
#     # print(published_at)
#     # print(comment_content)
#     total_reply_count += reply_count
#     # break
# print(total_reply_count)
    
# for comment in comments:
#     reply_count = comment[part]['totalReplyCount']
#     if reply_count > 0: print(reply_count)
# print(len(comments))

# with open('./Barry/comments.json', 'w', encoding='utf-8') as f:
#     json.dump(response, f, ensure_ascii=False, indent=4)

# part = 'snippet,statistics'
# request = youtube.channels().list(
#     part=part,
#     id=Chienseating_channel_id
# )
# response = request.execute()
# # print(response)
# item = response['items'][0]
# subscriber_count = item['statictis']['subscriberCount']
# view_count = item['statistics']['viewCount']
# print(item['statistics']['subscriberCount'])
# print(item['statistics']['viewCount'])
# print(item['snippet']['title'])

# comment_id = 'Ugw3IhbArwpE6zjUjyR4AaABAg'
# request = youtube.comments().list(
#     part=part,
#     id=comment_id
# )
# response = request.execute()
# print(response)

from database import DBManager

with DBManager().connect_to_db_readonly() as connection:
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute('select comment_id from video_comments where author_id is null')
        comment_ids = cursor.fetchall()
        print(comment_ids)
        for comment_id in comment_ids:
            print(comment_id['comment_id'])
            print(type(comment_id['comment_id']))
            comment_id = comment_id['comment_id']
            request = youtube.comments().list(
                part=part,
                id=comment_id
            )
            response = request.execute()
            print(response)
            if response['items']:
                comment_snippet = response['items'][0][part]
                # 這裡就是該留言者的 YouTube Channel ID
                author_id = comment_snippet['authorChannelId']['value'] 
                author_name = comment_snippet['authorDisplayName']
                print(f'留言者 ID: {author_id}, 暱稱: {author_name}')
                cursor.execute('update video_comments set author_id = %s where comment_id = %s', (author_id, comment_id))
                connection.commit()
            else:
                print('找不到該留言 (可能已被刪除)')








