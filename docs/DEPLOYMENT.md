# Deployment checklist

## Frontend

- Vercel project root: `frontend`
- Build command: `npm run build`
- Environment variable: `NEXT_PUBLIC_API_URL=https://<backend-host>`
- Redeploy after changing `NEXT_PUBLIC_API_URL`; it is embedded at build time.

## Backend

- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Or build `backend/Dockerfile`.
- `CORS_ORIGINS` must contain the exact browser origin, with no trailing slash.
- `DATA_ROOT` must point to persistent mounted storage.
- `STORAGE_BACKEND=filesystem` is the only implemented adapter.

## Smoke test

```bash
curl https://<backend-host>/api/health
curl https://<backend-host>/api/iems
curl https://<backend-host>/api/targets
```

The health response should have `status: "ok"`, the expected CORS origin, and a data root that survives a service restart. Upload a small IEM and Base Target file from the frontend, then restart the backend and confirm both remain in their libraries.

## Important storage limitation

The current adapter is intentionally a narrow filesystem adapter so no paid or external service is required. It is deployment-safe only when `DATA_ROOT` is a persistent disk/volume. A serverless filesystem is not persistent. A future database or object-storage adapter should implement the `StorageBackend` contract in `backend/app/storage.py` without changing the API routes or ingest layer.
