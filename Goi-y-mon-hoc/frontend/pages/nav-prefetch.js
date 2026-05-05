/**
 * nav-prefetch.js — Speed up multi-page navigation by prefetching HTML.
 *
 * Lý do tồn tại: ajax-nav.js đã DISABLED ở v6 (state leak), nên mọi navigation
 * giữa các page là full reload → user thấy giật khi đổi page.
 *
 * Strategy:
 *   1. Idle prefetch — sau page load, browser idle thì prefetch các sidebar
 *      target để cache sẵn.
 *   2. Hover prefetch — khi user hover 1 link >65ms (intent strong), prefetch
 *      ngay để khi click HTML đã ở browser cache.
 *
 * Kết quả: full reload vẫn xảy ra nhưng HTML đã cached → time-to-paint giảm
 * từ ~300-500ms xuống ~50-150ms → cảm giác mượt hơn nhiều.
 *
 * KHÔNG có state leak vì đây vẫn là multi-page nav truyền thống — chỉ tăng tốc.
 */
(function () {
  'use strict';

  // Các page có sidebar link, cần prefetch để chuyển nhanh.
  const PREFETCH_TARGETS = [
    'home.html',
    'grades.html',
    'integrated-roadmap.html',
    'career-goal.html',
    'ai-chat.html',
    'messaging.html',
    'notifications.html',
    'settings.html',
    'advisor.html',
  ];

  const prefetched = new Set();
  const HOVER_INTENT_MS = 65;
  let hoverTimer = null;

  function prefetch(href) {
    if (!href || prefetched.has(href)) return;
    // Chỉ prefetch same-origin .html
    if (href.startsWith('http') || href.startsWith('//')) return;
    if (!href.endsWith('.html') && !href.includes('.html#')) return;
    prefetched.add(href);
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = href;
    link.as = 'document';
    document.head.appendChild(link);
  }

  // ── Strategy 1: Idle prefetch ────────────────────────────────────────────
  function idlePrefetch() {
    const currentPath = (location.pathname.split('/').pop() || '').toLowerCase();
    PREFETCH_TARGETS.forEach(function (target) {
      if (target.toLowerCase() !== currentPath) prefetch(target);
    });
  }

  if ('requestIdleCallback' in window) {
    requestIdleCallback(idlePrefetch, { timeout: 2000 });
  } else {
    setTimeout(idlePrefetch, 1500);
  }

  // ── Strategy 2: Hover prefetch (instant.page-style) ─────────────────────
  function onMouseOver(e) {
    const link = e.target && e.target.closest && e.target.closest('a[href]');
    if (!link) return;
    const href = link.getAttribute('href');
    if (!href) return;
    if (href.startsWith('#') || href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
    if (link.target === '_blank') return;

    if (hoverTimer) clearTimeout(hoverTimer);
    hoverTimer = setTimeout(function () { prefetch(href); }, HOVER_INTENT_MS);
  }

  function onMouseOut() {
    if (hoverTimer) {
      clearTimeout(hoverTimer);
      hoverTimer = null;
    }
  }

  document.addEventListener('mouseover', onMouseOver, { passive: true, capture: true });
  document.addEventListener('mouseout', onMouseOut, { passive: true, capture: true });

  // ── Strategy 3: Touchstart prefetch (mobile) ─────────────────────────────
  document.addEventListener('touchstart', function (e) {
    const link = e.target && e.target.closest && e.target.closest('a[href]');
    if (!link) return;
    const href = link.getAttribute('href');
    if (href) prefetch(href);
  }, { passive: true, capture: true });
})();
