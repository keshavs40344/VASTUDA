/**
 * Staunt Web-Core Reverse-Proxy & Gateway Server
 * Enterprise-Hardened In-Process Proxy Gateway
 * 
 * 1. First-Party Masking & Origin Spoofing (Bypasses Edge/Chrome 3rd-party tracker blocks)
 * 2. Catch-All Relative Routing Middleware (Routes /youtubei/v1/..., /s/desktop/..., etc. directly to upstream)
 * 3. Frame-Unblocking & Permissive CORS (Strips XFO, CSP, COOP/COEP; injects Access-Control-*)
 * 4. WebSocket & Chunked Media Streaming Stability
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const http = require('http');
const https = require('https');
const { createProxyMiddleware, responseInterceptor } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;

// Modern desktop Chrome User-Agent
const DESKTOP_CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';

// Global upstream tracking state: Tracks currently active domain for relative catch-all routing
let activeUpstreamOrigin = 'https://www.youtube.com';

function normalizeTargetUrl(raw) {
  if (!raw) return null;
  let urlStr = raw.trim();
  if (!/^https?:\/\//i.test(urlStr)) {
    urlStr = 'https://' + urlStr;
  }
  return urlStr;
}

// 1. Enable Global Permissive CORS
app.use(cors({
  origin: '*',
  methods: ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['*'],
  exposedHeaders: ['*'],
  credentials: true
}));

// Preflight handler
app.options('*', (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, DELETE, PATCH, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.sendStatus(200);
});

// Helper: Configure Outgoing Request Headers to Spoof 1st-Party Origin
function configureOutgoingHeaders(proxyReq, req, targetUrl) {
  try {
    const targetObj = new URL(targetUrl);
    
    // Spoof Host, Origin, and Referer so the target service treats requests as 1st-party
    proxyReq.setHeader('Host', targetObj.host);
    proxyReq.setHeader('Origin', targetObj.origin);
    proxyReq.setHeader('Referer', targetObj.origin + '/');
    proxyReq.setHeader('User-Agent', DESKTOP_CHROME_UA);
    proxyReq.setHeader('Accept-Language', 'en-US,en;q=0.9');
    
    // Strip client-identifying headers that could trigger 3rd-party blocks
    proxyReq.removeHeader('sec-fetch-dest');
    proxyReq.removeHeader('sec-fetch-mode');
    proxyReq.removeHeader('sec-fetch-site');
    proxyReq.setHeader('sec-fetch-site', 'same-origin');
    proxyReq.setHeader('sec-fetch-mode', 'cors');
  } catch (e) {
    console.error('[PROXY HEADER ERROR]', e.message);
  }
}

// Helper: Strip Frame-Blocking Headers & Inject Permissive CORS
function cleanResponseHeaders(proxyRes, res) {
  const headersToDelete = [
    'x-frame-options',
    'content-security-policy',
    'content-security-policy-report-only',
    'frame-options',
    'strict-transport-security',
    'cross-origin-opener-policy',
    'cross-origin-embedder-policy',
    'cross-origin-resource-policy'
  ];

  headersToDelete.forEach((header) => {
    delete proxyRes.headers[header];
    res.removeHeader(header);
  });

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, DELETE, PATCH, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('X-Frame-Options', 'ALLOWALL');
}

// 2. PRIMARY GATEWAY PROXY ROUTE: /gateway?url=<TARGET_URL>
const gatewayProxy = createProxyMiddleware({
  router: (req) => {
    const rawTarget = req.query.url;
    const resolved = normalizeTargetUrl(rawTarget);
    if (!resolved) {
      return activeUpstreamOrigin;
    }
    try {
      const u = new URL(resolved);
      activeUpstreamOrigin = u.origin;
    } catch(e) {}
    return resolved;
  },
  changeOrigin: true,
  ws: true,
  followRedirects: true,
  autoRewrite: true,
  selfHandleResponse: true,

  on: {
    proxyReq: (proxyReq, req, res) => {
      const targetUrl = normalizeTargetUrl(req.query.url) || activeUpstreamOrigin;
      configureOutgoingHeaders(proxyReq, req, targetUrl);
    },

    proxyRes: responseInterceptor(async (responseBuffer, proxyRes, req, res) => {
      cleanResponseHeaders(proxyRes, res);

      const contentType = proxyRes.headers['content-type'] || '';

      // For HTML pages, inject <base href="..."> and navigation/tracker bridge
      if (contentType.includes('text/html')) {
        try {
          const targetUrl = normalizeTargetUrl(req.query.url) || activeUpstreamOrigin;
          const targetObj = new URL(targetUrl);
          let html = responseBuffer.toString('utf8');

          const baseTag = `<base href="${targetObj.origin}/">`;
          const navigationScript = `
            <script>
              (function() {
                // Intercept link clicks to keep navigation inside the Staunt Gateway
                document.addEventListener('click', function(e) {
                  var a = e.target.closest('a');
                  if (a && a.href && !a.href.startsWith('javascript:') && !a.href.startsWith('#')) {
                    e.preventDefault();
                    if (window.parent && window.parent !== window) {
                      window.parent.postMessage({ type: 'STAUNT_NAVIGATE', url: a.href }, '*');
                    } else {
                      window.location.href = '/gateway?url=' + encodeURIComponent(a.href);
                    }
                  }
                }, true);
              })();
            </script>
          `;

          if (/<head[^>]*>/i.test(html)) {
            html = html.replace(/<head[^>]*>/i, (m) => m + '\n' + baseTag);
          } else {
            html = baseTag + '\n' + html;
          }

          if (/<body[^>]*>/i.test(html)) {
            html = html.replace(/<body[^>]*>/i, (m) => m + '\n' + navigationScript);
          } else {
            html = html + '\n' + navigationScript;
          }

          return html;
        } catch (err) {
          console.error('[GATEWAY HTML TRANSFORM ERROR]:', err);
        }
      }

      return responseBuffer;
    }),

    error: (err, req, res) => {
      console.error('[GATEWAY PROXY ERROR]:', err.message);
      if (!res.headersSent) {
        cleanResponseHeaders({}, res);
        res.status(502).json({
          status: 'error',
          code: 'BAD_GATEWAY',
          message: 'Unable to connect to target destination via Staunt Web Gateway.',
          details: err.message
        });
      }
    }
  }
});

app.use('/gateway', gatewayProxy);

// 3. Local Static Frontend Hosting (Only matching local files)
const publicDir = path.join(__dirname, 'src');
app.use(express.static(publicDir, {
  maxAge: '1d',
  index: false,
  setHeaders: (res, filePath) => {
    if (filePath.endsWith('.html')) {
      res.setHeader('Cache-Control', 'no-cache');
    }
  }
}));

// Known local frontend routes
app.get('/', (req, res) => {
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.get('/index.html', (req, res) => {
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.get('/tools/staunt-browser', (req, res) => {
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'Staunt Web-Core Gateway',
    activeUpstream: activeUpstreamOrigin,
    timestamp: Date.now()
  });
});

// 4. CATCH-ALL RELATIVE ROUTING MIDDLEWARE
// Forwards any subresource requests (/youtubei/v1/..., /s/desktop/..., /manifest.json, etc.)
// directly to the active upstream origin to bypass 404s and 3rd-party tracker blocks
const catchAllProxy = createProxyMiddleware({
  router: () => activeUpstreamOrigin,
  changeOrigin: true,
  ws: true,
  followRedirects: true,
  autoRewrite: true,

  on: {
    proxyReq: (proxyReq, req, res) => {
      configureOutgoingHeaders(proxyReq, req, activeUpstreamOrigin + req.url);
    },
    proxyRes: (proxyRes, req, res) => {
      cleanResponseHeaders(proxyRes, res);
    },
    error: (err, req, res) => {
      console.warn(`[CATCH-ALL FORWARD WARNING] Failed for ${req.url}:`, err.message);
      if (!res.headersSent) {
        cleanResponseHeaders({}, res);
        res.status(404).json({ error: 'Upstream resource not reachable', path: req.url });
      }
    }
  }
});

// Any remaining unmatched route is forwarded to active upstream
app.use('*', catchAllProxy);

// 5. Create HTTP & WebSocket Server
const server = http.createServer(app);

// Handle WebSockets upgrade
server.on('upgrade', (req, socket, head) => {
  if (req.url.startsWith('/gateway')) {
    gatewayProxy.upgrade(req, socket, head);
  } else {
    catchAllProxy.upgrade(req, socket, head);
  }
});

// Start listening
server.listen(PORT, '0.0.0.0', () => {
  console.log(`[STAUNT CORE] Enterprise Reverse-Proxy Gateway running on port ${PORT}`);
  console.log(`[STAUNT CORE] Default Upstream Origin: ${activeUpstreamOrigin}`);
  console.log(`[STAUNT CORE] Ready on http://localhost:${PORT}`);
});

module.exports = app;
