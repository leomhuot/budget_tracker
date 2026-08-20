import db
from dotenv import load_dotenv
load_dotenv()

try:
    with db.get_db_cursor(commit=False) as cur:
        cur.execute('SELECT id, item, amount, currency, type, date FROM transactions ORDER BY id DESC LIMIT 10;')
        rows = cur.fetchall()
        print("Recent Transactions:")
        for row in rows:
            print(f"ID: {row[0]}, Item: {row[1]}, Amount: {row[2]}, Currency: {row[3]}, Type: {row[4]}, Date: {row[5]}")
except Exception as e:
    print(f"Error: {e}")
