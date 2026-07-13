import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ─── App Configuration ────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nexbank-loan-prediction-secret-2024'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# ── Vercel: filesystem is read-only except /tmp ───────────────────────────────
IS_VERCEL = os.environ.get('VERCEL') == '1'

if IS_VERCEL:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/bank.db'
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to continue.'
login_manager.login_message_category = 'warning'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─── Database Models ─────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    loans = db.relationship('LoanApplication', backref='user', lazy=True)
    account = db.relationship('BankAccount', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Personal Details
    full_name = db.Column(db.String(150))
    pan_number = db.Column(db.String(15))
    date_of_birth = db.Column(db.String(20))
    employment_type = db.Column(db.String(50))
    employer_name = db.Column(db.String(150))
    annual_income = db.Column(db.Float)

    # Loan Details
    loan_type = db.Column(db.String(50))
    loan_amount = db.Column(db.Float)
    tenure_months = db.Column(db.Integer)
    purpose = db.Column(db.String(200))

    # CIBIL
    cibil_score = db.Column(db.Integer)
    cibil_status = db.Column(db.String(20))  # passed / failed

    # Documents
    doc_aadhaar = db.Column(db.String(300))
    doc_pan = db.Column(db.String(300))
    doc_salary_slip = db.Column(db.String(300))
    doc_bank_statement = db.Column(db.String(300))
    docs_uploaded = db.Column(db.Boolean, default=False)

    # Result
    status = db.Column(db.String(30), default='pending')  # pending / approved / rejected
    approval_score = db.Column(db.Float, default=0)
    rejection_reason = db.Column(db.String(300))
    interest_rate = db.Column(db.Float)
    monthly_emi = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BankAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    account_number = db.Column(db.String(16), unique=True, nullable=False)
    account_type = db.Column(db.String(30), default='savings')  # savings / current
    balance = db.Column(db.Float, default=50000.00)  # demo default balance
    ifsc_code = db.Column(db.String(15), default='NEXA0001234')
    branch = db.Column(db.String(100), default='NexaBank Digital Branch')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions_sent = db.relationship('Transaction', foreign_keys='Transaction.sender_account_id', backref='sender_account', lazy=True)
    transactions_received = db.relationship('Transaction', foreign_keys='Transaction.receiver_account_id', backref='receiver_account', lazy=True)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(30), unique=True, nullable=False)
    sender_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    receiver_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=True)
    receiver_account_number = db.Column(db.String(16), nullable=False)
    receiver_name = db.Column(db.String(150))
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # transfer / credit / debit
    remarks = db.Column(db.String(200))
    status = db.Column(db.String(20), default='success')  # success / failed / pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── Loan Prediction Logic ──────────────────────────────────────────────────────
def predict_loan(cibil_score, annual_income, loan_amount, tenure_months, employment_type):
    """Rule-based loan prediction engine."""
    score = 0
    reasons = []
    interest_rate = 10.5  # base rate

    # 1. CIBIL Score (40% weight)
    # Minimum required: 600  (relaxed from 650 so borderline applicants proceed to doc check)
    if cibil_score >= 800:
        score += 40
        interest_rate = 8.5
    elif cibil_score >= 750:
        score += 36
        interest_rate = 9.0
    elif cibil_score >= 700:
        score += 30
        interest_rate = 10.5
    elif cibil_score >= 650:
        score += 22
        interest_rate = 12.0
        reasons.append("Moderate CIBIL score")
    elif cibil_score >= 600:
        score += 12
        interest_rate = 14.0
        reasons.append("Low CIBIL score")
    else:
        return {
            'status': 'rejected',
            'score': 0,
            'reason': f'CIBIL score {cibil_score} is below the minimum required score of 600.',
            'interest_rate': None,
            'monthly_emi': None
        }

    # 2. Income vs Loan Amount (30% weight)
    if annual_income > 0:
        loan_to_income = loan_amount / annual_income
        if loan_to_income <= 2:
            score += 30
        elif loan_to_income <= 4:
            score += 25
        elif loan_to_income <= 6:
            score += 18
            reasons.append("High loan-to-income ratio")
        elif loan_to_income <= 10:
            score += 10
            reasons.append("Very high loan-to-income ratio")
        else:
            score += 5
            reasons.append("Loan amount very high relative to income")
    else:
        score += 5

    # 3. Employment Type (20% weight)
    emp_scores = {
        'salaried_government': 20,
        'salaried_private': 18,
        'self_employed': 14,
        'business': 16,
        'freelancer': 11,
    }
    score += emp_scores.get(employment_type, 13)

    # 4. Tenure (10% weight)
    if 12 <= tenure_months <= 60:
        score += 10
    elif tenure_months <= 84:
        score += 8
    elif tenure_months <= 180:
        score += 6
    else:
        score += 4

    # Calculate EMI
    monthly_rate = (interest_rate / 100) / 12
    if monthly_rate == 0:
        emi = loan_amount / tenure_months
    else:
        emi = (loan_amount * monthly_rate * (1 + monthly_rate) ** tenure_months) / \
              ((1 + monthly_rate) ** tenure_months - 1)

    # Approval thresholds (out of 100)
    if score >= 65:
        status = 'approved'
        reason = None
    elif score >= 42:
        status = 'approved'
        reason = "Conditionally approved – subject to document verification."
        interest_rate = round(interest_rate + 1.0, 2)
    else:
        status = 'rejected'
        reason = "Application does not meet minimum eligibility criteria. " + "; ".join(reasons) if reasons else \
                 "Application does not meet our minimum credit eligibility criteria."

    return {
        'status': status,
        'score': round(score, 2),
        'reason': reason,
        'interest_rate': round(interest_rate, 2),
        'monthly_emi': round(emi, 2)
    }


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_app_id():
    return 'NEXA' + datetime.now().strftime('%Y%m%d') + str(uuid.uuid4())[:6].upper()


def generate_account_number():
    """Generate a unique 12-digit account number."""
    import random
    while True:
        acc_no = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        if not BankAccount.query.filter_by(account_number=acc_no).first():
            return acc_no


def generate_txn_id():
    return 'TXN' + datetime.now().strftime('%Y%m%d%H%M%S') + str(uuid.uuid4())[:4].upper()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([full_name, email, phone, password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('register.html')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html')

        user = User(full_name=full_name, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id before commit

        # Auto-create bank account for new user
        account = BankAccount(
            user_id=user.id,
            account_number=generate_account_number(),
            account_type='savings',
            balance=50000.00  # demo welcome balance
        )
        db.session.add(account)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(remember))
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.full_name.split()[0]}!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    loans = LoanApplication.query.filter_by(user_id=current_user.id)\
                .order_by(LoanApplication.created_at.desc()).all()
    return render_template('dashboard.html', loans=loans)


# ── Loan Application Step 1: Personal & Loan Details ──────────────────────────
@app.route('/apply-loan', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if request.method == 'POST':
        # Store step-1 data in session
        session['loan_data'] = {
            'full_name': request.form.get('full_name'),
            'pan_number': request.form.get('pan_number').upper(),
            'date_of_birth': request.form.get('date_of_birth'),
            'employment_type': request.form.get('employment_type'),
            'employer_name': request.form.get('employer_name'),
            'annual_income': float(request.form.get('annual_income', 0)),
            'loan_type': request.form.get('loan_type'),
            'loan_amount': float(request.form.get('loan_amount', 0)),
            'tenure_months': int(request.form.get('tenure_months', 12)),
            'purpose': request.form.get('purpose'),
        }
        return redirect(url_for('cibil_check'))

    return render_template('apply_loan.html')


# ── Loan Application Step 2: CIBIL Score ──────────────────────────────────────
@app.route('/cibil-check', methods=['GET', 'POST'])
@login_required
def cibil_check():
    if 'loan_data' not in session:
        flash('Please start the loan application first.', 'warning')
        return redirect(url_for('apply_loan'))

    if request.method == 'POST':
        cibil_score = int(request.form.get('cibil_score', 0))

        if cibil_score < 300 or cibil_score > 900:
            flash('CIBIL score must be between 300 and 900.', 'danger')
            return render_template('cibil_check.html')

        session['loan_data']['cibil_score'] = cibil_score
        session.modified = True  # ← CRITICAL: Flask won't detect nested dict mutations without this

        if cibil_score < 600:
            # Reject immediately, save to DB
            loan_data = session['loan_data']
            app_id = generate_app_id()
            loan = LoanApplication(
                application_id=app_id,
                user_id=current_user.id,
                **{k: v for k, v in loan_data.items()},
                cibil_status='failed',
                status='rejected',
                rejection_reason=f'CIBIL score {cibil_score} is below the minimum required score of 600.',
                docs_uploaded=False,
                approval_score=0
            )
            db.session.add(loan)
            db.session.commit()
            session.pop('loan_data', None)
            return redirect(url_for('loan_result', app_id=app_id))

        session['loan_data']['cibil_status'] = 'passed'
        session.modified = True  # ← Force session save again after second mutation
        return redirect(url_for('upload_docs'))

    return render_template('cibil_check.html', loan_data=session.get('loan_data', {}))


# ── Loan Application Step 3: Upload Documents ─────────────────────────────────
@app.route('/upload-docs', methods=['GET', 'POST'])
@login_required
def upload_docs():
    if 'loan_data' not in session:
        flash('Please start the loan application first.', 'warning')
        return redirect(url_for('apply_loan'))

    loan_data = session['loan_data']
    if loan_data.get('cibil_status') != 'passed':
        flash('CIBIL check not completed.', 'warning')
        return redirect(url_for('cibil_check'))

    if request.method == 'POST':
        doc_paths = {}
        doc_fields = ['doc_aadhaar', 'doc_pan', 'doc_salary_slip', 'doc_bank_statement']
        required_docs = ['doc_aadhaar', 'doc_pan', 'doc_salary_slip']

        for field in doc_fields:
            file = request.files.get(field)
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{current_user.id}_{field}_{uuid.uuid4().hex[:8]}.{ext}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                doc_paths[field] = filename

        # Check required docs
        missing = [d for d in required_docs if d not in doc_paths]
        if missing:
            labels = {'doc_aadhaar': 'Aadhaar Card', 'doc_pan': 'PAN Card', 'doc_salary_slip': 'Salary Slip'}
            missing_names = [labels.get(m, m) for m in missing]
            flash(f'Please upload required documents: {", ".join(missing_names)}', 'danger')
            return render_template('upload_docs.html', loan_data=loan_data)

        # Run loan prediction
        prediction = predict_loan(
            cibil_score=loan_data['cibil_score'],
            annual_income=loan_data['annual_income'],
            loan_amount=loan_data['loan_amount'],
            tenure_months=loan_data['tenure_months'],
            employment_type=loan_data['employment_type']
        )

        app_id = generate_app_id()
        loan = LoanApplication(
            application_id=app_id,
            user_id=current_user.id,
            full_name=loan_data['full_name'],
            pan_number=loan_data['pan_number'],
            date_of_birth=loan_data['date_of_birth'],
            employment_type=loan_data['employment_type'],
            employer_name=loan_data['employer_name'],
            annual_income=loan_data['annual_income'],
            loan_type=loan_data['loan_type'],
            loan_amount=loan_data['loan_amount'],
            tenure_months=loan_data['tenure_months'],
            purpose=loan_data['purpose'],
            cibil_score=loan_data['cibil_score'],
            cibil_status=loan_data['cibil_status'],
            doc_aadhaar=doc_paths.get('doc_aadhaar'),
            doc_pan=doc_paths.get('doc_pan'),
            doc_salary_slip=doc_paths.get('doc_salary_slip'),
            doc_bank_statement=doc_paths.get('doc_bank_statement'),
            docs_uploaded=True,
            status=prediction['status'],
            approval_score=prediction['score'],
            rejection_reason=prediction.get('reason'),
            interest_rate=prediction.get('interest_rate'),
            monthly_emi=prediction.get('monthly_emi')
        )
        db.session.add(loan)
        db.session.commit()
        session.pop('loan_data', None)
        return redirect(url_for('loan_result', app_id=app_id))

    return render_template('upload_docs.html', loan_data=loan_data)


# ── Loan Result ────────────────────────────────────────────────────────────────
@app.route('/loan-result/<app_id>')
@login_required
def loan_result(app_id):
    loan = LoanApplication.query.filter_by(
        application_id=app_id, user_id=current_user.id
    ).first_or_404()
    return render_template('loan_result.html', loan=loan)


# ── AJAX: EMI Calculator ───────────────────────────────────────────────────────
@app.route('/calculate-emi', methods=['POST'])
def calculate_emi():
    data = request.get_json()
    principal = float(data.get('principal', 0))
    rate = float(data.get('rate', 10.5))
    tenure = int(data.get('tenure', 12))
    monthly_rate = (rate / 100) / 12
    if monthly_rate == 0:
        emi = principal / tenure
    else:
        emi = (principal * monthly_rate * (1 + monthly_rate) ** tenure) / \
              ((1 + monthly_rate) ** tenure - 1)
    total = emi * tenure
    return jsonify({
        'emi': round(emi, 2),
        'total': round(total, 2),
        'interest': round(total - principal, 2)
    })


# ── Money Transfer ─────────────────────────────────────────────────────────────
@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    account = BankAccount.query.filter_by(user_id=current_user.id).first()
    if not account:
        flash('No bank account found. Please contact support.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        receiver_acc_no = request.form.get('receiver_account', '').strip()
        receiver_name   = request.form.get('receiver_name', '').strip()
        amount          = float(request.form.get('amount', 0))
        remarks         = request.form.get('remarks', '').strip()
        transfer_type   = request.form.get('transfer_type', 'IMPS')

        # Validations
        if not receiver_acc_no or not receiver_name:
            flash('Please fill in all required fields.', 'danger')
            return render_template('transfer.html', account=account)

        if receiver_acc_no == account.account_number:
            flash('You cannot transfer to your own account.', 'danger')
            return render_template('transfer.html', account=account)

        if amount <= 0:
            flash('Please enter a valid amount greater than 0.', 'danger')
            return render_template('transfer.html', account=account)

        if amount > account.balance:
            flash(f'Insufficient balance. Available: ₹{account.balance:,.2f}', 'danger')
            return render_template('transfer.html', account=account)

        if amount > 200000:
            flash('Single transfer limit is ₹2,00,000. Please split your transfer.', 'danger')
            return render_template('transfer.html', account=account)

        # Check if receiver exists in system
        receiver_account = BankAccount.query.filter_by(account_number=receiver_acc_no).first()

        # Deduct from sender
        account.balance -= amount

        # Credit to receiver if internal
        if receiver_account:
            receiver_account.balance += amount

        txn_id = generate_txn_id()
        txn = Transaction(
            transaction_id=txn_id,
            sender_account_id=account.id,
            receiver_account_id=receiver_account.id if receiver_account else None,
            receiver_account_number=receiver_acc_no,
            receiver_name=receiver_name,
            amount=amount,
            transaction_type='transfer',
            remarks=f'{transfer_type}: {remarks}' if remarks else transfer_type,
            status='success'
        )
        db.session.add(txn)
        db.session.commit()

        flash(f'₹{amount:,.2f} transferred successfully to {receiver_name}! TXN ID: {txn_id}', 'success')
        return redirect(url_for('transaction_history'))

    return render_template('transfer.html', account=account)


# ── Transaction History ────────────────────────────────────────────────────────
@app.route('/transactions')
@login_required
def transaction_history():
    account = BankAccount.query.filter_by(user_id=current_user.id).first()
    if not account:
        flash('No bank account found.', 'danger')
        return redirect(url_for('dashboard'))

    sent = Transaction.query.filter_by(sender_account_id=account.id)\
                .order_by(Transaction.created_at.desc()).all()
    received = Transaction.query.filter_by(receiver_account_id=account.id)\
                .order_by(Transaction.created_at.desc()).all()

    # Merge and sort all transactions
    all_txns = []
    for t in sent:
        all_txns.append({'txn': t, 'direction': 'debit', 'other_party': t.receiver_name,
                         'other_acc': t.receiver_account_number})
    for t in received:
        all_txns.append({'txn': t, 'direction': 'credit',
                         'other_party': t.sender_account.user.full_name,
                         'other_acc': t.sender_account.account_number})

    all_txns.sort(key=lambda x: x['txn'].created_at, reverse=True)

    return render_template('transactions.html', account=account, transactions=all_txns)


# ── AJAX: Validate Receiver Account ───────────────────────────────────────────
@app.route('/validate-account', methods=['POST'])
@login_required
def validate_account():
    data = request.get_json()
    acc_no = data.get('account_number', '').strip()
    acc = BankAccount.query.filter_by(account_number=acc_no).first()
    if acc and acc.user_id != current_user.id:
        return jsonify({'valid': True, 'name': acc.user.full_name})
    elif acc and acc.user_id == current_user.id:
        return jsonify({'valid': False, 'error': 'Cannot transfer to own account'})
    else:
        return jsonify({'valid': False, 'error': 'Account not found in NexaBank'})


# ── Create DB tables on startup (module-level for Vercel serverless) ──────────
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
