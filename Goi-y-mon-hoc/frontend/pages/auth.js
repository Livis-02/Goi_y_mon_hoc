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
  window.location.replace('index.html');
}

/**
 * Fetch the current authenticated user from GET /auth/me.
 * Returns the user object on success, or null on failure.
 * If the token is invalid the user is redirected to login.
 */
async function getCurrentUser() {
  const token = getToken();
  if (!token) { window.location.replace('index.html'); return null; }
  try {
    const res = await fetch(`${window.API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      if (res.status === 401) {
        localStorage.removeItem('access_token');
        window.location.replace('index.html');
      }
      return null;
    }
    const user = await res.json();
    // Setup gate: nếu chưa thiết lập tài khoản (email + MK), bounce về index để bắt setup
    if (user && user.is_first_login && !/(\/|^)index\.html$/.test(window.location.pathname)) {
      window.location.replace('index.html');
      return null;
    }
    return user;
  } catch (_) {
    return null;
  }
}
