# Pegadaian Spatial App on Replit

## Running
- Click Run to start the `Start application` workflow (`bash scripts/start.sh`).
- The existing SvelteKit frontend serves on `0.0.0.0:5000`.
- The existing FastAPI backend serves internally on `127.0.0.1:8000`.
- Vite proxies relative `/api` requests to FastAPI, so the preview does not need a separate backend URL.
- Both processes are stopped together when the workflow stops.

## Dependencies
- Node.js 20 and Python 3.12 are configured in `.replit`.
- Frontend dependencies and their lockfile remain in `frontend/`.
- Backend requirements remain in `backend/requirements.txt`; the root `pyproject.toml` and `uv.lock` track Replit's installed Python environment.
- No Docker is used for this workflow. The original Docker files remain unchanged.

## Database and data limitations
- The imported `backend/pegadaian_spatial.db` contains 750 records. This setup preserves the existing SQLite database rather than replacing it.
- The backend attempts the repository's PostgreSQL configuration first, then logs its existing SQLite fallback when PostgreSQL is unavailable. No external database or new credentials are needed for this local setup.
- Proximity analysis can use the existing Python Haversine engine without PostGIS.
- The scraper mixes an OpenStreetMap lookup with generated locations. Do not treat the imported dataset or newly scraped records as a verified real-world pawnshop directory.
- The setup does not run scraping or replace the imported records. Both basemap modes use OpenStreetMap tiles; dark mode applies a display-only CSS filter because the original CARTO tile endpoint now requires an API key. Map tiles require internet access.
- SQLite in this workspace is for development; durable database storage and appropriate authentication for scraper/analysis endpoints should be addressed before public production use.

## Verification
- Frontend build: `cd frontend && npm run build`
- Backend health through preview: `GET /api/health`
- Data endpoints: `GET /api/pegadaian` and `GET /api/stats`