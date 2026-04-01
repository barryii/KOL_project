import os, dotenv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, r2_score
from database import DBManager
from youtuber_info import Chienseating, HowHowEat
from xgboost import XGBRegressor
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

def run_xgboost_with_momentum(channel: Chienseating | HowHowEat, video_type: str = VideoType.VIDEO.value):
    # 1. 撈取資料 (加入 channel_id 以防未來有多個頻道混在一起算錯)
    print("1. 正在從資料庫撈取資料...")
    with DBManager().connect_to_db() as connection:
        query = """
            SELECT channel_id, view_count, published_at, duration_sec
            FROM videos 
            WHERE channel_id = %s and type = %s
        """
        df = pd.read_sql(query, connection, params=(channel.channel_id, video_type))

    if df.empty:
        print("沒有足夠的資料可以訓練模型。")
        return

    # 2. 特徵工程
    print("2. 進行特徵工程 (加入過去 3 支影片的平均觀看數)...")
    df['published_at'] = pd.to_datetime(df['published_at'])
    
    # --- 核心新增：計算滾動平均 (Momentum) ---
    # 必須先照時間排序，否則拿到的「過去」會是錯的
    df = df.sort_values(by=['channel_id', 'published_at']).reset_index(drop=True)
    
    # shift(1) 是絕對關鍵：確保當下這支影片只能看到「它發布之前」的數據
    df['past_3_avg_views'] = df.groupby('channel_id')['view_count'].transform(
        lambda x: x.shift(1).rolling(window=3, min_periods=1).mean()
    )
    
    # 第一支發布的影片沒有「過去」可以參考，會產生 NaN，我們直接把它濾掉
    df = df.dropna(subset=['past_3_avg_views'])
    # ----------------------------------------

    # 處理原本的時間與類別特徵
    df['publish_day_of_week'] = df['published_at'].dt.dayofweek
    df['publish_hour'] = df['published_at'].dt.hour
    df['duration_sec'] = df['duration_sec'].fillna(df['duration_sec'].median())
    # df = pd.get_dummies(df, columns=['type'], dummy_na=False, drop_first=True)

    # 準備 X 與 y (排除不需要投入訓練的欄位)
    drop_cols = ['channel_id', 'view_count', 'published_at']
    X = df.drop(columns=drop_cols)
    y = df['view_count']

    # 3. 切分訓練集與測試集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. XGBoost 模型與網格搜索
    print("3. 開始 XGBoost 模型訓練與調校...")
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [3, 5, 7],
        'learning_rate': [0.01, 0.05, 0.1]
    }
    
    base_xgb = XGBRegressor(random_state=42, objective='reg:squarederror')
    grid_search = GridSearchCV(base_xgb, param_grid, cv=5, scoring='r2', n_jobs=-1)
    grid_search.fit(X_train, y_train)
    best_xgb = grid_search.best_estimator_
    
    # 5. 模型成效評估
    y_pred = best_xgb.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print("\n================ 加入近期熱度特徵後的評估 ================")
    print(f"優化後的 R-squared (解釋力): {r2:.4f}")
    print(f"優化後的 MAE (平均絕對誤差): {mae:,.0f} 觀看次數")
    print("========================================================\n")

    # 6. 繪製特徵重要性圖表
    print("4. 正在產生特徵重要性圖表...")
    fi_df = pd.DataFrame({
        'Feature': X.columns,
        'Importance': best_xgb.feature_importances_
    }).sort_values(by='Importance', ascending=False)

    # 替換成中文標籤
    rename_dict = {
        'past_3_avg_views': '近期熱度 (前3支影片平均觀看)',
        'duration_sec': '影片長度 (秒)',
        'publish_hour': '發布時段 (小時)',
        'publish_day_of_week': '發布星期幾'
    }
    fi_df['Feature'] = fi_df['Feature'].replace(rename_dict)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=fi_df, x='Importance', y='Feature', palette='magma')
    plt.title('影響 YouTube 影片觀看數的特徵重要性 (加入近期熱度)', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('重要性分數 (加總為 1.0)', fontsize=12)
    plt.ylabel('特徵', fontsize=12)
    plt.grid(True, axis='x', ls="-", alpha=0.2, color='gray')
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    run_xgboost_with_momentum(Chienseating())