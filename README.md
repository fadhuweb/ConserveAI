# ConserveAI

**Multi-threat probabilistic forecasting and budget-constrained intervention recommendation for six Nigerian national parks.**

Repository: https://github.com/fadhuweb/ConserveAI

ConserveAI produces daily 30-day risk forecasts for **fire, drought, and vegetation degradation** across six national parks, then recommends how a park manager should spend a limited conservation budget to reduce that risk — allocated down to four zones per park. A machine-learning model serves the forecasts; an integer-linear-programming (ILP) optimiser produces the recommendations. The product is a **React web dashboard** backed by a **FastAPI** service (also browsable as a Swagger API).

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

## Deployment plan

The system is built to run on free-tier infrastructure:

| Layer | Platform |
|-------|----------|
| Database | **Neon** (serverless PostgreSQL — swap via `DATABASE_URL`) |
| Backend | **Fly.io** (always-on Docker container running FastAPI) |
| Scheduler | **GitHub Actions cron** → protected daily-forecast endpoint (replaces in-process APScheduler so a sleeping container can't miss the 3 AM job) |
| Frontend | **Vercel** (React dashboard) |

At deploy time, an `ENVIRONMENT=production` flag flips the auth cookie to `secure`/`samesite=none` and applies production CORS origins; `FRONTEND_URL` points the password-reset links at the deployed dashboard. Provisioning is a one-time `seed_data` + `backfill` run against the Neon database.

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
notebooks/        00_model_demo + supporting analysis notebooks
docs/             design spec, mockups, screenshots, demo script
results/          trained models, metrics, production model
```

## License

MIT
