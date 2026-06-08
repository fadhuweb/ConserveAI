# ConserveAI

**Multi-threat probabilistic forecasting and budget-constrained intervention recommendation for six Nigerian national parks.**

Repository: https://github.com/fadhuweb/ConserveAI

ConserveAI produces daily 30-day risk forecasts for **fire, drought, and vegetation degradation** across six national parks, then recommends how a park manager should spend a limited conservation budget to reduce that risk — allocated down to four zones per park. A machine-learning model serves the forecasts; an integer-linear-programming (ILP) optimiser produces the recommendations. The working interface for this demo is the **FastAPI Swagger UI**.

---

## What you can demo

| Capability | Endpoint |
|------------|----------|
| Log in (JWT in httpOnly cookie) | `POST /auth/login` |
| 30-day forecast history for a park | `GET /forecasts/{park}` |
| Latest forecast for all parks (admin) | `GET /national-overview` |
| Budget-constrained, zone-level recommendation | `POST /recommend` |
| Robustness / sensitivity analysis | `POST /sensitivity` |
| Parks, zones, intervention catalog | `GET /parks`, `/parks/{id}/zones`, `/catalog` |

The **ML model notebook** is [`notebooks/00_model_demo.ipynb`](notebooks/00_model_demo.ipynb) — data engineering, the 8-configuration architecture comparison, and performance metrics (F2, ROC-AUC, precision/recall) with rendered outputs.

---

## Tech stack

- **Backend:** FastAPI · SQLAlchemy · PostgreSQL · APScheduler
- **ML:** scikit-learn (Random Forest), XGBoost, PyTorch (LSTM, Transformer) — supervised + semi-supervised
- **Optimiser:** PuLP (integer linear programming)
- **Data sources:** Open-Meteo, NASA POWER, Google Earth Engine, NASA FIRMS (MODIS)
- **Auth:** JWT (httpOnly cookie) + bcrypt, park-scoped

---

## Setup (Windows / PowerShell)

> Prerequisites: Python 3.12+, PostgreSQL 17 installed.

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
NASA_FIRMS_API_KEY=          # optional; fire counts default to 0 if absent
```

**4. Seed the database** (creates tables, 7 users, intervention catalog, 24 zones)
```powershell
python -m src.backend.seed_data
```

**5. Backfill forecast history** (loads historical features + generates 60+ days of forecasts)
```powershell
python -m src.backend.jobs.backfill --days 60
```

**6. Run the API**
```powershell
uvicorn src.backend.main:app --reload --port 8000
```

**7. Open the interactive API** → **http://localhost:8000/docs**

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

**Quick walkthrough in Swagger:** log in as `admin` → `GET /national-overview` → `GET /forecasts/yankari` → `POST /recommend` with `{"park":"yankari","budget":10000}` → `POST /sensitivity` with `{"park":"yankari","budget":10000,"n_samples":30}`.

---

## Designs

- **Interface mockup (rendered):** [`docs/mockups/conserveai_mockup.html`](docs/mockups/conserveai_mockup.html) — open in a browser to see the planned dashboard (login, park-manager dashboard, national overview).
- **Design spec & wireframes:** [`docs/DESIGN.md`](docs/DESIGN.md)
- **Interface screenshots:** [`docs/screenshots/`](docs/screenshots/) — Swagger UI in action + mockup frames.

---

## Deployment plan

The system is built to run on free-tier infrastructure:

| Layer | Platform |
|-------|----------|
| Database | **Neon** (serverless PostgreSQL — swap via `DATABASE_URL`) |
| Backend | **Fly.io** (always-on Docker container running FastAPI) |
| Scheduler | **GitHub Actions cron** → protected daily-forecast endpoint (replaces in-process APScheduler so a sleeping container can't miss the 3 AM job) |
| Frontend | **Vercel** (planned React dashboard) |

At deploy time, an `ENVIRONMENT=production` flag flips the auth cookie to `secure`/`samesite=none` and applies production CORS origins. Provisioning is a one-time `seed_data` + `backfill` run against the Neon database.

---

## Video demo

📹 **[Demo video link — to be added]**

---

## Repository structure

```
src/
  backend/        FastAPI app — auth, routes, models, jobs, config
  models/         ML training, evaluation, production model packaging
  optimizer/      ILP recommender, sensitivity analysis, intervention catalog
  data_pipeline/  data ingestion & feature engineering
notebooks/        00_model_demo + supporting analysis notebooks
docs/             design spec, mockups, screenshots
results/          trained models, metrics, production model
```

## License

MIT
