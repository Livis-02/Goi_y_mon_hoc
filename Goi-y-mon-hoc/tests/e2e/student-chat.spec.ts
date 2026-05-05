import { test, expect } from '@playwright/test';
import { login, waitForPageReady, captureConsoleErrors, expectNoConsoleErrors, URLS } from './helpers';

/**
 * AI Chat (ai-chat.html) + Messaging (messaging.html) — iOS Messages style.
 * Kiểm tra:
 *   - FAB chat KHÔNG hiện trên 2 page chat (vì user đã ở context chat)
 *   - FAB hiện trên home / grades (page khác)
 *   - Empty state hero + chips
 *   - Input bar luôn visible
 */

test.beforeEach(async ({ page }) => {
  await login(page, 'student');
});

test.describe('FAB chat visibility', () => {

  test('FAB hiện trên home.html', async ({ page }) => {
    await page.goto(URLS.home);
    await waitForPageReady(page);
    const fab = page.locator('#fcFab');
    await expect(fab).toBeVisible({ timeout: 5000 });
  });

  test('FAB ẨN trên ai-chat.html', async ({ page }) => {
    await page.goto(URLS.ai);
    await waitForPageReady(page);
    await page.waitForTimeout(800);  // đợi page:ready event toggle visibility
    const fab = page.locator('#fcFab');
    // Có thể element tồn tại nhưng display:none — check both not.toBeVisible
    const visible = await fab.isVisible().catch(() => false);
    expect(visible).toBe(false);
  });

  test('FAB ẨN trên messaging.html', async ({ page }) => {
    await page.goto(URLS.msg);
    await waitForPageReady(page);
    await page.waitForTimeout(800);
    const fab = page.locator('#fcFab');
    const visible = await fab.isVisible().catch(() => false);
    expect(visible).toBe(false);
  });

  test('FAB hiện lại khi navigate từ ai-chat về home', async ({ page }) => {
    await page.goto(URLS.ai);
    await waitForPageReady(page);
    await page.goto(URLS.home);
    await waitForPageReady(page);
    const fab = page.locator('#fcFab');
    await expect(fab).toBeVisible({ timeout: 5000 });
  });

});

test.describe('AI Chat: empty state + input bar', () => {

  test('Empty state hero + 4 chips + input luôn visible', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.goto(URLS.ai);
    await waitForPageReady(page);

    // Hero placeholder
    const hero = page.locator('#emptyHero');
    const hasHero = await hero.isVisible().catch(() => false);
    if (hasHero) {
      // Hero hiện khi chưa có thread → check 4 chips
      await expect(page.locator('.imsg-chip')).toHaveCount(4);
    }

    // Input bar luôn visible (đặc biệt sau redesign)
    const input = page.locator('#chatInput');
    await expect(input).toBeVisible();

    // Send button
    const sendBtn = page.locator('#sendBtn');
    await expect(sendBtn).toBeVisible();

    // Header: "AI Tư vấn EduGuide" + status dot
    await expect(page.locator('#chatThreadTitle')).toBeVisible();

    expectNoConsoleErrors(errors);
  });

  test('Click chip → fill input (KHÔNG auto-send)', async ({ page }) => {
    await page.goto(URLS.ai);
    await waitForPageReady(page);

    const chip = page.locator('.imsg-chip').first();
    const isHeroVisible = await page.locator('#emptyHero').isVisible().catch(() => false);
    if (!isHeroVisible) {
      test.skip(true, 'Hero không hiện (đã có thread cũ) — skip chip test');
      return;
    }
    const chipText = await chip.textContent();
    await chip.click();

    // Input có value chip text (loại bỏ emoji prefix)
    const input = page.locator('#chatInput');
    const inputValue = await input.inputValue();
    expect(inputValue.length).toBeGreaterThan(5);

    // Focus on input (chứng tỏ chip không send mà chỉ fill)
    await expect(input).toBeFocused();
  });

  test('Tạo thread mới: click "+ Mới" → DAG hiện hint, header đổi', async ({ page }) => {
    await page.goto(URLS.ai);
    await waitForPageReady(page);

    // Tìm button "+ Mới" hoặc icon edit_square
    const newBtn = page.locator('button[onclick*="createNewThread"]').first();
    if (!(await newBtn.isVisible().catch(() => false))) {
      test.skip(true, 'Không tìm thấy nút tạo thread mới');
      return;
    }
    await newBtn.click();
    await page.waitForTimeout(500);

    // Header thread title đổi
    const titleText = await page.locator('#chatThreadTitle').textContent();
    expect(titleText).toMatch(/mới|chat/i);
  });

});

test.describe('Messaging: empty state + modals', () => {

  test('Empty state hero + input disabled', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.goto(URLS.msg);
    await waitForPageReady(page);

    // Hero hiện
    const hero = page.locator('#emptyConvHero');
    const heroVisible = await hero.isVisible().catch(() => false);
    if (heroVisible) {
      await expect(page.locator('text=/Hỏi cố vấn học tập|Trao đổi 1-1/i').first()).toBeVisible();
    }

    // Input disabled khi chưa chọn conv
    const input = page.locator('#msgInput');
    await expect(input).toHaveAttribute('disabled', /^(disabled|true|)$/);

    expectNoConsoleErrors(errors);
  });

  test('Modal "+ Mới" hiển thị', async ({ page }) => {
    await page.goto(URLS.msg);
    await waitForPageReady(page);

    await page.locator('button[onclick*="openAddUserModal"]').first().click();
    const modal = page.locator('#addUserModal');
    await expect(modal).toBeVisible();
    // imsg-modal-card layout mới
    await expect(modal.locator('.imsg-modal-card')).toBeVisible();
    await expect(modal.locator('.imsg-search-input')).toBeVisible();

    // Close
    await modal.locator('.imsg-modal-close').click();
    await expect(modal).not.toBeVisible();
  });

  test('Modal "Nhóm" hiển thị', async ({ page }) => {
    await page.goto(URLS.msg);
    await waitForPageReady(page);

    await page.locator('button[onclick*="openCreateGroupModal"]').first().click();
    const modal = page.locator('#createGroupModal');
    // Modal có thể bị block nếu user chưa có connections (defensive check trong code)
    const isVisible = await modal.isVisible().catch(() => false);
    if (!isVisible) {
      // Kiểm tra có toast warning "chưa có kết nối"
      await expect(page.locator('text=/chưa có kết nối/i').first()).toBeVisible({ timeout: 3000 });
      return;
    }
    await expect(modal.locator('#groupNameInput')).toBeVisible();
    await modal.locator('.imsg-modal-close').click();
  });

});
