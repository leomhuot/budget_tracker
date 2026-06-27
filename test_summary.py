import db
from dotenv import load_dotenv
load_dotenv()
import budget as budget_logic

try:
    summary = budget_logic.get_monthly_summary()
    print("Monthly Summary:")
    print(summary)
except Exception as e:
    print(f"Error: {e}")
