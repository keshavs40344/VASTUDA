// VASTUDA SaaS - Cloud Ingress & PythonAnywhere Integration
const API_BASE_URL = "https://keshavs40344.pythonanywhere.com";
window.API_BASE_URL = API_BASE_URL;
window.SOVEREIGN_API_BASE = API_BASE_URL;
window.CLOUDFLARE_WORKER_URL = "https://vastuda.keshavkumarthakur00007.workers.dev";

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

// Automatic Connectivity Verification Hook
async function checkBackend() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/status`);
    const data = await res.json();
    console.log("Connected to Backend:", data);
    return data;
  } catch (err) {
    console.error("Backend fetch error:", err);
    return null;
  }
}

window.checkBackend = checkBackend;

// Run on page load
document.addEventListener("DOMContentLoaded", () => {
  checkBackend();
});
