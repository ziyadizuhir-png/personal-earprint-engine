# Personal Earprint Engine — Web App Backbone

Backbone for the Personal Earprint Engine V4.4.

## Current scope

This starter provides a working foundation for:

- IEM Library
- Add IEM upload form
- Measurement FR upload
- SoundEQ Dore PEQ upload
- Automatic IEM folder creation
- Automatic measurement preparation
- Exact 1000 Hz preparation when the source does not contain 1000 Hz
- Automatic `metadata.json`
- Basic validation
- Local persistent IEM storage
- FastAPI backend
- Next.js frontend

## Not implemented yet

The full V4.4 target-generation mathematics is intentionally not implemented in this backbone.

Do not invent the currently-unlocked V4.4 formulas for:

- G
- C
- Broad / Local separation
- Feature Classification thresholds
- Delta Safe thresholding

Those must be locked before production implementation.

## Project layout

```text
backend/
  app/
    main.py
    ingest.py
    models.py
    storage.py
  requirements.txt

frontend/
  app/
    page.tsx
    globals.css
    layout.tsx
  package.json
  tsconfig.json

data/
  iems/
  base-targets/
  targets/

engine/
  v44/
    constants.py
    README.md

docs/
  V44_SPEC.md
```

## Development

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend shown by Next.js.

Set `NEXT_PUBLIC_API_URL` when the backend is not on `http://localhost:8000`.
