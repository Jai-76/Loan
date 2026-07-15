import os, uuid, random, hashlib
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, flash)
from werkzeug.utils import  secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'loanpro_2024_xK9mP3qR')

# ── Upload config (disabled on Vercel / serverless) ──────────────
UPLOAD_FOLDER  = os.path.join('static', 'uploads')
ALLOWED_EXT    = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
IS_SERVERLESS  = os.environ.get('VERCEL', '') == '1'
if not IS_SERVERLESS:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────── In-Memory DB ────────────────────────────
USERS = {
    "demo@loanpro.com": {
        "password" : hashlib.sha256(b"demo1234").hexdigest(),
        "name"     : "Alex Johnson",
        "phone"    : "+91 98765 43210",
        "pan"      : "ABCDE1234F",
        "dob"      : "15-Aug-1990",
        "address"  : "123 MG Road, Bengaluru, Karnataka 560001",
        "joined"   : "Jan 2024",
        "avatar"   : "AJ",
    }
}
APPLICATIONS = {}   # email → [list of apps]
DOCUMENTS    = {}   # email → [list of doc records]
CIBIL_CACHE  = {}   # pan   → score

DOC_LABELS = {
    'aadhaar': 'Aadhaar Card',   'pan': 'PAN Card',
    'passport':'Passport',       'driving':'Driving Licence',
    'voter':   'Voter ID',       'salary_slip':'Salary Slip',
    'bank_statement':'Bank Statement (6 months)',
    'itr':     'ITR / Income Tax Return',
    'form16':  'Form 16',        'property':'Property Documents',
    'rc_book': 'RC Book (Vehicle)',
    'business_reg':'Business Registration',  'other':'Other',
}

# ─────────────────────── Helpers ─────────────────────────────────
def hp(pw):   return hashlib.sha256(pw.encode()).hexdigest()
def gen_id(): return f"LP{random.randint(100000,999999)}"

def allowed(fname):
    return '.' in fname and fname.rsplit('.',1)[1].lower() in ALLOWED_EXT

def interest_rate(ltype, credit):
    base = {'personal':12.5,'home':8.5,'car':9.5,'education':7.5,
            'business':13.5,'gold':9.0,'medical':11.5}.get(ltype, 12.0)
    if credit >= 750: return base - 1.5
    if credit >= 700: return base - 0.5
    if credit >= 650: return base + 0.5
    return base + 2.0

def cibil_score(pan):
    if pan in CIBIL_CACHE: return CIBIL_CACHE[pan]
    seed = sum(ord(c) for c in pan.upper())
    random.seed(seed); s = random.randint(550, 900); random.seed()
    CIBIL_CACHE[pan] = s
    return s

def cibil_meta(score):
    if   score >= 800: return ("Excellent","#22c55e","🌟")
    elif score >= 750: return ("Very Good","#4ade80","✅")
    elif score >= 700: return ("Good",     "#86efac","👍")
    elif score >= 650: return ("Fair",     "#facc15","⚠️")
    elif score >= 600: return ("Poor",     "#f97316","🔴")
    else:              return ("Very Poor","#ef4444","❌")

def predict(data):
    credit  = int(data.get('credit_score') or 650)
    income  = float(data.get('annual_income') or 0)
    emp     = data.get('employment_type','salaried')
    amount  = float(data.get('loan_amount') or 0)
    term    = int(data.get('loan_term') or 12)
    exist_e = float(data.get('existing_emi') or 0)
    ltype   = data.get('loan_type','personal')
    age     = int(data.get('age') or 30)

    score=0; ok=[]; warn=[]
    # Credit
    if   credit>=750: score+=35; ok.append("Excellent credit score (750+)")
    elif credit>=700: score+=28; ok.append("Good credit score (700+)")
    elif credit>=650: score+=18; warn.append("Fair credit score – rate may be higher")
    elif credit>=600: score+=8;  warn.append("Low credit score – high risk")
    else:             score+=0;  warn.append("Poor credit score – very high risk")
    # Income
    mo = income/12
    if   mo>=10000: score+=25; ok.append("High monthly income")
    elif mo>=5000:  score+=18; ok.append("Adequate income level")
    elif mo>=3000:  score+=10; warn.append("Moderate income – watch EMI ratio")
    else:           score+=3;  warn.append("Low monthly income")
    # EMI ratio
    rm = interest_rate(ltype,credit)/12/100
    emi = (amount*rm*(1+rm)**term)/((1+rm)**term-1) if rm>0 else amount/term
    ratio = ((emi+exist_e)/mo*100) if mo>0 else 100
    if   ratio<=30: score+=20; ok.append("Healthy EMI-to-income ratio (≤30%)")
    elif ratio<=40: score+=12; warn.append("Moderate EMI burden (30–40%)")
    elif ratio<=50: score+=5;  warn.append("High EMI burden (40–50%)")
    else:           score+=0;  warn.append("EMI exceeds 50% of income – risky")
    # Employment
    if   emp=='salaried':     score+=10; ok.append("Stable salaried employment")
    elif emp=='self_employed': score+=7;  warn.append("Self-employed – needs income proof")
    elif emp=='business':      score+=8;  ok.append("Business owner profile")
    else:                      score+=2;  warn.append("Irregular employment")
    # Age
    if 25<=age<=50: score+=5; ok.append("Prime working age (25–50)")
    elif age<25:    score+=2; warn.append("Young applicant – limited credit history")
    else:           score+=3
    # Loan-type
    if ltype=='home':
        if amount>income*5: score-=5; warn.append("Loan exceeds 5× annual income")
        else: score+=5; ok.append("Amount within home-loan guidelines")
    elif ltype=='education':
        score+=5; ok.append("Education loans have favourable terms")

    score = min(100,max(0,score))
    if   score>=70: status="APPROVED";    col="#22c55e"
    elif score>=50: status="CONDITIONAL"; col="#f97316"
    else:           status="REJECTED";    col="#ef4444"
    ir = interest_rate(ltype,credit) + (1.5 if status=="CONDITIONAL" else 0)

    return dict(status=status,score=score,color=col,ok=ok,warn=warn,
                emi=round(emi,2),rate=round(ir,2),
                total=round(emi*term,2),interest=round(emi*term-amount,2))

# ══════════════════ AUTH ═════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form.get('email','').strip().lower()
        pw    = request.form.get('password','')
        u     = USERS.get(email)
        if u and u['password']==hp(pw):
            session.update(user=email, name=u['name'])
            flash(f"Welcome back, {u['name'].split()[0]}! 👋","success")
            return redirect(url_for('dashboard'))
        flash("Invalid email or password.","error")
    return render_template('login.html')

@app.route('/demo-login')
def demo_login():
    session.update(user='demo@loanpro.com',
                   name=USERS['demo@loanpro.com']['name'])
    flash("Logged in as Demo Account! 🎉","success")
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name  = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        pw    = request.form.get('password','')
        phone = request.form.get('phone','').strip()
        if email in USERS:
            flash("Email already registered.","error")
            return render_template('register.html')
        USERS[email]=dict(password=hp(pw),name=name,phone=phone,pan='',dob='',
                          address='',joined=datetime.now().strftime("%b %Y"),
                          avatar=''.join(w[0].upper() for w in name.split()[:2]))
        session.update(user=email, name=name)
        flash("Account created! Welcome 🎉","success")
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

# ══════════════════ DASHBOARD ════════════════════════════════════
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    email = session['user']
    apps  = APPLICATIONS.get(email,[])
    docs  = DOCUMENTS.get(email,[])
    stats = dict(total=len(apps),
                 approved=sum(1 for a in apps if a['status']=='APPROVED'),
                 conditional=sum(1 for a in apps if a['status']=='CONDITIONAL'),
                 rejected=sum(1 for a in apps if a['status']=='REJECTED'))
    return render_template('dashboard.html',
                           user=USERS[email], apps=apps[:5],
                           docs=docs, stats=stats)

# ══════════════════ WIZARD FLOW ══════════════════════════════════
# Step 1 – Choose loan type
@app.route('/loan/start')
def loan_start():
    if 'user' not in session: return redirect(url_for('login'))
    session.pop('wizard',None)
    return render_template('wizard/step1_type.html')

# Step 2 – Application details
@app.route('/loan/apply', methods=['GET','POST'])
def loan_apply():
    if 'user' not in session: return redirect(url_for('login'))
    ltype = request.args.get('type') or session.get('wizard',{}).get('loan_type','personal')
    if request.method=='POST':
        data = request.form.to_dict()
        session['wizard'] = data
        return redirect(url_for('loan_cibil'))
    return render_template('wizard/step2_apply.html', loan_type=ltype)

# Step 3 – CIBIL check
@app.route('/loan/cibil', methods=['GET','POST'])
def loan_cibil():
    if 'user' not in session: return redirect(url_for('login'))
    if 'wizard' not in session: return redirect(url_for('loan_start'))
    result = None
    if request.method=='POST':
        pan    = request.form.get('pan','').strip().upper()
        dob    = request.form.get('dob','')
        score  = cibil_score(pan) if len(pan)==10 else None
        if score is None:
            flash("Enter a valid 10-character PAN number.","error")
        else:
            grade,color,icon = cibil_meta(score)
            wiz = session.get('wizard',{})
            wiz['credit_score'] = str(score)
            wiz['pan']          = pan
            session['wizard']   = wiz
            result = dict(score=score,grade=grade,color=color,icon=icon,pan=pan,dob=dob)
            session['cibil_done'] = result
    # prefill from user profile
    user = USERS.get(session['user'],{})
    return render_template('wizard/step3_cibil.html',
                           result=session.get('cibil_done'), user=user)

# Step 4 – Upload documents
@app.route('/loan/documents', methods=['GET','POST'])
def loan_documents():
    if 'user' not in session: return redirect(url_for('login'))
    if 'wizard' not in session: return redirect(url_for('loan_start'))
    email = session['user']
    if request.method=='POST':
        dtype = request.form.get('doc_type','other')
        f     = request.files.get('document')
        saved = False
        if f and f.filename and allowed(f.filename):
            if IS_SERVERLESS:
                # Serverless – store meta only (no disk write)
                rec = dict(id=str(uuid.uuid4())[:8], type=dtype,
                           label=DOC_LABELS.get(dtype,'Document'),
                           filename=f.filename, saved_as='(server)',
                           size=0, ext=f.filename.rsplit('.',1)[-1].lower(),
                           uploaded=datetime.now().strftime("%d %b %Y, %H:%M"),
                           status='Under Review')
            else:
                ext  = f.filename.rsplit('.',1)[1].lower()
                name = f"{uuid.uuid4().hex}.{ext}"
                f.save(os.path.join(UPLOAD_FOLDER, name))
                sz   = os.path.getsize(os.path.join(UPLOAD_FOLDER, name))
                rec  = dict(id=str(uuid.uuid4())[:8], type=dtype,
                            label=DOC_LABELS.get(dtype,'Document'),
                            filename=f.filename, saved_as=name,
                            size=sz, ext=ext,
                            uploaded=datetime.now().strftime("%d %b %Y, %H:%M"),
                            status='Verified' if random.random()>.2 else 'Under Review')
            DOCUMENTS.setdefault(email,[]).insert(0,rec)
            flash(f"'{f.filename}' uploaded! ✅","success")
            saved = True
        if not saved and request.form.get('skip')=='1':
            return redirect(url_for('loan_result'))
        if saved and request.form.get('finish')=='1':
            return redirect(url_for('loan_result'))
        return redirect(url_for('loan_documents'))

    docs = DOCUMENTS.get(email,[])
    return render_template('wizard/step4_docs.html',
                           docs=docs, doc_labels=DOC_LABELS)

# Step 5 – Result
@app.route('/loan/result')
def loan_result():
    if 'user' not in session: return redirect(url_for('login'))
    wiz = session.get('wizard')
    if not wiz: return redirect(url_for('loan_start'))
    res    = predict(wiz)
    email  = session['user']
    record = dict(id=gen_id(), date=datetime.now().strftime("%d %b %Y"),
                  loan_type=wiz.get('loan_type','personal').title(),
                  amount=float(wiz.get('loan_amount',0)),
                  term=wiz.get('loan_term',12), **res)
    APPLICATIONS.setdefault(email,[]).insert(0,record)
    session.pop('wizard',None)
    session.pop('cibil_done',None)
    return render_template('wizard/step5_result.html', res=res, app=record)

# ══════════════════ HISTORY / PROFILE ════════════════════════════
@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('history.html',
                           apps=APPLICATIONS.get(session['user'],[]))

@app.route('/profile', methods=['GET','POST'])
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    email = session['user']; u = USERS[email]
    if request.method=='POST':
        u['name']    = request.form.get('name', u['name'])
        u['phone']   = request.form.get('phone', u.get('phone',''))
        u['dob']     = request.form.get('dob',   u.get('dob',''))
        u['pan']     = request.form.get('pan',   u.get('pan','')).upper()
        u['address'] = request.form.get('address', u.get('address',''))
        u['avatar']  = ''.join(w[0].upper() for w in u['name'].split()[:2])
        session['name'] = u['name']
        flash("Profile updated ✅","success")
        return redirect(url_for('profile'))
    return render_template('profile.html', user=u, email=email,
                           docs=DOCUMENTS.get(email,[]))

@app.route('/documents/delete/<did>')
def del_doc(did):
    if 'user' not in session: return redirect(url_for('login'))
    email = session['user']
    docs  = DOCUMENTS.get(email,[])
    for d in docs:
        if d['id']==did:
            if not IS_SERVERLESS:
                try: os.remove(os.path.join(UPLOAD_FOLDER,d['saved_as']))
                except: pass
            docs.remove(d); flash("Document deleted.","success"); break
    return redirect(url_for('profile'))

# ══════════════════ API ═══════════════════════════════════════════
@app.route('/api/emi', methods=['POST'])
def api_emi():
    d = request.get_json()
    p,r,n = float(d.get('p',0)), float(d.get('r',10))/12/100, int(d.get('n',12))
    emi = (p*r*(1+r)**n)/((1+r)**n-1) if r>0 else p/n
    return jsonify(emi=round(emi,2), total=round(emi*n,2),
                   interest=round(emi*n-p,2))

if __name__=='__main__':
    app.run(debug=True, port=5000)
