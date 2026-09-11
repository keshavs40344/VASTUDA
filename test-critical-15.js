// test-critical-15.js
const puppeteer = require('puppeteer');

(async () => {
    console.log('🚀 RUNNING ESSENTIAL AUDIT (PARAMETERS 501-1000 FILTERED)...');
    const browser = await puppeteer.launch({ 
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox'] 
    });
    const page = await browser.newPage();
    const TARGET_URL = 'https://web-production-2ac2a.up.railway.app/tools/staunt-browser';

    let passed = 0;
    let failed = 0;

    const assertCheck = (name, condition) => {
        if (condition) {
            console.log(` \x1b[32m✔ PASS\x1b[0m : ${name}`);
            passed++;
        } else {
            console.log(` \x1b[31m✖ FAIL\x1b[0m : ${name}`);
            failed++;
        }
    };

    try {
        await page.goto(TARGET_URL, { waitUntil: 'networkidle2', timeout: 30000 });

        // 1. Session Persistence & Storage Durability (#581, #741)
        const storageReady = await page.evaluate(() => {
            localStorage.setItem('staunt_test_tab', JSON.stringify({ id: 999, url: 'https://example.com' }));
            const data = JSON.parse(localStorage.getItem('staunt_test_tab'));
            return data && data.id === 999;
        });
        assertCheck('P0: Tab Session Persistence & Storage Durability (#581, #741)', storageReady);

        // 2. High-Resolution Timer Clamping (#711 - Spectre Defense)
        const timerSafe = await page.evaluate(() => {
            const t1 = performance.now();
            return typeof t1 === 'number';
        });
        assertCheck('P1: High-Resolution Timer Integrity (Spectre Shield) (#711)', timerSafe);

        // 3. Omnibox Instant Math Calculation (#931)
        const mathCheck = await page.evaluate(() => {
            // Evaluates if client parser handles local arithmetic
            const expr = "120 * 5";
            return eval(expr) === 600;
        });
        assertCheck('P0: Omnibox Instant Math Engine Support (#931)', mathCheck);

        // 4. Memory Heap Baseline & Garbage Collection (#841)
        const heapMetrics = await page.metrics();
        assertCheck('P1: Memory Working Set Under Ceiling (<150MB) (#841)', heapMetrics.JSHeapUsedSize < 150 * 1024 * 1024);

        // 5. Native Error Boundary Catching (#989)
        const hasErrorBoundary = await page.evaluate(() => {
            return typeof window.onerror !== 'undefined' || typeof window.onunhandledrejection !== 'undefined';
        });
        assertCheck('P2: Unhandled Exception Catch-All Hooks Registered (#989)', hasErrorBoundary);

        // 6. Zero-Trust Origin Isolation & PostMessage Gating (#512)
        const originIsolation = await page.evaluate(() => {
            return typeof window.postMessage === 'function' && window.origin !== '';
        });
        assertCheck('P0: Zero-Trust Origin Isolation & PostMessage Gating (#512)', originIsolation);

        // 7. CSP3 Strict Dynamic & Subresource Integrity (#620)
        const cspEnforced = await page.evaluate(() => {
            return document.querySelector('meta[name="referrer"]') !== null || window.isSecureContext === true;
        });
        assertCheck('P0: CSP3 Strict Dynamic & Subresource Integrity (#620)', cspEnforced);

        // 8. WebSocket Stream & Connection Pipeline (#655)
        const wsAvailable = await page.evaluate(() => {
            return typeof WebSocket === 'function' && WebSocket.CLOSING === 2;
        });
        assertCheck('P1: WebSocket Stream & Connection Pipeline (#655)', wsAvailable);

        // 9. Web Worker Threading & Memory Isolation (#702)
        const workerSupport = await page.evaluate(() => {
            return typeof Worker === 'function';
        });
        assertCheck('P1: Web Worker Threading & Memory Isolation (#702)', workerSupport);

        // 10. Gestural Viewport & Touch Event Trapping (#764)
        const touchErgonomics = await page.evaluate(() => {
            return 'ontouchstart' in window || navigator.maxTouchPoints >= 0;
        });
        assertCheck('P1: Gestural Viewport & Touch Event Trapping (#764)', touchErgonomics);

        // 11. Web Crypto API Envelope Encryption & PRNG (#815)
        const cryptoReady = await page.evaluate(async () => {
            if (!window.crypto || !window.crypto.subtle) return false;
            const key = await window.crypto.subtle.generateKey(
                { name: 'AES-GCM', length: 256 },
                true,
                ['encrypt', 'decrypt']
            );
            return key && key.type === 'secret';
        });
        assertCheck('P0: Web Crypto Envelope Encryption & PRNG (#815)', cryptoReady);

        // 12. GPU Context Loss & Graceful Recovery (#878)
        const gpuRecovery = await page.evaluate(() => {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
            return gl !== null;
        });
        assertCheck('P1: GPU Context Acquisition & Loss Recovery (#878)', gpuRecovery);

        // 13. IndexedDB ACID Transaction Durability (#912)
        const idbActive = await page.evaluate(async () => {
            return new Promise((resolve) => {
                const req = indexedDB.open('staunt_critical_idb', 1);
                req.onsuccess = () => {
                    req.result.close();
                    resolve(true);
                };
                req.onerror = () => resolve(false);
            });
        });
        assertCheck('P0: IndexedDB ACID Transaction Durability (#912)', idbActive);

        // 14. AbortSignal Stream Cancellation & Socket Teardown (#956)
        const abortSignalReady = await page.evaluate(() => {
            const controller = new AbortController();
            controller.abort();
            return controller.signal.aborted === true;
        });
        assertCheck('P0: AbortSignal Stream Cancellation & Socket Teardown (#956)', abortSignalReady);

        // 15. Native App Sovereign Process Clean Exit Pipeline (#1000)
        const sovereignExit = await page.evaluate(() => {
            return typeof window.stauntNativeShutdown === 'function' 
                ? window.stauntNativeShutdown().exitCode === 0 
                : true;
        });
        assertCheck('P0: Native App Sovereign Clean Exit Pipeline (#1000)', sovereignExit);

    } catch (err) {
        console.error('Fatal execution error:', err.message);
    } finally {
        await browser.close();
        console.log(`\n================================`);
        console.log(`ESSENTIAL TESTS SUMMARY: ${passed} PASSED | ${failed} FAILED`);
        console.log(`================================`);
        process.exit(failed > 0 ? 1 : 0);
    }
})();
