import os
import sqlite3
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
import psycopg2  # pyrefly: ignore [missing-import] # type: ignore
from psycopg2.extras import RealDictCursor, execute_values  # pyrefly: ignore [missing-import] # type: ignore

def build_accurate_gmaps_url(nama: Optional[str] = "", alamat: Optional[str] = "", wilayah: Optional[str] = "", lat: Any = None, lng: Any = None) -> str:
    """
    Generate high-accuracy Google Maps search URL combining Nama + Alamat + Wilayah
    Format: https://www.google.com/maps/search/?api=1&query={nama}+{alamat}+{wilayah}
    """
    clean_parts: List[str] = []
    for p in (nama, alamat, wilayah):
        if p:
            val = p.strip()
            if val:
                clean_parts.append(val)
    query_str = " ".join(clean_parts)
    encoded = urllib.parse.quote_plus(query_str)
    return f"https://www.google.com/maps/search/?api=1&query={encoded}"
# Native zero-dependency .env loader to satisfy static analyzers (Pyrefly)
def _load_dotenv_native():
    env_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    for path in env_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            if key and key not in os.environ:
                                os.environ[key] = val
                break
            except Exception:
                pass

_load_dotenv_native()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Database configuration from environment variables with sensible defaults
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "pegadaian_spatial")

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "pegadaian_spatial.db")
_USE_SQLITE = False


def check_postgres_available() -> bool:
    """Test if PostgreSQL database is reachable."""
    global _USE_SQLITE
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            connect_timeout=2
        )
        conn.close()
        _USE_SQLITE = False
        return True
    except Exception as e:
        logger.warning(f"PostgreSQL not accessible on {DB_HOST}:{DB_PORT}/{DB_NAME} ({e}). Falling back to local SQLite database: {SQLITE_DB_PATH}")
        _USE_SQLITE = True
        return False


def get_db_connection():
    """Establish and return a connection to PostgreSQL (or SQLite fallback)."""
    global _USE_SQLITE
    if not _USE_SQLITE:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME,
                connect_timeout=3
            )
            return conn
        except Exception:
            _USE_SQLITE = True

    # Fallback to SQLite
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initialize database schemas and create the pegadaian_cabang table
    with required spatial columns, kategori, neighbor_count, and unique constraint on (nama, alamat).
    """
    check_postgres_available()
    conn = get_db_connection()

    if not _USE_SQLITE:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS pegadaian_cabang (
            id SERIAL PRIMARY KEY,
            nama VARCHAR(255) NOT NULL,
            alamat TEXT NOT NULL,
            wilayah VARCHAR(100),
            lat FLOAT,
            lng FLOAT,
            density_zone VARCHAR(50),
            neighbor_count INT DEFAULT 0,
            kategori VARCHAR(100) DEFAULT 'BUMN (PT Pegadaian)',
            google_maps_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_cabang UNIQUE (nama, alamat)
        );
        ALTER TABLE pegadaian_cabang ADD COLUMN IF NOT EXISTS neighbor_count INT DEFAULT 0;
        ALTER TABLE pegadaian_cabang ADD COLUMN IF NOT EXISTS kategori VARCHAR(100) DEFAULT 'BUMN (PT Pegadaian)';
        ALTER TABLE pegadaian_cabang ADD COLUMN IF NOT EXISTS google_maps_url TEXT;
        CREATE INDEX IF NOT EXISTS idx_pegadaian_wilayah ON pegadaian_cabang (wilayah);
        CREATE INDEX IF NOT EXISTS idx_pegadaian_coords ON pegadaian_cabang (lat, lng);
        CREATE INDEX IF NOT EXISTS idx_pegadaian_density ON pegadaian_cabang (density_zone);
        CREATE INDEX IF NOT EXISTS idx_pegadaian_kategori ON pegadaian_cabang (kategori);
        """
        try:
            with conn:
                cur = conn.cursor()
                try:
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                    except Exception:
                        conn.rollback()
                    cur.execute(create_table_query)
                    
                    # Backfill high-accuracy Google Maps query string URL: https://www.google.com/maps/search/?api=1&query={nama}+{alamat}+{wilayah}
                    cur.execute("SELECT id, nama, alamat, wilayah FROM pegadaian_cabang;")
                    cabang_rows = cur.fetchall()
                    if cabang_rows:
                        updates = [(build_accurate_gmaps_url(r[1], r[2], r[3]), r[0]) for r in cabang_rows]
                        cur.executemany("UPDATE pegadaian_cabang SET google_maps_url = %s WHERE id = %s;", updates)
                    conn.commit()
                finally:
                    cur.close()
            logger.info("PostgreSQL Database initialized: Table 'pegadaian_cabang' is ready.")
        finally:
            conn.close()
    else:
        # SQLite Schema
        create_table_stmt = """
        CREATE TABLE IF NOT EXISTS pegadaian_cabang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            alamat TEXT NOT NULL,
            wilayah TEXT,
            lat REAL,
            lng REAL,
            density_zone TEXT,
            neighbor_count INTEGER DEFAULT 0,
            kategori TEXT DEFAULT 'BUMN (PT Pegadaian)',
            google_maps_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_cabang UNIQUE (nama, alamat)
        );
        """
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(create_table_stmt)

                # Check and add missing columns dynamically in SQLite
                cur.execute("PRAGMA table_info(pegadaian_cabang);")
                columns = [col[1] for col in cur.fetchall()]
                if "kategori" not in columns:
                    cur.execute("ALTER TABLE pegadaian_cabang ADD COLUMN kategori TEXT DEFAULT 'BUMN (PT Pegadaian)';")
                if "neighbor_count" not in columns:
                    cur.execute("ALTER TABLE pegadaian_cabang ADD COLUMN neighbor_count INTEGER DEFAULT 0;")
                if "google_maps_url" not in columns:
                    cur.execute("ALTER TABLE pegadaian_cabang ADD COLUMN google_maps_url TEXT;")

                # Backfill high-accuracy Google Maps query string URL: https://www.google.com/maps/search/?api=1&query={nama}+{alamat}+{wilayah}
                cur.execute("SELECT id, nama, alamat, wilayah FROM pegadaian_cabang;")
                cabang_rows = cur.fetchall()
                if cabang_rows:
                    updates = [(build_accurate_gmaps_url(r[1], r[2], r[3]), r[0]) for r in cabang_rows]
                    cur.executemany("UPDATE pegadaian_cabang SET google_maps_url = ? WHERE id = ?;", updates)

                cur.execute("CREATE INDEX IF NOT EXISTS idx_pegadaian_wilayah ON pegadaian_cabang (wilayah);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pegadaian_coords ON pegadaian_cabang (lat, lng);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pegadaian_density ON pegadaian_cabang (density_zone);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pegadaian_kategori ON pegadaian_cabang (kategori);")
                conn.commit()
            logger.info(f"SQLite Database initialized with full schema at {SQLITE_DB_PATH}: Table 'pegadaian_cabang' is ready.")
        finally:
            conn.close()


def upsert_data(data_list: List[Dict[str, Any]]) -> int:
    """
    Mass-scale idempotent UPSERT into pegadaian_cabang table.
    Enforces UNIQUE (nama, alamat) constraint so records are updated rather than duplicated.
    """
    if not data_list:
        logger.warning("upsert_data called with empty data_list")
        return 0

    conn = get_db_connection()

    if not _USE_SQLITE:
        query = """
        INSERT INTO pegadaian_cabang (nama, alamat, wilayah, lat, lng, density_zone, neighbor_count, kategori, google_maps_url)
        VALUES %s
        ON CONFLICT (nama, alamat) 
        DO UPDATE SET 
            lat = EXCLUDED.lat, 
            lng = EXCLUDED.lng, 
            wilayah = EXCLUDED.wilayah,
            kategori = COALESCE(EXCLUDED.kategori, pegadaian_cabang.kategori),
            density_zone = COALESCE(EXCLUDED.density_zone, pegadaian_cabang.density_zone),
            neighbor_count = COALESCE(EXCLUDED.neighbor_count, pegadaian_cabang.neighbor_count),
            google_maps_url = COALESCE(EXCLUDED.google_maps_url, pegadaian_cabang.google_maps_url)
        RETURNING id;
        """
        records = [
            (
                item.get("nama"),
                item.get("alamat"),
                item.get("wilayah"),
                item.get("lat"),
                item.get("lng"),
                item.get("density_zone"),
                item.get("neighbor_count", 0),
                item.get("kategori", "BUMN (PT Pegadaian)"),
                item.get("google_maps_url") or build_accurate_gmaps_url(item.get("nama"), item.get("alamat"), item.get("wilayah"), item.get("lat"), item.get("lng"))
            )
            for item in data_list
            if item.get("nama") and item.get("alamat")
        ]
        try:
            with conn:
                cur = conn.cursor()
                try:
                    execute_values(cur, query, records)
                    affected_count = cur.rowcount
                    conn.commit()
                    logger.info(f"Successfully upserted {len(records)} pawnshop records into PostgreSQL.")
                    return affected_count
                finally:
                    cur.close()
        finally:
            conn.close()
    else:
        # SQLite Upsert
        query = """
        INSERT INTO pegadaian_cabang (nama, alamat, wilayah, lat, lng, density_zone, neighbor_count, kategori, google_maps_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(nama, alamat) DO UPDATE SET
            lat = excluded.lat,
            lng = excluded.lng,
            wilayah = excluded.wilayah,
            kategori = COALESCE(excluded.kategori, pegadaian_cabang.kategori),
            density_zone = COALESCE(excluded.density_zone, pegadaian_cabang.density_zone),
            neighbor_count = COALESCE(excluded.neighbor_count, pegadaian_cabang.neighbor_count),
            google_maps_url = COALESCE(excluded.google_maps_url, pegadaian_cabang.google_maps_url);
        """
        records = [
            (
                item.get("nama"),
                item.get("alamat"),
                item.get("wilayah"),
                item.get("lat"),
                item.get("lng"),
                item.get("density_zone"),
                item.get("neighbor_count", 0),
                item.get("kategori", "BUMN (PT Pegadaian)"),
                item.get("google_maps_url") or build_accurate_gmaps_url(item.get("nama"), item.get("alamat"), item.get("wilayah"), item.get("lat"), item.get("lng"))
            )
            for item in data_list
            if item.get("nama") and item.get("alamat")
        ]
        try:
            with conn:
                conn.executemany(query, records)
                affected = len(records)
                logger.info(f"Successfully upserted {affected} pawnshop records into SQLite.")
                return affected
        finally:
            conn.close()


def get_all_cabang(wilayah: Optional[str] = None, kategori: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all pawnshop records across Jabodetabek, optionally filtered by wilayah and/or kategori.
    """
    conn = get_db_connection()
    try:
        if not _USE_SQLITE:
            query = """
            SELECT id, nama, alamat, wilayah, lat, lng, density_zone, COALESCE(neighbor_count, 0) as neighbor_count, COALESCE(kategori, 'BUMN (PT Pegadaian)') as kategori, COALESCE(google_maps_url, 'https://www.google.com/maps/search/?api=1&query=' || lat || ',' || lng) as google_maps_url, created_at
            FROM pegadaian_cabang
            WHERE 1=1
            """
            params = []
            if wilayah and wilayah.strip() and wilayah.strip().lower() != "all":
                query += " AND LOWER(wilayah) LIKE LOWER(%s)"
                params.append(f"%{wilayah.strip()}%")
            if kategori and kategori.strip() and kategori.strip().lower() != "all":
                query += " AND LOWER(kategori) LIKE LOWER(%s)"
                params.append(f"%{kategori.strip()}%")

            query += " ORDER BY id ASC;"

            cur = conn.cursor(cursor_factory=RealDictCursor)  # pyrefly: ignore[no-matching-overload,bad-context-manager] # type: ignore
            try:
                cur.execute(query, params)
                results = cur.fetchall()
                for row in results:
                    if row.get("created_at"):
                        row["created_at"] = str(row["created_at"])
                return list(results)
            finally:
                cur.close()
        else:
            query = """
            SELECT id, nama, alamat, wilayah, lat, lng, density_zone, COALESCE(neighbor_count, 0) as neighbor_count, COALESCE(kategori, 'BUMN (PT Pegadaian)') as kategori, COALESCE(google_maps_url, 'https://www.google.com/maps/search/?api=1&query=' || lat || ',' || lng) as google_maps_url, created_at
            FROM pegadaian_cabang
            WHERE 1=1
            """
            params = []
            if wilayah and wilayah.strip() and wilayah.strip().lower() != "all":
                query += " AND LOWER(wilayah) LIKE LOWER(?)"
                params.append(f"%{wilayah.strip()}%")
            if kategori and kategori.strip() and kategori.strip().lower() != "all":
                query += " AND LOWER(kategori) LIKE LOWER(?)"
                params.append(f"%{kategori.strip()}%")

            query += " ORDER BY id ASC;"

            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


def update_density_zones(updates: List[Dict[str, Any]]) -> int:
    """
    Batch update density_zone and neighbor_count for branches by their ID.
    updates format: [{'id': 1, 'density_zone': 'Tinggi', 'neighbor_count': 6}, ...]
    """
    if not updates:
        return 0

    conn = get_db_connection()
    try:
        if not _USE_SQLITE:
            query = """
            UPDATE pegadaian_cabang AS p
            SET 
                density_zone = c.density_zone,
                neighbor_count = c.neighbor_count
            FROM (VALUES %s) AS c(id, density_zone, neighbor_count)
            WHERE p.id = c.id;
            """
            records = [(u["id"], u["density_zone"], u.get("neighbor_count", 0)) for u in updates]
            with conn:
                cur = conn.cursor()
                try:
                    execute_values(cur, query, records, template="(%s, %s, %s)")
                    conn.commit()
                    return cur.rowcount
                finally:
                    cur.close()
        else:
            query = "UPDATE pegadaian_cabang SET density_zone = ?, neighbor_count = ? WHERE id = ?;"
            records = [(u["density_zone"], u.get("neighbor_count", 0), u["id"]) for u in updates]
            with conn:
                conn.executemany(query, records)
                return len(records)
    finally:
        conn.close()


def get_spatial_stats() -> Dict[str, Any]:
    """
    Calculate summary statistics across all pawnshops:
    - Total pawnshops
    - Density distribution (Tinggi, Sedang, Rendah)
    - Kategori distribution (BUMN, Swasta Berizin, Mandiri/Lokal)
    - Regional distribution across all 10 Jabodetabek territories
    """
    conn = get_db_connection()
    try:
        if not _USE_SQLITE:
            cur = conn.cursor(cursor_factory=RealDictCursor)  # pyrefly: ignore[no-matching-overload,bad-context-manager] # type: ignore
            try:
                cur.execute("SELECT COUNT(*) as total FROM pegadaian_cabang;")
                total_row = cur.fetchone()
                total = total_row["total"] if total_row else 0

                cur.execute("""
                    SELECT COALESCE(density_zone, 'Unassigned') as zone, COUNT(*) as count
                    FROM pegadaian_cabang
                    GROUP BY density_zone
                    ORDER BY count DESC;
                """)
                density_counts = {r["zone"]: r["count"] for r in cur.fetchall()}

                cur.execute("""
                    SELECT COALESCE(kategori, 'BUMN (PT Pegadaian)') as kat, COUNT(*) as count
                    FROM pegadaian_cabang
                    GROUP BY kategori
                    ORDER BY count DESC;
                """)
                kategori_counts = {r["kat"]: r["count"] for r in cur.fetchall()}

                cur.execute("""
                    SELECT COALESCE(wilayah, 'Lainnya') as wilayah, COUNT(*) as count
                    FROM pegadaian_cabang
                    GROUP BY wilayah
                    ORDER BY count DESC;
                """)
                wilayah_counts = {r["wilayah"]: r["count"] for r in cur.fetchall()}

                return {
                    "total_branches": total,
                    "density_distribution": density_counts,
                    "kategori_distribution": kategori_counts,
                    "wilayah_distribution": wilayah_counts
                }
            finally:
                cur.close()
        else:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as total FROM pegadaian_cabang;")
            total_row = cur.fetchone()
            total = total_row["total"] if total_row else 0

            cur.execute("""
                SELECT COALESCE(density_zone, 'Unassigned') as zone, COUNT(*) as count
                FROM pegadaian_cabang
                GROUP BY density_zone
                ORDER BY count DESC;
            """)
            density_counts = {r["zone"]: r["count"] for r in cur.fetchall()}

            cur.execute("""
                SELECT COALESCE(kategori, 'BUMN (PT Pegadaian)') as kat, COUNT(*) as count
                FROM pegadaian_cabang
                GROUP BY kategori
                ORDER BY count DESC;
            """)
            kategori_counts = {r["kat"]: r["count"] for r in cur.fetchall()}

            cur.execute("""
                SELECT COALESCE(wilayah, 'Lainnya') as wilayah, COUNT(*) as count
                FROM pegadaian_cabang
                GROUP BY wilayah
                ORDER BY count DESC;
            """)
            wilayah_counts = {r["wilayah"]: r["count"] for r in cur.fetchall()}

            return {
                "total_branches": total,
                "density_distribution": density_counts,
                "kategori_distribution": kategori_counts,
                "wilayah_distribution": wilayah_counts
            }
    finally:
        conn.close()
