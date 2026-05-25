import db
import os
from dotenv import load_dotenv
load_dotenv()

try:
    with db.get_db_cursor(commit=False) as cur:
        cur.execute('SELECT username, email FROM users;')
        users = cur.fetchall()
        print("Users and Emails:")
        for user in users:
            print(f"Username: {user[0]}, Email: {user[1]}")
except Exception as e:
    print(f"Error: {e}")
