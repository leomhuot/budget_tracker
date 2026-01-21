import json
import os
import db

DEFAULT_MONTHLY_SAVINGS_GOAL = 100.0

def _get_db_categories(table_name):
    categories = []
    category_icons = {}
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT name, icon FROM {table_name} ORDER BY name;")
            for row in cur.fetchall():
                categories.append(row[0])
                category_icons[row[0]] = row[1]
    finally:
        db.release_db_connection(conn)
    return categories, category_icons

def _save_db_categories(table_name, categories_data):
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Clear existing categories for simplicity before re-inserting
            # In a real app, you might do a diff and update/insert/delete more granularly
            cur.execute(f"DELETE FROM {table_name};")
            
            for name, icon in categories_data.items():
                cur.execute(
                    f"INSERT INTO {table_name} (name, icon) VALUES (%s, %s);",
                    (name, icon)
                )
            conn.commit()
    finally:
        db.release_db_connection(conn)



def get_settings():
    """
    Reads settings from the PostgreSQL database.
    If no settings exist, it returns a default value.
    """
    settings = {}
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get monthly_savings_goal
            cur.execute("SELECT value FROM settings WHERE key = 'monthly_savings_goal';")
            result = cur.fetchone()
            settings['monthly_savings_goal'] = float(result[0]) if result else DEFAULT_MONTHLY_SAVINGS_GOAL
    finally:
        db.release_db_connection(conn)

    # Get expense categories and icons
    expense_categories, category_icons = _get_db_categories('expense_categories')
    settings['expense_categories'] = expense_categories
    settings['category_icons'] = category_icons

    # Get income categories and icons
    income_categories, income_category_icons = _get_db_categories('income_categories')
    settings['income_categories'] = income_categories
    settings['income_category_icons'] = income_category_icons
    
    return settings

def save_settings(data):
    """
    Saves the provided settings data to the PostgreSQL database.
    """
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Save monthly_savings_goal
            monthly_goal = data.get('monthly_savings_goal', DEFAULT_MONTHLY_SAVINGS_GOAL)
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;",
                ('monthly_savings_goal', str(monthly_goal))
            )
            conn.commit()
    finally:
        db.release_db_connection(conn)

    # Prepare data for _save_db_categories
    expense_category_map = {}
    for cat_name in data.get('expense_categories', []):
        expense_category_map[cat_name] = data.get('category_icons', {}).get(cat_name, "fa-tags")
    _save_db_categories('expense_categories', expense_category_map)

    income_category_map = {}
    for cat_name in data.get('income_categories', []):
        income_category_map[cat_name] = data.get('income_category_icons', {}).get(cat_name, "fa-briefcase")
    _save_db_categories('income_categories', income_category_map)

def initialize_default_settings():
    """
    Initializes default settings and categories in the PostgreSQL database
    if they don't already exist.
    """
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if monthly_savings_goal exists
            cur.execute("SELECT COUNT(*) FROM settings WHERE key = 'monthly_savings_goal';")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s);",
                    ('monthly_savings_goal', str(DEFAULT_MONTHLY_SAVINGS_GOAL))
                )
                conn.commit()

            # Check and populate expense categories
            cur.execute("SELECT COUNT(*) FROM expense_categories;")
            if cur.fetchone()[0] == 0:
                default_expense_categories_data = {
                    "Food": "fa-utensils", 
                    "Drink": "fa-mug-saucer", 
                    "Coffee": "fa-coffee", 
                    "Transportation": "fa-car", 
                    "Rent": "fa-house", 
                    "Utilities": "fa-lightbulb", 
                    "Shopping": "fa-bag-shopping", 
                    "Entertainment": "fa-film", 
                    "Gym": "fa-dumbbell", 
                    "Event": "fa-calendar-check", 
                    "Petroleum": "fa-gas-pump", 
                    "Family": "fa-people-group", 
                    "Saving": "fa-piggy-bank",
                    "Annual Trip": "fa-plane",
                    "Haircut": "fa-cut",
                    "Other": "fa-ellipsis-h"
                }
                for name, icon in default_expense_categories_data.items():
                    cur.execute(
                        "INSERT INTO expense_categories (name, icon) VALUES (%s, %s);",
                        (name, icon)
                    )
                conn.commit()
                
            # Check and populate income categories
            cur.execute("SELECT COUNT(*) FROM income_categories;")
            if cur.fetchone()[0] == 0:
                default_income_categories_data = {
                    "Salary": "fa-money-bill-wave",
                    "Bonus": "fa-gift",
                    "Freelance": "fa-laptop-code",
                    "Other": "fa-search-dollar"
                }
                for name, icon in default_income_categories_data.items():
                    cur.execute(
                        "INSERT INTO income_categories (name, icon) VALUES (%s, %s);",
                        (name, icon)
                    )
                conn.commit()

    finally:
        db.release_db_connection(conn)
