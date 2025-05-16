from flask import Flask, render_template, request, redirect, url_for, flash, session
import csv
import os
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key

# User data storage
USER_FILE = 'users.csv'
TRANSACTION_FILE = 'transactions.csv'
users = {}
pending_requests = []  # Store money requests: [{'from': email, 'to': email, 'amount': float, 'date': timestamp}]


def load_users(csv_file='users.csv'):
    global users
    try:
        with open(csv_file, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users[row['email']] = {
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'phone': row['phone'],
                    'password': row['password'],
                    'pin': row['pin'],
                    'balance': float(row['balance'])
                }
        print(f"[INFO] Loaded {len(users)} users from {csv_file}")
    except FileNotFoundError:
        print(f"[WARNING] User file {csv_file} not found. Creating new file.")
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['email', 'first_name', 'last_name', 'phone', 'password', 'pin', 'balance'])
    except Exception as e:
        print(f"[ERROR] Failed to load users: {e}")

    return users  # <--- ADD THIS


def save_users():
    """Save users to CSV file"""
    try:
        with open(USER_FILE, 'w', newline='') as csvfile:
            # Get field names from the first user entry
            if not users:
                fieldnames = ['email', 'first_name', 'last_name', 'phone', 'password', 'pin', 'balance']
            else:
                fieldnames = ['email'] + list(next(iter(users.values())).keys())

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Convert the dictionary to the right format for writing
            for email, user_data in users.items():
                row = {'email': email}
                row.update(user_data)
                writer.writerow(row)
        print(f"[INFO] Saved {len(users)} users to {USER_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save users: {e}")


def add_transaction(sender, recipient, amount, transaction_type="payment"):
    """Record a transaction in the transaction history"""
    try:
        transaction = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'type': transaction_type
        }

        # Create the file with headers if it doesn't exist
        if not os.path.exists(TRANSACTION_FILE):
            with open(TRANSACTION_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['date', 'sender', 'recipient', 'amount', 'type'])

        # Append the transaction
        with open(TRANSACTION_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'sender', 'recipient', 'amount', 'type'])
            writer.writerow(transaction)

        return True
    except Exception as e:
        print(f"[ERROR] Failed to record transaction: {e}")
        return False


def get_user_transactions(email):
    """Get all transactions for a specific user"""
    transactions = []
    try:
        if os.path.exists(TRANSACTION_FILE):
            with open(TRANSACTION_FILE, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['sender'] == email or row['recipient'] == email:
                        transactions.append({
                            'date': row['date'],
                            'sender': row['sender'],
                            'recipient': row['recipient'],
                            'amount': float(row['amount']),
                            'type': row['type'],
                            'is_outgoing': row['sender'] == email
                        })
        return sorted(transactions, key=lambda x: x['date'], reverse=True)
    except Exception as e:
        print(f"[ERROR] Failed to get transactions: {e}")
        return []


# Routes
@app.route('/')
def index():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email in users and users[email]['password'] == password:
            session['user_email'] = email
            session['user_name'] = users[email]['first_name']
            flash(f"Welcome back, {users[email]['first_name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Please try again.", 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        pin = request.form.get('pin')

        # Basic validation
        if email in users:
            flash("Email already registered.", 'danger')
        elif password != confirm_password:
            flash("Passwords do not match.", 'danger')
        elif len(pin) != 4 or not pin.isdigit():
            flash("PIN must be a 4-digit number.", 'danger')
        else:
            # Add new user
            users[email] = {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'password': password,
                'pin': pin,
                'balance': 100.0  # New users get $100 starting balance
            }
            save_users()
            flash("Registration successful! You can now log in.", 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        flash("Please log in to continue.", 'warning')
        return redirect(url_for('login'))

    email = session['user_email']
    user_data = users[email]

    # Get user's transaction history
    transactions = get_user_transactions(email)

    # Get pending requests for this user
    user_pending_requests = [req for req in pending_requests
                             if req['to'] == email or req['from'] == email]

    return render_template(
        'dashboard.html',
        user=user_data,
        email=email,
        transactions=transactions[:5],  # Show only the 5 most recent transactions
        pending_requests=user_pending_requests
    )


@app.route('/send', methods=['GET', 'POST'])
@app.route('/send', methods=['GET', 'POST'])
def send_money():
    if 'user_email' not in session:
        flash("Please log in to continue.", 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        sender_email = session['user_email']
        recipient_email = request.form.get('recipient_email')
        amount_str = request.form.get('amount')
        pin = request.form.get('pin')

        try:
            amount = float(amount_str)
            if amount <= 0:
                flash("Amount must be positive.", 'danger')
                return redirect(url_for('send_money'))

            if pin != users[sender_email]['pin']:
                flash("Incorrect PIN.", 'danger')
                return redirect(url_for('send_money'))

            if recipient_email not in users:
                flash(f"Recipient {recipient_email} not found.", 'danger')
                return redirect(url_for('send_money'))

            if users[sender_email]['balance'] < amount:
                flash("Insufficient funds.", 'danger')
                return redirect(url_for('send_money'))

            users[sender_email]['balance'] -= amount
            users[recipient_email]['balance'] += amount
            save_users()
            add_transaction(sender_email, recipient_email, amount)

            flash(f"Successfully sent ${amount:.2f} to {recipient_email}.", 'success')
            return redirect(url_for('dashboard'))

        except ValueError:
            flash("Invalid amount. Please enter a number.", 'danger')

    return render_template('send_money.html', users=users)

@app.route('/request', methods=['GET', 'POST'])
def request_money():
    if 'user_email' not in session:
        flash("Please log in to continue.", 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        requester_email = session['user_email']
        target_email = request.form.get('target_email')
        amount_str = request.form.get('amount')

        # Validation
        try:
            amount = float(amount_str)
            if amount <= 0:
                flash("Amount must be positive.", 'danger')
                return redirect(url_for('request_money'))

            if target_email not in users:
                flash(f"User {target_email} not found.", 'danger')
                return redirect(url_for('request_money'))

            # Create money request
            request_data = {
                'from': requester_email,
                'to': target_email,
                'amount': amount,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'id': len(pending_requests)  # Simple ID for the request
            }
            pending_requests.append(request_data)

            flash(f"Money request sent to {target_email} for ${amount:.2f}.", 'success')
            return redirect(url_for('dashboard'))

        except ValueError:
            flash("Invalid amount. Please enter a number.", 'danger')

    return render_template('request_money.html')


@app.route('/requests')
def view_requests():
    if 'user_email' not in session:
        flash("Please log in to continue.", 'warning')
        return redirect(url_for('login'))

    email = session['user_email']

    # Get incoming requests (where this user is being asked for money)
    incoming_requests = [req for req in pending_requests if req['to'] == email]

    # Get outgoing requests (where this user has asked others for money)
    outgoing_requests = [req for req in pending_requests if req['from'] == email]

    return render_template(
        'requests.html',
        incoming_requests=incoming_requests,
        outgoing_requests=outgoing_requests
    )


@app.route('/respond_request/<int:request_id>/<action>')
def respond_request(request_id, action):
    if 'user_email' not in session:
        flash("Please log in to continue.", 'warning')
        return redirect(url_for('login'))

    email = session['user_email']

    # Find the request
    request_data = None
    for req in pending_requests:
        if req['id'] == request_id:
            request_data = req
            break

    if not request_data or request_data['to'] != email:
        flash("Invalid request.", 'danger')
        return redirect(url_for('view_requests'))

    if action == 'approve':
        # Check if user has enough funds
        if users[email]['balance'] < request_data['amount']:
            flash("Insufficient funds to approve this request.", 'danger')
            return redirect(url_for('view_requests'))

        # Process the payment
        users[email]['balance'] -= request_data['amount']
        users[request_data['from']]['balance'] += request_data['amount']
        save_users()

        # Record transaction
        add_transaction(email, request_data['from'], request_data['amount'], "request_payment")

        flash(f"Payment of ${request_data['amount']:.2f} to {request_data['from']} completed.", 'success')

        # Remove the request
        pending_requests.remove(request_data)

    elif action == 'reject':
        flash("Request rejected.", 'info')
        # Remove the request
        pending_requests.remove(request_data)

    return redirect(url_for('view_requests'))


@app.route('/transactions')
def transaction_history():
    if 'user_email' not in session:
        flash("Please log in to continue.", 'warning')
        return redirect(url_for('login'))

    email = session['user_email']
    user_data = users.get(email)

    if not user_data:
        flash("User data not found.", 'danger')
        return redirect(url_for('logout'))

    transactions = get_user_transactions(email)

    return render_template(
        'transactions.html',
        user=user_data,
        email=email,
        transactions=transactions
    )

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    load_users()
    app.run(host='192.168.29.114', port=2410, debug=True)
