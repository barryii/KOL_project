import os, dotenv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from youtuber_info import Chienseating, HowHowEat
from video_type import VideoType
from database import DBManager

dotenv.load_dotenv()

'''
每月發片量、平均觀看數、總觀看數趨勢圖
'''

# --- 設定深色主題 ---
plt.style.use('dark_background')
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['text.color'] = 'white'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'

def draw_monthly_trend(channel: Chienseating | HowHowEat, video_type: str = VideoType.VIDEO.value):
    # 1. 撈取資料
    print('正在從資料庫撈取資料...')
    with DBManager().connect_to_db() as connection:
        query = '''
            SELECT published_at, view_count 
            FROM videos 
            WHERE channel_id = %s and type = %s
        '''
        df = pd.read_sql(query, connection, params=(channel.channel_id, video_type))

    if df.empty:
        print('沒有資料可以繪圖。')
        return

    # 2. 資料轉換：按「月」加總觀看數
    df['published_at'] = pd.to_datetime(df['published_at'])
    df.set_index('published_at', inplace=True)
    
    # 使用 resample('ME') 將數據按月 (Month-End) 加總
    monthly_video_count = df['view_count'].resample('ME').count().reset_index()
    print(monthly_video_count)
    # 總觀看數
    monthly_views = df['view_count'].resample('ME').sum().reset_index()
    print(monthly_views)
    # 平均觀看數
    monthly_avg = df['view_count'].resample('ME').mean().reset_index()
    # 補0
    monthly_avg = monthly_avg.fillna(0)
    print(monthly_avg)

    # 過濾掉觀看數為 0 的月份 (可選，避免圖表首尾出現沒有發片的空白月)
    # monthly_views = monthly_views[monthly_views['view_count'] > 0]
    # monthly_avg = monthly_avg[monthly_avg['view_count'] > 0]

    # 3. 繪製折線圖
    plt.figure(figsize=(12, 6))
    
    # marker='o' 會在折線上畫出圓點，方便辨識每個月的具體位置
    plt.plot(
        monthly_avg['published_at'], 
        monthly_avg['view_count'], 
        marker='o',          # 資料點標記
        color='cyan',        # 線條顏色 (深色背景配淺藍色很清楚)
        linewidth=2,         # 線條粗細
        markersize=6         # 點的大小
    )
    
    # 4. 圖表細節設定
    plt.title(f'{channel.channel_name}頻道歷史每月{video_type}平均觀看數趨勢', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('月份', fontsize=12)
    plt.ylabel('每月平均觀看次數', fontsize=12)
    
    # 設定 X 軸的日期顯示格式 (例如顯示 2023-01)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    # 讓 X 軸的標籤稍微旋轉，避免字擠在一起
    plt.xticks(rotation=45)
    
    # 加入 Y 軸網格線幫助對齊數值
    plt.grid(True, axis='y', ls='-', alpha=0.3, color='gray')

    # 確保版面不會裁切到文字
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(12, 6))
    
    # marker='o' 會在折線上畫出圓點，方便辨識每個月的具體位置
    plt.plot(
        monthly_views['published_at'], 
        monthly_views['view_count'], 
        marker='o',          # 資料點標記
        color='cyan',        # 線條顏色 (深色背景配淺藍色很清楚)
        linewidth=2,         # 線條粗細
        markersize=6         # 點的大小
    )
    
    # 4. 圖表細節設定
    plt.title(f'{channel.channel_name}頻道歷史每月{video_type}總觀看數趨勢', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('月份', fontsize=12)
    plt.ylabel('每月總觀看次數', fontsize=12)
    
    # 設定 X 軸的日期顯示格式 (例如顯示 2023-01)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    # 讓 X 軸的標籤稍微旋轉，避免字擠在一起
    plt.xticks(rotation=45)
    
    # 加入 Y 軸網格線幫助對齊數值
    plt.grid(True, axis='y', ls='-', alpha=0.3, color='gray')

    # 確保版面不會裁切到文字
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(12, 6))
    
    # marker='o' 會在折線上畫出圓點，方便辨識每個月的具體位置
    plt.plot(
        monthly_video_count['published_at'], 
        monthly_video_count['view_count'], 
        marker='o',          # 資料點標記
        color='cyan',        # 線條顏色 (深色背景配淺藍色很清楚)
        linewidth=2,         # 線條粗細
        markersize=6         # 點的大小
    )
    
    # 4. 圖表細節設定
    plt.title(f'{channel.channel_name}頻道歷史每月{video_type}影片數量趨勢', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('月份', fontsize=12)
    plt.ylabel('每月影片數量', fontsize=12)
    
    # 設定 X 軸的日期顯示格式 (例如顯示 2023-01)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    # 讓 X 軸的標籤稍微旋轉，避免字擠在一起
    plt.xticks(rotation=45)
    
    # 加入 Y 軸網格線幫助對齊數值
    plt.grid(True, axis='y', ls='-', alpha=0.3, color='gray')

    # 確保版面不會裁切到文字
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    draw_monthly_trend(Chienseating())
    # draw_monthly_trend(HowHowEat())
    # draw_monthly_trend(Chienseating(), VideoType.SHORTS.value)
    # draw_monthly_trend(HowHowEat(), VideoType.SHORTS.value)
    # draw_monthly_trend(Chienseating(), VideoType.STREAM.value)