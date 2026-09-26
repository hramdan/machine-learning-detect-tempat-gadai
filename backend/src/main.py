import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query  # pyrefly: ignore[missing-import] # pyrefly: ignore
from fastapi.responses import RedirectResponse  # pyrefly: ignore[missing-import] # pyrefly: ignore
from fastapi.middleware.cors import CORSMiddleware  # pyrefly: ignore[missing-import] # pyrefly: ignore
from contextlib import asynccontextmanager

from src.database import init_db, get_all_cabang, get_spatial_stats
from src.scraper.pegadaian_scraper import PegadaianScraper
from src.ml.clustering import run_spatial_clustering

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pegadaian_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database initialization and warmup."""
    logger.info("Starting up Pegadaian Spatial API Server...")
    try:
        init_db()
        logger.info("Database schema verification and initialization complete.")
    except Exception as e:
        logger.error(f"Database initialization warning on startup: {e}")
    yield
    logger.info("Shutting down Pegadaian Spatial API Server...")


app = FastAPI(
    title="Pegadaian Spatial Intelligence API",
    description="Spatial Analytics, Scraper Automation, and Density Clustering API for Pegadaian Jabodetabek branch networks.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware allowing all origins for full-stack integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Redirect root to Swagger API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/api/health")
def health_check():
    """Service health verification endpoint."""
    return {"status": "healthy", "service": "pegadaian-spatial-backend", "version": "1.0.0"}


@app.api_route("/api/trigger-scraping", methods=["GET", "POST"])
def trigger_scraping():
    """
    Executes the Pegadaian automated scraping and spatial geocoding pipeline.
    Harvests branch locations, resolves GPS coordinates, upserts records to database,
    and runs ML K-Means density clustering.
    Supports both GET (browser navigation) and POST (AJAX / programmatic trigger).
    """
    try:
        logger.info("Triggering scraping pipeline via API request...")
        scraper = PegadaianScraper()
        result = scraper.run_pipeline()
        
        # Query updated total count from database
        all_cabang = get_all_cabang()
        total_count = len(all_cabang)

        return {
            "status": "success",
            "message": "Automated scraping and spatial density clustering completed successfully.",
            "total_count": total_count,
            "pipeline_details": result
        }
    except Exception as e:
        logger.error(f"Error during scraping pipeline execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scraping pipeline failed: {str(e)}")


@app.get("/api/pegadaian")
def get_pegadaian_branches(
    wilayah: Optional[str] = Query(None, description="Optional region filter (e.g. 'Jakarta Selatan', 'Depok', 'Tangerang Selatan', 'all')"),
    kategori: Optional[str] = Query(None, description="Optional category filter (e.g. 'BUMN', 'Gadai Swasta Berizin', 'Gadai Mandiri', 'all')")
):
    """
    Fetch spatial records of pawnshops across Jabodetabek from database.
    Supports filtering by wilayah / regional boundary and/or kategori (BUMN, Swasta, Mandiri).
    """
    try:
        branches = get_all_cabang(wilayah=wilayah, kategori=kategori)
        return branches
    except Exception as e:
        logger.error(f"Error retrieving pawnshop records: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query pawnshop data: {str(e)}")


@app.api_route("/api/trigger-clustering", methods=["GET", "POST"])
def trigger_clustering():
    """
    Directly run K-Means & k-NN spatial density clustering without re-scraping.
    Supports both GET and POST requests.
    """
    try:
        result = run_spatial_clustering()
        return {
            "status": "success",
            "message": "Spatial clustering executed successfully.",
            "result": result
        }
    except Exception as e:
        logger.error(f"Clustering error: {e}")
        raise HTTPException(status_code=500, detail=f"Clustering execution failed: {str(e)}")


@app.get("/api/stats")
def get_stats():
    """
    Retrieve spatial intelligence KPIs (total branches, density zone breakdowns, regional distribution).
    """
    try:
        stats = get_spatial_stats()
        return stats
    except Exception as e:
        logger.error(f"Stats calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn  # pyrefly: ignore[missing-import] # pyrefly: ignore
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
