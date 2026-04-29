/**
 * sidebar-init.js — synchronous sidebar injection + nav state wiring.
 *
 * Usage: load this file in <head>, ensure a <div id="sidebarMount"></div>
 * exists in <body>. The sidebar is injected on DOMContentLoaded with no
 * async fetch, eliminating the layout-shift jitter when navigating pages.
 */

const _SIDEBAR_STUDENT_HTML = `
<aside id="sidebarDrawer" class="fixed left-0 top-0 h-screen w-60 flex flex-col py-5 px-3 bg-slate-900 z-50 shadow-lg transition-transform duration-300 -translate-x-full lg:translate-x-0">
  <div class="flex items-center gap-3 px-3 mb-7">
    <div class="w-9 h-9 rounded-xl flex items-center justify-center text-white flex-shrink-0 shadow" style="background:linear-gradient(135deg,#4F46E5,#6366f1)">
      <span class="material-symbols-outlined msym text-lg" style="font-variation-settings:'FILL' 1">school</span>
    </div>
    <div>
      <h1 class="text-sm font-extrabold text-white leading-none tracking-tight">EduGuide</h1>
      <p class="text-[10px] text-slate-400 mt-0.5">Cổng Sinh viên · CNTT</p>
    </div>
  </div>
  <div class="mx-2 mb-5 p-3 bg-slate-800 rounded-xl">
    <div class="flex items-center gap-2.5 mb-2">
      <div class="w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0" id="avatarCircle" style="background:linear-gradient(135deg,#4F46E5,#6366f1)">?</div>
      <div class="overflow-hidden flex-1 min-w-0">
        <p class="text-sm font-semibold text-white truncate" id="sidebarUserName">Đang tải...</p>
        <p class="text-[10px] text-slate-400 truncate" id="sidebarSpec">CNTT 7480201</p>
      </div>
    </div>
    <div id="sidebarProgressWrap" class="hidden">
      <div class="flex items-center justify-between mb-1">
        <span class="text-[9px] text-slate-500 uppercase tracking-wide">Tiến độ TC</span>
        <span class="text-[9px] font-bold text-indigo-400" id="sidebarProgressLabel">0%</span>
      </div>
      <div class="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden">
        <div id="sidebarProgressBar" class="h-full rounded-full transition-colors duration-700" style="width:0%;background:linear-gradient(135deg,#4F46E5,#6366f1)"></div>
      </div>
    </div>
  </div>
  <nav class="flex-1 space-y-0.5 overflow-y-auto" id="sideNav">
    <p class="text-[9px] font-bold text-slate-600 uppercase tracking-widest px-4 mb-2">Học tập</p>
    <a href="home.html" data-page="home.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">dashboard</span>Tổng quan</a>
    <a href="grades.html" data-page="grades.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">grade</span>Bảng điểm</a>
    <a href="roadmap.html" data-page="roadmap.html" data-hub-pages="ctdt.html,goals.html,readiness.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">route</span>Lộ trình</a>
    <a href="compare-specs.html" data-page="compare-specs.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">compare</span>So sánh chuyên ngành</a>
    <p class="text-[9px] font-bold text-slate-600 uppercase tracking-widest px-4 mb-2 mt-4">Định hướng nghề</p>
    <a href="career-hub.html" data-page="career-hub.html" data-hub-pages="career-quiz.html,skill-tree.html,compare-plans.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">rocket_launch</span>Hướng nghề</a>
    <p class="text-[9px] font-bold text-slate-600 uppercase tracking-widest px-4 mb-2 mt-4">Hỗ trợ</p>
    <a href="messaging.html" data-page="messaging.html" data-hub-pages="ai-chat.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">forum</span>Trao đổi</a>
    <a href="notifications.html" data-page="notifications.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">notifications</span>Thông báo<span id="sidebarNotifBadge" class="hidden ml-auto min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">0</span></a>
    <a href="settings.html" data-page="settings.html" data-hub-pages="my-reviews.html" class="sidebar-link w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors"><span class="material-symbols-outlined msym text-xl">settings</span>Hồ sơ &amp; Cài đặt</a>
  </nav>
  <div class="border-t border-slate-800 pt-3 mt-3">
    <button id="sidebarLogoutBtn" class="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm text-slate-400 hover:bg-red-900/40 hover:text-red-400 transition-colors">
      <span class="material-symbols-outlined msym text-xl">logout</span>Đăng xuất
    </button>
  </div>
</aside>
<div id="sidebarOverlay" class="hidden fixed inset-0 bg-black/60 z-40 lg:hidden"></div>
<style>
  .sidebar-link { color: #94a3b8; }
  .sidebar-link:hover { background: #1e293b; color: #e2e8f0; }
  .sidebar-link.active { background: linear-gradient(135deg,#4f46e5,#7c3aed); color: #fff; font-weight: 600; }
</style>
`;

function renderSidebar() {
  const mount = document.getElementById('sidebarMount');
  if (!mount) return;
  mount.innerHTML = _SIDEBAR_STUDENT_HTML;
  initSidebarFragment();
}

function initSidebarFragment() {
  const page = window.location.pathname.split('/').pop() || 'home.html';
  document.querySelectorAll('.sidebar-link').forEach(function (a) {
    let isActive = a.dataset.page === page;
    // Hub items: also active when on any sub-page (e.g. career-hub active on career-quiz/skill-tree/...)
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

// Synchronous injection as early as possible
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', renderSidebar);
} else {
  renderSidebar();
}
