# PrithviX – Fix & Verification Report

## Setup
1. Backend: `cd backend && python -m venv .venv && .venv/Scripts/activate` (Windows) or `source .venv/bin/activate`; `pip install -r requirements.txt`
2. Copy `backend/.env.example` to `backend/.env`; set `GEMINI_API_KEY` (powers the PrithviXAI assistant) and run `earthengine authenticate` (or set the EE_* service-account vars) for NASA satellite data.
3. Start: `python main.py` (http://127.0.0.1:8000/docs). The SQLite DB is created automatically on first start.
4. Frontend: `cd frontend && npm install && npm run dev` (http://localhost:5173). `frontend/.env` only holds `VITE_API_URL`.

## Changes
- Backend no longer invents values when satellite data is missing (was 0.25 moisture, 28 °C, 0.5 NDVI, synthetic "Plot B", flat time series). Missing values are now null; the timeseries endpoint returns 503 with the reason if nothing is available.
- Dashboard plot is a single whole-farm record from real observations.
- `/api/analyze` had a broken import; removed.
- Chat: frontend never sent `farm_id`, so the assistant never received satellite data. Fixed. Satellite lookup failure no longer causes a 500. Gemini call has a 30 s timeout; frontend has a 60 s timeout and shows the backend's error message.
- Frontend: demo farms, `data/demo.ts`, Demo banners, "(Demo)" labels, local fallback plots/crops/rotations/alerts/series and the localStorage farm cache removed. Backend database is the single source of truth; empty state, loading state and backend-down error are shown. Hidden default coordinates (Hyderabad) removed: an unresolvable location now shows an error.
- Removed from ZIP: `.venv`, `node_modules`, `__pycache__`, stale `dist` (contained old demo text), `.env`, and the bundled `prithvix.db` (held test farms such as "Hyderabad Demo Farm").

## Test results
| Component | Result | Notes |
|---|---|---|
| Frontend TypeScript compile (`tsc --noEmit`) | PASS | |
| Backend Python syntax (`py_compile`, all files) | PASS | |
| Backend startup | NOT TESTED | Sandbox has no internet; FastAPI etc. could not be installed |
| API endpoints / database operations | NOT TESTED | Same reason |
| PrithviXAI / Gemini integration | NOT TESTED | No key supplied and no network |
| Earth Engine / NASA POWER | NOT TESTED | No network, no GEE credentials |
| Frontend production build / browser run | NOT TESTED | `node_modules` shipped with Windows binaries; could not rebuild here |
| Integration, dashboard with real data, fresh session, regression | NOT TESTED | Depend on a running backend |

## Open issues
- No separate "PrithviXAI API" exists in the code; the assistant uses Gemini. If you have a different PrithviXAI service, send its endpoint and request format.
- Satellite data needs Earth Engine authentication; otherwise dashboards show "--" and an explanatory error.
- Run `pytest` in `backend/` after install; existing tests were not updated or run.
