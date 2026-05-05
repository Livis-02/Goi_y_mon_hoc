import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config — EduGuide E2E.
 *
 * Assumptions (run before `npx playwright test`):
 *   1. Backend lên port 8000:  uvicorn backend.main:app --reload --port 8000
 *   2. Frontend serve port 5500: live-server frontend/pages  hoặc  python -m http.server 5500 --directory frontend/pages
 *   3. DB đã seed (test accounts trong data/demo/seed_passwords.txt + admin demo_admin/Demo@2025)
 *
 * Test accounts:
 *   - SV  : sv14001 / 220238
 *   - GV  : KHMT001 / 714526
 *   - Admin: demo_admin / Demo@2025
 *
 * Lưu ý: test giả định first-login đã hoàn tất cho sv14001. Nếu chưa, login flow sẽ
 * bị chặn ở màn "Đổi mật khẩu lần đầu". Reset DB hoặc dùng SV khác đã first-login.
 */
export default defineConfig({
  testDir: './tests/e2e',
  // Run files sequentially để tránh conflict state DB (login + drag-drop save chung user)
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },

  // Reporter: HTML cho dev, dot cho CI
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],

  use: {
    baseURL: 'http://127.0.0.1:5500',
    actionTimeout: 8_000,
    navigationTimeout: 15_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1440, height: 900 },
    locale: 'vi-VN',
    timezoneId: 'Asia/Ho_Chi_Minh',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Output dir
  outputDir: 'test-results',
});
