/**
 * StudyMate AI — Core App Utilities
 * Shared functions used across all pages.
 */

// If frontend is accessed from a different port (e.g. 5500 via http.server) or file://,
// route API requests to the FastAPI backend on 127.0.0.1:8000.
const API_BASE = (() => {
  if (typeof window !== 'undefined' && window.location) {
    const { protocol, port } = window.location;
    if (protocol === 'file:' || (port && port !== '8000')) {
      return 'http://127.0.0.1:8000/api';
    }
  }
  return '/api';
})();

// ============================================================
// API Helper
// ============================================================

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = { ...options };

  // Setup headers safely without mutating shared objects
  if (config.body instanceof FormData) {
    const headers = { ...(config.headers || {}) };
    delete headers['Content-Type'];
    delete headers['content-type'];
    if (Object.keys(headers).length > 0) {
      config.headers = headers;
    } else {
      delete config.headers;
    }
  } else {
    config.headers = {
      'Content-Type': 'application/json',
      ...(config.headers || {}),
    };
    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }
  }

  let response;
  try {
    response = await fetch(url, config);
  } catch (networkErr) {
    console.error(`[API Network Error] ${config.method || 'GET'} ${url}:`, networkErr);
    const err = new Error(
      `Cannot connect to backend server at ${API_BASE}. Ensure the FastAPI server is running on http://127.0.0.1:8000.`
    );
    err.isNetworkError = true;
    throw err;
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = { detail: `HTTP ${response.status}: Non-JSON server response` };
  }

  if (!response.ok) {
    let msg = data.detail || `Server error (${response.status})`;
    if (typeof msg !== 'string') {
      try { msg = JSON.stringify(msg); } catch { msg = `HTTP ${response.status}`; }
    }
    const err = new Error(msg);
    err.status = response.status;
    err.data = data;
    throw err;
  }

  return data;
}

// ============================================================
// Toast Notifications
// ============================================================

function initToasts() {
  if (!document.querySelector('.toast-container')) {
    const container = document.createElement('div');
    container.className = 'toast-container';
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
}

function showToast(message, type = 'info', duration = 4000) {
  initToasts();
  const container = document.getElementById('toast-container');

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'fadeIn 0.2s ease reverse';
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

// ============================================================
// Loading Helpers
// ============================================================

function setLoading(btnEl, isLoading, loadingText = 'Loading…') {
  if (!btnEl) return;
  if (isLoading) {
    btnEl.dataset.originalText = btnEl.innerHTML;
    btnEl.innerHTML = `<span class="spinner"></span> ${loadingText}`;
    btnEl.disabled = true;
  } else {
    btnEl.innerHTML = btnEl.dataset.originalText || btnEl.innerHTML;
    btnEl.disabled = false;
  }
}

function showLoadingOverlay(containerId, message = 'Loading…') {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="loading-overlay">
      <div class="spinner" style="width:32px;height:32px;border-width:3px;"></div>
      <span>${message}</span>
    </div>`;
}

function showEmptyState(containerId, icon, title, subtitle, actionHtml = '') {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">${icon}</div>
      <div class="empty-title">${title}</div>
      <div class="empty-subtitle">${subtitle}</div>
      ${actionHtml ? `<div class="mt-4">${actionHtml}</div>` : ''}
    </div>`;
}

// ============================================================
// Format Helpers
// ============================================================

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatDateTime(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function fileTypeIcon(type) {
  const icons = { pdf: '📕', docx: '📘', txt: '📄' };
  return icons[type] || '📄';
}

function difficultyBadge(difficulty) {
  const map = { easy: 'badge-green', medium: 'badge-amber', hard: 'badge-rose' };
  return `<span class="badge ${map[difficulty] || 'badge-indigo'}">${difficulty}</span>`;
}

function scoreColor(pct) {
  if (pct >= 80) return 'var(--accent-emerald)';
  if (pct >= 60) return 'var(--accent-amber)';
  return 'var(--accent-rose)';
}

// ============================================================
// Active Nav Highlighting
// ============================================================

function highlightActiveNav() {
  const current = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(item => {
    const href = item.getAttribute('href') || '';
    if (href && current.endsWith(href)) {
      item.classList.add('active');
    }
  });
}

document.addEventListener('DOMContentLoaded', highlightActiveNav);
