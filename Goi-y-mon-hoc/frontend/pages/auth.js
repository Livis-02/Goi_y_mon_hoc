/**
 * auth.js — Shared authentication utilities
 * Depends on: window.API_BASE being set before this script runs (or sets its own)
 */

/* ── Avatar dropdown (used by all protected pages) ────────────────────────── */
function toggleAvatarMenu() {
  document.getElementById('avatarDropdown')?.classList.toggle('hidden');
}
document.addEventListener('click', function (e) {
  const menu = document.getElementById('avatarMenu');
  if (menu && !menu.contains(e.target)) {
    document.getElementById('avatarDropdown')?.classList.add('hidden');
  }
});

/**
 * Populate the topbar avatar chip and dropdown with user data.
 * Call after getCurrentUser() resolves.
 */
function updateTopbarUser(user) {
  if (!user) return;
  const name = user.full_name || user.username || '';
  const initials = name.trim().split(/\s+/).map(w => w[0]).filter(Boolean).slice(-2).join('').toUpperCase() || '?';
  const roleMap = { student: 'Sinh viên', advisor: 'Cố vấn học tập', admin: 'Quản trị viên' };
  const el = id => document.getElementById(id);
  if (el('topbarUserName'))  el('topbarUserName').textContent  = name;
  if (el('topbarAvatar'))    el('topbarAvatar').textContent    = initials;
  if (el('avatarDropName'))  el('avatarDropName').textContent  = name;
  if (el('avatarDropRole'))  el('avatarDropRole').textContent  = roleMap[user.role] || '';
  if (el('avatarCircle'))    el('avatarCircle').textContent    = initials;
  if (el('sidebarUserName')) el('sidebarUserName').textContent = name;
}

(function () {
  // Set API_BASE if not already defined by the page
  if (!window.API_BASE) {
    window.API_BASE = window.VITE_API_BASE
      || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
          ? 'http://127.0.0.1:8000'
          : window.location.origin);
  }
})();

/** Return the stored access token (string or empty string). */
function getToken() {
  return localStorage.getItem('access_token') || '';
}

/**
 * Redirect to index.html if no token in localStorage.
 * Call at the top of every protected page.
 */
function checkAuth() {
  if (!getToken()) {
    window.location.replace('index.html');
  }
}

/** Clear token and redirect to login. */
async function logout() {
  const token = getToken();
  if (token) {
    try {
      await fetch(`${window.API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (_) { /* ignore network errors on logout */ }
  }
  localStorage.removeItem('access_token');
  try { localStorage.removeItem('user_role'); } catch (_) {}
  try { localStorage.removeItem('fc_thread_id'); } catch (_) {}
  try { localStorage.removeItem('user_me'); } catch (_) {}
  // Clear sidebar caches (sb_* keys) — tránh user mới thấy data user cũ
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && k.startsWith('sb_')) localStorage.removeItem(k);
    }
  } catch (_) {}
  window.location.replace('index.html');
}

/**
 * Shared in-flight promise dedup for /auth/me. Sidebar, floating-chat, page init
 * all fire /auth/me concurrently → 3 redundant requests → 3 re-renders. With
 * dedup, parallel callers share 1 fetch promise → 1 network round-trip.
 * Cleared automatically when the promise settles.
 */
window.__authMeInflight = window.__authMeInflight || null;

function _dedupedAuthMeFetch(token) {
  if (window.__authMeInflight) return window.__authMeInflight;
  window.__authMeInflight = (async () => {
    try {
      const res = await fetch(`${window.API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        if (res.status === 401) {
          localStorage.removeItem('access_token');
          try { localStorage.removeItem('sb_user'); } catch (_) {}
          window.location.replace('index.html');
        }
        return null;
      }
      return await res.json();
    } catch (_) {
      return null;
    } finally {
      // Clear after delay so late callers (vd floating-chat defer 500ms) cũng
      // share. 600ms cover hết các caller trong vòng init đầu của 1 page.
      setTimeout(() => { window.__authMeInflight = null; }, 600);
    }
  })();
  return window.__authMeInflight;
}
window._dedupedAuthMeFetch = _dedupedAuthMeFetch;

/**
 * Fetch the current authenticated user from GET /auth/me.
 * Returns the user object on success, or null on failure.
 * If the token is invalid the user is redirected to login.
 *
 * Uses stale-while-revalidate caching via localStorage (key: sb_user, shared
 * with sidebar-init.js). Subsequent page navs return cached data immediately
 * and refresh in the background — eliminates the 150-200ms perceived gap on
 * every page transition that the MPA full-reload model otherwise creates.
 *
 * Pass `{ skipCache: true }` to force a fresh fetch (e.g. after profile edit).
 */
async function getCurrentUser(opts) {
  const token = getToken();
  if (!token) { window.location.replace('index.html'); return null; }
  const skipCache = !!(opts && opts.skipCache);

  // Try cache first (instant render). Cache shared with sidebar-init.js.
  let cached = null;
  if (!skipCache) {
    try { cached = JSON.parse(localStorage.getItem('sb_user') || 'null'); } catch (_) {}
  }

  // Fire fresh fetch (await it if no cache, otherwise let caller race against it).
  // Uses _dedupedAuthMeFetch to share 1 in-flight request across concurrent callers.
  const fetchFresh = async () => {
    const user = await _dedupedAuthMeFetch(token);
    if (!user) return null;
    if (user.is_first_login && !/(\/|^)index\.html$/.test(window.location.pathname)) {
      window.location.replace('index.html');
      return null;
    }
    // Persist into shared cache so sidebar + future page loads can use it
    try { localStorage.setItem('sb_user', JSON.stringify(user)); } catch (_) {}
    return user;
  };

  if (cached) {
    // Stale-while-revalidate: return cached now, refresh in background. Caller
    // sees instant data; if their page re-paints on /auth/me changes, hook
    // window.refreshSidebarUserInfo or listen for 'user:refreshed' events.
    fetchFresh().then(fresh => {
      if (fresh && JSON.stringify(fresh) !== JSON.stringify(cached)) {
        try { window.dispatchEvent(new CustomEvent('user:refreshed', { detail: fresh })); } catch (_) {}
      }
    });
    return cached;
  }

  return await fetchFresh();
}
