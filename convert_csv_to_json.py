import csv
import json
import os

def convert_data_to_json():
    """
    Reads data from transactions.csv, savings_goals.json, settings.json,
    and users.csv and compiles it into a single data_export.json file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # --- Read Transactions ---
    transactions = []
    transactions_file = os.path.join(base_dir, 'transactions.csv')
    try:
        with open(transactions_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert amount to float
                try:
                    row['amount'] = float(row.get('amount', 0.0))
                except (ValueError, TypeError):
                    row['amount'] = 0.0
                transactions.append(row)
    except FileNotFoundError:
        print(f"Warning: '{transactions_file}' not found. No transactions will be exported.")

    # --- Read Savings Goals ---
    savings_goals = []
    savings_goals_file = os.path.join(base_dir, 'savings_goals.json')
    try:
        with open(savings_goals_file, 'r') as f:
            savings_goals = json.load(f)
    except FileNotFoundError:
        print(f"Warning: '{savings_goals_file}' not found. No savings goals will be exported.")
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from '{savings_goals_file}'.")

    # --- Read Settings ---
    settings = {}
    settings_file = os.path.join(base_dir, 'settings.json')
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        print(f"Warning: '{settings_file}' not found. No settings will be exported.")
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from '{settings_file}'.")

    # --- Read Users ---
    users = []
    users_file = os.path.join(base_dir, 'users.csv')
    try:
        with open(users_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append(row)
    except FileNotFoundError:
        print(f"Warning: '{users_file}' not found. No users will be exported.")

    # --- Compile all data ---
    compiled_data = {
        "transactions": transactions,
        "savings_goals": savings_goals,
        "settings": settings,
        "users": users
    }

    # --- Write to JSON file ---
    export_file = os.path.join(base_dir, 'data_export.json')
    with open(export_file, 'w') as f:
        json.dump(compiled_data, f, indent=4)
        
    print(f"Data successfully exported to '{export_file}'")

if __name__ == '__main__':
    convert_data_to_json()
