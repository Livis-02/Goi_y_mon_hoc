import { test, expect } from '@playwright/test';
import { login, captureConsoleErrors, expectNoConsoleErrors, waitForPageReady, URLS } from './helpers';

/**
 * SMOKE TEST — đi qua mọi page cho 3 role, check:
 *   1. Page load không lỗi 5xx
 *   2. Console không có error (trừ noise đã filter)
 *   3. Element key của page render (heading / breadcrumb)
 *   4. Network: không có 5xx response
 *
 * Chạy đầu tiên — nếu pass thì các spec chi tiết sẽ pass.
 */

const STUDENT_PAGES = [
  { url: URLS.home,     heading: /Tổng quan|Chào/ },
  { url: URLS.roadmap,  heading: /Lộ trình tích hợp/ },
  { url: URLS.grades,   heading: /Bảng điểm/ },
  { url: URLS.career,   heading: /Mục tiêu nghề/ },
  { url: URLS.ai,       heading: /AI|Trợ lý/ },
  { url: URLS.msg,      heading: /Hỏi cố vấn|Tin nhắn/ },
  { url: URLS.notif,    heading: /Thông báo/ },
  { url: URLS.settings, heading: /Cài đặt/ },
];

test.describe('Smoke: Sinh viên — duyệt qua mọi page', () => {
  test('SV: đăng nhập + duyệt 8 page chính, không có console error', async ({ page }) => {
    test.setTimeout(60_000);  // 8 pages × ~5s với overlay block + init retry → cần >30s default
    const errors = captureConsoleErrors(page);
    const networkErrors: string[] = [];
    page.on('response', (res) => {
      if (res.status() >= 500) networkErrors.push(`${res.status()} ${res.url()}`);
    });

    await login(page, 'student');
    await waitForPageReady(page);

    for (const p of STUDENT_PAGES) {
      await test.step(`Visit ${p.url}`, async () => {
        await page.goto(p.url);
        await waitForPageReady(page);
        // Check heading hoặc nav crumb match
        const has = await page.locator('h1, h2, nav span').filter({ hasText: p.heading }).count();
        expect(has, `Page ${p.url} thiếu heading khớp ${p.heading}`).toBeGreaterThan(0);
      });
    }

    expect(networkErrors, '5xx requests:\n' + networkErrors.join('\n')).toHaveLength(0);
    expectNoConsoleErrors(errors);
  });
});

test.describe('Smoke: Cố vấn', () => {
  test('GV: login → advisor.html render', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await login(page, 'advisor');
    await waitForPageReady(page);
    expect(page.url()).toContain('advisor.html');
    // Sidebar advisor có ít nhất 1 nav item về sinh viên (advisor sections:
    // overview/students/notes/assign/ctdt — text varies)
    const sidebarBtns = page.locator('aside button, aside a, nav button, nav a');
    expect(await sidebarBtns.count()).toBeGreaterThan(0);
    expectNoConsoleErrors(errors);
  });
});

test.describe('Smoke: Admin', () => {
  test('Admin: login → admin.html với 6 tabs', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await login(page, 'admin');
    await waitForPageReady(page);
    expect(page.url()).toContain('admin.html');

    // Sidebar admin: 6 tab buttons
    const tabs = ['Tổng quan', 'Sinh viên', 'Cố vấn', 'Môn học', 'Thông báo', 'Nhật ký'];
    for (const t of tabs) {
      const btn = page.locator(`button:has-text("${t}")`).first();
      await expect(btn, `Tab "${t}" không tìm thấy`).toBeVisible();
    }
    expectNoConsoleErrors(errors);
  });
});
