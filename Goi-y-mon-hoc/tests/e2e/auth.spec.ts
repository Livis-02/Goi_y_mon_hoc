import { test, expect } from '@playwright/test';
import { ACCOUNTS, URLS, login, captureConsoleErrors, expectNoConsoleErrors } from './helpers';

test.describe('Auth: login + redirect đúng role', () => {

  test('Login form hiển thị đúng + có branding', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.goto(URLS.login);
    // Index có 3 form (login/setup/forgot) — chỉ login visible mặc định.
    // Dùng id cụ thể thay vì selector chung.
    await expect(page.locator('#loginUsername')).toBeVisible();
    await expect(page.locator('#loginPassword')).toBeVisible();
    await expect(page.locator('#loginBtn')).toBeVisible();
    expectNoConsoleErrors(errors);
  });

  test('Login sai password → toast error + ở lại login page', async ({ page }) => {
    await page.goto(URLS.login);
    await page.locator('#loginUsername').fill('sv14001');
    await page.locator('#loginPassword').fill('WRONG_PASSWORD');
    await page.locator('#loginBtn').click();
    // Phải có toast error hoặc text báo sai
    const toastOrError = page.locator('text=/sai|incorrect|không đúng|invalid/i').first();
    await expect(toastOrError).toBeVisible({ timeout: 5000 });
    // URL vẫn ở index.html
    expect(page.url()).toContain('index.html');
  });

  test('SV login → redirect home.html', async ({ page }) => {
    await login(page, 'student');
    expect(page.url()).toMatch(/home\.html/);
    // Topbar avatar hiển thị
    await expect(page.locator('#topbarUserName, #topbarAvatar').first()).toBeVisible();
  });

  test('GV login → redirect advisor.html', async ({ page }) => {
    await login(page, 'advisor');
    expect(page.url()).toMatch(/advisor\.html/);
  });

  test('Admin login → redirect admin.html', async ({ page }) => {
    await login(page, 'admin');
    expect(page.url()).toMatch(/admin\.html/);
  });

  test('Logout → redirect index.html, localStorage cleared', async ({ page }) => {
    await login(page, 'student');
    // Logout: tìm button "Đăng xuất" — sidebar SV có button trực tiếp,
    //   admin/advisor cũng có. Avatar dropdown có thể alternative.
    const sidebarLogout = page.locator('button:has-text("Đăng xuất")').first();
    if (await sidebarLogout.isVisible({ timeout: 2000 }).catch(() => false)) {
      await sidebarLogout.click();
    } else {
      const avatar = page.locator('#avatarMenu button').first();
      await avatar.click();
      await page.locator('button:has-text("Đăng xuất")').click();
    }
    await page.waitForURL(/index\.html/, { timeout: 5000 });
    // localStorage không còn token
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

});
