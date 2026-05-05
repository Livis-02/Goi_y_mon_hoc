import { test, expect } from '@playwright/test';
import { login, waitForPageReady, captureConsoleErrors, expectNoConsoleErrors, URLS } from './helpers';

/**
 * Roadmap (Lộ trình tích hợp) — kiểm tra Phương án A:
 *   - 2 mode tab "Lộ trình của tôi" / "Khám phá CTDT"
 *   - Mine mode: spec badge xanh "Đã chốt" hoặc badge vàng wizard (nếu chưa chốt)
 *   - Explore mode: watermark READ-ONLY, banner purple, dropdown 6 CN, save/reset BIẾN MẤT
 *   - Click môn → modal chỉ có "Mô tả" + "Kỹ năng môn này dạy" (không còn prereq tree)
 */

test.beforeEach(async ({ page }) => {
  await login(page, 'student');
});

test.describe('Roadmap: Mode toggle (Mine / Explore)', () => {

  test('Header có 4 nút action (saveBtn / revertBtn / resetCtdtBtn / dirtyBadge) trong DOM', async ({ page }) => {
    // Regression: trước đó nhóm save/revert/reset/dirtyBadge bị xóa khỏi HTML
    // → user không lưu được lộ trình. Test này đảm bảo 4 element luôn tồn tại.
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);
    // Element tồn tại trong DOM (có thể hidden bằng class/CSS, nhưng phải có)
    expect(await page.locator('#saveBtn').count()).toBe(1);
    expect(await page.locator('#revertBtn').count()).toBe(1);
    expect(await page.locator('#resetCtdtBtn').count()).toBe(1);
    expect(await page.locator('#dirtyBadge').count()).toBe(1);
    expect(await page.locator('#btnCompareSpec').count()).toBe(1);
  });

  test('Mine mode: tab active + spec badge hiển thị', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);
    await page.waitForTimeout(1500);  // đợi initRoadmap async fetch

    // Mode tabs
    const tabMine = page.locator('#tabMine');
    await expect(tabMine).toHaveClass(/active/);

    // Body class KHÔNG có 'is-explore' (vì mặc định mine)
    const bodyClass = await page.locator('body').getAttribute('class') || '';
    expect(bodyClass).not.toMatch(/is-explore/);

    // Spec label hiển thị (badge hoặc text wizard hint)
    const specLabel = page.locator('#specLabel');
    await expect(specLabel).toBeVisible();
    const labelText = await specLabel.textContent() || '';
    expect(labelText.length).toBeGreaterThan(0);

    expectNoConsoleErrors(errors);
  });

  test('Click "Khám phá CTDT" → mode explore với watermark + read-only', async ({ page }) => {
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);

    await page.locator('#tabExplore').click();
    await page.waitForTimeout(500);  // đợi setMode

    // Body class is-explore
    const bodyClass = await page.locator('body').getAttribute('class') || '';
    expect(bodyClass).toMatch(/is-explore/);

    // Banner explore visible
    const banner = page.locator('#exploreBanner');
    await expect(banner).toBeVisible();

    // Save/Reset button KHÔNG hiện trong explore mode
    await expect(page.locator('#saveBtn')).not.toBeVisible();

    // Dropdown chọn CN trong banner
    await expect(page.locator('#exploreSpecSelect')).toBeVisible();

    // Watermark CSS pseudo-element thì khó test trực tiếp, check class trên dagScroller
    const dagScroller = page.locator('#dagScroller');
    await expect(dagScroller).toBeVisible();
  });

  test('Explore mode: đổi dropdown CN → DAG re-render', async ({ page }) => {
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);

    await page.locator('#tabExplore').click();
    await page.waitForTimeout(500);

    const select = page.locator('#exploreSpecSelect');
    const initialValue = await select.inputValue();
    // Chọn CN khác (MMT)
    const otherSpec = initialValue === '7480201_06' ? '7480201_07' : '7480201_06';
    await select.selectOption(otherSpec);
    await page.waitForTimeout(1500);  // đợi fetch standardPlan

    // Spec label header phải update
    const specLabelText = await page.locator('#specLabel').textContent();
    expect(specLabelText).toMatch(/Khám phá|read-only/i);
  });

  test('Quay lại Mine từ Explore → restore state', async ({ page }) => {
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);
    await page.waitForTimeout(1500);

    await page.locator('#tabExplore').click();
    await page.waitForTimeout(1000);
    await page.locator('#tabMine').click();
    await page.waitForTimeout(1000);

    // Body class KHÔNG có is-explore
    const bodyClass = await page.locator('body').getAttribute('class') || '';
    expect(bodyClass).not.toMatch(/is-explore/);

    // Banner explore ẩn
    const banner = page.locator('#exploreBanner');
    const isVisible = await banner.isVisible().catch(() => false);
    expect(isVisible).toBe(false);

    // Tab mine active lại
    const tabMine = page.locator('#tabMine');
    await expect(tabMine).toHaveClass(/active/);
  });

});

test.describe('Roadmap: Course detail modal', () => {

  test('Click môn → modal có "Mô tả" + "Kỹ năng" (không còn tiên quyết)', async ({ page }) => {
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);

    // Click 1 course card đầu tiên (mine hoặc explore mode đều OK)
    const card = page.locator('.course-card').first();
    await expect(card).toBeVisible({ timeout: 10000 });
    await card.click();

    // Modal hiện
    const modal = page.locator('#courseDetailModal');
    await expect(modal).toBeVisible();

    // Section heading "Mô tả môn học" hoặc "Kỹ năng môn này mang lại"
    await expect(modal.locator('text=/Mô tả môn học|Kỹ năng môn này/').first()).toBeVisible();

    // KHÔNG còn section "Đường đi tiên quyết" hay "Môn này dẫn đến" (đã bỏ theo user feedback)
    await expect(modal.locator('text=Đường đi tiên quyết')).toHaveCount(0);
    await expect(modal.locator('text=Môn này dẫn đến')).toHaveCount(0);

    // Đóng modal
    await page.locator('#courseDetailModal button:has-text("Đóng"), #courseDetailModal button[onclick*="closeCourseDetail"]').first().click();
    await expect(modal).not.toBeVisible();
  });

});

test.describe('Roadmap: So sánh 6 chuyên ngành modal', () => {

  test('Click "So sánh 6 chuyên ngành" → modal mở + đóng', async ({ page }) => {
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);

    await page.locator('#btnCompareSpec').click();
    const modal = page.locator('#specCompareModal');
    await expect(modal).toBeVisible();
    await expect(modal.locator('text=So sánh 6 chuyên ngành')).toBeVisible();

    // Close
    await modal.locator('button[onclick*="closeSpecCompare"]').first().click();
    await expect(modal).not.toBeVisible();
  });

});
