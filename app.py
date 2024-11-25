from flask import Flask, render_template, request, redirect, url_for, session, flash
import random
import os

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
            # Try to convert the balance to a float, if it fails, set it to 0.0
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
                'transactions': []
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
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        id_number = request.form['id_number']
        username = request.form['username']
        password = request.form['password']

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
        account['transactions'].append(f"Deposited R{amount:.2f}")  # Save the transaction


        save_accounts(accounts)
        flash(f"Deposited R{amount:.2f}")
        return redirect(url_for('dashboard'))

    return render_template('deposit.html')  # You need a form here for GET request

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
        account['transactions'].append(f"Withdrew R{amount:.2f}")  # Save the transaction

        save_accounts(accounts)
        flash(f"Withdrew R{amount:.2f}")
        return redirect(url_for('dashboard'))

    return render_template('withdraw.html')  # You need a form here for GET request

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'username' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        recipient_username = request.form['recipient_username']
        amount = float(request.form['amount'])

        if amount <= 0:
            flash("Transfer amount must be positive.")
            return redirect(url_for('transfer'))

        username = session['username']
        accounts = load_accounts()

        if recipient_username not in accounts:
            flash("Recipient not found.")
            return redirect(url_for('transfer'))

        sender_account = accounts[username]
        recipient_account = accounts[recipient_username]

        if sender_account['balance'] < amount:
            flash("Insufficient funds for this transfer.")
            return redirect(url_for('transfer'))

        # Perform the transfer
        sender_account['balance'] -= amount
        recipient_account['balance'] += amount
        sender_account['transactions'].append(f"Transferred R{amount:.2f} to {recipient_username}")  # Save sender transaction
        recipient_account['transactions'].append(f"Received R{amount:.2f} from {username}")  # Save recipient transaction

        save_accounts(accounts)
        flash(f"Transferred R{amount:.2f} to {recipient_username}")
        return redirect(url_for('dashboard'))

    return render_template('transfer.html')  # This will show the transfer form
    

@app.route('/transaction_history')
def transaction_history():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    accounts = load_accounts()
    account = accounts[username]
    return render_template('transaction_history.html', transactions=account['transactions'])

if __name__ == '__main__':
    app.run(debug=True)
