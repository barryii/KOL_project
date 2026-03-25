import os, dotenv
import pandas as pd
import numpy as np
import mysql.connector
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from youtuber_info import Chienseating, HowHowEat

dotenv.load_dotenv()
# 解決 matplotlib 中文顯示問題 (如果你電腦有安裝 Microsoft JhengHei)
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False # 解決負號顯示問題

def preview_kmeans_results(channel_id, type: str = 'video'):
    # 1. 建立連線並撈取資料
    conn = mysql.connector.connect(
        host='dv108.aiturn.fun',
        user='barry',
        password=os.getenv('KOL_DB_PW'),
        database='db_kol'
    )
    
    query = """
        SELECT video_id, title, view_count, like_count, comment_count 
        FROM videos 
        WHERE channel_id = %s and type = %s
    """
    df = pd.read_sql(query, conn, params=(channel_id, type))
    conn.close()
    
    if df.empty:
        print("資料庫中沒有可用的影片資料。")
        return

    # 處理缺失值
    df.fillna({'view_count': 0, 'like_count': 0, 'comment_count': 0}, inplace=True)
    
    # 2. 執行 K-Means
    features = ['view_count', 'like_count', 'comment_count']
    X = df[features]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 這裡暫定分 3 群，你可以根據印出來的結果調整這個數字
    n_clusters = 5
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['cluster_label'] = kmeans.fit_predict(X_scaled)

    # 計算群組數量並建立自訂圖例標籤
    cluster_counts = df['cluster_label'].value_counts().to_dict()
    df['legend_label'] = df['cluster_label'].apply(
        lambda x: f"群組 {x} (共 {cluster_counts.get(x, 0)} 筆)"
    )
    label_order = [f"群組 {i} (共 {cluster_counts.get(i, 0)} 筆)" for i in range(n_clusters) if i in cluster_counts]

    # 3. 繪製四圖 (2 列, 2 欄，畫布大小 16x12)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # ---------------- 左上圖：觀看數 vs 按讚數 (無 Log) ----------------
    sns.scatterplot(
        data=df, x='view_count', y='like_count', 
        hue='legend_label', hue_order=label_order, 
        palette='viridis', s=80, alpha=0.7, ax=axes[0, 0]
    )
    axes[0, 0].set_title('觀看數 vs 按讚數 (無 Log)')
    axes[0, 0].set_xlabel('觀看數')
    axes[0, 0].set_ylabel('按讚數')
    axes[0, 0].grid(True, which="both", ls="-", alpha=0.3)
    axes[0, 0].get_legend().remove() # 隱藏圖例
    
    # ---------------- 右上圖：觀看數 vs 留言數 (無 Log) ----------------
    sns.scatterplot(
        data=df, x='view_count', y='comment_count', 
        hue='legend_label', hue_order=label_order, 
        palette='viridis', s=80, alpha=0.7, ax=axes[0, 1]
    )
    axes[0, 1].set_title('觀看數 vs 留言數 (無 Log)')
    axes[0, 1].set_xlabel('觀看數')
    axes[0, 1].set_ylabel('留言數')
    axes[0, 1].grid(True, which="both", ls="-", alpha=0.3)
    axes[0, 1].legend(title='群組統計', loc='best') # 只保留這個圖例
    
    # ---------------- 左下圖：觀看數 vs 按讚數 (僅 X 軸 Log) ----------------
    sns.scatterplot(
        data=df, x='view_count', y='like_count', 
        hue='legend_label', hue_order=label_order, 
        palette='viridis', s=80, alpha=0.7, ax=axes[1, 0]
    )
    axes[1, 0].set_xscale('log')
    axes[1, 0].set_title('觀看數 vs 按讚數 (僅 X 軸 Log)')
    axes[1, 0].set_xlabel('觀看數 (Log Scale)')
    axes[1, 0].set_ylabel('按讚數')
    axes[1, 0].grid(True, which="both", ls="-", alpha=0.3)
    axes[1, 0].get_legend().remove() # 隱藏圖例

    # ---------------- 右下圖：觀看數 vs 留言數 (僅 X 軸 Log) ----------------
    sns.scatterplot(
        data=df, x='view_count', y='comment_count', 
        hue='legend_label', hue_order=label_order, 
        palette='viridis', s=80, alpha=0.7, ax=axes[1, 1]
    )
    axes[1, 1].set_xscale('log')
    axes[1, 1].set_title('觀看數 vs 留言數 (僅 X 軸 Log)')
    axes[1, 1].set_xlabel('觀看數 (Log Scale)')
    axes[1, 1].set_ylabel('留言數')
    axes[1, 1].grid(True, which="both", ls="-", alpha=0.3)
    axes[1, 1].get_legend().remove() # 隱藏圖例

    # 調整整體佈局，避免標籤互相重疊
    plt.tight_layout()
    print("正在產生雙子圖，請查看彈出視窗...")
    plt.show()
    
    # 3. 印出分析結果供你檢視
    # print("================ K-Means 分群預覽 ================\n")
    
    # # 統計各群的影片數量
    # print("【各群影片數量分佈】")
    # print(df['cluster_label'].value_counts().sort_index())
    # print("-" * 50)
    
    # # 計算各群在原始數據上的平均值 (幫助你定義這群是什麼屬性)
    # print("【各群平均數據表現】")
    # cluster_means = df.groupby('cluster_label')[features].mean().round(0).astype(int)
    # print(cluster_means)
    # print("-" * 50)
    
    # # 隨機抽樣幾筆影片看看是否符合該群的特徵
    # print("【各群影片抽樣預覽 (每群最多顯示 5 筆)】")
    # for i in range(n_clusters):
    #     print(f"\n>>> 群組 {i} 的影片：")
    #     sample_df = df[df['cluster_label'] == i][['title', 'view_count', 'like_count', 'comment_count']].head(5)
    #     # 調整 pandas 輸出格式讓標題不會被截斷
    #     pd.set_option('display.max_colwidth', 50) 
    #     print(sample_df)

if __name__ == '__main__':
    preview_kmeans_results(Chienseating().channel_id)