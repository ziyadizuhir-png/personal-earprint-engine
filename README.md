# Personal Earprint Engine — Deployment-ready Backbone

Deployment-ready foundation for the Personal Earprint Engine V4.4 web app.
This repository deliberately does **not** implement the locked V4.4 target-generation mathematics.

## Included now

- Next.js frontend in `frontend/`
- FastAPI backend in `backend/`
- IEM Library and Add IEM upload flow
- Target Library and Add Target upload flow
- Original upload preservation plus prepared frequency-response CSV
- Exact 1000 Hz preparation by log-frequency interpolation
- Environment-driven API URL and CORS configuration
- `/api/health` health check
- Storage adapter boundary with configurable `DATA_ROOT`
- Dockerfile for the backend and CI verification workflow

## V4.4 scope boundary

No formulas for G, C, Broad/Local separation, feature-classification thresholds, or Delta Safe thresholding are implemented here. Target uploads only validate and prepare the source data; `mathematics_applied` is explicitly recorded as `false`.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Frontend in another terminal:

```bash
cd frontend
npm install
copy .env.example .env.local  # Windows
# cp .env.example .env.local  # macOS/Linux
npm run dev
```

Open `http://localhost:3000`. The backend defaults to `http://localhost:8000`.

## Deployment

The frontend and backend are separate deployables:

1. Deploy `frontend/` as the Vercel project root. Set `NEXT_PUBLIC_API_URL` to the public HTTPS URL of the FastAPI backend. `frontend/vercel.json` contains the Next.js build setting.
2. Deploy `backend/` as a container using `backend/Dockerfile` (or any Python service that runs `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
3. Set backend `CORS_ORIGINS` to the exact frontend origin, for example `https://your-app.vercel.app`. Multiple origins are comma-separated.
4. Set `DATA_ROOT` to a mounted persistent directory on the backend host. The filesystem adapter is suitable for local development and a persistent volume; it is not safe to use an ephemeral serverless filesystem for user uploads.
5. Verify `GET https://your-api.example.com/api/health` before opening the frontend. The response reports CORS origins and the active storage root.

No paid storage service is required by this backbone. If a deployment cannot provide a persistent volume, implement another `StorageBackend` adapter before enabling that deployment; do not silently rely on ephemeral storage.

## Verification

```bash
python -m compileall backend/app
pytest backend/tests
cd frontend
npm run build
```

GitHub Actions runs the same backend checks and frontend build on pushes and pull requests.

## Data layout

```text
DATA_ROOT/
  iems/<slug>/
    measurement_source.txt
    measurement.csv
    preferred.txt
    metadata.json
  base-targets/<slug>/
    target_source.txt
    target.csv
    metadata.json
  targets/<slug>/
    target_source.txt
    target.csv
    metadata.json
```
