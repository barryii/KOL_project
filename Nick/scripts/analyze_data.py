import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# 1. 載入連線資訊
load_dotenv()
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME")

engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

def run_analysis():
    print("⏳ 正在提取豪豪的清洗數據並計算戰略得分...")
    df = pd.read_sql("SELECT * FROM video_cleaned", engine)

    if df.empty:
        print("⚠️ 錯誤：資料表為空，請確認 clean_data.py 是否執行成功。")
        return

    # 2. 計算基礎 KPI
    df['like_rate'] = (df['like_count'] / df['view_count'] * 100).round(2)
    df['comment_rate'] = (df['comment_count'] / df['view_count'] * 100).round(2)

    # 3. 計算【綜合實力得分】 (平衡流量與互動)
    # 我們將觀看次數進行對數處理(log)，避免幾百萬點擊的影片權重過大，再結合點讚率
    import numpy as np
    df['score_view'] = np.log1p(df['view_count']) # 流量分數
    df['score_like'] = df['like_rate']           # 互動分數
    
    # 綜合公式：流量佔 40%，互動佔 60% (可依你的需求調整)
    df['total_score'] = ((df['score_view'] / df['score_view'].max() * 40) + 
                         (df['score_like'] / df['score_like'].max() * 60)).round(2)

    # 4. 產生報表 (定義 report 變數，修復 NameError)
    report = df.groupby('strategic_tag').agg({
        'view_count': 'mean',
        'like_rate': 'mean',
        'comment_rate': 'mean',
        'total_score': 'mean',
        'duration_sec': 'count'
    }).rename(columns={'duration_sec': 'video_count'}).round(2)

    # 5. 找出「名利雙收」的長影片 Top 5 (長影片且綜合得分最高)
    top_balanced = df[df['strategic_tag'] == 'Video (長影片-衝收益)'].sort_values(by='total_score', ascending=False).head(5)

    print("\n" + "="*65)
    print("📊 豪豪內容戰略績效彙整")
    print("="*65)
    print(report)
    print("-" * 65)
    print("\n🏆 豪豪「名利雙收」核心長影片排行 (綜合流量與點讚)：")
    for i, (_, row) in enumerate(top_balanced.iterrows(), 1):
        print(f"{i}. {row['title']}")
        print(f"   📈 觀看：{int(row['view_count']):,} 次 | ❤️ 點讚率：{row['like_rate']}% | ⭐ 綜合戰力：{row['total_score']}")
    print("="*65)

    # 6. 存檔到 Excel (修復 IndexError)
    if not os.path.exists('reports'):
        os.makedirs('reports')
    
    file_path = f"reports/haohao_final_report_{pd.Timestamp.now().strftime('%m%d')}.xlsx"
    
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            report.to_excel(writer, sheet_name='戰略類型對比')
            df.sort_values('total_score', ascending=False).to_excel(writer, sheet_name='全影片綜合排名', index=False)
            top_balanced.to_excel(writer, sheet_name='核心標竿長片', index=False)
        print(f"\n✅ 報表已成功存至：{file_path}")
    except Exception as e:
        print(f"❌ 存檔失敗：{e}")

if __name__ == "__main__":
    run_analysis()