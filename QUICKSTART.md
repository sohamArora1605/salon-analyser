# Quickstart

This project runs a FastAPI backend, Supabase Postgres/S3 storage, and a Vite React analytics dashboard.

## 1. Fill `.env`

Update `salon_platform/.env` with real Supabase values.

The local data paths are already set to:

```text
DATA_RAW_DIR=data/raw
DATA_PROFILE_PATH=data/profile.json
```

Use a Supabase Postgres pooler URL for Render:

```text
postgresql+psycopg://postgres.PROJECT_REF:DB_PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
```

Use the Supabase S3 endpoint:

```text
https://PROJECT_REF.storage.supabase.co/storage/v1/s3
```

## 2. Install Backend Dependencies

```powershell
cd salon_platform/backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## 3. Test Local API

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/api/health
http://localhost:8000/api/datasets/profile
http://localhost:8000/api/analytics/overview
http://localhost:8000/api/analytics/eda
```

## 4. Initialize Supabase Tables

First, test both Supabase Postgres and S3 Storage:

```powershell
$env:PYTHONPATH="."
python scripts/test_connections.py
```

If that passes, initialize tables:

```powershell
python scripts/init_db.py
```

## 5. Load CSVs

```powershell
python scripts/ingest_csvs.py
```

After this, Supabase will have tables for appointments, cancellations, no-shows, products, services, receipts, and ML seed events.

The ingestion script refreshes those analytics tables before loading, so reruns do not duplicate rows.

## 6. Run Frontend Dashboard

```powershell
cd ..\frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```
