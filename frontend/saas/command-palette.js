/**
 * STAUNT BROWSER ULTRA: ARC-STYLE OMNIPRESENT COMMAND PALETTE
 * File: command-palette.js
 * Specification: Zero-Mock, Global Ctrl+K / Cmd+K Spotlight Modal & Fuzzy Actions Engine
 */

(function(window) {
  'use strict';

  class CommandPalette {
    constructor() {
      this.isOpen = false;
      this.selectedIndex = 0;
      this.currentResults = [];
      this.builtInActions = [
        { id: 'new_tab', title: 'Open New Tab', shortcut: 'Ctrl+T', category: 'Browser Action', action: () => window.createNewTab && window.createNewTab() },
        { id: 'toggle_shield', title: 'Toggle Ad & Tracker Shield', shortcut: 'Alt+S', category: 'Privacy', action: () => window.StauntShield && window.StauntShield.toggleShield() },
        { id: 'reader_mode', title: 'Toggle Safari Reader Mode', shortcut: 'Alt+R', category: 'Page View', action: () => window.StauntReader && window.StauntReader.toggleReaderMode() },
        { id: 'history', title: 'Open Browsing History', shortcut: 'Ctrl+H', category: 'Navigation', action: () => document.getElementById('staunt-btn-history')?.click() },
        { id: 'bookmarks', title: 'Open Bookmarks Manager', shortcut: 'Ctrl+B', category: 'Navigation', action: () => document.getElementById('staunt-btn-bookmarks')?.click() },
        { id: 'downloads', title: 'Open Downloads Manager', shortcut: 'Ctrl+J', category: 'Tools', action: () => document.getElementById('staunt-btn-downloads')?.click() },
        { id: 'clear_cache', title: 'Clear Browser Cache & Reset', shortcut: '', category: 'Maintenance', action: () => { localStorage.clear(); location.reload(); } }
      ];

      this.injectDOM();
      this.bindEvents();
    }

    injectDOM() {
      if (document.getElementById('staunt-command-spotlight')) return;

      const overlay = document.createElement('div');
      overlay.id = 'staunt-command-spotlight';
      overlay.className = 'staunt-spotlight-overlay';
      overlay.innerHTML = `
        <div class="staunt-spotlight-card">
          <div class="staunt-spotlight-input-row">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" class="staunt-spotlight-icon">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input type="text" id="staunt-spotlight-input" placeholder="Type a command, search open tabs, or type a URL..." autocomplete="off" spellcheck="false" />
            <span class="staunt-spotlight-esc">ESC</span>
          </div>
          <div class="staunt-spotlight-results" id="staunt-spotlight-results"></div>
          <div class="staunt-spotlight-footer">
            <span><strong>↑↓</strong> Navigate</span>
            <span><strong>↵</strong> Select</span>
            <span><strong>ESC</strong> Close</span>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);

      // Add spotlight dynamic styles if not already present
      if (!document.getElementById('staunt-spotlight-styles')) {
        const style = document.createElement('style');
        style.id = 'staunt-spotlight-styles';
        style.textContent = `
          .staunt-spotlight-overlay {
            position: fixed;
            inset: 0;
            background: rgba(4, 6, 12, 0.68);
            backdrop-filter: blur(28px) saturate(200%);
            -webkit-backdrop-filter: blur(28px) saturate(200%);
            display: none;
            align-items: flex-start;
            justify-content: center;
            padding-top: 15vh;
            z-index: 99999;
          }
          .staunt-spotlight-overlay.open {
            display: flex;
          }
          .staunt-spotlight-card {
            width: 100%;
            max-width: 640px;
            background: rgba(15, 22, 35, 0.88);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.75), 0 0 25px rgba(59, 130, 246, 0.2);
            overflow: hidden;
            animation: spotlightPop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
          }
          @keyframes spotlightPop {
            from { transform: scale(0.96) translateY(-10px); opacity: 0; }
            to { transform: scale(1) translateY(0); opacity: 1; }
          }
          .staunt-spotlight-input-row {
            display: flex;
            align-items: center;
            padding: 16px 20px;
            gap: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          }
          .staunt-spotlight-icon {
            width: 20px;
            height: 20px;
            color: #94a3b8;
          }
          #staunt-spotlight-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: #f8fafc;
            font-size: 16px;
            font-family: inherit;
          }
          .staunt-spotlight-esc {
            font-size: 11px;
            font-weight: 700;
            padding: 3px 7px;
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.08);
            color: #94a3b8;
            border: 1px solid rgba(255, 255, 255, 0.08);
          }
          .staunt-spotlight-results {
            max-height: 340px;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 4px;
          }
          .staunt-spotlight-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.12s ease;
          }
          .staunt-spotlight-item.selected, .staunt-spotlight-item:hover {
            background: rgba(59, 130, 246, 0.2);
            border-left: 3px solid #3b82f6;
          }
          .staunt-spotlight-item-left {
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .staunt-spotlight-item-title {
            font-size: 14px;
            color: #f8fafc;
            font-weight: 500;
          }
          .staunt-spotlight-item-cat {
            font-size: 11px;
            color: #94a3b8;
            background: rgba(255, 255, 255, 0.05);
            padding: 2px 8px;
            border-radius: 4px;
          }
          .staunt-spotlight-shortcut {
            font-size: 11.5px;
            color: #64748b;
            font-family: monospace;
          }
          .staunt-spotlight-footer {
            display: flex;
            gap: 16px;
            padding: 10px 20px;
            background: rgba(0, 0, 0, 0.25);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 11.5px;
            color: #64748b;
          }
          .staunt-spotlight-footer strong {
            color: #94a3b8;
          }
        `;
        document.head.appendChild(style);
      }
    }

    bindEvents() {
      const overlay = document.getElementById('staunt-command-spotlight');
      const input = document.getElementById('staunt-spotlight-input');

      // Global Keybinding Trigger (Ctrl + K / Cmd + K)
      window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
          e.preventDefault();
          this.toggle();
        } else if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });

      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) this.close();
      });

      input.addEventListener('input', () => {
        this.filterResults(input.value.trim());
      });

      input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this.moveSelection(1);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.moveSelection(-1);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          this.dispatchSelection();
        }
      });
    }

    toggle() {
      if (this.isOpen) this.close();
      else this.open();
    }

    open() {
      this.isOpen = true;
      const overlay = document.getElementById('staunt-command-spotlight');
      const input = document.getElementById('staunt-spotlight-input');
      overlay.classList.add('open');
      input.value = '';
      input.focus();
      this.filterResults('');
    }

    close() {
      this.isOpen = false;
      const overlay = document.getElementById('staunt-command-spotlight');
      overlay.classList.remove('open');
    }

    filterResults(query) {
      const q = query.toLowerCase();
      let results = [];

      // 1. Match Open Tabs
      if (window.tabs && Array.isArray(window.tabs)) {
        window.tabs.forEach(tab => {
          if (!q || tab.title.toLowerCase().includes(q) || (tab.url && tab.url.toLowerCase().includes(q))) {
            results.push({
              id: 'tab_' + tab.id,
              title: `Jump to Tab: ${tab.title}`,
              category: 'Open Tab',
              shortcut: '',
              action: () => window.switchTab && window.switchTab(tab.id)
            });
          }
        });
      }

      // 2. Match Built-in Actions
      this.builtInActions.forEach(action => {
        if (!q || action.title.toLowerCase().includes(q) || action.category.toLowerCase().includes(q)) {
          results.push(action);
        }
      });

      // 3. Fallback: If looks like URL or Search
      if (q && results.length === 0) {
        results.push({
          id: 'navigate',
          title: `Navigate to: "${query}"`,
          category: 'Web Navigation',
          shortcut: 'Enter',
          action: () => window.navigateToUrl && window.navigateToUrl(query)
        });
      }

      this.currentResults = results;
      this.selectedIndex = 0;
      this.renderResults();
    }

    renderResults() {
      const container = document.getElementById('staunt-spotlight-results');
      container.innerHTML = '';

      if (this.currentResults.length === 0) {
        container.innerHTML = '<div style="padding: 24px; text-align: center; color: #64748b; font-size: 13px;">No matching commands found</div>';
        return;
      }

      this.currentResults.forEach((res, idx) => {
        const item = document.createElement('div');
        item.className = 'staunt-spotlight-item' + (idx === this.selectedIndex ? ' selected' : '');
        item.innerHTML = `
          <div class="staunt-spotlight-item-left">
            <span class="staunt-spotlight-item-title">${this.escape(res.title)}</span>
            <span class="staunt-spotlight-item-cat">${res.category}</span>
          </div>
          ${res.shortcut ? `<span class="staunt-spotlight-shortcut">${res.shortcut}</span>` : ''}
        `;
        item.addEventListener('click', () => {
          this.selectedIndex = idx;
          this.dispatchSelection();
        });
        container.appendChild(item);
      });
    }

    moveSelection(delta) {
      if (this.currentResults.length === 0) return;
      this.selectedIndex = (this.selectedIndex + delta + this.currentResults.length) % this.currentResults.length;
      this.renderResults();
      const container = document.getElementById('staunt-spotlight-results');
      const selectedEl = container.children[this.selectedIndex];
      if (selectedEl) selectedEl.scrollIntoView({ block: 'nearest' });
    }

    dispatchSelection() {
      const chosen = this.currentResults[this.selectedIndex];
      if (chosen && typeof chosen.action === 'function') {
        this.close();
        chosen.action();
      }
    }

    escape(str) {
      return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
  }

  window.StauntCommandPalette = new CommandPalette();
})(window);
