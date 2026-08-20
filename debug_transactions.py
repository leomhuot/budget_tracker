import budget
import settings_manager

transactions = budget.get_transactions()
for t in transactions:
    print(f"ID: {t['id']}, Amount: {t['amount']}, Currency: {t.get('currency')}, Type: {t['type']}")

app_settings = settings_manager.get_settings()
print(f"Exchange Rate: {app_settings.get('exchange_rate')}")
