const puppeteer = require('puppeteer');
const path = require('path');

const TARGET_URL = 'file:///' + path.resolve(__dirname, 'frontend/saas/staunt-browser.html').replace(/\\/g, '/');

async function runPhase4Tests() {
  console.log('====================================================================');
  console.log('   STAUNT BROWSER ULTRA: PHASE 4 HARDENING & RELIABILITY AUDIT');
  console.log('   Target:', TARGET_URL);
  console.log('====================================================================\n');

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  let passed = 0;
  let failed = 0;

  async function test(name, fn) {
    try {
      await fn();
      console.log(`[PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`[FAIL] ${name}:`, err.message);
      failed++;
    }
  }

  await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });

  // 1. User Journey: Open browser and verify initial tab
  await test('Journey 1.1: Browser initializes with valid active tab and clock', async () => {
    const state = await page.evaluate(() => {
      return {
        hasTabs: window.tabs && window.tabs.length >= 1,
        activeTabId: window.activeTabId !== null,
        tabCount: document.querySelectorAll('.tab-pill').length
      };
    });
    if (!state.hasTabs || !state.activeTabId || state.tabCount < 1) throw new Error('Tab initialization invalid');
  });

  // 2. User Journey: New tab creation
  await test('Journey 1.2: New tab creation increments tab count and updates DOM', async () => {
    const beforeCount = await page.evaluate(() => window.tabs.length);
    await page.evaluate(() => window.createTab('https://example.com'));
    const afterCount = await page.evaluate(() => window.tabs.length);
    if (afterCount !== beforeCount + 1) throw new Error('Tab count did not increment');
  });

  // 3. User Journey: Search resolution
  await test('Journey 1.3: Search query resolves with configured search engine', async () => {
    const resolved = await page.evaluate(() => window.resolveTargetUrl('quantum computing fundamentals'));
    if (!resolved.includes('google.com/search?q=') && !resolved.includes('duckduckgo.com') && !resolved.includes('bing.com')) {
      throw new Error('Search query did not resolve to search engine: ' + resolved);
    }
  });

  // 4. User Journey: Navigation & Bookmarking
  await test('Journey 1.4: Bookmark current page and verify persistence in safeStorage', async () => {
    await page.evaluate(() => {
      const bms = window.safeStorage.get('staunt_bookmarks', []);
      bms.push({ name: 'Test Target', url: 'https://test-target.org' });
      window.safeStorage.set('staunt_bookmarks', bms);
    });
    const hasBm = await page.evaluate(() => {
      const bms = window.safeStorage.get('staunt_bookmarks', []);
      const backupBms = JSON.parse(localStorage.getItem('staunt_bookmarks_backup') || '[]');
      return bms.some(b => b.name === 'Test Target') && backupBms.some(b => b.name === 'Test Target');
    });
    if (!hasBm) throw new Error('Bookmark not preserved in primary and backup storage');
  });

  // 5. User Journey: Close tab and reopen closed tab
  await test('Journey 1.5: Close tab and reopen via reopenClosedTab restores state', async () => {
    const countBefore = await page.evaluate(() => window.tabs.length);
    await page.evaluate(() => window.closeActiveTab());
    const countClosed = await page.evaluate(() => window.tabs.length);
    await page.evaluate(() => window.reopenClosedTab());
    const countReopened = await page.evaluate(() => window.tabs.length);
    if (countClosed !== countBefore - 1 || countReopened !== countBefore) {
      throw new Error(`Tab count transition invalid: ${countBefore} -> ${countClosed} -> ${countReopened}`);
    }
  });

  // 6. User Journey: History recording
  await test('Journey 1.6: Navigation records entry in history drawer and backup storage', async () => {
    await page.evaluate(() => window.addHistoryEntry('https://history-journey.org', 'Journey Page'));
    const recorded = await page.evaluate(() => {
      const h = window.safeStorage.get('staunt_history', []);
      const hb = JSON.parse(localStorage.getItem('staunt_history_backup') || '[]');
      return h.some(x => x.url === 'https://history-journey.org') && hb.some(x => x.url === 'https://history-journey.org');
    });
    if (!recorded) throw new Error('History entry missing in primary or backup storage');
  });

  // 7. Error Handling: In-frame error recovery card
  await test('Resilience 2.1: showTabError renders actionable recovery card with zero blank screen', async () => {
    const errRendered = await page.evaluate(() => {
      const tId = window.activeTabId;
      window.showTabError(tId, 'https://broken-domain-offline-test.org', 'ERR_NAME_NOT_RESOLVED', 'Server address could not be found');
      const vp = document.getElementById('viewport-' + tId);
      const card = vp ? vp.querySelector('.tab-error-card') : null;
      const iframe = vp ? vp.querySelector('.embed-frame') : null;
      const hasRetry = card && !!card.querySelector('.btn-retry-nav');
      const hasFallback = card && !!card.querySelector('.btn-fallback-search');
      const iframeHidden = iframe && iframe.style.display === 'none';
      return !!card && hasRetry && hasFallback && iframeHidden;
    });
    if (!errRendered) throw new Error('Error card or recovery buttons failed to render');
  });

  // 8. Error Recovery: Retry button action
  await test('Resilience 2.2: Error card Retry button removes error state and reloads frame', async () => {
    const recovered = await page.evaluate(() => {
      const tId = window.activeTabId;
      const vp = document.getElementById('viewport-' + tId);
      const retryBtn = vp.querySelector('.btn-retry-nav');
      if (retryBtn) retryBtn.click();
      const cardRemaining = vp.querySelector('.tab-error-card');
      const iframeVisible = vp.querySelector('.embed-frame').style.display === 'block';
      return !cardRemaining && iframeVisible;
    });
    if (!recovered) throw new Error('Retry did not clear error card and restore iframe');
  });

  // 9. Safe Storage Corruption Resilience
  await test('Data Safety 3.1: safeStorage gracefully recovers from intentionally corrupted JSON', async () => {
    const recoveryResult = await page.evaluate(() => {
      // 1. Establish known good data
      window.safeStorage.set('staunt_test_corrupt', { valid: true, timestamp: 12345 });
      // 2. Corrupt primary key with malformed JSON
      localStorage.setItem('staunt_test_corrupt', '{malformed: "broken JSON-);');
      // 3. safeStorage.get should detect corrupt JSON and fall back to backup
      const recovered = window.safeStorage.get('staunt_test_corrupt', null);
      // Clean up
      localStorage.removeItem('staunt_test_corrupt');
      localStorage.removeItem('staunt_test_corrupt_backup');
      return recovered && recovered.valid === true;
    });
    if (!recoveryResult) throw new Error('safeStorage failed to heal corrupted JSON from backup mirror');
  });

  // 10. Session Recovery Self-Healing
  await test('Data Safety 3.2: Corrupted session tabs self-heals without uncaught exception', async () => {
    const sessionHealed = await page.evaluate(() => {
      localStorage.setItem('staunt_session_tabs', '###CORRUPT_NOT_JSON###');
      localStorage.removeItem('staunt_session_tabs_backup');
      try {
        const list = window.safeStorage.get('staunt_session_tabs', null);
        return list === null; // Confirms safeStorage handles corruption and returns fallback
      } catch (e) {
        return false;
      }
    });
    if (!sessionHealed) throw new Error('Corrupted session threw uncaught exception');
  });

  // 11. Offline and Online Auto-Recovery
  await test('Network 4.1: Offline event triggers banner and online event initiates auto-recovery', async () => {
    const networkFlow = await page.evaluate(() => {
      window.dispatchEvent(new Event('offline'));
      const banner = document.getElementById('offline-banner');
      const offlineShown = banner && banner.style.display === 'flex' && document.body.classList.contains('is-offline');
      
      window.dispatchEvent(new Event('online'));
      const onlineCleared = banner && banner.style.display === 'none' && !document.body.classList.contains('is-offline');
      return offlineShown && onlineCleared;
    });
    if (!networkFlow) throw new Error('Offline/Online event transitions failed');
  });

  // 12. Accessibility: Global Escape key closes all open modals and drawers
  await test('A11y 5.1: Global Escape key dismisses open drawers and dropdowns', async () => {
    const escDismissed = await page.evaluate(() => {
      const sDrawer = document.getElementById('settings-drawer');
      sDrawer.classList.add('open');
      const isOpened = sDrawer.classList.contains('open');

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
      const isClosed = !sDrawer.classList.contains('open');
      return isOpened && isClosed;
    });
    if (!escDismissed) throw new Error('Escape key failed to dismiss open drawer');
  });

  // 13. Accessibility: Focus-visible outline styling
  await test('A11y 5.2: Focus-visible rules are present in stylesheet', async () => {
    const hasFocusVisible = await page.evaluate(() => {
      const styles = Array.from(document.querySelectorAll('style')).map(s => s.textContent).join(' ');
      return styles.includes(':focus-visible') && styles.includes('outline');
    });
    if (!hasFocusVisible) throw new Error(':focus-visible CSS rules missing from page stylesheet');
  });

  // 14. Responsive Viewport Matrix
  const breakpoints = [
    { name: 'Mobile 320px', width: 320, height: 600 },
    { name: 'Mobile 390px', width: 390, height: 844 },
    { name: 'Tablet 768px', width: 768, height: 1024 },
    { name: 'Desktop 1440px', width: 1440, height: 900 },
    { name: '4K UHD 3840px', width: 3840, height: 2160 }
  ];

  for (const bp of breakpoints) {
    await test(`Responsive Matrix 6: Layout stability at ${bp.name} (${bp.width}x${bp.height})`, async () => {
      await page.setViewport({ width: bp.width, height: bp.height });
      const noHorizontalOverflow = await page.evaluate(() => {
        const bodyWidth = document.body.getBoundingClientRect().width;
        const rootWidth = document.documentElement.clientWidth;
        return Math.abs(bodyWidth - rootWidth) <= 5;
      });
      if (!noHorizontalOverflow) throw new Error(`Horizontal overflow or clipping detected at ${bp.name}`);
    });
  }

  await browser.close();

  console.log('\n====================================================================');
  console.log(` PHASE 4 AUDIT COMPLETE: ${passed} PASSED, ${failed} FAILED`);
  console.log('====================================================================\n');

  if (failed > 0) process.exit(1);
}

runPhase4Tests().catch(err => {
  console.error('Fatal error running Phase 4 tests:', err);
  process.exit(1);
});
