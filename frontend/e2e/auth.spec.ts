import { test, expect, Page } from '@playwright/test'

/**
 * 认证相关测试
 */

test.describe('登录页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('应该显示登录表单', async ({ page }) => {
    await expect(page.locator('input[type="text"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('空表单提交应显示错误', async ({ page }) => {
    await page.click('button[type="submit"]')

    // 应该显示验证错误
    await expect(page.locator('.ant-form-item-explain-error')).toBeVisible()
  })

  test('错误的凭据应显示错误消息', async ({ page }) => {
    await page.fill('input[type="text"]', 'wrong@example.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')

    // 应该显示错误消息
    await expect(page.locator('.ant-message-error')).toBeVisible()
  })

  test('正确登录应跳转到笔记列表', async ({ page }) => {
    // 使用测试账号
    await page.fill('input[type="text"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')

    // 应该跳转到笔记列表
    await page.waitForURL('**/notes')
    expect(page.url()).toContain('/notes')
  })

  test('登录超时后应跳转回原页面', async ({ page }) => {
    // 先登录
    await page.fill('input[type="text"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')
    await page.waitForURL('**/notes')

    // 清除 token 模拟超时
    await page.evaluate(() => {
      localStorage.removeItem('token')
    })

    // 访问需要认证的页面
    await page.goto('/notes/some-id')

    // 应该跳转到登录页并带有 redirect 参数
    await page.waitForURL('**/login**')
    expect(page.url()).toContain('redirect=')
  })
})

test.describe('注册页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register')
  })

  test('应该显示注册表单', async ({ page }) => {
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible()
    await expect(page.locator('input[type="text"]').first()).toBeVisible()
    await expect(page.locator('input[type="password"]').first()).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('密码不匹配应显示错误', async ({ page }) => {
    await page.fill('input[placeholder*="用户名"]', 'testuser')
    await page.fill('input[type="text"]', 'new@example.com')
    await page.fill('input[type="password"]').first().fill('password123')
    await page.locator('input[type="password"]').last().fill('password456')
    await page.click('button[type="submit"]')

    // 应该显示密码不匹配错误
    await expect(page.locator('.ant-form-item-explain-error')).toBeVisible()
  })
})

test.describe('登出', () => {
  test('登出应清除 token 并跳转到登录页', async ({ page }) => {
    // 先登录
    await page.goto('/login')
    await page.fill('input[type="text"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')
    await page.waitForURL('**/notes')

    // 验证已登录
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).not.toBeNull()

    // 点击登出（假设有一个登出按钮）
    await page.click('[data-testid="logout-button"]')

    // 应该跳转到登录页
    await page.waitForURL('**/login')

    // token 应该被清除
    const tokenAfter = await page.evaluate(() => localStorage.getItem('token'))
    expect(tokenAfter).toBeNull()
  })
})
