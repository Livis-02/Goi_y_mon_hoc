/**
 * accessibility.js — global a11y helpers shared across pages.
 *
 * What it does (auto, no per-page code):
 *  1. Detects modals = element with attribute `data-modal` OR id ending in "Modal"
 *     that becomes visible (class change from "hidden" → not "hidden").
 *  2. Traps Tab focus inside the modal.
 *  3. Restores focus to the trigger element when modal closes.
 *  4. Listens for Escape — if a modal is open, calls its first
 *     `[data-modal-close]` button OR the function named in `data-close-fn` attr.
 *  5. Adds role="dialog", aria-modal="true" to detected modals on first show.
 *
 * Per-page opt-in (recommended for new modals):
 *   <div id="myModal" data-modal aria-labelledby="myModalTitle" ...>
 *     <button data-modal-close aria-label="Đóng modal">×</button>
 *   </div>
 *
 * Legacy modals (no attributes) still work — handler picks them up via id heuristic.
 */
(function () {
  'use strict';

  const MODAL_SELECTOR = '[data-modal], [id$="Modal"]';
  let _activeModal = null;
  let _previouslyFocused = null;

  function getFocusable(root) {
    return Array.from(root.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), '
      + 'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(el => el.offsetParent !== null);  // visible only
  }

  function _activate(modal) {
    if (modal === _activeModal) return;
    if (_activeModal) _deactivate(_activeModal);

    _activeModal = modal;
    _previouslyFocused = document.activeElement;

    // Set ARIA if missing (idempotent)
    if (!modal.hasAttribute('role')) modal.setAttribute('role', 'dialog');
    if (!modal.hasAttribute('aria-modal')) modal.setAttribute('aria-modal', 'true');

    // Focus first interactive element (or modal itself)
    const focusables = getFocusable(modal);
    setTimeout(() => {
      if (focusables.length) focusables[0].focus();
      else modal.setAttribute('tabindex', '-1') === undefined && modal.focus();
    }, 50);
  }

  function _deactivate(modal) {
    if (modal !== _activeModal) return;
    _activeModal = null;
    if (_previouslyFocused && typeof _previouslyFocused.focus === 'function') {
      try { _previouslyFocused.focus(); } catch (_) {}
    }
    _previouslyFocused = null;
  }

  function _isHidden(el) {
    if (!el || !el.classList) return true;
    if (el.classList.contains('hidden')) return true;
    const cs = getComputedStyle(el);
    return cs.display === 'none' || cs.visibility === 'hidden';
  }

  // Track modals with MutationObserver — auto-detect class flips.
  function _initObserver() {
    const all = document.querySelectorAll(MODAL_SELECTOR);
    all.forEach(modal => {
      // Initial state
      if (!_isHidden(modal)) _activate(modal);
    });

    const obs = new MutationObserver(muts => {
      for (const m of muts) {
        if (m.type !== 'attributes' || m.attributeName !== 'class') continue;
        const target = m.target;
        if (!target.matches || !target.matches(MODAL_SELECTOR)) continue;
        if (_isHidden(target)) {
          _deactivate(target);
        } else {
          _activate(target);
        }
      }
    });
    obs.observe(document.body, {
      attributes: true,
      attributeFilter: ['class'],
      subtree: true,
    });
  }

  // Tab trap
  document.addEventListener('keydown', e => {
    if (!_activeModal) return;

    if (e.key === 'Escape') {
      // Try data-modal-close button first
      const closeBtn = _activeModal.querySelector('[data-modal-close]')
        || _activeModal.querySelector('button[onclick*="close"]')
        || _activeModal.querySelector('button[aria-label*="Đóng" i], button[aria-label*="close" i]');
      if (closeBtn) {
        e.preventDefault();
        closeBtn.click();
      } else {
        // Fallback: try named close function from data attr
        const fn = _activeModal.dataset.closeFn;
        if (fn && typeof window[fn] === 'function') {
          e.preventDefault();
          window[fn]();
        }
      }
      return;
    }

    if (e.key !== 'Tab') return;
    const focusables = getFocusable(_activeModal);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  // Inert background — so screen readers don't announce siblings while modal open.
  // Skip for now — `inert` polyfill needed for older browsers.

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _initObserver);
  } else {
    _initObserver();
  }
})();
