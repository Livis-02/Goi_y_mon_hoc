/**
 * utils.js — Shared UI helpers cho EduGuide.
 *
 * Cung cấp:
 *   - formatNumber(n)         → "1,500" với dấu phẩy thousands separator vi-VN
 *   - formatDate(input)       → relative ("6 giờ trước") nếu < 7 ngày, absolute sau đó
 *   - formatDateLong(input)   → đầy đủ ngày + giờ
 *   - showToastWithUndo(...)  → toast với button "Hoàn tác" client-side
 *   - showConfirmModal(...)   → modal confirm đẹp thay browser.confirm()
 *
 * Load BEFORE page-specific scripts:
 *   <script src="utils.js?v=1"></script>
 */
(function () {
  'use strict';

  // ─── 1. formatNumber ─────────────────────────────────────────────────────
  // 1500 → "1.500" (vi-VN dùng dấu chấm), 1.5 → "1,5"
  const _numFmt = new Intl.NumberFormat('vi-VN');
  window.formatNumber = function (n) {
    if (n == null || n === '' || isNaN(n)) return '—';
    return _numFmt.format(Number(n));
  };
  // formatNumber với min/max decimals (cho GPA 3.45)
  window.formatNumberFixed = function (n, digits = 2) {
    if (n == null || n === '' || isNaN(n)) return '—';
    return new Intl.NumberFormat('vi-VN', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(Number(n));
  };

  // ─── 2. formatDate ───────────────────────────────────────────────────────
  // Relative khi < 7 ngày, absolute khi ≥ 7 ngày
  window.formatDate = function (input) {
    if (!input) return '—';
    const d = new Date(input);
    if (isNaN(d.getTime())) return '—';
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'vừa xong';
    if (diff < 3600) return Math.floor(diff / 60) + ' phút trước';
    if (diff < 86400) return Math.floor(diff / 3600) + ' giờ trước';
    if (diff < 86400 * 2) return 'Hôm qua';
    if (diff < 86400 * 7) return Math.floor(diff / 86400) + ' ngày trước';
    return d.toLocaleDateString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  };
  window.formatDateLong = function (input) {
    if (!input) return '—';
    const d = new Date(input);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };
  // formatDateAuto: hiển thị relative + tooltip absolute on hover
  window.formatDateAuto = function (input) {
    if (!input) return '—';
    const rel = window.formatDate(input);
    const long = window.formatDateLong(input);
    return `<span title="${long}" class="cursor-help">${rel}</span>`;
  };

  // ─── 3. showToastWithUndo ────────────────────────────────────────────────
  // Toast với button "Hoàn tác" 5s trước khi tự dismiss.
  // onUndo callback gọi nếu user click "Hoàn tác". Hover → pause auto-dismiss.
  let _activeUndoToast = null;
  window.showToastWithUndo = function (message, onUndo, opts = {}) {
    const timeoutMs = opts.timeoutMs || 5000;
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'fixed top-5 right-5 z-[9999] flex flex-col gap-2 pointer-events-none';
      document.body.appendChild(container);
    }
    if (_activeUndoToast) {
      _activeUndoToast.remove();
      _activeUndoToast = null;
    }

    const toast = document.createElement('div');
    toast.className = 'pointer-events-auto text-sm font-medium px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 min-w-[300px] max-w-[420px]';
    toast.style.cssText = 'background: var(--text-primary); color: var(--surface); animation: __toastSlideIn .25s cubic-bezier(0.16, 1, 0.3, 1);';

    const messageSpan = document.createElement('span');
    messageSpan.className = 'flex-1';
    messageSpan.textContent = message;

    const undoBtn = document.createElement('button');
    undoBtn.className = 'font-bold hover:underline transition-colors flex-shrink-0 px-2';
    undoBtn.style.color = '#a5b4fc';  // light indigo on dark bg
    undoBtn.textContent = '↶ Hoàn tác';

    const closeBtn = document.createElement('button');
    closeBtn.className = 'opacity-50 hover:opacity-100 transition-opacity flex-shrink-0';
    closeBtn.title = 'Đóng';
    closeBtn.innerHTML = '<span class="material-symbols-outlined msym text-base">close</span>';

    toast.appendChild(messageSpan);
    toast.appendChild(undoBtn);
    toast.appendChild(closeBtn);
    container.appendChild(toast);
    _activeUndoToast = toast;

    let dismissed = false;
    let timeoutId;
    function dismiss() {
      if (dismissed) return;
      dismissed = true;
      toast.style.transition = 'opacity .2s, transform .2s';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px)';
      setTimeout(() => toast.remove(), 220);
      _activeUndoToast = null;
    }

    undoBtn.addEventListener('click', () => {
      try { if (typeof onUndo === 'function') onUndo(); }
      catch (e) { console.error('[showToastWithUndo] onUndo error:', e); }
      dismiss();
    });
    closeBtn.addEventListener('click', dismiss);

    timeoutId = setTimeout(dismiss, timeoutMs);
    toast.addEventListener('mouseenter', () => clearTimeout(timeoutId));
    toast.addEventListener('mouseleave', () => {
      if (!dismissed) timeoutId = setTimeout(dismiss, 2000);
    });
  };

  // ─── 4. showConfirmModal ─────────────────────────────────────────────────
  // Modal confirm đẹp thay browser.confirm() — Promise-based.
  // Trả về Promise<boolean>: true nếu user click confirm, false nếu cancel/close.
  window.showConfirmModal = function (opts = {}) {
    return new Promise((resolve) => {
      const {
        title = 'Xác nhận',
        message = '',
        confirmText = 'Xác nhận',
        cancelText = 'Huỷ',
        variant = 'default',  // 'default' | 'danger' | 'warning'
        icon,                 // optional material icon name
      } = opts;

      // Variant → icon + color
      const variantCfg = {
        default:  { icon: icon || 'help',     bg: 'bg-accent-soft',   text: 'text-accent',  btn: 'imsg-btn-primary' },
        danger:   { icon: icon || 'warning',  bg: 'bg-danger-soft',   text: 'text-danger',  btn: 'imsg-btn-danger' },
        warning:  { icon: icon || 'info',     bg: 'bg-warning-soft',  text: 'text-warning', btn: 'imsg-btn-warning' },
      };
      const cfg = variantCfg[variant] || variantCfg.default;

      const overlay = document.createElement('div');
      overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:16px;animation:__confirmFade .2s';

      const card = document.createElement('div');
      card.style.cssText = 'background:var(--surface);border:1px solid var(--border-default);border-radius:20px;box-shadow:0 25px 60px -12px rgba(15,23,42,0.30);max-width:420px;width:100%;animation:__confirmIn .25s cubic-bezier(0.16, 1, 0.3, 1)';

      // Body
      const body = document.createElement('div');
      body.style.cssText = 'padding:24px';
      body.innerHTML = `
        <div class="flex items-start gap-3 mb-4">
          <div class="${cfg.bg} w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0">
            <span class="material-symbols-outlined msym ${cfg.text} text-xl" style="font-variation-settings:'FILL' 1">${cfg.icon}</span>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="text-base font-bold text-text-primary mb-1.5 leading-snug">${_escHtml(title)}</h3>
            <p class="text-sm text-text-secondary leading-relaxed whitespace-pre-line">${_escHtml(message)}</p>
          </div>
        </div>
      `;

      // Footer (buttons)
      const footer = document.createElement('div');
      footer.style.cssText = 'display:flex;gap:8px;padding:12px 24px 20px;justify-content:flex-end';

      const cancelBtn = document.createElement('button');
      cancelBtn.textContent = cancelText;
      cancelBtn.style.cssText = 'padding:8px 18px;font-size:13px;font-weight:600;border-radius:10px;background:var(--surface-subtle);color:var(--text-secondary);border:1px solid var(--border-default);cursor:pointer;transition:all .12s';
      cancelBtn.addEventListener('mouseenter', () => cancelBtn.style.background = 'var(--surface-strong)');
      cancelBtn.addEventListener('mouseleave', () => cancelBtn.style.background = 'var(--surface-subtle)');

      const confirmBtn = document.createElement('button');
      confirmBtn.textContent = confirmText;
      const btnGrad = variant === 'danger' ? 'linear-gradient(135deg, var(--danger), #d44510)'
                    : variant === 'warning' ? 'linear-gradient(135deg, var(--warning), #d18000)'
                    : 'linear-gradient(135deg, var(--accent), var(--accent-hover))';
      confirmBtn.style.cssText = `padding:8px 18px;font-size:13px;font-weight:700;border-radius:10px;background:${btnGrad};color:#fff;border:0;cursor:pointer;transition:transform .12s, box-shadow .15s;box-shadow:0 1px 3px rgba(0,0,0,0.15)`;
      confirmBtn.addEventListener('mouseenter', () => { confirmBtn.style.transform = 'translateY(-1px)'; confirmBtn.style.boxShadow = '0 3px 8px rgba(0,0,0,0.25)'; });
      confirmBtn.addEventListener('mouseleave', () => { confirmBtn.style.transform = 'translateY(0)'; confirmBtn.style.boxShadow = '0 1px 3px rgba(0,0,0,0.15)'; });

      footer.appendChild(cancelBtn);
      footer.appendChild(confirmBtn);
      card.appendChild(body);
      card.appendChild(footer);
      overlay.appendChild(card);
      document.body.appendChild(overlay);

      function close(result) {
        overlay.style.animation = '__confirmFade .15s reverse';
        setTimeout(() => overlay.remove(), 150);
        resolve(result);
      }
      cancelBtn.addEventListener('click', () => close(false));
      confirmBtn.addEventListener('click', () => close(true));
      overlay.addEventListener('click', (e) => { if (e.target === overlay) close(false); });

      // ESC = cancel, Enter = confirm
      function onKey(e) {
        if (e.key === 'Escape') { document.removeEventListener('keydown', onKey); close(false); }
        else if (e.key === 'Enter') { document.removeEventListener('keydown', onKey); close(true); }
      }
      document.addEventListener('keydown', onKey);

      // Auto-focus confirm
      setTimeout(() => confirmBtn.focus(), 50);
    });
  };

  // ─── 5. __retryFetch (exponential backoff) ────────────────────────────────
  // Robust retry cho init fetches (vd /auth/me) khi backend cold start chậm.
  // Default: 5 retries với delay 400ms → 800ms → 1.6s → 3.2s → 6.4s (~12s tổng).
  window.__retryFetch = async function (fn, opts = {}) {
    const { retries = 5, baseMs = 400, factor = 2, maxMs = 8000, onAttempt } = opts;
    let lastErr;
    for (let i = 0; i <= retries; i++) {
      try {
        if (onAttempt) onAttempt(i);
        return await fn();
      } catch (e) {
        lastErr = e;
        if (i === retries) break;
        const delay = Math.min(baseMs * Math.pow(factor, i), maxMs);
        await new Promise(r => setTimeout(r, delay));
      }
    }
    throw lastErr;
  };

  // ─── 6. __waitFor (poll until condition true) ─────────────────────────────
  // Helper cho action handlers: đợi state ready trước khi proceed.
  // Trả về true nếu condition met trong timeoutMs, false nếu timeout.
  window.__waitFor = async function (condition, opts = {}) {
    const { timeoutMs = 5000, interval = 50 } = opts;
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try { if (condition()) return true; }
      catch (_) { /* condition throw → treat as not-met */ }
      await new Promise(r => setTimeout(r, interval));
    }
    return false;
  };

  // ─── 7. Init error banner ─────────────────────────────────────────────────
  // Hiện banner đỏ sticky top khi init fail hoàn toàn (sau retry).
  // User click "Thử lại" → reload page. Tránh trạng thái mơ hồ "đôi lúc work".
  let _initBanner = null;
  window.__showInitErrorBanner = function (message) {
    if (_initBanner) return;
    const bar = document.createElement('div');
    bar.id = '__initErrorBanner';
    bar.style.cssText = [
      'position:fixed', 'top:0', 'left:0', 'right:0',
      'z-index:99999',
      'padding:10px 16px',
      'background:linear-gradient(135deg, #cd3500, #d44510)',
      'color:#fff',
      'font-size:13px', 'font-weight:600',
      'display:flex', 'align-items:center', 'justify-content:center', 'gap:12px',
      'box-shadow:0 2px 8px rgba(205, 53, 0, 0.30)',
      'animation: __toastSlideIn .3s ease-out',
    ].join(';');
    bar.innerHTML = `
      <span class="material-symbols-outlined msym" style="font-size:18px">error</span>
      <span>${String(message || 'Không tải được dữ liệu. Vui lòng thử lại.').replace(/</g, '&lt;')}</span>
      <button onclick="location.reload()" style="padding:5px 14px;background:#fff;color:#cd3500;border:0;border-radius:8px;font-weight:700;font-size:12px;cursor:pointer">↻ Thử lại</button>
      <button onclick="document.getElementById('__initErrorBanner')?.remove();" style="padding:5px 8px;background:transparent;border:0;color:#fff;cursor:pointer;opacity:0.7" title="Đóng">
        <span class="material-symbols-outlined msym" style="font-size:16px">close</span>
      </button>
    `;
    document.body.appendChild(bar);
    _initBanner = bar;
  };

  // ─── 8. __withInit (defensive wrapper cho action handlers) ────────────────
  // Wrap async handler để check init state trước khi run. Nếu init chưa xong,
  // đợi tối đa timeoutMs. Nếu không xong → toast warning + abort.
  // Usage: button.onclick = __withInit(async () => { ... });
  window.__withInit = function (handlerFn, opts = {}) {
    const { timeoutMs = 5000, message = 'Hệ thống đang tải, vui lòng đợi...' } = opts;
    return async function (...args) {
      if (window.__initDone) return handlerFn.apply(this, args);
      // Block + wait
      const ok = await window.__waitFor(() => window.__initDone, { timeoutMs });
      if (!ok) {
        if (window.showToast) showToast(message, 'warning');
        else alert(message);
        return;
      }
      return handlerFn.apply(this, args);
    };
  };

  // ─── Inject keyframes one-time ────────────────────────────────────────────
  if (!document.getElementById('__utilsCss')) {
    const css = document.createElement('style');
    css.id = '__utilsCss';
    css.textContent = `
@keyframes __toastSlideIn {
  from { opacity: 0; transform: translateY(-12px) scale(0.95); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes __confirmFade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes __confirmIn {
  from { opacity: 0; transform: translateY(8px) scale(0.96); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
`;
    document.head.appendChild(css);
  }

  function _escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();
