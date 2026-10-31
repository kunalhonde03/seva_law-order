"""Analytics and Financial Crime Threat Intelligence Router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.intel.clustering import run_scam_clustering_pipeline
from backend.app.intel.reports import generate_weekly_leads_report

router = APIRouter(prefix="/analytics", tags=["Intelligence"])


@router.get("/clusters")
async def get_crime_clusters(db: AsyncSession = Depends(get_db)):
    """Surfaces active cyber crime syndicates and repeat identifier graphs."""
    clusters = await run_scam_clustering_pipeline(db)
    return {
        "status": "SUCCESS",
        "total_active_clusters": len(clusters),
        "clusters": clusters
    }


@router.get("/report")
async def get_weekly_leads(db: AsyncSession = Depends(get_db)):
    """Generates Weekly Police Leads Report for Maharashtra Cyber Cell and I4C."""
    report = await generate_weekly_leads_report(db)
    return report

