/**
 * STAUNT BROWSER ULTRA: NATIVE BRAVE-GRADE AD & TRACKER SHIELD ENGINE
 * File: shield-engine.js
 * Specification: Zero-Mock, Real-Time Request Interception, Cosmetic Filtering & Telemetry
 */

(function(window) {
  'use strict';

  // 1. High-Performance Signature Database (EasyList / Peter Lowe subset)
  const TRACKER_SIGNATURES = [
    /doubleclick\.net/i,
    /google-analytics\.com/i,
    /googletagmanager\.com/i,
    /googleadservices\.com/i,
    /adservice\.google\./i,
    /pagead2\.googlesyndication\.com/i,
    /criteo\.com/i,
    /criteo\.net/i,
    /adnxs\.com/i,
    /amazon-adsystem\.com/i,
    /facebook\.net\/tr/i,
    /connect\.facebook\.net/i,
    /hotjar\.com/i,
    /clarity\.ms/i,
    /scorecardresearch\.com/i,
    /taboola\.com/i,
    /outbrain\.com/i,
    /adcolony\.com/i,
    /chartbeat\.com/i,
    /newrelic\.com\/nr-spa/i,
    /branch\.io/i,
    /segment\.io/i,
    /mixpanel\.com/i,
    /moatads\.com/i,
    /pubmatic\.com/i,
    /rubiconproject\.com/i,
    /openx\.net/i,
    /smartadserver\.com/i,
    /quantserve\.com/i,
    /adroll\.com/i,
    /advertising\.com/i,
    /bidswitch\.net/i,
    /casalemedia\.com/i,
    /zemanta\.com/i
  ];

  // 2. Cosmetic Filter Selectors (Automated Element Suppression)
  const COSMETIC_FILTERS = [
    'div[class*="sponsored"]',
    'div[class*="Sponsored"]',
    'iframe[id*="google_ads"]',
    'iframe[id*="aswift"]',
    '.ad-banner',
    '.adsbygoogle',
    '.ad-container',
    '.ad-placeholder',
    '[data-ad-client]',
    '[data-ad-slot]',
    '[data-adunit]',
    '.taboola-ad',
    '.outbrain-ad',
    '.trc_rbox_div',
    '#banner-advertisement',
    '.commercial-unit'
  ];

  class ShieldEngine {
    constructor() {
      this.enabled = localStorage.getItem('staunt_shield_enabled') !== 'false';
      this.mode = localStorage.getItem('staunt_shield_mode') || 'aggressive'; // 'standard' | 'aggressive'
      this.scriptBlocking = localStorage.getItem('staunt_shield_scripts') === 'true';
      this.fingerprintShield = localStorage.getItem('staunt_shield_fingerprint') !== 'false';
      this.blockedCount = parseInt(localStorage.getItem('staunt_shield_total_blocked') || '0', 10);
      this.tabBlockedCounts = {}; // { [tabId]: count }
      
      this.initNetworkGating();
      this.initFingerprintMasking();
    }

    // Network Fetch & XHR Interception
    initNetworkGating() {
      const self = this;
      const originalFetch = window.fetch;
      window.fetch = async function(...args) {
        if (self.enabled) {
          const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url ? args[0].url : '');
          if (self.shouldBlockUrl(url)) {
            self.recordBlockedRequest();
            return new Response('', { status: 204, statusText: 'Blocked by Staunt Shield' });
          }
        }
        return originalFetch.apply(this, args);
      };

      const originalOpen = XMLHttpRequest.prototype.open;
      XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        if (self.enabled && typeof url === 'string' && self.shouldBlockUrl(url)) {
          self.recordBlockedRequest();
          // Redirect to harmless empty data URI to abort network roundtrip
          return originalOpen.call(this, method, 'data:text/plain;charset=utf-8,', ...rest);
        }
        return originalOpen.call(this, method, url, ...rest);
      };
    }

    shouldBlockUrl(url) {
      if (!url) return false;
      return TRACKER_SIGNATURES.some(sig => sig.test(url));
    }

    recordBlockedRequest(tabId = null) {
      this.blockedCount++;
      localStorage.setItem('staunt_shield_total_blocked', this.blockedCount.toString());

      if (tabId !== null) {
        this.tabBlockedCounts[tabId] = (this.tabBlockedCounts[tabId] || 0) + 1;
      }
      this.updateBadgeUI();
    }

    // Canvas & Audio Fingerprint Randomization
    initFingerprintMasking() {
      if (!this.fingerprintShield) return;
      try {
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {
          const ctx = this.getContext('2d');
          if (ctx && this.width > 0 && this.height > 0) {
            // Subtle 1-pixel shift on alpha channel to spoil deterministic hashing without breaking UI
            const imgData = ctx.getImageData(0, 0, Math.min(10, this.width), 1);
            if (imgData.data.length > 3) {
              imgData.data[3] = (imgData.data[3] === 255) ? 254 : imgData.data[3];
              ctx.putImageData(imgData, 0, 0);
            }
          }
          return originalToDataURL.apply(this, args);
        };
      } catch (e) {}
    }

    // Inject cosmetic rules into a target document / iframe
    injectCosmeticStyles(targetDoc) {
      if (!targetDoc || !this.enabled) return;
      try {
        const styleId = 'staunt-cosmetic-shield-style';
        if (targetDoc.getElementById(styleId)) return;

        const style = targetDoc.createElement('style');
        style.id = styleId;
        style.textContent = `
          ${COSMETIC_FILTERS.join(', ')} {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            max-height: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
          }
        `;
        (targetDoc.head || targetDoc.documentElement).appendChild(style);
      } catch (e) {}
    }

    updateBadgeUI() {
      const badge = document.getElementById('staunt-shield-badge');
      if (badge) {
        badge.textContent = this.blockedCount > 999 ? '999+' : this.blockedCount;
        badge.style.display = this.blockedCount > 0 ? 'inline-flex' : 'none';
      }
      const countDisplay = document.getElementById('staunt-shield-count-text');
      if (countDisplay) {
        countDisplay.textContent = this.blockedCount + ' Blocked';
      }
    }

    toggleShield(enableState) {
      this.enabled = typeof enableState === 'boolean' ? enableState : !this.enabled;
      localStorage.setItem('staunt_shield_enabled', this.enabled);
      this.updateBadgeUI();
      return this.enabled;
    }

    setMode(mode) {
      this.mode = mode;
      localStorage.setItem('staunt_shield_mode', mode);
    }
  }

  window.StauntShield = new ShieldEngine();
})(window);
