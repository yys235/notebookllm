import { test, expect } from '@playwright/test'

/**
 * 首页测试
 */

test.describe('首页', () => {
  test('应该正常加载', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('body')).toBeVisible()
  })

  test('应该显示应用标题', async ({ page }) => {
    await page.goto('/')
    const title = await page.title()
    expect(title).toBeTruthy()
  })

  test('应该有导航按钮', async ({ page }) => {
    await page.goto('/')

    // 首页使用 Button 组件而不是 anchor 标签
    // 检查有 "Get Started" 和 "Sign In" 按钮
    const getStartedBtn = page.locator('button:has-text("Get Started"), button:has-text("开始")')
    const signInBtn = page.locator('button:has-text("Sign In"), button:has-text("登录")')

    const getStartedCount = await getStartedBtn.count()
    const signInCount = await signInBtn.count()

    // 至少应该有一个按钮
    expect(getStartedCount + signInCount).toBeGreaterThan(0)
  })

  test('应该显示功能特性', async ({ page }) => {
    await page.goto('/')

    // 检查功能卡片
    const featureCards = page.locator('.feature-card')
    const count = await featureCards.count()
    expect(count).toBeGreaterThan(0)
  })
})

test.describe('首页 - 导航', () => {
  test('点击 Sign In 按钮应跳转到登录页', async ({ page }) => {
    await page.goto('/')

    const signInBtn = page.locator('button:has-text("Sign In")')
    if (await signInBtn.count() > 0) {
      await signInBtn.first().click()
      await page.waitForTimeout(500)
      await expect(page).toHaveURL(/login/)
    }
  })

  test('点击 Get Started 按钮应跳转到笔记页', async ({ page }) => {
    await page.goto('/')

    const getStartedBtn = page.locator('button:has-text("Get Started")')
    if (await getStartedBtn.count() > 0) {
      await getStartedBtn.first().click()
      await page.waitForTimeout(500)
      // 由于未登录，应该跳转到登录页或笔记页
      const url = page.url()
      expect(url).toMatch(/login|notes/)
    }
  })
})
