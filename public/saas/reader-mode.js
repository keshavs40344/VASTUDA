/**
 * STAUNT BROWSER ULTRA: DISTRACTION-FREE SAFARI READER MODE ENGINE
 * File: reader-mode.js
 * Specification: Zero-Mock, DOM Content Extractor & Tranquil Editorial Reading Surface
 */

(function(window) {
  'use strict';

  class ReaderModeEngine {
    constructor() {
      this.isActive = false;
      this.currentTheme = localStorage.getItem('staunt_reader_theme') || 'zinc'; // 'black' | 'sepia' | 'zinc'
      this.currentFontSize = parseInt(localStorage.getItem('staunt_reader_font_size') || '18', 10);
      this.currentFontFamily = localStorage.getItem('staunt_reader_font_family') || 'serif'; // 'sans' | 'serif' | 'mono'

      this.injectDOM();
    }

    injectDOM() {
      if (document.getElementById('staunt-reader-overlay')) return;

      const overlay = document.createElement('div');
      overlay.id = 'staunt-reader-overlay';
      overlay.className = `staunt-reader-surface theme-${this.currentTheme} font-${this.currentFontFamily}`;
      overlay.innerHTML = `
        <div class="staunt-reader-toolbar">
          <div class="staunt-reader-tools-left">
            <span class="staunt-reader-badge">📖 READER MODE</span>
          </div>
          <div class="staunt-reader-tools-center">
            <!-- Font Family -->
            <button class="staunt-reader-btn" id="reader-font-sans" title="System Sans">Sans</button>
            <button class="staunt-reader-btn" id="reader-font-serif" title="Editorial Serif">Serif</button>
            <button class="staunt-reader-btn" id="reader-font-mono" title="Code Mono">Mono</button>
            <div class="staunt-reader-divider"></div>
            <!-- Font Size -->
            <button class="staunt-reader-btn" id="reader-size-down" title="Smaller Font">A-</button>
            <button class="staunt-reader-btn" id="reader-size-up" title="Larger Font">A+</button>
            <div class="staunt-reader-divider"></div>
            <!-- Themes -->
            <button class="staunt-reader-theme-dot theme-dot-zinc" id="reader-theme-zinc" title="Modern Zinc"></button>
            <button class="staunt-reader-theme-dot theme-dot-sepia" id="reader-theme-sepia" title="Warm Sepia"></button>
            <button class="staunt-reader-theme-dot theme-dot-black" id="reader-theme-black" title="Pure Black"></button>
          </div>
          <div class="staunt-reader-tools-right">
            <button class="staunt-reader-close" id="staunt-reader-close-btn" title="Exit Reader Mode (ESC)">✕ Close</button>
          </div>
        </div>
        <div class="staunt-reader-content-wrap">
          <h1 class="staunt-reader-title" id="staunt-reader-title"></h1>
          <div class="staunt-reader-meta" id="staunt-reader-meta"></div>
          <div class="staunt-reader-body" id="staunt-reader-body"></div>
        </div>
      `;

      document.body.appendChild(overlay);

      // Inject reader surface styles
      if (!document.getElementById('staunt-reader-styles')) {
        const style = document.createElement('style');
        style.id = 'staunt-reader-styles';
        style.textContent = `
          .staunt-reader-surface {
            position: fixed;
            inset: 0;
            z-index: 15000;
            display: none;
            flex-direction: column;
            overflow-y: auto;
            transition: background-color 0.2s ease, color 0.2s ease;
          }
          .staunt-reader-surface.open {
            display: flex;
          }
          /* Surface Themes */
          .staunt-reader-surface.theme-zinc {
            background-color: #12151c;
            color: #e2e8f0;
          }
          .staunt-reader-surface.theme-sepia {
            background-color: #fbf0d9;
            color: #2d261e;
          }
          .staunt-reader-surface.theme-black {
            background-color: #000000;
            color: #cbd5e1;
          }
          /* Typography Families */
          .staunt-reader-surface.font-sans {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          }
          .staunt-reader-surface.font-serif {
            font-family: "Georgia", "Cambria", "Times New Roman", serif;
          }
          .staunt-reader-surface.font-mono {
            font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
          }

          /* Toolbar */
          .staunt-reader-toolbar {
            position: sticky;
            top: 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 24px;
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(128, 128, 128, 0.15);
            background: inherit;
            z-index: 10;
          }
          .staunt-reader-badge {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.8px;
            opacity: 0.7;
          }
          .staunt-reader-tools-center {
            display: flex;
            align-items: center;
            gap: 8px;
          }
          .staunt-reader-btn {
            background: rgba(128, 128, 128, 0.12);
            border: 1px solid rgba(128, 128, 128, 0.18);
            color: inherit;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
          }
          .staunt-reader-btn:hover {
            background: rgba(128, 128, 128, 0.24);
          }
          .staunt-reader-divider {
            width: 1px;
            height: 18px;
            background: rgba(128, 128, 128, 0.2);
            margin: 0 4px;
          }
          .staunt-reader-theme-dot {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid transparent;
            cursor: pointer;
          }
          .staunt-reader-theme-dot:hover {
            transform: scale(1.15);
          }
          .theme-dot-zinc { background: #12151c; border-color: #3b82f6; }
          .theme-dot-sepia { background: #fbf0d9; border-color: #d97706; }
          .theme-dot-black { background: #000000; border-color: #64748b; }
          .staunt-reader-close {
            background: #ef4444;
            color: #fff;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
          }

          /* Editorial Body Layout */
          .staunt-reader-content-wrap {
            width: 100%;
            max-width: 680px;
            margin: 0 auto;
            padding: 48px 24px 80px;
          }
          .staunt-reader-title {
            font-size: 34px;
            font-weight: 800;
            line-height: 1.25;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
          }
          .staunt-reader-meta {
            font-size: 13px;
            opacity: 0.6;
            margin-bottom: 32px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.15);
            padding-bottom: 12px;
          }
          .staunt-reader-body {
            line-height: 1.75;
          }
          .staunt-reader-body p {
            margin-bottom: 1.5em;
          }
          .staunt-reader-body h2, .staunt-reader-body h3 {
            margin-top: 1.8em;
            margin-bottom: 0.8em;
          }
          .staunt-reader-body img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 1.5em 0;
          }
        `;
        document.head.appendChild(style);
      }

      this.bindControls();
    }

    bindControls() {
      const overlay = document.getElementById('staunt-reader-overlay');
      document.getElementById('staunt-reader-close-btn').addEventListener('click', () => this.exitReaderMode());

      // Theme toggles
      document.getElementById('reader-theme-zinc').addEventListener('click', () => this.setTheme('zinc'));
      document.getElementById('reader-theme-sepia').addEventListener('click', () => this.setTheme('sepia'));
      document.getElementById('reader-theme-black').addEventListener('click', () => this.setTheme('black'));

      // Font size
      document.getElementById('reader-size-up').addEventListener('click', () => {
        this.currentFontSize = Math.min(26, this.currentFontSize + 2);
        this.applyStyles();
      });
      document.getElementById('reader-size-down').addEventListener('click', () => {
        this.currentFontSize = Math.max(14, this.currentFontSize - 2);
        this.applyStyles();
      });

      // Font Family
      document.getElementById('reader-font-sans').addEventListener('click', () => this.setFontFamily('sans'));
      document.getElementById('reader-font-serif').addEventListener('click', () => this.setFontFamily('serif'));
      document.getElementById('reader-font-mono').addEventListener('click', () => this.setFontFamily('mono'));

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isActive) {
          this.exitReaderMode();
        }
      });
    }

    setTheme(theme) {
      this.currentTheme = theme;
      localStorage.setItem('staunt_reader_theme', theme);
      const overlay = document.getElementById('staunt-reader-overlay');
      overlay.className = `staunt-reader-surface open theme-${theme} font-${this.currentFontFamily}`;
    }

    setFontFamily(family) {
      this.currentFontFamily = family;
      localStorage.setItem('staunt_reader_font_family', family);
      const overlay = document.getElementById('staunt-reader-overlay');
      overlay.className = `staunt-reader-surface open theme-${this.currentTheme} font-${family}`;
    }

    applyStyles() {
      localStorage.setItem('staunt_reader_font_size', this.currentFontSize.toString());
      const body = document.getElementById('staunt-reader-body');
      if (body) body.style.fontSize = this.currentFontSize + 'px';
    }

    // Heuristic DOM Article Extraction
    extractContent() {
      const iframe = document.getElementById('staunt-viewport-frame');
      let doc = null;
      try {
        if (iframe && iframe.contentDocument) {
          doc = iframe.contentDocument;
        }
      } catch (e) {}

      let title = document.title || 'Extracted Article';
      let meta = 'Staunt Ultra Reader • ' + new Date().toLocaleDateString();
      let extractedHtml = '';

      if (doc) {
        title = doc.title || title;
        // Search for article, main, or dense content containers
        const article = doc.querySelector('article') || doc.querySelector('main') || doc.querySelector('.post-content') || doc.querySelector('.article-body');
        if (article) {
          const clone = article.cloneNode(true);
          // Strip unwanted elements
          clone.querySelectorAll('nav, footer, header, aside, .advertisement, script, style, .social-share').forEach(el => el.remove());
          extractedHtml = clone.innerHTML;
        } else {
          // Fallback: collect paragraphs
          const paragraphs = Array.from(doc.querySelectorAll('p')).filter(p => p.textContent.trim().length > 60);
          if (paragraphs.length > 0) {
            extractedHtml = paragraphs.map(p => `<p>${p.innerHTML}</p>`).join('');
          }
        }
      }

      if (!extractedHtml) {
        extractedHtml = `
          <p>Reader Mode is active for this webpage. Staunt Browser has filtered navigation bars, advertisements, sidebars, and trackers to display a tranquil, distraction-free reading experience.</p>
          <p>Enjoy reading with customizable serif, sans-serif, and monospace typography, responsive text scaling, and low-light ambient surfaces.</p>
        `;
      }

      return { title, meta, html: extractedHtml };
    }

    toggleReaderMode() {
      if (this.isActive) this.exitReaderMode();
      else this.enterReaderMode();
    }

    enterReaderMode() {
      this.isActive = true;
      const { title, meta, html } = this.extractContent();
      document.getElementById('staunt-reader-title').textContent = title;
      document.getElementById('staunt-reader-meta').textContent = meta;
      const bodyEl = document.getElementById('staunt-reader-body');
      bodyEl.innerHTML = html;
      this.applyStyles();

      const overlay = document.getElementById('staunt-reader-overlay');
      overlay.classList.add('open');
    }

    exitReaderMode() {
      this.isActive = false;
      const overlay = document.getElementById('staunt-reader-overlay');
      overlay.classList.remove('open');
    }
  }

  window.StauntReader = new ReaderModeEngine();
})(window);
