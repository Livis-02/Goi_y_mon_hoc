/**
 * app-core.js — Module nhất quán cho toàn bộ EduGuide frontend.
 *
 * Mục tiêu:
 *   1. UI/UX nhất quán giữa các trang (toast, modal, loading, error).
 *   2. Web app mượt — caching, dedup, prefetch, debounce.
 *
 * Cách dùng:
 *   <script src="app-core.js" defer></script>
 *   App.api('/foo')     →  { ok, status, data }
 *   App.toast('Done')   →  toast top-right
 *   App.modal.confirm('Xoá?')  →  Promise<boolean>
 *
 * Backward compat:
 *   window.callApi → App.api
 *   window.toast   → App.toast
 *   window.showToast → App.toast
 */
(function () {
  'use strict';

  // ─────────────────────────────────────────────────────────────────────────
  // Config
  // ─────────────────────────────────────────────────────────────────────────
  const API_BASE = (typeof window.__API_BASE === 'string' && window.__API_BASE)
    || (typeof window.API_BASE === 'string' && window.API_BASE)
    || 'http://localhost:8000';

  const DEFAULT_TIMEOUT_MS = 30000;
  const CACHE_TTL_MS = 5 * 60 * 1000;   // stale-while-revalidate window

  // ─────────────────────────────────────────────────────────────────────────
  // Internal state
  // ─────────────────────────────────────────────────────────────────────────
  const _inflight = new Map();   // path → Promise (request dedup)
  const _cache    = new Map();   // path → { ts, data, status }

  function _token() {
    return localStorage.getItem('access_token') || '';
  }

  function _authHeader(extra = {}) {
    const t = _token();
    return t ? { Authorization: `Bearer ${t}`, ...extra } : { ...extra };
  }

  function _is401Redirect() {
    // Tránh redirect loop: nếu đã ở login page rồi thì không redirect.
    const here = (location.pathname || '').toLowerCase();
    return !(here.endsWith('/index.html') || here.endsWith('/index') ||
             here.endsWith('/reset-password.html') || here.endsWith('/landing.html') ||
             here === '/' || here.endsWith('/'));
  }

  // ─────────────────────────────────────────────────────────────────────────
  // App.api(path, opts) — unified fetch wrapper
  // ─────────────────────────────────────────────────────────────────────────
  /**
   * Fetch wrapper với auth, timeout, dedup, cache (cho GET).
   *
   * @param {string} path     — đường dẫn (vd '/auth/me') hoặc URL đầy đủ
   * @param {object} opts     — fetch options + EduGuide flags:
   *   - headers              : extra headers
   *   - timeoutMs            : default 30000
   *   - cache                : true → stale-while-revalidate (chỉ GET)
   *   - dedup                : true (default cho GET) → share in-flight promise
   *   - signal               : AbortSignal
   * @returns {Promise<{ok, status, data, error?}>}
   */
  async function api(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const isGet = method === 'GET';
    const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
    const cacheKey = isGet ? url : null;
    const useCache = opts.cache === true && isGet;
    const useDedup = opts.dedup !== false && isGet;

    // 1. Cache hit (stale-while-revalidate)
    if (useCache && _cache.has(cacheKey)) {
      const cached = _cache.get(cacheKey);
      if (Date.now() - cached.ts < CACHE_TTL_MS) {
        // Return cached → revalidate in background nếu sắp hết hạn
        if (Date.now() - cached.ts > CACHE_TTL_MS / 2) {
          setTimeout(() => api(path, { ...opts, cache: false }), 0);
        }
        return { ok: true, status: cached.status, data: cached.data, _fromCache: true };
      }
    }

    // 2. Dedup: share in-flight promise
    if (useDedup && _inflight.has(cacheKey)) {
      return _inflight.get(cacheKey);
    }

    const promise = _doFetch(url, opts, method, isGet, cacheKey, useCache);
    if (useDedup) _inflight.set(cacheKey, promise);
    try {
      return await promise;
    } finally {
      if (useDedup) _inflight.delete(cacheKey);
    }
  }

  async function _doFetch(url, opts, method, isGet, cacheKey, useCache) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs || DEFAULT_TIMEOUT_MS);
    const headers = { ..._authHeader(opts.headers || {}) };
    // Nếu body là object thuần → tự stringify + set Content-Type
    let body = opts.body;
    if (body && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof Blob)) {
      body = JSON.stringify(body);
      if (!headers['Content-Type']) headers['Content-Type'] = 'application/json';
    }

    try {
      const res = await fetch(url, {
        method,
        headers,
        body,
        signal: opts.signal || ctrl.signal,
      });
      clearTimeout(timer);

      // 401 → redirect login (trừ khi đang ở login page)
      if (res.status === 401 && _is401Redirect()) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('sb_user');
        location.replace('index.html');
        return { ok: false, status: 401, data: { detail: 'Session expired' } };
      }

      let data;
      try { data = await res.json(); } catch { data = {}; }
      const result = { ok: res.ok, status: res.status, data };

      // Cache GET success
      if (useCache && isGet && res.ok) {
        _cache.set(cacheKey, { ts: Date.now(), data, status: res.status });
      }
      return result;
    } catch (err) {
      clearTimeout(timer);
      const isTimeout = err && err.name === 'AbortError';
      return {
        ok: false,
        status: 0,
        data: { detail: isTimeout ? 'Yêu cầu quá lâu, đã hết thời gian chờ.' : 'Không thể kết nối tới máy chủ.' },
        error: err,
      };
    }
  }

  /** Invalidate cache cho 1 path hoặc tất cả (khi POST/PATCH) */
  function invalidateCache(pathOrPrefix) {
    if (!pathOrPrefix) {
      _cache.clear();
      return;
    }
    const url = pathOrPrefix.startsWith('http') ? pathOrPrefix : `${API_BASE}${pathOrPrefix}`;
    for (const key of _cache.keys()) {
      if (key.startsWith(url)) _cache.delete(key);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // App.toast — unified toast
  // ─────────────────────────────────────────────────────────────────────────
  /**
   * Hiện toast nhất quán.
   * @param {string} msg — text hoặc HTML (auto-detect: bắt đầu bằng '<' = HTML)
   * @param {string} type — 'success' | 'error' | 'warning' | 'info'
   *                       (compat: true → success, false → error)
   * @param {number} duration — ms (default 3000, 0 = không tự đóng)
   * @param {object} options — { html: true } để force HTML rendering
   */
  function toast(msg, type = 'info', duration = 3000, options = {}) {
    // Backward compat: cũ dùng (msg, ok=true)
    if (type === true)  type = 'success';
    if (type === false) type = 'error';
    if (type === 'ok')  type = 'success';

    // Auto-detect HTML: nếu msg chứa tag → render as HTML (cho phép button/link/strong)
    // Page cũ truyền HTML (vd toast cũ admin có <strong>, <button onclick>) vẫn work.
    const msgStr = msg == null ? '' : String(msg);
    const isHtml = options.html === true || /<[a-zA-Z][^>]*>/.test(msgStr);

    let host = document.getElementById('app-toast-host');
    if (!host) {
      host = document.createElement('div');
      host.id = 'app-toast-host';
      host.className = 'fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none';
      document.body.appendChild(host);
    }

    const palette = {
      success: 'bg-emerald-600 text-white border-emerald-700',
      error:   'bg-rose-600 text-white border-rose-700',
      warning: 'bg-amber-500 text-white border-amber-600',
      info:    'bg-slate-800 text-white border-slate-900',
    };
    const icon = {
      success: 'check_circle',
      error:   'error',
      warning: 'warning',
      info:    'info',
    };

    const t = document.createElement('div');
    t.className = `app-toast pointer-events-auto flex items-start gap-2 min-w-[260px] max-w-[420px] px-4 py-3 rounded-xl shadow-lg border text-sm font-medium ${palette[type] || palette.info}`;
    t.style.transform = 'translateX(120%)';
    t.style.opacity = '0';
    t.style.transition = 'transform .2s ease, opacity .2s ease';
    const content = isHtml ? msgStr : _escapeHtml(msgStr);
    t.innerHTML = `
      <span class="material-symbols-outlined text-base flex-shrink-0 mt-0.5" style="font-variation-settings:'FILL' 1">${icon[type] || icon.info}</span>
      <span class="flex-1 break-words">${content}</span>
      <button class="ml-2 opacity-80 hover:opacity-100 flex-shrink-0" aria-label="Đóng">
        <span class="material-symbols-outlined text-base">close</span>
      </button>
    `;
    host.appendChild(t);

    requestAnimationFrame(() => {
      t.style.transform = 'translateX(0)';
      t.style.opacity = '1';
    });

    const close = () => {
      t.style.transform = 'translateX(120%)';
      t.style.opacity = '0';
      setTimeout(() => t.remove(), 220);
    };
    t.querySelector('button').addEventListener('click', close);
    if (duration > 0) setTimeout(close, duration);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // App.modal — open / close / confirm
  // ─────────────────────────────────────────────────────────────────────────
  const modal = {
    open(idOrEl) {
      const el = typeof idOrEl === 'string' ? document.getElementById(idOrEl) : idOrEl;
      if (!el) return;
      el.classList.remove('hidden');
      el.classList.add('flex');
      // Focus first input
      setTimeout(() => {
        const f = el.querySelector('input,select,textarea,button');
        if (f) f.focus();
      }, 50);
    },
    close(idOrEl) {
      const el = typeof idOrEl === 'string' ? document.getElementById(idOrEl) : idOrEl;
      if (!el) return;
      el.classList.add('hidden');
      el.classList.remove('flex');
    },
    /** Promise-based confirm — replace native confirm() */
    confirm(message, opts = {}) {
      return new Promise((resolve) => {
        const okText = opts.okText || 'Đồng ý';
        const cancelText = opts.cancelText || 'Huỷ';
        const danger = !!opts.danger;
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black/50 z-[9998] flex items-center justify-center p-4';
        overlay.innerHTML = `
          <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm p-5 space-y-4">
            <p class="text-sm text-gray-800">${_escapeHtml(message)}</p>
            <div class="flex justify-end gap-2">
              <button data-act="cancel" class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">${_escapeHtml(cancelText)}</button>
              <button data-act="ok" class="px-4 py-2 text-sm text-white rounded-lg ${danger ? 'bg-rose-600 hover:bg-rose-700' : 'bg-emerald-600 hover:bg-emerald-700'}">${_escapeHtml(okText)}</button>
            </div>
          </div>
        `;
        document.body.appendChild(overlay);
        const cleanup = (val) => { overlay.remove(); resolve(val); };
        overlay.addEventListener('click', (e) => {
          if (e.target === overlay) cleanup(false);
        });
        overlay.querySelector('[data-act=ok]').addEventListener('click', () => cleanup(true));
        overlay.querySelector('[data-act=cancel]').addEventListener('click', () => cleanup(false));
        // Esc to cancel
        const onEsc = (e) => { if (e.key === 'Escape') { document.removeEventListener('keydown', onEsc); cleanup(false); } };
        document.addEventListener('keydown', onEsc);
      });
    },
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Loading + Empty + Error states (DOM helpers)
  // ─────────────────────────────────────────────────────────────────────────
  function showLoading(target, options = {}) {
    const el = typeof target === 'string' ? document.getElementById(target) : target;
    if (!el) return;
    const rows = options.rows || 3;
    let html = '<div class="space-y-3 p-4">';
    for (let i = 0; i < rows; i++) {
      html += '<div class="app-skeleton h-4 rounded w-full"></div>';
      html += '<div class="app-skeleton h-3 rounded w-3/4"></div>';
    }
    html += '</div>';
    el.innerHTML = html;
  }

  function showEmpty(target, msg = 'Không có dữ liệu', icon = 'inbox') {
    const el = typeof target === 'string' ? document.getElementById(target) : target;
    if (!el) return;
    el.innerHTML = `
      <div class="app-state-card flex flex-col items-center justify-center py-12 px-4 text-center">
        <span class="material-symbols-outlined text-5xl text-gray-400 mb-2">${icon}</span>
        <p class="text-sm text-gray-500">${_escapeHtml(msg)}</p>
      </div>
    `;
  }

  function showError(target, msg = 'Có lỗi xảy ra', retry) {
    const el = typeof target === 'string' ? document.getElementById(target) : target;
    if (!el) return;
    const retryBtn = retry
      ? `<button class="mt-3 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-bold" data-app-retry>Thử lại</button>`
      : '';
    el.innerHTML = `
      <div class="app-state-card flex flex-col items-center justify-center py-12 px-4 text-center">
        <span class="material-symbols-outlined text-5xl text-rose-500 mb-2">error</span>
        <p class="text-sm text-gray-700">${_escapeHtml(msg)}</p>
        ${retryBtn}
      </div>
    `;
    if (retry) {
      const btn = el.querySelector('[data-app-retry]');
      btn && btn.addEventListener('click', retry);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Utilities
  // ─────────────────────────────────────────────────────────────────────────
  function debounce(fn, delay = 300) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function throttle(fn, limit = 300) {
    let inThrottle = false;
    return function (...args) {
      if (!inThrottle) {
        fn.apply(this, args);
        inThrottle = true;
        setTimeout(() => { inThrottle = false; }, limit);
      }
    };
  }

  function _escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /** Extract user-facing error message from response data (handles nested detail). */
  function extractError(data) {
    if (!data) return 'Có lỗi xảy ra';
    if (typeof data === 'string') return data;
    if (typeof data.detail === 'string') return data.detail;
    if (data.detail && typeof data.detail === 'object') {
      if (typeof data.detail.message === 'string') return data.detail.message;
      try { return JSON.stringify(data.detail); } catch { /* ignore */ }
    }
    if (Array.isArray(data.detail)) {
      // Pydantic validation errors
      return data.detail.map(e => e.msg || e.message || JSON.stringify(e)).join('; ');
    }
    if (typeof data.message === 'string') return data.message;
    return 'Có lỗi xảy ra';
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Export
  // ─────────────────────────────────────────────────────────────────────────
  window.App = {
    api,
    invalidateCache,
    toast,
    modal,
    loading: { show: showLoading, hide: (t) => { const el = typeof t === 'string' ? document.getElementById(t) : t; if (el) el.innerHTML = ''; } },
    showEmpty,
    showError,
    debounce,
    throttle,
    extractError,
    escapeHtml: _escapeHtml,
    // Constants
    API_BASE,
    CACHE_TTL_MS,
  };

  // Backward compat shims — page cũ dùng tên callApi/toast/showToast/escHtml
  // sẽ tự động chuyển sang implementation chuẩn mà không phá code legacy.
  if (!window.callApi)   window.callApi = api;
  if (!window.toast)     window.toast = toast;
  if (!window.showToast) window.showToast = toast;
  if (!window.escHtml)   window.escHtml = _escapeHtml;
})();
