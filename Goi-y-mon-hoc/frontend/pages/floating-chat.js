/**
 * floating-chat.js — Self-contained floating AI chat widget
 * Depends on: auth.js (getToken, window.API_BASE) loaded first
 * Globals exposed: toggleFloatingChat(), openChatWithText(), closeChat()
 */
(function () {
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
  const _html = `
<!-- Floating Chat FAB -->
<button id="fcFab"
  onclick="toggleFloatingChat()"
  style="position:fixed;bottom:24px;right:24px;z-index:9998;width:52px;height:52px;border-radius:50%;
         background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;cursor:pointer;
         box-shadow:0 4px 20px rgba(79,70,229,.45);display:flex;align-items:center;justify-content:center;
         transition:transform .2s,box-shadow .2s;"
  onmouseenter="this.style.transform='scale(1.08)';this.style.boxShadow='0 6px 24px rgba(79,70,229,.6)'"
  onmouseleave="this.style.transform='scale(1)';this.style.boxShadow='0 4px 20px rgba(79,70,229,.45)'"
  title="AI Tư vấn">
  <span class="material-symbols-outlined msym" style="font-size:22px;font-variation-settings:'FILL' 1">psychology</span>
</button>

<!-- Floating Chat Panel -->
<div id="fcPanel" style="display:none;position:fixed;bottom:88px;right:24px;z-index:9997;
     width:380px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 120px);
     background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(15,23,42,.18);
     display:none;flex-direction:column;overflow:hidden;border:1px solid #e2e8f0;
     animation:fcSlideUp .22s ease-out;">
  <!-- Header -->
  <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:14px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0;">
    <div style="width:32px;height:32px;background:rgba(255,255,255,.2);border-radius:10px;
                display:flex;align-items:center;justify-content:center;flex-shrink:0;">
      <span class="material-symbols-outlined msym" style="color:#fff;font-size:18px;font-variation-settings:'FILL' 1">psychology</span>
    </div>
    <div style="flex:1;min-width:0;">
      <p style="font-weight:700;color:#fff;font-size:13px;margin:0;line-height:1.2">AI Tư vấn</p>
      <p style="font-size:10px;color:rgba(255,255,255,.7);margin:0" id="fcStatusText">Đang kiểm tra...</p>
    </div>
    <button onclick="closeChat()" style="background:rgba(255,255,255,.15);border:none;cursor:pointer;
      border-radius:8px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;
      color:#fff;transition:background .15s;" title="Đóng"
      onmouseenter="this.style.background='rgba(255,255,255,.25)'"
      onmouseleave="this.style.background='rgba(255,255,255,.15)'">
      <span class="material-symbols-outlined msym" style="font-size:16px">close</span>
    </button>
  </div>

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

<style>
@keyframes fcSlideUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
.fc-chip {
  flex-shrink:0;padding:4px 10px;background:#fff;border:1px solid #e2e8f0;border-radius:999px;
  font-size:11px;font-weight:500;color:#64748b;cursor:pointer;white-space:nowrap;
  transition:border-color .15s,color .15s;
}
.fc-chip:hover { border-color:#4f46e5; color:#4f46e5; background:#eef2ff; }
.fc-msg-user { align-self:flex-end;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;
  border-radius:14px 14px 4px 14px;padding:8px 12px;font-size:13px;max-width:85%;line-height:1.5; }
.fc-msg-bot { align-self:flex-start;background:#f1f5f9;color:#334155;
  border-radius:14px 14px 14px 4px;padding:8px 12px;font-size:13px;max-width:85%;line-height:1.5; }
</style>
`;

  // Inject into body
  const _container = document.createElement('div');
  _container.innerHTML = _html;
  document.body.appendChild(_container);

  // ── State ─────────────────────────────────────────────────────────────────
  let _fcThreadId = null;
  let _fcOpen = false;
  let _fcRole = null;           // cached: 'student' | 'advisor' | 'admin'
  let _fcGreeting = null;
  let _fcChips = [];

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

  // ── Public API ────────────────────────────────────────────────────────────
  async function _fcShowWelcome() {
    await _fcLoadSuggestions();
    if (!document.getElementById('fcBox').children.length) {
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

  window.fcFill = function (text) {
    const inp = document.getElementById('fcInput');
    if (inp) { inp.value = text; inp.focus(); }
  };

  // ── Form submit ───────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('fcForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('fcInput');
      const msg = input.value.trim(); if (!msg) return;

      if (!_fcThreadId) _fcThreadId = crypto.randomUUID();

      _fcAddMsg('user', msg); input.value = '';
      const btn = document.getElementById('fcSendBtn'); btn.disabled = true; btn.style.opacity = '0.5';
      _fcAddTyping();

      const res = await _fcCallApi('/chat/me', {
        method: 'POST',
        headers: _fcHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ message: msg, limit: 5, prefer_llm: true, thread_id: _fcThreadId }),
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
  });

})();
