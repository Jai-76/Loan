# 🏦 NexBank – Loan Prediction

> AI-powered loan eligibility prediction platform built with Flask & Python.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://bank-weld-five-55.vercel.app)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?style=for-the-badge&logo=github)](https://github.com/Jai-76/Bank-System)
[![Python](https://img.shields.io/badge/Python-3.12-green?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)

---

## 🌐 Live Demo

**👉 [https://bank-weld-five-55.vercel.app](https://bank-weld-five-55.vercel.app)**

---

## ✨ Features

- 🤖 **AI-Powered Loan Prediction** — Rule-based scoring engine for instant loan decisions
- 📊 **CIBIL Score Check** — Credit score verification with visual meter
- 📄 **Document Upload** — Secure Aadhaar, PAN, Salary Slip upload
- 🔐 **User Authentication** — Register, Login, Logout with session management
- 📋 **Dashboard** — Track all loan applications with status filters
- 💳 **Loan Types** — Personal, Car & Education loans
- 📱 **Responsive Design** — Works on all screen sizes

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Database | SQLite (SQLAlchemy ORM) |
| Auth | Flask-Login |
| Frontend | HTML5, Vanilla CSS, JavaScript |
| Deployment | Vercel |
| Version Control | Git + GitHub |

---

## 🚀 Getting Started (Local)

### 1. Clone the repo
```bash
git clone https://github.com/Jai-76/Bank-System.git
cd Bank-System
```

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🏗️ Project Structure

```
Bank-System/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── vercel.json             # Vercel deployment config
├── static/
│   ├── css/style.css       # Global styles
│   └── js/main.js          # Client-side JavaScript
└── templates/
    ├── base.html           # Base layout (navbar + footer)
    ├── index.html          # Homepage
    ├── login.html          # Login page
    ├── register.html       # Registration page
    ├── dashboard.html      # User dashboard
    ├── apply_loan.html     # Step 1 – Loan application form
    ├── cibil_check.html    # Step 2 – CIBIL score check
    ├── upload_docs.html    # Step 3 – Document upload
    └── loan_result.html    # Loan decision result
```

---

## 📊 Loan Prediction Logic

The scoring engine evaluates applications across 4 factors:

| Factor | Weight | Details |
|--------|--------|---------|
| CIBIL Score | 40% | 800+ = Excellent, 750+ = Very Good, 700+ = Good, 650+ = Fair, 600+ = Low |
| Income vs Loan | 30% | Loan-to-income ratio (lower = better) |
| Employment Type | 20% | Govt Salaried > Business > Private > Self-Employed > Freelancer |
| Tenure | 10% | 12–60 months preferred |

- **Score ≥ 65** → ✅ Approved
- **Score ≥ 42** → ✅ Conditionally Approved
- **Score < 42** → ❌ Rejected

---

## 🔒 Security

- Passwords hashed with Werkzeug's `generate_password_hash`
- Flask session-based authentication
- File upload validation (PDF, PNG, JPG only)
- CSRF protection via Flask secret key

---

## 📸 Screenshots

| Page | Description |
|------|-------------|
| 🏠 Homepage | Hero section with loan types, 3-step process & trust badges |
| 🔐 Login/Register | Clean split-layout auth pages |
| 📋 Dashboard | Loan application tracking with status filters |
| ✅ Result | Detailed loan decision with interest rate & EMI |

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

---

## 📄 License

This project is for educational/demo purposes.

---

<div align="center">
  Made with ❤️ by <a href="https://github.com/Jai-76">Jai-76</a>
  <br/>
  <a href="https://bank-weld-five-55.vercel.app">🌐 Live Demo</a>
</div>
