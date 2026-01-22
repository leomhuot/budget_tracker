import os
import psycopg2
from psycopg2 import pool
import urllib.parse as urlparse
import settings_manager # Added import

# Create a connection pool
db_pool = None

def init_pool():
    global db_pool
    if db_pool is None:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

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
    if db_pool is None: # Corrected from '==='
        init_pool()
    return db_pool.getconn()

def release_db_connection(conn):
    if db_pool is not None:
        db_pool.putconn(conn)

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    print("DEBUG: init_db() started.")
    conn = get_db_connection()
    print("DEBUG: Connection obtained in init_db().")
    try:
        with conn.cursor() as cur:
            print("DEBUG: Cursor obtained. Creating tables...")
            # User Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    totp_secret TEXT
                );
            """)
            print("DEBUG: Table 'users' creation statement executed.")
            # Savings Goals Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS savings_goals (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    target_amount NUMERIC NOT NULL,
                    saved_amount NUMERIC DEFAULT 0.0
                );
            """)
            print("DEBUG: Table 'savings_goals' creation statement executed.")
            # Transactions Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id SERIAL PRIMARY KEY,
                    type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    item TEXT NOT NULL,
                    amount NUMERIC NOT NULL,
                    date DATE NOT NULL,
                    description TEXT,
                    savings_goal_id INTEGER REFERENCES savings_goals(id) ON DELETE SET NULL
                );
            """)
            print("DEBUG: Table 'transactions' creation statement executed.")
            # Expense Categories Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expense_categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    icon TEXT
                );
            """)
            print("DEBUG: Table 'expense_categories' creation statement executed.")
            # Income Categories Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS income_categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    icon TEXT
                );
            """)
            print("DEBUG: Table 'income_categories' creation statement executed.")
            # Settings Table (Key-Value Store)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            print("DEBUG: Table 'settings' creation statement executed.")

            conn.commit()
            print("DEBUG: All table creation committed. Initializing default settings...")
            # Initialize default settings after tables are created
            settings_manager.initialize_default_settings() # Added call
            print("DEBUG: Default settings initialization called.")
    except Exception as e:
        print(f"DEBUG: An error occurred during init_db: {e}")
        if conn:
            conn.rollback()
    finally:
        release_db_connection(conn)
        print("DEBUG: init_db() finished.")

if __name__ == '__main__':
    # This allows you to run `python db.py` to initialize the database manually.
    print("Initializing database...")
    init_db()
    print("Database initialization complete.")