import os
from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load local .env
load_dotenv()

app = Flask(__name__)

# Load config from .env (same as app.py)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.sendgrid.net')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)

print("--- Email Diagnostic ---")
print(f"Server: {app.config['MAIL_SERVER']}")
print(f"Port: {app.config['MAIL_PORT']}")
print(f"TLS: {app.config['MAIL_USE_TLS']}")
print(f"SSL: {app.config['MAIL_USE_SSL']}")
print(f"Username: {app.config['MAIL_USERNAME']}")
print(f"Sender: {app.config['MAIL_DEFAULT_SENDER']}")
print("------------------------")

with app.app_context():
    recipient = input("Enter a recipient email address to test: ")
    msg = Message('Test Email from Budget Tracker',
                  sender=app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[recipient])
    msg.body = "This is a test email to verify your SendGrid configuration."
    
    try:
        print("Attempting to send email...")
        mail.send(msg)
        print("SUCCESS: Email sent!")
    except Exception as e:
        print(f"FAILURE: {e}")
        if "Connection unexpectedly closed" in str(e):
            print("\nHINT: This usually means there is a mismatch between the Port and the Security setting (TLS/SSL).")
            print("For SendGrid:")
            print("- If Port is 587, MAIL_USE_TLS should be True and MAIL_USE_SSL should be False.")
            print("- If Port is 465, MAIL_USE_TLS should be False and MAIL_USE_SSL should be True.")
