/**
 * GENESIS ENTERPRISE CLIENT RUNTIME v2.0
 * Zero-dependency, air-gapped operating primitives for Sovereign Micro-SaaS.
 */
(function(window) {
    'use strict';

    const Genesis = {
        version: "2.0.0",
        build: "2026-TITAN",

        // --- 1. LOCAL WORKSPACE STATE PERSISTENCE ---
        State: {
            save: function(key, data) {
                try {
                    localStorage.setItem(`genesis_${key}`, JSON.stringify(data));
                    return true;
                } catch(e) {
                    console.error("[Genesis.State] Write error:", e);
                    return false;
                }
            },
            load: function(key, fallback = null) {
                try {
                    const item = localStorage.getItem(`genesis_${key}`);
                    return item ? JSON.parse(item) : fallback;
                } catch(e) {
                    console.error("[Genesis.State] Read error:", e);
                    return fallback;
                }
            },
            clear: function(key) {
                localStorage.removeItem(`genesis_${key}`);
            }
        },

        // --- 2. ZERO-LEAK LOCAL TELEMETRY BUFFER ---
        Telemetry: {
            logEvent: function(action, metadata = {}) {
                const logs = Genesis.State.load("telemetry_stream", []);
                logs.push({
                    ts: new Date().toISOString(),
                    act: action,
                    meta: metadata,
                    url: window.location.pathname
                });
                if (logs.length > 50) logs.shift(); // retain rolling 50 items
                Genesis.State.save("telemetry_stream", logs);
            },
            getMetrics: function() {
                return Genesis.State.load("telemetry_stream", []);
            }
        },

        // --- 3. EXPORT AND PRINT ENGINES ---
        IO: {
            download: function(filename, content, mime = "text/plain") {
                const blob = new Blob([content], { type: mime });
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(a.href);
                Genesis.Telemetry.logEvent("file_export", { file: filename });
            },
            copy: function(text, btnElement) {
                navigator.clipboard.writeText(text).then(() => {
                    if (btnElement) {
                        const orig = btnElement.innerHTML;
                        btnElement.innerHTML = "✔ Copied";
                        setTimeout(() => { btnElement.innerHTML = orig; }, 1500);
                    }
                    Genesis.Telemetry.logEvent("clipboard_copy");
                });
            }
        },

        // --- 4. NPCI UNIVERSAL AMOUNT-LOCKED GATEWAY ---
        Payments: {
            invokeUPI: function() {
                if (window.GenesisDonation) window.GenesisDonation.open();
            }
        },

        // --- 5. INTER-AGENT SHARED BUS ---
        Bus: {
            emit: function(channel, data) {
                window.dispatchEvent(new CustomEvent(`genesis_event_${channel}`, { detail: data }));
            },
            on: function(channel, callback) {
                window.addEventListener(`genesis_event_${channel}`, (e) => callback(e.detail));
            }
        }
    };

    window.Genesis = Genesis;
})(window);
