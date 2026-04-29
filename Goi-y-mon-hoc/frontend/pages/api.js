/* api.js — fetch wrapper with auth header, JSON parsing, and toast helpers.
   Depends on: auth.js (API_BASE, getToken, clearToken). */

/** Generic authenticated fetch. Returns parsed JSON on 2xx, throws on error.
    Pass `raw: true` in opts to get the Response object back instead. */
async function apiFetch(path, opts) {
  opts = opts || {};
  const headers = Object.assign({}, opts.headers || {});
  if (!(opts.body instanceof FormData) && opts.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const url = path.startsWith("http") ? path : `${window.API_BASE}${path}`;
  let res;
  try {
    res = await fetch(url, {
      method: opts.method || "GET",
      headers,
      body:
        opts.body && !(opts.body instanceof FormData) && typeof opts.body !== "string"
          ? JSON.stringify(opts.body)
          : opts.body,
    });
  } catch (err) {
    const e = new Error("Không kết nối được máy chủ");
    e.cause = err;
    throw e;
  }

  if (res.status === 401) {
    clearToken();
    window.location.replace("index.html");
    throw new Error("Phiên đăng nhập đã hết hạn");
  }

  if (opts.raw) return res;

  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch (_) { data = text; }
  }
  if (!res.ok) {
    const msg =
      (data && (data.detail || data.message)) ||
      (typeof data === "string" ? data : `HTTP ${res.status}`);
    const err = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

const apiGet = (p, o) => apiFetch(p, Object.assign({ method: "GET" }, o || {}));
const apiPost = (p, body, o) => apiFetch(p, Object.assign({ method: "POST", body }, o || {}));
const apiPut = (p, body, o) => apiFetch(p, Object.assign({ method: "PUT", body }, o || {}));
const apiPatch = (p, body, o) => apiFetch(p, Object.assign({ method: "PATCH", body }, o || {}));
const apiDelete = (p, o) => apiFetch(p, Object.assign({ method: "DELETE" }, o || {}));

/* -------------------- Toast helpers -------------------- */
(function ensureToastContainer() {
  if (document.getElementById("toastContainer")) return;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureToastContainer);
    return;
  }
  const c = document.createElement("div");
  c.id = "toastContainer";
  c.className = "fixed top-4 right-4 z-[1000] flex flex-col gap-2 pointer-events-none";
  document.body.appendChild(c);
})();

/** Show a toast: kind = "success" | "error" | "warning" | "info" */
function toast(message, kind, ms) {
  kind = kind || "info";
  ms = ms || 4000;
  const colors = {
    success: "bg-secondary text-on-secondary",
    error: "bg-error text-on-error",
    warning: "bg-tertiary-container text-on-tertiary-container",
    info: "bg-primary text-on-primary",
  };
  const icons = {
    success: "check_circle",
    error: "error",
    warning: "warning",
    info: "info",
  };
  const c = document.getElementById("toastContainer") || document.body;
  const el = document.createElement("div");
  el.className =
    `pointer-events-auto px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 max-w-md font-body-sm text-body-sm ${colors[kind] || colors.info}`;
  el.innerHTML = `<span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">${icons[kind] || icons.info}</span><span class="flex-1">${escapeHtml(message)}</span><button class="opacity-70 hover:opacity-100 ml-1"><span class="material-symbols-outlined text-[18px]">close</span></button>`;
  el.style.opacity = "0";
  el.style.transform = "translateY(-6px)";
  el.style.transition = "opacity .25s ease, transform .25s ease";
  c.appendChild(el);
  requestAnimationFrame(() => {
    el.style.opacity = "1";
    el.style.transform = "translateY(0)";
  });
  const close = () => {
    el.style.opacity = "0";
    el.style.transform = "translateY(-6px)";
    setTimeout(() => el.remove(), 250);
  };
  el.querySelector("button")?.addEventListener("click", close);
  setTimeout(close, ms);
}

/* -------------------- Format helpers -------------------- */
function fmtScore(score, digits) {
  if (score == null || score === "") return "—";
  const n = Number(score);
  if (Number.isNaN(n)) return "—";
  return n.toFixed(digits == null ? 2 : digits);
}

function fmtCredits(n) {
  if (n == null) return "0";
  return Number(n).toFixed(0);
}

function fmtRelativeTime(iso) {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diff = (Date.now() - t) / 1000;
  if (diff < 60) return "vừa xong";
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/** Initials from a Vietnamese full name. "Nguyễn Văn An" -> "NA". */
function initialsOf(name) {
  if (!name) return "?";
  const parts = String(name).trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/** Map specialization code → short Vietnamese name. */
const SPEC_NAMES = {
  "7480201_07": "Khoa học máy tính",
  "7480201_06": "Mạng máy tính & Truyền thông",
  "7480201_05": "Công nghệ phần mềm",
  "7480201_09": "Hệ thống thông tin",
  "7480201_04": "Tin học kinh tế",
  "7480201_08": "CNTT định hướng ứng dụng",
};
function specName(code) {
  return SPEC_NAMES[code] || code || "Chưa chốt CN";
}

/** Cohort key from student code: "2100000001" → "K21". */
function cohortFromCode(code) {
  if (!code) return "";
  const m = String(code).match(/^(\d{2})/);
  return m ? `K${m[1]}` : "";
}
