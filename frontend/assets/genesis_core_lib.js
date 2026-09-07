/**
 * GENESIS ENTERPRISE SHARED RUNTIME v1.0
 * Zero-dependency universal export and conversion utilities.
 */
window.GenesisCore = {
    // 1. Instant Clean Clipboard Copy
    copyToClipboard: function(text, feedbackId) {
        if (!navigator.clipboard) {
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            const el = document.getElementById(feedbackId);
            if (el) {
                const prev = el.innerText;
                el.innerText = "✔ Copied!";
                setTimeout(() => { el.innerText = prev; }, 1800);
            }
            return;
        }
        navigator.clipboard.writeText(text).then(() => {
            const el = document.getElementById(feedbackId);
            if (el) {
                const prev = el.innerText;
                el.innerText = "✔ Copied!";
                setTimeout(() => { el.innerText = prev; }, 1800);
            }
        });
    },

    // 2. Direct Client-Side JSON / Text / CSV File Downloader
    downloadFile: function(filename, content, mimeType = 'text/plain') {
        const blob = new Blob([content], { type: mimeType });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    },

    // 3. Tabular CSV to JSON In-Memory Converter
    csvToJson: function(csvText) {
        const lines = csvText.trim().split('\n');
        if (lines.length < 2) return [];
        const headers = lines[0].split(',').map(h => h.trim().replace(/^["']|["']$/g, ''));
        return lines.slice(1).map(line => {
            const values = line.split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
            return headers.reduce((acc, h, i) => {
                acc[h] = values[i] || "";
                return acc;
            }, {});
        });
    },

    // 4. Standard NPCI Pre-Filled UPI Paywall Invoker
    triggerPaywall: function() {
        if (window.GenesisDonation) window.GenesisDonation.open();
    }
};
