# Loan Prediction 💳

> **AI-powered Loan Eligibility Prediction App** built with Flask, Python, and a premium dark UI.

## 🌐 Live Demo
- **Vercel:** [Deploy link after setup]
- **Demo Login:** `demo@loanpro.com` / `demo1234`

## ✨ Features

| Feature | Description |
|---|---|
| 🚀 5-Step Wizard | Choose Type → Fill Details → CIBIL → Upload Docs → Get Result |
| 📊 CIBIL Score Check | Simulated credit score with animated meter & factors |
| 📁 Document Upload | Upload KYC & income documents with drag-drop |
| 💰 Live EMI Calculator | Real-time EMI with principal/interest breakdown |
| 🎮 Demo Account | One-click auto-login, no signup needed |
| 🤖 AI Prediction | Rule-based engine with 7 loan types |

## 🏦 Loan Types
- 🚗 Car Loan
- 🏠 Home Loan  
- 💳 Personal Loan
- 🎓 Education Loan
- 💼 Business Loan
- 🥇 Gold Loan
- 🏥 Medical Loan

## 🚀 Run Locally

```bash
git clone https://github.com/Jai-76/Bank-System.git
cd Bank-System
pip install -r requirements.txt
python app.py
```
Open → **http://localhost:5000**

## 📁 Project Structure

```
bank/
├── app.py                  # Flask backend
├── requirements.txt
├── vercel.json             # Vercel deployment config
├── static/
│   ├── css/style.css       # Premium dark design system
│   ├── js/main.js          # Frontend interactions
│   └── uploads/            # Uploaded documents (local only)
└── templates/
    ├── base.html           # Base layout + navbar
    ├── index.html          # Landing page
    ├── login.html          # Login + demo auto-login
    ├── register.html       # Registration
    ├── dashboard.html      # User dashboard
    ├── history.html        # Application history
    ├── profile.html        # Profile management
    └── wizard/
        ├── step1_type.html    # Choose loan type
        ├── step2_apply.html   # Fill details + EMI preview
        ├── step3_cibil.html   # CIBIL score check
        ├── step4_docs.html    # Upload documents
        └── step5_result.html  # AI prediction result
```

## ☁️ Deploy to Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel` in the project folder
3. Follow prompts – deployed in ~60 seconds!

## ⚠️ Disclaimer
This is an **educational/demo application**. Not real financial advice.
