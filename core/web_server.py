"""
VASTUDA SaaS Core - FastAPI Production Web Server
Serves the frontend static assets and exposes REST APIs for cloud agents.
"""

import os
import time
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.daemons import BackgroundWorkerDaemon

app = FastAPI(
    title="VASTUDA Autonomous SaaS Engine",
    description="Production-grade API and Web Server with Background Daemons",
    version="2.0.0"
)

# Enable CORS for cross-origin clients and Cloudflare CDN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Initialize Background Daemon
worker_daemon = BackgroundWorkerDaemon()

@app.on_event("startup")
async def startup_event():
    # Start background scraper and telemetry loops
    asyncio.create_task(worker_daemon.start_loop())

@app.on_event("shutdown")
async def shutdown_event():
    worker_daemon.stop()

# --- REST API Endpoints ---

@app.get("/api/health")
async def health_check():
    """Layer 1 & 2 Health Check Endpoint"""
    return {
        "status": "healthy",
        "service": "vastuda-saas-core",
        "timestamp": time.time(),
        "memory": worker_daemon.get_memory_usage(),
        "daemon_status": worker_daemon.is_running
    }

@app.get("/api/stats")
async def get_system_stats():
    """Live system telemetry and agent counts"""
    return worker_daemon.get_stats()

@app.post("/api/scrape")
async def trigger_scrape_job(payload: Dict[str, Any]):
    """Trigger an autonomous data scraping task"""
    target_url = payload.get("url", "https://news.ycombinator.com")
    result = await worker_daemon.execute_scrape_job(target_url)
    return {"status": "success", "data": result}

# --- Frontend Static Routes ---

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>VASTUDA SaaS Engine Online</h1>")

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin-dashboard.html", response_class=HTMLResponse)
async def serve_admin():
    admin_path = os.path.join(FRONTEND_DIR, "admin-dashboard.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return HTMLResponse("<h1>Admin Dashboard</h1>")

@app.get("/admin-login.html", response_class=HTMLResponse)
async def serve_admin_login():
    login_path = os.path.join(FRONTEND_DIR, "admin-login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)
    return HTMLResponse("<h1>Admin Login</h1>")

# Mount any remaining frontend files if directory exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8088))
    uvicorn.run("core.web_server:app", host="0.0.0.0", port=port, reload=False)
