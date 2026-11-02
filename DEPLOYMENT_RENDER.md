# 🚀 Deployment Guide: Deploying to Render (Free Tier)

**Project:** AI-Based Electricity Theft and Distribution Loss Detection Using Machine Learning  
**Display Name:** Electricity Theft & Distribution Loss Detection  
**Stack:** Flask 3.x, Gunicorn WSGI, SQLite 3, Scikit-learn, HTML5/CSS3/Vanilla JS  

---

## 📋 Table of Contents
1. [Architecture & Deployment Overview](#1-architecture--deployment-overview)
2. [Exact Render Configuration Settings](#2-exact-render-configuration-settings)
3. [Flask Application Entry Point & Gunicorn Command](#3-flask-application-entry-point--gunicorn-command)
4. [Environment Variables](#4-environment-variables)
5. [Database & Seeded Demo Data Management](#5-database--seeded-demo-data-management)
6. [⚠️ Important: Free Tier Ephemeral Storage Notice](#6-️-important-free-tier-ephemeral-storage-notice)
7. [Step-by-Step Deployment Instructions](#7-step-by-step-deployment-instructions)
8. [Post-Deployment Verification & Health Checks](#8-post-deployment-verification--health-checks)
9. [Troubleshooting & Common Questions](#9-troubleshooting--common-questions)

---

## 1. Architecture & Deployment Overview

This project is a self-contained Flask web application that serves both the HTML frontend views and the REST API backend. It uses **Gunicorn** as a production-grade WSGI HTTP server to handle requests reliably on Render's Linux containers.

```
[User Browser]
       │
       ▼
[Render Reverse Proxy / Cloudflare SSL]
       │ (Port 80/443 -> Forwarded to $PORT)
       ▼
[Gunicorn WSGI Server: app:app (0.0.0.0:$PORT)]
       │
       ├── Flask Application Factory (`app/__init__.py`)
       ├── 5 Core Web Views (`/dashboard`, `/energy-accounting`, `/ai-detection`, `/analytics`, `/inspection`)
       ├── 12 REST API Endpoints (`/api/*`)
       ├── Pre-trained ML Models (`models/isolation_forest.joblib`, `models/random_forest.joblib`)
       └── Pre-seeded SQLite Database (`database/grid_loss_system.db`)
```

---

## 2. Exact Render Configuration Settings

When creating a new **Web Service** on [dashboard.render.com](https://dashboard.render.com), use the exact parameters below:

| Setting Field | Value | Notes |
|---|---|---|
| **Service Type** | **Web Service** | Python application running on Linux |
| **Name** | `electricity-theft-detection` | Or your preferred unique name |
| **Region** | `Oregon (US West)` or `Frankfurt (EU)` | Pick the region closest to you |
| **Branch** | `main` | Default production branch |
| **Root Directory** | *(Leave blank)* | Uses root of repository |
| **Runtime** | **Python 3** | Render uses standard Python environment |
| **Build Command** | `pip install -r requirements.txt` | Installs Flask, Gunicorn, Scikit-learn, Pandas, etc. |
| **Start Command** | `gunicorn --workers 2 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT app:app` | Binds to Render's assigned `$PORT` |
| **Instance Type / Plan** | **Free** | $0.00/month (512 MB RAM, 0.1 CPU) |
| **Auto-Deploy** | **Yes** | Automatically deploys new commits pushed to `main` |

---

## 3. Flask Application Entry Point & Gunicorn Command

### Application Entry Point
- **File:** `app.py`
- **WSGI Callable:** `app`
- **Definition in `app.py`:**
  ```python
  from app import create_app
  app = create_app()
  ```
- **Gunicorn Target:** `app:app` (`<filename_without_py>:<wsgi_app_variable>`)

### Exact Start Command
```bash
gunicorn --workers 2 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT app:app
```

#### Why these flags?
- `--bind 0.0.0.0:$PORT`: Render dynamically assigns a port to each container via the `$PORT` environment variable (typically port 10000). Gunicorn **must** bind to `0.0.0.0:$PORT` to receive incoming traffic from Render's routing mesh.
- `--workers 2 --threads 2`: Optimal concurrency on Render's Free Tier (512 MB RAM limit). Keeps memory usage well below 250 MB while handling multiple concurrent requests.
- `--timeout 120`: Provides a comfortable 120-second threshold for loading machine learning models into memory during initial spin-up.

---

## 4. Environment Variables

Configure these environment variables in the Render Dashboard under **Environment**:

| Variable Name | Value | Required | Purpose |
|---|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | **Recommended** | Ensures fast, pre-compiled binary wheels for numpy/scipy/pandas |
| `FLASK_DEBUG` | `0` | **Recommended** | Disables Flask debug mode in production |
| `HOST` | `0.0.0.0` | **Recommended** | Binds to all interfaces |
| `SECRET_KEY` | *(Click "Generate" in Render)* | **Recommended** | Cryptographic session signing key |
| `PORT` | *(Automatically injected by Render)* | Automatic | Render provides this; do not hardcode |

> [!NOTE]
> Local development secrets are stored in `.env`. The `.gitignore` file automatically excludes `.env` so secrets are never pushed to GitHub. Use Render's Environment Variable dashboard for production values.

---

## 5. Database & Seeded Demo Data Management

1. **Pre-Seeded SQLite Database Included:**
   - The SQLite database file `database/grid_loss_system.db` (~54.7 MB) is committed to the Git repository.
   - It contains complete seeded academic demo data:
     - **5 11 kV Feeders** (FDR-01 through FDR-05)
     - **500 Consumers** (300 Residential, 125 Commercial, 75 Agricultural)
     - **360,000 Hourly Telemetry Readings** (30 days × 24 hours)
     - **150 Daily Energy Accounting Logs** (30 days × 5 feeders) with zero-residual mathematical reconciliation
     - **500 Pre-Calculated Isolation Forest Anomaly Scores** & Triage Categories
2. **Pre-Trained Machine Learning Artifacts Included:**
   - `models/isolation_forest.joblib` (Unsupervised anomaly scoring model)
   - `models/random_forest.joblib` (Supervised validation benchmark)
   - `models/metrics.json` (Gini feature importances, accuracy, precision, recall, F1, ROC-AUC, confusion matrix)
3. **Automatic Startup Verification (`src/utils/helpers.py`):**
   - The application checks for database tables and counts on startup.
   - Because `grid_loss_system.db` is already seeded, startup completes in **under 2 seconds** with zero computation overhead.

---

## 6. ⚠️ Important: Free Tier Ephemeral Storage Notice

> [!WARNING]
> **Ephemeral Filesystem Behavior:**
> Render Free instances use an **ephemeral disk**. 
> - Any inspection status edits, inspector assignments, or field remarks submitted via the **Inspection Worklist** will write to the SQLite database during the active session.
> - However, Render Free web services **spin down after 15 minutes of inactivity** to conserve resources.
> - When a new request arrives, Render spins up a fresh container instance from your deployed Git image.
> - **Result:** The SQLite database will reset back to the committed seeded state whenever the container spins down or redeploys.
> 
> *For a final-year academic project demonstration, this is actually advantageous: it ensures the demo always boots in a clean, consistent, pre-validated state with all 500 consumers and audit logs intact.*

---

## 7. Step-by-Step Deployment Instructions

### Step 1: Push Project to GitHub

Open a terminal in your project root (`c:\laragon\www\electricity-ai`):

```bash
# 1. Initialize git if not already initialized
git init

# 2. Stage all deployment-ready files
git add .

# 3. Commit changes
git commit -m "Prepare Electricity Theft & Distribution Loss Detection for Render deployment"

# 4. Link your GitHub repository (replace with your repo URL)
git remote add origin https://github.com/<your-username>/electricity-theft-detection.git

# 5. Push to main branch
git branch -M main
git push -u origin main
```

### Step 2: Create Web Service on Render

#### Option A: Quick Blueprint Deploy (Recommended)
Because this repository includes `render.yaml`:
1. Log in to [Render](https://render.com).
2. Click **New +** > **Blueprint**.
3. Connect your GitHub repository.
4. Render will automatically read `render.yaml` and set up the build command, start command, and environment variables.
5. Click **Apply**.

#### Option B: Manual Setup
1. Log in to [Render](https://render.com).
2. Click **New +** > **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your repo.
4. Enter the settings:
   - **Name:** `electricity-theft-detection`
   - **Language / Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --workers 2 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT app:app`
   - **Instance Type:** `Free`
5. In the **Environment Variables** section, add:
   - `PYTHON_VERSION` = `3.11.9`
   - `FLASK_DEBUG` = `0`
6. Click **Create Web Service**.

---

## 8. Post-Deployment Verification & Health Checks

Once the deployment status indicates **"Live"**, verify your deployment:

1. **Service Health Check:**
   Navigate to:
   `https://<your-render-subdomain>.onrender.com/api/health`
   **Expected Response:**
   ```json
   {
     "status": "HEALTHY",
     "service": "grid_loss_system",
     "database": "CONNECTED",
     "feeder_count": 5,
     "consumer_count": 500
   }
   ```
2. **Executive Dashboard:**
   Visit `https://<your-render-subdomain>.onrender.com/dashboard`
   - Verify all 8 KPI cards render live database figures.
   - Verify Chart.js visualizations load (Supply vs Billed, Doughnut, Feeder Bars, Loss Trend).
3. **Energy Accounting:**
   Visit `https://<your-render-subdomain>.onrender.com/energy-accounting`
   - Verify zero-residual mathematical balance banner.
   - Test the **Export CSV** download button.
4. **AI Anomaly Detection:**
   Visit `https://<your-render-subdomain>.onrender.com/ai-detection`
   - Verify 500 consumer predictions and priority badges.
   - Click **Details** on any consumer to inspect the engineered feature modal.
5. **Analytics & Insights:**
   Visit `https://<your-render-subdomain>.onrender.com/analytics`
   - Verify the 5 evaluation metrics (Accuracy 97.33%, Precision 88.89%, etc.).
   - Verify the Confusion Matrix and 5 analytical charts.
6. **Inspection Worklist:**
   Visit `https://<your-render-subdomain>.onrender.com/inspection`
   - Verify worklist table, filters, and update status modal.

---

## 9. Troubleshooting & Common Questions

### Q: Why did the first request take 30-50 seconds to respond?
**A:** Render Free instances spin down after 15 minutes of inactivity. When a new visitor accesses the URL, Render initiates a "cold start". Subsequent requests respond instantly in under 150ms.

### Q: Why does Render log show `Listening at: http://0.0.0.0:10000`?
**A:** This is normal and correct. Render dynamically sets `PORT=10000` (or similar) internally and forwards standard external HTTPS (port 443) traffic directly to your Gunicorn listener.

### Q: Will my edits in the Inspection Worklist be saved permanently?
**A:** Edits persist throughout the active session. If the free instance goes to sleep (spins down) or is redeployed, the filesystem refreshes to the original committed database state.

### Q: Can I run this locally using the same configuration?
**A:** Yes! Run `python app.py` locally or execute `run.bat`. The app automatically detects local environments and runs with default host `127.0.0.1` and port `5000`.

