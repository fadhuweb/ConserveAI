# ConserveAI Deployment Guide

Production stack (all free tier): **Neon** (Postgres) · **Fly.io** (FastAPI backend) ·
**Vercel** (React frontend) · **GitHub Actions** (daily-forecast cron).

The whole production behaviour is gated on `ENVIRONMENT=production`, so local dev
keeps using http/localhost/lax cookies and the in-process scheduler. Setting
`ENVIRONMENT=production` flips: Secure + SameSite=None cookies, the deployed
frontend added to CORS, and the in-process APScheduler disabled (the GitHub cron
drives the job instead).

---

## 1. Database — Neon ✅ done
- Project created (AWS Frankfurt, PG 17).
- Local Postgres migrated via `pg_dump` → `psql` restore (all 7 tables).
- Connection string is the app's `DATABASE_URL`. Use the **pooled** string for the
  app; the **direct** (no `-pooler`) string for one-off restores/migrations.

To reload from a fresh dump:
```bash
pg_dump "<LOCAL_DATABASE_URL>" --no-owner --no-privileges -f backup/conserveai_dump.sql
psql "<NEON_DIRECT_URL>" -f backup/conserveai_dump.sql
```

## 2. Earth Engine service account ✅ done
- Service account `conserveai-ee@conserve-ai.iam.gserviceaccount.com` with roles
  **Earth Engine Resource Viewer** + **Service Usage Consumer**.
- Local: key at `secrets/gee-key.json`, referenced by `GEE_KEY_FILE`.
- Fly: set the **contents** of that JSON as the secret `GEE_KEY_DATA` (the code
  reads `GEE_KEY_DATA` when present, else falls back to `GEE_KEY_FILE`).

## 3. Backend — Fly.io
Files: `Dockerfile`, `.dockerignore`, `fly.toml`, `requirements-api.txt` (slim:
no torch/xgboost/shap). The 17 MB production model is baked into the image.

```bash
fly launch --no-deploy           # creates/links the app (edit `app` in fly.toml)
# Set secrets (values from your .env / Neon / GEE key):
fly secrets set \
  DATABASE_URL="<NEON_POOLED_URL>" \
  JWT_SECRET_KEY="<long-random>" \
  NASA_FIRMS_API_KEY="<key>" \
  GEE_PROJECT="conserve-ai" \
  GEE_SERVICE_ACCOUNT="conserveai-ee@conserve-ai.iam.gserviceaccount.com" \
  GEE_KEY_DATA="$(cat secrets/gee-key.json)" \
  JOB_TRIGGER_TOKEN="<long-random>" \
  FRONTEND_URL="https://<your-app>.vercel.app" \
  SMTP_USER="<gmail>" SMTP_PASSWORD="<gmail-app-password>"
# ENVIRONMENT=production is already set in fly.toml [env].
fly deploy
fly open                          # https://<app>.fly.dev  — check /health
```

## 4. Frontend — Vercel
- Import the GitHub repo in Vercel; set **Root Directory = `frontend`** (Vite preset).
- Env var: `VITE_API_BASE_URL = https://<app>.fly.dev`
- Deploy. Note the resulting URL (e.g. `https://conserveai.vercel.app`).

## 5. CORS / cross-domain cookies
- Set the Fly secret `FRONTEND_URL` to the Vercel URL (step 3) and redeploy if it
  changed — that adds the origin to CORS, and `ENVIRONMENT=production` makes the
  auth cookie Secure + SameSite=None so it survives the Vercel↔Fly cross-domain hop.

## 6. Daily-forecast cron — GitHub Actions
File: `.github/workflows/daily-forecast.yml` (cron 04:00 UTC ≈ 05:00 Lagos).
- Add repo secrets (Settings → Secrets and variables → Actions):
  - `API_BASE_URL` = `https://<app>.fly.dev`
  - `JOB_TRIGGER_TOKEN` = same value as the Fly secret
- Test immediately via **Actions → Daily forecast → Run workflow** (workflow_dispatch).

## 7. Dry run / shakeout
1. `GET /health` on Fly → `{"status":"ok","database":"ok"}`.
2. Log in as `admin` on the Vercel site → national overview loads.
3. Log in as a manager → forecast + run a recommendation.
4. Manually run the cron; confirm `forecasts` gains a new row for today.
5. If a forecast gap exists, backfill against Neon:
   `python -m src.backend.jobs.daily_forecast --fill-from <date> --fill-to <today>`

---

### All Fly secrets at a glance
`DATABASE_URL`, `JWT_SECRET_KEY`, `NASA_FIRMS_API_KEY`, `GEE_PROJECT`,
`GEE_SERVICE_ACCOUNT`, `GEE_KEY_DATA`, `JOB_TRIGGER_TOKEN`, `FRONTEND_URL`,
`SMTP_USER`, `SMTP_PASSWORD` (and `SMTP_FROM` if different).
