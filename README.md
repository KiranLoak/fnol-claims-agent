# ClaimSight — FNOL Claims Processing Agent

A web application that processes First Notice of Loss (FNOL) documents — extracts structured claim data, detects missing fields, and routes each claim to the right workflow automatically.

Built with **Python + Flask** on the backend and a custom dark UI on the frontend. Uses **Groq's free API** (LLaMA 3.1) for intelligent field extraction from unstructured documents.

---

## What It Does

Upload any FNOL `.txt` document and get back:

- **Extracted fields** — policy info, incident details, involved parties, asset details, claim type
- **Missing field detection** — flags any mandatory field that's absent or incomplete
- **Automatic routing** with a plain-English explanation

| Rule | Route |
|---|---|
| Damage < $25,000 + no other flags | Fast-track |
| Any mandatory field missing | Manual Review |
| "fraud" / "inconsistent" / "staged" in description | Investigation Flag |
| Claim type = Injury | Specialist Queue |

---

## Project Structure

```
fnol-claims-agent/
├── app.py                  ← Flask app (routes, filters, UI logic)
├── agent.py                ← Groq LLM extraction + missing field detection
├── router.py               ← Routing rules
├── requirements.txt
├── Procfile                ← For Render / Railway deployment
├── render.yaml             ← Render one-click deploy config
├── .env.example            ← Environment variable template
├── .gitignore
├── templates/
│   ├── index.html          ← Upload page
│   └── result.html         ← Results page
└── sample_fnols/
    ├── fnol_001.txt        ← Fast-track case
    ├── fnol_002.txt        ← Injury → Specialist Queue
    ├── fnol_003.txt        ← Fraud keywords → Investigation Flag
    ├── fnol_004.txt        ← Missing fields → Manual Review
    └── fnol_005.txt        ← High damage → Manual Review
```

---

## Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/fnol-claims-agent.git
cd fnol-claims-agent
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get your free Groq API key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up — no credit card required
3. Click **API Keys → Create API Key**
4. Copy the key

### 5. Set environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
GROQ_API_KEY=gsk_your_key_here
SECRET_KEY=any-random-string
```

### 6. Run

```bash
python app.py
```

Open **http://localhost:5000**

---

## Deploy to Render (Free)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/fnol-claims-agent.git
git push -u origin main
```

Make sure `.env` is in `.gitignore` — never push your API key.

### Step 2 — Create Web Service on Render

1. Go to [render.com](https://render.com) and sign in
2. Click **New → Web Service**
3. Connect GitHub and select `fnol-claims-agent`
4. Render auto-detects from `render.yaml`

If not auto-detected, set manually:

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |

### Step 3 — Add environment variables in Render dashboard

Go to your service → **Environment** tab:

| Key | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_your_key_here` |
| `SECRET_KEY` | any random string |

### Step 4 — Deploy

Click **Deploy**. Your live URL: `https://fnol-claims-agent.onrender.com`

> Free tier apps spin down after 15 min of inactivity and take ~30s to cold start. Fine for demos.

---

## Deploy to Railway (Alternative)

1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project → Deploy from GitHub Repo**
3. Select your repo
4. Add `GROQ_API_KEY` and `SECRET_KEY` in the **Variables** tab
5. Railway auto-detects the `Procfile` — deploy

---

## Quick Demo Without Deploying

Use ngrok to get a public link from your local machine:

```bash
# install from ngrok.com, then:
ngrok http 5000
```

Gives you a live `https://xxxx.ngrok.io` URL instantly.

---

## Tech Stack

- **Backend:** Python, Flask, Gunicorn
- **LLM:** Groq API (LLaMA 3.1 8B Instant) — free
- **Frontend:** HTML + CSS + vanilla JS, no frameworks
- **Fonts:** Syne + JetBrains Mono
