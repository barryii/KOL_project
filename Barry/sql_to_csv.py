from database import DBManager
from youtuber_info import Chienseating, HowHowEat
import csv

if __name__ == '__main__':
    db = DBManager()
    kol_list = [Chienseating(), HowHowEat()]
    for kol in kol_list:
        data = db.get_db_videos(kol.channel_id)
        with open(f'./Barry/{kol.channel_name}_videos.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['video_id', 'channel_id', 'title', 'description', 'topic_tag', 'published_at', 'type', 'duration', 'duration_sec', 'view_count', 'like_count', 'comment_count', 'actual_comment_count', 'cluster_label'])
            writer.writerows(data)

        data = db.get_db_video_comments(kol.channel_id)
        with open(f'./Barry/{kol.channel_name}_video_comments.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['comment_id', 'video_id', 'channel_id', 'author_id', 'author_name', 'text_content', 'like_count', 'reply_count', 'sentiment', 'topic_tag', 'published_at'])
            writer.writerows(data)