import { Page, expect } from '@playwright/test';

// ─── Test accounts (DB phải đã seed bởi generate_demo_data --reset) ──────────
// Tất cả SV/GV trong bộ demo dùng chung password Test1234! (set is_first_login=False
// trong seed → bypass màn setup-account, login thẳng vào app).
// Xem `data/demo/README.md` cho danh sách 10 SV + 10 GV.
export const ACCOUNTS = {
  student: { username: 'sv22001', password: 'Test1234!' },  // top student KHMT
  advisor: { username: 'KHMT001', password: 'Test1234!' },  // head BM KHMT
  admin:   { username: 'demo_admin', password: 'Demo@2026' },
};

// ─── Page paths ───────────────────────────────────────────────────────────────
export const URLS = {
  login:    '/frontend/pages/index.html',
  home:     '/frontend/pages/home.html',
  roadmap:  '/frontend/pages/integrated-roadmap.html',
  grades:   '/frontend/pages/grades.html',
  career:   '/frontend/pages/career-goal.html',
  ai:       '/frontend/pages/ai-chat.html',
  msg:      '/frontend/pages/messaging.html',
  notif:    '/frontend/pages/notifications.html',
  settings: '/frontend/pages/settings.html',
  advisor:  '/frontend/pages/advisor.html',
  admin:    '/frontend/pages/admin.html',
};

/** Login với username/password, đợi redirect tới đúng page theo role. */
export async function login(page: Page, role: keyof typeof ACCOUNTS) {
  const { username, password } = ACCOUNTS[role];
  await page.goto(URLS.login);
  // Login form: #loginUsername + #loginPassword + #loginBtn
  await page.locator('#loginUsername').fill(username);
  await page.locator('#loginPassword').fill(password);
  await page.locator('#loginBtn').click();

  // Đợi navigate khỏi /index.html (success) hoặc dialog first-login
  await page.waitForURL(/(home|admin|advisor|reset-password)\.html/, { timeout: 10_000 });

  // Nếu rơi vào màn first-login → fail hard với message rõ ràng
  if (page.url().includes('reset-password.html')) {
    throw new Error(
      `Account "${username}" yêu cầu first-login (reset password).\n` +
      `→ Reset DB hoặc dùng SV khác đã first-login xong, hoặc handle dialog trong helper.`
    );
  }
}

/** Logout — click avatar → "Đăng xuất". Defensive với null. */
export async function logout(page: Page) {
  // Try sidebar logout first (admin/advisor có nút Đăng xuất ở sidebar)
  const sidebarLogout = page.locator('button:has-text("Đăng xuất"), a:has-text("Đăng xuất")').first();
  if (await sidebarLogout.isVisible({ timeout: 1500 }).catch(() => false)) {
    await sidebarLogout.click();
  } else {
    // Fallback: avatar dropdown
    const avatar = page.locator('#avatarMenu button, button[aria-label*="ài khoản"]').first();
    await avatar.click();
    await page.locator('button:has-text("Đăng xuất")').click();
  }
  await page.waitForURL(/index\.html/, { timeout: 5_000 });
}

/**
 * Capture console errors during a test. Auto-fails test if errors found.
 * Usage:
 *   const errors = captureConsoleErrors(page);
 *   ... do stuff ...
 *   expectNoConsoleErrors(errors);
 */
export function captureConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Bỏ qua các noise phổ biến không phải bug app:
      //   - failed favicon load
      //   - Tailwind CDN warning về production
      //   - "Failed to fetch": transient khi browser hủy in-flight fetch lúc
      //     navigate (full reload trong MPA mode v16+ — browser cleanup tự nhiên)
      //   - AbortError: cùng lý do
      if (text.includes('favicon')) return;
      if (text.includes('cdn.tailwindcss.com should not be used in production')) return;
      if (text.includes('Failed to fetch')) return;
      if (text.includes('AbortError') || text.includes('aborted')) return;
      errors.push(text);
    }
  });
  page.on('pageerror', (err) => {
    if (err.message.includes('Failed to fetch') || err.message.includes('AbortError')) return;
    errors.push(`PAGE ERROR: ${err.message}`);
  });
  return errors;
}

export function expectNoConsoleErrors(errors: string[]) {
  if (errors.length > 0) {
    throw new Error(`Found ${errors.length} console errors:\n${errors.join('\n---\n')}`);
  }
}

/** Đợi page:ready event (do init() dispatch) — đảm bảo data đã load.
 *  Check sync `window.__initDone` flag trước khi attach listener — tránh race
 *  trường hợp event đã fire xong trước khi page.evaluate chạy. */
export async function waitForPageReady(page: Page, timeout = 12000) {
  await page.evaluate((t) => {
    return new Promise((resolve) => {
      // Nếu init đã done sync → resolve ngay, không cần đợi event
      // @ts-ignore
      if (window.__initDone) return resolve(null);
      const tid = setTimeout(resolve, t);
      window.addEventListener('page:ready', () => {
        clearTimeout(tid);
        resolve(null);
      }, { once: true });
    });
  }, timeout);
}

/** Helper: scroll element into view trước khi assert visible (vì page dài). */
export async function scrollAndExpectVisible(page: Page, selector: string) {
  const el = page.locator(selector).first();
  await el.scrollIntoViewIfNeeded();
  await expect(el).toBeVisible();
}
