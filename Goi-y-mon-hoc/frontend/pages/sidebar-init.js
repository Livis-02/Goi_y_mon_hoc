/**
 * sidebar-init.js — synchronous sidebar injection + nav state wiring.
 *
 * Usage: load this file in <head>, ensure a <div id="sidebarMount"></div>
 * exists in <body>.
 *
 * IA (redesign v3 2026-05-08): trật tự dẫn dắt SV theo flow đúng.
 *   ĐỊNH HƯỚNG: Tổng quan, Mục tiêu nghề (chọn TRƯỚC để AI gợi ý TC chính xác)
 *   HỌC TẬP:    Lộ trình tích hợp, Bảng điểm
 *   HỖ TRỢ:     Trợ lý AI, Hỏi cố vấn, Thông báo
 *
 *   Lý do đảo: career_goal tác động đến /recommendations/me (preferred_track,
 *   skill alignment, LLM context). SV nên chọn nghề trước → roadmap sau.
 */

const _SIDEBAR_STUDENT_HTML = `
<aside id="sidebarDrawer" class="fixed left-0 top-0 h-screen w-60 flex flex-col bg-surface border-r border-border-default z-50 transition-transform duration-300 -translate-x-full lg:translate-x-0">

  <!-- Logo -->
  <div class="flex items-center gap-2.5 px-5 py-5 flex-shrink-0">
    <div class="w-8 h-8 rounded-md flex items-center justify-center text-white flex-shrink-0 pri-grad shadow-sm">
      <span class="material-symbols-outlined msym text-base" style="font-variation-settings:'FILL' 1">school</span>
    </div>
    <div>
      <h1 class="text-sm font-bold text-text-primary leading-none tracking-tight">EduGuide</h1>
      <p class="text-[10px] text-text-tertiary mt-1 font-medium" id="sidebarRoleLabel">Cổng sinh viên</p>
    </div>
  </div>

  <!-- User info -->
  <div class="mx-3 mb-3 p-3 rounded-lg bg-surface-subtle border border-border-subtle flex-shrink-0">
    <div class="flex items-center gap-2.5 mb-2">
      <div class="w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0 pri-grad" id="avatarCircle">?</div>
      <div class="overflow-hidden flex-1 min-w-0">
        <p class="text-sm font-semibold text-text-primary truncate" id="sidebarUserName">Đang tải...</p>
        <p class="text-[11px] text-text-tertiary truncate" id="sidebarSpec">CNTT 7480201</p>
      </div>
    </div>
    <div id="sidebarProgressWrap" class="hidden">
      <div class="flex items-center justify-between mb-1">
        <span class="text-[10px] text-text-tertiary font-medium">Tín chỉ</span>
        <span class="text-[10px] font-bold text-text-primary" id="sidebarProgressLabel">0%</span>
      </div>
      <div class="h-1 w-full bg-border-default rounded-full overflow-hidden">
        <div id="sidebarProgressBar" class="h-full rounded-full transition-all duration-700 bg-accent" style="width:0%"></div>
      </div>
    </div>
  </div>

  <!-- Nav: 3 groups -->
  <nav class="flex-1 overflow-y-auto px-2 pb-2" id="sideNav">

    <p class="sidebar-group-label">Định hướng</p>
    <a href="home.html" data-page="home.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">dashboard</span>Tổng quan
    </a>
    <a href="career-goal.html" data-page="career-goal.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">rocket_launch</span>Mục tiêu nghề
      <span id="sidebarCareerFitBadge" class="hidden ml-auto pill pill-accent">0%</span>
    </a>

    <p class="sidebar-group-label">Học tập</p>
    <a href="integrated-roadmap.html" data-page="integrated-roadmap.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">route</span>Lộ trình
    </a>
    <a href="grades.html" data-page="grades.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">grade</span>Bảng điểm
    </a>

    <p class="sidebar-group-label">Hỗ trợ</p>
    <a href="ai-chat.html" data-page="ai-chat.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">smart_toy</span>Trợ lý AI
    </a>
    <a href="messaging.html" data-page="messaging.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">forum</span>Hỏi cố vấn
      <span id="sidebarMsgBadge" class="hidden ml-auto min-w-[18px] h-[18px] px-1 bg-danger text-white text-[10px] font-bold rounded-full flex items-center justify-center">0</span>
    </a>
    <a href="notifications.html" data-page="notifications.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">notifications</span>Thông báo
      <span id="sidebarNotifBadge" class="hidden ml-auto min-w-[18px] h-[18px] px-1 bg-danger text-white text-[10px] font-bold rounded-full flex items-center justify-center">0</span>
    </a>
  </nav>

  <!-- A3: Advisor widget — hiện khi SV được phân công cố vấn. Click → open FAB tab Cố vấn. -->
  <div id="sidebarAdvisorWidget" class="hidden mx-3 mb-2 p-2.5 rounded-lg bg-[#ecfdf5] border border-[#a7f3d0] flex-shrink-0">
    <p class="text-[10px] uppercase tracking-wider font-semibold text-[#047857] mb-1.5">Cố vấn của bạn</p>
    <div class="flex items-center gap-2 mb-2">
      <div id="sidebarAdvisorAvatar" class="w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-[11px] flex-shrink-0" style="background:linear-gradient(135deg,#22c55e,#10b981)">?</div>
      <div class="overflow-hidden flex-1 min-w-0">
        <p id="sidebarAdvisorName" class="text-[12px] font-semibold text-[#064e3b] truncate leading-tight">—</p>
        <p id="sidebarAdvisorRole" class="text-[10px] text-[#047857] truncate">Cố vấn học tập</p>
      </div>
    </div>
    <button onclick="if(window.openAdvisorChat)window.openAdvisorChat('')"
      class="w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md bg-[#10b981] text-white text-[11px] font-semibold hover:bg-[#059669] transition">
      <span class="material-symbols-outlined msym" style="font-size:14px">chat</span>
      Nhắn tin nhanh
    </button>
  </div>

  <!-- Bottom: theme toggle + logout -->
  <div class="border-t border-border-subtle px-2 py-3 flex-shrink-0 flex items-center gap-1">
    <button id="sidebarLogoutBtn" class="flex-1 flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-text-secondary hover:bg-danger-soft hover:text-danger transition-colors">
      <span class="material-symbols-outlined msym text-[20px]">logout</span>Đăng xuất
    </button>
    <button class="theme-toggle" data-tooltip="Sáng/Tối">
      <span class="material-symbols-outlined msym text-[18px] icon-moon">dark_mode</span>
      <span class="material-symbols-outlined msym text-[18px] icon-sun">light_mode</span>
    </button>
  </div>
</aside>
<div id="sidebarOverlay" class="hidden fixed inset-0 bg-[var(--surface-overlay)] z-40 lg:hidden backdrop-blur-sm"></div>
`;

// ── ADVISOR sidebar template ────────────────────────────────────────────────
const _SIDEBAR_ADVISOR_HTML = `
<aside id="sidebarDrawer" class="fixed left-0 top-0 h-screen w-60 flex flex-col bg-surface border-r border-border-default z-50 transition-transform duration-300 -translate-x-full lg:translate-x-0">

  <!-- Logo -->
  <div class="flex items-center gap-2.5 px-5 py-5 flex-shrink-0">
    <div class="w-8 h-8 rounded-md flex items-center justify-center text-white flex-shrink-0 pri-grad shadow-sm">
      <span class="material-symbols-outlined msym text-base" style="font-variation-settings:'FILL' 1">school</span>
    </div>
    <div>
      <h1 class="text-sm font-bold text-text-primary leading-none tracking-tight">EduGuide</h1>
      <p class="text-[10px] text-text-tertiary mt-1 font-medium" id="sidebarRoleLabel">Cố vấn học tập</p>
    </div>
  </div>

  <!-- User info -->
  <div class="mx-3 mb-3 p-3 rounded-lg bg-surface-subtle border border-border-subtle flex-shrink-0">
    <div class="flex items-center gap-2.5">
      <div class="w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0 pri-grad" id="avatarCircle">?</div>
      <div class="overflow-hidden flex-1 min-w-0">
        <p class="text-sm font-semibold text-text-primary truncate" id="sidebarUserName">Đang tải...</p>
        <p class="text-[11px] text-text-tertiary truncate" id="sidebarSpec">Cố vấn học tập</p>
      </div>
    </div>
  </div>

  <!-- Nav -->
  <nav class="flex-1 overflow-y-auto px-2 pb-2" id="sideNav">

    <p class="sidebar-group-label">Quản lý</p>
    <a href="advisor.html#overview" data-page="advisor.html" data-section="overview" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">priority_high</span>Cần chú ý
    </a>
    <a href="advisor.html#students" data-page="advisor.html" data-section="students" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">groups</span>Sinh viên của tôi
    </a>
    <a href="advisor.html#assign" data-page="advisor.html" data-section="assign" id="sidebarAssignLink" class="hidden sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">manage_accounts</span>Phân công SV
    </a>

    <p class="sidebar-group-label">Tham chiếu</p>
    <a href="advisor.html#ctdt" data-page="advisor.html" data-section="ctdt" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">schema</span>Sơ đồ CTĐT
    </a>

    <p class="sidebar-group-label">Hỗ trợ</p>
    <a href="messaging.html" data-page="messaging.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">forum</span>Trao đổi
      <span id="sidebarMsgBadge" class="hidden ml-auto min-w-[18px] h-[18px] px-1 bg-danger text-white text-[10px] font-bold rounded-full flex items-center justify-center">0</span>
    </a>
    <a href="notifications.html" data-page="notifications.html" class="sidebar-link">
      <span class="material-symbols-outlined msym text-[20px]">notifications</span>Thông báo
      <span id="sidebarNotifBadge" class="hidden ml-auto min-w-[18px] h-[18px] px-1 bg-danger text-white text-[10px] font-bold rounded-full flex items-center justify-center">0</span>
    </a>
  </nav>

  <!-- Bottom: theme toggle + logout -->
  <div class="border-t border-border-subtle px-2 py-3 flex-shrink-0 flex items-center gap-1">
    <button id="sidebarLogoutBtn" class="flex-1 flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-text-secondary hover:bg-danger-soft hover:text-danger transition-colors">
      <span class="material-symbols-outlined msym text-[20px]">logout</span>Đăng xuất
    </button>
    <button class="theme-toggle" data-tooltip="Sáng/Tối">
      <span class="material-symbols-outlined msym text-[18px] icon-moon">dark_mode</span>
      <span class="material-symbols-outlined msym text-[18px] icon-sun">light_mode</span>
    </button>
  </div>
</aside>
<div id="sidebarOverlay" class="hidden fixed inset-0 bg-[var(--surface-overlay)] z-40 lg:hidden backdrop-blur-sm"></div>
`;

function _getCachedRole() {
  try { return (localStorage.getItem('user_role') || 'student').toLowerCase(); }
  catch (_) { return 'student'; }
}

function _pickSidebarHtml(role) {
  if (role === 'advisor' || role === 'admin') return _SIDEBAR_ADVISOR_HTML;
  return _SIDEBAR_STUDENT_HTML;
}

let _renderedRole = null;

function renderSidebar() {
  const mount = document.getElementById('sidebarMount');
  if (!mount) return;
  const role = _getCachedRole();
  mount.innerHTML = _pickSidebarHtml(role);
  _renderedRole = role;
  initSidebarFragment();
}

// Re-render if cached role changes after /auth/me resolves
function _maybeReRenderSidebar() {
  const role = _getCachedRole();
  if (role !== _renderedRole) {
    renderSidebar();
  }
}

// ── Sidebar user/progress state (self-managed, survives ajax-nav) ──────────
let _cachedUser = null;
let _cachedProgress = null;

function _specName(code) {
  const m = { '7480201_07': 'KHMT', '7480201_06': 'MMT', '7480201_05': 'CNPM', '7480201_09': 'HTTT', '7480201_04': 'THKT', '7480201_08': 'CNTTDH' };
  return m[code] || (code || 'CNTT 7480201');
}

// localStorage cache helpers — fix layout shift khi nav (MPA full reload mất state).
// Strategy: render từ cache ngay (sync), fetch refresh background (stale-while-revalidate).
function _sbCacheGet(key) {
  try { return JSON.parse(localStorage.getItem('sb_' + key) || 'null'); }
  catch (_) { return null; }
}
function _sbCacheSet(key, value) {
  try { localStorage.setItem('sb_' + key, JSON.stringify(value)); } catch (_) {}
}

// Sync render: chỉ chạm DOM, không fetch. Dùng cho cả cache-apply và fetch-result.
function _renderUserUI(u) {
  if (!u) return;
  const name = u.full_name || u.username || '';
  const initials = name.trim().split(/\s+/).map(function (w) { return w[0]; }).filter(Boolean).slice(-2).join('').toUpperCase() || '?';
  const sName = document.getElementById('sidebarUserName');
  const avatar = document.getElementById('avatarCircle');
  const sSpec = document.getElementById('sidebarSpec');
  if (sName) sName.textContent = name;
  if (avatar) avatar.textContent = initials;
  if (sSpec) {
    if (u.role === 'student' && u.specialization) sSpec.textContent = _specName(u.specialization);
    else if (u.role === 'advisor') sSpec.textContent = u.is_head_of_department ? 'Trưởng bộ môn' : 'Cố vấn học tập';
    else if (u.role === 'admin') sSpec.textContent = 'Quản trị viên';
  }
  const assignLink = document.getElementById('sidebarAssignLink');
  if (assignLink && u.role === 'advisor' && u.is_head_of_department) {
    assignLink.classList.remove('hidden');
  }
}

function _renderProgressUI(p) {
  if (!p) return;
  const earned = p.earned_credits || 0;
  const pct = Math.min(100, Math.round((earned / 153) * 100));
  const wrap = document.getElementById('sidebarProgressWrap');
  const label = document.getElementById('sidebarProgressLabel');
  const bar = document.getElementById('sidebarProgressBar');
  if (wrap) wrap.classList.remove('hidden');
  if (label) label.textContent = pct + '%';
  if (bar) bar.style.width = pct + '%';
}

async function _loadSidebarUserInfo(forceRefresh) {
  const tok = (typeof getToken === 'function') ? getToken() : null;
  if (!tok) return;
  const apiBase = window.API_BASE || (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : location.origin);

  // 1. Apply cache TRƯỚC (instant render, không layout shift)
  if (!_cachedUser) {
    _cachedUser = _sbCacheGet('user');
    if (_cachedUser) _renderUserUI(_cachedUser);
  }
  if (!_cachedProgress) {
    _cachedProgress = _sbCacheGet('progress');
    if (_cachedProgress) _renderProgressUI(_cachedProgress);
  }

  // 2. Fetch fresh data (background refresh) — use deduped fetcher from auth.js
  // để các callers concurrent (home init + floating-chat) share 1 request thay
  // vì 3x parallel calls ⇒ 3 re-renders.
  if (forceRefresh || !_cachedUser) {
    try {
      const fresh = (typeof window._dedupedAuthMeFetch === 'function')
        ? await window._dedupedAuthMeFetch(tok)
        : await fetch(apiBase + '/auth/me', { headers: { Authorization: 'Bearer ' + tok } }).then(r => r.ok ? r.json() : null).catch(() => null);
      if (fresh) {
        _cachedUser = fresh;
        _sbCacheSet('user', _cachedUser);
      }
    } catch (_) {}
  }
  if (_cachedUser && _cachedUser.role) {
    try { localStorage.setItem('user_role', _cachedUser.role); } catch (_) {}
    _maybeReRenderSidebar();
  }
  const role = (_cachedUser && _cachedUser.role) || 'student';
  if (role === 'student' && (forceRefresh || !_cachedProgress)) {
    try {
      const r = await fetch(apiBase + '/progress/me', { headers: { Authorization: 'Bearer ' + tok } });
      if (r.ok) {
        _cachedProgress = await r.json();
        _sbCacheSet('progress', _cachedProgress);
      }
    } catch (_) {}
  }

  // 3. Re-render với fresh data (overwrite cache state nếu khác)
  _renderUserUI(_cachedUser);
  _renderProgressUI(_cachedProgress);
}

window.refreshSidebarUserInfo = function (force) { _loadSidebarUserInfo(force === true); };

function initSidebarFragment() {
  const page = window.location.pathname.split('/').pop() || 'home.html';
  const hash = (window.location.hash || '').replace('#', '');
  const links = Array.from(document.querySelectorAll('.sidebar-link'));
  // Group links by page so we can do hash-aware active picking
  const sameP = links.filter(a => a.dataset.page === page);
  const hasHashLinks = sameP.some(a => a.dataset.section);
  links.forEach(function (a) {
    let isActive = false;
    if (a.dataset.page === page) {
      if (hasHashLinks) {
        if (a.dataset.section) {
          // Match section to hash; if no hash, fall back to first section link
          if (hash) isActive = a.dataset.section === hash;
          else isActive = a === sameP.find(x => x.dataset.section); // first
        }
      } else {
        isActive = true;
      }
    }
    if (!isActive && a.dataset.hubPages) {
      const subPages = a.dataset.hubPages.split(',').map(s => s.trim());
      if (subPages.includes(page)) isActive = true;
    }
    a.classList.toggle('active', isActive);
  });

  document.getElementById('sidebarLogoutBtn')?.addEventListener('click', function () {
    if (typeof logout === 'function') logout();
    else { localStorage.removeItem('access_token'); window.location.replace('index.html'); }
  });

  document.getElementById('sidebarOverlay')?.addEventListener('click', closeSidebar);

  _loadCareerFitBadge();
  _loadSidebarUserInfo(false);
  _loadSidebarAdvisor();  // A3: Hiện widget cố vấn nếu SV được assigned
  _startBadgePolling();   // A1 (light): Poll Tin nhắn + Thông báo badges trên sidebar
}

function _renderCareerFitUI(pct) {
  const badge = document.getElementById('sidebarCareerFitBadge');
  if (!badge) return;
  if (pct != null && pct >= 0) {
    badge.textContent = pct + '%';
    badge.classList.remove('hidden');
  }
}

async function _loadCareerFitBadge() {
  const badge = document.getElementById('sidebarCareerFitBadge');
  if (!badge) return;
  // 1. Apply cache instant (tránh badge pop-in khi nav)
  const cachedPct = _sbCacheGet('career_fit');
  if (typeof cachedPct === 'number') _renderCareerFitUI(cachedPct);

  // 2. Fetch refresh background
  const tok = (typeof getToken === 'function') ? getToken() : null;
  if (!tok) return;
  try {
    const apiBase = window.API_BASE || (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : location.origin);
    const r = await fetch(apiBase + '/v2/career/fit/me', { headers: { Authorization: 'Bearer ' + tok } });
    if (!r.ok) return;
    const d = await r.json();
    if (d.has_blueprint && d.fit_percent >= 0) {
      _sbCacheSet('career_fit', d.fit_percent);
      _renderCareerFitUI(d.fit_percent);
    }
  } catch (_) {}
}

// A1 (light): Poll badges cho sidebar — Tin nhắn + Thông báo. Hiện trên MỌI page
// (sidebar-init.js load mọi page). Trước đây chỉ home/notifications mới populate
// → page khác badge ẩn vô hình. Bây giờ luôn update.
// + localStorage cache → render instant tránh badge pop-in khi navigate.
let _badgePollTimer = null;

function _setBadge(id, count) {
  const el = document.getElementById(id);
  if (!el) return;
  if (count > 0) {
    el.textContent = count > 9 ? '9+' : String(count);
    el.classList.remove('hidden');
  } else {
    el.classList.add('hidden');
  }
}

function _renderBadgesUI(notifCount, msgCount) {
  if (typeof notifCount === 'number') _setBadge('sidebarNotifBadge', notifCount);
  if (typeof msgCount === 'number') _setBadge('sidebarMsgBadge', msgCount);
}

async function _loadSidebarBadges() {
  // 1. Apply cache instant
  const cached = _sbCacheGet('badges');
  if (cached) _renderBadgesUI(cached.notif, cached.msg);

  // 2. Fetch refresh background
  const tok = (typeof getToken === 'function') ? getToken() : null;
  if (!tok) return;
  const apiBase = window.API_BASE || (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : location.origin);
  const headers = { Authorization: 'Bearer ' + tok };
  let notifCount = cached?.notif;
  let msgCount   = cached?.msg;
  try {
    const r = await fetch(apiBase + '/notifications/me/unread-count', { headers });
    if (r.ok) {
      const d = await r.json();
      notifCount = d.unread || d.count || 0;
    }
  } catch (_) {}
  const role = (_cachedUser && _cachedUser.role) || _getCachedRole();
  if (role === 'student' || role === 'advisor') {
    try {
      const r = await fetch(apiBase + '/messages/direct/unread/count', { headers });
      if (r.ok) {
        const d = await r.json();
        msgCount = d.total || 0;
      }
    } catch (_) {}
  } else {
    msgCount = 0;
  }
  _sbCacheSet('badges', { notif: notifCount, msg: msgCount });
  _renderBadgesUI(notifCount, msgCount);
}

function _startBadgePolling() {
  if (_badgePollTimer) return;
  _loadSidebarBadges();
  _badgePollTimer = setInterval(_loadSidebarBadges, 60000);
}

// A3: Load advisor info → populate sidebar widget. Chỉ áp dụng cho SV.
// localStorage cache: render instant, fetch refresh background.
let _cachedAdvisor = null;
let _advisorFetched = false;

function _renderAdvisorUI(advisor) {
  const widget = document.getElementById('sidebarAdvisorWidget');
  if (!widget) return;
  if (!advisor) {
    widget.classList.add('hidden');
    return;
  }
  const name = advisor.full_name || advisor.username || 'Cố vấn';
  const initials = name.trim().split(/\s+/).map(w => w[0]).filter(Boolean).slice(-2).join('').toUpperCase() || '?';
  const nameEl = document.getElementById('sidebarAdvisorName');
  const avatarEl = document.getElementById('sidebarAdvisorAvatar');
  const roleEl = document.getElementById('sidebarAdvisorRole');
  if (nameEl) nameEl.textContent = name;
  if (avatarEl) avatarEl.textContent = initials;
  if (roleEl) {
    let label = 'Cố vấn học tập';
    if (advisor.is_head_of_department) label = 'Trưởng bộ môn';
    if (advisor.teacher_code) label += ` · ${advisor.teacher_code}`;
    roleEl.textContent = label;
  }
  widget.classList.remove('hidden');
}

async function _loadSidebarAdvisor() {
  const widget = document.getElementById('sidebarAdvisorWidget');
  if (!widget) return;
  const role = (_cachedUser && _cachedUser.role) || _getCachedRole();
  if (role !== 'student') return;

  // 1. Apply cache instant (tránh widget pop-in khi nav)
  if (!_cachedAdvisor) {
    _cachedAdvisor = _sbCacheGet('advisor');
    if (_cachedAdvisor) _renderAdvisorUI(_cachedAdvisor);
  }

  // 2. Fetch refresh background (chỉ 1 lần per page-load — module-level guard)
  const tok = (typeof getToken === 'function') ? getToken() : null;
  if (!tok) return;
  if (!_advisorFetched) {
    try {
      const apiBase = window.API_BASE || (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? 'http://127.0.0.1:8000' : location.origin);
      const r = await fetch(apiBase + '/me/advisor', { headers: { Authorization: 'Bearer ' + tok } });
      if (r.ok) {
        const d = await r.json();
        _cachedAdvisor = d.advisor || null;
        _sbCacheSet('advisor', _cachedAdvisor);
        _renderAdvisorUI(_cachedAdvisor);
      }
      _advisorFetched = true;
    } catch (_) {}
  }
}

function toggleSidebar() {
  const el = document.getElementById('sidebarDrawer');
  const ov = document.getElementById('sidebarOverlay');
  if (!el) return;
  const hidden = el.classList.toggle('-translate-x-full');
  if (ov) ov.classList.toggle('hidden', hidden);
}

function closeSidebar() {
  document.getElementById('sidebarDrawer')?.classList.add('-translate-x-full');
  document.getElementById('sidebarOverlay')?.classList.add('hidden');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', renderSidebar);
} else {
  renderSidebar();
}

window.addEventListener('ajax:navigated', function () {
  _loadSidebarUserInfo(false);
  _loadCareerFitBadge();
  // Re-pick active link after navigation (hash may have changed too)
  initSidebarFragment();
});

// Update active state when hash changes within the same page
window.addEventListener('hashchange', function () {
  initSidebarFragment();
});
