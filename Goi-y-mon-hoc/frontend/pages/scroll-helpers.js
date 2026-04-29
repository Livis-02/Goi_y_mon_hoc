/**
 * scroll-helpers.js — translate vertical mouse wheel into horizontal scroll
 * for any container whose content is wider than the container (horizontal overflow).
 *
 * Strategy:
 * - Walk up from e.target, find the first element with horizontal overflow
 *   (scrollWidth > clientWidth + 1 AND overflowX in ['auto','scroll']).
 * - Before hijacking, confirm no inner vertical scroller on the walk path
 *   that still has room to scroll in the wheel direction.
 *
 * Opt-in override: add `data-hscroll` to force enable on a specific element.
 *
 * Load this file in <head> of every host page (once, after sidebar-init.js).
 */
(function () {
  'use strict';

  function _hasHScroll(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.hasAttribute && el.hasAttribute('data-hscroll')) return true;
    if (el.scrollWidth <= el.clientWidth + 1) return false;
    const style = window.getComputedStyle(el);
    return style.overflowX === 'auto' || style.overflowX === 'scroll';
  }

  function _canScrollVert(el, deltaY) {
    if (!el || el.nodeType !== 1) return false;
    const style = window.getComputedStyle(el);
    const oy = style.overflowY;
    if (oy !== 'auto' && oy !== 'scroll') return false;
    if (el.scrollHeight <= el.clientHeight + 1) return false;
    if (deltaY > 0) return el.scrollTop + el.clientHeight < el.scrollHeight - 1;
    if (deltaY < 0) return el.scrollTop > 0;
    return false;
  }

  // Walk up from target: find innermost vertical scroller (if any) and first horizontal scroller.
  function findScrollers(el, deltaY) {
    let cur = el;
    let innerVert = null;
    let outerHoriz = null;
    for (let i = 0; i < 15 && cur && cur !== document.body; i++) {
      if (!innerVert && _canScrollVert(cur, deltaY)) innerVert = cur;
      if (!outerHoriz && _hasHScroll(cur)) outerHoriz = cur;
      if (innerVert && outerHoriz) break;
      cur = cur.parentElement;
    }
    return { innerVert, outerHoriz };
  }

  window.addEventListener('wheel', function (e) {
    if (!e.deltaY || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
    if (e.shiftKey) return;

    const { innerVert, outerHoriz } = findScrollers(e.target, e.deltaY);

    // Priority: if inner vertical scroller is INSIDE the horizontal scroller, let it scroll first.
    // Only hijack when vertical target either doesn't exist or cannot scroll further.
    if (innerVert && outerHoriz && outerHoriz.contains(innerVert)) {
      // Vertical scroller is inside horizontal — it can still scroll, let native handle
      return;
    }
    if (innerVert && !outerHoriz) {
      // Only vertical scroller — let native handle
      return;
    }
    if (!outerHoriz) return;

    // Hijack to horizontal, but release at edges so page can scroll further
    const atStart = outerHoriz.scrollLeft <= 0 && e.deltaY < 0;
    const atEnd = Math.ceil(outerHoriz.scrollLeft + outerHoriz.clientWidth) >= outerHoriz.scrollWidth && e.deltaY > 0;
    if (atStart || atEnd) return;

    outerHoriz.scrollLeft += e.deltaY;
    e.preventDefault();
  }, { passive: false });
})();
