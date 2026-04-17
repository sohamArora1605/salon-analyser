# Deployment Notes

## Backend on Render

1. Push this repository to GitHub.
2. Create a Render web service using `salon_platform/backend` as the root directory.
3. Use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env.example`.
5. Set `BACKEND_CORS_ORIGINS` to the deployed Vercel URL after frontend deployment.

## Frontend on Vercel

The frontend folder is prepared but not implemented in this step.

When created, configure:

```text
VITE_API_BASE_URL=https://your-render-service.onrender.com/api
```

## Supabase

Run database initialization and ingestion locally once, or run the same scripts from a secure admin environment.

Never expose `SUPABASE_SERVICE_ROLE_KEY` or S3 secret keys in the frontend.

