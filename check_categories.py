import db
from dotenv import load_dotenv
load_dotenv()

try:
    with db.get_db_cursor(commit=False) as cur:
        cur.execute('SELECT DISTINCT category FROM transactions;')
        rows = cur.fetchall()
        print("Distinct Categories in Transactions:")
        for row in rows:
            print(f"'{row[0]}'")
except Exception as e:
    print(f"Error: {e}")
