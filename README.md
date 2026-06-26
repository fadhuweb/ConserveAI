# ConserveAI

**Multi-threat probabilistic forecasting and budget-constrained intervention recommendation for six Nigerian national parks.**

Repository: https://github.com/fadhuweb/ConserveAI

ConserveAI produces daily 30-day risk forecasts for **fire, drought, and vegetation degradation** across six national parks, then recommends how a park manager should spend a limited conservation budget to reduce that risk — allocated down to four zones per park. A machine-learning model produces the forecasts; an integer-linear-programming (ILP) optimiser produces the recommendations. The product is a **React web dashboard** backed by a **FastAPI** service (also browsable as a Swagger API).

---

## Live demo

The system is deployed and live:

- **App:** https://conserve-ai.vercel.app
- **API:** https://conserveai-api.fly.dev (Swagger at [`/docs`](https://conserveai-api.fly.dev/docs), health at [`/health`](https://conserveai-api.fly.dev/health))

Log in with `admin` / `admin2025` (national view) or `manager_yankari` / `conserve2025` (single park). Full account list under [Demo accounts](#demo-accounts).

---

## Key documents

| Document | What it covers |
|----------|----------------|
| **[Testing results](docs/TESTING.md)** | Testing strategies (unit, model evaluation, API, end-to-end), results with screenshots, different data values, and local-vs-cloud performance |
| **[Analysis](docs/ANALYSIS.md)** | Results against the proposal objectives, discussion, and recommendations / future work |
| **[Deployment guide](docs/deployment_guide.md)** | Step-by-step deployment on Neon, Fly.io, Vercel, and the GitHub Actions cron |

---

## What you can demo (the dashboard)

| Capability | Where in the app |
|------------|------------------|
| Role-based login (JWT in an httpOnly cookie) | Login screen |
| National risk overview — Nigeria map with per-park risk markers + summary table | Admin → **National Overview** |
| 30-day forecast chart (fire / drought / vegetation) over the last 60 days | **Park Detail** |
| Forecast drivers — the key features behind each threat | **Park Detail** |
| Budget-constrained, **zone-level** intervention recommendation (live budget slider, intervention toggles, zone priority) | **Park Detail** |
| Zone deployment map (units allocated per zone) | **Park Detail** |
| Provision park managers — system emails a temporary password; forced change on first login | Admin → **Park Managers** |
| Park-scoping — managers only ever see their own park; admin sees the national view | Enforced app-wide (frontend routing + backend 403s) |

The underlying service is also browsable as a **Swagger API** at `http://localhost:8000/docs`.

The **ML model notebook** is [`notebooks/00_model_demo.ipynb`](notebooks/00_model_demo.ipynb) — data engineering, the architecture comparison, and performance metrics (F2, ROC-AUC, precision/recall) with rendered outputs.

---

## Tech stack

- **Frontend:** React (Vite) · Ant Design · Leaflet (maps) · Recharts (forecast charts)
- **Backend:** FastAPI · SQLAlchemy · PostgreSQL · APScheduler
- **ML:** scikit-learn (Random Forest, self-training), XGBoost, PyTorch (LSTM, Transformer) — supervised + semi-supervised
- **Optimiser:** PuLP (integer linear programming)
- **Data sources:** Open-Meteo, NASA POWER, Google Earth Engine, NASA FIRMS (VIIRS/MODIS)
- **Auth:** JWT (httpOnly cookie) + bcrypt, park-scoped; admin-provisioned accounts with emailed temporary passwords

---

## Setup (Windows / PowerShell)

> Prerequisites: **Python 3.12+**, **Node.js 18+**, **PostgreSQL 17** installed.

### Backend

**1. Clone and create the virtual environment**
```powershell
git clone https://github.com/fadhuweb/ConserveAI.git
cd ConserveAI
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**2. Create the database** (adjust the PostgreSQL version in the path if needed)
```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE USER conserveai WITH PASSWORD 'conserveai';"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE conserveai OWNER conserveai;"
```

**3. Configure environment** — create a `.env` file in the project root:
```
DATABASE_URL=postgresql://conserveai:conserveai@localhost:5432/conserveai
JWT_SECRET_KEY=change-this-to-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=8
ENVIRONMENT=development
LOG_LEVEL=INFO
FRONTEND_URL=http://localhost:5173
NASA_FIRMS_API_KEY=          # optional; fire counts default to 0 if absent

# Email — needed only to create new manager accounts (admin user-provisioning).
# SMTP_USER is a Gmail address; SMTP_PASSWORD is a Gmail App Password.
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

**4. Seed the database** (creates tables, 7 users, intervention catalog, 24 zones)
```powershell
python -m src.backend.seed_data
```

**5. Backfill forecast history** (loads historical features + generates 60+ days of forecasts)
```powershell
python -m src.backend.jobs.backfill --days 60
```

**6. Run the backend API**
```powershell
uvicorn src.backend.main:app --reload --port 8000
```
The Swagger UI is then at **http://localhost:8000/docs**.

### Frontend

**7. In a second terminal, install and run the dashboard**
```powershell
cd frontend
npm install
npm run dev
```

**8. Open the dashboard** → **http://localhost:5173**

---

## Demo accounts

| Username | Password | Role | Scope |
|----------|----------|------|-------|
| `manager_yankari` | `conserve2025` | manager | Yankari only |
| `manager_cross_river` | `conserve2025` | manager | Cross River only |
| `manager_gashaka_gumti` | `conserve2025` | manager | Gashaka-Gumti only |
| `manager_kainji_lake` | `conserve2025` | manager | Kainji Lake only |
| `manager_chad_basin` | `conserve2025` | manager | Chad Basin only |
| `manager_old_oyo` | `conserve2025` | manager | Old Oyo only |
| `admin` | `admin2025` | admin | all parks + national overview |

**Quick walkthrough:** open the dashboard → log in as **`admin`** to see the National Overview map and per-park risk table → then log in as a manager (e.g. **`manager_chad_basin`**) to explore that park's 60-day forecast chart and generate a budget-constrained, zone-level recommendation. As admin, **Park Managers** shows the account-provisioning flow.

> New managers created through the admin UI receive a temporary password by email and set their own on first login, so creating accounts requires the SMTP variables above. The seeded demo accounts work without any email setup.

---

## Designs

- **Live dashboard** — the React app above is the primary interface (login, national overview, park detail, manager provisioning).
- **Interface mockup:** [`docs/mockups/conserveai_mockup.html`](docs/mockups/conserveai_mockup.html) — the original design reference.
- **Design spec & wireframes:** [`docs/DESIGN.md`](docs/DESIGN.md)
- **Screenshots:** [`docs/screenshots/`](docs/screenshots/)

---

## Testing

Run the automated test suite from the project root:

```powershell
python -m pytest tests/ -v
```

17 unit tests pass, covering the ILP optimiser (budget, capacity, type toggles, urgency floors) and authentication (bcrypt hashing, password policy, JWT access / reset tokens). The full testing record — unit tests, model evaluation on a held-out 2024–2025 test set (Fire F2 0.94, Drought 0.89, Vegetation 0.75), API / integration tests, different-data-value runs, and performance across local and cloud — is in **[`docs/TESTING.md`](docs/TESTING.md)**.

---

## Analysis

An analysis of the results against the proposal objectives — what was achieved, what fell short (label leakage, vegetation accuracy, threat scope), the discussion, and recommendations / future work — is in **[`docs/ANALYSIS.md`](docs/ANALYSIS.md)**.

---

## Deployment (live)

The system is deployed and running on free-tier infrastructure:

| Layer | Platform | URL |
|-------|----------|-----|
| Frontend | **Vercel** | https://conserve-ai.vercel.app |
| Backend | **Fly.io** (Docker, FastAPI) | https://conserveai-api.fly.dev |
| Database | **Neon** (serverless PostgreSQL, Frankfurt) | via `DATABASE_URL` |
| Scheduler | **GitHub Actions cron** (daily 04:00 UTC) → protected `POST /jobs/run-daily-forecast` on Fly | — |

Production behaviour is gated on `ENVIRONMENT=production`: the auth cookie becomes `secure` / `samesite=none` for the cross-domain Vercel↔Fly hop, production CORS origins apply, and the in-process scheduler is replaced by the external cron (a sleeping container can't miss the job). The daily cron keeps the database current automatically. Step-by-step instructions are in **[`docs/deployment_guide.md`](docs/deployment_guide.md)**, and deployment was verified end-to-end against the live URLs (see [`docs/TESTING.md`](docs/TESTING.md)).

---

## Video demo

https://drive.google.com/file/d/13hFM-HJQQouwi9S0ZQP2i-dPRxxds7mD/view?usp=sharing

---

## Repository structure

```
frontend/         React dashboard (Vite) — pages, components, AntD UI
src/
  backend/        FastAPI app — auth, routes, models, jobs, config
  models/         ML training, evaluation, production model packaging
  optimizer/      ILP recommender, sensitivity analysis, intervention catalog
  data_pipeline/  data ingestion & feature engineering
tests/            pytest suite — optimiser + auth unit tests
notebooks/        00_model_demo + supporting analysis notebooks
docs/             TESTING.md, deployment_guide.md, design spec, demo script
results/          trained models, metrics, production model
Dockerfile, fly.toml          backend deployment (Fly.io)
frontend/vercel.json          frontend deployment (Vercel SPA routing)
.github/workflows/            daily-forecast cron (GitHub Actions)
```
