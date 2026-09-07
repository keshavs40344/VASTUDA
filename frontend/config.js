// VASTUDA SaaS - Layer 1 Hardware, Compute & Cloud Ingress Architecture
// Multi-Cloud Redundancy & Automated Failover Configuration

const PRIMARY_BACKEND = "https://keshavs40344.pythonanywhere.com";
const SECONDARY_BACKEND = "https://web-production-2ac2a.up.railway.app";
const CLOUDFLARE_EDGE = "https://vastuda.keshavkumarthakur00007.workers.dev";

// Global Ingress Pointers
window.PRIMARY_BACKEND = PRIMARY_BACKEND;
window.SECONDARY_BACKEND = SECONDARY_BACKEND;
window.CLOUDFLARE_WORKER_URL = CLOUDFLARE_EDGE;
window.API_BASE_URL = PRIMARY_BACKEND;
window.SOVEREIGN_API_BASE = PRIMARY_BACKEND;

// Google Firebase Cloud Configuration (Project: saas-34243)
window.FIREBASE_CONFIG = {
  apiKey: "AIzaSyDpSwbMUHP1L7hSK_o-3Kg4uW8pKaZfyR4",
  authDomain: "saas-34243.firebaseapp.com",
  projectId: "saas-34243",
  storageBucket: "saas-34243.firebasestorage.app",
  messagingSenderId: "964647710435",
  appId: "1:964647710435:web:368c5e868e434ed61f9fd6",
  measurementId: "G-P8XJF24WHD"
};

/**
 * Intelligent Multi-Cloud Fetch Client
 * Automatically fails over between Primary (PythonAnywhere), Secondary (Railway),
 * and Anycast Edge (Cloudflare) if any single provider experiences downtime.
 */
async function vastudaFetch(endpoint, options = {}, timeoutMs = 3500) {
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const targets = [
    { url: `${PRIMARY_BACKEND}${path}`, name: "PythonAnywhere (Primary)" },
    { url: `${SECONDARY_BACKEND}${path}`, name: "Railway (Secondary)" },
    { url: `${CLOUDFLARE_EDGE}${path}`, name: "Cloudflare (Edge)" }
  ];

  let lastError = null;

  for (const target of targets) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      const res = await fetch(target.url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timer);

      if (res.ok || res.status < 500) {
        // Set active backend url to the responding node
        window.API_BASE_URL = target.url.replace(path, "");
        return res;
      }
      console.warn(`[FAILOVER] ${target.name} returned status ${res.status}. Falling over...`);
    } catch (err) {
      console.warn(`[FAILOVER] ${target.name} connection failed:`, err.message);
      lastError = err;
    }
  }

  throw lastError || new Error("All Layer 1 compute nodes unreachable.");
}

window.vastudaFetch = vastudaFetch;

/**
 * Health check & cross-node latency benchmark
 */
async function getClusterNodeHealth() {
  const testNode = async (url, name) => {
    const start = performance.now();
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(`${url}/api/status`, { signal: controller.signal });
      clearTimeout(timer);
      const latency = Math.round(performance.now() - start);
      return { name, url, status: res.ok ? "ONLINE" : "DEGRADED", latency: `${latency}ms` };
    } catch (e) {
      return { name, url, status: "OFFLINE", latency: "timeout" };
    }
  };

  const results = await Promise.all([
    testNode(PRIMARY_BACKEND, "Primary (PythonAnywhere WSGI)"),
    testNode(SECONDARY_BACKEND, "Secondary (Railway PaaS)"),
    testNode(CLOUDFLARE_EDGE, "Edge (Cloudflare Anycast)")
  ]);

  return results;
}

window.getClusterNodeHealth = getClusterNodeHealth;

// Automatic Connectivity Verification Hook
async function checkBackend() {
  try {
    const res = await vastudaFetch("/api/status");
    const data = await res.json();
    console.log("[VASTUDA-LAYER-1] Compute Mesh Connected:", data);
    return data;
  } catch (err) {
    console.error("[VASTUDA-LAYER-1] Connection Notice:", err);
    return null;
  }
}

window.checkBackend = checkBackend;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  checkBackend();
});

