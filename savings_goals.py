
import json
import os
from datetime import datetime

# Get the absolute path for the directory where this script is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Data directory: use environment variable if set, otherwise default to BASE_DIR
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)

SAVINGS_GOALS_FILE = os.path.join(DATA_DIR, 'savings_goals.json')

def get_savings_goals():
    """Reads all savings goals from the JSON file."""
    if not os.path.exists(SAVINGS_GOALS_FILE) or os.path.getsize(SAVINGS_GOALS_FILE) == 0:
        return []
    
    try:
        with open(SAVINGS_GOALS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_savings_goals(goals):
    """Saves the provided savings goals data to the JSON file."""
    with open(SAVINGS_GOALS_FILE, 'w') as f:
        json.dump(goals, f, indent=4)

def get_savings_goal(goal_id):
    """Retrieves a single savings goal by its ID."""
    goals = get_savings_goals()
    for goal in goals:
        if goal.get('id') == goal_id:
            return goal
    return None

def add_savings_goal(name, target_amount):
    """Adds a new savings goal."""
    goals = get_savings_goals()
    new_id = str(int(goals[-1]['id']) + 1) if goals else '1'
    
    new_goal = {
        'id': new_id,
        'name': name,
        'target_amount': target_amount,
        'saved_amount': 0.0
    }
    goals.append(new_goal)
    save_savings_goals(goals)
    return new_goal

def update_savings_goal(goal_id, name, target_amount):
    """Updates a savings goal's name and target amount."""
    goals = get_savings_goals()
    for goal in goals:
        if goal.get('id') == goal_id:
            goal['name'] = name
            goal['target_amount'] = target_amount
            break
    save_savings_goals(goals)

def delete_savings_goal(goal_id):
    """Deletes a savings goal by its ID."""
    goals = get_savings_goals()
    updated_goals = [g for g in goals if g.get('id') != goal_id]
    save_savings_goals(updated_goals)

def update_saved_amount(goal_id, amount):
    """Updates the saved amount for a savings goal."""
    goals = get_savings_goals()
    for goal in goals:
        if goal.get('id') == goal_id:
            goal['saved_amount'] += amount
            break
    save_savings_goals(goals)

def recalculate_saved_amounts(transactions):
    """Recalculates all saved amounts from transactions."""
    goals = get_savings_goals()
    for goal in goals:
        goal['saved_amount'] = 0.0

    for t in transactions:
        if t['type'] == 'expense' and t['category'] == 'Goal Savings' and t.get('savings_goal_id'):
            for goal in goals:
                if goal['id'] == t['savings_goal_id']:
                    goal['saved_amount'] += t['amount']
                    break
    save_savings_goals(goals)

def get_general_savings_total(transactions):
    """Calculates the total amount from all 'General Savings' expenses."""
    total_general_savings = sum(t['amount'] for t in transactions if t['type'] == 'expense' and t['category'] == 'General Savings')
    return total_general_savings
