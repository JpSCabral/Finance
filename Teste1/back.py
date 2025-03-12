# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from decimal import Decimal
import json
from functools import wraps
import calendar

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-for-testing'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///fintrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    merchant = db.Column(db.String(120), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': float(self.amount),
            'date': self.date.isoformat(),
            'category': self.category,
            'merchant': self.merchant
        }

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'amount': float(self.amount),
            'month': self.month,
            'year': self.year
        }

# Create tables
with app.app_context():
    db.create_all()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get current month and year
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Get summary data
    total_income = db.session.query(db.func.sum(Transaction.amount)).\
        filter(Transaction.user_id == user_id).\
        filter(Transaction.amount > 0).scalar() or 0
    
    total_expenses = db.session.query(db.func.sum(Transaction.amount)).\
        filter(Transaction.user_id == user_id).\
        filter(Transaction.amount < 0).scalar() or 0
    
    total_balance = total_income + total_expenses
    
    # Calculate savings rate if there's income
    savings_rate = 0
    if total_income > 0:
        savings_rate = (total_income + total_expenses) / total_income * 100
    
    # Get recent transactions
    recent_transactions = Transaction.query.\
        filter_by(user_id=user_id).\
        order_by(Transaction.date.desc()).\
        limit(5).all()
    
    # Get budget progress
    budgets = Budget.query.\
        filter_by(user_id=user_id, month=current_month, year=current_year).all()
    
    budget_progress = []
    for budget in budgets:
        # Get spent amount for this category in current month
        spent = db.session.query(db.func.sum(Transaction.amount)).\
            filter(Transaction.user_id == user_id).\
            filter(Transaction.category == budget.category).\
            filter(db.extract('month', Transaction.date) == current_month).\
            filter(db.extract('year', Transaction.date) == current_year).\
            filter(Transaction.amount < 0).scalar() or 0
        
        # Convert to positive number for display
        spent = abs(float(spent))
        budget_amount = float(budget.amount)
        
        # Calculate percentage
        percentage = (spent / budget_amount) * 100 if budget_amount > 0 else 0
        
        # Determine status
        if percentage < 70:
            status = "good"
        elif percentage < 90:
            status = "warning"
        else:
            status = "danger"
        
        budget_progress.append({
            'category': budget.category,
            'spent': spent,
            'budget_amount': budget_amount,
            'percentage': percentage,
            'status': status
        })
    
    # Get calendar data
    cal = calendar.monthcalendar(current_year, current_month)
    
    # Get dates with transactions
    transaction_dates = db.session.query(db.func.extract('day', Transaction.date)).\
        filter(Transaction.user_id == user_id).\
        filter(db.extract('month', Transaction.date) == current_month).\
        filter(db.extract('year', Transaction.date) == current_year).\
        distinct().all()
    
    transaction_days = [int(day[0]) for day in transaction_dates]
    
    # Calculate month-over-month changes
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_year = current_year if current_month > 1 else current_year - 1
    
    prev_income = db.session.query(db.func.sum(Transaction.amount)).\
        filter(Transaction.user_id == user_id).\
        filter(Transaction.amount > 0).\
        filter(db.extract('month', Transaction.date) == previous_month).\
        filter(db.extract('year', Transaction.date) == previous_year).scalar() or 0
    
    prev_expenses = db.session.query(db.func.sum(Transaction.amount)).\
        filter(Transaction.user_id == user_id).\
        filter(Transaction.amount < 0).\
        filter(db.extract('month', Transaction.date) == previous_month).\
        filter(db.extract('year', Transaction.date) == previous_year).scalar() or 0
    
    prev_balance = prev_income + prev_expenses
    
    # Calculate percentage changes
    income_change = ((total_income - prev_income) / prev_income * 100) if prev_income != 0 else 0
    expense_change = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses != 0 else 0
    balance_change = ((total_balance - prev_balance) / prev_balance * 100) if prev_balance != 0 else 0
    
    # Savings rate change
    prev_savings_rate = 0
    if prev_income > 0:
        prev_savings_rate = (prev_income + prev_expenses) / prev_income * 100
    
    savings_change = savings_rate - prev_savings_rate
    
    return render_template('dashboard.html', 
                          user=user,
                          total_balance=total_balance,
                          total_income=total_income,
                          total_expenses=total_expenses,
                          savings_rate=savings_rate,
                          recent_transactions=recent_transactions,
                          budget_progress=budget_progress,
                          calendar=cal,
                          transaction_days=transaction_days,
                          current_day=now.day,
                          current_month=current_month,
                          current_month_name=now.strftime('%B'),
                          current_year=current_year,
                          balance_change=balance_change,
                          income_change=income_change,
                          expense_change=expense_change,
                          savings_change=savings_change)

# Transaction routes
@app.route('/transactions')
@login_required
def transactions():
    user_id = session['user_id']
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
    return render_template('transactions.html', transactions=transactions)

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        description = request.form.get('description')
        amount = request.form.get('amount')
        category = request.form.get('category')
        date_str = request.form.get('date')
        merchant = request.form.get('merchant')
        
        # Convert string to float
        try:
            amount = float(amount)
            # Make expenses negative
            if 'expense' in request.form and amount > 0:
                amount = -amount
        except ValueError:
            flash('Invalid amount')
            return redirect(url_for('add_transaction'))
        
        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            date = datetime.utcnow()
        
        transaction = Transaction(
            description=description,
            amount=amount,
            category=category,
            date=date,
            merchant=merchant,
            user_id=session['user_id']
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transaction added successfully')
        return redirect(url_for('transactions'))
    
    return render_template('add_transaction.html')

@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Make sure user can only edit their own transactions
    if transaction.user_id != session['user_id']:
        flash('Unauthorized')
        return redirect(url_for('transactions'))
    
    if request.method == 'POST':
        transaction.description = request.form.get('description')
        
        amount = float(request.form.get('amount'))
        if 'expense' in request.form and amount > 0:
            amount = -amount
        transaction.amount = amount
        
        transaction.category = request.form.get('category')
        transaction.merchant = request.form.get('merchant')
        
        date_str = request.form.get('date')
        try:
            transaction.date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            pass
        
        db.session.commit()
        flash('Transaction updated successfully')
        return redirect(url_for('transactions'))
    
    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Make sure user can only delete their own transactions
    if transaction.user_id != session['user_id']:
        flash('Unauthorized')
        return redirect(url_for('transactions'))
    
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully')
    return redirect(url_for('transactions'))

# Budget routes
@app.route('/budgets')
@login_required
def budgets():
    user_id = session['user_id']
    
    # Get current month and year
    now = datetime.now()
    month = request.args.get('month', type=int) or now.month
    year = request.args.get('year', type=int) or now.year
    
    budgets = Budget.query.\
        filter_by(user_id=user_id, month=month, year=year).all()
    
    # Get spending for each category
    budget_data = []
    for budget in budgets:
        spent = db.session.query(db.func.sum(Transaction.amount)).\
            filter(Transaction.user_id == user_id).\
            filter(Transaction.category == budget.category).\
            filter(db.extract('month', Transaction.date) == month).\
            filter(db.extract('year', Transaction.date) == year).\
            filter(Transaction.amount < 0).scalar() or 0
        
        # Convert to positive number for display
        spent = abs(float(spent))
        
        budget_data.append({
            'id': budget.id,
            'category': budget.category,
            'amount': float(budget.amount),
            'spent': spent,
            'percentage': (spent / float(budget.amount) * 100) if float(budget.amount) > 0 else 0
        })
    
    # Get months for navigation
    months = []
    for m in range(1, 13):
        months.append({
            'number': m,
            'name': calendar.month_name[m]
        })
    
    return render_template('budgets.html', 
                          budgets=budget_data, 
                          current_month=month,
                          current_month_name=calendar.month_name[month],
                          current_year=year,
                          months=months)

@app.route('/budgets/add', methods=['GET', 'POST'])
@login_required
def add_budget():
    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        month = request.form.get('month', type=int)
        year = request.form.get('year', type=int)
        
        # Default to current month/year if not provided
        if not month or not year:
            now = datetime.now()
            month = month or now.month
            year = year or now.year
        
        # Check if budget already exists for this category/month/year
        existing = Budget.query.\
            filter_by(user_id=session['user_id'], category=category, month=month, year=year).first()
        
        if existing:
            flash('Budget for this category already exists for the selected month')
            return redirect(url_for('budgets'))
        
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount')
            return redirect(url_for('add_budget'))
        
        budget = Budget(
            category=category,
            amount=amount,
            month=month,
            year=year,
            user_id=session['user_id']
        )
        
        db.session.add(budget)
        db.session.commit()
        
        flash('Budget added successfully')
        return redirect(url_for('budgets'))
    
    # Get all unique categories from transactions
    user_id = session['user_id']
    categories = db.session.query(Transaction.category).\
        filter(Transaction.user_id == user_id).\
        distinct().all()
    
    categories = [cat[0] for cat in categories]
    
    # Get months for dropdown
    months = []
    for m in range(1, 13):
        months.append({
            'number': m,
            'name': calendar.month_name[m]
        })
    
    now = datetime.now()
    
    return render_template('add_budget.html', 
                          categories=categories,
                          months=months,
                          current_month=now.month,
                          current_year=now.year)

@app.route('/budgets/<int:budget_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    
    # Make sure user can only edit their own budgets
    if budget.user_id != session['user_id']:
        flash('Unauthorized')
        return redirect(url_for('budgets'))
    
    if request.method == 'POST':
        budget.amount = float(request.form.get('amount'))
        db.session.commit()
        flash('Budget updated successfully')
        return redirect(url_for('budgets'))
    
    return render_template('edit_budget.html', budget=budget)

@app.route('/budgets/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    
    # Make sure user can only delete their own budgets
    if budget.user_id != session['user_id']:
        flash('Unauthorized')
        return redirect(url_for('budgets'))
    
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted successfully')
    return redirect(url_for('budgets'))

# API endpoints for AJAX requests
@app.route('/api/transactions', methods=['GET'])
@login_required
def api_transactions():
    user_id = session['user_id']
    
    # Get query parameters
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    category = request.args.get('category')
    
    # Build query
    query = Transaction.query.filter_by(user_id=user_id)
    
    if month:
        query = query.filter(db.extract('month', Transaction.date) == month)
    
    if year:
        query = query.filter(db.extract('year', Transaction.date) == year)
    
    if category:
        query = query.filter_by(category=category)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    
    return jsonify([t.to_dict() for t in transactions])

@app.route('/api/budget-summary', methods=['GET'])
@login_required
def api_budget_summary():
    user_id = session['user_id']
    
    # Get current month and year
    now = datetime.now()
    month = request.args.get('month', type=int) or now.month
    year = request.args.get('year', type=int) or now.year
    
    # Get all budgets for the month
    budgets = Budget.query.\
        filter_by(user_id=user_id, month=month, year=year).all()
    
    # Calculate total budget and spent
    total_budget = sum(float(b.amount) for b in budgets)
    
    # Get total spent (expenses only)
    total_spent = db.session.query(db.func.sum(Transaction.amount)).\
        filter(Transaction.user_id == user_id).\
        filter(db.extract('month', Transaction.date) == month).\
        filter(db.extract('year', Transaction.date) == year).\
        filter(Transaction.amount < 0).scalar() or 0
    
    # Convert to positive number
    total_spent = abs(float(total_spent))
    
    # Calculate remaining budget
    remaining = total_budget - total_spent
    
    # Get spending by category
    categories = db.session.query(
        Transaction.category,
        db.func.sum(Transaction.amount).label('amount')
    ).\
    filter(Transaction.user_id == user_id).\
    filter(db.extract('month', Transaction.date) == month).\
    filter(db.extract('year', Transaction.date) == year).\
    filter(Transaction.amount < 0).\
    group_by(Transaction.category).all()
    
    category_data = []
    for cat, amount in categories:
        category_data.append({
            'category': cat,
            'amount': abs(float(amount))
        })
    
    return jsonify({
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining': remaining,
        'categories': category_data
    })

@app.route('/api/income-expense-summary', methods=['GET'])
@login_required
def api_income_expense_summary():
    user_id = session['user_id']
    
    # Get date range (last 6 months by default)
    months = 6
    end_date = datetime.now()
    
    # Build summary data
    summary = []
    for i in range(months):
        # Calculate month and year
        month = end_date.month - i
        year = end_date.year
        
        while month <= 0:
            month += 12
            year -= 1
        
        # Get income and expenses for this month
        income = db.session.query(db.func.sum(Transaction.amount)).\
            filter(Transaction.user_id == user_id).\
            filter(db.extract('month', Transaction.date) == month).\
            filter(db.extract('year', Transaction.date) == year).\
            filter(Transaction.amount > 0).scalar() or 0
        
        expenses = db.session.query(db.func.sum(Transaction.amount)).\
            filter(Transaction.user_id == user_id).\
            filter(db.extract('month', Transaction.date) == month).\
            filter(db.extract('year', Transaction.date) == year).\
            filter(Transaction.amount < 0).scalar() or 0
        
        # Convert expenses to positive number
        expenses = abs(float(expenses))
        income = float(income)
        
        # Get month name
        month_name = calendar.month_name[month][:3] + " " + str(year)
        
        summary.append({
            'month': month_name,
            'income': income,
            'expenses': expenses,
            'balance': income - expenses
        })
    
    # Reverse to get chronological order
    summary.reverse()
    
    return jsonify(summary)

if __name__ == '__main__':
    app.run(debug=True)