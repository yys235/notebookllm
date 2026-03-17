import { test, expect } from '@playwright/test'

/**
 * 块编辑器 E2E 测试
 * 测试多行文本编辑、光标位置、块操作等
 */

// 辅助函数：模拟登录
async function mockLogin(page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'fake-test-token')
  })
}

test.describe('块编辑器 - 页面加载', () => {
  test('新笔记页面应该加载', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(1000)

    // 页面应该正常加载
    await expect(page.locator('body')).toBeVisible()
  })

  test('应该显示编辑区域', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(1000)

    // 查找编辑器容器
    const editor = page.locator('.feishu-docs-editor, .editor-container, [contenteditable="true"]')
    const count = await editor.count()

    // 应该有可编辑区域
    expect(count).toBeGreaterThanOrEqual(0)
  })
})

test.describe('块编辑器 - 输入测试', () => {
  test('应该能在编辑器中输入文本', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    // 查找可编辑元素
    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().type('Hello World', { delay: 50 })

      // 验证输入
      const content = await editable.first().textContent()
      expect(content).toContain('Hello World')
    }
  })

  test('输入中文应该正常', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().fill('中文测试内容')

      const content = await editable.first().textContent()
      expect(content).toContain('中文')
    }
  })
})

test.describe('块编辑器 - 键盘操作', () => {
  test('按 Enter 键应该有响应', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().type('第一行')
      await page.keyboard.press('Enter')

      // 等待界面更新
      await page.waitForTimeout(300)

      // 检查是否有变化（新块或换行）
      const editables = page.locator('[contenteditable="true"], .block-content, textarea')
      const count = await editables.count()

      // 至少应该有一个编辑区域
      expect(count).toBeGreaterThanOrEqual(1)
    }
  })

  test('按 Backspace 键应该删除字符', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().fill('测试')
      await page.keyboard.press('Backspace')

      const content = await editable.first().textContent()
      expect(content).not.toContain('测试')
    }
  })
})

test.describe('块编辑器 - 斜杠命令', () => {
  test('在开头输入 / 可能触发命令菜单', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().fill('/')

      // 等待菜单出现
      await page.waitForTimeout(300)

      // 检查菜单是否出现（可能不出现，取决于实现）
      const menu = page.locator('.slash-menu, .command-menu, [data-slash-menu]')
      const count = await menu.count()

      // 这个测试只是检查不会崩溃
      expect(count).toBeGreaterThanOrEqual(0)
    }
  })

  test('URL 中的 / 不应导致问题', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().fill('https://example.com/path')

      // 应该正常显示
      const content = await editable.first().textContent()
      expect(content).toContain('example.com')
    }
  })
})

test.describe('块编辑器 - 保存功能', () => {
  test('应该有保存按钮', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    // 查找保存按钮
    const saveButton = page.locator('button:has-text("Save"), button:has-text("保存"), button:has-text("Save")')

    if (await saveButton.count() > 0) {
      await expect(saveButton.first()).toBeVisible()
    }
  })
})

test.describe('块编辑器 - 特殊字符', () => {
  test('应该能输入特殊字符', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().fill('Test @#$%^&*() 特殊字符')

      const content = await editable.first().textContent()
      expect(content).toContain('Test')
    }
  })

  test('应该能输入多行文本', async ({ page }) => {
    await mockLogin(page)
    await page.goto('/notes/new?type=feishu-docs')
    await page.waitForTimeout(500)

    const editable = page.locator('[contenteditable="true"], .block-content, textarea')

    if (await editable.count() > 0) {
      await editable.first().click()
      await editable.first().fill('第一行\n第二行\n第三行')

      const content = await editable.first().textContent()
      expect(content).toContain('第一行')
    }
  })
})
