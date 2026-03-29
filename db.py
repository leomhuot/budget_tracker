import os
import psycopg2
from psycopg2 import pool
import urllib.parse as urlparse
import settings_manager # Added import
import contextlib # Added for context manager

# Create a connection pool
db_pool = None
_pool_pid = None

def init_pool():
    global db_pool, _pool_pid
    database_url = os.environ.get('DATABASE_URL')
    print(f"DEBUG: Initializing pool (PID: {os.getpid()}). DATABASE_URL present: {bool(database_url)}")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    url = urlparse.urlparse(database_url)
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=30,
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        database=url.path[1:],
        sslmode='require',
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )
    _pool_pid = os.getpid()

def get_db_connection():
    global db_pool, _pool_pid
    # Re-initialize pool if it doesn't exist OR if we are in a different process (forked)
    if db_pool is None or _pool_pid != os.getpid():
        # If we're in a new process, we can't reliably close the old pool's connections
        # as they belong to the parent process's socket. We just create a new pool.
        init_pool()
    return db_pool.getconn()

def release_db_connection(conn):
    global db_pool, _pool_pid
    if db_pool is not None and _pool_pid == os.getpid():
        db_pool.putconn(conn)
    else:
        # If the pool was created in a different process, just close the connection
        try:
            conn.close()
        except:
            pass

@contextlib.contextmanager
def get_db_cursor(commit=True):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise psycopg2.pool.PoolError("Failed to acquire database connection.")
        
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except (psycopg2.pool.PoolError, psycopg2.OperationalError) as e:
        print(f"ERROR: Database connection error (PID: {os.getpid()}): {e}")
        raise 
    except Exception as e:
        print(f"ERROR: An error occurred during database operation: {e}")
        if conn:
            try:
                conn.rollback()
            except psycopg2.InterfaceError:
                # Connection is already closed, cannot rollback
                pass
        raise 
    finally:
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            release_db_connection(conn)

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
                    totp_secret TEXT,
                    approved BOOLEAN DEFAULT FALSE NOT NULL
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
                    id SERIAL PRIMARY KEY,
                    transaction_id TEXT NOT NULL, -- Keeping this as a unique identifier for existing data if needed
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