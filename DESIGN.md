# Pegadaian & Jabodetabek Pawnshop Spatial Intelligence - Design System (DESIGN.md)

An Awwwards Statskog-inspired, high-performance mass-scale spatial analytics interface engineered for geographic intelligence, competitive pawnshop density mapping, and proximity clustering across the entire Jabodetabek metropolitan agglomeration (Jakarta Pusat, Jakarta Selatan, Jakarta Timur, Jakarta Barat, Jakarta Utara, Depok, Tangerang, Tangerang Selatan, Bekasi, and Bogor).

---

## 1. Visual Identity & Aesthetic Philosophy

The visual language combines dark obsidian foundations, frosted glassmorphism layers, electric blue neon accents, and real-time spatial telemetry. It evokes high-precision spatial compute environments (reminiscent of Statskog, Palantir Foundry, and Kepler.gl).

### Core Color Palette
| Token | Hex Code | Purpose |
|---|---|---|
| **Background Obsidian** | `#0b0f19` | Deepest foundation, minimizing ocular fatigue during long analytics sessions |
| **Surface Dark (Slate)** | `#0f172a` | Container, map background, and structural panel backdrops |
| **Glass Surface** | `rgba(15, 23, 42, 0.82)` | Frosted cards with `backdrop-filter: blur(20px)` |
| **Border Glass** | `rgba(255, 255, 255, 0.08)` | 1px sub-pixel highlight border giving crisp optical depth |
| **Primary Accent (Electric Blue)** | `#3b82f6` | Active states, primary action CTA buttons, glowing radar pulses |
| **Cyan Glow Accent** | `#06b6d4` | Spatial telemetry highlights, coordinate chips |
| **Text Primary** | `#f8fafc` | High-contrast headings and metrics |
| **Text Secondary** | `#94a3b8` | Subtitles, labels, and address metadata |
| **Text Muted** | `#64748b` | Dimmed telemetry, inactive tabs |

---

## 2. Spatial Density Zone Badge System (Radius 1 km Proximity)

Spatial proximity analysis computes the exact number of neighboring pawnshops within a **1 km radius** for every single location point, categorizing each into one of 3 density tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│  ZONE        COLOR CODE   GLOW SHADOW           CRITERIA (RADIUS ≤ 1 KM)│
├────────────────────────────────────────────────────────────────────────┤
│  Tinggi      #ef4444      rgba(239, 68, 68, 0.5) ≥ 5 neighboring outlets│
│  Sedang      #f59e0b      rgba(245, 158, 11, 0.5) 2 to 4 neighbors     │
│  Rendah      #10b981      rgba(16, 185, 129, 0.5) < 2 neighbors         │
└────────────────────────────────────────────────────────────────────────┘
```

- **Tinggi (High Density - `#ef4444`)**: Hyper-concentrated commercial hotspots with severe pawnshop density (≥ 5 competitors within 1 km, e.g., Blok M / Melawai corridor, Pasar Senen / Salemba, Margonda Beji).
- **Sedang (Medium Density - `#f59e0b`)**: Balanced sub-urban clusters with healthy competition (2 to 4 competitors within 1 km, e.g., BSD Serpong, Tebet Barat, Ciputat Raya).
- **Rendah (Low Density - `#10b981`)**: Dispersed or pioneer outlets (< 2 competitors within 1 km), indicating high expansion potential or sparse suburban coverage.

---

## 3. Pawnshop Category Classification System

The application tracks, maps, and analyzes three distinct tiers of collateralized lending institutions:

| Category | Typical Brands / Entitas | Accent Badge Color |
|---|---|---|
| **BUMN (PT Pegadaian)** | Kantor Cabang (CP), Unit Pelayanan Cabang (UPC), Pegadaian Syariah | `#3b82f6` (Electric Blue) |
| **Gadai Swasta Berizin** | Pusat Gadai Indonesia, Raja Gadai Indonesia, Indogadai, Gadai Top, Budi Gadai *(OJK Licensed)* | `#a855f7` (Vibrant Violet) |
| **Gadai Mandiri / Lokal** | Toko Gadai Mandiri, Gadai Rakyat, Gadai Berkah BPKB/Emas | `#06b6d4` (Neon Cyan) |

---

## 4. Typography & Spatial Micro-Hierarchy

- **Primary Font**: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, sans-serif.
- **Monospace Telemetry**: `JetBrains Mono`, `Fira Code`, `ui-monospace` for coordinates (`lat`, `lng`), IDs, and neighbor count telemetry.
- **Hierarchy Scale**:
  - Hero Brand: `1.25rem` (`20px`) / Font-Weight: `800` / Tracking: `0.06em`
  - Stat KPI Metric: `1.15rem` (`18px`) / Font-Weight: `700` / Tracking: `-0.01em`
  - Card Titles: `0.85rem` (`13.6px`) / Font-Weight: `600` / Line-Height: `1.3`
  - Metadata & Addresses: `0.72rem` (`11.5px`) / Font-Weight: `400` / Line-Height: `1.4`
  - Micro Badges: `0.65rem` (`10.4px`) / Font-Weight: `700` / Uppercase Tracking: `0.04em`

---

## 5. UI Component Architecture

### A. 380px Glassmorphism Sidebar
- Fixed left dock with fluid internal scrolling.
- Multi-layer frosted backdrop (`backdrop-filter: blur(20px)`).
- **Header**: Brand logo with animated pulsing radar dot and live status pill (`Spatial Radius 1 km`).
- **Global KPI Cards**: Instant summary of Total Monitored Outlets, High Density hotspots, and Medium/Low distribution.
- **Action CTA**: "Jalankan Scraping Otomatis" with gradient button, animated spinning loader, and real-time status feedback.
- **Multi-Dimension Filters**:
  - Category selector (All, BUMN Pegadaian, Gadai Swasta Berizin, Gadai Mandiri/Lokal)
  - Administrative Region pills across all 10 Jabodetabek territories:
    * All Jabodetabek
    * Jakarta Pusat
    * Jakarta Selatan
    * Jakarta Timur
    * Jakarta Barat
    * Jakarta Utara
    * Depok
    * Tangerang
    * Tangerang Selatan
    * Bekasi
    * Bogor
- **Interactive Search**: Real-time fuzzy filtering across outlet name, brand, street address, and district.
- **Outlet Feed**: Scrollable card list showing real-time 1 km neighbor count badge, category chip, coordinates, and single-click camera focus.

### B. Interactive 3D Spatial Map
- **Basemap Engine**: Dark Matter CartoDB / MapLibre raster tiles with deep navy water styling.
- **Marker Design**: Custom HTML markers with dual-layer SVG pin and dynamic pulsing radar waves styled by ML cluster tier.
- **Interactive Popup**: Glassmorphism tooltip with full outlet name, category badge, geocoded address, regional metadata, and exact 1km competitor density.
- **Smooth FlyTo Camera**: Cubic-bezier dynamic easing transitions when zooming into specific outlets (`zoom: 15-16`) or resetting to Jabodetabek regional overview (`zoom: 11`).
- **HUD Overlays**: Floating layer filter controls (Toggle High/Med/Low density markers), Map Tile Switcher (Dark / OSM), and Real-time Telemetry Status Bar.
