from database import DBManager

def check_foreign_keys():
    db = DBManager()
    try:
        with db.connect_to_db_readonly() as conn:
            with conn.cursor(dictionary=True) as cursor:
                sql = """
                SELECT 
                    TABLE_NAME, 
                    COLUMN_NAME, 
                    CONSTRAINT_NAME, 
                    REFERENCED_TABLE_NAME, 
                    REFERENCED_COLUMN_NAME
                FROM
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE
                    TABLE_SCHEMA = 'db_kol' 
                    AND REFERENCED_TABLE_NAME IS NOT NULL;
                """
                cursor.execute(sql)
                results = cursor.fetchall()
                
                if not results:
                    print("目前資料庫中沒有定義任何外鍵 (Foreign Keys)。")
                else:
                    print(f"{'資料表':<20} | {'欄位':<20} | {'參考資料表':<20} | {'參考欄位':<20} | {'約束名稱':<20}")
                    print("-" * 110)
                    for row in results:
                        print(f"{row['TABLE_NAME']:<20} | {row['COLUMN_NAME']:<20} | {row['REFERENCED_TABLE_NAME']:<20} | {row['REFERENCED_COLUMN_NAME']:<20} | {row['CONSTRAINT_NAME']:<20}")
    except Exception as e:
        print(f"查詢失敗: {e}")

if __name__ == "__main__":
    check_foreign_keys()
