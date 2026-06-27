import db
from dotenv import load_dotenv
load_dotenv()

try:
    with db.get_db_cursor(commit=False) as cur:
        cur.execute('SELECT category, SUM(amount) FROM transactions WHERE type = \'expense\' GROUP BY category;')
        rows = cur.fetchall()
        print("Expense Totals by Category:")
        for row in rows:
            print(f"Category: {row[0]}, Total: {row[1]}")
except Exception as e:
    print(f"Error: {e}")
