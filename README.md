# Electricity Theft & Distribution Loss Detection
### AI-Based Electricity Theft and Distribution Loss Detection Using Machine Learning

**Smart Grid Intelligence & Distribution Loss Monitoring**  
*Final Year Academic Capstone Project*  
**Institution:** Sri Shakthi Institute of Engineering and Technology  
**Department:** Artificial Intelligence and Data Science  
**Project Guide:** Mrs. Dr. Kamalaveni  

---

## ⚡ Project Overview

**Electricity Theft & Distribution Loss Detection** is an enterprise-grade electricity distribution monitoring platform that integrates electrical engineering physics with unsupervised machine learning to detect technical losses, unexplained commercial discrepancies, and abnormal consumer consumption signatures.

An anomaly prediction is an engineering indicator requiring further investigation rather than proof of criminal conduct. All flagged consumers are triaged as *inspection candidates* categorized by review urgency (**Critical**, **High**, **Medium**, **Low**).

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Application Pages](#-application-pages)
3. [Technology Stack](#-technology-stack)
4. [Electrical Physics Formulations](#-electrical-physics-formulations)
5. [Feature Engineering](#-feature-engineering-10-features)
6. [Machine Learning Pipeline](#-machine-learning-pipeline)
7. [Database Architecture & Statistics](#-database-architecture--statistics)
8. [Folder Structure](#-folder-structure)
9. [Localhost Execution & Startup](#-localhost-execution--startup)
10. [Cloud Deployment on Render (Free Tier)](#-cloud-deployment-on-render-free-tier)
11. [Automated Test Suite](#-automated-test-suite)
12. [REST API Documentation](#-rest-api-documentation)
13. [Academic Disclaimer & Limitations](#-academic-disclaimer--limitations)

---

## 🌟 Key Features

- **Mathematical Energy Accounting:** Reconciles Substation Supplied Energy against Customer Billing and Physical Technical Dissipation ($I^2R$ and Transformer Core/Copper losses) with documented residual tracking.
- **Unsupervised Anomaly Scoring:** Uses **Isolation Forest** normalized strictly to $[0.0, 1.0]$ with automated diagnostic explanations.
- **Supervised Benchmark:** Evaluates a 120-tree **Random Forest Classifier** against held-out simulated tampering scenarios with genuine classification metrics.
- **Field Inspection Lifecycle:** Complete worklist management with SQLite persistence for status updates (`Pending`, `Scheduled`, `In Progress`, `Completed`, `Not Suspicious After Verification`).
- **Interactive Data Visualizations:** Real-time Chart.js time series, doughnut charts, histograms, confusion matrix, and feature importances.
- **Export Capabilities:** One-click CSV export for Daily Accounting, Inspection Worklist, and Model Predictions.

---

## 🖥 Application Pages

| # | Route | Page Title | Key Capabilities |
|---|---|---|---|
| **1** | `/dashboard` | **Executive Dashboard** | 8 primary KPI cards, 30-day supply vs billed chart, feeder breakdown, priority doughnut, recent anomaly alerts. |
| **2** | `/energy-accounting` | **Energy Accounting** | Reconciled balance cards, cable loss ($I^2R$), transformer core & copper losses, daily audit table with pagination, CSV export. |
| **3** | `/ai-detection` | **AI Theft Detection** | 500-consumer predictions table, priority filters, search, score sorting, consumer detail modal with feature radar/bars. |
| **4** | `/analytics` | **Analytics & Insights** | 30-day load dynamics (peak vs base), confusion matrix, feature importance, score distribution histogram, model comparison. |
| **5** | `/inspection` | **Inspection Worklist** | Consumer inspection management, status transition, technician assignments, remark updates with SQLite persistence, CSV export. |

---

## 🛠 Technology Stack

- **Backend:** Python 3.11+, Flask, Flask Blueprints, REST API architecture
- **Database:** SQLite 3 with Foreign Key constraints, WAL mode, indexed schemas
- **Machine Learning:** Scikit-learn (Isolation Forest, Random Forest), NumPy, Pandas, Joblib
- **Frontend:** HTML5, CSS3 Custom Properties, Vanilla JavaScript (ES6+), Bootstrap 5 utilities, Chart.js 4.4, Font Awesome 6.5
- **Testing:** Pytest 9.2 (20 passing unit & integration tests)

---

## ⚡ Electrical Physics Formulations

### 1. Three-Phase Cable Ohmic Power Loss
$$P_{\text{cable}} = 3 \cdot I^2 \cdot R_{\text{phase}} \quad (\text{Watts})$$
$$\text{Line Current: } I = \frac{P}{\sqrt{3} \cdot V_{LL} \cdot \cos\phi} \quad (\text{Amperes})$$
$$\text{Energy Loss (kWh)} = P_{\text{cable (kW)}} \times \Delta t_{\text{hours}}$$
*Parameters:* Nominal voltage $V_{LL} = 11.0\text{ kV}$, power factor $\cos\phi = 0.92$, ACSR resistance $R \approx 0.35 - 0.48\ \Omega$.

### 2. Transformer Total Losses
$$P_{\text{transformer}} = P_{\text{core}} + P_{\text{copper}} \cdot \left(\frac{S}{S_{\text{rated}}}\right)^2$$
- **Core Loss ($P_{\text{core}}$):** Constant no-load hysteresis and eddy current iron loss under continuous energization (~1.35 - 2.60 kW).
- **Copper Loss ($P_{\text{copper}}$):** Winding resistance losses varying quadratically with apparent load loading ratio.

### 3. Energy Balance Reconciliation
$$E_{\text{supplied}} = E_{\text{billed}} + E_{\text{technical}} + E_{\text{unexplained}} + \text{Residual}$$
$$E_{\text{unexplained}} = \max(0,\ E_{\text{supplied}} - E_{\text{billed}} - E_{\text{technical}})$$

---

## 🔬 Feature Engineering (10 Features)

1. `mean_daily_consumption`: 30-day average daily usage in kWh.
2. `rolling_avg_7d`: Average daily consumption over the recent 7 days (days 24 to 30).
3. `consumption_std`: Standard deviation of daily consumption.
4. `cv_consumption`: Coefficient of variation ($\sigma/\mu$) capturing consumption volatility.
5. `drop_ratio`: Ratio of recent 7-day average to baseline 23-day average ($\text{avg}_{\text{recent}} / \max(0.05, \text{avg}_{\text{baseline}})$).
6. `hourly_variability`: Standard deviation across diurnal 24-hour load bins.
7. `load_factor`: Ratio of average hourly consumption to maximum peak load ($\text{mean} / \text{max}$).
8. `peak_to_average_ratio`: Evening peak (18:00–22:00) usage relative to overall hourly average.
9. `missing_reading_pct`: Percentage of zero, dropout, or missing telemetry readings.
10. `peer_relative_deviation`: Consumer's mean daily consumption normalized by tariff peers on the same feeder.

---

## 🤖 Machine Learning Pipeline

### Primary Model: Isolation Forest (Unsupervised)
- Detects multidimensional outliers through recursive random partitioning without requiring historical labels.
- Decision function scores are inverted and min-max scaled into $[0.0, 1.0]$:
  $$\text{anomaly\_score} = \frac{(-\text{raw}) - \min(-\text{raw})}{\max(-\text{raw}) - \min(-\text{raw})}$$
- **Configurable Review Priority Rules:**
  - **Critical:** $0.75 \le \text{score} \le 1.00$
  - **High:** $0.60 \le \text{score} < 0.75$
  - **Medium:** $0.45 \le \text{score} < 0.60$
  - **Low:** $0.00 \le \text{score} < 0.45$

### Secondary Model: Random Forest Benchmark (Supervised)
- 120 estimators, stratified 70% train / 30% test split on 500 consumers.
- Evaluated on 150 held-out test consumers:
  - **Accuracy:** 97.33%
  - **Precision:** 88.89%
  - **Recall:** 88.89%
  - **F1-Score:** 0.8889
  - **ROC-AUC:** 0.9979
  - **Confusion Matrix:** $\begin{bmatrix} 130 & 2 \\ 2 & 16 \end{bmatrix}$
  - **Top Features:** `load_factor` (0.3035), `drop_ratio` (0.2247), `cv_consumption` (0.1891).

---

## 🗄 Database Architecture & Statistics

Database file: `database/grid_loss_system.db`

| Table | Records | Description |
|---|---|---|
| `feeders` | **5** | 11 kV distribution feeders across 5 substations |
| `transformers` | **5** | Distribution step-down transformers (630–1250 kVA) |
| `consumers` | **500** | 300 Residential, 125 Commercial, 75 Agricultural |
| `consumer_readings` | **360,000** | 500 consumers × 24 hours × 30 days |
| `feeder_readings` | **3,600** | 5 feeders × 24 hours × 30 days |
| `loss_audit_logs` | **150** | 5 feeders × 30 days daily energy audit records |
| `theft_predictions` | **500** | Isolation Forest scores, priorities, diagnostic reasons |
| `inspection_records` | **62** | Candidates requiring investigation (Critical/High/Med) |
| `model_metrics` | **1** | Evaluated metrics on held-out test data |
| `system_settings` | **7** | Configuration parameters & thresholds |

---

## 🚀 Localhost Execution & Startup

### Option 1: Automated Windows Startup Script (Recommended)
Double-click `run.bat` or execute in Windows Command Prompt:
```cmd
run.bat
```
The script will automatically:
1. Verify Python installation.
2. Initialize the virtual environment `.\venv`.
3. Check and install dependencies from `requirements.txt`.
4. Initialize the SQLite database and verify 360,000 readings.
5. Train and save models if missing.
6. Launch the web server on `http://127.0.0.1:5000`.

### Option 2: Manual Terminal Commands
```powershell
# 1. Create and activate virtual environment
python -m venv venv --system-site-packages
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the application
python app.py
```

Open your browser and navigate to:
**http://127.0.0.1:5000**

---

## ☁️ Cloud Deployment on Render (Free Tier)

This repository is pre-configured for one-click or manual deployment to **Render's Free Web Service** tier using Gunicorn.

- **WSGI Target:** `app:app`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --workers 2 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT app:app`
- **Complete Step-by-Step Instructions:** Refer to [DEPLOYMENT_RENDER.md](DEPLOYMENT_RENDER.md)

> [!IMPORTANT]
> **Ephemeral Storage Notice:** On Render's Free tier, the filesystem is ephemeral. The pre-seeded SQLite database (`database/grid_loss_system.db`) and trained ML models are bundled with the repository and available immediately upon deployment. Any inspection updates made during a live session will write to SQLite, but will reset back to the committed seeded state whenever the free instance spins down (after 15 minutes of inactivity) or restarts.

---

## 🧪 Automated Test Suite

Run the full pytest suite:
```powershell
.\venv\Scripts\python.exe -m pytest tests/ -v
```

**20 Passing Tests:**
- `test_db.py`: Connection, foreign keys, exact table record counts (5 feeders, 500 consumers, 360k readings, 150 audits).
- `test_physics.py`: Cable loss $I^2R$, transformer core/copper losses, energy balance zero-residual reconciliation.
- `test_features.py`: 10 domain features, no null/NaN values, valid numerical bounds.
- `test_models.py`: Isolation Forest training, $[0, 1]$ normalization, Random Forest evaluation metrics, confusion matrix.
- `test_api.py`: Dashboard summary, energy accounting daily logs, inspection worklist, PUT status persistence, CSV export downloads.

---

## 🌐 REST API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `GET` | `/api/dashboard/summary` | 8 Executive KPI metrics |
| `GET` | `/api/dashboard/energy-trend` | Time series for dashboard charts |
| `GET` | `/api/feeders` | List all 5 feeders with specifications |
| `GET` | `/api/consumers` | Paginated consumer records with filters |
| `GET` | `/api/consumers/<id>` | Full consumer profile with 30-day trend |
| `GET` | `/api/energy-accounting` | Reconciled summary and feeder breakdown |
| `GET` | `/api/energy-accounting/daily` | Paginated daily audit logs |
| `GET` | `/api/ai/predictions` | 500 consumer predictions with triage rules |
| `GET` | `/api/ai/metrics` | Model evaluation metrics & feature importances |
| `GET` | `/api/analytics` | Datasets for all 8 analytics charts |
| `GET` | `/api/inspection` | Filterable inspection worklist candidates |
| `PUT` | `/api/inspection/<id>` | Update status, inspector, and remarks (persisted in SQLite) |
| `GET` | `/api/export/inspection` | Download inspection worklist as CSV |
| `GET` | `/api/export/energy` | Download daily energy accounting logs as CSV |
| `GET` | `/api/export/predictions` | Download AI predictions as CSV |
| `POST` | `/api/ai/train` | Retrain ML pipeline on-demand |
| `POST` | `/api/simulation/generate`| Full simulation regeneration |

---

## ⚠️ Academic Disclaimer & Limitations

1. **Investigative Nature:** Machine learning anomaly scores highlight deviations from baseline statistical expectations; they do not constitute legal proof of electricity theft.
2. **Synthetic Data Assumptions:** Feeder loads and tampering patterns are synthetically modeled assuming balanced three-phase loading and constant conductor operating temperatures.
3. **Physical Verification Mandatory:** All suspicious meters must undergo on-site physical inspection and seal verification before administrative action.

