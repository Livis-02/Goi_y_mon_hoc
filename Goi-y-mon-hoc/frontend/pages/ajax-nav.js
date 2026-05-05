/**
 * ajax-nav.js — DISABLED ở v16 (revert to MPA, fix dứt điểm "phải reload" bug).
 *
 * History:
 *   v6: disabled lần đầu (state leak)
 *   v7: re-enabled với listener cleanup
 *   v14-v15: hardened với init recovery + cold-start retry
 *   v16: disabled dứt điểm — chuyển sang MPA full reload.
 *
 * Lý do v16: SPA simulation gây class of bugs (listener accumulation, state
 * leak, init race, script re-execution edge cases) — patch theo symptom không
 * dứt điểm. MPA full reload: mỗi page process mới, zero race condition.
 *
 * GIỮ:
 *   - Overlay show on initial load (block click trong cold-start init race)
 *   - Listener tracking patches (no-op vì cleanup không chạy, harmless)
 *   - Function definitions navigation (dead code, kept for rollback)
 *
 * BÙ bằng:
 *   - nav-prefetch.js: <link rel="prefetch"> cho sidebar (HTML cached trước click)
 *   - View Transitions API trong design-system.css (fade smooth giữa page)
 *
 * Rollback: xóa block "MPA MODE — v16" (early return) ở giữa file.
 */
(function () {
  'use strict';
  if (!window.fetch || !window.history.pushState || !window.DOMParser) return;

  // Skip SPA behavior on auth screens + admin (admin có sidebar riêng + tabs trong cùng page)
  const PATH = (location.pathname.split('/').pop() || '').toLowerCase();
  if (PATH === 'index.html' || PATH === 'reset-password.html' || PATH === '' || PATH === 'admin.html') return;

  const CACHE = new Map();  // url -> { packet, ts } (60s TTL — fresh enough for dev, snappy for prod)
  const CACHE_TTL_MS = 60 * 1000;

  // ────────────────────────────────────────────────────────────────────────
  // State leak prevention — track timers + fetches của page hiện tại,
  // clear/abort hết khi navigate sang page khác.
  // ────────────────────────────────────────────────────────────────────────
  const _activeTimers = new Set();
  const _activeIntervals = new Set();
  const _activeFetches = new Set();

  // Patch setInterval/setTimeout để track. Bật tracking ngay từ đầu để timers
  // của trang đầu tiên cũng được clear khi navigate. ajax-nav tự dùng _origSet*
  // để tránh tự clear timer của chính nó.
  let _trackingEnabled = true;
  const _origSetTimeout = window.setTimeout.bind(window);
  const _origSetInterval = window.setInterval.bind(window);
  const _origClearTimeout = window.clearTimeout.bind(window);
  const _origClearInterval = window.clearInterval.bind(window);
  const _origFetch = window.fetch.bind(window);

  // Patch tối thiểu: track id, KHÔNG wrap callback fn (tránh thay đổi
  // semantic của user code — quan trọng cho async functions giữ this binding).
  window.setTimeout = function () {
    const id = _origSetTimeout.apply(window, arguments);
    if (_trackingEnabled) _activeTimers.add(id);
    return id;
  };
  window.setInterval = function () {
    const id = _origSetInterval.apply(window, arguments);
    if (_trackingEnabled) _activeIntervals.add(id);
    return id;
  };
  window.clearTimeout = function (id) {
    _activeTimers.delete(id);
    return _origClearTimeout(id);
  };
  window.clearInterval = function (id) {
    _activeIntervals.delete(id);
    return _origClearInterval(id);
  };
  // Fetch patch tối thiểu: KHÔNG inject signal (tránh conflict với user
  // signal), chỉ track AbortController khi user chưa pass signal — minor
  // tracking only. Nếu cleanup, gọi controller.abort().
  window.fetch = function () {
    let ctrl = null;
    if (_trackingEnabled && (!arguments[1] || !arguments[1].signal)) {
      ctrl = new AbortController();
      const opts = arguments[1] || {};
      arguments[1] = Object.assign({}, opts, { signal: ctrl.signal });
      _activeFetches.add(ctrl);
    }
    const p = _origFetch.apply(window, arguments);
    if (ctrl) p.finally(function () { _activeFetches.delete(ctrl); });
    return p;
  };

  // ── Patch addEventListener để track + cleanup khi navigate ────────────────
  // Bug gốc: page scripts add `document.addEventListener('click', ...)` mỗi lần
  // ajax-nav re-execute → sau N nav có N listeners cùng loại fire → click 1 lần
  // chạy handler N lần → unpredictable. Fix: track tất cả listeners được add
  // trong scope page → remove tự động khi navigate.
  //
  // QUAN TRỌNG: skip các event types CROSS-PAGE để chúng persist:
  //   - 'ajax:navigated'  (floating-chat dùng để toggle FAB visibility)
  //   - 'page:ready'      (ajax-nav overlay listen)
  //   - 'popstate', 'hashchange', 'beforeunload' (browser navigation)
  //   - 'unhandledrejection', 'error'             (global error handlers)
  const _origDocAdd    = document.addEventListener.bind(document);
  const _origDocRemove = document.removeEventListener.bind(document);
  const _origWinAdd    = window.addEventListener.bind(window);
  const _origWinRemove = window.removeEventListener.bind(window);
  const _SKIP_LISTENER_EVENTS = new Set([
    'ajax:navigated', 'page:ready',
    'popstate', 'hashchange', 'beforeunload',
    'unhandledrejection', 'error',
  ]);
  const _pageListeners = [];  // {target, type, listener, options}

  function _trackListener(target, type, listener, options) {
    if (_SKIP_LISTENER_EVENTS.has(type)) return;
    if (!_trackingEnabled) return;
    _pageListeners.push({ target, type, listener, options });
  }
  document.addEventListener = function (type, listener, options) {
    _trackListener(document, type, listener, options);
    return _origDocAdd(type, listener, options);
  };
  document.removeEventListener = function (type, listener, options) {
    // Remove khỏi track để không double-remove khi cleanup
    for (let i = _pageListeners.length - 1; i >= 0; i--) {
      const it = _pageListeners[i];
      if (it.target === document && it.type === type && it.listener === listener) {
        _pageListeners.splice(i, 1);
        break;
      }
    }
    return _origDocRemove(type, listener, options);
  };
  window.addEventListener = function (type, listener, options) {
    _trackListener(window, type, listener, options);
    return _origWinAdd(type, listener, options);
  };
  window.removeEventListener = function (type, listener, options) {
    for (let i = _pageListeners.length - 1; i >= 0; i--) {
      const it = _pageListeners[i];
      if (it.target === window && it.type === type && it.listener === listener) {
        _pageListeners.splice(i, 1);
        break;
      }
    }
    return _origWinRemove(type, listener, options);
  };

  function _cleanupPageListeners() {
    for (const { target, type, listener, options } of _pageListeners) {
      try {
        if (target === document) _origDocRemove(type, listener, options);
        else                     _origWinRemove(type, listener, options);
      } catch (_) {}
    }
    _pageListeners.length = 0;
  }

  function _cleanupPageState() {
    // Clear tất cả timer/interval của page cũ
    _activeTimers.forEach(function (id) { _origClearTimeout(id); });
    _activeTimers.clear();
    _activeIntervals.forEach(function (id) { _origClearInterval(id); });
    _activeIntervals.clear();
    // Abort in-flight fetch
    _activeFetches.forEach(function (ctrl) { try { ctrl.abort(); } catch (_) {} });
    _activeFetches.clear();
    // Remove tất cả document/window listeners đã track của page cũ
    // (KHÔNG remove cross-page events như ajax:navigated, popstate)
    _cleanupPageListeners();
    // Page-specific cleanup (nếu page có gắn)
    if (typeof window.__pageCleanup === 'function') {
      try { window.__pageCleanup(); } catch (e) { console.error('[ajax-nav cleanup]', e); }
      window.__pageCleanup = null;
    }
  }

  // ────────────────────────────────────────────────────────────────────────
  // Progress bar + click-block overlay (prevent race condition khi init chưa xong)
  // ────────────────────────────────────────────────────────────────────────
  function ensureBar() {
    let bar = document.getElementById('__ajaxBar');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = '__ajaxBar';
      bar.style.cssText = 'position:fixed;top:0;left:0;height:3px;width:0;z-index:99999;background:linear-gradient(90deg,#4F46E5,#7c3aed);transition:width .3s ease-out,opacity .25s .15s;pointer-events:none';
      document.body.appendChild(bar);
    }
    return bar;
  }
  // Overlay che main content nhẹ trong khi page init chạy. Ngăn user click button
  // trước khi data loaded → tránh modal/handler mở với state rỗng (race condition
  // sau ajax navigation HOẶC initial page load).
  // Page dispatch 'page:ready' event khi init xong → overlay hide.
  // Fallback: tự hide sau OVERLAY_MAX_MS dù page không dispatch (safety net).
  // 10s đủ cho backend cold start (FastAPI uvicorn ~3-8s khi vừa start).
  const OVERLAY_MAX_MS = 10000;
  let _overlayTimer = null;
  function ensureOverlay() {
    let ov = document.getElementById('__ajaxOverlay');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = '__ajaxOverlay';
      ov.style.cssText = [
        'position:fixed','top:60px','left:0','right:0','bottom:0',
        'z-index:99998',
        'background:transparent',
        'display:none','cursor:wait',
        'pointer-events:auto',
        // Soft fade-in — không che hẳn content, chỉ block click
        'transition:background .25s',
      ].join(';');
      document.body.appendChild(ov);
    }
    return ov;
  }
  function overlayShow() {
    ensureOverlay().style.display = 'block';
    // KHÔNG dim — chỉ block click. Animation fade-in của main content + progress
    // bar trên cùng đã đủ visual feedback. Dim nền gây cảm giác laggy.
    _origClearTimeout(_overlayTimer);
    // Safety timeout — fallback hide
    _overlayTimer = _origSetTimeout(() => {
      if (ensureOverlay().style.display === 'block') {
        console.warn('[ajax-nav] page:ready not fired in ' + OVERLAY_MAX_MS + 'ms — auto-hiding overlay');
        overlayHide();
      }
    }, OVERLAY_MAX_MS);
  }
  function overlayHide() {
    _origClearTimeout(_overlayTimer);
    const ov = ensureOverlay();
    ov.style.display = 'none';
  }
  function barStart() {
    const b = ensureBar();
    b.style.opacity = '1'; b.style.width = '0'; b.offsetHeight; b.style.width = '70%';
    overlayShow();
  }
  function barDone() {
    const b = ensureBar();
    b.style.width = '100%';
    _origSetTimeout(() => { b.style.opacity = '0'; }, 180);
    // KHÔNG hide overlay ở đây — đợi page:ready event hoặc safety timeout.
  }
  // Listen 'page:ready' event — page dispatch khi init() async hoàn tất.
  window.addEventListener('page:ready', () => overlayHide());

  // ────────────────────────────────────────────────────────────────────────
  // Fetch + parse + cache
  // ────────────────────────────────────────────────────────────────────────
  async function fetchPage(url) {
    const hit = CACHE.get(url);
    if (hit && (Date.now() - hit.ts) < CACHE_TTL_MS) return hit.packet;
    if (hit) CACHE.delete(url);  // expired — drop it
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const text = await res.text();
    const doc = new DOMParser().parseFromString(text, 'text/html');
    const mainEl = doc.querySelector('main');
    if (!mainEl) throw new Error('No <main> found');
    const headerEl = doc.querySelector('header');  // optional — page-specific header swap

    // Collect ALL scripts (head + body) from fetched page.
    // Skip scripts ALREADY present in host (exact src path match) to avoid duplicate.
    // Skip inline tailwind.config scripts — tailwind already configured globally.
    const hostSrcs = new Set(
      Array.from(document.querySelectorAll('script[src]'))
        .map(s => {
          try { return new URL(s.getAttribute('src'), location.href).pathname.split('?')[0]; }
          catch { return s.getAttribute('src'); }
        })
    );
    const bodyScripts = [];
    doc.querySelectorAll('script').forEach(s => {
      const src = s.getAttribute('src');
      if (src) {
        let srcPath = src;
        try { srcPath = new URL(src, location.href).pathname.split('?')[0]; } catch {}
        if (hostSrcs.has(srcPath)) return;
        // Skip the Tailwind CDN itself — it's already loaded on host page
        if (src.includes('cdn.tailwindcss.com')) return;
        bodyScripts.push({ src, text: '' });
      } else {
        const txt = s.textContent || '';
        // Skip tailwind.config reassignment (already set on host)
        if (/tailwind\.config/.test(txt)) return;
        // Skip tiny scripts
        if (txt.trim().length < 5) return;
        bodyScripts.push({ src: null, text: txt });
      }
    });

    // Collect <style> blocks unique to this page (simple heuristic: those inside <head> that aren't in shell)
    const pageStyles = [];
    doc.head.querySelectorAll('style').forEach(s => {
      const txt = s.textContent || '';
      if (!txt || txt.length < 10) return;
      pageStyles.push(txt);
    });

    // Collect body-level "extra" elements (modals, drawers, overlays) that live as direct
    // children of <body> outside <header>/<main>. These are page-specific and must be
    // swapped too — many pages put modals (#uploadModal, #addUserModal, etc.) here, and
    // their inline init scripts would crash on null if we leave the previous page's body.
    const SHELL_IDS = new Set([
      'sidebarMount', 'sidebarDrawer', 'sidebarOverlay',
      'adminSidebarMount', 'adminSidebar', 'adminSidebarOverlay',
      'toastContainer', '__ajaxBar',
      // Floating chat — persistent FAB + panel + style (wrapped trong fcRoot)
      'fcRoot', 'fcFab', 'fcPanel',
      // Avatar dropdown menu nếu được inject ở body
      'avatarMenu', 'avatarDropdown',
    ]);
    const bodyExtras = [];
    Array.from(doc.body.children).forEach(el => {
      const tag = el.tagName.toLowerCase();
      if (tag === 'header' || tag === 'main' || tag === 'script') return;
      if (el.id && SHELL_IDS.has(el.id)) return;
      bodyExtras.push(el.outerHTML);
    });

    const packet = {
      title: doc.title,
      mainHtml: mainEl.innerHTML,
      mainClass: mainEl.className,
      headerHtml: headerEl ? headerEl.innerHTML : null,
      headerClass: headerEl ? headerEl.className : null,
      bodyExtras,
      scripts: bodyScripts,
      styles: pageStyles,
    };
    CACHE.set(url, { packet, ts: Date.now() });
    return packet;
  }

  // ────────────────────────────────────────────────────────────────────────
  // Apply packet: swap main, execute scripts
  // ────────────────────────────────────────────────────────────────────────
  // Inject 1 lần CSS cho transition + skeleton (ngày đầu load)
  (function injectAjaxTransitionCss() {
    if (document.getElementById('__ajaxTransitionCss')) return;
    const css = document.createElement('style');
    css.id = '__ajaxTransitionCss';
    css.textContent = `
/* Page transition — fade-up nhẹ khi swap content qua ajax-nav */
@keyframes __ajaxFadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
main.__ajax-enter {
  animation: __ajaxFadeUp .28s cubic-bezier(0.16, 1, 0.3, 1) both;
}
header.__ajax-enter {
  animation: __ajaxFadeUp .22s cubic-bezier(0.16, 1, 0.3, 1) both;
}

/* Skeleton placeholder (block UI shows ngay khi nav start, trước khi data load) */
@keyframes __ajaxSkelShimmer {
  0% { background-position: -200px 0; }
  100% { background-position: calc(200px + 100%) 0; }
}
.__ajax-skeleton {
  background: linear-gradient(90deg,
    var(--surface-subtle, #f1f5f9) 0%,
    var(--surface-strong, #e2e8f0) 50%,
    var(--surface-subtle, #f1f5f9) 100%);
  background-size: 200px 100%;
  background-repeat: no-repeat;
  animation: __ajaxSkelShimmer 1.4s linear infinite;
  border-radius: 10px;
}

/* Sidebar nav item — micro-interaction lúc click */
@keyframes __ajaxNavPulse {
  0%   { transform: scale(1); }
  35%  { transform: scale(0.96); }
  100% { transform: scale(1); }
}
.__ajax-clicking {
  animation: __ajaxNavPulse .24s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Smooth highlight cho overlay (subtle) */
#__ajaxOverlay { transition: background-color .25s ease; }
`;
    document.head.appendChild(css);
  })();

  function applyPage(packet) {
    document.title = packet.title || document.title;

    // Swap <header> (page-specific IDs differ between pages — must replace to avoid
    // scripts hitting null elements like getElementById('headerUserName') on a page that
    // uses a different ID convention than the previous page).
    const header = document.querySelector('header');
    if (header && packet.headerHtml != null) {
      header.innerHTML = packet.headerHtml;
      if (packet.headerClass) header.className = packet.headerClass;
      // Trigger fade-in animation
      header.classList.remove('__ajax-enter');
      void header.offsetHeight;  // force reflow để animation chạy lại
      header.classList.add('__ajax-enter');
    }

    // Swap <main>
    const main = document.querySelector('main');
    if (main) {
      main.innerHTML = packet.mainHtml;
      if (packet.mainClass) main.className = packet.mainClass;
      // Trigger fade-up animation cho main content (impact lớn nhất về cảm giác mượt)
      main.classList.remove('__ajax-enter');
      void main.offsetHeight;
      main.classList.add('__ajax-enter');
    }

    // Swap body-level "extra" elements (modals, drawers, overlays from the previous page).
    // We mark injected elements with data-ajax-extra so we can find/replace them on next nav.
    const SHELL_IDS = new Set([
      'sidebarMount', 'sidebarDrawer', 'sidebarOverlay',
      'adminSidebarMount', 'adminSidebar', 'adminSidebarOverlay',
      'toastContainer', '__ajaxBar',
      // Floating chat — persistent FAB + panel + style (wrapped trong fcRoot)
      'fcRoot', 'fcFab', 'fcPanel',
      // Avatar dropdown menu nếu được inject ở body
      'avatarMenu', 'avatarDropdown',
    ]);
    Array.from(document.body.children).forEach(el => {
      if (el.hasAttribute && el.hasAttribute('data-ajax-extra')) {
        el.remove();
        return;
      }
      const tag = el.tagName.toLowerCase();
      if (tag === 'header' || tag === 'main' || tag === 'script') return;
      if (el.id && SHELL_IDS.has(el.id)) return;
      // Anything else from a prior page (modal containers without data-ajax-extra) — drop it
      el.remove();
    });
    if (Array.isArray(packet.bodyExtras) && packet.bodyExtras.length) {
      const tpl = document.createElement('template');
      tpl.innerHTML = packet.bodyExtras.join('\n');
      Array.from(tpl.content.children).forEach(node => {
        node.setAttribute('data-ajax-extra', '1');
        document.body.appendChild(node);
      });
    }

    // Merge page-specific <style> (avoid duplicating by content hash key)
    const existingStyles = new Set(
      Array.from(document.head.querySelectorAll('style[data-ajax-style]'))
        .map(s => s.getAttribute('data-ajax-style'))
    );
    // Remove styles from previous AJAX page that aren't in new packet
    packet.styles.forEach((text, i) => {
      const key = 'ajax-style-' + _hash(text);
      if (existingStyles.has(key)) return;
      const el = document.createElement('style');
      el.setAttribute('data-ajax-style', key);
      el.textContent = text;
      document.head.appendChild(el);
    });

    // Execute scripts in an IIFE + auto-expose top-level function declarations
    // to window. This way:
    //  - top-level `let/const` are scoped to IIFE → no redeclaration errors across pages
    //  - `function foo(){}` declarations get `window.foo = foo;` appended so
    //    inline onclick="foo()" still works after swap.
    return new Promise((resolve, reject) => {
      const scripts = packet.scripts.slice();
      function next() {
        if (!scripts.length) return resolve();
        const s = scripts.shift();
        if (s.src) {
          if (document.querySelector('script[src="' + s.src + '"]')) { _origSetTimeout(next, 0); return; }
          const el = document.createElement('script');
          el.src = s.src;
          el.onload = next;
          el.onerror = () => { reject(new Error('script load: ' + s.src)); };
          document.body.appendChild(el);
          return;
        }
        try {
          const wrapped = wrapInlineScript(s.text);
          const el = document.createElement('script');
          el.textContent = wrapped;
          document.body.appendChild(el);
          _origSetTimeout(next, 0);
        } catch (e) {
          reject(e);
        }
      }
      next();
    });
  }

  /**
   * Wrap an inline page script so that:
   *  - It runs inside an IIFE (prevents global let/const redeclaration across pages)
   *  - All top-level `function name(...)` declarations are exposed to window
   *    (so onclick="name()" handlers still work)
   *  - Top-level `async function name(...)` also exposed
   *  - exposeLines run BEFORE main script body — function declarations are hoisted,
   *    so this guarantees window.foo exists even if the main body throws at runtime
   *    (e.g. getElementById returns null, fetch fails, etc.). Otherwise a single
   *    init bug would silently kill ALL click handlers on the page until reload.
   */
  function wrapInlineScript(src) {
    // Find top-level function declarations. Simple regex (skip matches inside other functions is tricky;
    // we accept that nested function declarations also get exposed — harmless).
    const fnNames = new Set();
    const fnRegex = /(?:^|\n)\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(/g;
    let m;
    while ((m = fnRegex.exec(src)) !== null) fnNames.add(m[1]);

    const exposeLines = [...fnNames]
      .map(n => `try{window[${JSON.stringify(n)}]=${n};}catch(e){}`)
      .join('\n');

    // Wrap so init errors don't kill onclick handler wiring:
    //   - Inner try around src catches runtime errors during page-init code.
    //   - V8 hoists function declarations encountered before a throw to the
    //     enclosing IIFE scope (sloppy-mode behavior). So exposeLines AFTER
    //     the inner try will still see all functions declared in src — even
    //     if init code threw partway through.
    //   - Outer try catches syntax errors in exposeLines itself (paranoid).
    return [
      '(function(){',
      // Capture DOMContentLoaded listeners — they would otherwise never fire
      // because the event already happened on the host page. We collect them
      // here and replay asynchronously after the script body has run.
      'var __pendingDCL = [];',
      'var __origAdd = document.addEventListener.bind(document);',
      'document.addEventListener = function(ev, cb, opts) {',
      '  if (ev === "DOMContentLoaded") { __pendingDCL.push(cb); return; }',
      '  return __origAdd(ev, cb, opts);',
      '};',
      'try {',
      'try {',
      src,
      '} catch(initErr) { console.error("[ajax-nav page init]", initErr); }',
      exposeLines,                          // run AFTER src — sees hoisted decls
      'document.addEventListener = __origAdd;',
      // Replay captured DOMContentLoaded listeners asynchronously so any
      // top-level code that registered them has finished setting up state.
      'Promise.resolve().then(function(){',
      '  __pendingDCL.forEach(function(cb){',
      '    try { cb(new Event("DOMContentLoaded")); }',
      '    catch(e){ console.error("[ajax-nav DCL cb]", e); }',
      '  });',
      '});',
      '} catch(err) { console.error("[ajax-nav page script]", err); throw err; }',
      '})();',
    ].join('\n');
  }

  function _hash(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = ((h << 5) - h) + str.charCodeAt(i) | 0;
    return Math.abs(h).toString(36);
  }

  // ────────────────────────────────────────────────────────────────────────
  // Navigate
  // ────────────────────────────────────────────────────────────────────────
  let _navigating = false;
  let _navStartedAt = 0;
  const NAV_STUCK_MS = 10000;  // if navigation takes longer than 10s, assume it's wedged

  async function navigate(url, push = true) {
    // Safety net: if a previous navigation got stuck (rare — usually from a thrown
    // script during applyPage), allow a new one to take over instead of locking
    // the entire app from clicks.
    if (_navigating) {
      if (Date.now() - _navStartedAt < NAV_STUCK_MS) return;
      console.warn('[ajax-nav] previous navigation appears stuck — overriding');
    }
    _navigating = true;
    _navStartedAt = Date.now();
    barStart();
    // Hard timeout fallback: if navigation hasn't finished after NAV_STUCK_MS,
    // do a real page reload so user isn't trapped.
    // Dùng _origSetTimeout để KHÔNG track timer này (tránh _cleanupPageState clear nhầm).
    const stuckTimer = _origSetTimeout(() => {
      if (_navigating) {
        console.warn('[ajax-nav] navigation timeout — falling back to full reload');
        _navigating = false;
        window.location.href = url;
      }
    }, NAV_STUCK_MS);
    try {
      const packet = await fetchPage(url);
      // Validate packet — nếu mainHtml trống bất thường, fallback full reload
      if (!packet || !packet.mainHtml || packet.mainHtml.length < 50) {
        console.warn('[ajax-nav] empty mainHtml, fallback full reload');
        window.location.href = url;
        return;
      }
      // Cleanup state của page cũ TRƯỚC khi swap content (clear timers, abort fetches)
      _cleanupPageState();
      if (push) history.pushState({ url }, '', url);
      await applyPage(packet);
      if (typeof initSidebarFragment === 'function') {
        try { initSidebarFragment(); } catch (_) {}
      }
      // Smooth scroll lên đầu — cảm giác fluid hơn instant scroll
      window.scrollTo({ top: 0, behavior: 'smooth' });
      window.dispatchEvent(new CustomEvent('ajax:navigated', { detail: { url } }));
    } catch (err) {
      console.warn('[ajax-nav] fallback full navigation:', err);
      window.location.href = url;
      return;
    } finally {
      _origClearTimeout(stuckTimer);
      barDone();
      _navigating = false;
    }
  }

  // ────────────────────────────────────────────────────────────────────────
  // Link click interception
  // ────────────────────────────────────────────────────────────────────────
  function shouldIntercept(link, evt) {
    if (!link) return false;
    if (link.target && link.target !== '_self') return false;
    if (link.hasAttribute('download')) return false;
    if (link.classList.contains('no-ajax')) return false;
    if (evt && (evt.ctrlKey || evt.metaKey || evt.shiftKey || evt.altKey || evt.button !== 0)) return false;

    const href = link.getAttribute('href') || '';
    if (!href || href.startsWith('#') || href.startsWith('javascript:')) return false;
    if (href.startsWith('mailto:') || href.startsWith('tel:')) return false;
    // Only same-origin .html links
    try {
      const u = new URL(link.href, location.href);
      if (u.origin !== location.origin) return false;
      if (!u.pathname.endsWith('.html')) return false;
      // Don't intercept login/reset (they don't share the sidebar layout)
      if (u.pathname.endsWith('/index.html') || u.pathname.endsWith('/reset-password.html')) return false;
      return true;
    } catch (_) { return false; }
  }

  // ════════════════════════════════════════════════════════════════════════
  // MPA MODE — v16: SPA navigation DISABLED dứt điểm.
  //
  // Lý do: ajax-nav SPA simulation gây ra class of bugs khó fix dứt điểm:
  //   - Listener accumulation across nav (đã fix ở v14 nhưng vẫn rò qua các path
  //     library 3rd-party / property-style listener)
  //   - State leak (biến module-level không được reset khi swap <main>)
  //   - Init race condition (user click trước khi async init() xong)
  //   - Script re-execution edge cases (const/let redeclare, init() side-effect)
  //
  // Fix dứt điểm: dùng full page reload (browser default). Mỗi page = process
  // mới, listener fresh, state fresh, init() chạy 1 lần duy nhất.
  // Mất "snappy SPA feel" → bù bằng:
  //   - nav-prefetch.js: <link rel="prefetch"> cho sidebar links (browser cache HTML)
  //   - View Transitions API trong design-system.css (animate fade giữa page)
  //   - Browser paint holding (auto, không cần code)
  //
  // GIỮ overlay show on initial load — vẫn cần để block click trong cold-start
  // init race (user click button trước khi /auth/me fetch xong → handler fail).
  //
  // Để rollback (re-enable SPA): xóa block return; bên dưới (cùng comment header).
  // ════════════════════════════════════════════════════════════════════════
  if (PATH !== 'index.html' && PATH !== 'reset-password.html' && PATH !== 'admin.html' && PATH !== '') {
    overlayShow();
  }
  return;
  /* eslint-disable */
  // ─── BEGIN LEGACY SPA NAV CODE (dead in MPA mode, kept for rollback) ─────
  // ajax-nav own listeners: dùng _origDocAdd/_origWinAdd để BYPASS tracking
  // → các listener này persist across navigations, không bị cleanup remove.
  _origDocAdd('click', function (e) {
    const link = e.target.closest('a[href]');
    if (!shouldIntercept(link, e)) return;
    e.preventDefault();
    const url = link.href.replace(location.origin, '') || link.getAttribute('href');
    if (url === location.pathname + location.search) return;
    // Micro-interaction: scale-down briefly để user cảm thấy "click registered"
    try {
      link.classList.add('__ajax-clicking');
      _origSetTimeout(() => link.classList.remove('__ajax-clicking'), 240);
    } catch (_) {}
    navigate(url);
  });

  // ────────────────────────────────────────────────────────────────────────
  // Hover prefetch (warm cache before user clicks)
  // ────────────────────────────────────────────────────────────────────────
  let _prefetchTimer = null;
  _origDocAdd('mouseover', function (e) {
    const link = e.target.closest('a[href]');
    if (!shouldIntercept(link, null)) return;
    const url = link.href.replace(location.origin, '') || link.getAttribute('href');
    const hit = CACHE.get(url);
    if (hit && (Date.now() - hit.ts) < CACHE_TTL_MS) return;
    _origClearTimeout(_prefetchTimer);
    _prefetchTimer = _origSetTimeout(() => {
      fetchPage(url).catch(() => {});
    }, 80);
  });
  _origDocAdd('mouseout', function () {
    _origClearTimeout(_prefetchTimer);
  });

  // ────────────────────────────────────────────────────────────────────────
  // Back/forward
  // ────────────────────────────────────────────────────────────────────────
  _origWinAdd('popstate', function (e) {
    const url = location.pathname + location.search;
    navigate(url, false);
  });

  // Store initial state
  history.replaceState({ url: location.pathname + location.search }, '', location.href);

  // ── Show overlay on INITIAL page load (block clicks until page:ready) ────
  // Bug gốc: F5/load lần đầu KHÔNG có overlay → user click button trước khi
  // init() async fetch xong → handler chạy với state rỗng → action fail silently.
  // Fix: overlay show ngay sau ajax-nav setup, mỗi page tự dispatch page:ready
  // khi init xong → overlay hide.
  // Skip cho login/admin (admin SKIP ajax-nav, login không có init async dài).
  if (PATH !== 'index.html' && PATH !== 'reset-password.html' && PATH !== 'admin.html' && PATH !== '') {
    overlayShow();
  }
})();
