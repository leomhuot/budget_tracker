import db
from dotenv import load_dotenv
load_dotenv()

try:
    with db.get_db_cursor(commit=False) as cur:
        cur.execute('SELECT key, value FROM settings WHERE key = \'exchange_rate\';')
        row = cur.fetchone()
        print(f"Exchange Rate in DB: {row}")
except Exception as e:
    print(f"Error: {e}")
