from datetime import datetime, timedelta
import db # Import the db module for database interaction
import uuid # Import uuid for generating unique transaction IDs
import settings_manager
import psycopg2




def get_monthly_summary():
    """Calculates monthly summary data efficiently using SQL and USD-only conversion."""
    app_settings = settings_manager.get_settings()
    exchange_rate = float(app_settings.get('exchange_rate', 4000.0))
    print(f"DEBUG: Using exchange_rate={exchange_rate}")
    
    today = datetime.now()
    start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if today.month == 12:
        end_date = start_date.replace(year=today.year + 1, month=1)
    else:
        end_date = start_date.replace(month=today.month + 1)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    try:
        with db.get_db_cursor(commit=False) as cur:
            # Helper to calculate USD total
            def get_usd_total(query, params=None):
                cur.execute(query, params)
                rows = cur.fetchall()
                total_usd = 0.0
                for amount, currency in rows:
                    amount = float(amount)
                    # Force string and strip
                    curr = str(currency).strip() if currency else 'USD'
                    print(f"DEBUG: Processing amount={amount}, raw_currency='{currency}', normalized_curr='{curr}'")
                    if curr.upper() == 'USD':
                        print(f"DEBUG: Currency is USD")
                        total_usd += amount
                    elif curr.upper() == 'KHR':
                        print(f"DEBUG: Currency is KHR, converting {amount} to {amount / exchange_rate}")
                        total_usd += (amount / exchange_rate)
                    else:
                        print(f"DEBUG: Unknown currency '{curr}', defaulting to USD")
                        total_usd += amount
                return total_usd

            # Get Total Income (Monthly)
            total_income = get_usd_total(
                "SELECT COALESCE(amount, 0), currency FROM transactions WHERE type = 'income' AND date >= %s AND date < %s;",
                (start_date_str, end_date_str)
            )

            # Get Total Expense (Monthly)
            total_expense = get_usd_total(
                "SELECT COALESCE(amount, 0), currency FROM transactions WHERE type = 'expense' AND date >= %s AND date < %s;",
                (start_date_str, end_date_str)
            )

            # Get Total General Savings (All time)
            total_general_savings = get_usd_total(
                "SELECT COALESCE(amount, 0), currency FROM transactions WHERE type = 'expense' AND category = 'General Savings';"
            )
            
            # Get Total Goal Savings (All time)
            total_goal_savings = get_usd_total(
                "SELECT COALESCE(amount, 0), currency FROM transactions WHERE type = 'expense' AND category = 'Goal Savings';"
            )

            total_savings = total_general_savings + total_goal_savings

            return {
                "total_income": total_income,
                "total_expense": total_expense,
                "balance": total_income - total_expense,
                "total_savings": total_savings,
                "total_general_savings": total_general_savings,
                "total_goal_savings": total_goal_savings,
                "period_name": today.strftime('%B %Y'),
                "exchange_rate": exchange_rate
            }
    except psycopg2.pool.PoolError:
        print("ERROR: Database is temporarily unavailable.")
        raise

def add_transaction(type, category, item, amount, date, description, savings_goal_id=None, currency='USD'):
    """Adds a single transaction to the database."""
    try:
        with db.get_db_cursor() as cur: # commit=True by default for INSERT operation
            # Generate a unique transaction_id using UUID
            transaction_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO transactions (transaction_id, type, category, item, amount, date, description, savings_goal_id, currency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (transaction_id, type, category, item, amount, date, description, savings_goal_id if savings_goal_id else None, currency)
            )
    except psycopg2.pool.PoolError:
        print("ERROR: Database is temporarily unavailable. Unable to add transaction.")
        raise # Re-raise to be handled by calling function/Flask
def get_transactions(sort_by_date=True):
    """Reads all transactions from the database."""
    transactions = []
    try:
        with db.get_db_cursor(commit=False) as cur: # commit=False for SELECT operation
            cur.execute("SELECT id, transaction_id, date, type, category, item, amount, description, savings_goal_id, currency FROM transactions ORDER BY date DESC;")
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
                    'savings_goal_id': str(row[8]) if row[8] else '', # Ensure ID is string
                    'currency': row[9] if row[9] else 'USD'
                }
                transactions.append(transaction_dict)
    except psycopg2.pool.PoolError:
        print("ERROR: Database is temporarily unavailable. Unable to retrieve transactions.")
        raise # Re-raise to be handled by calling function/Flask
    return transactions

def get_transaction(transaction_id):
    """Retrieves a single transaction by its ID from the database."""
    try:
        with db.get_db_cursor(commit=False) as cur: # commit=False for SELECT operation
            cur.execute(
                "SELECT id, transaction_id, date, type, category, item, amount, description, savings_goal_id, currency FROM transactions WHERE id = %s;",
                (transaction_id,)
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
                    'savings_goal_id': str(row[8]) if row[8] else '',
                    'currency': row[9] if row[9] else 'USD'
                }
                return transaction_dict
    except psycopg2.pool.PoolError:
        print("ERROR: Database is temporarily unavailable. Unable to retrieve transaction.")
        raise # Re-raise to be handled by calling function/Flask
    return None

def delete_transaction(transaction_id):
    """Deletes a transaction by its ID from the database."""
    try:
        with db.get_db_cursor() as cur: # commit=True by default for DELETE operation
            cur.execute("DELETE FROM transactions WHERE id = %s;", (transaction_id,))
    except psycopg2.pool.PoolError:
        print("ERROR: Database is temporarily unavailable. Unable to delete transaction.")
        raise # Re-raise to be handled by calling function/Flask

def update_transaction(transaction_id, data):
    """Updates a transaction by its ID in the database."""
    try:
        with db.get_db_cursor() as cur: # commit=True by default for UPDATE operation
            # Construct the SET part of the SQL query dynamically
            set_clauses = []
            values = []
            for key, value in data.items():
                if key != 'id': # Query by 'id', not 'transaction_id'
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            # If currency is not in data, we don't update it (it stays as is)
            
            values.append(transaction_id) # Add transaction_id (which is now the 'id') for WHERE clause

            cur.execute(
                f"""
                UPDATE transactions
                SET {', '.join(set_clauses)}
                WHERE id = %s;
                """,
                tuple(values)
            )
    except psycopg2.pool.PoolError:
        print("ERROR: Database is temporarily unavailable. Unable to update transaction.")
        raise # Re-raise to be handled by calling function/Flask

def generate_report_data(period=None, start_date_str=None, end_date_str=None):
    """Generates budget report data for a given period or custom date range with USD-only summaries."""
    app_settings = settings_manager.get_settings()
    exchange_rate = app_settings.get('exchange_rate', 4000.0)
    
    transactions = get_transactions(sort_by_date=False)
    today = datetime.now()
    # ... (date handling logic)
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            period = 'monthly'
    
    # ... (date period setting logic)
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
        period = 'daily'
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    
    if 'start_date' not in locals() or 'end_date' not in locals():
        # Default to daily if no period and no custom dates or if custom dates were invalid
        period = 'daily'
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

    filtered_transactions = [
        t for t in transactions 
        if 'date' in t and t['date'] and start_date <= datetime.strptime(t['date'], '%Y-%m-%d') < end_date
    ]
    
    filtered_transactions.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)

    def calc_usd_total(txs):
        usd_sum = 0.0
        for t in txs:
            amt = float(t['amount'])
            # Force string and strip
            curr = str(t.get('currency', 'USD')).strip()
            print(f"DEBUG: Processing transaction item='{t.get('item')}', amount={amt}, currency='{curr}'")
            if curr.upper() == 'USD':
                usd_sum += amt
            elif curr.upper() == 'KHR':
                usd_sum += (amt / exchange_rate)
            else:
                print(f"DEBUG: Unknown currency '{curr}', defaulting to USD")
                usd_sum += amt
        return usd_sum

    total_income = calc_usd_total([t for t in filtered_transactions if t['type'] == 'income'])
    total_expense = calc_usd_total([t for t in filtered_transactions if t['type'] == 'expense'])
    total_goal_savings = calc_usd_total([t for t in filtered_transactions if t['type'] == 'expense' and t['category'] == 'Goal Savings'])
    total_general_savings = calc_usd_total([t for t in filtered_transactions if t['type'] == 'expense' and t['category'] == 'General Savings'])
    
    total_savings = total_goal_savings + total_general_savings
    balance = total_income - total_expense

    income_breakdown_by_item = {}
    for t in filtered_transactions:
        if t['type'] == 'income':
            item = t.get('item', 'Other')
            amt = float(t['amount'])
            curr = t.get('currency', 'USD')
            if curr == 'KHR':
                amt = amt / exchange_rate
            income_breakdown_by_item[item] = income_breakdown_by_item.get(item, 0) + amt

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
            
            m_income = calc_usd_total([t for t in month_transactions if t['type'] == 'income'])
            m_expense = calc_usd_total([t for t in month_transactions if t['type'] == 'expense'])
            m_savings = calc_usd_total([t for t in month_transactions if t['type'] == 'expense' and (t['category'] == 'Goal Savings' or t['category'] == 'General Savings')])
            m_balance = m_income - m_expense

            if m_income > 0 or m_expense > 0 or m_savings > 0: # Only include months with data
                monthly_summaries.append({
                    'month': current_month_start.strftime('%Y-%m'),
                    'total_income': m_income,
                    'total_expense': m_expense,
                    'total_savings': m_savings,
                    'balance': m_balance
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
        "monthly_summaries": monthly_summaries if period == 'yearly' else [],
        "exchange_rate": exchange_rate
    }