import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";

// Registered ADMIN-PORTAL Web App Configuration (Project: saas-34243)
const firebaseConfig = {
  apiKey: "AIzaSyDpSwbMUHP1L7hSK_o-3Kg4uW8pKaZfyR4",
  authDomain: "saas-34243.firebaseapp.com",
  projectId: "saas-34243",
  storageBucket: "saas-34243.firebasestorage.app",
  messagingSenderId: "964647710435",
  appId: "1:964647710435:web:c1159dc50b671a891f9fd6",
  measurementId: "G-LZK0Y6D017"
};

export const app = initializeApp(firebaseConfig, "adminPortalInstance");
export const auth = getAuth(app);
export const db = getFirestore(app);
