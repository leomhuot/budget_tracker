from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
import os # Added os import
import budget as budget_logic
import settings_manager
import savings_goals as savings_goals_logic
from datetime import datetime
import db  # Import the new db module

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

# Initialize the database
with app.app_context():
    db.init_db()

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function



class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role='user', totp_secret=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.totp_secret = totp_secret

def get_user_by_username(username):
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
            user_data = cur.fetchone()
            if user_data:
                return User(id=user_data[0], username=user_data[1], email=user_data[2], password_hash=user_data[3], role=user_data[4], totp_secret=user_data[5])
    finally:
        db.release_db_connection(conn)
    return None

def get_user_by_id(user_id):
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
            user_data = cur.fetchone()
            if user_data:
                return User(id=user_data[0], username=user_data[1], email=user_data[2], password_hash=user_data[3], role=user_data[4], totp_secret=user_data[5])
    finally:
        db.release_db_connection(conn)
    return None

def get_user_by_email(email):
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
            user_data = cur.fetchone()
            if user_data:
                return User(id=user_data[0], username=user_data[1], email=user_data[2], password_hash=user_data[3], role=user_data[4], totp_secret=user_data[5])
    finally:
        db.release_db_connection(conn)
    return None


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)


def get_all_users():
    users = []
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY id;")
            for row in cur.fetchall():
                users.append(User(id=row[0], username=row[1], email=row[2], password_hash=row[3], role=row[4], totp_secret=row[5]))
    finally:
        db.release_db_connection(conn)
    return users

def update_user_totp_secret(user_id, totp_secret):
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET totp_secret = %s WHERE id = %s;", (totp_secret, user_id))
            conn.commit()
    finally:
        db.release_db_connection(conn)

def update_user_password(user_id, new_password_hash):
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (new_password_hash, user_id))
            conn.commit()
    finally:
        db.release_db_connection(conn)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = get_all_users()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin_users'))
    
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            conn.commit()
    finally:
        db.release_db_connection(conn)

    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/promote/<int:user_id>')
@login_required
@admin_required
def promote_user(user_id):
    if user_id == current_user.id:
        flash("You cannot change your own role.", 'danger')
        return redirect(url_for('admin_users'))

    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role = 'admin' WHERE id = %s;", (user_id,))
            conn.commit()
    finally:
        db.release_db_connection(conn)

    flash('User promoted to admin.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/demote/<int:user_id>')
@login_required
@admin_required
def demote_user(user_id):
    if user_id == current_user.id:
        flash("You cannot change your own role.", 'danger')
        return redirect(url_for('admin_users'))

    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role = 'user' WHERE id = %s;", (user_id,))
            conn.commit()
    finally:
        db.release_db_connection(conn)

    flash('User demoted to user.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not check_password_hash(current_user.password_hash, current_password):
            flash('Incorrect current password.', 'danger')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('change_password'))

        if len(new_password) < 6: # Basic password strength check
            flash('New password must be at least 6 characters long.', 'danger')
            return redirect(url_for('change_password'))

        new_password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        update_user_password(current_user.id, new_password_hash)
        
        flash('Your password has been changed successfully.', 'success')
        return redirect(url_for('settings'))

    return render_template('change_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        if user and check_password_hash(user.password_hash, password):
            if user.totp_secret:
                session['temp_user_id'] = user.id
                return redirect(url_for('verify_2fa'))
            else:
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        
        user = get_user_by_username(username_or_email)
        if not user:
            user = get_user_by_email(username_or_email)

        if user and user.email:
            token = s.dumps(user.id, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            print(f"Password reset URL: {reset_url}") # Temporary print for testing
            msg = Message('Password Reset Request', sender=app.config['MAIL_DEFAULT_SENDER'], recipients=[user.email])
            msg.body = f'To reset your password, visit the following link: {reset_url}\n\n' \
                       f'If you did not request a password reset, please ignore this email.'
            try:
                mail.send(msg)
                flash('A password reset link has been sent to your email address.', 'info')
            except Exception as e:
                flash(f'Error sending email: {e}. Please check your mail server configuration.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Username or email not found, or no email associated with this account.', 'danger')
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        user_id = s.loads(token, salt='password-reset-salt', max_age=3600)  # Token valid for 1 hour
    except SignatureExpired:
        flash('The password reset link is expired. Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))
    except BadTimeSignature:
        flash('The password reset link is invalid. Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))
    
    user = get_user_by_id(user_id)
    if not user:
        flash('Invalid user for password reset.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
            flash('Both new password and confirmation are required.', 'danger')
            return render_template('reset_password.html', token=token)

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return render_template('reset_password.html', token=token)

        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
            return render_template('reset_password.html', token=token)
        
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        update_user_password(user.id, hashed_password)
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

@app.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    user_id = session.get('temp_user_id')
    if not user_id:
        flash('Session expired or invalid. Please log in again.', 'danger')
        return redirect(url_for('login'))

    user = get_user_by_id(user_id)
    if not user or not user.totp_secret:
        flash('Invalid user or 2FA not set up. Please log in again.', 'danger')
        session.pop('temp_user_id', None)
        return redirect(url_for('login'))

    if request.method == 'POST':
        totp_code = request.form.get('totp_code')
        if not totp_code:
            flash('2FA code is required.', 'danger')
            return render_template('verify_2fa.html')

        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(totp_code):
            login_user(user)
            session.pop('temp_user_id', None) # Clear the temporary user ID from session
            flash('Two-Factor Authentication successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid 2FA code. Please try again.', 'danger')
            return render_template('verify_2fa.html')
            
    return render_template('verify_2fa.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if get_user_by_username(username):
            flash('Username already exists.', 'warning')
            return redirect(url_for('register'))
            
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        conn = db.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users;")
                user_count = cur.fetchone()[0]
                role = 'admin' if user_count == 0 else 'user'
                
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s);",
                    (username, email, password_hash, role)
                )
                conn.commit()
        finally:
            db.release_db_connection(conn)
            
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # Load settings dynamically to ensure latest categories and icons are used
    app_settings = settings_manager.get_settings()
    current_expense_categories = app_settings['expense_categories']
    current_category_icons = app_settings['category_icons']
    current_income_categories = app_settings['income_categories']
    current_income_category_icons = app_settings['income_category_icons']
    savings_goals = savings_goals_logic.get_savings_goals()

    if request.method == 'POST':
        transaction_type = request.form.get('type')
        item = request.form.get('item')
        amount = float(request.form.get('amount', 0))
        date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        description = request.form.get('description', '')
        savings_goal_id = request.form.get('savings_goal_id')

        if transaction_type == 'income' and item and amount > 0:
            category = request.form.get('category')
            if category in current_income_categories:
                budget_logic.add_transaction('income', category, item, amount, date, description)
        elif transaction_type == 'expense' and item and amount > 0:
            category = request.form.get('category')
            # Ensure savings_goal_id is only processed if category is "Goal Savings"
            transaction_savings_goal_id = request.form.get('savings_goal_id') if category == 'Goal Savings' else ''

            if category in current_expense_categories:
                if category == 'Goal Savings':
                    if not transaction_savings_goal_id:
                        flash('Please select a savings goal for "Goal Savings" category.', 'danger')
                        return redirect(url_for('index'))
                    budget_logic.add_transaction('expense', category, item, amount, date, description, transaction_savings_goal_id)
                    savings_goals_logic.update_saved_amount(transaction_savings_goal_id, amount)
                elif category == 'General Savings':
                    # General Savings should not be linked to a specific goal
                    budget_logic.add_transaction('expense', category, item, amount, date, description, '')
                else:
                    # Other categories (non-saving related)
                    budget_logic.add_transaction('expense', category, item, amount, date, description, '')
        
        return redirect(url_for('index'))

    all_transactions = budget_logic.get_transactions()
    savings_goals_logic.recalculate_saved_amounts(all_transactions) # Recalculate saved amounts for goals
    return render_template('index.html', 
                           categories=current_expense_categories, 
                           transactions=all_transactions, 
                           category_icons=current_category_icons, 
                           income_categories=current_income_categories,
                           income_category_icons=current_income_category_icons,
                           savings_goals=savings_goals,
                           today_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_query = request.args.get('search_query', '').strip()

    all_transactions = budget_logic.get_transactions()
    
    app_settings = settings_manager.get_settings()
    current_category_icons = app_settings['category_icons']
    income_category_icons = app_settings['income_category_icons']
    
    if search_query:
        filtered_transactions = [
            t for t in all_transactions
            if search_query.lower() in str(t.get('item', '')).lower() or \
               search_query.lower() in str(t.get('category', '')).lower() or \
               search_query.lower() in str(t.get('description', '')).lower() or \
               search_query.lower() in str(t.get('amount', '')).lower() or \
               search_query.lower() in str(t.get('date', '')).lower() or \
               search_query.lower() in str(t.get('type', '')).lower() or \
               search_query.lower() in str(t.get('transaction_id', '')).lower()
        ]
        transactions_to_paginate = filtered_transactions
    else:
        transactions_to_paginate = all_transactions

    total_transactions = len(transactions_to_paginate)
    total_pages = (total_transactions + per_page - 1) // per_page

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_transactions = transactions_to_paginate[start_index:end_index]

    return render_template('transactions.html', 
                           transactions=paginated_transactions, 
                           category_icons=current_category_icons,
                           income_category_icons=income_category_icons,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           total_transactions=total_transactions,
                           search_query=search_query)

@app.route('/report')
@login_required
def report():
    period = request.args.get('period')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    search_query = request.args.get('search_query', '').strip()
    page = request.args.get('page', 1, type=int) # Define page at the beginning
    per_page = request.args.get('per_page', 10, type=int) # Define per_page at the beginning

    if period in ['daily', 'weekly', 'monthly', 'yearly', 'last_year_to_date']:
        session.pop('custom_report_range', None)
    elif period == 'custom':
        if start_date_str and end_date_str:
            session['custom_report_range'] = (start_date_str, end_date_str)
        elif 'custom_report_range' in session:
            start_date_str, end_date_str = session['custom_report_range']
    elif period is None and 'custom_report_range' in session:
        period = 'custom'
        start_date_str, end_date_str = session['custom_report_range']

    if period == 'last_year_to_date':
        today = datetime.now()
        last_year = today.year - 1
        start_date_obj = datetime(last_year, 1, 1, 0, 0, 0, 0)
        end_date_obj = today
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

    report_data = budget_logic.generate_report_data(period=period, start_date_str=start_date_str, end_date_str=end_date_str)

    if report_data is None:
        flash('Invalid custom date range. Please provide valid start and end dates.', 'danger')
        return redirect(url_for('index'))

    app_settings = settings_manager.get_settings()
    current_category_icons = app_settings['category_icons']
    income_category_icons = app_settings['income_category_icons']
    
    all_transactions = budget_logic.get_transactions()
    savings_goals_logic.recalculate_saved_amounts(all_transactions)
    savings_goals = savings_goals_logic.get_savings_goals()
    # total_general_savings = savings_goals_logic.get_general_savings_total(all_transactions) # Get total general savings
    total_general_savings = report_data.get('total_general_savings', 0) # Get total general savings
    original_total_income = report_data['total_income'] if report_data else 0

    transactions_to_paginate = report_data['transactions'] # This is the list of all transactions for the period

    if search_query:
        transactions_to_paginate = [
            t for t in transactions_to_paginate
            if search_query.lower() in str(t.get('item', '')).lower() or \
               search_query.lower() in str(t.get('category', '')).lower() or \
               search_query.lower() in str(t.get('description', '')).lower() or \
               search_query.lower() in str(t.get('amount', '')).lower() or \
               search_query.lower() in str(t.get('date', '')).lower() or \
               search_query.lower() in str(t.get('type', '')).lower() or \
               search_query.lower() in str(t.get('transaction_id', '')).lower()
        ]
    
    # Calculate totals AFTER search filter
    displayed_total_expense = sum(t['amount'] for t in transactions_to_paginate if t['type'] == 'expense')
    
    # Pagination logic
    total_transactions_in_period = len(transactions_to_paginate)
    total_pages_in_period = (total_transactions_in_period + per_page - 1) // per_page

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_transactions_for_report = transactions_to_paginate[start_index:end_index]

    if report_data and report_data['period'] == 'monthly':
        settings = settings_manager.get_settings()
        report_data['total_budget'] = original_total_income
        report_data['savings_goal'] = settings.get('monthly_savings_goal', 0)
        report_data['remaining_spending'] = report_data['total_budget'] - report_data['savings_goal'] - displayed_total_expense
        
    return render_template('report.html', 
                           report=report_data, 
                           displayed_transactions=paginated_transactions_for_report,
                           displayed_total_expense=displayed_total_expense,
                           current_period=period, 
                           category_icons=current_category_icons,
                           income_category_icons=income_category_icons,
                           start_date=report_data['start_date'], 
                         #  end_date=report_data['end_date'], 
                         # all_transactions_for_export=all_transactions, # Keep this for PDF export
                         #  savings_goals=savings_goals,
                           end_date=report_data['end_date'],
                           savings_goals=savings_goals,
                          # total_general_savings=total_general_savings, # New variable passed
                           search_query=search_query,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages_in_period,
                           total_transactions=total_transactions_in_period)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        monthly_savings_goal = float(request.form.get('monthly_savings_goal'))
        settings_data = settings_manager.get_settings()
        settings_data['monthly_savings_goal'] = monthly_savings_goal
        settings_manager.save_settings(settings_data)
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('settings'))

    current_settings = settings_manager.get_settings()
    return render_template('settings.html', settings=current_settings, current_user=current_user)

@app.route('/settings/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    current_settings = settings_manager.get_settings()
    expense_categories = current_settings.get('expense_categories', [])
    category_icons = current_settings.get('category_icons', {})

    if request.method == 'POST':
        new_category_name = request.form.get('new_category_name', '').strip()
        new_category_icon = request.form.get('new_category_icon', '').strip()

        if new_category_name:
            # Check for duplicate category name (case-insensitive)
            if any(new_category_name.lower() == existing_category.lower() for existing_category in expense_categories):
                flash(f'Category "{new_category_name}" already exists!', 'warning')
                return redirect(url_for('manage_categories'))

            expense_categories.append(new_category_name)
            category_icons[new_category_name] = new_category_icon if new_category_icon else category_icons.get('_default')
            
            current_settings['expense_categories'] = expense_categories
            current_settings['category_icons'] = category_icons
            settings_manager.save_settings(current_settings)
            flash(f'Category "{new_category_name}" added successfully!', 'success')
        else:
            flash('Category name cannot be empty.', 'danger')
        
        return redirect(url_for('manage_categories'))

    return render_template('categories.html', 
                           expense_categories=expense_categories, 
                           category_icons=category_icons,
                           current_settings=current_settings)


@app.route('/settings/categories/delete/<category_name>')
@login_required
def delete_category(category_name):
    current_settings = settings_manager.get_settings()
    expense_categories = current_settings.get('expense_categories', [])
    category_icons = current_settings.get('category_icons', {})

    if category_name in expense_categories:
        expense_categories.remove(category_name)
        if category_name in category_icons:
            del category_icons[category_name]
        
        current_settings['expense_categories'] = expense_categories
        current_settings['category_icons'] = category_icons
        settings_manager.save_settings(current_settings)
        flash(f'Category "{category_name}" deleted successfully!', 'success')
    else:
        flash(f'Category "{category_name}" not found.', 'danger')
    
    return redirect(url_for('manage_categories'))


@app.route('/settings/categories/edit/<old_category_name>', methods=['GET', 'POST'])
@login_required
def edit_category(old_category_name):
    current_settings = settings_manager.get_settings()
    expense_categories = current_settings.get('expense_categories', [])
    category_icons = current_settings.get('category_icons', {})

    if request.method == 'POST':
        new_category_name = request.form.get('new_category_name', '').strip()
        new_category_icon = request.form.get('new_category_icon', '').strip()

        if not new_category_name:
            flash('New category name cannot be empty.', 'danger')
            return redirect(url_for('edit_category', old_category_name=old_category_name))

        # Check for duplicate category name (case-insensitive) excluding the category being edited
        if any(new_category_name.lower() == existing_category.lower() for existing_category in expense_categories if existing_category.lower() != old_category_name.lower()):
            flash(f'Category "{new_category_name}" already exists!', 'warning')
            return redirect(url_for('edit_category', old_category_name=old_category_name))

        if old_category_name in expense_categories:
            idx = expense_categories.index(old_category_name)
            expense_categories[idx] = new_category_name
            
            if old_category_name in category_icons:
                del category_icons[old_category_name]
            category_icons[new_category_name] = new_category_icon if new_category_icon else category_icons.get('_default')

            current_settings['expense_categories'] = expense_categories
            current_settings['category_icons'] = category_icons
            settings_manager.save_settings(current_settings)
            flash(f'Category "{old_category_name}" updated to "{new_category_name}" successfully!', 'success')
            return redirect(url_for('manage_categories'))
        else:
            flash(f'Category "{old_category_name}" not found.', 'danger')
            return redirect(url_for('manage_categories'))
    
    if old_category_name not in expense_categories:
        flash(f'Category "{old_category_name}" not found.', 'danger')
        return redirect(url_for('manage_categories'))
        
    current_icon = category_icons.get(old_category_name, category_icons.get('_default'))
    return render_template('edit_category.html', 
                           category_name=old_category_name, 
                           category_icon=current_icon)

@app.route('/settings/income_categories', methods=['GET', 'POST'])
@login_required
def manage_income_categories():
    current_settings = settings_manager.get_settings()
    income_categories = current_settings.get('income_categories', [])
    income_category_icons = current_settings.get('income_category_icons', {})

    if request.method == 'POST':
        new_category_name = request.form.get('new_category_name', '').strip()
        new_category_icon = request.form.get('new_category_icon', '').strip()

        if new_category_name:
            # Check for duplicate category name (case-insensitive)
            if any(new_category_name.lower() == existing_category.lower() for existing_category in income_categories):
                flash(f'Income Category "{new_category_name}" already exists!', 'warning')
                return redirect(url_for('manage_income_categories'))

            income_categories.append(new_category_name)
            income_category_icons[new_category_name] = new_category_icon if new_category_icon else income_category_icons.get('_default')
            
            current_settings['income_categories'] = income_categories
            current_settings['income_category_icons'] = income_category_icons
            settings_manager.save_settings(current_settings)
            flash(f'Income Category "{new_category_name}" added successfully!', 'success')
        else:
            flash('Income Category name cannot be empty.', 'danger')
        
        return redirect(url_for('manage_income_categories'))

    return render_template('income_categories.html', 
                           income_categories=income_categories, 
                           income_category_icons=income_category_icons,
                           current_settings=current_settings)


@app.route('/settings/income_categories/delete/<category_name>')
@login_required
def delete_income_category(category_name):
    current_settings = settings_manager.get_settings()
    income_categories = current_settings.get('income_categories', [])
    income_category_icons = current_settings.get('income_category_icons', {})

    if category_name in income_categories:
        income_categories.remove(category_name)
        if category_name in income_category_icons:
            del income_category_icons[category_name]
        
        current_settings['income_categories'] = income_categories
        current_settings['income_category_icons'] = income_category_icons
        settings_manager.save_settings(current_settings)
        flash(f'Income Category "{category_name}" deleted successfully!', 'success')
    else:
        flash(f'Income Category "{category_name}" not found.', 'danger')
    
    return redirect(url_for('manage_income_categories'))


@app.route('/settings/income_categories/edit/<old_category_name>', methods=['GET', 'POST'])
@login_required
def edit_income_category(old_category_name):
    current_settings = settings_manager.get_settings()
    income_categories = current_settings.get('income_categories', [])
    income_category_icons = current_settings.get('income_category_icons', {})

    if request.method == 'POST':
        new_category_name = request.form.get('new_category_name', '').strip()
        new_category_icon = request.form.get('new_category_icon', '').strip()

        if not new_category_name:
            flash('New income category name cannot be empty.', 'danger')
            return redirect(url_for('edit_income_category', old_category_name=old_category_name))

        # Check for duplicate category name (case-insensitive) excluding the category being edited
        if any(new_category_name.lower() == existing_category.lower() for existing_category in income_categories if existing_category.lower() != old_category_name.lower()):
            flash(f'Income Category "{new_category_name}" already exists!', 'warning')
            return redirect(url_for('edit_income_category', old_category_name=old_category_name))

        if old_category_name in income_categories:
            idx = income_categories.index(old_category_name)
            income_categories[idx] = new_category_name
            
            if old_category_name in income_category_icons:
                del income_category_icons[old_category_name]
            income_category_icons[new_category_name] = new_category_icon if new_category_icon else income_category_icons.get('_default')

            current_settings['income_categories'] = income_categories
            current_settings['income_category_icons'] = income_category_icons
            settings_manager.save_settings(current_settings)
            flash(f'Income Category "{old_category_name}" updated to "{new_category_name}" successfully!', 'success')
            return redirect(url_for('manage_income_categories'))
        else:
            flash(f'Income Category "{old_category_name}" not found.', 'danger')
            return redirect(url_for('manage_income_categories'))
    
    if old_category_name not in income_categories:
        flash(f'Income Category "{old_category_name}" not found.', 'danger')
        return redirect(url_for('manage_income_categories'))
        
    current_icon = income_category_icons.get(old_category_name, income_category_icons.get('_default'))
    return render_template('edit_income_category.html', 
                           category_name=old_category_name, 
                           category_icon=current_icon)


@app.route('/settings/savings_goals', methods=['GET', 'POST'], endpoint='manage_savings_goals')
@login_required
def manage_savings_goals():
    current_savings_goals = savings_goals_logic.get_savings_goals()

    if request.method == 'POST':
        new_goal_name = request.form.get('new_goal_name', '').strip()
        new_goal_target = float(request.form.get('new_goal_target', 0))

        if new_goal_name and new_goal_target > 0:
            savings_goals_logic.add_savings_goal(new_goal_name, new_goal_target)
            flash(f'Savings Goal "{new_goal_name}" added successfully!', 'success')
        else:
            flash('Goal name and target amount cannot be empty or zero.', 'danger')
        
        return redirect(url_for('manage_savings_goals'))

    return render_template('savings_goals.html', savings_goals=current_savings_goals)

@app.route('/settings/savings_goals/delete/<goal_id>', endpoint='delete_savings_goal')
@login_required
def delete_savings_goal(goal_id):
    savings_goals_logic.delete_savings_goal(goal_id)
    flash('Savings Goal deleted successfully.', 'success')
    return redirect(url_for('manage_savings_goals'))

@app.route('/settings/savings_goals/edit/<goal_id>', methods=['GET', 'POST'], endpoint='edit_savings_goal')
@login_required
def edit_savings_goal(goal_id):
    goal = savings_goals_logic.get_savings_goal(goal_id)
    if not goal:
        flash('Savings Goal not found.', 'danger')
        return redirect(url_for('manage_savings_goals'))

    if request.method == 'POST':
        new_goal_name = request.form.get('new_goal_name', '').strip()
        new_goal_target = float(request.form.get('new_goal_target', 0))

        if not new_goal_name or new_goal_target <= 0:
            flash('Goal name and target amount cannot be empty or zero.', 'danger')
            return redirect(url_for('edit_savings_goal', goal_id=goal_id))

        savings_goals_logic.update_savings_goal(goal_id, new_goal_name, new_goal_target)
        flash(f'Savings Goal "{new_goal_name}" updated successfully!', 'success')
        return redirect(url_for('manage_savings_goals'))



@app.route('/setup_2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    user = current_user
    if request.method == 'GET':
        if user.totp_secret:
            flash('2FA is already set up for your account.', 'info')
            return redirect(url_for('settings'))

        secret = pyotp.random_base32()
        session['otp_secret'] = secret
        
        # Generate the OTPAuth URL for the QR code
        # The 'BudgetTracker' is the issuer name, and user.username is the account name
        otpauth_url = pyotp.totp.TOTP(secret).provisioning_uri(user.username, issuer_name="BudgetTracker")
        
        return render_template('setup_2fa.html', totp_secret=secret, otpauth_url=otpauth_url)
    
    elif request.method == 'POST':
        totp_code = request.form.get('totp_code')
        secret = session.get('otp_secret')

        if not secret:
            flash('2FA setup session expired or invalid. Please try again.', 'danger')
            return redirect(url_for('setup_2fa'))

        totp = pyotp.TOTP(secret)
        if totp.verify(totp_code):
            update_user_totp_secret(user.id, secret)
            # Clear the secret from session after successful setup
            session.pop('otp_secret', None)
            flash('Two-Factor Authentication has been successfully enabled!', 'success')
            return redirect(url_for('settings'))
        else:
            flash('Invalid 2FA code. Please try again.', 'danger')
            # Re-render the setup page with the same secret and QR code
            otpauth_url = pyotp.totp.TOTP(secret).provisioning_uri(user.username, issuer_name="BudgetTracker")
            return render_template('setup_2fa.html', totp_secret=secret, otpauth_url=otpauth_url)

@app.route('/disable_2fa', methods=['POST'])
@login_required
def disable_2fa():
    user = current_user
    if user.totp_secret:
        update_user_totp_secret(user.id, None)
        flash('Two-Factor Authentication has been successfully disabled.', 'info')
    else:
        flash('Two-Factor Authentication is not enabled for your account.', 'warning')
    return redirect(url_for('settings'))

@app.route('/delete/<transaction_id>')
@login_required
def delete(transaction_id):
    # Before deleting the transaction, if it's a Saving expense,
    # we need to deduct the amount from the corresponding savings goal.
    transaction = budget_logic.get_transaction(transaction_id)
    if transaction and transaction.get('type') == 'expense' and \
       transaction.get('category') == 'Saving' and transaction.get('savings_goal_id'):
        savings_goals_logic.update_saved_amount(transaction['savings_goal_id'], -transaction['amount'])

    budget_logic.delete_transaction(transaction_id)
    flash('Transaction deleted successfully.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/edit/<transaction_id>', methods=['GET', 'POST'])
@login_required
def edit(transaction_id):
    app_settings = settings_manager.get_settings()
    current_categories = app_settings['expense_categories']
    current_category_icons = app_settings['category_icons']
    savings_goals = savings_goals_logic.get_savings_goals()

    transaction = budget_logic.get_transaction(transaction_id)
    if not transaction:
        flash("Transaction not found", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        old_amount = transaction.get('amount', 0.0)
        old_savings_goal_id = transaction.get('savings_goal_id')

        updated_data = {
            'transaction_id': transaction_id,
            'date': request.form.get('date'),
            'type': request.form.get('type'),
            'category': request.form.get('category'),
            'item': request.form.get('item'),
            'amount': float(request.form.get('amount', 0)),
            'description': request.form.get('description', '')
        }
        
        new_amount = updated_data['amount']
        new_category = updated_data['category']
        new_savings_goal_id = request.form.get('savings_goal_id')


        # Handle savings goal amount updates
        # 1. Undo effect of original transaction on its savings goal (if applicable)
        if transaction.get('type') == 'expense' and transaction.get('category') == 'Goal Savings' and old_savings_goal_id:
            savings_goals_logic.update_saved_amount(old_savings_goal_id, -old_amount)

        # 2. Apply effect of new transaction on its savings goal (if applicable)
        if updated_data['type'] == 'expense' and new_category == 'Goal Savings':
            # Ensure a savings_goal_id is provided for "Goal Savings"
            if not new_savings_goal_id:
                flash('Please select a savings goal for "Goal Savings" category.', 'danger')
                return redirect(url_for('edit', transaction_id=transaction_id))
            
            savings_goals_logic.update_saved_amount(new_savings_goal_id, new_amount)
            updated_data['savings_goal_id'] = new_savings_goal_id # Set the ID in the updated data
        elif new_category == 'General Savings' or (new_category != 'Goal Savings' and new_category != 'General Savings'):
            # For General Savings or any other non-Goal Saving category, ensure no savings_goal_id is set
            updated_data['savings_goal_id'] = ''
        
        budget_logic.update_transaction(transaction_id, updated_data)
        flash('Transaction updated successfully.', 'success')
        return redirect(url_for('transactions'))
        
    return render_template('edit.html', transaction=transaction, categories=current_categories, 
                           category_icons=current_category_icons, savings_goals=savings_goals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
