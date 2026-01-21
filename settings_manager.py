import json
import os

# Get the absolute path for the directory where this script is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Data directory: use environment variable if set, otherwise default to BASE_DIR
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)

SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

DEFAULT_SETTINGS = {
    "monthly_savings_goal": 100.0,
    "expense_categories": [
        "Food", 
        "Drink", 
        "Coffee", 
        "Transportation", 
        "Rent", 
        "Utilities", 
        "Shopping", 
        "Entertainment", 
        "Gym", 
        "Event", 
        "Petroleum", 
        "Family", 
        "Saving",
        "Annual Trip",
        "Haircut",
        "Other"
    ],
    "category_icons": {
        "_default": "fa-tags",
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
    },
    "income_categories": [
        "Salary",
        "Bonus",
        "Freelance",
        "Other"
    ],
    "income_category_icons": {
        "_default": "fa-briefcase",
        "Salary": "fa-money-bill-wave",
        "Bonus": "fa-gift",
        "Freelance": "fa-laptop-code",
        "Other": "fa-search-dollar"
    }
}

def get_settings():
    """
    Reads settings from settings.json.
    If the file doesn't exist, is empty, or corrupted, it returns a default value 
    and ensures all keys are present.
    """
    if not os.path.exists(SETTINGS_FILE) or os.path.getsize(SETTINGS_FILE) == 0:
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Ensure all default keys exist in the loaded settings
            for key, value in DEFAULT_SETTINGS.items():
                if key not in settings:
                    settings[key] = value
            return settings
    except (json.JSONDecodeError, IOError):
        return DEFAULT_SETTINGS.copy()

def save_settings(data):
    """
    Saves the provided settings data to settings.json.
    """
    settings_to_save = {}
    for key in DEFAULT_SETTINGS.keys():
        settings_to_save[key] = data.get(key, DEFAULT_SETTINGS[key])

    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings_to_save, f, indent=4)
