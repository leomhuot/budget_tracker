from datetime import datetime, timedelta
import db # Import the db module for database interaction
import uuid # Import uuid for generating unique transaction IDs




def add_transaction(type, category, item, amount, date, description, savings_goal_id=None):
    """Adds a single transaction to the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Generate a unique transaction_id using UUID
            transaction_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO transactions (transaction_id, type, category, item, amount, date, description, savings_goal_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (transaction_id, type, category, item, amount, date, description, savings_goal_id if savings_goal_id else None)
            )
            conn.commit()
    finally:
        db.release_db_connection(conn)
def get_transactions(sort_by_date=True):
    """Reads all transactions from the database."""
    transactions = []
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, transaction_id, date, type, category, item, amount, description, savings_goal_id FROM transactions ORDER BY date DESC;")
            # Convert rows to a list of dictionaries for consistency with original CSV output
            # Also convert Decimal to float for JSON serialization later
            for row in cur.fetchall():
                transaction_dict = {
                    'id': str(row[0]), # The new auto-generated ID
                    'transaction_id': str(row[1]), # The UUID
                    'date': str(row[2]),
                    'type': row[3],
                    'category': row[4],
                    'item': row[5],
                    'amount': float(row[6]), # Convert Decimal to float
                    'description': row[7],
                    'savings_goal_id': str(row[8]) if row[8] else '' # Ensure ID is string
                }
                transactions.append(transaction_dict)
    finally:
        db.release_db_connection(conn)
    return transactions

def get_transaction(transaction_id): # Renaming parameter to 'id' would be clearer but keeping original for minimal change
    """Retrieves a single transaction by its ID from the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, transaction_id, date, type, category, item, amount, description, savings_goal_id FROM transactions WHERE id = %s;",
                (transaction_id,) # Assuming transaction_id parameter is actually the new 'id'
            )
            row = cur.fetchone()
            if row:
                transaction_dict = {
                    'id': str(row[0]),
                    'transaction_id': str(row[1]),
                    'date': str(row[2]),
                    'type': row[3],
                    'category': row[4],
                    'item': row[5],
                    'amount': float(row[6]),
                    'description': row[7],
                    'savings_goal_id': str(row[8]) if row[8] else ''
                }
                return transaction_dict
    finally:
        db.release_db_connection(conn)
    return None
def delete_transaction(transaction_id): # Renaming parameter to 'id' would be clearer but keeping original for minimal change
    """Deletes a transaction by its ID from the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM transactions WHERE id = %s;", (transaction_id,))
            conn.commit()
    finally:
        db.release_db_connection(conn)
def update_transaction(transaction_id, data): # Renaming parameter to 'id' would be clearer but keeping original for minimal change
    """Updates a transaction by its ID in the database."""
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Construct the SET part of the SQL query dynamically
            set_clauses = []
            values = []
            for key, value in data.items():
                if key != 'id': # Query by 'id', not 'transaction_id'
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            values.append(transaction_id) # Add transaction_id (which is now the 'id') for WHERE clause

            cur.execute(
                f"""
                UPDATE transactions
                SET {', '.join(set_clauses)}
                WHERE id = %s;
                """,
                tuple(values)
            )
            conn.commit()
    finally:
        db.release_db_connection(conn)
def generate_report_data(period=None, start_date_str=None, end_date_str=None):
    """Generates budget report data for a given period or custom date range."""
    transactions = get_transactions(sort_by_date=False)
    today = datetime.now()

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            # period is already correctly set by app.py, so no need to overwrite to "custom" here
        except ValueError:
            period = 'monthly'
    
    if period == 'daily':
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(weeks=1)
    elif period == 'monthly':
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if today.month == 12:
            end_date = start_date.replace(year=today.year + 1, month=1)
        else:
            end_date = start_date.replace(month=today.month + 1)
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date.replace(year=today.year + 1)
    elif period == 'last_year_to_date': # Added this line for last_year_to_date
        last_year = today.year - 1
        start_date = datetime(last_year, 1, 1, 0, 0, 0, 0)
        end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif not (start_date_str and end_date_str):
        period = 'monthly'
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if today.month == 12:
            end_date = start_date.replace(year=today.year + 1, month=1)
        else:
            end_date = start_date.replace(month=today.month + 1)
    
    if 'start_date' not in locals() or 'end_date' not in locals():
        # Default to monthly if no period and no custom dates or if custom dates were invalid
        period = 'monthly'
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if today.month == 12:
            end_date = start_date.replace(year=today.year + 1, month=1)
        else:
            end_date = start_date.replace(month=today.month + 1)


    filtered_transactions = [
        t for t in transactions 
        if 'date' in t and t['date'] and start_date <= datetime.strptime(t['date'], '%Y-%m-%d') < end_date
    ]
    
    filtered_transactions.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)

    total_income = sum(t['amount'] for t in filtered_transactions if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in filtered_transactions if t['type'] == 'expense')
    total_goal_savings = sum(t['amount'] for t in filtered_transactions if t['type'] == 'expense' and t['category'] == 'Goal Savings')
    total_general_savings = sum(t['amount'] for t in filtered_transactions if t['type'] == 'expense' and t['category'] == 'General Savings')
    total_savings = total_goal_savings + total_general_savings
    balance = total_income - total_expense

    income_breakdown_by_item = {}
    for t in filtered_transactions:
        if t['type'] == 'income':
            item = t.get('item', 'Other')
            income_breakdown_by_item[item] = income_breakdown_by_item.get(item, 0) + t['amount']

    monthly_summaries = []
    if period == 'yearly':
        current_month_start = start_date.replace(day=1)
        while current_month_start < end_date:
            next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1) # Advance to next month
            if next_month_start > end_date: # Don't go past the year's end
                next_month_start = end_date

            month_transactions = [
                t for t in filtered_transactions
                if current_month_start <= datetime.strptime(t['date'], '%Y-%m-%d') < next_month_start
            ]
            
            month_income = sum(t['amount'] for t in month_transactions if t['type'] == 'income')
            month_expense = sum(t['amount'] for t in month_transactions if t['type'] == 'expense')
            month_savings = sum(t['amount'] for t in month_transactions if t['type'] == 'expense' and (t['category'] == 'Goal Savings' or t['category'] == 'General Savings'))
            month_balance = month_income - month_expense

            if month_income > 0 or month_expense > 0 or month_savings > 0: # Only include months with data
                monthly_summaries.append({
                    'month': current_month_start.strftime('%Y-%m'),
                    'total_income': month_income,
                    'total_expense': month_expense,
                    'total_savings': month_savings,
                    'balance': month_balance
                })
            current_month_start = next_month_start


    return {
        "period": period,
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": (end_date - timedelta(days=1)).strftime('%Y-%m-%d'),
        "total_income": total_income,
        "total_expense": total_expense,
        "total_savings": total_savings,
        "total_goal_savings": total_goal_savings,
        "total_general_savings": total_general_savings,
        "balance": balance,
        "transactions": filtered_transactions,
        "income_breakdown_by_item": income_breakdown_by_item,
        "monthly_summaries": monthly_summaries if period == 'yearly' else []
    }