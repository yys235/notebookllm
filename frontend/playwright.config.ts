import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  // 测试目录
  testDir: './e2e',

  // 完全并行运行测试
  fullyParallel: true,

  // CI 上失败时禁止 test.only
  forbidOnly: !!process.env.CI,

  // CI 上重试失败测试
  retries: process.env.CI ? 2 : 0,

  // CI 上限制并行 workers
  workers: process.env.CI ? 1 : undefined,

  // Reporter 配置
  reporter: [
    ['html', { open: 'never' }],
    ['list']
  ],

  // 全局测试配置
  use: {
    // 基础 URL
    baseURL: 'http://localhost:5173',

    // 收集失败测试的 trace
    trace: 'on-first-retry',

    // 截图
    screenshot: 'only-on-failure',

    // 视频
    video: 'retain-on-failure',
  },

  // 配置项目（浏览器）
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 移动端测试（可选）
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
  ],

  // 启动开发服务器
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
