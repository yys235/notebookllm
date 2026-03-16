import { test, expect } from '@playwright/test'

/**
 * 笔记列表测试
 */

test.describe('笔记列表页面', () => {
  test('未登录应跳转到登录页', async ({ page }) => {
    await page.goto('/notes')
    await page.waitForURL('**/login**')
    expect(page.url()).toContain('/login')
  })

  test('登录后应显示笔记列表', async ({ page }) => {
    // 模拟登录状态
    await page.addInitScript(() => {
      localStorage.setItem('token', 'fake-test-token')
    })

    await page.goto('/notes')

    // 应该显示笔记列表容器
    await expect(page.locator('.notes-page')).toBeVisible()
  })

  test('点击新建按钮应跳转到新笔记页面', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'fake-test-token')
    })

    await page.goto('/notes')

    // 点击新建按钮
    await page.click('button:has-text("新建")')

    // 应该显示编辑器类型选择
    await expect(page.locator('.editor-type-selector')).toBeVisible()
  })

  test('选择编辑器类型应创建对应类型的笔记', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'fake-test-token')
    })

    await page.goto('/notes')
    await page.click('button:has-text("新建")')

    // 选择飞书文档
    await page.click('[data-editor-type="feishu-docs"]')

    // 应该跳转到新笔记页面
    await page.waitForURL('**/notes/new**')
    expect(page.url()).toContain('type=feishu-docs')
  })
})

test.describe('笔记搜索', () => {
  test('搜索应过滤笔记列表', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'fake-test-token')
    })

    await page.goto('/notes')

    // 输入搜索关键词
    const searchInput = page.locator('input[placeholder*="搜索"]')
    if (await searchInput.isVisible()) {
      await searchInput.fill('测试关键词')
      // 等待搜索结果更新
      await page.waitForTimeout(500)

      // 验证搜索结果
      const notes = page.locator('.note-card')
      const count = await notes.count()

      for (let i = 0; i < count; i++) {
        const text = await notes.nth(i).textContent()
        expect(text?.toLowerCase()).toContain('测试关键词')
      }
    }
  })
})

test.describe('笔记操作', () => {
  test('删除笔记应从列表中移除', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'fake-test-token')
    })

    await page.goto('/notes')

    // 获取删除前的笔记数量
    const notesBefore = await page.locator('.note-card').count()

    if (notesBefore > 0) {
      // 点击第一个笔记的删除按钮
      await page.locator('.note-card').first().hover()
      await page.locator('.note-card .delete-button').first().click()

      // 确认删除
      await page.click('.ant-modal-confirm-btns .ant-btn-dangerous')

      // 等待删除完成
      await page.waitForTimeout(500)

      // 验证笔记数量减少
      const notesAfter = await page.locator('.note-card').count()
      expect(notesAfter).toBe(notesBefore - 1)
    }
  })

  test('置顶笔记应移动到顶部', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'fake-test-token')
    })

    await page.goto('/notes')

    // 悬停并点击置顶
    await page.locator('.note-card').last().hover()
    await page.locator('.note-card .pin-button').last().click()

    // 等待更新
    await page.waitForTimeout(500)

    // 验证该笔记移动到了顶部
    const firstNote = page.locator('.note-card').first()
    await expect(firstNote).toHaveClass(/pinned/)
  })
})
