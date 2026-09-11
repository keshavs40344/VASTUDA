/**
 * STAUNT BROWSER ULTRA: ZERO-KNOWLEDGE ENCRYPTED VAULT STORAGE ENGINE
 * File: vault-storage.js
 * Specification: Zero-Mock, WebCrypto AES-GCM 256-bit Key Derivation & Encrypted Export/Import
 */

(function(window) {
  'use strict';

  class EncryptedVault {
    constructor() {
      this.isLocked = true;
      this.cryptoKey = null;
      this.hasPassphrase = localStorage.getItem('staunt_vault_configured') === 'true';
    }

    // Derive 256-bit AES-GCM Key using PBKDF2 (100,000 Iterations)
    async deriveKey(passphrase, salt) {
      const enc = new TextEncoder();
      const baseKey = await window.crypto.subtle.importKey(
        'raw',
        enc.encode(passphrase),
        { name: 'PBKDF2' },
        false,
        ['deriveKey']
      );

      return await window.crypto.subtle.deriveKey(
        {
          name: 'PBKDF2',
          salt: salt,
          iterations: 100000,
          hash: 'SHA-256'
        },
        baseKey,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
      );
    }

    // Configure a new master passphrase
    async setupPassphrase(passphrase) {
      if (!passphrase || passphrase.length < 6) {
        throw new Error('Master passphrase must be at least 6 characters long.');
      }
      const salt = window.crypto.getRandomValues(new Uint8Array(16));
      this.cryptoKey = await this.deriveKey(passphrase, salt);
      this.isLocked = false;
      this.hasPassphrase = true;

      // Store salt and verification token
      const saltHex = Array.from(salt).map(b => b.toString(16).padStart(2, '0')).join('');
      localStorage.setItem('staunt_vault_salt', saltHex);
      localStorage.setItem('staunt_vault_configured', 'true');

      // Create a test verification token to validate passwords on unlock
      const verificationPayload = await this.encryptText('STAUNT_VAULT_VERIFY_OK');
      localStorage.setItem('staunt_vault_token', JSON.stringify(verificationPayload));
      return true;
    }

    // Unlock vault using passphrase
    async unlock(passphrase) {
      const saltHex = localStorage.getItem('staunt_vault_salt');
      const tokenRaw = localStorage.getItem('staunt_vault_token');
      if (!saltHex || !tokenRaw) {
        throw new Error('No vault configured yet.');
      }

      const salt = new Uint8Array(saltHex.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
      const candidateKey = await this.deriveKey(passphrase, salt);

      try {
        const token = JSON.parse(tokenRaw);
        const decrypted = await this.decryptText(token, candidateKey);
        if (decrypted === 'STAUNT_VAULT_VERIFY_OK') {
          this.cryptoKey = candidateKey;
          this.isLocked = false;
          return true;
        }
      } catch (e) {
        throw new Error('Incorrect master passphrase.');
      }
      throw new Error('Incorrect master passphrase.');
    }

    lock() {
      this.cryptoKey = null;
      this.isLocked = true;
    }

    // Encrypt Plain Text to AES-GCM (Ciphertext + IV)
    async encryptText(plainText) {
      if (!this.cryptoKey) throw new Error('Vault is locked. Unlock before encrypting.');
      const enc = new TextEncoder();
      const iv = window.crypto.getRandomValues(new Uint8Array(12));
      const ciphertext = await window.crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: iv },
        this.cryptoKey,
        enc.encode(plainText)
      );

      return {
        iv: Array.from(iv).map(b => b.toString(16).padStart(2, '0')).join(''),
        data: Array.from(new Uint8Array(ciphertext)).map(b => b.toString(16).padStart(2, '0')).join('')
      };
    }

    // Decrypt AES-GCM Payload to Plain Text
    async decryptText(payload, overrideKey = null) {
      const key = overrideKey || this.cryptoKey;
      if (!key) throw new Error('Vault is locked. Unlock before decrypting.');

      const iv = new Uint8Array(payload.iv.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
      const data = new Uint8Array(payload.data.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));

      const decrypted = await window.crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        data
      );

      return new TextDecoder().decode(decrypted);
    }

    // One-Click Encrypted Backup Export
    async exportBackup() {
      const rawData = {
        shortcuts: localStorage.getItem('staunt_shortcuts') || '[]',
        bookmarks: localStorage.getItem('staunt_bookmarks') || '[]',
        history: localStorage.getItem('staunt_history') || '[]',
        sessionTabs: localStorage.getItem('staunt_session_tabs') || '[]',
        exportDate: new Date().toISOString()
      };

      const plainJson = JSON.stringify(rawData);
      let payload = null;

      if (!this.isLocked && this.cryptoKey) {
        payload = {
          encrypted: true,
          vault: await this.encryptText(plainJson)
        };
      } else {
        payload = {
          encrypted: false,
          data: rawData
        };
      }

      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Staunt-Backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }

    // Encrypted Import Recovery Pipeline
    async importBackup(jsonString, passphrase = null) {
      const backup = JSON.parse(jsonString);
      let data = null;

      if (backup.encrypted) {
        if (!passphrase && this.isLocked) {
          throw new Error('Encrypted backup requires master passphrase to import.');
        }
        const key = this.cryptoKey || (await this.deriveKey(passphrase, new Uint8Array(localStorage.getItem('staunt_vault_salt').match(/.{1,2}/g).map(b => parseInt(b, 16)))));
        const decryptedJson = await this.decryptText(backup.vault, key);
        data = JSON.parse(decryptedJson);
      } else {
        data = backup.data;
      }

      if (data) {
        if (data.shortcuts) localStorage.setItem('staunt_shortcuts', data.shortcuts);
        if (data.bookmarks) localStorage.setItem('staunt_bookmarks', data.bookmarks);
        if (data.history) localStorage.setItem('staunt_history', data.history);
        if (data.sessionTabs) localStorage.setItem('staunt_session_tabs', data.sessionTabs);
        return true;
      }
      return false;
    }
  }

  window.StauntVault = new EncryptedVault();
})(window);
