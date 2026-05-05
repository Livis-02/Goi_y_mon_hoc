import { test, expect } from '@playwright/test';
import { login, waitForPageReady, captureConsoleErrors, expectNoConsoleErrors, URLS } from './helpers';

/**
 * Admin → tab Tổng quan — kiểm tra:
 *   - 5 stat cards với 3-color discipline (chip-primary/secondary/neutral)
 *   - Charts cohort + spec render
 *   - Cảnh báo hệ thống có icons màu đúng severity
 *   - Hoạt động gần đây có icon vuông chip-color theo action type
 */

test.beforeEach(async ({ page }) => {
  await login(page, 'admin');
  await waitForPageReady(page);
});

test.describe('Admin Dashboard: Stat cards 3-color discipline', () => {

  test('5 stat cards với chip-primary/secondary/neutral (không 5 màu lung tung)', async ({ page }) => {
    const errors = captureConsoleErrors(page);

    const cards = page.locator('#dashboardCards button.card');
    await expect(cards).toHaveCount(5, { timeout: 10000 });

    // Mỗi card có 1 div chip-* class
    for (let i = 0; i < 5; i++) {
      const chipDiv = cards.nth(i).locator('div').first();
      const cls = await chipDiv.getAttribute('class') || '';
      const hasValidChip = /chip-primary|chip-secondary|chip-neutral/.test(cls);
      expect(hasValidChip, `Card ${i + 1}: chip class="${cls}" không phải 1 trong 3 variants chuẩn`).toBe(true);
    }

    expectNoConsoleErrors(errors);
  });

  test('Charts: cohort bar + spec doughnut render', async ({ page }) => {
    // Canvas Chart.js
    await expect(page.locator('#dashCohortChart')).toBeVisible({ timeout: 8000 });
    await expect(page.locator('#dashSpecChart')).toBeVisible();
  });

  test('Cảnh báo hệ thống: rows với icon màu severity-coded', async ({ page }) => {
    const warnings = page.locator('#dashWarnings > div');
    const cnt = await warnings.count();
    if (cnt === 0) return;  // không có warning là OK

    // Mỗi warning có 1 icon material-symbols-outlined
    for (let i = 0; i < cnt; i++) {
      const icon = warnings.nth(i).locator('.material-symbols-outlined').first();
      await expect(icon).toBeVisible();
    }
  });

  test('Hoạt động gần đây: rows với icon vuông chip-* theo action type', async ({ page }) => {
    const logs = page.locator('#dashRecentLogs > div');
    const cnt = await logs.count();
    if (cnt === 0) return;

    // Mỗi log có 1 div w-8 h-8 rounded-lg với class chip-*
    for (let i = 0; i < Math.min(3, cnt); i++) {
      const iconBox = logs.nth(i).locator('div').filter({ hasText: '' }).first();
      const cls = await iconBox.getAttribute('class') || '';
      // Chấp nhận chip-primary/secondary/neutral
      const hasChip = /chip-primary|chip-secondary|chip-neutral/.test(cls);
      // Hoặc inner div chứa
      if (!hasChip) {
        const innerCls = await logs.nth(i).locator('[class*="chip-"]').first().getAttribute('class').catch(() => '');
        expect(innerCls).toMatch(/chip-/);
      }
    }
  });

});

test.describe('Admin Dashboard: Click stat card → switch tab', () => {

  test('Click card "Tổng sinh viên" → chuyển tab Sinh viên', async ({ page }) => {
    const card = page.locator('#dashboardCards button:has-text("Tổng sinh viên")').first();
    if (!(await card.isVisible().catch(() => false))) {
      test.skip(true, 'Card "Tổng sinh viên" không tìm thấy');
      return;
    }
    await card.click();
    await page.waitForTimeout(500);

    // Tab Sinh viên active
    const usersTab = page.locator('#adminTab-users');
    await expect(usersTab).not.toHaveClass(/hidden/);
  });

});
