import logging
import math
from typing import Dict, Any, List, Optional
import pandas as pd  # pyrefly: ignore [missing-import] # type: ignore
import psycopg2  # pyrefly: ignore [missing-import] # type: ignore
from psycopg2.extras import RealDictCursor  # pyrefly: ignore [missing-import] # type: ignore

from src.database import get_all_cabang, update_density_zones, get_db_connection, _USE_SQLITE

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points in kilometers
    using the Haversine formula.
    
    Formula:
      a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
      c = 2 * atan2(√a, √(1−a))
      d = R * c
    """
    R = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def calculate_density_zone(neighbor_count: int) -> str:
    """
    Assign density zone label based on neighbor count within 1 km radius:
      - 'Tinggi' (High density): >= 5 neighboring pawnshops within 1 km.
      - 'Sedang' (Medium density): 2 to 4 neighboring pawnshops within 1 km.
      - 'Rendah' (Low density): < 2 neighboring pawnshops within 1 km.
    """
    if neighbor_count >= 5:
        return "Tinggi"
    elif 2 <= neighbor_count <= 4:
        return "Sedang"
    else:
        return "Rendah"


def try_postgis_dwithin_analysis(radius_meters: float = 1000.0) -> Optional[List[Dict[str, Any]]]:
    """
    Attempts proximity analysis using native PostGIS ST_DWithin spatial geography query.
    Returns list of {'id': int, 'neighbor_count': int} or None if PostGIS is unavailable.
    """
    if _USE_SQLITE:
        return None

    query = f"""
    SELECT 
        p1.id,
        p1.nama,
        p1.kategori,
        COUNT(p2.id) AS neighbor_count
    FROM pegadaian_cabang p1
    LEFT JOIN pegadaian_cabang p2 
        ON p1.id != p2.id 
        AND p2.lat IS NOT NULL 
        AND p2.lng IS NOT NULL
        AND ST_DWithin(
            ST_SetSRID(ST_MakePoint(p1.lng, p1.lat), 4326)::geography,
            ST_SetSRID(ST_MakePoint(p2.lng, p2.lat), 4326)::geography,
            {radius_meters}
        )
    WHERE p1.lat IS NOT NULL AND p1.lng IS NOT NULL
    GROUP BY p1.id, p1.nama, p1.kategori;
    """
    try:
        conn = get_db_connection()
        with conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)  # pyrefly: ignore[no-matching-overload,bad-context-manager] # type: ignore
            try:
                cur.execute(query)
                results = cur.fetchall()
                logger.info("Successfully executed PostGIS ST_DWithin 1 km proximity query.")
                return [dict(r) for r in results]
            finally:
                cur.close()
    except Exception as e:
        logger.info(f"PostGIS ST_DWithin query not available or error ({e}). Using Haversine formula engine.")
        return None


def run_spatial_clustering(radius_km: float = 1.0) -> Dict[str, Any]:
    """
    Spatial analysis engine for ALL types of pawnshops across Jabodetabek:
    Calculates exact neighboring pawnshops within a 1 km radius for every single location point,
    utilizing PostGIS ST_DWithin (when available) with Python Haversine fallback.
    
    Assigns:
      - 'Tinggi': >= 5 neighbors within 1 km
      - 'Sedang': 2 to 4 neighbors within 1 km
      - 'Rendah': < 2 neighbors within 1 km
      
    Updates the density_zone column in the database accordingly.
    """
    logger.info(f"Initiating 1 km radius spatial proximity analysis across all pawnshops (radius={radius_km} km)...")
    
    # 1. Check if native PostGIS ST_DWithin query can be used
    postgis_results = try_postgis_dwithin_analysis(radius_meters=radius_km * 1000.0)
    engine_used = "PostGIS ST_DWithin" if postgis_results else "Python Haversine"

    cabang_list = get_all_cabang()
    if not cabang_list:
        logger.warning("No pawnshop records found in database for proximity analysis.")
        return {"status": "no_data", "total_processed": 0}

    df = pd.DataFrame(cabang_list)
    valid_mask = df["lat"].notnull() & df["lng"].notnull()
    df_valid = df[valid_mask].copy()
    df_valid["lat"] = pd.to_numeric(df_valid["lat"], errors="coerce")
    df_valid["lng"] = pd.to_numeric(df_valid["lng"], errors="coerce")
    df_valid = df_valid.dropna(subset=["lat", "lng"]).copy()

    total_pawnshops = len(df_valid)
    if total_pawnshops == 0:
        return {"status": "no_valid_coordinates", "total_processed": 0}

    if postgis_results:
        # Map PostGIS counts
        postgis_map = {r["id"]: r["neighbor_count"] for r in postgis_results}
        df_valid["neighbor_count_1km"] = df_valid["id"].map(postgis_map).fillna(0).astype(int)
    else:
        # Compute pairwise distances using Haversine formula
        lats = df_valid["lat"].to_numpy()
        lngs = df_valid["lng"].to_numpy()
        neighbor_counts = []

        for i in range(total_pawnshops):
            current_lat = lats[i]
            current_lng = lngs[i]
            count = 0
            for j in range(total_pawnshops):
                if i == j:
                    continue
                dist = haversine_distance(current_lat, current_lng, lats[j], lngs[j])
                if dist <= radius_km:
                    count += 1
            neighbor_counts.append(count)

        df_valid["neighbor_count_1km"] = neighbor_counts

    # Assign density zones
    df_valid["density_zone"] = df_valid["neighbor_count_1km"].apply(calculate_density_zone)

    # Update database records
    updates: List[Dict[str, Any]] = [
        {"id": int(row["id"]), "density_zone": str(row["density_zone"]), "neighbor_count": int(row["neighbor_count_1km"])}
        for _, row in df_valid.iterrows()
    ]
    updated_count = update_density_zones(updates)
    distribution = df_valid["density_zone"].value_counts().to_dict()

    for zone in ["Tinggi", "Sedang", "Rendah"]:
        if zone not in distribution:
            distribution[zone] = 0

    logger.info(f"Analysis complete ({engine_used}). Distribution: {distribution}")

    # Build response summary
    pawnshop_summary = []
    for _, row in df_valid.iterrows():
        pawnshop_summary.append({
            "id": int(row["id"]),
            "nama": str(row["nama"]),
            "kategori": str(row.get("kategori", "BUMN (PT Pegadaian)")),
            "wilayah": str(row.get("wilayah", "")),
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "google_maps_url": str(row.get("google_maps_url", f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lng']}")),
            "neighbor_count_1km": int(row["neighbor_count_1km"]),
            "density_zone": str(row["density_zone"])
        })

    return {
        "status": "success",
        "engine_used": engine_used,
        "radius_km": radius_km,
        "total_processed": total_pawnshops,
        "database_records_updated": updated_count,
        "density_distribution": distribution,
        "criteria": {
            "Tinggi": ">= 5 neighboring pawnshops within 1 km",
            "Sedang": "2 to 4 neighboring pawnshops within 1 km",
            "Rendah": "< 2 neighboring pawnshops within 1 km"
        },
        "sample": pawnshop_summary[:12]
    }


if __name__ == "__main__":
    result = run_spatial_clustering()
    print("Spatial 1km Analysis Output:", result)
