# Personal Earprint Studio v0.3.0

The canonical production engine is Personal Earprint Studio v0.3.0. It
combines the nine initial IEM measurement/PEQ pairs into one deterministic
Robust Target curve. The browser owns the numerical PEQ solver; the FastAPI
service owns persistent source data and artifact storage.

The v0.3.0 contract is documented in
`docs/PERSONAL_EARPRINT_STUDIO_V0.3.0_SPEC.md`. V4.4 files are legacy audit
material and are not mathematical authority.

## Included now

- Next.js frontend in `frontend/`
- FastAPI backend in `backend/` for storage and source-data delivery
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
- `GET /api/robust-targets/inputs`

The browser requests prepared inputs with `base_target_id` and `iem_ids`, then
runs `frontend/lib/personal-earprint-v030.ts`. The legacy
`POST /api/robust-targets/generate` and `/api/v44/*` routes remain compatibility
surfaces only and are not used by the v0.3.0 UI.

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

The repository includes `render.yaml` for a Render Docker Web Service. Mount a
persistent disk at `/data` and configure `DATA_ROOT=/data`,
`STORAGE_BACKEND=filesystem`, and
`CORS_ORIGINS=https://ziyadizuhir-png.github.io`. After Render provides the
HTTPS service URL, set the GitHub repository variable `NEXT_PUBLIC_API_URL` and
rerun the Pages deployment. GitHub Pages cannot run FastAPI or provide
persistent storage.

Render uses the repository root as the Docker context and
`backend/Dockerfile`; the Dockerfile copies the backend, engine, and seeded
data directories explicitly. The backend is not considered deployed until a
public HTTPS service has been created and `/api/health` and
`/api/engine/status` respond successfully.

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
