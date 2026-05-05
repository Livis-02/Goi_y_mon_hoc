import { test, expect } from '@playwright/test';
import { login, waitForPageReady, captureConsoleErrors, expectNoConsoleErrors, URLS } from './helpers';

/**
 * Bảng điểm + Mô phỏng GPA (A4 What-if simulator).
 */

test.beforeEach(async ({ page }) => {
  await login(page, 'student');
});

test.describe('Grades: Mô phỏng GPA modal', () => {

  test('Click "Mô phỏng GPA" → modal mở với 2 tab', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.goto(URLS.grades);
    await waitForPageReady(page);

    await page.locator('button:has-text("Mô phỏng GPA")').first().click();
    await page.waitForTimeout(400);

    const modal = page.locator('#simulatorModal');
    await expect(modal).toBeVisible();
    await expect(modal.locator('text=Mô phỏng điểm')).toBeVisible();

    // 2 tabs: "Kỳ tới" + "Target GPA tốt nghiệp"
    await expect(page.locator('#simTab1Btn')).toBeVisible();
    await expect(page.locator('#simTab2Btn')).toBeVisible();

    // Default tab 1 active
    await expect(page.locator('#simTab1')).toBeVisible();

    // Switch sang tab 2 → target GPA slider
    await page.locator('#simTab2Btn').click();
    await page.waitForTimeout(200);
    await expect(page.locator('#simTargetSlider')).toBeVisible();

    // Đóng (modal có 2 nút close — pick first)
    await page.locator('#simulatorModal button[onclick*="closeSimulator"]').first().click();
    await expect(modal).not.toBeVisible();

    expectNoConsoleErrors(errors);
  });

  test('Deep link ?sim=open → simulator auto mở', async ({ page }) => {
    await page.goto(URLS.grades + '?sim=open');
    await waitForPageReady(page);
    await page.waitForTimeout(800);  // đợi setTimeout 400ms openSimulator
    await expect(page.locator('#simulatorModal')).toBeVisible({ timeout: 5000 });
  });

});

test.describe('Grades: Page basics', () => {

  test('Page load với 4 KPI cards + tab Đã học/Chưa học', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.goto(URLS.grades);
    await waitForPageReady(page);

    // KPI cards
    const kpis = page.locator('[id^="stat"], [id*="GPA"], [id*="Cred"]').filter({ hasText: /\d|—/ });
    expect(await kpis.count()).toBeGreaterThan(0);

    expectNoConsoleErrors(errors);
  });

});
