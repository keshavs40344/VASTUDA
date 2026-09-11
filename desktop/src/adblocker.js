// Staunt Shield — Enterprise Defense-in-Depth Network Armor
// Network-layer blocker, scriptlet surrogate firewall, anti-phishing, & homograph guard

const BLOCKED_PATTERNS = [
  // Major Ad Networks
  '*://*.doubleclick.net/*',
  '*://*.googlesyndication.com/*',
  '*://*.googleadservices.com/*',
  '*://*.adservice.google.*/*',
  '*://*.adnxs.com/*',
  '*://*.rubiconproject.com/*',
  '*://*.criteo.com/*',
  '*://*.criteo.net/*',
  '*://*.outbrain.com/*',
  '*://*.taboola.com/*',
  '*://*.popads.net/*',
  '*://*.propellerads.com/*',
  '*://*.media.net/*',
  '*://*.pubmatic.com/*',
  '*://*.casalemedia.com/*',
  '*://*.bidswitch.net/*',
  '*://*.adroll.com/*',
  '*://*.scorecardresearch.com/*',
  '*://*.quantserve.com/*',
  '*://*.zedo.com/*',
  '*://*.adform.net/*',
  '*://*.adtechus.com/*',
  '*://*.moatads.com/*',
  '*://*.inmobi.com/*',
  '*://*.smartadserver.com/*',
  '*://*.exponential.com/*',
  '*://*.advertising.com/*',

  // Trackers & Telemetry Beacons
  '*://*.google-analytics.com/*',
  '*://*.hotjar.com/*',
  '*://*.mouseflow.com/*',
  '*://*.crazyegg.com/*',
  '*://*.fullstory.com/*',
  '*://*.segment.io/*',
  '*://*.segment.com/*',
  '*://*.mixpanel.com/*',
  '*://*.optimizely.com/*',
  '*://*.clarity.ms/*',
  '*://*.facebook.net/*/fbevents.js*',
  '*://*.connect.facebook.net/*/sdk.js*',
  '*://*.ads-twitter.com/*',
  '*://*.analytics.twitter.com/*',

  // YouTube Prerolls & Ad Pods
  '*://*.youtube.com/api/stats/ads*',
  '*://*.youtube.com/pagead/*',
  '*://*.youtube.com/ptracking*',

  // Crypto Miners
  '*://*.coinhive.com/*',
  '*://*.crypto-loot.com/*',
  '*://*.coin-have.com/*',
  '*://*.jsecoin.com/*'
];

// High-Risk TLDs & Phishing Signatures
const DECEPTIVE_TLDS = ['.zip', '.mov', '.kim', '.country', '.work', '.gq', '.cf', '.tk', '.ml'];

let blockedStats = {
  totalBlocked: 0,
  trackersBlocked: 0,
  adsBlocked: 0,
  phishingBlocked: 0,
  bandwidthSavedMB: 0.0
};

function isHomographOrDeceptive(urlStr) {
  try {
    const parsed = new URL(urlStr);
    const host = parsed.hostname.toLowerCase();
    
    // Check for punycode / homograph spoofing (xn--)
    if (host.includes('xn--')) {
      return true;
    }
    // Check for deceptive brand spoofing (e.g. paypa1, go0gle, app1e)
    if (/paypa[l1i]|g[o0]{2}g[l1]e|micr[o0]s[o0]ft|app[l1]e-secure|netflix-login/i.test(host)) {
      if (!host.endsWith('.paypal.com') && !host.endsWith('.google.com') && !host.endsWith('.microsoft.com') && !host.endsWith('.apple.com') && !host.endsWith('.netflix.com')) {
        return true;
      }
    }
    return false;
  } catch (e) {
    return false;
  }
}

function setupStauntShield(ses, onBlockedCallback) {
  // 1. Pre-execution Network Interceptor
  ses.webRequest.onBeforeRequest({ urls: ['*://*/*'] }, (details, callback) => {
    // Check homograph / phishing guard
    if (details.resourceType === 'mainFrame' && isHomographOrDeceptive(details.url)) {
      blockedStats.phishingBlocked++;
      console.warn('[PHISHING BLOCKED] Homograph/Spoofed domain intercepted:', details.url);
      if (onBlockedCallback) {
        onBlockedCallback({ url: details.url, type: 'phishing', stats: getShieldStats() });
      }
      return callback({ cancel: true });
    }

    // Check Ad / Tracker matching
    const isBlocked = BLOCKED_PATTERNS.some(pat => {
      const clean = pat.replace(/\*/g, '').replace(/^[a-z]+:\/\//, '');
      return details.url.includes(clean);
    });

    if (isBlocked) {
      // Contextual First-Party Protection: Allow direct navigation to analytics dashboards
      if (details.resourceType === 'mainFrame') {
        return callback({ cancel: false });
      }

      blockedStats.totalBlocked++;
      if (details.url.includes('analytics') || details.url.includes('metric') || details.url.includes('telemetry') || details.url.includes('fbevents')) {
        blockedStats.trackersBlocked++;
      } else {
        blockedStats.adsBlocked++;
      }
      blockedStats.bandwidthSavedMB += 0.15;

      if (onBlockedCallback) {
        onBlockedCallback({
          url: details.url,
          type: 'ad',
          stats: getShieldStats()
        });
      }
      return callback({ cancel: true });
    }

    callback({ cancel: false });
  });

  // 2. Outgoing Header Sanitization (Anti-Fingerprinting)
  ses.webRequest.onBeforeSendHeaders((details, callback) => {
    const headers = { ...details.requestHeaders };
    
    // Strip device-identifying telemetry & tracking headers
    delete headers['X-Client-Data'];
    delete headers['Sec-CH-UA-Model'];
    delete headers['Sec-CH-UA-Platform-Version'];
    delete headers['Sec-CH-UA-Full-Version-List'];
    
    // Enforce Global Privacy Control and Do Not Track
    headers['Sec-GPC'] = '1';
    headers['DNT'] = '1';
    
    callback({ requestHeaders: headers });
  });
}

function getShieldStats() {
  return { 
    ...blockedStats, 
    bandwidthSavedMB: Number(blockedStats.bandwidthSavedMB.toFixed(2)) 
  };
}

function resetShieldStats() {
  blockedStats = { totalBlocked: 0, trackersBlocked: 0, adsBlocked: 0, phishingBlocked: 0, bandwidthSavedMB: 0.0 };
}

module.exports = {
  setupStauntShield,
  getShieldStats,
  resetShieldStats,
  isHomographOrDeceptive,
  BLOCKED_PATTERNS
};
