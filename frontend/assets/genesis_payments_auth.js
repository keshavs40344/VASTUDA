/**

 * GENESIS SOVEREIGN CORE v8.0

 * Architecture:

 * 1. WebCrypto SHA-256 Client-Side Private Workspace Authentication & Session Vault

 * 2. Global Open-Source R&D Grant & Fellowship Backing (Zero Begging, 100% Free Public Good)

 *    - Allows patrons anywhere in the world to sponsor R&D / computational infrastructure

 *    - Real-time custom amount calculation (Dynamic UPI for India + Global Wire / Crypto for International)

 *    - Clean, dignified, institutional UI matching Stripe, GitHub Sponsors, or Linux Foundation

 * 3. 100% Client-Side In-Browser Execution. All utilities remain 100% free and open.

 */



(function(window) {

    'use strict';



    const CONFIG = {

        githubUrl: "https://github.com/keshavs40344/ai-world-core",

        sponsorsUrl: "https://github.com/sponsors/keshavs40344"

    };



    // ==========================================

    // 1. WEBCRYPTO SHA-256 HASHING

    // ==========================================

    async function sha256(str) {

        try {

            const buf = new TextEncoder().encode(str + "_genesis_sovereign_salt_2026");

            const hashBuf = await crypto.subtle.digest("SHA-256", buf);

            const hashArr = Array.from(new Uint8Array(hashBuf));

            return hashArr.map(b => b.toString(16).padStart(2, '0')).join('');

        } catch(e) {

            let hash = 0;

            for (let i = 0; i < str.length; i++) {

                hash = ((hash << 5) - hash) + str.charCodeAt(i);

                hash |= 0;

            }

            return "h_" + Math.abs(hash).toString(16);

        }

    }



    // ==========================================

    // 2. SOVEREIGN AUTH ENGINE (Local Vault)

    // ==========================================

    const GenesisAuth = {

        getUserVault: function() {

            try {

                const vault = localStorage.getItem("genesis_users_vault");

                return vault ? JSON.parse(vault) : {};

            } catch(e) {

                return {};

            }

        },



        getCurrentUser: function() {

            try {

                const user = localStorage.getItem("genesis_current_user");

                return user ? JSON.parse(user) : null;

            } catch(e) {

                return null;

            }

        },



        isLoggedIn: function() {

            return this.getCurrentUser() !== null;

        },



        hasProAccess: function() {

            // All tools are completely free public goods

            return true;

        },



        register: async function(email, password, displayName) {

            const cleanEmail = email ? email.trim().toLowerCase() : "";

            if (!cleanEmail || !cleanEmail.includes("@")) {

                return { success: false, msg: "Valid email address is required." };

            }

            if (!password || password.length < 4) {

                return { success: false, msg: "Password must be at least 4 characters long." };

            }



            const vault = this.getUserVault();

            if (vault[cleanEmail]) {

                return { success: false, msg: "An account with this email already exists. Please Sign In." };

            }



            const passHash = await sha256(password);

            const name = displayName && displayName.trim() ? displayName.trim() : cleanEmail.split("@")[0];



            const newUser = {

                email: cleanEmail,

                displayName: name,

                passHash: passHash,

                avatar: name.charAt(0).toUpperCase(),

                createdAt: new Date().toISOString()

            };



            vault[cleanEmail] = newUser;

            localStorage.setItem("genesis_users_vault", JSON.stringify(vault));



            const sessionUser = {

                email: newUser.email,

                displayName: newUser.displayName,

                avatar: newUser.avatar,

                token: "gnx_" + Math.random().toString(36).substr(2, 12),

                loginAt: new Date().toISOString()

            };

            localStorage.setItem("genesis_current_user", JSON.stringify(sessionUser));

            this.updateNavbarAuth();

            return { success: true, user: sessionUser };

        },



        login: async function(email, password) {

            const cleanEmail = email ? email.trim().toLowerCase() : "";

            if (!cleanEmail || !password) {

                return { success: false, msg: "Email and password are required." };

            }



            const vault = this.getUserVault();

            const user = vault[cleanEmail];

            const passHash = await sha256(password);



            if (!user) {

                return this.register(cleanEmail, password);

            }



            if (user.passHash !== passHash) {

                return { success: false, msg: "Incorrect password. Please try again." };

            }



            const sessionUser = {

                email: user.email,

                displayName: user.displayName,

                avatar: user.avatar,

                token: "gnx_" + Math.random().toString(36).substr(2, 12),

                loginAt: new Date().toISOString()

            };

            localStorage.setItem("genesis_current_user", JSON.stringify(sessionUser));

            this.updateNavbarAuth();

            return { success: true, user: sessionUser };

        },



        loginAsGuest: function() {

            const guestId = Math.floor(1000 + Math.random() * 9000);

            const guestUser = {

                email: `guest_${guestId}@genesis.world`,

                displayName: `Guest #${guestId}`,

                avatar: "G",

                token: "gnx_guest_" + guestId,

                loginAt: new Date().toISOString(),

                isGuest: true

            };

            localStorage.setItem("genesis_current_user", JSON.stringify(guestUser));

            this.updateNavbarAuth();

            return { success: true, user: guestUser };

        },



        logout: function() {

            localStorage.removeItem("genesis_current_user");

            this.updateNavbarAuth();

            window.location.reload();

        },



        updateNavbarAuth: function() {
            const authContainer = document.getElementById("genesisAuthWidget");
            if (!authContainer) return;

            const user = this.getCurrentUser();
            if (user) {
                authContainer.innerHTML = `
                    <div class="flex items-center gap-2">
                        <a href="user_dashboard.html" title="Open User Portal" class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-emerald-500/40 text-xs font-mono transition group">
                            <span class="w-5 h-5 rounded-full bg-emerald-500 text-slate-950 font-black flex items-center justify-center text-[10px]">
                                ${user.avatar || 'Ω'}
                            </span>
                            <span class="text-white font-bold hidden sm:inline max-w-[120px] truncate">${user.displayName || user.email.split('@')[0]}</span>
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        </a>
                        <button onclick="GenesisAuth.logout()" title="Logout" class="px-2 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-rose-500/40 text-slate-400 hover:text-rose-400 text-xs transition">✕</button>
                        <button onclick="GenesisDonation.open()" class="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-300 hover:text-white px-3 py-1.5 rounded-xl border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 transition font-mono">
                            <span>⚡</span>
                            <span>Back R&amp;D</span>
                        </button>
                    </div>
                `;
            } else {
                authContainer.innerHTML = `
                    <div class="flex items-center gap-2">
                        <button onclick="GenesisAuth.openModal('login')" class="text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-xl hover:bg-slate-800/80 transition font-sans inline-flex items-center">Log In</button>
                        <button onclick="GenesisAuth.openModal('register')" class="text-xs font-bold text-slate-950 hover:text-black px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-400 hover:from-emerald-300 hover:to-teal-300 shadow-md shadow-emerald-500/20 transition font-sans inline-flex items-center gap-1.5 group">
                            <span>Sign Up Free</span>
                            <span class="group-hover:translate-x-0.5 transition-transform text-[11px]">→</span>
                        </button>
                        <button onclick="GenesisDonation.open()" class="hidden md:inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-300 hover:text-white px-3 py-1.5 rounded-xl border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 transition font-mono">
                            <span>⚡</span>
                            <span>Back R&amp;D</span>
                        </button>
                    </div>
                `;
            }
        },



        openModal: function(mode = 'login') {

            let modal = document.getElementById("genesisAuthModal");

            if (!modal) {

                this._injectAuthModal();

                modal = document.getElementById("genesisAuthModal");

            }

            this.switchModalTab(mode);

            modal.classList.remove("hidden");

        },



        closeModal: function() {

            const modal = document.getElementById("genesisAuthModal");

            if (modal) modal.classList.add("hidden");

        },



        switchModalTab: function(mode) {
            const isLogin = mode === 'login';
            const tabLogin = document.getElementById("authTabLogin");
            const tabRegister = document.getElementById("authTabRegister");
            const nameField = document.getElementById("authNameContainer");
            const confirmField = document.getElementById("authConfirmPassContainer");
            const submitBtn = document.getElementById("authSubmitBtn");
            const modalTitle = document.getElementById("authModalTitle");
            const modalSubtitle = document.getElementById("authModalSubtitle");
            const togglePrompt = document.getElementById("authTogglePrompt");
            const errBox = document.getElementById("authModalError");

            if (!tabLogin) return;
            if (errBox) { errBox.classList.add("hidden"); errBox.innerText = ""; }

            if (isLogin) {
                tabLogin.className = "flex-1 py-2 text-xs font-bold text-white border-b-2 border-emerald-500 transition";
                tabRegister.className = "flex-1 py-2 text-xs font-medium text-slate-400 hover:text-white transition";
                if (nameField) nameField.classList.add("hidden");
                if (confirmField) confirmField.classList.add("hidden");
                if (submitBtn) submitBtn.innerText = "Sign In to Workspace";
                if (modalTitle) modalTitle.innerText = "Welcome Back";
                if (modalSubtitle) modalSubtitle.innerText = "Cloud-Verified Sovereign Authentication (Firebase & Firestore)";
                if (togglePrompt) togglePrompt.innerHTML = `Don't have an account? <button onclick="GenesisAuth.switchModalTab('register')" class="text-emerald-400 hover:underline font-bold">Create one free</button>`;
                document.getElementById("authForm").setAttribute("data-mode", "login");
            } else {
                tabLogin.className = "flex-1 py-2 text-xs font-medium text-slate-400 hover:text-white transition";
                tabRegister.className = "flex-1 py-2 text-xs font-bold text-white border-b-2 border-emerald-500 transition";
                if (nameField) nameField.classList.remove("hidden");
                if (confirmField) confirmField.classList.remove("hidden");
                if (submitBtn) submitBtn.innerText = "Create Cloud-Verified Account";
                if (modalTitle) modalTitle.innerText = "Create Cloud Account";
                if (modalSubtitle) modalSubtitle.innerText = "Direct Firebase Cloud Auth with Firestore telemetry sync";
                if (togglePrompt) togglePrompt.innerHTML = `Already have an account? <button onclick="GenesisAuth.switchModalTab('login')" class="text-emerald-400 hover:underline font-bold">Sign In</button>`;
                document.getElementById("authForm").setAttribute("data-mode", "register");
            }
        },



        _injectAuthModal: function() {

            const div = document.createElement("div");

            div.id = "genesisAuthModal";

            div.className = "fixed inset-0 bg-black/85 backdrop-blur-md z-50 hidden flex items-center justify-center p-4 font-sans antialiased";

            div.innerHTML = `

                <div class="bg-slate-900 border border-slate-800 max-w-md w-full rounded-3xl p-6 sm:p-7 shadow-2xl relative text-slate-100">

                    <button onclick="GenesisAuth.closeModal()" class="absolute top-5 right-5 text-slate-400 hover:text-white text-base font-bold">✕</button>

                    

                    <div class="text-center pb-2">

                        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-500 flex items-center justify-center text-xl font-black text-slate-950 mx-auto mb-3 shadow-lg shadow-emerald-500/25">

                            Ω

                        </div>

                        <h3 id="authModalTitle" class="text-xl font-extrabold text-white">Welcome Back</h3>

                        <p id="authModalSubtitle" class="text-xs text-slate-400 mt-1">Cloud-Verified Sovereign Authentication (Firebase &amp; Firestore)</p>

                    </div>



                    <!-- Mode Selector Tabs -->

                    <div class="flex border-b border-slate-800 my-4 text-center">

                        <button id="authTabLogin" onclick="GenesisAuth.switchModalTab('login')" class="flex-1 py-2 text-xs font-bold text-white border-b-2 border-emerald-500 transition">Sign In</button>

                        <button id="authTabRegister" onclick="GenesisAuth.switchModalTab('register')" class="flex-1 py-2 text-xs font-medium text-slate-400 hover:text-white transition">Register Free</button>

                    </div>



                    <!-- OAuth Providers (GitHub & Google via Firebase) -->

                    <div class="space-y-2.5 mb-4">

                        <!-- Sign in with GitHub -->

                        <button id="btnGitHubSignInModal" type="button" onclick="window.handleFirebaseGitHubSignIn()" class="w-full py-2.5 px-4 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-slate-500 text-white text-xs font-mono font-bold flex items-center justify-center gap-2.5 transition shadow-sm group">

                            <svg class="w-4 h-4 fill-white group-hover:scale-105 transition-transform" viewBox="0 0 24 24">

                                <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>

                            </svg>

                            <span>Sign in with GitHub</span>

                        </button>



                        <!-- Sign in with Google -->

                        <button id="btnGoogleSignInModal" type="button" onclick="window.handleFirebaseGoogleSignIn()" class="w-full py-2.5 px-4 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-slate-500 text-white text-xs font-mono font-bold flex items-center justify-center gap-2.5 transition shadow-sm">

                            <svg class="w-4 h-4" viewBox="0 0 24 24">

                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>

                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>

                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>

                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>

                            </svg>

                            <span>Sign in with Google</span>

                        </button>

                    </div>



                    <div class="relative my-3 text-center">

                        <div class="absolute inset-0 flex items-center"><div class="w-full border-t border-slate-800"></div></div>

                        <span class="relative px-3 bg-slate-900 text-[10px] font-mono text-slate-500">OR WITH EMAIL</span>

                    </div>



                    <!-- Error Alert Banner -->
                    <div id="authModalError" class="hidden mb-3 p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-mono"></div>

                    <!-- Interactive Form -->
                    <form id="authForm" data-mode="login" onsubmit="event.preventDefault(); window.handleSovereignAuth();" class="space-y-3.5">
                        <div id="authNameContainer" class="hidden">
                            <label class="text-[11px] font-mono text-slate-400 uppercase">Your Name</label>
                            <input id="authNameInput" type="text" placeholder="e.g. Keshav Sharma" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white mt-1 focus:outline-none focus:border-emerald-500 font-mono">
                        </div>

                        <div>
                            <label class="text-[11px] font-mono text-slate-400 uppercase">Email Address</label>
                            <input id="authEmailInput" type="email" required placeholder="you@domain.com" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white mt-1 focus:outline-none focus:border-emerald-500 font-mono">
                        </div>

                        <div>
                            <label class="text-[11px] font-mono text-slate-400 uppercase">Password</label>
                            <input id="authPassInput" type="password" required placeholder="••••••••••••" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white mt-1 focus:outline-none focus:border-emerald-500 font-mono">
                        </div>

                        <div id="authConfirmPassContainer" class="hidden">
                            <label class="text-[11px] font-mono text-slate-400 uppercase">Confirm Password</label>
                            <input id="authConfirmPassInput" type="password" placeholder="Repeat your password" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white mt-1 focus:outline-none focus:border-emerald-500 font-mono">
                        </div>

                        <button id="authSubmitBtn" type="submit" class="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-extrabold text-xs py-3.5 rounded-xl transition shadow-lg shadow-emerald-500/25 mt-2 flex items-center justify-center gap-2">
                            <span>Sign In to Workspace</span>
                        </button>
                    </form>



                    <div class="relative my-4 text-center">

                        <div class="absolute inset-0 flex items-center"><div class="w-full border-t border-slate-800"></div></div>

                        <span class="relative px-3 bg-slate-900 text-[11px] font-mono text-slate-500">OR</span>

                    </div>



                    <button onclick="GenesisAuth.loginAsGuest(); GenesisAuth.closeModal();" class="w-full py-2.5 rounded-xl border border-slate-800 hover:bg-slate-800/60 text-slate-300 text-xs font-mono transition">

                        ⚡ Continue as Instant Guest

                    </button>



                    <p id="authTogglePrompt" class="text-xs text-center text-slate-400 mt-4">

                        Don't have an account? <button onclick="GenesisAuth.switchModalTab('register')" class="text-emerald-400 hover:underline font-bold">Create one free</button>

                    </p>



                    <p class="text-[10px] text-slate-500 text-center mt-3 font-mono">
                        ☁️ Firebase Cloud Auth &amp; Firestore Telemetry Sync • Sovereign Client Encryption
                    </p>

                </div>

            `;

            document.body.appendChild(div);

        }

    };



            window.handleFirebaseGitHubSignIn = async function() {

        if (window.GenesisFirebase) {

            const res = await window.GenesisFirebase.signInWithGitHub();

            if (res.success) {

                if (window.GenesisAuth) window.GenesisAuth.closeModal();

                alert(`Welcome @${res.user.displayName}! Successfully authenticated with GitHub via Firebase.`);

                if (window.location.pathname.endsWith("login.html")) {

                    window.location.href = "dashboard.html";

                }

            } else if (res.msg) {

                alert(res.msg);

            }

        } else {

            alert("Firebase client bridge loading... Please try again.");

        }

    };



    window.handleFirebaseGoogleSignIn = async function() {

        if (window.GenesisFirebase) {

            const res = await window.GenesisFirebase.signInWithGoogle();

            if (res.success) {

                if (window.GenesisAuth) window.GenesisAuth.closeModal();

                alert(`Welcome ${res.user.displayName}! Signed in securely with Google Firebase.`);

                if (window.location.pathname.endsWith("login.html")) {

                    window.location.href = "dashboard.html";

                }

            } else if (res.msg) {

                alert(res.msg);

            }

        } else {

            alert("Firebase client bridge loading... Please try again.");

        }

    };



    window.handleSovereignAuth = async function() {
        const form = document.getElementById("authForm");
        const mode = form ? form.getAttribute("data-mode") : "login";
        const emailEl = document.getElementById("authEmailInput");
        const passEl = document.getElementById("authPassInput");
        const nameEl = document.getElementById("authNameInput");
        const confirmEl = document.getElementById("authConfirmPassInput");
        const errBox = document.getElementById("authModalError");
        const submitBtn = document.getElementById("authSubmitBtn");

        const showError = (msg) => {
            if (errBox) {
                errBox.innerText = msg;
                errBox.classList.remove("hidden");
            } else {
                alert(msg);
            }
        };

        if (errBox) {
            errBox.classList.add("hidden");
            errBox.innerText = "";
        }

        const email = emailEl ? emailEl.value.trim() : "";
        const pass = passEl ? passEl.value : "";
        const name = nameEl ? nameEl.value.trim() : "";
        const confirmPass = confirmEl ? confirmEl.value : "";

        if (!email || !email.includes("@")) {
            showError("Please enter a valid email address.");
            if (emailEl) emailEl.focus();
            return;
        }

        if (!pass || pass.length < 6) {
            showError("Password must be at least 6 characters long.");
            if (passEl) passEl.focus();
            return;
        }

        const origBtnHtml = submitBtn ? submitBtn.innerHTML : "";
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span>Processing...</span>`;
        }

        try {
            if (mode === "register") {
                if (!name) {
                    showError("Please provide your full name.");
                    if (nameEl) nameEl.focus();
                    return;
                }
                if (confirmEl && pass !== confirmPass) {
                    showError("Passwords do not match. Please re-enter.");
                    if (confirmEl) confirmEl.focus();
                    return;
                }

                // 1. Try Firebase modular registration first (writes to Firestore)
                if (typeof window.handleModularEmailRegister === "function") {
                    const res = await window.handleModularEmailRegister(email, pass, name);
                    if (res && res.success) {
                        GenesisAuth.closeModal();
                        return;
                    } else if (res && res.msg && res.msg.includes("email-already-in-use")) {
                        showError("This email is already registered. Please sign in instead.");
                        return;
                    }
                }

                // 2. Sovereign Local Vault Fallback (100% offline private WebCrypto SHA-256)
                const res = await GenesisAuth.register(email, pass, name);
                if (res.success) {
                    GenesisAuth.closeModal();
                } else {
                    showError(res.msg || "Registration failed. Please try again.");
                }
            } else {
                // 1. Try Firebase modular login first
                if (typeof window.handleModularEmailSignIn === "function") {
                    const res = await window.handleModularEmailSignIn(email, pass);
                    if (res && res.success) {
                        GenesisAuth.closeModal();
                        return;
                    }
                }

                // 2. Sovereign Local Vault Fallback
                const res = await GenesisAuth.login(email, pass);
                if (res.success) {
                    GenesisAuth.closeModal();
                } else {
                    showError(res.msg || "Incorrect email or password.");
                }
            }
        } catch (e) {
            showError(e.message || "Authentication error occurred.");
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origBtnHtml;
            }
        }
    };



    // ==========================================

    // 3. GLOBAL R&D GRANT & FELLOWSHIP ENGINE

    //    (Enterprise Institutional Backing, Zero Begging)

    // ==========================================

        const GenesisDonation = {

        open: function() {

            let modal = document.getElementById("genesisDonationModal");

            if (!modal) {

                this._injectDonationModal();

                modal = document.getElementById("genesisDonationModal");

            }

            modal.classList.remove("hidden");

        },



        close: function() {

            const modal = document.getElementById("genesisDonationModal");

            if (modal) modal.classList.add("hidden");

        },



        _injectDonationModal: function() {

            const div = document.createElement("div");

            div.id = "genesisDonationModal";

            div.className = "fixed inset-0 bg-black/85 backdrop-blur-md z-50 hidden flex items-center justify-center p-4 font-sans antialiased";

            div.innerHTML = `

                <div class="bg-slate-900 border border-slate-800 max-w-lg w-full rounded-3xl p-6 sm:p-7 shadow-2xl relative text-slate-100 max-h-[94vh] overflow-y-auto">

                    <button onclick="GenesisDonation.close()" class="absolute top-5 right-5 text-slate-400 hover:text-white text-base font-bold">✕</button>

                    

                    <div class="text-center pb-2">

                        <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-pink-950/80 text-pink-300 border border-pink-800/80 mb-3">

                            <span>💖</span>

                            <span>OPEN-SOURCE SPONSORSHIP</span>

                        </div>

                        <h3 class="text-xl font-display font-extrabold text-white">Support Autonomous R&amp;D</h3>

                        <p class="text-xs text-slate-400 mt-1.5 leading-relaxed max-w-md mx-auto">

                            All 50+ developer utilities and SaaS studios are <strong class="text-white">100% free, private, and open for everyone</strong>. There are no fees or paywalls. If our work saves you time, you can voluntarily sponsor our open-source research through GitHub Sponsors.

                        </p>

                    </div>



                    <div class="my-6 p-4 bg-slate-950 border border-slate-800 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">

                        <div class="space-y-1 text-center sm:text-left">

                            <div class="text-sm font-mono font-bold text-white flex items-center justify-center sm:justify-start gap-2">

                                <svg class="w-4 h-4 fill-pink-500" viewBox="0 0 16 16"><path d="m8 14.25.345.666a.75.75 0 0 1-.69 0l-.008-.004-.018-.01a7.152 7.152 0 0 1-.31-.17 22.055 22.055 0 0 1-3.434-2.414C2.045 10.731 0 8.35 0 5.5 0 2.836 2.086 1 4.75 1a4.912 4.912 0 0 1 3.25 1.258A4.912 4.912 0 0 1 11.25 1C13.914 1 16 2.836 16 5.5c0 2.85-2.045 5.231-3.885 6.818a22.066 22.066 0 0 1-3.434 2.414 7.152 7.152 0 0 1-.31.17l-.018.01-.008.004Zm.006-1.503.018-.01.066-.037c.307-.173.856-.492 1.543-.967C11.17 10.63 14.5 7.97 14.5 5.5 14.5 3.69 13.06 2.5 11.25 2.5a3.42 3.42 0 0 0-2.457 1.054l-.793.812-.793-.812A3.42 3.42 0 0 0 4.75 2.5C2.94 2.5 1.5 3.69 1.5 5.5c0 2.47 3.33 5.13 4.867 6.233.687.475 1.236.794 1.543.967l.066.037.018.01.006.003Z"/></svg>

                                <span>GitHub Sponsors</span>

                            </div>

                            <p class="text-xs font-mono text-slate-400">Direct global sponsor for @keshavs40344</p>

                        </div>

                        <iframe src="https://github.com/sponsors/keshavs40344/button" title="Sponsor keshavs40344" height="32" width="114" style="border: 0; border-radius: 6px;"></iframe>

                    </div>



                    <a href="https://github.com/sponsors/keshavs40344" target="_blank" class="w-full py-3 rounded-xl border border-pink-500/40 hover:border-pink-500/80 bg-pink-500/15 hover:bg-pink-500/25 text-pink-300 font-mono text-xs font-bold block text-center transition flex items-center justify-center gap-2 shadow-lg shadow-pink-900/20">

                        <span>💖 Open GitHub Sponsors Profile</span>

                    </a>



                    <div class="mt-6 pt-4 border-t border-slate-800 text-center">

                        <p class="text-[11px] font-mono text-slate-500">

                            100% Free Public Software • Zero Compulsion • Pure Open-Source Research

                        </p>

                    </div>

                </div>

            `;

            document.body.appendChild(div);

        }

    };



    // Stubs for backwards compatibility

    const GenesisSupport = GenesisDonation;

    const GenesisCheckout = {

        open: function() { GenesisDonation.open(); },

        close: function() { GenesisDonation.close(); }

    };



    // Auto-mount on DOM ready

    window.addEventListener("DOMContentLoaded", () => {

        GenesisAuth.updateNavbarAuth();

    });



    window.GenesisAuth = GenesisAuth;

    window.GenesisDonation = GenesisDonation;

    window.GenesisSupport = GenesisSupport;

    window.GenesisCheckout = GenesisCheckout;



})(window);

