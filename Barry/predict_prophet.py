import os, dotenv
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
from databsae import DBManager
from youtuber_info import Chienseating, HowHowEat
from video_type import VideoType

dotenv.load_dotenv()

# --- 設定深色主題 ---
plt.style.use('dark_background')
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['text.color'] = 'white'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'

def run_prophet_forecasting(channel: Chienseating | HowHowEat, video_type: str = VideoType.VIDEO.value):
    # 1. 撈取資料
    print("1. 正在從資料庫撈取時間與觀看數據...")
    with DBManager().connect_to_db() as connection:
        # 我們只需要發布時間和觀看數
        query = """
            SELECT published_at, view_count 
            FROM videos 
            WHERE channel_id = %s and type = %s
        """
        df = pd.read_sql(query, connection, params=(channel.channel_id, video_type))

    if df.empty:
        print("沒有足夠的資料可以進行預測。")
        return

    # 2. 資料轉換：轉換成 Prophet 需要的格式 (ds 和 y)
    print("2. 正在整理每日流量走勢...")
    df['published_at'] = pd.to_datetime(df['published_at'])
    
    # 將時間設為 Index，並把時/分/秒抹除，只保留「日期」
    df.set_index('published_at', inplace=True)
    
    # 使用 resample('D').sum() 將同一天的觀看數加總
    # 這樣就得到了「該頻道每日新發布影片帶來的觀看總數」走勢
    daily_views = df['view_count'].resample('D').sum().reset_index()
    
    # Prophet 嚴格要求欄位名稱必須是 'ds' (日期) 和 'y' (目標數值)
    daily_views.rename(columns={'published_at': 'ds', 'view_count': 'y'}, inplace=True)

    # 3. 建立並訓練 Prophet 模型
    print("3. 開始訓練 Prophet 模型...")
    # 啟用每日與每週的季節性分析
    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(daily_views)

    # 4. 產生未來的預測時間表
    # periods=30 代表我們要預測未來 30 天的走勢
    future = model.make_future_dataframe(periods=30)
    
    # 進行預測
    print("4. 正在預測未來 30 天的流量走勢...")
    forecast = model.predict(future)

    # 5. 繪製預測走勢圖
    print("5. 正在產生預測圖表...")
    
    # 使用 Prophet 內建的繪圖功能 (但套用我們的深色設定)
    fig = model.plot(forecast, figsize=(12, 6))
    
    # 取得當前畫布的軸 (Axes) 進行客製化設定
    ax = fig.gca()
    ax.set_title('KOL 頻道未來 30 天流量趨勢預測', fontsize=16, fontweight='bold', color='white', pad=15)
    ax.set_xlabel('日期', fontsize=12, color='white')
    ax.set_ylabel('每日觀看總數', fontsize=12, color='white')
    
    # 修改 Prophet 預設畫出來的線條顏色以搭配深色背景
    # 黑點(歷史真實數據)改為淺藍色，藍線(預測趨勢)加粗
    for line in ax.get_lines():
        if line.get_marker() == '.':
            line.set_color('cyan')      # 歷史資料點
            line.set_markersize(4)
        else:
            line.set_color('#ff9900')     # 趨勢預測線 (橘色)
            line.set_linewidth(2)
            
    # 調整網格線
    ax.grid(True, which="both", ls="-", alpha=0.2, color='gray')

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    run_prophet_forecasting(Chienseating())