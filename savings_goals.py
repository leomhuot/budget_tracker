
import json
import os
from datetime import datetime
import db



def get_savings_goals():
    """Reads all savings goals from the database."""
    goals = []
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, target_amount, saved_amount FROM savings_goals ORDER BY id;")
            for row in cur.fetchall():
                goals.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'target_amount': float(row[2]),
                    'saved_amount': float(row[3])
                })
    finally:
        db.release_db_connection(conn)
    return goals



def get_savings_goal(goal_id):
    """Retrieves a single savings goal by its ID from the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, target_amount, saved_amount FROM savings_goals WHERE id = %s;",
                (goal_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'id': str(row[0]),
                    'name': row[1],
                    'target_amount': float(row[2]),
                    'saved_amount': float(row[3])
                }
    finally:
        db.release_db_connection(conn)
    return None

def add_savings_goal(name, target_amount):
    """Adds a new savings goal to the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO savings_goals (name, target_amount, saved_amount) VALUES (%s, %s, %s) RETURNING id;",
                (name, target_amount, 0.0)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return {
                'id': str(new_id),
                'name': name,
                'target_amount': target_amount,
                'saved_amount': 0.0
            }
    finally:
        db.release_db_connection(conn)

def update_savings_goal(goal_id, name, target_amount):
    """Updates a savings goal's name and target amount in the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE savings_goals SET name = %s, target_amount = %s WHERE id = %s;",
                (name, target_amount, goal_id)
            )
            conn.commit()
    finally:
        db.release_db_connection(conn)

def delete_savings_goal(goal_id):
    """Deletes a savings goal by its ID from the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM savings_goals WHERE id = %s;", (goal_id,))
            conn.commit()
    finally:
        db.release_db_connection(conn)

def update_saved_amount(goal_id, amount):
    """Updates the saved amount for a savings goal in the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE savings_goals SET saved_amount = saved_amount + %s WHERE id = %s;",
                (amount, goal_id)
            )
            conn.commit()
    finally:
        db.release_db_connection(conn)

def recalculate_saved_amounts(transactions):
    """Recalculates all saved amounts in the database based on transactions."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Reset all saved_amounts to 0
            cur.execute("UPDATE savings_goals SET saved_amount = 0.0;")

            # 2. Recalculate based on transactions (only Goal Savings expenses)
            # Group by savings_goal_id and sum amounts
            cur.execute(
                """
                UPDATE savings_goals sg
                SET saved_amount = sg.saved_amount + sub.total_saved
                FROM (
                    SELECT CAST(savings_goal_id AS INTEGER) as goal_id, SUM(amount) AS total_saved
                    FROM transactions
                    WHERE type = 'expense' AND category = 'Goal Savings' AND savings_goal_id IS NOT NULL
                    GROUP BY savings_goal_id
                ) AS sub
                WHERE sg.id = sub.goal_id;
                """
            )
            conn.commit()
    finally:
        db.release_db_connection(conn)

def get_general_savings_total(transactions):
    """Calculates the total amount from all 'General Savings' expenses."""
    total_general_savings = sum(t['amount'] for t in transactions if t['type'] == 'expense' and t['category'] == 'General Savings')
    return total_general_savings
