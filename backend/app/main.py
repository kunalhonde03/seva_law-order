"""SurakshaVani: Core FastAPI Application."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.db.session import engine, Base
from backend.app.api import health, webhooks, sim, cases, analytics, admin
from scripts.seed import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize tables and seed default state data
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_all()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Voice-First Golden-Hour Cyber-Fraud, Digital Extortion and Financial-Crime Intelligence Layer for Maharashtra Cyber",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers (both direct and /api prefixes)
app.include_router(health.router)
app.include_router(health.router, prefix="/api")
app.include_router(webhooks.router)
app.include_router(webhooks.router, prefix="/api")
app.include_router(sim.router)
app.include_router(sim.router, prefix="/api")
app.include_router(cases.router)
app.include_router(cases.router, prefix="/api")
app.include_router(analytics.router)
app.include_router(analytics.router, prefix="/api")
app.include_router(admin.router)
app.include_router(admin.router, prefix="/api")

# Static and Web UI serving
STATIC_DIRS = [
    Path(__file__).resolve().parent.parent.parent / "console",
    Path.cwd() / "console",
    Path("/var/task/console"),
]
STATIC_DIR = next((d for d in STATIC_DIRS if d.exists()), STATIC_DIRS[0])

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root_index():
    for d in STATIC_DIRS:
        index_file = d / "index.html"
        if index_file.exists():
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return {
        "app": settings.APP_NAME,
        "status": "OPERATIONAL",
        "docs": "/docs",
        "console": "/static/index.html"
    }
