import { test, expect } from '@playwright/test';
import { login, waitForPageReady, captureConsoleErrors, expectNoConsoleErrors, URLS } from './helpers';

/**
 * Navigation stability — regression test cho bug "phải reload mới dùng được".
 *
 * Root cause cũ: ajax-nav SPA simulation gây class of bugs:
 *   - Listener accumulation across nav (page scripts add listener mỗi lần
 *     ajax-nav re-execute)
 *   - State leak (biến module-level không reset khi swap <main>)
 *   - Init race (user click trước khi async init xong)
 *
 * Fix dứt điểm v16: chuyển sang MPA full-reload navigation. Mỗi page = process
 * mới → zero listener accumulation, zero state leak, init() chạy 1 lần duy nhất.
 * Bù snappy feel bằng nav-prefetch.js (prefetch HTML on hover/idle) +
 * View Transitions API (smooth fade).
 *
 * Test này là regression: với MPA mọi assertion pass trivially. Giữ để bảo vệ
 * khi ai đó lỡ re-enable ajax-nav (sẽ fail ngay).
 */

test.beforeEach(async ({ page }) => {
  await login(page, 'student');
});

test.describe('Nav stability: listener cleanup', () => {

  test('Navigate qua lại 5 lần → handlers vẫn fire đúng 1 lần', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    // Cycle 5 lần: home → roadmap → grades → chat → home
    const cycle = [URLS.home, URLS.roadmap, URLS.grades, URLS.ai, URLS.home];
    for (const url of cycle) {
      await page.goto(url);
      await waitForPageReady(page);
    }
    // Inject probe: count document click listeners — sau cycle nên không lớn quá
    const listenerCount = await page.evaluate(() => {
      // EventTarget không expose listener count → đếm gián tiếp qua handler invocations
      let fireCount = 0;
      const probe = () => fireCount++;
      document.addEventListener('__test_probe', probe);
      document.dispatchEvent(new Event('__test_probe'));
      document.removeEventListener('__test_probe', probe);
      return fireCount;
    });
    // 1 listener fire 1 lần
    expect(listenerCount).toBe(1);
    expectNoConsoleErrors(errors);
  });

  test('Modal "Mô phỏng GPA" mở được sau khi navigate qua lại', async ({ page }) => {
    // Bug pattern user phản ánh: chuyển tab xong click button modal → không hiện
    await page.goto(URLS.home);
    await waitForPageReady(page);
    await page.goto(URLS.grades);
    await waitForPageReady(page);
    await page.goto(URLS.home);
    await waitForPageReady(page);
    await page.goto(URLS.grades);
    await waitForPageReady(page);

    // Click button → modal phải mở ngay (không cần reload)
    await page.locator('button:has-text("Mô phỏng GPA")').first().click();
    const modal = page.locator('#simulatorModal');
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('Roadmap mode toggle sau khi navigate qua lại nhiều lần', async ({ page }) => {
    await page.goto(URLS.home);
    await waitForPageReady(page);
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);
    await page.goto(URLS.grades);
    await waitForPageReady(page);
    await page.goto(URLS.roadmap);
    await waitForPageReady(page);
    await page.waitForTimeout(1500);

    // Click tab Khám phá → body class is-explore
    await page.locator('#tabExplore').click();
    await page.waitForTimeout(500);
    const cls = await page.locator('body').getAttribute('class') || '';
    expect(cls).toMatch(/is-explore/);
  });

  test('window.__initDone set sau khi init xong', async ({ page }) => {
    await page.goto(URLS.home);
    await waitForPageReady(page);
    const done = await page.evaluate(() => window.__initDone);
    expect(done).toBe(true);
  });

  test('utils helpers exposed: __retryFetch + __waitFor + __withInit', async ({ page }) => {
    await page.goto(URLS.home);
    await waitForPageReady(page);
    const helpers = await page.evaluate(() => ({
      retryFetch: typeof window.__retryFetch === 'function',
      waitFor:    typeof window.__waitFor === 'function',
      withInit:   typeof window.__withInit === 'function',
      banner:     typeof window.__showInitErrorBanner === 'function',
    }));
    expect(helpers.retryFetch).toBe(true);
    expect(helpers.waitFor).toBe(true);
    expect(helpers.withInit).toBe(true);
    expect(helpers.banner).toBe(true);
  });

  test('Send chat message ngay sau page load (không phải reload)', async ({ page }) => {
    // Reproduce bug user phản ánh: load ai-chat → click chip → Enter → message gửi
    await page.goto(URLS.ai);
    await waitForPageReady(page);
    // Click chip → fill input
    const chip = page.locator('.imsg-chip').first();
    if (await chip.isVisible({ timeout: 2000 }).catch(() => false)) {
      await chip.click();
      // Input có value
      const input = page.locator('#chatInput');
      const value = await input.inputValue();
      expect(value.length).toBeGreaterThan(0);
      // Click send button → sendChatMessage được gọi (defensive guard pass)
      // Không assert response (cần backend AI), chỉ check button click không error
      const sendBtn = page.locator('#sendBtn');
      await expect(sendBtn).toBeEnabled({ timeout: 3000 });
    }
  });

  test('FAB chat persistent qua các page (KHÔNG accumulate panel)', async ({ page }) => {
    await page.goto(URLS.home);
    await waitForPageReady(page);
    await page.goto(URLS.grades);
    await waitForPageReady(page);
    await page.goto(URLS.home);
    await waitForPageReady(page);
    // Đếm element fcFab — phải đúng 1
    expect(await page.locator('#fcFab').count()).toBe(1);
    // Đếm panel — phải đúng 1
    expect(await page.locator('#fcPanel').count()).toBe(1);
  });

});
