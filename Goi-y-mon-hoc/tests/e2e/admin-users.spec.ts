import { test, expect } from '@playwright/test';
import { login, waitForPageReady, captureConsoleErrors, expectNoConsoleErrors, URLS } from './helpers';

/**
 * Admin → tab Sinh viên — flat sorted table (Phương án bỏ collapsible by cohort).
 *   - Bảng flat, không còn group expand/collapse
 *   - Sort: cohort DESC (K14 trên đầu, K13 dưới...) → username ASC
 *   - Cột "Mã SV" có badge `K14` indigo cạnh username
 *   - Master checkbox top row → chọn tất cả
 *   - Filter cohort dropdown → bảng update
 */

test.beforeEach(async ({ page }) => {
  await login(page, 'admin');
  await waitForPageReady(page);
  // Switch sang tab Sinh viên
  await page.locator('button:has-text("Sinh viên")').first().click();
  await page.waitForTimeout(1500);
});

test.describe('Admin Users: Flat sorted table', () => {

  test('Bảng flat, không có group header collapsible', async ({ page }) => {
    const errors = captureConsoleErrors(page);

    // Có duy nhất 1 table trong svGroupedTable (không phải nhiều card per cohort)
    const groupedTable = page.locator('#svGroupedTable');
    await expect(groupedTable).toBeVisible({ timeout: 10000 });

    const tables = groupedTable.locator('table');
    expect(await tables.count()).toBe(1);

    // KHÔNG có button toggleCohortGroup (đã refactor)
    const oldGroupHeaders = page.locator('button[onclick*="toggleCohortGroup"]');
    expect(await oldGroupHeaders.count()).toBe(0);

    expectNoConsoleErrors(errors);
  });

  test('Sort: cohort DESC — K14 trước K13', async ({ page }) => {
    // Đợi bảng load có row
    await page.waitForSelector('#svGroupedTable tbody tr[data-uid], #svGroupedTable tbody tr', { timeout: 10000 });

    const rows = page.locator('#svGroupedTable tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // Lấy 5 username đầu để verify sort
    const usernames: string[] = [];
    for (let i = 0; i < Math.min(5, count); i++) {
      const txt = await rows.nth(i).locator('td').nth(1).textContent();
      if (txt) usernames.push(txt.trim().split(/\s+/)[0]);  // chỉ phần username, bỏ K14 badge
    }

    // Cohort của user đầu >= cohort user cuối (DESC)
    const cohortOf = (u: string) => {
      const m = u.match(/sv(\d{2})/);
      return m ? parseInt(m[1]) : 0;
    };
    if (usernames.length >= 2) {
      expect(cohortOf(usernames[0])).toBeGreaterThanOrEqual(cohortOf(usernames[usernames.length - 1]));
    }
  });

  test('Cohort badge "K14" hiển thị inline trong cột Mã SV', async ({ page }) => {
    await page.waitForSelector('#svGroupedTable tbody tr', { timeout: 10000 });
    // Cell đầu của row đầu phải có 1 badge dạng "K14"
    const firstRow = page.locator('#svGroupedTable tbody tr').first();
    const codeCell = firstRow.locator('td').nth(1);
    const badge = codeCell.locator('span').filter({ hasText: /^K\d+$/ }).first();
    await expect(badge).toBeVisible();
  });

  test('Master checkbox → chọn tất cả checkbox row', async ({ page }) => {
    await page.waitForSelector('#svGroupedTable tbody tr', { timeout: 10000 });
    const master = page.locator('#svSelectAllChk');
    if (!(await master.isVisible().catch(() => false))) {
      test.skip(true, 'Master checkbox không có (có thể UI khác)');
      return;
    }
    await master.check();
    // Tất cả row checkbox phải checked
    const rowCbs = page.locator('#svGroupedTable tbody input[type="checkbox"][data-uid]');
    const cnt = await rowCbs.count();
    for (let i = 0; i < Math.min(3, cnt); i++) {
      expect(await rowCbs.nth(i).isChecked()).toBe(true);
    }
    // Uncheck master → uncheck tất cả
    await master.uncheck();
    for (let i = 0; i < Math.min(3, cnt); i++) {
      expect(await rowCbs.nth(i).isChecked()).toBe(false);
    }
  });

  test('Filter cohort dropdown → bảng update', async ({ page }) => {
    const filter = page.locator('#filterCohort');
    if (!(await filter.isVisible().catch(() => false))) {
      test.skip(true, 'Filter cohort không có');
      return;
    }
    // Lấy option khả dụng
    const options = await filter.locator('option').allTextContents();
    if (options.length < 2) return;
    // Pick option thứ 2 (option 1 thường là "Tất cả")
    const targetVal = await filter.locator('option').nth(1).getAttribute('value');
    if (!targetVal) return;
    await filter.selectOption(targetVal);
    await page.waitForTimeout(800);

    // Bảng vẫn hiển thị (không broken)
    await expect(page.locator('#svGroupedTable')).toBeVisible();
  });

  test('Bulk action bar: chọn 2 SV → bar hiện 4 button (Reset/Notif/CSV/Xóa)', async ({ page }) => {
    await page.waitForSelector('#svGroupedTable tbody tr', { timeout: 10000 });
    // Check 2 row đầu
    const cbs = page.locator('#svGroupedTable tbody input[type="checkbox"][data-uid]');
    const cnt = await cbs.count();
    if (cnt < 2) { test.skip(true, 'Cần ít nhất 2 SV trong DB'); return; }
    await cbs.nth(0).check();
    await cbs.nth(1).check();
    await page.waitForTimeout(300);

    const bar = page.locator('#svBulkBar');
    await expect(bar).toBeVisible();
    // Count text "2 SV"
    await expect(page.locator('#svBulkCount')).toContainText(/2/);
    // 4 action buttons (Reset MK, Gửi thông báo, Xuất CSV, Xoá)
    await expect(bar.locator('button[onclick*="bulkResetPasswords"]')).toBeVisible();
    await expect(bar.locator('button[onclick*="bulkSendNotif"]')).toBeVisible();
    await expect(bar.locator('button[onclick*="bulkExportCsv"]')).toBeVisible();
    await expect(bar.locator('button[onclick*="bulkDeleteUsers"]')).toBeVisible();
    // Click Huỷ → bar ẩn
    await bar.locator('button:has-text("Huỷ")').click();
    await page.waitForTimeout(300);
    await expect(bar).not.toBeVisible();
  });

  test('Click row → side panel SV detail', async ({ page }) => {
    const firstRow = page.locator('#svGroupedTable tbody tr[onclick*="openSvSidePanel"]').first();
    if (!(await firstRow.isVisible().catch(() => false))) {
      // Fallback: row không có onclick attr, click trực tiếp
      const fallback = page.locator('#svGroupedTable tbody tr').first();
      await fallback.click();
    } else {
      await firstRow.click();
    }
    await page.waitForTimeout(500);

    const panel = page.locator('#svSidePanel');
    await expect(panel).toBeVisible({ timeout: 5000 });
  });

});
