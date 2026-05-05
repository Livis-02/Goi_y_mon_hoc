/* theme-switcher.js — light/dark mode toggle with persistence + system preference
 *
 * Strategy:
 *   1. On first paint, read saved preference (localStorage) OR system pref.
 *   2. Toggle by adding/removing `.dark` on <html>.
 *   3. Persist user choice; "auto" mode follows system.
 *
 * Usage:
 *   - Load this script in <head> AFTER theme.js, BEFORE Tailwind CDN.
 *   - The script self-applies on load (no FOUC).
 *   - Pages can render a button anywhere with class `theme-toggle`; click
 *     handler is wired automatically.
 *
 * Storage keys:
 *   eduguide_theme: 'light' | 'dark' | 'auto'
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'eduguide_theme';
  const DARK_CLASS = 'dark';
  const root = document.documentElement;

  function getSystemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark' : 'light';
  }

  function getSavedPreference() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (_) { return null; }
  }

  function savePreference(value) {
    try { localStorage.setItem(STORAGE_KEY, value); } catch (_) {}
  }

  function applyTheme(mode) {
    // mode: 'light' | 'dark' | 'auto'
    const effective = (mode === 'auto' || !mode) ? getSystemTheme() : mode;
    if (effective === 'dark') {
      root.classList.add(DARK_CLASS);
    } else {
      root.classList.remove(DARK_CLASS);
    }
    root.dataset.themeMode = mode || 'auto';
    root.dataset.themeEffective = effective;
    // Update any visible theme-toggle UI states
    document.querySelectorAll('[data-theme-value]').forEach(el => {
      el.dataset.active = (el.dataset.themeValue === (mode || 'auto')) ? 'true' : 'false';
    });
  }

  // Initial application — runs synchronously to avoid FOUC.
  const initial = getSavedPreference() || 'auto';
  applyTheme(initial);

  // First-visit-of-session marker — controls one-time fade-in animations.
  // Without this, fade-up classes would replay on every full-page reload
  // (since ajax-nav is disabled), causing visible jitter on each navigation.
  try {
    if (!sessionStorage.getItem('eduguide_visited')) {
      sessionStorage.setItem('eduguide_visited', '1');
      root.setAttribute('data-first-visit', 'true');
      // Strip the marker after the first paint cycle so it doesn't re-trigger
      // on subsequent same-page paints.
      setTimeout(function () { root.removeAttribute('data-first-visit'); }, 600);
    }
  } catch (_) {}

  // React to system preference changes only when user is on 'auto'.
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = function () {
      const current = getSavedPreference() || 'auto';
      if (current === 'auto') applyTheme('auto');
    };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);  // Safari < 14
  }

  // Public API
  window.EduGuideTheme = {
    get: function () { return getSavedPreference() || 'auto'; },
    getEffective: function () { return root.dataset.themeEffective || getSystemTheme(); },
    set: function (mode) {
      if (!['light', 'dark', 'auto'].includes(mode)) return;
      savePreference(mode);
      applyTheme(mode);
      window.dispatchEvent(new CustomEvent('themechange', { detail: { mode: mode, effective: root.dataset.themeEffective } }));
    },
    toggle: function () {
      // Cycle: auto → light → dark → auto
      const cur = window.EduGuideTheme.get();
      const next = cur === 'auto' ? 'light' : cur === 'light' ? 'dark' : 'auto';
      window.EduGuideTheme.set(next);
      return next;
    },
    /** Quick toggle: just light ↔ dark (ignores 'auto'). */
    flip: function () {
      const eff = window.EduGuideTheme.getEffective();
      window.EduGuideTheme.set(eff === 'dark' ? 'light' : 'dark');
    },
  };

  // Wire any element with class `theme-toggle` (no per-page code needed)
  function wireToggleButtons() {
    document.querySelectorAll('.theme-toggle').forEach(btn => {
      if (btn.dataset.themeWired) return;
      btn.dataset.themeWired = '1';
      btn.addEventListener('click', function () { window.EduGuideTheme.flip(); });
      // Tooltip hint
      if (!btn.hasAttribute('aria-label')) {
        btn.setAttribute('aria-label', 'Đổi giao diện sáng/tối');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireToggleButtons);
  } else {
    wireToggleButtons();
  }
  // Re-wire after AJAX nav swaps
  window.addEventListener('ajax:navigated', wireToggleButtons);
})();
