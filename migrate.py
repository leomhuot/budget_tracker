import os
import psycopg2
import urllib.parse as urlparse

def run_migration():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    url = urlparse.urlparse(database_url)
    conn = None
    try:
        conn = psycopg2.connect(
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:]
        )
        cur = conn.cursor()

        # Check if the 'id' column already exists to prevent errors on re-runs
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='transactions' AND column_name='id';")
        if cur.fetchone():
            print("Column 'id' already exists in 'transactions' table. Skipping migration.")
            return

        print("Starting migration for 'transactions' table...")

        # 1. Drop existing PRIMARY KEY constraint on transaction_id if it exists
        # We need to find the name of the constraint first
        cur.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'transactions' AND constraint_type = 'PRIMARY KEY';
        """)
        pk_constraint = cur.fetchone()
        if pk_constraint:
            print(f"Dropping existing primary key constraint '{pk_constraint[0]}' from 'transactions' table...")
            cur.execute(f"ALTER TABLE transactions DROP CONSTRAINT {pk_constraint[0]};")
            conn.commit() # Commit this change immediately
            print("Existing primary key constraint dropped.")
        else:
            print("No existing primary key constraint found on 'transactions' table.")

        # 2. Add the new 'id' column as SERIAL PRIMARY KEY
        print("Adding 'id' column as SERIAL PRIMARY KEY to 'transactions' table...")
        cur.execute("ALTER TABLE transactions ADD COLUMN id SERIAL PRIMARY KEY;")
        conn.commit()
        print("Successfully added 'id' column as SERIAL PRIMARY KEY to 'transactions' table.")

    except Exception as e:
        print(f"Error during migration: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    run_migration()