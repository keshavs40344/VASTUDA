"""
VASTUDA SaaS Core - Flask & Gunicorn Production Web Server
Integrated with Firebase Admin SDK, REST APIs, and static frontend routing.
"""

import os
import time
import threading
from flask import Flask, jsonify, request, send_from_directory
import requests
import firebase_admin
from firebase_admin import credentials, auth as fb_auth, firestore as fb_firestore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# Initialize Firebase Admin SDK if not already initialized
try:
    if not firebase_admin._apps:
        # Defaults to Application Default Credentials or Project ID
        firebase_admin.initialize_app(options={
            "projectId": "saas-34243"
        })
        print("[FIREBASE-ADMIN] Initialized successfully for project: saas-34243")
except Exception as e:
    print(f"[FIREBASE-ADMIN] Notice: {e}")

# Initialize Background Daemon
from core.daemons import BackgroundWorkerDaemon
worker_daemon = BackgroundWorkerDaemon()
daemon_thread = threading.Thread(target=worker_daemon.start_loop, daemon=True)
daemon_thread.start()

# --- REST API Endpoints ---

@app.route("/api/health", methods=["GET"])
def health_check():
    """Layer 1 & 2 Health Check Endpoint"""
    return jsonify({
        "status": "healthy",
        "engine": "Flask/Gunicorn",
        "service": "vastuda-saas-core",
        "timestamp": time.time(),
        "memory": worker_daemon.get_memory_usage(),
        "daemon_status": worker_daemon.is_running
    }), 200

@app.route("/api/stats", methods=["GET"])
def get_system_stats():
    """Live system telemetry and agent counts"""
    return jsonify(worker_daemon.get_stats()), 200

@app.route("/api/scrape", methods=["POST"])
def trigger_scrape_job():
    """Trigger an autonomous data scraping task via requests"""
    payload = request.get_json(silent=True) or {}
    target_url = payload.get("url", "https://news.ycombinator.com")
    result = worker_daemon.execute_scrape_job(target_url)
    return jsonify({"status": "success", "data": result}), 200

@app.route("/api/verify-token", methods=["POST"])
def verify_firebase_token():
    """Verify Firebase ID Token server-side via firebase-admin"""
    payload = request.get_json(silent=True) or {}
    id_token = payload.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400

    try:
        decoded_token = fb_auth.verify_id_token(id_token)
        uid = decoded_token["uid"]
        return jsonify({
            "status": "valid",
            "uid": uid,
            "email": decoded_token.get("email")
        }), 200
    except Exception as err:
        return jsonify({"status": "invalid", "error": str(err)}), 401

# --- Frontend Static Routes ---

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

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
    port = int(os.environ.get("PORT", 8088))
    app.run(host="0.0.0.0", port=port, debug=False)
