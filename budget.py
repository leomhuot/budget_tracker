import csv
from datetime import datetime, timedelta
import os
import sys

# Get the absolute path for the directory where this script is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Data directory: use environment variable if set, otherwise default to BASE_DIR
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)

TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.csv')
FILE_HEADER = ['transaction_id', 'date', 'type', 'category', 'item', 'amount', 'description', 'savings_goal_id']

def _migrate_data_if_needed():
    """
    Checks if the CSV file needs migration to match the current FILE_HEADER.
    If so, it rewrites the file, ensuring all rows conform to FILE_HEADER.
    """
    if not os.path.exists(TRANSACTIONS_FILE) or os.path.getsize(TRANSACTIONS_FILE) == 0:
        with open(TRANSACTIONS_FILE, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(FILE_HEADER)
        return

    existing_transactions = []
    existing_header = []
    needs_migration = False

    with open(TRANSACTIONS_FILE, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        try:
            existing_header = next(reader)
        except StopIteration:
            needs_migration = True
            existing_header = []

        if existing_header != FILE_HEADER:
            needs_migration = True
            print(f"Header mismatch detected. Existing: {existing_header}, Expected: {FILE_HEADER}", file=sys.stderr)
        
        if existing_header:
            csvfile.seek(0)
            next(reader)
            dict_reader = csv.DictReader(csvfile, fieldnames=existing_header)
            for row in dict_reader:
                existing_transactions.append(row)
        
        for transaction_row in existing_transactions:
            for field in FILE_HEADER:
                if field not in transaction_row or transaction_row.get(field) is None:
                    needs_migration = True
                    break
            if needs_migration:
                break

    if needs_migration:
        print("Migration to new format with all required columns triggered...", file=sys.stderr)
        with open(TRANSACTIONS_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FILE_HEADER)
            writer.writeheader()
            
            for old_row_dict in existing_transactions:
                new_row = {}
                for field in FILE_HEADER:
                    if field == 'transaction_id':
                        new_row[field] = old_row_dict.get(field) or datetime.now().strftime('%Y%m%d%H%M%S%f')
                    elif field == 'savings_goal_id':
                        new_row[field] = old_row_dict.get(field, '')
                    else:
                        new_row[field] = old_row_dict.get(field, '')
                writer.writerow(new_row)
        print("Migration complete.", file=sys.stderr)


def add_transaction(type, category, item, amount, date, description, savings_goal_id=''):
    """Adds a single transaction with a unique ID to the CSV file."""
    _migrate_data_if_needed()
    if not os.path.exists(TRANSACTIONS_FILE) or os.path.getsize(TRANSACTIONS_FILE) == 0:
        with open(TRANSACTIONS_FILE, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(FILE_HEADER)

    with open(TRANSACTIONS_FILE, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        transaction_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        writer.writerow([transaction_id, date, type, category, item, amount, description, savings_goal_id])

def get_transactions(sort_by_date=True):
    """Reads all transactions from the CSV file, handling migration if necessary."""
    _migrate_data_if_needed()
    if not os.path.exists(TRANSACTIONS_FILE):
        return []

    transactions_raw = []
    with open(TRANSACTIONS_FILE, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            transactions_raw.append(row)

    transactions = []
    transactions_for_sorting = []

    for row_dict in transactions_raw:
        transaction_dict = {}
        for field in FILE_HEADER:
            value = row_dict.get(field, None)
            
            if field == 'amount':
                try:
                    transaction_dict[field] = float(value) if value is not None and value != '' else 0.00
                except ValueError:
                    transaction_dict[field] = 0.00
            else:
                transaction_dict[field] = value if value is not None else ''
        
        if sort_by_date:
            try:
                temp_dict_for_sort = transaction_dict.copy()
                temp_dict_for_sort['datetime_obj'] = datetime.strptime(transaction_dict['date'], '%Y-%m-%d')
                transactions_for_sorting.append(temp_dict_for_sort)
            except (ValueError, KeyError, TypeError) as e:
                print(f"Skipping row due to date parse error during sorting prep ({e}): {row_dict}", file=sys.stderr)
                transactions.append(transaction_dict)
        else:
            transactions.append(transaction_dict)

    if sort_by_date:
        transactions_for_sorting.sort(key=lambda x: x['datetime_obj'], reverse=True)
        for t_with_dt in transactions_for_sorting:
            t_copy = t_with_dt.copy()
            del t_copy['datetime_obj']
            transactions.append(t_copy)

    return transactions

def get_transaction(transaction_id):
    """Retrieves a single transaction by its ID."""
    transactions = get_transactions()
    for t in transactions:
        if t.get('transaction_id') == transaction_id:
            return t
    return None

def delete_transaction(transaction_id):
    """Deletes a transaction by its ID."""
    transactions = get_transactions(sort_by_date=False)
    updated_transactions = [t for t in transactions if t.get('transaction_id') != transaction_id]

    with open(TRANSACTIONS_FILE, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FILE_HEADER)
        writer.writeheader()
        writer.writerows(updated_transactions)

def update_transaction(transaction_id, data):
    """Updates a transaction by its ID."""
    transactions = get_transactions(sort_by_date=False)
    
    for i, t in enumerate(transactions):
        if t.get('transaction_id') == transaction_id:
            updated_t = t.copy()
            for key, value in data.items():
                updated_t[key] = value
            
            transactions[i] = updated_t
            break
            
    with open(TRANSACTIONS_FILE, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FILE_HEADER)
        writer.writeheader()
        writer.writerows(transactions)

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