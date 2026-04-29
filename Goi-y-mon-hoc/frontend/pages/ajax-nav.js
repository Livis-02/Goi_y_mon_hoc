/**
 * ajax-nav.js — AJAX navigation for EduGuide (multi-page → SPA-lite).
 *
 * Strategy:
 * - Intercept clicks on same-origin `.html` links (sidebar, in-page nav).
 * - Fetch target page, extract <main> + <title> + any page-specific <style>.
 * - Swap into current document; execute fresh <script> tags.
 * - On any re-execution error (e.g. let/const redeclaration), fall back to
 *   full browser navigation — guaranteed to work.
 *
 * Extras:
 * - Hover prefetch: warm browser cache when user hovers a link.
 * - Top progress bar during fetch.
 * - Updates sidebar active state.
 * - Back/forward via popstate.
 *
 * Load order: after auth.js + sidebar-init.js, before other page-specific scripts.
 */
(function () {
  'use strict';

  if (!window.fetch || !window.history.pushState || !window.DOMParser) return;

  // Skip SPA behavior on auth screens
  const PATH = location.pathname.split('/').pop() || '';
  if (PATH === 'index.html' || PATH === 'reset-password.html' || PATH === '') return;

  const CACHE = new Map();  // url -> { title, mainHtml, scripts:[{src,text}], styles:[text] }

  // ────────────────────────────────────────────────────────────────────────
  // Progress bar
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
  function barStart() {
    const b = ensureBar();
    b.style.opacity = '1'; b.style.width = '0'; b.offsetHeight; b.style.width = '70%';
  }
  function barDone() {
    const b = ensureBar();
    b.style.width = '100%';
    setTimeout(() => { b.style.opacity = '0'; }, 180);
  }

  // ────────────────────────────────────────────────────────────────────────
  // Fetch + parse + cache
  // ────────────────────────────────────────────────────────────────────────
  async function fetchPage(url) {
    if (CACHE.has(url)) return CACHE.get(url);
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

    const packet = {
      title: doc.title,
      mainHtml: mainEl.innerHTML,
      mainClass: mainEl.className,
      headerHtml: headerEl ? headerEl.innerHTML : null,
      headerClass: headerEl ? headerEl.className : null,
      scripts: bodyScripts,
      styles: pageStyles,
    };
    CACHE.set(url, packet);
    return packet;
  }

  // ────────────────────────────────────────────────────────────────────────
  // Apply packet: swap main, execute scripts
  // ────────────────────────────────────────────────────────────────────────
  function applyPage(packet) {
    document.title = packet.title || document.title;

    // Swap <header> (page-specific IDs differ between pages — must replace to avoid
    // scripts hitting null elements like getElementById('headerUserName') on roadmap.html
    // when previous page had 'topbarUserName' instead).
    const header = document.querySelector('header');
    if (header && packet.headerHtml != null) {
      header.innerHTML = packet.headerHtml;
      if (packet.headerClass) header.className = packet.headerClass;
    }

    // Swap <main>
    const main = document.querySelector('main');
    if (main) {
      main.innerHTML = packet.mainHtml;
      if (packet.mainClass) main.className = packet.mainClass;
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
          if (document.querySelector('script[src="' + s.src + '"]')) { setTimeout(next, 0); return; }
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
          setTimeout(next, 0);
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
      'try {',
      'try {',
      src,
      '} catch(initErr) { console.error("[ajax-nav page init]", initErr); }',
      exposeLines,                          // run AFTER src — sees hoisted decls
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

  async function navigate(url, push = true) {
    if (_navigating) return;
    _navigating = true;
    barStart();
    try {
      const packet = await fetchPage(url);
      if (push) history.pushState({ url }, '', url);
      await applyPage(packet);
      // Re-apply sidebar active state
      if (typeof initSidebarFragment === 'function') {
        try { initSidebarFragment(); } catch (_) {}
      }
      window.scrollTo({ top: 0, behavior: 'instant' });
      window.dispatchEvent(new CustomEvent('ajax:navigated', { detail: { url } }));
    } catch (err) {
      console.warn('[ajax-nav] fallback full navigation:', err);
      window.location.href = url;
      return;
    } finally {
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
      // Don't intercept redirect shims
      if (u.pathname.endsWith('/ctdt.html') || u.pathname.endsWith('/careers.html')) return false;
      if (u.pathname.endsWith('/index.html') || u.pathname.endsWith('/reset-password.html')) return false;
      return true;
    } catch (_) { return false; }
  }

  document.addEventListener('click', function (e) {
    const link = e.target.closest('a[href]');
    if (!shouldIntercept(link, e)) return;
    e.preventDefault();
    const url = link.href.replace(location.origin, '') || link.getAttribute('href');
    if (url === location.pathname + location.search) return;
    navigate(url);
  });

  // ────────────────────────────────────────────────────────────────────────
  // Hover prefetch (warm cache before user clicks)
  // ────────────────────────────────────────────────────────────────────────
  let _prefetchTimer = null;
  document.addEventListener('mouseover', function (e) {
    const link = e.target.closest('a[href]');
    if (!shouldIntercept(link, null)) return;
    const url = link.href.replace(location.origin, '') || link.getAttribute('href');
    if (CACHE.has(url)) return;
    clearTimeout(_prefetchTimer);
    _prefetchTimer = setTimeout(() => {
      fetchPage(url).catch(() => {});
    }, 80);
  });
  document.addEventListener('mouseout', function () {
    clearTimeout(_prefetchTimer);
  });

  // ────────────────────────────────────────────────────────────────────────
  // Back/forward
  // ────────────────────────────────────────────────────────────────────────
  window.addEventListener('popstate', function (e) {
    const url = location.pathname + location.search;
    navigate(url, false);
  });

  // Store initial state
  history.replaceState({ url: location.pathname + location.search }, '', location.href);
})();
