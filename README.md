# VASTUDA Autonomous SaaS Engine

Production-ready, multi-agent cloud platform engineered for 24/7 cloud execution.

## Architecture
`
VASTUDA/
├── frontend/               # index.html, admin-dashboard.html, admin-login.html, static assets
├── core/
│   ├── web_server.py       # FastAPI production app with REST endpoints & static routes
│   └── daemons.py          # Background worker / scraper / health daemon
├── requirements.txt        # FastAPI, Uvicorn, Pydantic, Requests
├── Procfile                # Render / PaaS start command
└── render.yaml             # Render deployment configuration
`

## Quick Start
1. Install dependencies:
   `ash
   pip install -r requirements.txt
   `
2. Start server:
   `ash
   uvicorn core.web_server:app --host 0.0.0.0 --port 8088
   `

## Cloud Deployment (Render / PaaS)
This repository is pre-configured with 
ender.yaml and Procfile.
Simply connect this repository to Render as a Web Service for 1-click 24/7 online deployment.
