"""
FastAPI Admin Panel Main Application.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from admin_backend import auth, routes
from database import init_database

# Initialize FastAPI app
app = FastAPI(
    title="Lead Manager Admin Panel",
    description="Admin Web Interface for Lead Management System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="admin_backend/templates")
app.mount("/static", StaticFiles(directory="admin_backend/static"), name="static")

# Include routers
app.include_router(routes.auth_router, prefix="/admin", tags=["auth"])
app.include_router(routes.dashboard_router, prefix="/admin", tags=["dashboard"])
app.include_router(routes.agents_router, prefix="/admin", tags=["agents"])
app.include_router(routes.leads_router, prefix="/admin", tags=["leads"])
app.include_router(routes.kpi_router, prefix="/admin", tags=["kpi"])
app.include_router(routes.stats_router, prefix="/admin", tags=["stats"])
app.include_router(routes.logs_router, prefix="/admin", tags=["logs"])
app.include_router(routes.sync_router, prefix="/admin", tags=["sync"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_database()
    print("✅ Database initialized")
    print("✅ Admin Panel ready at http://localhost:8000")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to login."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/login")


@app.get("/admin", response_class=HTMLResponse)
async def admin_root(request: Request):
    """Redirect to login."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/login")


if __name__ == "__main__":
    uvicorn.run(
        "admin_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

