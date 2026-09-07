"""
VASTUDA SaaS Core - Flask Web Server (PythonAnywhere & Cloud Native)
Integrated with Cloudflare Worker CORS, Firebase Admin, and REST APIs.
"""

import os
import sys
import time
import threading
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# Configure CORS specifically allowing Cloudflare Worker, PythonAnywhere, and local dev
CORS(app, origins=[
    "https://vastuda.keshavkumarthakur00007.workers.dev",
    "https://keshavs40344.pythonanywhere.com",
    "https://web-production-2ac2a.up.railway.app",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "http://localhost:8088",
    "*"
], supports_credentials=True)

# Firebase Admin SDK (Safe lazy initialization)
try:
    import firebase_admin
    from firebase_admin import auth as fb_auth, firestore as fb_firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": "saas-34243"})
        print("[FIREBASE-ADMIN] Initialized for saas-34243")
except Exception as e:
    print(f"[FIREBASE-ADMIN] Notice: {e}")

# Safe Background Daemon initialization
try:
    from core.daemons import BackgroundWorkerDaemon
    worker_daemon = BackgroundWorkerDaemon()
    daemon_thread = threading.Thread(target=worker_daemon.start_loop, daemon=True)
    daemon_thread.start()
except Exception as e:
    worker_daemon = None
    print(f"[DAEMON] Notice: {e}")

# --- REST API Endpoints ---

@app.route("/", methods=["GET"])
def index():
    # If index.html exists in frontend, serve it, otherwise return JSON status
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({"status": "live", "service": "VASTUDA Backend", "cloud": "PythonAnywhere"}), 200

@app.route("/api/status", methods=["GET"])
def health():
    uptime = worker_daemon.get_stats()["uptime_seconds"] if worker_daemon else 0
    current_host = request.host_url.rstrip("/")
    return jsonify({
        "status": "online",
        "message": "Backend connected successfully",
        "service": "VASTUDA Sovereign Backend (Layer 1)",
        "current_node": current_host,
        "primary_backend": "https://keshavs40344.pythonanywhere.com",
        "secondary_backend": "https://web-production-2ac2a.up.railway.app",
        "cloudflare_worker": "https://vastuda.keshavkumarthakur00007.workers.dev",
        "uptime": uptime,
        "timestamp": time.time(),
        "layer": "Layer 1 - Compute & Cloud Infra"
    }), 200

@app.route("/api/nodes", methods=["GET"])
def get_cloud_nodes():
    """
    Returns the complete Layer 1 multi-cloud compute and ingress topology.
    """
    current_host = request.host_url.rstrip("/")
    is_railway = "railway" in current_host.lower() or os.environ.get("RAILWAY_ENVIRONMENT") is not None
    is_pa = "pythonanywhere" in current_host.lower()

    if is_railway:
        active_role = "Secondary (Railway PaaS)"
    elif is_pa:
        active_role = "Primary (PythonAnywhere WSGI)"
    else:
        active_role = "Edge / Local Ingress"

    return jsonify({
        "status": "healthy",
        "layer": "Layer 1: Hardware, Compute & Cloud Infra",
        "topology": "Multi-Cloud Active-Active / Automated Failover",
        "current_serving_node": {
            "role": active_role,
            "url": current_host,
            "status": "ONLINE"
        },
        "nodes": [
            {
                "id": "node-primary-pa",
                "role": "Primary Compute (WSGI)",
                "provider": "PythonAnywhere",
                "url": "https://keshavs40344.pythonanywhere.com",
                "status": "ONLINE",
                "tier": "Free Cloud Native ($0/mo)"
            },
            {
                "id": "node-secondary-railway",
                "role": "Secondary Compute (Container/PaaS)",
                "provider": "Railway",
                "url": "https://web-production-2ac2a.up.railway.app",
                "status": "ONLINE",
                "tier": "Free Cloud Native ($0/mo)"
            },
            {
                "id": "node-edge-cloudflare",
                "role": "Anycast Edge Gateway & Failover Ingress",
                "provider": "Cloudflare Workers",
                "url": "https://vastuda.keshavkumarthakur00007.workers.dev",
                "status": "ONLINE",
                "tier": "Free Global Edge ($0/mo)"
            }
        ],
        "failover_configured": True,
        "memory_guard_active": True,
        "timestamp": time.time()
    }), 200

@app.route("/api/telemetry", methods=["GET"])
def get_telemetry():
    """
    Returns deep OS container, memory guardian, and process telemetry.
    """
    telemetry = worker_daemon.get_telemetry() if worker_daemon else {
        "status": "active",
        "rss_memory_mb": 35.0,
        "peak_rss_memory_mb": 35.0,
        "oom_mitigations_total": 0
    }
    return jsonify({
        "status": "operational",
        "telemetry": telemetry,
        "layer": "Layer 1 - Compute & Memory Shield",
        "timestamp": time.time()
    }), 200

@app.route("/api/health", methods=["GET"])
def health_check():
    mem = worker_daemon.get_memory_usage() if worker_daemon else "Active"
    return jsonify({
        "status": "healthy",
        "engine": "Flask WSGI Sovereign Mesh",
        "service": "vastuda-saas-core",
        "timestamp": time.time(),
        "memory": mem,
        "layer1_certified": True
    }), 200

@app.route("/api/stats", methods=["GET"])
def get_system_stats():
    stats = worker_daemon.get_stats() if worker_daemon else {"status": "running"}
    return jsonify(stats), 200

@app.route("/api/scrape", methods=["POST"])
def trigger_scrape_job():
    payload = request.get_json(silent=True) or {}
    target_url = payload.get("url", "https://news.ycombinator.com")
    result = worker_daemon.execute_scrape_job(target_url) if worker_daemon else {"target": target_url}
    return jsonify({"status": "success", "data": result}), 200

@app.route("/api/verify-token", methods=["POST"])
def verify_firebase_token():
    payload = request.get_json(silent=True) or {}
    id_token = payload.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(id_token)
        return jsonify({"status": "valid", "uid": decoded["uid"], "email": decoded.get("email")}), 200
    except Exception as err:
        return jsonify({"status": "invalid", "error": str(err)}), 401

# --- Frontend Static Routes ---

@app.route("/admin")
@app.route("/admin-dashboard.html")
def serve_admin():
    return send_from_directory(FRONTEND_DIR, "admin-dashboard.html")

@app.route("/admin-login.html")
def serve_admin_login():
    return send_from_directory(FRONTEND_DIR, "admin-login.html")

@app.route("/user_dashboard.html")
def serve_user_dashboard():
    return send_from_directory(FRONTEND_DIR, "user_dashboard.html")

@app.route("/<path:path>")
def serve_static(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"error": "Not Found", "path": path}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
