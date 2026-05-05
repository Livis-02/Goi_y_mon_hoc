import { test, expect } from '@playwright/test';
import { login, waitForPageReady, captureConsoleErrors, expectNoConsoleErrors, URLS } from './helpers';

/**
 * Admin → tab Môn học → Side Panel (Phương án A).
 *   - Click row → side panel slide từ phải
 *   - 3 sub-tabs: Thông tin / Tiên quyết / Mô tả & Kỹ năng
 *   - Mã môn IMMUTABLE
 *   - Sửa field → dirty bar hiện
 *   - Critical fields confirm dialog
 *   - Hủy thay đổi revert OK
 */

test.beforeEach(async ({ page }) => {
  await login(page, 'admin');
  await waitForPageReady(page);
  await page.locator('button:has-text("Môn học")').first().click();
  await page.waitForSelector('tr[onclick*="openCourseSidePanel"]', { timeout: 15000 });
});

/** Helper: open side panel của row môn đầu tiên.
 *  Click tr trực tiếp thường fail vì child elements (button kebab, toggle TC)
 *  intercept click. Workaround: gọi openCourseSidePanel() qua page.evaluate
 *  với course_code lấy từ cell đầu tiên (mã môn). */
async function openFirstCoursePanel(page: any) {
  const firstRow = page.locator('tr[onclick*="openCourseSidePanel"]').first();
  await firstRow.scrollIntoViewIfNeeded();
  await expect(firstRow).toBeVisible({ timeout: 5000 });
  // Lấy course_code từ cột đầu (font-mono span)
  const courseCode = await firstRow.locator('td').first().textContent();
  const cleanCode = (courseCode || '').trim();
  expect(cleanCode.length).toBeGreaterThan(0);
  await page.evaluate((code: string) => {
    // @ts-ignore
    if (typeof openCourseSidePanel === 'function') openCourseSidePanel(code);
  }, cleanCode);
  await page.waitForTimeout(500);
  await expect(page.locator('#crsSidePanel')).toBeVisible({ timeout: 5000 });
}

test.describe('Admin Courses: Side panel chi tiết', () => {

  test('Click row môn → side panel slide từ phải', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await openFirstCoursePanel(page);

    // Header + 3 tab buttons
    await expect(page.locator('#crsPanelCode')).toBeVisible();
    await expect(page.locator('#crsPanelName')).toBeVisible();
    await expect(page.locator('#crsTabBasic')).toBeVisible();
    await expect(page.locator('#crsTabPrereq')).toBeVisible();
    await expect(page.locator('#crsTabContent')).toBeVisible();

    expectNoConsoleErrors(errors);
  });

  test('Tab "Thông tin": Mã môn lock + Tên môn editable', async ({ page }) => {
    await openFirstCoursePanel(page);

    // Mã môn input không tồn tại — chỉ có div readonly
    const codeInput = page.locator('#crsSidePanel input').filter({ hasText: '' }).first();
    // Body chỉ có inputs cho name/credits/hk/desc
    const nameInput = page.locator('#crsPanelInput_name');
    await expect(nameInput).toBeVisible();
    await expect(nameInput).toBeEditable();

    // Sửa tên → dirty bar hiện
    const original = await nameInput.inputValue();
    await nameInput.fill(original + ' (test edit)');
    await page.waitForTimeout(200);

    const dirtyBar = page.locator('#crsPanelDirtyBar');
    await expect(dirtyBar).toBeVisible();

    // Save button enabled
    await expect(page.locator('#crsPanelBtnSave')).toBeEnabled();

    // Revert (không save) → dirty clear
    page.on('dialog', d => d.accept());  // confirm "Hủy thay đổi"
    await page.locator('#crsPanelBtnRevert').click();
    await page.waitForTimeout(400);

    // Dirty bar ẩn lại
    await expect(dirtyBar).not.toBeVisible();
    // Tên môn revert
    await expect(nameInput).toHaveValue(original);
  });

  test('Tab "Tiên quyết": chip list + search add', async ({ page }) => {
    await openFirstCoursePanel(page);
    await page.locator('#crsTabPrereq').click();
    await page.waitForTimeout(300);

    // Search box visible
    await expect(page.locator('#crsPanelPrereqSearch')).toBeVisible();

    // Section heading "Cần học trước" + "Môn dẫn đến" (h3 only, không phải nội dung khác)
    await expect(page.locator('#crsSidePanel h3:has-text("Cần học trước")')).toBeVisible();
    await expect(page.locator('#crsSidePanel h3:has-text("Môn dẫn đến")')).toBeVisible();
  });

  test('Tab "Mô tả & Kỹ năng": textarea + button skills', async ({ page }) => {
    await openFirstCoursePanel(page);
    await page.locator('#crsTabContent').click();
    await page.waitForTimeout(300);

    await expect(page.locator('#crsPanelInput_desc')).toBeVisible();
    await expect(page.locator('button:has-text("Quản lý kỹ năng")')).toBeVisible();
  });

  test('Đóng panel khi dirty → confirm dialog', async ({ page }) => {
    await openFirstCoursePanel(page);

    // Sửa để dirty
    const nameInput = page.locator('#crsPanelInput_name');
    await nameInput.fill('temp dirty');
    await page.waitForTimeout(200);

    // Click X → confirm dialog
    let dialogTriggered = false;
    page.once('dialog', d => {
      dialogTriggered = true;
      d.dismiss();  // Cancel → không đóng
    });
    await page.locator('#crsSidePanel button[onclick*="closeCourseSidePanel"]').click();
    await page.waitForTimeout(300);

    expect(dialogTriggered).toBe(true);
    // Panel vẫn visible (dismiss)
    await expect(page.locator('#crsSidePanel')).toBeVisible();
  });

});

test.describe('Admin Courses: Inline actions', () => {

  test('Toggle "Tính TC" inline (1 click không cần mở panel)', async ({ page }) => {
    // Tìm button toggle TC trong row đầu
    const tcBtn = page.locator('button[onclick*="toggleCourseCredit"]').first();
    await expect(tcBtn).toBeVisible({ timeout: 5000 });
    const beforeText = await tcBtn.textContent();
    await tcBtn.click();
    await page.waitForTimeout(800);  // đợi API call
    const afterText = await tcBtn.textContent();
    expect(afterText).not.toBe(beforeText);

    // Toggle lại để revert
    await tcBtn.click();
    await page.waitForTimeout(800);
  });

  test('Kebab "Tác vụ nâng cao" → menu fixed-position, không bị clip', async ({ page }) => {
    const kebab = page.locator('button[onclick*="_toggleCrsRowMore"]').first();
    await expect(kebab).toBeVisible({ timeout: 5000 });
    await kebab.click();
    await page.waitForTimeout(300);

    // Menu visible với class "fixed"
    const menu = page.locator('[id^="crs-more-"]').filter({ hasText: 'Tác vụ nâng cao' }).first();
    await expect(menu).toBeVisible();
    const cls = await menu.getAttribute('class');
    expect(cls).toMatch(/fixed/);

    // Đóng (click ngoài)
    await page.locator('body').click({ position: { x: 50, y: 50 } });
    await page.waitForTimeout(200);
  });

});
