# Salon Analytics Platform

Full-stack salon analytics project with a FastAPI backend, Supabase Postgres, Supabase S3-compatible Storage, and a Vite React dashboard.

The CSV files are treated as one hypothetical salon dataset even if their original sources differ.

## Structure

- `backend/`: FastAPI API, Supabase Postgres connection, analytics endpoints, Supabase Storage upload route, CSV profiling and ingestion scripts.
- `frontend/`: Vite React dashboard for revenue, appointments, staff, products, services, and no-show risk.
- `data/raw/`: Local CSV files copied from the workspace root.
- `.env`: Local environment variables.
- `.env.example`: Safe template for deployment and sharing.

## Supabase Setup

1. Create a Supabase project.
2. Create a Storage bucket named `salon-assets`.
3. If uploaded images should be visible in browser dashboards, make the bucket public or add signed URL support later.
4. In Supabase project settings, copy the Postgres connection string into `DATABASE_URL`.
5. In Supabase Storage settings, create S3 access keys and fill:
   - `SUPABASE_S3_ENDPOINT`
   - `SUPABASE_S3_REGION`
   - `SUPABASE_S3_BUCKET`
   - `SUPABASE_S3_ACCESS_KEY_ID`
   - `SUPABASE_S3_SECRET_ACCESS_KEY`

## Backend Setup

From `salon_platform/backend`:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Initialize database tables:

```powershell
python scripts/init_db.py
```

Profile local CSV files:

```powershell
python scripts/profile_datasets.py
```

Ingest CSV files into Supabase Postgres:

```powershell
python scripts/ingest_csvs.py
```

The ingestion script refreshes the analytics tables before loading, so reruns do not duplicate rows.

Run the API:

```powershell
uvicorn app.main:app --reload
```

Useful endpoints:

- `GET /api/health`
- `GET /api/health/db`
- `GET /api/datasets`
- `GET /api/datasets/profile`
- `GET /api/analytics/overview`
- `GET /api/analytics/trends`
- `GET /api/analytics/staff`
- `GET /api/analytics/services`
- `GET /api/analytics/products`
- `GET /api/analytics/ml`
- `GET /api/analytics/eda`
- `GET /api/analytics/predict/options`
- `POST /api/analytics/predict/no-show`
- `POST /api/uploads/image`

## Frontend Setup

From `salon_platform/frontend`:

```powershell
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

For deployment, set `VITE_API_BASE_URL` to the deployed backend URL ending in `/api`.

## Remaining Production Steps

1. Deploy the FastAPI backend and Vite frontend.
2. Move back to the Supabase pooler URL for hosted environments that do not support direct IPv6 Postgres.
3. Add authentication before exposing private business metrics.
4. Replace the heuristic no-show segments with a trained model when more labeled data is available.
