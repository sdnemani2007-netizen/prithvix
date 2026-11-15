# PrithviX – NASA Earth Observation Agricultural Intelligence Platform

PrithviX is an agricultural intelligence platform that transforms multi-sensor NASA Earth observation datasets and agroclimatological models into farm-level decision intelligence for farmers and agronomists.

---

## 1. Project Architecture

PrithviX is composed of two tiers:

```
prithvix/
├── backend/
│   ├── app/
│   │   ├── config.py             # Environment & configuration settings
│   │   ├── database.py           # SQLAlchemy database connection & session setup
│   │   ├── main.py               # FastAPI entrypoint, middleware & routers
│   │   ├── models/               # SQLAlchemy ORM models (Farm, SatelliteCache)
│   │   ├── schemas/              # Pydantic validation & response contracts
│   │   ├── routers/              # REST API endpoints (health, farms, dashboard, etc.)
│   │   ├── services/             # Core engines:
│   │   │   ├── earth_engine.py   # Earth Engine extractions & NASA POWER
│   │   │   ├── weather_service.py# Agroclimatology meteorology
│   │   │   ├── farm_service.py   # Farm CRUD & spatial processing
│   │   │   ├── crop_service.py   # Evidence-based crop recommendations
│   │   │   ├── irrigation_service.py # Soil moisture & deficit advisories
│   │   │   ├── alert_service.py  # Critical & warning triggers
│   │   │   └── ai_service.py     # PrithviXAI conversational assistant
│   │   └── utils/                # Geometry validation, area & unit helpers
│   ├── tests/                    # Pytest test suite (health, farms, services)
│   ├── PrithviX_pipeline.py      # Preserved core extraction adapter
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Environment variables template
│   └── pytest.ini                # Pytest configuration
├── frontend/
│   ├── src/
│   │   ├── components/           # UI widgets & trend charts
│   │   ├── data/                 # Demo data & agro-climate zone definitions
│   │   ├── pages/                # Dashboard, MyFarm, SoilClimate, Crops, Rotation, Alerts, PrithviXAI, FarmerHub
│   │   ├── services/api.ts       # Full integration layer connecting to backend
│   │   ├── types.ts              # TypeScript interfaces
│   │   ├── App.tsx               # Main application layout, sidebar & farm selector
│   │   └── main.tsx              # React DOM entry
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
└── README.md
```

---

## 2. NASA Datasets & Verification Status

| Dataset | Platform / Collection | Native Scale | Status | Details / Caveats |
| :--- | :--- | :--- | :--- | :--- |
| **NASA POWER** | `power.larc.nasa.gov` Daily Agroclimatology | 1/2° × 5/8° | **Tested & Verified (Live)** | Public REST API; works without GEE auth. Supplies T2M, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN. |
| **SMAP L4** | `NASA/SMAP/SPL4SMGP/008` | ~9 km (11,000 m) | **Verified in Pipeline / Awaiting Local GEE Auth** | Model-assimilated surface (`sm_surface`) and rootzone (`sm_rootzone`) moisture. Coarse resolution. |
| **GPM IMERG** | `NASA/GPM_L3/IMERG_V07` | ~11.1 km (0.1°) | **Verified in Pipeline / Awaiting Local GEE Auth** | 30-min precipitation rate calibrated to monthly accumulated mm. |
| **Landsat 8/9** | `LANDSAT/LC08/C02/T1_L2` + `LC09` | 30 m | **Verified in Pipeline / Awaiting Local GEE Auth** | Clear-sky QA masked NDVI, NDMI, and LST_C. Cloud-dependent revisit. |
| **MODIS** | `MODIS/061/MOD13Q1` | 250 m | **Verified in Pipeline / Awaiting Local GEE Auth** | 16-day composite vegetation indices with DetailedQA screening. |
| **SRTM** | `USGS/SRTMGL1_003` | 30 m (summarized at 90 m) | **Verified in Pipeline / Awaiting Local GEE Auth** | Static elevation and terrain slope analysis. |
| **GRACE / FO**| `NASA/GRACE/MASS_GRIDS_V04/MASCON_CRI` | ~300 km (55,660 m) | **Verified in Pipeline / Awaiting Local GEE Auth** | Mascon water storage anomaly. Regional only; collection ends Sep 2024. |
| **ECOSTRESS** | `NASA/ECOSTRESS/L2T_LSTE/V2` | 70 m | **Implemented with Catalog Warning** | Global catalog ingestion currently limited; returns `no_data` outside coverage zones. |

---

## 3. Getting Started & Running the Application

### Prerequisites

- Python 3.10 to 3.13
- Node.js 18+ and npm

---

### Backend Setup (Windows Powershell)

1. Open PowerShell and navigate to the backend directory:
   ```powershell
   cd C:\Users\Sreedhruti\.gemini\antigravity\scratch\prithvix\backend
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```powershell
   Copy-Item .env.example .env
   ```

5. (Optional) Authenticate Google Earth Engine:
   ```powershell
   earthengine authenticate
   ```
   *Note: If GEE is not yet authenticated, the backend gracefully activates real NASA POWER agroclimatology feeds and returns transparent status messages.*

6. Start the FastAPI backend server:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

Interactive Swagger documentation will be available at: `http://127.0.0.1:8000/docs`.

---

### Frontend Setup (Windows Powershell)

1. Open a second PowerShell terminal and navigate to the frontend directory:
   ```powershell
   cd C:\Users\Sreedhruti\.gemini\antigravity\scratch\prithvix\frontend
   ```

2. Install dependencies:
   ```powershell
   npm install
   ```

3. Configure environment variables:
   ```powershell
   Copy-Item .env.example .env
   ```
   *(Ensure `VITE_API_URL=http://127.0.0.1:8000`)*

4. Start the Vite development server:
   ```powershell
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

Open your browser at: `http://127.0.0.1:5173`.

---

## 4. End-to-End Workflow Demonstration

1. **Create Farm Profile**: Go to **Farmer Hub** tab. Enter Farmer Name, Farm Name, Location (e.g. `Medchal, Telangana`), Farm Size (e.g. `5 Acres`), Crop (`Cotton`), Soil Type (`Black Cotton Soil (Vertisol)`), and Water Source. Click **Save Profile & Generate Guidance**.
2. **Backend Persistence**: The farm is validated, geocoded to coordinates, and committed to the SQLite database table `farms`.
3. **Sidebar Synchronization**: The **Active Farm Profile** card in the sidebar immediately unlocks, reflecting the farm details.
4. **Retrieve NASA Observations**: Switch to **Dashboard** or **Soil & Climate**. The backend queries live NASA observations for the farm's centroid and boundaries.
5. **Crop Recommendations**: Go to **Crop Recommendations** to inspect suitability scores, agronomic reasoning, and supporting observations.
6. **Crop Rotation**: Review the seasonal 4-season sequence on the **Crop Rotation** page.
7. **Consult PrithviXAI**: Go to **PrithviX AI** and ask:
   - *"What is the condition of my farm?"*
   - *"Is my soil moisture low and should I irrigate today?"*
   The assistant answers using the farm's profile and telemetry.

---

## 5. Automated Testing

To run the backend test suite:
```powershell
cd C:\Users\Sreedhruti\.gemini\antigravity\scratch\prithvix\backend
.\.venv\Scripts\python.exe -m pytest -v
```

To run frontend TypeScript and production build verification:
```powershell
cd C:\Users\Sreedhruti\.gemini\antigravity\scratch\prithvix\frontend
npm run build
```

## Security and deployment notes

- `backend/.env` is intentionally not included in the distribution archive. Set `GEMINI_API_KEY`, Earth Engine credentials, database settings, and CORS origins as environment variables on the deployment platform.
- Never place secrets in `frontend/.env` or any `VITE_*` variable. Vite exposes `VITE_*` values to browser users.
- `backend/.env.example` contains placeholders only.
- The local SQLite database is intentionally not included. The application will create a new database when started; use PostgreSQL for multi-instance production deployments.
- `frontend/node_modules`, Python caches, and other generated files are excluded from the distribution archive.
- Production Uvicorn startup uses `PORT` when supplied and does not enable auto-reload.
- Set `PRITHVIX_CORS_ORIGINS` to the exact HTTPS origin(s) of the deployed frontend. Do not use `*` when credentials are enabled.
- The API currently has no user authentication/authorization layer. Do not expose destructive or sensitive endpoints to an untrusted public audience until authentication is added at the application or gateway layer.
