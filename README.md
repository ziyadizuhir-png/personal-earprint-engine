# Personal Earprint Engine — Dynamic Robust Target Engine

The production engine converts a dynamic collection of IEM measurements and
SoundEQ Dore preferences into one deterministic Robust Target curve. AutoEQ
and other PEQ optimizers are downstream consumers; this engine does not
generate device-specific PEQ output.

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

## Production API

- `GET /api/engine/status`
- `GET /api/iems`
- `GET /api/base-targets`
- `POST /api/robust-targets/generate`

Generation accepts `base_target_id` and an optional `iem_ids` list. The
selected Base Target defines the master grid; the active dataset defines the
votes. Each generation returns a canonical target hash and provenance summary.
The legacy `/api/v44/*` routes are compatibility-only and do not expose a
second production mathematical pipeline.

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
pytest tests/test_v44_engine.py
cd frontend
npm run build
```

GitHub Actions runs the same backend checks and frontend build on pushes and pull requests.

## GitHub Pages

The frontend is exported and deployed automatically from `main` using
`.github/workflows/pages.yml`.

Production URL:

<https://ziyadizuhir-png.github.io/personal-earprint-engine/>

The static shell is available on GitHub Pages. Live IEM/Target Library data,
uploads, health checks, and Robust Target generation still require the FastAPI
backend. Set `NEXT_PUBLIC_API_URL` to the externally hosted backend URL when
building the frontend; no production backend URL is assumed by this repository.
For local development, use `http://localhost:8000` as documented in
`frontend/.env.example` and run the backend separately.

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
