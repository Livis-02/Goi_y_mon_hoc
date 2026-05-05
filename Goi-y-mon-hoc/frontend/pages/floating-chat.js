/**
 * floating-chat.js — Self-contained floating AI chat widget
 * Depends on: auth.js (getToken, window.API_BASE) loaded first
 * Globals exposed: toggleFloatingChat(), openChatWithText(), closeChat()
 *
 * Behavior:
 *  - Single floating FAB + panel, persists across page navigation (ajax-nav).
 *  - Thread per login: 1 thread_id (lưu localStorage.fc_thread_id), tạo mới khi login,
 *    clear khi logout. Cùng 1 lần đăng nhập, mọi tin nhắn dồn vào 1 thread.
 *  - Auto-load history từ server khi mở panel → chuyển page không mất tin nhắn.
 *  - Nút mở rộng (↗) trong header → mở ai-chat.html?thread=<tid> để xem nhiều thread.
 */
(function () {
  // ── Pages where FAB is REDUNDANT (user is already in chat experience):
  //    ai-chat.html (full-page AI chat) + messaging.html (advisor/group chat).
  //    Hide FAB on those routes. Use ajax:navigated event để toggle khi đổi trang
  //    (vì IIFE chỉ chạy 1 lần, các nav sau ko re-execute floating-chat.js).
  function _fcCurrentPath() {
    return (location.pathname.split('/').pop() || '').toLowerCase();
  }
  function _fcOnChatPage() {
    const p = _fcCurrentPath();
    return p === 'ai-chat.html' || p === 'messaging.html';
  }
  function _fcApplyVisibility() {
    const root = document.getElementById('fcRoot');
    const fab  = document.getElementById('fcFab');
    const panel = document.getElementById('fcPanel');
    const hide = _fcOnChatPage();
    if (root)  root.style.display  = hide ? 'none' : '';
    if (fab)   fab.style.display   = hide ? 'none' : 'flex';
    if (panel && hide) {
      panel.style.display = 'none';
      try { _fcOpen = false; } catch (_) {}
    }
  }
  // Listen to ajax-nav navigation events để re-apply visibility mỗi lần đổi trang
  window.addEventListener('ajax:navigated', _fcApplyVisibility);
  window.addEventListener('popstate', _fcApplyVisibility);

  // ── Idempotent guard: nếu đã inject FAB rồi (do ajax-nav re-execute script)
  //    thì skip phần inject — chỉ apply visibility cho route hiện tại.
  if (document.getElementById('fcFab')) {
    _fcApplyVisibility();
    return;
  }

  // ── Role guard: AI tư vấn chỉ áp dụng cho SV.
  //    GV/Admin có conversation riêng (messaging.html với SV phụ trách),
  //    không cần AI bot floating. Check role qua localStorage cached, fallback
  //    qua /auth/me nếu chưa có cache.
  const _role = (function () {
    try { return (localStorage.getItem('user_role') || '').toLowerCase(); }
    catch (_) { return ''; }
  })();
  if (_role && _role !== 'student') return;
  // Nếu chưa có cache role, vẫn cho phép init nhưng kiểm tra async sau khi
  // /auth/me trả về — sẽ self-remove FAB nếu role advisor/admin.
  if (!_role) {
    setTimeout(async function () {
      try {
        const tok = (typeof getToken === 'function') ? getToken() : (localStorage.getItem('access_token') || '');
        if (!tok) return;
        // Try cache trước (đã có sb_user từ sidebar-init / page init), tránh
        // request thừa. Fallback fetch nếu cache miss.
        let me = null;
        try { me = JSON.parse(localStorage.getItem('sb_user') || 'null'); } catch (_) {}
        if (!me) {
          if (typeof window._dedupedAuthMeFetch === 'function') {
            me = await window._dedupedAuthMeFetch(tok);
          } else {
            const r = await fetch((window.API_BASE || 'http://127.0.0.1:8000') + '/auth/me', {
              headers: { Authorization: 'Bearer ' + tok }
            });
            if (!r.ok) return;
            me = await r.json();
          }
        }
        if (!me) return;
        try { localStorage.setItem('user_role', (me.role || '').toLowerCase()); } catch (_) {}
        if (me.role && me.role !== 'student') {
          document.getElementById('fcFab')?.remove();
          document.getElementById('fcPanel')?.remove();
        }
      } catch (_) {}
    }, 500);
  }

  // ── Private helpers ───────────────────────────────────────────────────────
  function _fcApiBase() { return window.API_BASE || 'http://127.0.0.1:8000'; }
  function _fcHeaders(extra = {}) {
    return { Authorization: `Bearer ${(typeof getToken === 'function' ? getToken() : localStorage.getItem('access_token')) || ''}`, ...extra };
  }
  async function _fcCallApi(path, opts = {}, timeoutMs = 30000) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(`${_fcApiBase()}${path}`, { signal: ctrl.signal, ...opts });
      clearTimeout(timer);
      if (res.status === 401) {
        localStorage.removeItem('access_token');
        window.location.replace('index.html');
        return { ok: false, status: 401, data: {} };
      }
      let data; try { data = await res.json(); } catch { data = {}; }
      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      clearTimeout(timer);
      const msg = err?.name === 'AbortError' ? 'Yêu cầu quá thời gian.' : 'Không thể kết nối server.';
      return { ok: false, status: 0, data: { detail: msg } };
    }
  }

  // ── Inject HTML ───────────────────────────────────────────────────────────
  // v9: Dual-tab layout — AI Tư vấn + Cố vấn. Cùng FAB, switch tab trong panel.
  // SV thường có 1 cố vấn (UNIQUE constraint trên student_id), tab Cố vấn = thread DM.
  const _html = `
<!-- Floating Chat FAB (with optional unread badge) -->
<button id="fcFab"
  onclick="toggleFloatingChat()"
  style="position:fixed;bottom:24px;right:24px;z-index:9998;width:52px;height:52px;border-radius:50%;
         background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;cursor:pointer;
         box-shadow:0 4px 20px rgba(79,70,229,.45);display:flex;align-items:center;justify-content:center;
         transition:transform .2s,box-shadow .2s;"
  onmouseenter="this.style.transform='scale(1.08)';this.style.boxShadow='0 6px 24px rgba(79,70,229,.6)'"
  onmouseleave="this.style.transform='scale(1)';this.style.boxShadow='0 4px 20px rgba(79,70,229,.45)'"
  title="Trợ lý: AI + Cố vấn">
  <span class="material-symbols-outlined msym" style="font-size:22px;font-variation-settings:'FILL' 1">forum</span>
  <span id="fcFabBadge" style="position:absolute;top:-2px;right:-2px;min-width:18px;height:18px;
        background:#ef4444;border-radius:9px;border:2px solid #fff;color:#fff;font-size:10px;font-weight:700;
        display:none;align-items:center;justify-content:center;padding:0 4px;line-height:1;"></span>
</button>

<!-- Floating Chat Panel -->
<div id="fcPanel" style="display:none;position:fixed;bottom:88px;right:24px;z-index:9997;
     width:380px;max-width:calc(100vw - 32px);height:600px;max-height:calc(100vh - 120px);
     background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(15,23,42,.18);
     display:none;flex-direction:column;overflow:hidden;border:1px solid #e2e8f0;
     animation:fcSlideUp .22s ease-out;">
  <!-- Header (shared, status-text đổi theo tab) -->
  <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:14px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0;">
    <div id="fcHeaderIcon" style="width:32px;height:32px;background:rgba(255,255,255,.2);border-radius:10px;
                display:flex;align-items:center;justify-content:center;flex-shrink:0;">
      <span class="material-symbols-outlined msym" style="color:#fff;font-size:18px;font-variation-settings:'FILL' 1">psychology</span>
    </div>
    <div style="flex:1;min-width:0;">
      <p id="fcHeaderTitle" style="font-weight:700;color:#fff;font-size:13px;margin:0;line-height:1.2">AI Tư vấn</p>
      <p style="font-size:10px;color:rgba(255,255,255,.7);margin:0" id="fcStatusText">Đang kiểm tra...</p>
    </div>
    <a id="fcExpandLink" href="ai-chat.html" style="background:rgba(255,255,255,.15);border:none;cursor:pointer;
      border-radius:8px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;
      color:#fff;transition:background .15s;text-decoration:none;" title="Mở chat đầy đủ"
      onmouseenter="this.style.background='rgba(255,255,255,.25)'"
      onmouseleave="this.style.background='rgba(255,255,255,.15)'">
      <span class="material-symbols-outlined msym" style="font-size:16px">open_in_full</span>
    </a>
    <button onclick="closeChat()" style="background:rgba(255,255,255,.15);border:none;cursor:pointer;
      border-radius:8px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;
      color:#fff;transition:background .15s;" title="Đóng"
      onmouseenter="this.style.background='rgba(255,255,255,.25)'"
      onmouseleave="this.style.background='rgba(255,255,255,.15)'">
      <span class="material-symbols-outlined msym" style="font-size:16px">close</span>
    </button>
  </div>

  <!-- Tab bar -->
  <div id="fcTabs" style="display:flex;background:#f8f9fc;border-bottom:1px solid #e2e8f0;flex-shrink:0;">
    <button id="fcTabAi" class="fc-tab fc-tab-active" data-tab="ai" type="button">
      <span class="material-symbols-outlined msym" style="font-size:15px;vertical-align:-2px">smart_toy</span>
      AI
    </button>
    <button id="fcTabAdvisor" class="fc-tab" data-tab="advisor" type="button">
      <span class="material-symbols-outlined msym" style="font-size:15px;vertical-align:-2px">support_agent</span>
      Cố vấn
      <span id="fcAdvisorBadge" class="fc-tab-badge" style="display:none">0</span>
    </button>
  </div>

  <!-- ─────────── AI VIEW ─────────── -->
  <div id="fcAiView" class="fc-view fc-view-active" style="display:flex;flex:1;flex-direction:column;overflow:hidden;">
    <!-- Quick prompts -->
    <div style="padding:8px 12px;background:#f8f9fc;border-bottom:1px solid #f1f5f9;display:flex;gap:6px;overflow-x:auto;flex-shrink:0;">
      <button onclick="fcFill('Tôi nên học môn gì tiếp theo?')" class="fc-chip">Môn tiếp theo?</button>
      <button onclick="fcFill('Tiến độ học tập của tôi thế nào?')" class="fc-chip">Tiến độ?</button>
      <button onclick="fcFill('Tôi cần bao nhiêu tín chỉ nữa để tốt nghiệp?')" class="fc-chip">TC còn lại?</button>
      <button onclick="fcFill('Định hướng nghề nghiệp nào phù hợp với tôi?')" class="fc-chip">Định hướng?</button>
    </div>
    <!-- Messages -->
    <div id="fcBox" style="flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;"></div>
    <!-- Input -->
    <div style="padding:10px 12px;background:#fff;border-top:1px solid #f1f5f9;flex-shrink:0;">
      <form id="fcForm" style="display:flex;gap:8px;align-items:flex-end;">
        <textarea id="fcInput" rows="1" placeholder="Đặt câu hỏi…"
          style="flex:1;background:#f8f9fc;border:1px solid #e2e8f0;border-radius:12px;
                 padding:8px 12px;font-size:13px;resize:none;outline:none;max-height:90px;
                 font-family:inherit;line-height:1.5;transition:border-color .15s;"
          onfocus="this.style.borderColor='#4f46e5'"
          onblur="this.style.borderColor='#e2e8f0'"
          onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();document.getElementById('fcForm').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))}"></textarea>
        <button id="fcSendBtn" type="submit"
          style="width:36px;height:36px;background:linear-gradient(135deg,#4f46e5,#7c3aed);border:none;
                 border-radius:10px;cursor:pointer;display:flex;align-items:center;justify-content:center;
                 color:#fff;flex-shrink:0;transition:opacity .15s;box-shadow:0 2px 8px rgba(79,70,229,.35);">
          <span class="material-symbols-outlined msym" style="font-size:17px">send</span>
        </button>
      </form>
      <p style="font-size:10px;color:#cbd5e1;text-align:center;margin:4px 0 0">Enter gửi · Shift+Enter xuống dòng</p>
    </div>
  </div>

  <!-- ─────────── ADVISOR VIEW ─────────── -->
  <div id="fcAdvisorView" class="fc-view" style="display:none;flex:1;flex-direction:column;overflow:hidden;">
    <!-- Advisor info bar -->
    <div id="fcAdvisorInfo" style="padding:10px 12px;background:#f8f9fc;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;gap:10px;flex-shrink:0;">
      <div id="fcAdvisorAvatar" style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#22c55e,#10b981);
           display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:13px;flex-shrink:0;">?</div>
      <div style="flex:1;min-width:0;">
        <p id="fcAdvisorName" style="font-size:12px;font-weight:600;color:#0f172a;margin:0;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Đang tải...</p>
        <p id="fcAdvisorRole" style="font-size:10px;color:#64748b;margin:0">Cố vấn học tập</p>
      </div>
    </div>
    <!-- Empty state (when no advisor assigned) -->
    <div id="fcAdvisorEmpty" style="display:none;flex:1;flex-direction:column;align-items:center;justify-content:center;padding:24px;text-align:center;color:#94a3b8;">
      <span class="material-symbols-outlined msym" style="font-size:40px;margin-bottom:8px">person_search</span>
      <p style="font-size:13px;color:#475569;margin:0 0 6px;font-weight:500">Chưa có cố vấn được phân công</p>
      <p style="font-size:11px;margin:0;line-height:1.5">Liên hệ phòng đào tạo để được phân công cố vấn học tập.</p>
    </div>
    <!-- Messages -->
    <div id="fcAdvisorBox" style="flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;">
      <div id="fcAdvisorLoading" style="text-align:center;color:#94a3b8;font-size:12px;padding:20px;">
        <span class="material-symbols-outlined msym" style="animation:spin 1s linear infinite;font-size:18px;vertical-align:-3px">progress_activity</span>
        Đang tải tin nhắn...
      </div>
    </div>
    <!-- Input -->
    <div style="padding:10px 12px;background:#fff;border-top:1px solid #f1f5f9;flex-shrink:0;">
      <form id="fcAdvisorForm" style="display:flex;gap:8px;align-items:flex-end;">
        <textarea id="fcAdvisorInput" rows="1" placeholder="Nhắn cố vấn…"
          style="flex:1;background:#f8f9fc;border:1px solid #e2e8f0;border-radius:12px;
                 padding:8px 12px;font-size:13px;resize:none;outline:none;max-height:90px;
                 font-family:inherit;line-height:1.5;transition:border-color .15s;"
          onfocus="this.style.borderColor='#10b981'"
          onblur="this.style.borderColor='#e2e8f0'"
          onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();document.getElementById('fcAdvisorForm').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))}"></textarea>
        <button id="fcAdvisorSendBtn" type="submit"
          style="width:36px;height:36px;background:linear-gradient(135deg,#22c55e,#10b981);border:none;
                 border-radius:10px;cursor:pointer;display:flex;align-items:center;justify-content:center;
                 color:#fff;flex-shrink:0;transition:opacity .15s;box-shadow:0 2px 8px rgba(34,197,94,.35);">
          <span class="material-symbols-outlined msym" style="font-size:17px">send</span>
        </button>
      </form>
      <p style="font-size:10px;color:#cbd5e1;text-align:center;margin:4px 0 0">Tin nhắn được gửi tới cố vấn của bạn</p>
    </div>
  </div>
</div>

<style>
@keyframes fcSlideUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
.fc-chip {
  flex-shrink:0;padding:4px 10px;background:#fff;border:1px solid #e2e8f0;border-radius:999px;
  font-size:11px;font-weight:500;color:#64748b;cursor:pointer;white-space:nowrap;
  transition:border-color .15s,color .15s;
}
.fc-chip:hover { border-color:#4f46e5; color:#4f46e5; background:#eef2ff; }
.fc-msg-user { align-self:flex-end;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;
  border-radius:14px 14px 4px 14px;padding:8px 12px;font-size:13px;max-width:85%;line-height:1.5;
  word-wrap:break-word;overflow-wrap:break-word; }
.fc-msg-bot { align-self:flex-start;background:#f1f5f9;color:#334155;
  border-radius:14px 14px 14px 4px;padding:8px 12px;font-size:13px;max-width:85%;line-height:1.5;
  word-wrap:break-word;overflow-wrap:break-word; }
.fc-msg-advisor-me { align-self:flex-end;background:linear-gradient(135deg,#22c55e,#10b981);color:#fff;
  border-radius:14px 14px 4px 14px;padding:8px 12px;font-size:13px;max-width:85%;line-height:1.5;
  word-wrap:break-word;overflow-wrap:break-word; }
.fc-msg-advisor-them { align-self:flex-start;background:#f1f5f9;color:#334155;
  border-radius:14px 14px 14px 4px;padding:8px 12px;font-size:13px;max-width:85%;line-height:1.5;
  word-wrap:break-word;overflow-wrap:break-word; }
.fc-msg-time { font-size:10px;color:#94a3b8;align-self:center;margin:4px 0; }
.fc-tab {
  flex:1;background:transparent;border:none;cursor:pointer;padding:10px 12px;
  font-size:12px;font-weight:600;color:#64748b;
  transition:color .15s,background .15s,border-color .15s;
  border-bottom:2px solid transparent;
  position:relative;
  font-family:inherit;
}
.fc-tab:hover { color:#0f172a;background:#fff; }
.fc-tab-active { color:#4f46e5;border-bottom-color:#4f46e5;background:#fff; }
.fc-tab[data-tab="advisor"].fc-tab-active { color:#10b981;border-bottom-color:#10b981; }
.fc-tab-badge {
  display:inline-flex;align-items:center;justify-content:center;
  min-width:16px;height:16px;padding:0 4px;margin-left:4px;
  background:#ef4444;color:#fff;border-radius:8px;
  font-size:10px;font-weight:700;line-height:1;vertical-align:1px;
}
</style>
`;

  // Inject into body — wrap trong div có id="fcRoot" để ajax-nav giữ nguyên
  // toàn bộ (FAB + Panel + <style> CSS chip). SHELL_IDS check chỉ apply cho
  // direct children của body, nên wrapper PHẢI có id.
  const _container = document.createElement('div');
  _container.id = 'fcRoot';
  _container.innerHTML = _html;
  document.body.appendChild(_container);
  // Apply visibility ngay sau khi inject (ẩn FAB nếu đang ở ai-chat/messaging)
  _fcApplyVisibility();

  // ── State ─────────────────────────────────────────────────────────────────
  // Thread ID persists trong suốt phiên đăng nhập (lưu localStorage):
  //  - Login → tạo thread mới (index.html cache fc_thread_id)
  //  - Logout → clear (auth.js)
  //  - Click "Chat mới" → fcNewThread() tạo UUID mới, clear box
  //  - Chuyển trang/F5: thread cũ giữ → reopen panel auto-load history → không mất context
  function _fcGetOrCreateThreadId() {
    let tid = null;
    try { tid = localStorage.getItem('fc_thread_id'); } catch (_) {}
    if (!tid) {
      tid = (crypto.randomUUID && crypto.randomUUID()) || ('fc_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10));
      try { localStorage.setItem('fc_thread_id', tid); } catch (_) {}
    }
    return tid;
  }
  let _fcOpen = false;
  let _fcRole = null;           // cached: 'student' | 'advisor' | 'admin'
  let _fcGreeting = null;
  let _fcChips = [];
  let _fcHistoryLoaded = false; // đã fetch history cho thread hiện tại chưa
  let _fcLoadedTid = null;      // thread_id đã load lần cuối (để detect đổi thread)

  async function _fcLoadSuggestions() {
    if (_fcRole) return;  // already loaded
    const r = await _fcCallApi('/chat/suggestions/me', { headers: _fcHeaders() }, 8000);
    if (r.ok) {
      _fcRole = r.data.role || 'student';
      _fcGreeting = r.data.greeting || 'Xin chào! Tôi có thể giúp gì cho bạn?';
      _fcChips = r.data.suggestions || [];
    } else {
      _fcRole = 'student';
      _fcGreeting = 'Xin chào! Tôi có thể tư vấn về môn học và tiến độ học tập.';
      _fcChips = [];
    }
  }

  function _fcRenderWelcomeChips() {
    const box = document.getElementById('fcBox');
    if (!_fcChips.length) return;
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;align-self:flex-start;margin-top:8px;';
    _fcChips.forEach(c => {
      const b = document.createElement('button');
      b.className = 'fc-chip';
      b.textContent = c;
      b.onclick = () => {
        const inp = document.getElementById('fcInput');
        if (inp) { inp.value = c; inp.focus(); }
      };
      row.appendChild(b);
    });
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
  }

  // ── DOM helpers ───────────────────────────────────────────────────────────
  function _fcAddMsg(role, text) {
    const box = document.getElementById('fcBox');
    const div = document.createElement('div');
    div.className = role === 'user' ? 'fc-msg-user' : 'fc-msg-bot';
    div.innerHTML = text
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
      .replace(/\n/g,'<br>');
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  function _fcAddTyping() {
    const box = document.getElementById('fcBox');
    const div = document.createElement('div');
    div.id = 'fcTyping'; div.className = 'fc-msg-bot';
    div.innerHTML = '<span style="display:inline-block;animation:spin 1s linear infinite" class="material-symbols-outlined msym">progress_activity</span>';
    box.appendChild(div); box.scrollTop = box.scrollHeight;
  }

  function _fcRemoveTyping() { document.getElementById('fcTyping')?.remove(); }

  // ── AI status check ───────────────────────────────────────────────────────
  function _fcCheckStatus() {
    _fcCallApi('/health', {}, 5000).then(r => {
      const el = document.getElementById('fcStatusText');
      if (!el) return;
      if (r.ok && r.data.status === 'ok') {
        const has = r.data.ai_available ?? (r.data.gemini_key_loaded || r.data.groq_key_loaded || r.data.openai_key_loaded);
        el.textContent = has ? '● AI đầy đủ' : '● Chế độ cơ bản';
        el.style.color = has ? 'rgba(134,239,172,.9)' : 'rgba(253,230,138,.9)';
      } else {
        el.textContent = '● Mất kết nối';
        el.style.color = 'rgba(252,165,165,.9)';
      }
    });
  }

  // ── History loader: fetch toàn bộ tin của thread hiện tại từ server ───────
  // Gọi khi mở panel lần đầu hoặc sau khi đổi thread.
  // Server lưu mọi tin theo thread_id → đảm bảo chuyển page F5 không mất context.
  async function _fcLoadHistory(tid) {
    if (!tid) return;
    if (_fcHistoryLoaded && _fcLoadedTid === tid) return;
    const r = await _fcCallApi(`/chat/history/me?thread_id=${encodeURIComponent(tid)}&limit=50`,
      { headers: _fcHeaders() }, 8000);
    _fcHistoryLoaded = true;
    _fcLoadedTid = tid;
    if (!r.ok) return;  // Thread chưa có msg (thread_id mới) — vô hại, panel rỗng
    const items = r.data?.messages || r.data || [];
    if (!Array.isArray(items) || !items.length) return;
    const box = document.getElementById('fcBox');
    if (!box) return;
    box.innerHTML = '';  // wipe greeting placeholder (sẽ render lại nếu cần)
    // Server returns ChatHistoryItemOut sorted DESC (newest first) — reverse so
    // we render chronologically: oldest at top, newest at bottom.
    const ordered = items.slice().reverse();
    ordered.forEach(m => {
      // Current schema: { id, role: 'user'|'assistant', message, ... }
      // Legacy turn-pair format: { message, answer } (user msg + AI reply combined)
      if (m.role && typeof m.message === 'string') {
        _fcAddMsg(m.role === 'user' ? 'user' : 'bot', m.message);
      } else if (m.role && typeof m.content === 'string') {
        // Older field name fallback
        _fcAddMsg(m.role === 'user' ? 'user' : 'bot', m.content);
      } else {
        // Turn-pair fallback (no role field)
        if (m.message) _fcAddMsg('user', m.message);
        if (m.answer)  _fcAddMsg('bot', m.answer);
      }
    });
  }

  // ── Public API ────────────────────────────────────────────────────────────
  async function _fcShowWelcome() {
    await _fcLoadSuggestions();
    const tid = _fcGetOrCreateThreadId();
    // 1) Cố load history trước — nếu thread đã có tin từ trang khác, hiện đầy đủ
    await _fcLoadHistory(tid);
    // 2) Nếu vẫn rỗng (thread mới, chưa có tin nào) → hiện greeting + welcome chips
    const box = document.getElementById('fcBox');
    if (box && !box.children.length) {
      _fcAddMsg('bot', _fcGreeting || 'Xin chào!');
      _fcRenderWelcomeChips();
    }
  }


  window.toggleFloatingChat = async function () {
    const panel = document.getElementById('fcPanel');
    _fcOpen = !_fcOpen;
    if (_fcOpen) {
      panel.style.display = 'flex';
      _fcCheckStatus();
      await _fcShowWelcome();
      setTimeout(() => document.getElementById('fcInput')?.focus(), 100);
    } else {
      panel.style.display = 'none';
    }
  };

  window.openChatWithText = async function (text) {
    const panel = document.getElementById('fcPanel');
    if (!_fcOpen) {
      _fcOpen = true;
      panel.style.display = 'flex';
      _fcCheckStatus();
      await _fcShowWelcome();
    }
    if (text) {
      setTimeout(() => {
        const inp = document.getElementById('fcInput');
        if (inp) { inp.value = text; inp.focus(); inp.select(); }
      }, 150);
    }
  };

  window.closeChat = function () {
    _fcOpen = false;
    document.getElementById('fcPanel').style.display = 'none';
  };

  // Public: mở FAB panel + chuyển tab Cố vấn + prefill input.
  // Dùng cho contextual CTAs ("Hỏi cố vấn về môn này", "Trao đổi về kỳ", ...).
  // Ví dụ: openAdvisorChat("Em đang xem môn 7080216. Cô có thể tư vấn em không?")
  window.openAdvisorChat = async function (text) {
    const panel = document.getElementById('fcPanel');
    if (!panel) return;
    if (!_fcOpen) {
      _fcOpen = true;
      panel.style.display = 'flex';
    }
    _fcSwitchTab('advisor');
    if (text) {
      // Đợi switch xong (load advisor + messages async) rồi prefill
      setTimeout(() => {
        const inp = document.getElementById('fcAdvisorInput');
        if (inp) {
          inp.value = text;
          inp.focus();
          // Auto-resize textarea
          inp.style.height = 'auto';
          inp.style.height = Math.min(inp.scrollHeight, 90) + 'px';
        }
      }, 200);
    }
  };

  window.fcFill = function (text) {
    const inp = document.getElementById('fcInput');
    if (inp) { inp.value = text; inp.focus(); }
  };

  // ── Form submit ───────────────────────────────────────────────────────────
  // Phải attach listener ngay (DOM đã được inject ở trên), không đợi DOMContentLoaded —
  // vì script có thể load sau DOMContentLoaded đã fire (đặc biệt với ajax-nav).
  function _fcAttachFormHandler() {
    const form = document.getElementById('fcForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('fcInput');
      const msg = input.value.trim(); if (!msg) return;

      const threadId = _fcGetOrCreateThreadId();

      _fcAddMsg('user', msg); input.value = '';
      const btn = document.getElementById('fcSendBtn'); btn.disabled = true; btn.style.opacity = '0.5';
      _fcAddTyping();

      const res = await _fcCallApi('/chat/me', {
        method: 'POST',
        headers: _fcHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ message: msg, limit: 5, prefer_llm: true, thread_id: threadId }),
      });
      _fcRemoveTyping(); btn.disabled = false; btn.style.opacity = '1';

      if (res.ok) {
        _fcAddMsg('bot', res.data.answer || '(không có nội dung)');
        if (res.data.suggestions?.length) {
          const box = document.getElementById('fcBox');
          const row = document.createElement('div');
          row.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;align-self:flex-start;';
          res.data.suggestions.forEach(s => {
            const b = document.createElement('button');
            b.className = 'fc-chip';
            b.textContent = s; b.onclick = () => fcFill(s);
            row.appendChild(b);
          });
          box.appendChild(row); box.scrollTop = box.scrollHeight;
        }
      } else {
        _fcAddMsg('bot', `Lỗi: ${res.data?.detail || 'Không thể kết nối'}`);
      }
      input.focus();
    });
  }
  _fcAttachFormHandler();

  // ════════════════════════════════════════════════════════════════════════
  // ADVISOR TAB — Direct messaging với cố vấn được phân công.
  // SV thường có 1 cố vấn duy nhất (UNIQUE constraint trên student_id của
  // advisor_assignments). Tab này = thread DM với cố vấn đó.
  // ════════════════════════════════════════════════════════════════════════

  // Advisor state
  let _fcActiveTab = 'ai';        // 'ai' | 'advisor'
  let _fcAdvisor = null;          // {id, full_name, ...} | null
  let _fcAdvisorLoaded = false;   // đã fetch /me/advisor chưa
  let _fcAdvisorMsgsLoaded = false; // đã fetch DM history chưa
  let _fcLastMsgId = 0;           // largest DM id loaded — cho incremental polling
  let _fcPollTimer = null;        // setInterval handle cho unread polling
  let _fcUnreadCount = 0;         // tổng unread DM (tin từ advisor chưa đọc)

  // Helper: format timestamp ngắn cho message bubble
  function _fcFmtTime(iso) {
    try {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) {
        return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch (_) { return ''; }
  }

  // Helper: avatar initials từ full_name
  function _fcInitials(name) {
    if (!name) return '?';
    const parts = String(name).trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 1).toUpperCase();
    return (parts[parts.length - 2].slice(0, 1) + parts[parts.length - 1].slice(0, 1)).toUpperCase();
  }

  // Switch giữa tab AI và Advisor — toggle visibility + update header.
  function _fcSwitchTab(name) {
    _fcActiveTab = name;
    const aiTab = document.getElementById('fcTabAi');
    const adTab = document.getElementById('fcTabAdvisor');
    const aiView = document.getElementById('fcAiView');
    const adView = document.getElementById('fcAdvisorView');
    const headerTitle = document.getElementById('fcHeaderTitle');
    const headerIcon = document.getElementById('fcHeaderIcon');
    const expandLink = document.getElementById('fcExpandLink');
    const statusText = document.getElementById('fcStatusText');
    if (!aiTab || !adTab) return;

    if (name === 'advisor') {
      aiTab.classList.remove('fc-tab-active');
      adTab.classList.add('fc-tab-active');
      if (aiView) aiView.style.display = 'none';
      if (adView) adView.style.display = 'flex';
      if (headerTitle) headerTitle.textContent = 'Cố vấn học tập';
      if (headerIcon) headerIcon.firstElementChild.textContent = 'support_agent';
      if (statusText) statusText.textContent = _fcAdvisor ? `${_fcAdvisor.full_name || _fcAdvisor.username}` : 'Tin nhắn 1-1';
      // Expand link → messaging.html với advisor_id (nếu có)
      if (expandLink) {
        expandLink.href = _fcAdvisor ? `messaging.html?with=${_fcAdvisor.id}` : 'messaging.html';
      }
      // Lazy-load advisor data + messages khi user mở tab lần đầu
      _fcLoadAdvisorTab();
    } else {
      aiTab.classList.add('fc-tab-active');
      adTab.classList.remove('fc-tab-active');
      if (aiView) aiView.style.display = 'flex';
      if (adView) adView.style.display = 'none';
      if (headerTitle) headerTitle.textContent = 'AI Tư vấn';
      if (headerIcon) headerIcon.firstElementChild.textContent = 'psychology';
      _fcCheckStatus();  // refresh AI status text
      // Expand link → ai-chat.html với thread_id
      if (expandLink) {
        let tid = '';
        try { tid = localStorage.getItem('fc_thread_id') || ''; } catch (_) {}
        expandLink.href = tid ? `ai-chat.html?thread=${encodeURIComponent(tid)}` : 'ai-chat.html';
      }
    }
  }

  // Fetch advisor info + DM history. Gọi lần đầu khi switch sang tab Cố vấn.
  async function _fcLoadAdvisorTab() {
    if (!_fcAdvisorLoaded) {
      const r = await _fcCallApi('/me/advisor', { headers: _fcHeaders() }, 8000);
      _fcAdvisorLoaded = true;
      if (r.ok && r.data && r.data.advisor) {
        _fcAdvisor = r.data.advisor;
        _fcRenderAdvisorInfo();
      } else {
        // Không có advisor → hiện empty state, ẩn input
        document.getElementById('fcAdvisorEmpty').style.display = 'flex';
        document.getElementById('fcAdvisorBox').style.display = 'none';
        document.getElementById('fcAdvisorForm').parentElement.style.display = 'none';
        document.getElementById('fcAdvisorName').textContent = 'Chưa có cố vấn';
        return;
      }
    }
    if (_fcAdvisor && !_fcAdvisorMsgsLoaded) {
      await _fcLoadAdvisorMessages();
    }
    // Mark all unread messages as read sau khi user mở tab
    if (_fcAdvisor && _fcUnreadCount > 0) {
      _fcCallApi(`/messages/direct/read-all/${_fcAdvisor.id}`, {
        method: 'PATCH', headers: _fcHeaders(),
      }).then(() => {
        _fcUnreadCount = 0;
        _fcUpdateBadges();
      });
    }
  }

  function _fcRenderAdvisorInfo() {
    if (!_fcAdvisor) return;
    const name = _fcAdvisor.full_name || _fcAdvisor.username;
    document.getElementById('fcAdvisorName').textContent = name;
    document.getElementById('fcAdvisorAvatar').textContent = _fcInitials(name);
    const roleEl = document.getElementById('fcAdvisorRole');
    if (roleEl) {
      let label = 'Cố vấn học tập';
      if (_fcAdvisor.is_head_of_department) label = 'Trưởng bộ môn';
      if (_fcAdvisor.teacher_code) label += ` · ${_fcAdvisor.teacher_code}`;
      roleEl.textContent = label;
    }
    // Status text trong header
    const statusText = document.getElementById('fcStatusText');
    if (statusText && _fcActiveTab === 'advisor') statusText.textContent = name;
  }

  async function _fcLoadAdvisorMessages() {
    if (!_fcAdvisor) return;
    const r = await _fcCallApi(`/messages/direct/${_fcAdvisor.id}?limit=50`, {
      headers: _fcHeaders(),
    }, 8000);
    _fcAdvisorMsgsLoaded = true;
    const box = document.getElementById('fcAdvisorBox');
    const loading = document.getElementById('fcAdvisorLoading');
    if (loading) loading.remove();
    if (!r.ok) {
      box.innerHTML = '<p style="color:#94a3b8;font-size:12px;text-align:center;padding:20px;">Không tải được tin nhắn. Thử lại sau.</p>';
      return;
    }
    const msgs = r.data?.messages || [];
    if (msgs.length === 0) {
      box.innerHTML = `<div style="text-align:center;padding:24px 12px;color:#94a3b8;">
        <span class="material-symbols-outlined msym" style="font-size:32px;opacity:.6">chat</span>
        <p style="font-size:12px;margin:6px 0 0">Chưa có tin nhắn nào.<br/>Gửi tin đầu tiên cho cố vấn của bạn!</p>
      </div>`;
      return;
    }
    box.innerHTML = '';
    // Server có thể trả desc hoặc asc — sort lại theo created_at asc cho display
    msgs.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    msgs.forEach(m => _fcAppendAdvisorMsg(m));
    if (msgs.length) _fcLastMsgId = Math.max(..._fcLastMsgId ? [_fcLastMsgId, ...msgs.map(m => m.id)] : msgs.map(m => m.id));
    box.scrollTop = box.scrollHeight;
  }

  function _fcAppendAdvisorMsg(m) {
    const box = document.getElementById('fcAdvisorBox');
    if (!box) return;
    const isMe = m.sender_id === _fcMyId();
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;gap:2px;' + (isMe ? 'align-items:flex-end;' : 'align-items:flex-start;');
    const div = document.createElement('div');
    div.className = isMe ? 'fc-msg-advisor-me' : 'fc-msg-advisor-them';
    div.textContent = m.content || '';
    const time = document.createElement('span');
    time.style.cssText = 'font-size:10px;color:#94a3b8;padding:0 4px;';
    time.textContent = _fcFmtTime(m.created_at);
    wrap.appendChild(div);
    wrap.appendChild(time);
    box.appendChild(wrap);
  }

  // Get current user id from cached /auth/me (set sau khi login).
  // Fallback: parse JWT token (không reliable), hoặc cache 1 lần đầu.
  let _fcMyIdCache = null;
  function _fcMyId() {
    if (_fcMyIdCache !== null) return _fcMyIdCache;
    try {
      const cached = JSON.parse(localStorage.getItem('user_me') || 'null');
      if (cached && cached.id) { _fcMyIdCache = cached.id; return _fcMyIdCache; }
    } catch (_) {}
    return 0;  // unknown — sẽ fix lúc fetch advisor (gọi /auth/me song song)
  }

  // Form handler cho advisor input
  function _fcAttachAdvisorFormHandler() {
    const form = document.getElementById('fcAdvisorForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!_fcAdvisor) return;
      const input = document.getElementById('fcAdvisorInput');
      const msg = input.value.trim();
      if (!msg) return;
      const btn = document.getElementById('fcAdvisorSendBtn');
      btn.disabled = true; btn.style.opacity = '0.5';
      input.value = '';
      // Optimistic render — append ngay, server response có thể bổ sung id
      const tempMsg = {
        id: 0,
        sender_id: _fcMyId(),
        receiver_id: _fcAdvisor.id,
        content: msg,
        created_at: new Date().toISOString(),
      };
      // Clear empty placeholder nếu có
      const box = document.getElementById('fcAdvisorBox');
      if (box && box.children.length === 1 && box.querySelector('span.material-symbols-outlined')) {
        box.innerHTML = '';
      }
      _fcAppendAdvisorMsg(tempMsg);
      box.scrollTop = box.scrollHeight;

      const res = await _fcCallApi(`/messages/direct/${_fcAdvisor.id}`, {
        method: 'POST',
        headers: _fcHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ content: msg }),
      });
      btn.disabled = false; btn.style.opacity = '1';
      if (!res.ok) {
        // Rollback: hiện error inline
        const err = document.createElement('p');
        err.style.cssText = 'font-size:11px;color:#ef4444;align-self:flex-end;margin:0;';
        err.textContent = `Gửi không thành công: ${res.data?.detail || 'lỗi'}`;
        box.appendChild(err);
      } else if (res.data?.id) {
        _fcLastMsgId = Math.max(_fcLastMsgId, res.data.id);
      }
      input.focus();
    });
  }
  _fcAttachAdvisorFormHandler();

  // Wire tab click handlers
  function _fcAttachTabHandlers() {
    const aiTab = document.getElementById('fcTabAi');
    const adTab = document.getElementById('fcTabAdvisor');
    if (aiTab) aiTab.onclick = () => _fcSwitchTab('ai');
    if (adTab) adTab.onclick = () => _fcSwitchTab('advisor');
  }
  _fcAttachTabHandlers();

  // ── Unread polling ────────────────────────────────────────────────────────
  // Poll /messages/direct/unread/count để update badge trên FAB + tab.
  // Cadence: 30s khi panel open, 60s khi closed.
  // SV chỉ DM với advisor → unread chủ yếu từ advisor → đếm vào tab Cố vấn.
  async function _fcPollUnread() {
    const r = await _fcCallApi('/messages/direct/unread/count', { headers: _fcHeaders() }, 5000);
    if (!r.ok) return;
    _fcUnreadCount = r.data?.total || 0;
    _fcUpdateBadges();
    // Nếu user đang ở tab advisor + có tin mới → fetch increment
    if (_fcOpen && _fcActiveTab === 'advisor' && _fcAdvisor && _fcUnreadCount > 0) {
      // Re-fetch toàn bộ messages (đơn giản, không tối ưu polling delta)
      _fcAdvisorMsgsLoaded = false;
      await _fcLoadAdvisorMessages();
      // Auto mark read vì user đang xem
      _fcCallApi(`/messages/direct/read-all/${_fcAdvisor.id}`, {
        method: 'PATCH', headers: _fcHeaders(),
      }).then(() => {
        _fcUnreadCount = 0;
        _fcUpdateBadges();
      });
    }
  }

  function _fcUpdateBadges() {
    const fabBadge = document.getElementById('fcFabBadge');
    const tabBadge = document.getElementById('fcAdvisorBadge');
    if (_fcUnreadCount > 0) {
      const txt = _fcUnreadCount > 9 ? '9+' : String(_fcUnreadCount);
      if (fabBadge) {
        fabBadge.textContent = txt;
        fabBadge.style.display = 'flex';
      }
      if (tabBadge) {
        tabBadge.textContent = txt;
        tabBadge.style.display = 'inline-flex';
      }
    } else {
      if (fabBadge) fabBadge.style.display = 'none';
      if (tabBadge) tabBadge.style.display = 'none';
    }
  }

  function _fcStartPolling() {
    if (_fcPollTimer) return;
    _fcPollUnread();  // ngay lập tức
    _fcPollTimer = setInterval(_fcPollUnread, 60000);  // 60s default
  }

  function _fcStopPolling() {
    if (_fcPollTimer) { clearInterval(_fcPollTimer); _fcPollTimer = null; }
  }

  // Cache user_me sau khi /auth/me trả về (cần cho _fcMyId)
  setTimeout(async function _fcCacheMyId() {
    try {
      const tok = (typeof getToken === 'function') ? getToken() : (localStorage.getItem('access_token') || '');
      if (!tok) return;
      // Check if already cached
      const cached = JSON.parse(localStorage.getItem('user_me') || 'null');
      if (cached && cached.id) { _fcMyIdCache = cached.id; }
      const r = await fetch(_fcApiBase() + '/auth/me', { headers: { Authorization: 'Bearer ' + tok } });
      if (!r.ok) return;
      const me = await r.json();
      _fcMyIdCache = me.id;
      try { localStorage.setItem('user_me', JSON.stringify({ id: me.id, role: me.role, full_name: me.full_name })); } catch (_) {}
      // Nếu role student → start polling background cho unread
      if (me.role === 'student') {
        _fcStartPolling();
      }
    } catch (_) {}
  }, 800);

})();
