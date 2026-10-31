"""Integration tests for FastAPI REST Endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.db.session import engine, Base
from scripts.seed import seed_all

_DB_INITIALIZED = False


async def ensure_db_initialized():
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_all()
        _DB_INITIALIZED = True


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints():
    await ensure_db_initialized()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["app"] == "SurakshaVani"

        ready_res = await ac.get("/ready")
        assert ready_res.status_code == 200
        assert ready_res.json()["database"] == "CONNECTED"


@pytest.mark.asyncio
async def test_cases_listing_and_pdf_generation():
    await ensure_db_initialized()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # List cases
        res = await ac.get("/cases")
        assert res.status_code == 200
        cases = res.json()
        assert len(cases) > 0
        first_case_id = cases[0]["id"]

        # Detail view
        detail_res = await ac.get(f"/cases/{first_case_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert "ref_no" in detail
        assert "details" in detail

        # Summary PDF generation
        pdf_res = await ac.get(f"/cases/{first_case_id}/summary.pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 1000


@pytest.mark.asyncio
async def test_analytics_and_threat_clusters():
    await ensure_db_initialized()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        cl_res = await ac.get("/analytics/clusters")
        assert cl_res.status_code == 200
        assert cl_res.json()["status"] == "SUCCESS"

        rep_res = await ac.get("/analytics/report")
        assert rep_res.status_code == 200
        assert "jurisdiction" in rep_res.json()
