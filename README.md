# Pegadaian & Jabodetabek Pawnshop Spatial AI Application

A complete, production-ready, mass-scale spatial intelligence and proximity analytics platform covering **ALL types of pawnshops ("tempat gadai", official Pegadaian, and licensed private pawnshops)** across the entire **Jabodetabek metropolitan region** (Jakarta Pusat, Jakarta Selatan, Jakarta Timur, Jakarta Barat, Jakarta Utara, Bogor, Depok, Tangerang, Tangerang Selatan, and Bekasi).

---

## 🏗️ Architecture & Directory Structure

```
pegadaian-spatial-app/
├── docker-compose.yml              # PostGIS, FastAPI backend & SvelteKit frontend services
├── .env                            # Environment variables & database credentials
├── DESIGN.md                       # Awwwards Statskog-inspired UI specifications
├── README.md                       # Technical documentation & quickstart guide
├── backend/
│   ├── Dockerfile                  # Python 3.10 slim FastAPI container
│   ├── requirements.txt            # FastAPI, PostGIS/Psycopg2, Scikit-learn, Geopy, etc.
│   └── src/
│       ├── main.py                 # FastAPI application with CORS & REST endpoints
│       ├── database.py             # PostgreSQL/PostGIS connection, neighbor_count & idempotent UPSERT
│       ├── scraper/
│       │   └── pegadaian_scraper.py # Mass-scale harvester across 10 Jabodetabek zones & pawnshop brands
│       └── ml/
│           └── clustering.py       # Dual PostGIS ST_DWithin & Haversine 1 km proximity analysis
└── frontend/
    ├── Dockerfile                  # Node 18 Alpine SvelteKit container
    ├── package.json                # SvelteKit, Vite & Leaflet dependencies
    ├── svelte.config.js            # SvelteKit adapter configuration
    ├── vite.config.js              # Vite server configuration
    └── src/
        ├── app.html                # Inter & JetBrains Mono typography shell
        ├── lib/
        │   └── api.js              # API client for FastAPI backend
        └── routes/
            └── +page.svelte        # Dark glassmorphism sidebar, 3D camera tilt & spatial map
```

---

## ⚡ Key Technical Features

### 1. Mass-Scale Jabodetabek Pawnshop Harvesting
- Covers all **10 administrative territories**:
  - Jakarta Pusat, Jakarta Selatan, Jakarta Timur, Jakarta Barat, Jakarta Utara
  - Bogor, Depok, Tangerang, Tangerang Selatan, Bekasi
- Indexes across **all 3 major categories**:
  - `BUMN (PT Pegadaian)`: Kantor Cabang (CP), Unit Pelayanan Cabang (UPC), Pegadaian Syariah.
  - `Gadai Swasta Berizin`: Pusat Gadai Indonesia, Raja Gadai Indonesia, Indogadai, Gadai Top, Budi Gadai *(OJK Licensed)*.
  - `Gadai Mandiri / Lokal`: Toko Gadai Mandiri, Gadai Rakyat, Gadai Berkah BPKB/Emas.
- Idempotent deduplication using PostgreSQL `ON CONFLICT (nama, alamat) DO UPDATE`.

### 2. Spatial Proximity Analysis (Radius 1 km)
- Computes exact competitor counts within a 1 km radius for every single location point via:
  - **Native PostGIS `ST_DWithin` Geography Query** (when connected to PostgreSQL/PostGIS)
  - **Vectorized Python Haversine Distance Engine** (automatic fallback for SQLite/offline local dev)
- Automatically categorizes points into 3 density tiers:
  - 🔴 **Tinggi (High Density)**: $\ge 5$ neighboring pawnshops within 1 km
  - 🟡 **Sedang (Medium Density)**: $2 \text{ to } 4$ neighboring pawnshops within 1 km
  - 🟢 **Rendah (Low Density)**: $< 2$ neighboring pawnshops within 1 km

### 3. Awwwards Statskog-Inspired Dark Glassmorphism UI
- 380px frosted glass sidebar (`backdrop-filter: blur(20px)`).
- 3D perspective camera tilt toggle (`3D Tilt` mode).
- Real-time fuzzy search and category/regional pill filtering.
- Smooth `flyTo` camera navigation with animated pulsing radar markers displaying exact 1 km competitor counts.

---

## 🚀 Running the Stack

### Option A: Docker Compose (All-in-One)

```bash
cd "pegadaian-spatial-app"
docker-compose up --build
```

- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database**: PostgreSQL 15 + PostGIS 3.3 on port `5432`

### Option B: Local Development

```bash
# Terminal 1: Backend
cd "pegadaian-spatial-app/backend"
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd "pegadaian-spatial-app/frontend"
cmd.exe /c npm run dev
```
