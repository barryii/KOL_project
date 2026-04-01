import os, dotenv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from database import DBManager
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

def run_random_forest_prediction(channel: Chienseating | HowHowEat, video_type: str = VideoType.VIDEO.value):
    # 1. 撈取合法特徵的資料
    print("1. 正在從資料庫撈取資料...")
    with DBManager().connect_to_db_readonly() as connection:
        query = """
            SELECT view_count, published_at, duration_sec 
            FROM videos 
            WHERE channel_id = %s and type = %s
        """
        df = pd.read_sql(query, connection, params=(channel.channel_id, video_type))

    if df.empty:
        print("沒有足夠的資料可以訓練模型。")
        return

    # 2. 特徵工程 (Feature Engineering)
    print("2. 進行特徵工程萃取時間資訊...")
    # 確保 published_at 是時間格式
    df['published_at'] = pd.to_datetime(df['published_at'])

    # 萃取出「星期幾」(0=星期一, 6=星期日) 與「發布小時」(0~23)
    df['publish_day_of_week'] = df['published_at'].dt.dayofweek
    df['publish_hour'] = df['published_at'].dt.hour

    # 處理缺失值 (把沒有長度的影片補平均值或 0)
    df['duration_sec'] = df['duration_sec'].fillna(df['duration_sec'].median())

    # # 處理類別變數 (One-Hot Encoding)：把 type 拆成多個 0/1 的欄位
    # df = pd.get_dummies(df, columns=['type'], dummy_na=False, drop_first=True)

    # 準備 X (特徵) 與 y (目標)
    # 排除不需要的欄位，剩下的都是特徵
    drop_cols = ['view_count', 'published_at']
    X = df.drop(columns=drop_cols)
    y = df['view_count']

    # # 3. 切分訓練集與測試集 (80% 訓練，20% 測試)
    # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # # 4. 建立與訓練 Random Forest 模型
    # print("3. 開始訓練隨機森林模型...")
    # # n_estimators=100 代表我們種了 100 棵決策樹
    # rf_model = RandomForestRegressor(n_estimators=1000, random_state=42)
    # rf_model.fit(X_train, y_train)

    # # 5. 模型成效評估
    # y_pred = rf_model.predict(X_test)
    # r2 = r2_score(y_test, y_pred)
    # mae = mean_absolute_error(y_test, y_pred)
    
    # print("\n================ 模型評估結果 ================")
    # print(f"R-squared (解釋力): {r2:.4f}")
    # print(f"MAE (平均絕對誤差): {mae:,.0f} 觀看次數")
    # print("============================================\n")

    # 3. 切分訓練集與測試集 (80% 訓練，20% 測試)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. 建立 GridSearchCV 進行超參數調校
    print("3. 開始進行網格搜索 (Grid Search)，尋找最佳參數...")
    
    # 定義你想測試的參數範圍
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [None, 5, 10, 20],
        'min_samples_split': [2, 5, 10]
    }
    
    # 建立基礎模型
    base_rf = RandomForestRegressor(random_state=42)
    
    # 包裝成 GridSearch 尋找最佳組合
    # cv=5 代表使用 5 折交叉驗證，n_jobs=-1 代表火力全開使用所有 CPU 核心
    grid_search = GridSearchCV(
        estimator=base_rf, 
        param_grid=param_grid, 
        cv=5, 
        scoring='r2', 
        n_jobs=-1,
        verbose=1 # 會在終端機印出進度
    )
    
    # 開始跑迴圈訓練 (這會花一點時間，因為要訓練 3x4x3x5 = 180 次模型)
    grid_search.fit(X_train, y_train)

    # 取得考試成績最好的那一個模型
    best_rf_model = grid_search.best_estimator_
    
    print("\n================ 調校結果 ================")
    print(f"找到的最佳參數組合: {grid_search.best_params_}")

    # 5. 使用「最佳模型」進行成效評估
    y_pred = best_rf_model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print("\n================ 最終模型評估 ================")
    print(f"優化後的 R-squared (解釋力): {r2:.4f}")
    print(f"優化後的 MAE (平均絕對誤差): {mae:,.0f} 觀看次數")
    print("============================================\n")

    # 6. 萃取並繪製「特徵重要性」
    print("4. 正在產生特徵重要性圖表...")
    # feature_importances = rf_model.feature_importances_
    feature_importances = best_rf_model.feature_importances_
    
    # 將特徵名稱與重要性綁定，並由大到小排序
    fi_df = pd.DataFrame({
        'Feature': X.columns,
        'Importance': feature_importances
    }).sort_values(by='Importance', ascending=False)

    # 將英文特徵名稱換成好讀的中文 (視情況增減)
    rename_dict = {
        'duration_sec': '影片長度 (秒)',
        'publish_hour': '發布時段 (小時)',
        'publish_day_of_week': '發布星期幾'
    }
    fi_df['Feature'] = fi_df['Feature'].replace(rename_dict)

    # 繪圖
    plt.figure(figsize=(10, 6))
    sns.barplot(
        data=fi_df, 
        x='Importance', 
        y='Feature', 
        palette='viridis'
    )
    plt.title('影響 YouTube 影片觀看數的特徵重要性 (Random Forest)', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('重要性分數 (加總為 1.0)', fontsize=12)
    plt.ylabel('特徵', fontsize=12)
    plt.grid(True, axis='x', ls="-", alpha=0.2, color='gray')
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    run_random_forest_prediction(Chienseating())