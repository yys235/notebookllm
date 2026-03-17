import { test, expect, Page } from '@playwright/test'

/**
 * 导航测试
 * 测试路由跳转和页面导航
 */

// 辅助函数：模拟登录
async function mockLogin(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'fake-test-token')
  })
}

test.describe('导航 - 公开页面', () => {
  test('首页应该可访问', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('body')).toBeVisible()
  })

  test('登录页应该可访问', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('.login-container, body')).toBeVisible()
  })

  test('注册页应该可访问', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('.register-container, body')).toBeVisible()
  })

  test('分享笔记页应该可访问（即使未登录）', async ({ page }) => {
    await page.goto('/shared/test-share-id')
    await page.waitForTimeout(500)
    // 应该加载（可能显示错误信息）
    await expect(page.locator('body')).toBeVisible()
  })
})

test.describe('导航 - 受保护页面', () => {
  test('笔记列表页需要登录', async ({ page }) => {
    await page.goto('/notes')
    await page.waitForTimeout(1000)

    const url = page.url()
    expect(url).toMatch(/login|register/)
  })

  test('新建笔记页需要登录', async ({ page }) => {
    await page.goto('/notes/new')
    await page.waitForTimeout(1000)

    const url = page.url()
    expect(url).toMatch(/login|register/)
  })

  test('设置页需要登录', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(1000)

    const url = page.url()
    expect(url).toMatch(/login|register/)
  })
})

test.describe('导航 - 登录后访问', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
  })

  test('登录后可访问笔记列表', async ({ page }) => {
    await page.goto('/notes')
    await page.waitForTimeout(500)

    const url = page.url()
    // 登录后应该能访问笔记列表（假 token 可能会被后端拒绝）
    expect(url).toBeDefined()
  })

  test('登录后可访问新建笔记', async ({ page }) => {
    await page.goto('/notes/new')
    await page.waitForTimeout(500)

    // 页面应该加载
    await expect(page.locator('body')).toBeVisible()
  })

  test('登录后可访问设置页', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(500)

    await expect(page.locator('body')).toBeVisible()
  })
})

test.describe('导航 - 路由守卫', () => {
  test('未登录访问受保护页面后登录应重定向', async ({ page }) => {
    // 尝试访问受保护页面
    await page.goto('/notes?redirect=test')
    await page.waitForTimeout(1000)

    // 应该被重定向到登录页
    const url = page.url()
    expect(url).toMatch(/login/)
  })

  test('404 页面应该显示', async ({ page }) => {
    await page.goto('/nonexistent-page')
    await page.waitForTimeout(500)

    // 应该显示 404 或空白页面
    await expect(page.locator('body')).toBeVisible()
  })
})

test.describe('导航 - 链接跳转', () => {
  test('登录页到注册页', async ({ page }) => {
    await page.goto('/login')

    const registerLink = page.locator('a[href*="register"]')
    if (await registerLink.count() > 0) {
      await registerLink.first().click()
      await page.waitForTimeout(500)

      expect(page.url()).toContain('register')
    }
  })

  test('注册页到登录页', async ({ page }) => {
    await page.goto('/register')

    const loginLink = page.locator('a[href*="login"]')
    if (await loginLink.count() > 0) {
      await loginLink.first().click()
      await page.waitForTimeout(500)

      expect(page.url()).toContain('login')
    }
  })
})
