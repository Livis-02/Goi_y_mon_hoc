# EduGuide — Playwright E2E Test Suite

Tự động test giao diện cho 3 role (Sinh viên / Cố vấn / Admin) với Playwright.

## Setup (một lần)

```bash
# Ở root project
npm install                        # cài @playwright/test
npx playwright install chromium    # cài Chromium browser (~150MB)
```

## Tiền điều kiện trước khi chạy

1. **Backend chạy port 8000:**
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

2. **Frontend serve port 5500** (đúng cấu hình `playwright.config.ts`):
   ```bash
   # Cách 1: live-server (npm install -g live-server)
   live-server --port=5500 --no-browser
   # Cách 2: Python
   python -m http.server 5500
   ```
   (Phải serve từ root project, vì test path `/frontend/pages/index.html`)

3. **DB seeded** với test accounts:
   - SV: `sv14001` / `220238` (chưa first-login → cần reset hoặc seed lại)
   - GV: `KHMT001` / `714526`
   - Admin: `demo_admin` / `Demo@2025`

   Kiểm tra `data/test_data/legacy_k14/seed_passwords.txt` cho danh sách đầy đủ.

## Chạy tests

```bash
# Toàn bộ suite (headless, fastest)
npm test

# Headed (xem browser run real-time)
npm run test:headed

# UI mode (interactive, recommended cho dev)
npm run test:ui

# Smoke test only (nhanh, chạy đầu tiên)
npm run test:smoke

# Theo nhóm role
npm run test:student
npm run test:admin

# Xem report HTML sau khi chạy
npm run report
```

## Files

```
tests/e2e/
├── helpers.ts              # ACCOUNTS, URLS, login(), captureConsoleErrors()
├── smoke.spec.ts           # Smoke 3 roles + console error scan
├── auth.spec.ts            # Login form + sai password + logout
├── student-roadmap.spec.ts # Mode toggle (mine/explore), modal course detail
├── student-chat.spec.ts    # FAB visibility, AI chat empty state, messaging modals
├── admin-dashboard.spec.ts # 5 stat cards 3-color, charts, warnings, recent logs
├── admin-courses.spec.ts   # Side panel 3 sub-tabs, dirty save, kebab fixed-pos
├── admin-users.spec.ts     # Flat sorted table + cohort badge + master checkbox
└── README.md               # File này
```

## Troubleshooting

### "Login failed: account requires first-login"
SV `sv14001` chưa hoàn tất first-login (đổi password lần đầu). Cách fix:
- Login manual `sv14001`/`220238` → đổi password → password mới setup là gì → cập nhật `helpers.ts` `ACCOUNTS.student.password`
- Hoặc reset DB seed lại từ đầu

### "Connection refused 127.0.0.1:8000"
Backend chưa chạy. Start:
```bash
uvicorn backend.main:app --reload --port 8000
```

### "404 Not Found /frontend/pages/index.html"
Frontend serve sai thư mục. Phải serve từ ROOT project (chứa `frontend/`), không phải từ `frontend/pages/`.

### Test fails với "TimeoutError: Locator not found"
- Hard reload `Ctrl+Shift+R` ở browser thường không giúp Playwright (browser headless mới)
- Check `playwright-report/` HTML report → có screenshot lỗi tại moment fail
- Có thể UI đổi → update selector trong spec file

### Test bị flaky
- Tăng `timeout` trong `playwright.config.ts`
- Thêm `await page.waitForTimeout(N)` sau action async
- Dùng `expect(locator).toBeVisible({ timeout: 8000 })` thay vì `await expect(locator).toBeVisible()` ngay

## Tip

- **Debug 1 test:** `npx playwright test admin-courses.spec.ts:42 --headed --debug` (line 42 ~ test name)
- **Trace viewer:** mỗi failure tạo trace zip trong `test-results/` → `npx playwright show-trace path/to/trace.zip`
- **Screenshot mỗi step:** thêm `await page.screenshot({ path: 'debug.png' });` trong test

## Coverage hiện tại

| Spec file | # tests | Mục tiêu |
|---|---|---|
| smoke.spec.ts | 3 | Login + duyệt qua mọi page, không lỗi console |
| auth.spec.ts | 6 | Login flow, sai pass, logout, redirect đúng role |
| student-roadmap.spec.ts | 7 | Mode toggle, watermark explore, modal course |
| student-chat.spec.ts | 8 | FAB visibility, AI empty state, messaging modals |
| admin-dashboard.spec.ts | 5 | 5 stat cards, charts, warnings, recent logs |
| admin-courses.spec.ts | 7 | Side panel 3 tabs, dirty save, kebab |
| admin-users.spec.ts | 6 | Flat sort, cohort badge, master checkbox |
| **Tổng** | **~42 tests** | |

Run full suite ~2-3 phút headed, ~1.5 phút headless.
