from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import random
import os
import csv
from io import StringIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# File-based "database" for storing user data (in a real app, use a proper database)
DB_FILE = 'account_db.txt'

# Helper functions
def load_accounts():
    """Load all accounts from the database."""
    if not os.path.exists(DB_FILE):
        return {}
    
    accounts = {}
    with open(DB_FILE, 'r') as file:
        for line in file:
            parts = line.strip().split(',')
            try:
                balance = float(parts[8])
            except ValueError:
                balance = 0.0  # Default to 0.0 if conversion fails
            
            accounts[parts[6]] = {
                'name': parts[1],
                'surname': parts[2],
                'phone': parts[3],
                'id_number': parts[4],
                'account_number': parts[5],
                'username': parts[6],
                'password': parts[7],
                'balance': balance,
                'transactions': []  # Add transactions to each account
            }
    return accounts

def save_accounts(accounts):
    """Save all accounts to the database."""
    with open(DB_FILE, 'w') as file:
        for username, data in accounts.items():
            file.write(f"{username},{data['name']},{data['surname']},{data['phone']}," 
                       f"{data['id_number']},{data['account_number']},{data['username']}," 
                       f"{data['password']},{data['balance']}\n")

def generate_account_number():
    """Generate a random account number."""
    return f"{random.randint(1000000000, 9999999999)}"

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    accounts = load_accounts()
    
    if username in accounts and accounts[username]['password'] == password:
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid login credentials, please try again.')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    accounts = load_accounts()
    account = accounts[username]
    return render_template('dashboard.html', account=account)

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        try:
            print(request.form)  # Debugging: See what data is sent

            name = request.form['name']  # Matches updated form field name
            surname = request.form['surname']
            phone = request.form['phone']
            id_number = request.form['id_number']
            username = request.form['username']
            password = request.form['password']

            if not name or not surname or not phone or not id_number or not username or not password:
                flash("All fields are required!")
                return redirect(url_for('create_account'))

            account_number = generate_account_number()

            accounts = load_accounts()
            if username in accounts:
                flash("Username already exists. Please choose another one.")
                return redirect(url_for('create_account'))
            
            # Save the new account to the file
            accounts[username] = {
                'name': name,
                'surname': surname,
                'phone': phone,
                'id_number': id_number,
                'account_number': account_number,
                'username': username,
                'password': password,
                'balance': 0.0,
                'transactions': []
            }

            save_accounts(accounts)
            flash("Account created successfully. Please login.")
            return redirect(url_for('index'))

        except KeyError as e:
            flash(f"Missing field: {str(e)}")  # Show error if a field is missing
            return redirect(url_for('create_account'))

    return render_template('create_account.html')

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if 'username' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        if amount <= 0:
            flash("Deposit amount must be positive.")
            return redirect(url_for('deposit'))

        username = session['username']
        accounts = load_accounts()
        account = accounts[username]
        account['balance'] += amount

        # Create a structured transaction entry
        transaction = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'Deposit',
            'amount': amount,
            'details': f"Deposited R{amount:.2f}",
            'balance_after': account['balance']
        }
        account['transactions'].append(transaction)

        save_accounts(accounts)
        flash(f"Deposited R{amount:.2f}")
        return redirect(url_for('dashboard'))

    return render_template('deposit.html')

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'username' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        if amount <= 0:
            flash("Withdrawal amount must be positive.")
            return redirect(url_for('withdraw'))

        username = session['username']
        accounts = load_accounts()
        account = accounts[username]

        if account['balance'] < amount:
            flash("Insufficient funds for this withdrawal.")
            return redirect(url_for('withdraw'))

        account['balance'] -= amount

        # Create a structured transaction entry
        transaction = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'Withdrawal',
            'amount': amount,
            'details': f"Withdrew R{amount:.2f}",
            'balance_after': account['balance']
        }
        account['transactions'].append(transaction)

        save_accounts(accounts)
        flash(f"Withdrew R{amount:.2f}")
        return redirect(url_for('dashboard'))

    return render_template('withdraw.html')


@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session.get('username')
    if not username:
        return redirect(url_for('index'))

    if request.method == 'POST':
        recipient_username = request.form.get('recipient')
        amount = request.form.get('amount')

        if not recipient_username or not amount:
            flash("Recipient and amount are required.")
            return redirect(url_for('transfer'))

        try:
            amount = float(amount)
            if amount <= 0:
                flash("Transfer amount must be positive.")
                return redirect(url_for('transfer'))
        except ValueError:
            flash("Invalid amount entered.")
            return redirect(url_for('transfer'))

        accounts = load_accounts()
        if recipient_username not in accounts:
            flash("Recipient not found.")
            return redirect(url_for('transfer'))

        sender_account = accounts.get(username)
        recipient_account = accounts.get(recipient_username)

        if sender_account['balance'] < amount:
            flash("Insufficient funds for this transfer.")
            return redirect(url_for('transfer'))

        # Perform the transfer
        sender_account['balance'] -= amount
        recipient_account['balance'] += amount

        # Create structured transactions
        sender_transaction = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'Transfer',
            'amount': amount,
            'details': f"Transferred R{amount:.2f} to {recipient_username}",
            'balance_after': sender_account['balance']
        }
        recipient_transaction = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'Transfer',
            'amount': amount,
            'details': f"Received R{amount:.2f} from {username}",
            'balance_after': recipient_account['balance']
        }

        sender_account['transactions'].append(sender_transaction)
        recipient_account['transactions'].append(recipient_transaction)

        save_accounts(accounts)
        flash(f"Transferred R{amount:.2f} to {recipient_username}")
        return redirect(url_for('dashboard'))

    return render_template('transfer.html')


@app.route('/transaction_history', methods=['GET', 'POST'])
def transaction_history():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    accounts = load_accounts()
    account = accounts[username]
    transactions = account['transactions']

    # Filtering functionality
    if request.method == 'POST':
        transaction_type = request.form.get('transaction_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # Filter by transaction type
        if transaction_type != 'All':
            transactions = [t for t in transactions if t['type'] == transaction_type]

        # Filter by date range
        if start_date:
            transactions = [t for t in transactions if t['timestamp'] >= start_date]

        if end_date:
            transactions = [t for t in transactions if t['timestamp'] <= end_date]

    return render_template('transaction_history.html', transactions=transactions)

@app.route('/export_transactions')
def export_transactions():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    accounts = load_accounts()
    account = accounts[username]
    transactions = account['transactions']

    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Type', 'Amount', 'Details', 'Balance After'])
    
    for transaction in transactions:
        writer.writerow([transaction['timestamp'], transaction['type'], transaction['amount'],
                         transaction['details'], transaction['balance_after']])
    
    output.seek(0)

    # Send as a CSV file for download
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=transactions.csv'})

if __name__ == '__main__':
    app.run(debug=True)
