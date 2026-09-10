
const PRIMARY_ORIGIN = "https://keshavs40344.pythonanywhere.com";
const SECONDARY_ORIGIN = "https://web-production-2ac2a.up.railway.app";
const TIMEOUT_MS = 3500; // 3.5s timeout threshold for primary failover

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, HEAD, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-Vastuda-Node",
  "Access-Control-Max-Age": "86400",
};

/**
 * Helper to fetch with a timeout
 */
async function fetchWithTimeout(resource, options = {}, timeout = TIMEOUT_MS) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(resource, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1. Handle CORS Preflight Requests
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: CORS_HEADERS
      });
    }

    // 2. Direct Edge Health Check Endpoint
    if (url.pathname === "/api/edge-health") {
      return new Response(JSON.stringify({
        status: "online",
        layer: "Layer 1 - Anycast Edge Ingress",
        provider: "Cloudflare Workers",
        node: "edge-gateway-1",
        timestamp: Date.now(),
        primary_backend: PRIMARY_ORIGIN,
        secondary_backend: SECONDARY_ORIGIN
      }), {
        status: 200,
        headers: {
          ...CORS_HEADERS,
          "Content-Type": "application/json"
        }
      });
    }

    // 3. Forward API & Backend Requests with Multi-Cloud Failover
    const isApiRequest = url.pathname.startsWith("/api/") || url.pathname === "/health" || url.pathname === "/stats";

    if (isApiRequest) {
      let activeOrigin = PRIMARY_ORIGIN;
      let backendResp = null;
      let failoverTriggered = false;

      // Prepare request copy
      const clonedRequest = new Request(request);

      // Attempt Primary (PythonAnywhere)
      try {
        const primaryUrl = new URL(url.pathname + url.search, PRIMARY_ORIGIN);
        const reqInit = {
          method: request.method,
          headers: new Headers(request.headers),
          redirect: "follow"
        };

        if (request.method !== "GET" && request.method !== "HEAD") {
          reqInit.body = await clonedRequest.arrayBuffer();
        }

        backendResp = await fetchWithTimeout(primaryUrl.toString(), reqInit, TIMEOUT_MS);

        // If primary returns server error (502, 503, 504), force failover to secondary
        if (backendResp.status >= 500) {
          throw new Error(`Primary backend returned status ${backendResp.status}`);
        }
      } catch (primaryErr) {
        console.warn(`[FAILOVER] Primary backend failed (${primaryErr.message}). Switching to Secondary (Railway)...`);
        failoverTriggered = true;
        activeOrigin = SECONDARY_ORIGIN;

        // Attempt Secondary (Railway)
        try {
          const secondaryUrl = new URL(url.pathname + url.search, SECONDARY_ORIGIN);
          const reqInitSecondary = {
            method: request.method,
            headers: new Headers(request.headers),
            redirect: "follow"
          };
          if (request.method !== "GET" && request.method !== "HEAD") {
            reqInitSecondary.body = await request.clone().arrayBuffer();
          }

          backendResp = await fetchWithTimeout(secondaryUrl.toString(), reqInitSecondary, 5000);
        } catch (secondaryErr) {
          console.error(`[FAILOVER CRITICAL] Both backends unreachable: ${secondaryErr.message}`);
          backendResp = null;
        }
      }

      // If a backend responded, attach CORS and edge telemetry headers
      if (backendResp) {
        const responseHeaders = new Headers(backendResp.headers);
        Object.entries(CORS_HEADERS).forEach(([k, v]) => responseHeaders.set(k, v));
        responseHeaders.set("X-Vastuda-Routing-Node", activeOrigin);
        responseHeaders.set("X-Vastuda-Failover-Active", failoverTriggered ? "true" : "false");

        return new Response(backendResp.body, {
          status: backendResp.status,
          statusText: backendResp.statusText,
          headers: responseHeaders
        });
      }

      // 4. Graceful Fallback if both nodes are offline
      return new Response(JSON.stringify({
        status: "degraded",
        service: "VASTUDA Sovereign Edge Mesh",
        message: "Origin backends undergoing failover transition. Edge mesh active.",
        layer1_status: "operational",
        failover_active: true,
        timestamp: Date.now()
      }), {
        status: 203,
        headers: {
          ...CORS_HEADERS,
          "Content-Type": "application/json",
          "X-Vastuda-Resilience": "edge-cached-fallback"
        }
      });
    }

    // 5. Non-API / Static Requests: Forward to Primary origin or serve landing page
    try {
      const targetUrl = new URL(url.pathname + url.search, PRIMARY_ORIGIN);
      const resp = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: request.headers
      });
      if (resp.status !== 404 && resp.status < 500) {
        return resp;
      }
    } catch (e) {
      // Fall through to secondary
    }

    // Fallback to Secondary for static files
    try {
      const secUrl = new URL(url.pathname + url.search, SECONDARY_ORIGIN);
      return await fetch(secUrl.toString(), {
        method: request.method,
        headers: request.headers
      });
    } catch (e) {
      return new Response("VASTUDA Cloud Mesh Active - Initializing frontend...", {
        status: 200,
        headers: { "Content-Type": "text/plain" }
      });
    }
  }
};
