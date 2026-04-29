'use strict';
/**
 * initCurriculumChart(containerEl, opts) → controller
 *
 * Renders a semester-column grid with SVG prerequisite arrows.
 * - Normal mode: click card to highlight connections; drag card to move between semester columns
 * - Edit mode: connection ports appear on each card; drag port → draw line → release on target card to add/remove prereq
 *
 * opts:
 *   canEdit      {boolean}   — show edit features (default false)
 *   apiHeaders   {object}    — Authorization headers for mutation calls
 *   editStatusEl {HTMLElement|null} — element to display edit instructions
 *   callApi      {function}  — async (url, opts) → {ok, data}
 *   toast        {function}  — (msg, ok?) → void
 *   onRefresh    {function}  — called after prereq or semester mutation
 */
function initCurriculumChart(containerEl, opts) {
  opts = opts || {};
  const canEdit    = opts.canEdit    ?? false;
  const apiHeaders = opts.apiHeaders ?? {};
  const statusEl   = opts.editStatusEl ?? null;
  const _call      = opts.callApi  ?? window.callApi;
  const _toast     = opts.toast    ?? window.toast;
  const onRefresh  = opts.onRefresh ?? null;

  let _courses  = [];
  let _selected = null;
  let _editMode = false;

  const _uid = 'cc' + Math.random().toString(36).slice(2, 7);
  const svgNS = 'http://www.w3.org/2000/svg';

  /* ── SVG overlay ──────────────────────────────────────────────────── */
  containerEl.style.position = 'relative';
  // Remove any previous chart SVG in this container
  containerEl.querySelectorAll('svg.cc-svg').forEach(el => el.remove());
  const _svg = document.createElementNS(svgNS, 'svg');
  _svg.classList.add('cc-svg');
  _svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:visible;z-index:10';
  _svg.innerHTML = `<defs>
    <marker id="${_uid}-arr"     markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#94a3b8"/></marker>
    <marker id="${_uid}-arr-pre" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#10b981"/></marker>
    <marker id="${_uid}-arr-suc" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#f59e0b"/></marker>
    <marker id="${_uid}-arr-tmp" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#6366f1"/></marker>
  </defs>`;
  containerEl.appendChild(_svg);

  // Click on empty area → deselect
  containerEl.addEventListener('click', e => {
    if (_selected && !e.target.closest('[data-code]')) {
      _selected = null;
      _courses.forEach(c => _resetCard(c.course_code));
      drawArrows(null);
    }
  });

  /* ── Color map by group ───────────────────────────────────────────── */
  const GRP = {
    compulsory: { border: '#2563eb', bg: '#eff6ff', code: '#1d4ed8' },
    a:          { border: '#059669', bg: '#ecfdf5', code: '#065f46' },
    b:          { border: '#d97706', bg: '#fffbeb', code: '#92400e' },
    c:          { border: '#7c3aed', bg: '#f5f3ff', code: '#5b21b6' },
  };

  function _esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ── Public: render(courses) ──────────────────────────────────────── */
  function render(courses) {
    _courses  = courses || [];
    _selected = null;
    containerEl.querySelectorAll('.cc-col').forEach(el => el.remove());
    _setStatus(_editMode ? _EDIT_HINT : '');

    if (!_courses.length) {
      const el = document.createElement('div');
      el.className = 'cc-col';
      el.style.cssText = 'padding:3rem 2rem;font-size:.875rem;color:#94a3b8;font-style:italic;text-align:center';
      el.textContent = 'Chưa có môn học nào trong chuyên ngành này.';
      containerEl.appendChild(el);
      return;
    }

    const byHk = {};
    for (let i = 1; i <= 9; i++) byHk[i] = [];
    const unassigned = [];
    _courses.forEach(c => {
      const hk = c.typical_semester;
      if (hk >= 1 && hk <= 9) byHk[hk].push(c);
      else unassigned.push(c);
    });

    const activeHks = [];
    for (let i = 1; i <= 9; i++) { if (byHk[i].length) activeHks.push(i); }
    activeHks.forEach(hk => containerEl.appendChild(_makeCol('Học kỳ ' + hk, hk, byHk[hk])));
    if (unassigned.length) containerEl.appendChild(_makeCol('Chưa xếp HK', 0, unassigned));

    if (_editMode) _applyEditModeStyles(true);
    requestAnimationFrame(() => requestAnimationFrame(() => drawArrows(null)));
  }

  /* ── Column ───────────────────────────────────────────────────────── */
  function _makeCol(label, hkNum, list) {
    const col = document.createElement('div');
    col.className = 'cc-col';
    col.dataset.hk = String(hkNum);

    const tc = list.reduce((s, c) => s + (parseFloat(c.credits) || 0), 0);
    const tcStr = tc % 1 === 0 ? tc.toFixed(0) : tc.toFixed(1);
    const dimmed = hkNum === 0;

    col.style.cssText =
      `display:flex;flex-direction:column;gap:8px;width:190px;flex-shrink:0;position:relative;z-index:2;` +
      (dimmed ? 'opacity:.65' : '');

    const hdr = document.createElement('div');
    hdr.style.cssText =
      `text-align:center;padding:8px 10px;border-radius:10px;` +
      (dimmed ? 'background:#94a3b8' : 'background:#334155') +
      `;color:#fff;user-select:none;`;
    hdr.innerHTML =
      `<div style="font-size:12px;font-weight:700;letter-spacing:.3px">${_esc(label)}</div>` +
      `<div style="font-size:10px;color:rgba(255,255,255,.65);margin-top:2px">${list.length} môn · ${tcStr} TC</div>`;
    col.appendChild(hdr);

    /* Drop zone for drag-move */
    if (canEdit && hkNum > 0) {
      col.addEventListener('dragover', e => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        col.style.outline = '2px dashed #6366f1';
        col.style.outlineOffset = '4px';
        col.style.borderRadius = '12px';
      });
      col.addEventListener('dragleave', e => {
        if (!col.contains(e.relatedTarget)) _clearColHighlight(col);
      });
      col.addEventListener('drop', e => {
        e.preventDefault();
        _clearColHighlight(col);
        const code = e.dataTransfer.getData('text/plain');
        if (!code) return;
        const course = _courses.find(c => c.course_code === code);
        if (!course || course.typical_semester === hkNum) return;
        _updateSemester(code, hkNum);
      });
    }

    list.forEach(c => col.appendChild(_makeCard(c)));
    return col;
  }

  function _clearColHighlight(col) {
    col.style.outline = '';
    col.style.outlineOffset = '';
    col.style.borderRadius = '';
  }

  /* ── Placeholder card (Tự chọn A/B/C slot) ───────────────────────── */
  function _makePlaceholderCard(c) {
    const clr = GRP[c.group] || GRP.compulsory;
    const label = c.group === 'a' ? 'Tự chọn A' : c.group === 'b' ? 'Tự chọn B' : 'Tự chọn C';
    const card = document.createElement('div');
    card.id           = _uid + '-card-' + c.course_code;
    card.dataset.code = c.course_code;
    card.style.cssText =
      `position:relative;border:2px dashed ${clr.border};background:${clr.bg};border-radius:10px;` +
      `padding:10px 12px;cursor:default;opacity:.7;`;
    card.innerHTML =
      `<div style="font-size:12px;font-style:italic;font-weight:600;color:${clr.code};text-align:center">${label}</div>` +
      `<div style="font-size:11px;color:#94a3b8;margin-top:4px;text-align:center">${c.credits || 3} TC</div>`;
    return card;
  }

  /* ── Card ─────────────────────────────────────────────────────────── */
  function _makeCard(c) {
    if (c.is_placeholder) return _makePlaceholderCard(c);
    const clr = GRP[c.group] || GRP.compulsory;
    const statusStyles = {
      passed:  { border: '#16a34a', bg: '#f0fdf4', badge: '✓', bclr: '#15803d', bbg: 'rgba(22,163,74,.15)' },
      failed:  { border: '#dc2626', bg: '#fef2f2', badge: '✗', bclr: '#b91c1c', bbg: 'rgba(220,38,38,.12)' },
      current: { border: '#2563eb', bg: '#eff6ff', badge: '▶', bclr: '#1d4ed8', bbg: 'rgba(37,99,235,.15)' },
    };
    const st = statusStyles[c.status] || null;
    const borderColor = st ? st.border : clr.border;
    const bgColor     = st ? st.bg     : clr.bg;

    const card = document.createElement('div');
    card.id           = _uid + '-card-' + c.course_code;
    card.dataset.code = c.course_code;
    card.draggable    = canEdit;
    card.style.cssText =
      `position:relative;border-left:4px solid ${borderColor};background:${bgColor};border-radius:10px;` +
      `padding:10px 12px;cursor:${canEdit ? 'grab' : 'pointer'};` +
      `transition:opacity .15s,box-shadow .15s,outline .1s;` +
      `box-shadow:0 1px 3px rgba(0,0,0,.08);user-select:none;`;

    const badgeHtml = st
      ? `<span style="position:absolute;top:5px;right:28px;font-size:9px;font-weight:700;color:${st.bclr};background:${st.bbg};border-radius:3px;padding:1px 4px;line-height:1.4">${st.badge}</span>`
      : '';

    const noteBadge = c.has_note
      ? `<span style="position:absolute;top:5px;right:5px;font-size:11px" title="Cố vấn có ghi chú">💬</span>`
      : '';

    card.innerHTML =
      `${badgeHtml}${noteBadge}` +
      `<div style="font-family:monospace;font-size:11px;font-weight:700;color:${clr.code};margin-bottom:3px;padding-right:20px">${_esc(c.course_code)}</div>` +
      `<div style="font-size:12px;color:#1e293b;line-height:1.4;word-break:break-word">${_esc(c.course_name)}</div>` +
      `<div style="font-size:11px;color:#94a3b8;margin-top:5px">${c.credits != null ? c.credits + ' TC' : '—'}${!c.count_toward_credits ? ' <span style="color:#d97706;font-weight:600">-TC</span>' : ''}</div>` +
      (canEdit ? `<div class="cc-port" data-code="${_esc(c.course_code)}" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);width:14px;height:14px;border-radius:50%;background:#fff;border:2px solid ${borderColor};cursor:crosshair;display:none;box-shadow:0 1px 3px rgba(0,0,0,.2)" title="Kéo để nối tiên quyết"></div>` : '');

    card.title = `${c.course_code} — ${c.course_name}` +
      (c.status === 'passed' ? ' ✓ Đã qua' : c.status === 'failed' ? ' ✗ Chưa qua' : c.status === 'current' ? ' ▶ Đang học' : '') +
      ((c.prereqs || []).length ? '\nTiên quyết: ' + c.prereqs.join(', ') : '');

    /* Drag-to-move */
    if (canEdit) {
      card.addEventListener('dragstart', e => {
        if (e.target.classList && e.target.classList.contains('cc-port')) { e.preventDefault(); return; }
        e.dataTransfer.setData('text/plain', c.course_code);
        e.dataTransfer.effectAllowed = 'move';
        setTimeout(() => { card.style.opacity = '0.4'; }, 0);
      });
      card.addEventListener('dragend', () => {
        card.style.opacity = '1';
        containerEl.querySelectorAll('.cc-col').forEach(col => _clearColHighlight(col));
      });
    }

    /* Click */
    card.addEventListener('click', e => {
      if (e.target.classList && e.target.classList.contains('cc-port')) return;
      _viewClick(c.course_code);
    });

    /* Connection port mousedown */
    const port = card.querySelector('.cc-port');
    if (port) {
      port.addEventListener('mousedown', e => {
        e.stopPropagation();
        e.preventDefault();
        _startConnect(c.course_code);
      });
    }

    return card;
  }

  /* ── Drag-to-move: update semester via API ────────────────────────── */
  async function _updateSemester(courseCode, newSem) {
    const res = await _call(`/admin/courses/${encodeURIComponent(courseCode)}/semester`, {
      method: 'PATCH',
      headers: { ...apiHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ semester: newSem }),
    });
    if (!res.ok) { _toast(res.data?.detail || 'Lỗi cập nhật học kỳ', false); return; }
    _toast(`Đã chuyển sang Học kỳ ${newSem}`);
    // Update local array and re-render without reloading static data
    const course = _courses.find(c => c.course_code === courseCode);
    if (course) { course.typical_semester = newSem; render(_courses); }
  }

  /* ── Drag-to-connect ──────────────────────────────────────────────── */
  let _connSrc     = null;
  let _connTmpLine = null;

  const _EDIT_HINT = 'Kéo card vào cột khác để thay HK · Kéo từ nút ○ để tạo / xóa tiên quyết · Click card để xem quan hệ';

  function _startConnect(srcCode) {
    _connSrc = srcCode;
    _connTmpLine = document.createElementNS(svgNS, 'path');
    _connTmpLine.setAttribute('stroke', '#6366f1');
    _connTmpLine.setAttribute('stroke-width', '2');
    _connTmpLine.setAttribute('stroke-dasharray', '6,3');
    _connTmpLine.setAttribute('fill', 'none');
    _connTmpLine.setAttribute('opacity', '0.85');
    _connTmpLine.setAttribute('marker-end', `url(#${_uid}-arr-tmp)`);
    _svg.appendChild(_connTmpLine);
    document.addEventListener('mousemove', _onConnMove);
    document.addEventListener('mouseup', _onConnEnd, { once: true });
  }

  function _onConnMove(e) {
    if (!_connSrc || !_connTmpLine) return;
    const cR = containerEl.getBoundingClientRect();
    const p1 = _cardRight(_connSrc);
    const x2 = e.clientX - cR.left;
    const y2 = e.clientY - cR.top;
    const cx = (p1.x + x2) / 2;
    _connTmpLine.setAttribute('d', `M ${p1.x} ${p1.y} C ${cx} ${p1.y}, ${cx} ${y2}, ${x2} ${y2}`);
  }

  function _onConnEnd(e) {
    document.removeEventListener('mousemove', _onConnMove);
    if (_connTmpLine) { _connTmpLine.remove(); _connTmpLine = null; }
    const src = _connSrc;
    _connSrc = null;
    if (!src) return;
    const target = document.elementFromPoint(e.clientX, e.clientY);
    const targetCard = target?.closest('[data-code]');
    const targetCode = targetCard?.dataset?.code;
    if (targetCode && targetCode !== src) _togglePrereqApi(src, targetCode);
  }

  function _cardRight(code) {
    const el = _card(code);
    if (!el) return { x: 0, y: 0 };
    const cR = containerEl.getBoundingClientRect();
    const eR = el.getBoundingClientRect();
    return { x: eR.right - cR.left, y: eR.top + eR.height / 2 - cR.top };
  }

  /* ── View-mode highlight ──────────────────────────────────────────── */
  function _viewClick(code) {
    if (_selected === code) {
      _selected = null;
      _courses.forEach(c => _resetCard(c.course_code));
      drawArrows(null);
      return;
    }
    _selected = code;
    const sel = _courses.find(c => c.course_code === code);
    if (!sel) return;
    const prereqSet = new Set(sel.prereqs || []);
    const sucSet    = new Set(_courses.filter(c => (c.prereqs || []).includes(code)).map(c => c.course_code));
    _courses.forEach(c => {
      const el = _card(c.course_code);
      if (!el) return;
      if (c.course_code === code) {
        el.style.opacity   = '1';
        el.style.outline   = '2.5px solid #3b82f6';
        el.style.boxShadow = '0 0 0 4px rgba(59,130,246,.2),0 4px 14px rgba(0,0,0,.15)';
      } else if (prereqSet.has(c.course_code)) {
        el.style.opacity   = '1';
        el.style.outline   = '2.5px solid #10b981';
        el.style.boxShadow = '0 0 0 3px rgba(16,185,129,.2)';
      } else if (sucSet.has(c.course_code)) {
        el.style.opacity   = '1';
        el.style.outline   = '2.5px solid #f59e0b';
        el.style.boxShadow = '0 0 0 3px rgba(245,158,11,.18)';
      } else {
        el.style.opacity   = '0.22';
        el.style.outline   = 'none';
        el.style.boxShadow = 'none';
      }
    });
    drawArrows(code);
  }

  /* ── Prereq API ───────────────────────────────────────────────────── */
  async function _togglePrereqApi(courseCode, prereqCode) {
    const srcCourse  = _courses.find(c => c.course_code === courseCode);
    const isExisting = (srcCourse?.prereqs || []).includes(prereqCode);
    const prereqName = _courses.find(c => c.course_code === prereqCode)?.course_name || prereqCode;
    const srcName    = srcCourse?.course_name || courseCode;

    if (!confirm(`${isExisting ? 'Xóa' : 'Thêm'} tiên quyết?\n${prereqCode} — ${prereqName}\n→ ${courseCode} — ${srcName}`)) return;

    let res;
    if (isExisting) {
      res = await _call(
        `/admin/prerequisites/${encodeURIComponent(courseCode)}/${encodeURIComponent(prereqCode)}`,
        { method: 'DELETE', headers: apiHeaders },
      );
    } else {
      res = await _call('/admin/prerequisites', {
        method: 'POST',
        headers: { ...apiHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ course_code: courseCode, prerequisite_code: prereqCode }),
      });
    }

    if (!res.ok) { _toast(res.data?.detail || 'Lỗi cập nhật tiên quyết', false); return; }
    _toast(isExisting ? 'Đã xóa tiên quyết' : 'Đã thêm tiên quyết');
    if (onRefresh) onRefresh();
  }

  /* ── Edit mode toggle ─────────────────────────────────────────────── */
  function setEditMode(v) {
    _editMode = v;
    _connSrc  = null;
    _selected = null;
    containerEl.querySelectorAll('.cc-card-drag').forEach(h => h.style.display = v ? 'flex' : 'none');
    containerEl.querySelectorAll('.cc-port').forEach(p => { p.style.display = v ? 'block' : 'none'; });
    containerEl.querySelectorAll('[data-code]').forEach(card => {
      card.draggable = canEdit;
    });
    _applyEditModeStyles(v);
    _setStatus(v ? _EDIT_HINT : '');
    drawArrows(null);
  }

  function _applyEditModeStyles(on) {
    _courses.forEach(c => {
      const el = _card(c.course_code);
      if (!el) return;
      el.style.opacity   = '1';
      el.style.outline   = on ? '1.5px dashed #c7d2fe' : 'none';
      el.style.boxShadow = '0 1px 3px rgba(0,0,0,.08)';
    });
  }

  /* ── Draw SVG arrows ──────────────────────────────────────────────── */
  function drawArrows(sel) {
    _svg.querySelectorAll('.cc-edge').forEach(el => el.remove());
    const cR = containerEl.getBoundingClientRect();

    _courses.forEach(course => {
      const toEl = _card(course.course_code);
      if (!toEl) return;
      const toR = toEl.getBoundingClientRect();
      const x2  = toR.left - cR.left;
      const y2  = toR.top + toR.height / 2 - cR.top;

      (course.prereqs || []).forEach(prereqCode => {
        const fromEl = _card(prereqCode);
        if (!fromEl) return;
        const fromR = fromEl.getBoundingClientRect();
        const x1    = fromR.right - cR.left;
        const y1    = fromR.top + fromR.height / 2 - cR.top;
        if (Math.abs(x1 - x2) < 4) return;

        let stroke = '#94a3b8', sw = '1.5', op = '0.55', marker = `url(#${_uid}-arr)`;
        if (sel) {
          if (course.course_code === sel)  { stroke = '#10b981'; sw = '2.5'; op = '1'; marker = `url(#${_uid}-arr-pre)`; }
          else if (prereqCode === sel)     { stroke = '#f59e0b'; sw = '2.5'; op = '1'; marker = `url(#${_uid}-arr-suc)`; }
          else                             { op = '0.07'; }
        }

        const cx   = (x1 + x2) / 2;
        const path = document.createElementNS(svgNS, 'path');
        path.setAttribute('class', 'cc-edge');
        path.setAttribute('d', `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`);
        path.setAttribute('stroke', stroke);
        path.setAttribute('stroke-width', sw);
        path.setAttribute('fill', 'none');
        path.setAttribute('opacity', op);
        path.setAttribute('marker-end', marker);
        _svg.appendChild(path);
      });
    });
  }

  /* ── Helpers ─────────────────────────────────────────────────────── */
  function _card(code) { return document.getElementById(_uid + '-card-' + code); }

  function _resetCard(code) {
    const el = _card(code);
    if (el) {
      el.style.opacity   = '1';
      el.style.outline   = _editMode ? '1.5px dashed #c7d2fe' : 'none';
      el.style.boxShadow = '0 1px 3px rgba(0,0,0,.08)';
    }
  }

  function _setStatus(html) { if (statusEl) statusEl.innerHTML = html; }

  /* ── Public API ───────────────────────────────────────────────────── */
  return { render, drawArrows, setEditMode };
}
