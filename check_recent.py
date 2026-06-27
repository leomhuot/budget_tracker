import db
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta

try:
    with db.get_db_cursor(commit=False) as cur:
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        cur.execute('SELECT category, item, amount, date FROM transactions WHERE date >= %s ORDER BY date DESC;', (two_days_ago,))
        rows = cur.fetchall()
        print("Recent Transactions:")
        for row in rows:
            print(f"Category: {row[0]}, Item: {row[1]}, Amount: {row[2]}, Date: {row[3]}")
except Exception as e:
    print(f"Error: {e}")
