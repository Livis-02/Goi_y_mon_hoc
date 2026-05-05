/* theme.js — EduGuide Tailwind tokens (Stripe-inspired, light + dark)
 *
 * Load BEFORE the Tailwind CDN script in every page:
 *   <script src="theme.js"></script>
 *   <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
 *
 * Color tokens reference CSS variables defined in theme.css. The single
 * source of truth lives in theme.css's `:root` and `.dark` blocks — we just
 * expose them to Tailwind utility classes here. Existing markup keeps its
 * `bg-surface`, `text-on-surface`, etc. classes and gets dark mode for free.
 *
 * IMPORTANT: Tailwind v3 CDN replaces `window.tailwind` with its API object
 * when it loads, which discards any `window.tailwind.config` we set first.
 * To survive that, we (a) set the config eagerly here so it's available IF
 * the CDN reads it before overwriting, and (b) re-apply + call refresh()
 * after the CDN script finishes loading. See TW_CONFIG below.
 */
window.__EDUGUIDE_TW_CONFIG = (function () {
  return {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        /* ── Stripe-inspired tokens (preferred for new markup) ── */
        canvas:           'var(--canvas)',
        surface:          'var(--surface)',
        'surface-raised': 'var(--surface-raised)',
        'surface-subtle': 'var(--surface-subtle)',
        'surface-strong': 'var(--surface-strong)',
        'border-subtle':  'var(--border-subtle)',
        'border-default': 'var(--border-default)',
        'border-strong':  'var(--border-strong)',
        'text-primary':   'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-tertiary':  'var(--text-tertiary)',
        'text-disabled':  'var(--text-disabled)',
        accent:           'var(--accent)',
        'accent-hover':   'var(--accent-hover)',
        'accent-soft':    'var(--accent-soft)',
        'accent-soft-hi': 'var(--accent-soft-hi)',
        success:          'var(--success)',
        'success-soft':   'var(--success-soft)',
        warning:          'var(--warning)',
        'warning-soft':   'var(--warning-soft)',
        danger:           'var(--danger)',
        'danger-soft':    'var(--danger-soft)',
        info:             'var(--info)',
        'info-soft':      'var(--info-soft)',

        /* ── Legacy M3 token aliases (existing markup) ──────────
           Mapped to new CSS vars so old class names auto-flip on
           dark mode without rewriting every page. */
        background:                  'var(--canvas)',
        'on-background':             'var(--text-primary)',
        'on-surface':                'var(--text-primary)',
        'on-surface-variant':        'var(--text-secondary)',
        'surface-bright':            'var(--surface)',
        'surface-dim':               'var(--surface-strong)',
        'surface-variant':           'var(--surface-strong)',
        'surface-container-lowest':  'var(--surface)',
        'surface-container-low':     'var(--surface-subtle)',
        'surface-container':         'var(--surface-subtle)',
        'surface-container-high':    'var(--surface-strong)',
        'surface-container-highest': 'var(--surface-strong)',
        'surface-tint':              'var(--accent)',
        'inverse-surface':           'var(--text-primary)',
        'inverse-on-surface':        'var(--surface)',
        outline:                     'var(--text-tertiary)',
        'outline-variant':           'var(--border-default)',
        primary:                     'var(--accent)',
        'on-primary':                'var(--text-on-accent)',
        'primary-container':         'var(--accent-hover)',
        'on-primary-container':      'var(--text-on-accent)',
        'primary-fixed':             'var(--accent-soft)',
        'primary-fixed-dim':         'var(--accent-soft-hi)',
        'on-primary-fixed':          'var(--accent)',
        'primary-light':             'var(--accent-soft)',
        'inverse-primary':           'var(--accent-soft-hi)',
        secondary:                   'var(--success)',
        'on-secondary':              'var(--text-on-accent)',
        'secondary-container':       'var(--success-soft)',
        'on-secondary-container':    'var(--success)',
        'secondary-fixed':           'var(--success-soft)',
        'on-secondary-fixed':        'var(--success)',
        tertiary:                    'var(--accent-hover)',
        'on-tertiary':               'var(--text-on-accent)',
        'tertiary-container':        'var(--accent-active, #4d44d6)',
        'on-tertiary-container':     'var(--text-on-accent)',
        'tertiary-fixed':            'var(--accent-soft)',
        'on-tertiary-fixed':         'var(--accent)',
        error:                       'var(--danger)',
        'on-error':                  'var(--text-on-accent)',
        'error-container':           'var(--danger-soft)',
        'on-error-container':        'var(--danger)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        h1: ['Inter'], h2: ['Inter'], h3: ['Inter'],
        'body-lg': ['Inter'], 'body-md': ['Inter'], 'body-sm': ['Inter'],
        'label-md': ['Inter'], 'label-sm': ['Inter'],
      },
      fontSize: {
        h1:        ['36px', { lineHeight: '1.2', letterSpacing: '-0.02em', fontWeight: '700' }],
        h2:        ['30px', { lineHeight: '1.3', letterSpacing: '-0.01em', fontWeight: '600' }],
        h3:        ['24px', { lineHeight: '1.3',                          fontWeight: '600' }],
        'body-lg': ['18px', { lineHeight: '1.6', fontWeight: '400' }],
        'body-md': ['16px', { lineHeight: '1.5', fontWeight: '400' }],
        'body-sm': ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        'label-md':['14px', { lineHeight: '1.2', fontWeight: '600' }],
        'label-sm':['12px', { lineHeight: '1.2', fontWeight: '500' }],
      },
      spacing: {
        xs:    '4px',
        base:  '4px',
        sm:    '8px',
        md:    '16px',
        lg:    '24px',
        xl:    '32px',
        '2xl': '48px',
        gutter:'24px',
        margin:'32px',
      },
      borderRadius: {
        DEFAULT: '0.375rem',
        sm:      '0.375rem',
        md:      '0.5rem',
        lg:      '0.75rem',
        xl:      '1rem',
        '2xl':   '1.25rem',
      },
      boxShadow: {
        xs:  'var(--shadow-xs)',
        sm:  'var(--shadow-sm)',
        md:  'var(--shadow-md)',
        lg:  'var(--shadow-lg)',
        pop: 'var(--shadow-pop)',
      },
      maxWidth: {
        app: '1280px',
      },
      transitionTimingFunction: {
        ease: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  };
})();

// Eager apply — works if Tailwind CDN reads config before overwriting window.tailwind
window.tailwind = window.tailwind || {};
window.tailwind.config = window.__EDUGUIDE_TW_CONFIG;

// Re-apply after Tailwind CDN finishes loading. The CDN replaces
// `window.tailwind` with its API object (discarding our pre-set config),
// then watches DOM mutations and JIT-compiles classes it sees. Strategy:
//   1. Wait until the API is available (`resolveConfig` is exposed by CDN).
//   2. Re-set `tailwind.config` to our saved copy.
//   3. Trigger one DOM mutation so the JIT picks up custom tokens like
//      `bg-primary` — the CDN re-scans and generates rules from the
//      restored config.
(function () {
  const TW_CFG = window.__EDUGUIDE_TW_CONFIG;
  let applied = false;

  function isTailwindReady() {
    return !!(window.tailwind && typeof window.tailwind.resolveConfig === 'function');
  }

  function apply() {
    if (applied || !isTailwindReady()) return;
    window.tailwind.config = TW_CFG;
    // Kick the JIT — insert and remove a sentinel element so the CDN's
    // MutationObserver re-runs class extraction with the new config.
    try {
      const ping = document.createElement('div');
      ping.className = 'bg-primary text-on-primary hidden';
      ping.setAttribute('data-tw-config-ping', '1');
      (document.body || document.documentElement).appendChild(ping);
      // Remove on next tick — the observer will have already noticed the insertion
      setTimeout(() => ping.remove(), 0);
    } catch (_) {}
    applied = true;
  }

  // 1. Hook the CDN <script>'s load event if available
  function tryHookCdnScript() {
    const cdn = document.querySelector('script[src*="cdn.tailwindcss.com"]');
    if (!cdn) return false;
    if (isTailwindReady()) {
      apply();
    } else {
      cdn.addEventListener('load', apply, { once: true });
    }
    return true;
  }

  // 2. If CDN script not yet in DOM (theme.js parsed first), observe for it
  if (!tryHookCdnScript()) {
    const obs = new MutationObserver(() => {
      if (tryHookCdnScript()) obs.disconnect();
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(() => obs.disconnect(), 5000);
  }

  // 3. Polling fallback — covers edge cases where load event is missed
  let tries = 0;
  const poll = setInterval(() => {
    if (applied) { clearInterval(poll); return; }
    if (isTailwindReady()) {
      apply();
      clearInterval(poll);
    } else if (++tries > 100) clearInterval(poll); // ~5s max
  }, 50);
})();
