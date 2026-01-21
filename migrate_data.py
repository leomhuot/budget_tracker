import os
import csv
import json
import psycopg2
from psycopg2 import pool
import urllib.parse as urlparse
from datetime import datetime

# --- Database Connection Pool Setup (Copied from db.py) ---
db_pool = None

def init_pool():
    global db_pool
    if db_pool is None:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set. Please set it to your Render PostgreSQL internal connection string.")

        url = urlparse.urlparse(database_url)
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:]
        )

def get_db_connection():
    if db_pool is None:
        init_pool()
    return db_pool.getconn()

def release_db_connection(conn):
    if db_pool is not None:
        db_pool.putconn(conn)

# --- Data Loading Functions from Local Files ---

def load_csv_users(file_path):
    users = []
    if not os.path.exists(file_path):
        print(f"Warning: Users CSV file not found at {file_path}")
        return users
    with open(file_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader) # Skip header
        for row in reader:
            # Assuming header: ['id', 'username', 'email', 'password', 'role', 'totp_secret']
            # Make sure to handle potential missing columns for older CSVs
            user_data = {
                'id': row[0],
                'username': row[1],
                'email': row[2] if len(row) > 2 else None,
                'password_hash': row[3],
                'role': row[4] if len(row) > 4 else 'user',
                'totp_secret': row[5] if len(row) > 5 else None
            }
            users.append(user_data)
    return users

def load_csv_transactions(file_path):
    transactions = []
    if not os.path.exists(file_path):
        print(f"Warning: Transactions CSV file not found at {file_path}")
        return transactions
    with open(file_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader) # Skip header
        for row in reader:
            # Assuming header: ['transaction_id', 'date', 'type', 'category', 'item', 'amount', 'description', 'savings_goal_id']
            transactions.append({
                'transaction_id': row[0],
                'date': row[1],
                'type': row[2],
                'category': row[3],
                'item': row[4],
                'amount': float(row[5]),
                'description': row[6] if len(row) > 6 else '',
                'savings_goal_id': row[7] if len(row) > 7 and row[7] else None # Convert empty string to None
            })
    return transactions

def load_json_settings(file_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        print(f"Warning: Settings JSON file not found or empty at {file_path}")
        return {{}}
    with open(file_path, 'r') as f:
        return json.load(f)

def load_json_savings_goals(file_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        print(f"Warning: Savings Goals JSON file not found or empty at {file_path}")
        return []
    with open(file_path, 'r') as f:
        return json.load(f)

# --- Migration Logic ---

def migrate_data(local_data_dir):
    print("Starting data migration...")

    # Load data from local files
    users_data = load_csv_users(os.path.join(local_data_dir, 'users.csv'))
    transactions_data = load_csv_transactions(os.path.join(local_data_dir, 'transactions.csv'))
    settings_data = load_json_settings(os.path.join(local_data_dir, 'settings.json'))
    savings_goals_data = load_json_savings_goals(os.path.join(local_data_dir, 'savings_goals.json'))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # --- Clear existing data in tables ---
            print("Clearing existing data in PostgreSQL tables...")
            cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;") # CASCADE will clear dependent tables like transactions
            cur.execute("TRUNCATE TABLE savings_goals RESTART IDENTITY CASCADE;") # CASCADE will clear dependent transactions
            cur.execute("TRUNCATE TABLE transactions RESTART IDENTITY;")
            cur.execute("TRUNCATE TABLE settings RESTART IDENTITY;")
            cur.execute("TRUNCATE TABLE expense_categories RESTART IDENTITY;")
            cur.execute("TRUNCATE TABLE income_categories RESTART IDENTITY;")
            conn.commit()
            print("Existing data cleared.")

            # --- Migrate Users ---
            print(f"Migrating {len(users_data)} users...")
            for user in users_data:
                cur.execute(
                    "INSERT INTO users (id, username, email, password_hash, role, totp_secret) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET username=EXCLUDED.username, email=EXCLUDED.email, password_hash=EXCLUDED.password_hash, role=EXCLUDED.role, totp_secret=EXCLUDED.totp_secret;",
                    (user['id'], user['username'], user['email'], user['password_hash'], user['role'], user['totp_secret'])
                )
            conn.commit()
            print("Users migrated.")

            # --- Migrate Settings and Categories ---
            print("Migrating settings and categories...")
            if settings_data:
                # Migrate monthly_savings_goal
                monthly_goal = settings_data.get('monthly_savings_goal')
                if monthly_goal is not None:
                    cur.execute(
                        "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;",
                        ('monthly_savings_goal', str(monthly_goal))
                    )
                
                # Migrate expense categories
                category_icons_map = settings_data.get('category_icons', {})
                for cat_name, icon in category_icons_map.items(): # Iterate over items directly
                    if cat_name == '_default': # Skip default as it's not a category itself
                        continue
                    cur.execute(
                        "INSERT INTO expense_categories (name, icon) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET icon = EXCLUDED.icon;",
                        (cat_name, icon)
                    )
                
                # Migrate income categories
                income_category_icons_map = settings_data.get('income_category_icons', {})
                for cat_name, icon in income_category_icons_map.items(): # Iterate over items directly
                    if cat_name == '_default': # Skip default as it's not a category itself
                        continue
                    cur.execute(
                        "INSERT INTO income_categories (name, icon) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET icon = EXCLUDED.icon;",
                        (cat_name, icon)
                    )
            conn.commit()
            print("Settings and categories migrated.")

            # --- Migrate Savings Goals ---
            print(f"Migrating {len(savings_goals_data)} savings goals...")
            for goal in savings_goals_data:
                cur.execute(
                    "INSERT INTO savings_goals (id, name, target_amount, saved_amount) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, target_amount=EXCLUDED.target_amount, saved_amount=EXCLUDED.saved_amount;",
                    (goal['id'], goal['name'], goal['target_amount'], goal['saved_amount'])
                )
            conn.commit()
            print("Savings goals migrated.")

            # --- Migrate Transactions ---
            print(f"Migrating {len(transactions_data)} transactions...")
            for t in transactions_data:
                # Convert transaction_id to int for PostgreSQL (assuming it's serial/integer)
                # Need to cast savings_goal_id to int if it's not None
                savings_goal_id_int = int(t['savings_goal_id']) if t['savings_goal_id'] else None

                cur.execute(
                    """
                    INSERT INTO transactions (transaction_id, date, type, category, item, amount, description, savings_goal_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (transaction_id) DO UPDATE SET 
                    date=EXCLUDED.date, type=EXCLUDED.type, category=EXCLUDED.category, item=EXCLUDED.item, 
                    amount=EXCLUDED.amount, description=EXCLUDED.description, savings_goal_id=EXCLUDED.savings_goal_id;
                    """,
                    (t['transaction_id'], t['date'], t['type'], t['category'], t['item'], t['amount'], t['description'], savings_goal_id_int)
                )
            conn.commit()
            print("Transactions migrated.")

        print("Data migration complete successfully!")

    except Exception as e:
        print(f"An error occurred during migration: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)
        if db_pool:
            db_pool.closeall()

if __name__ == '__main__':
    # Assume local_data_dir is the current directory unless specified
    current_dir = os.path.dirname(os.path.abspath(__file__))
    migrate_data(current_dir)
    print("\nTo run this script:")
    print("1. Ensure you have 'psycopg2-binary' installed: `pip install psycopg2-binary`")
    print("2. Set the DATABASE_URL environment variable to your Render PostgreSQL internal connection string.")
    print("   Example (PowerShell): $env:DATABASE_URL=\"postgres://user:password@host:port/database\"")
    print("   Example (Bash): export DATABASE_URL=\"postgres://user:password@host:port/database\"")
    print("3. Run the script: `python migrate_data.py`")
    print("   If your data files are in a different directory, pass it as an argument: `python migrate_data.py /path/to/your/data`")
