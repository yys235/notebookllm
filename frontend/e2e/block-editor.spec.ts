import { test, expect, Page } from '@playwright/test'

/**
 * 块编辑器 E2E 测试
 * 测试多行文本编辑、光标位置、块操作等
 */

// 辅助函数：登录
async function login(page: Page) {
  await page.goto('/login')
  await page.fill('input[type="text"]', 'test@example.com')
  await page.fill('input[type="password"]', 'password123')
  await page.click('button[type="submit"]')
  await page.waitForURL('**/notes')
}

// 辅助函数：创建新笔记
async function createNote(page: Page, type: string = 'feishu-docs') {
  await page.goto(`/notes/new?type=${type}`)
  await page.waitForSelector('.feishu-docs-editor')
}

// 辅助函数：获取第一个块
async function getFirstBlock(page: Page) {
  return page.locator('[data-block-id] .block-content').first()
}

// 辅助函数：获取所有块
async function getAllBlocks(page: Page) {
  return page.locator('[data-block-id] .block-content')
}

// 辅助函数：聚焦块并输入
async function typeInBlock(page: Page, index: number, text: string) {
  const blocks = await getAllBlocks(page)
  const block = blocks.nth(index)
  await block.click()
  await block.type(text, { delay: 50 })
}

test.describe('块编辑器 - 基础操作', () => {
  test.beforeEach(async ({ page }) => {
    // 可以选择登录或跳过认证
    // await login(page)
    await createNote(page)
  })

  test('应该显示空块', async ({ page }) => {
    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(1)
  })

  test('输入文本应该更新块内容', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('Hello World')

    await expect(block).toContainText('Hello World')
  })

  test('按 Enter 应该创建新块', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一行')
    await page.keyboard.press('Enter')

    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(2)
  })

  test('在块末尾按 Enter 应该分割内容', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一行第二行')

    // 移动到中间位置
    await page.keyboard.press('Home')
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press('ArrowRight')
    }

    await page.keyboard.press('Enter')

    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(2)
    await expect(blocks.nth(0)).toContainText('第一行')
    await expect(blocks.nth(1)).toContainText('第二行')
  })
})

test.describe('块编辑器 - 多行文本', () => {
  test.beforeEach(async ({ page }) => {
    await createNote(page)
  })

  test('Shift+Enter 应该插入换行而不是新块', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一行')
    await page.keyboard.press('Shift+Enter')
    await page.type('.block-content', '第二行')

    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(1)
    await expect(block).toContainText('第一行')
    await expect(block).toContainText('第二行')
  })

  test('多行文本块按退格合并', async ({ page }) => {
    // 创建两个块
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一块')
    await page.keyboard.press('Enter')
    await page.type('.block-content', '第二块')

    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(2)

    // 在第二个块开头按退格
    await page.keyboard.press('Home')
    await page.keyboard.press('Backspace')

    // 应该合并成一个块
    await expect(blocks).toHaveCount(1)
    await expect(blocks.first()).toContainText('第一块第二块')
  })

  test('在多行文本中间按 Enter 分割', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一行')

    // 使用 Shift+Enter 创建多行
    await page.keyboard.press('Shift+Enter')
    await page.type('.block-content', '第二行')
    await page.keyboard.press('Shift+Enter')
    await page.type('.block-content', '第三行')

    // 现在块内有3行
    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(1)

    // 移动到第二行开头并按 Enter
    await page.keyboard.press('Home')
    await page.keyboard.press('ArrowUp')

    await page.keyboard.press('Enter')

    // 应该分割成两个块
    await expect(blocks).toHaveCount(2)
  })
})

test.describe('块编辑器 - 光标位置', () => {
  test.beforeEach(async ({ page }) => {
    await createNote(page)
  })

  test('在块开头按退格应合并到上一块', async ({ page }) => {
    // 创建两个块
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一块内容')
    await page.keyboard.press('Enter')
    await page.type('.block-content', '第二块内容')

    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(2)

    // 移动到第二块开头
    await page.keyboard.press('Home')

    // 按退格合并
    await page.keyboard.press('Backspace')

    await expect(blocks).toHaveCount(1)
    await expect(blocks.first()).toContainText('第一块内容第二块内容')
  })

  test('空块按退格应删除块', async ({ page }) => {
    // 创建两个块，第二个为空
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('内容')
    await page.keyboard.press('Enter')

    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(2)

    // 在空块按退格
    await page.keyboard.press('Backspace')

    await expect(blocks).toHaveCount(1)
  })

  test('唯一空块按退格不应删除', async ({ page }) => {
    const blocks = await getAllBlocks(page)
    await expect(blocks).toHaveCount(1)

    // 在唯一的空块按退格
    const block = await getFirstBlock(page)
    await block.click()
    await page.keyboard.press('Backspace')

    // 块应该仍然存在
    await expect(blocks).toHaveCount(1)
  })
})

test.describe('块编辑器 - 斜杠命令', () => {
  test.beforeEach(async ({ page }) => {
    await createNote(page)
  })

  test('在块开头输入 / 应弹出命令菜单', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('/')

    // 应该显示斜杠菜单
    const slashMenu = page.locator('.slash-menu')
    await expect(slashMenu).toBeVisible()
  })

  test('在文本后输入 / 不应弹出菜单', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('https://example.com/')

    // 不应该显示斜杠菜单
    const slashMenu = page.locator('.slash-menu')
    await expect(slashMenu).not.toBeVisible()
  })

  test('URL 中的 / 不应触发菜单', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('http://10.104.200.115:8080/notes')

    // 不应该显示斜杠菜单
    const slashMenu = page.locator('.slash-menu')
    await expect(slashMenu).not.toBeVisible()
  })

  test('按 Escape 应关闭菜单', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('/')

    const slashMenu = page.locator('.slash-menu')
    await expect(slashMenu).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(slashMenu).not.toBeVisible()
  })
})

test.describe('块编辑器 - 键盘导航', () => {
  test.beforeEach(async ({ page }) => {
    await createNote(page)
  })

  test('上箭头应移动到上一块', async ({ page }) => {
    // 创建两个块
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一块')
    await page.keyboard.press('Enter')
    await page.type('.block-content', '第二块')

    // 在第二块开头按上箭头
    await page.keyboard.press('ArrowUp')

    // 光标应该在第一块
    const blocks = await getAllBlocks(page)
    await expect(blocks.first()).toBeFocused()
  })

  test('下箭头应移动到下一块', async ({ page }) => {
    // 创建两个块
    const block = await getFirstBlock(page)
    await block.click()
    await block.type('第一块')
    await page.keyboard.press('Enter')
    await page.type('.block-content', '第二块')

    // 移动到第一块末尾
    await page.keyboard.press('ArrowUp')
    await page.keyboard.press('End')

    // 按下箭头
    await page.keyboard.press('ArrowDown')

    // 光标应该在第二块
    const blocks = await getAllBlocks(page)
    await expect(blocks.nth(1)).toBeFocused()
  })
})

test.describe('块编辑器 - 特殊场景', () => {
  test('连续快速输入不应丢失内容', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()

    // 快速输入
    const text = '这是一段测试文本用于验证快速输入场景'
    await block.type(text, { delay: 0 })

    await expect(block).toContainText(text)
  })

  test('粘贴多行文本应正确处理', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()

    // 模拟粘贴
    const multiLineText = '第一行\n第二行\n第三行'
    await page.evaluate((text) => {
      navigator.clipboard.writeText(text)
    }, multiLineText)

    await page.keyboard.press('Control+v')

    // 验证内容
    const content = await block.textContent()
    expect(content).toContain('第一行')
  })

  test('输入中文应正确处理', async ({ page }) => {
    const block = await getFirstBlock(page)
    await block.click()

    // 输入中文（使用 type 模拟）
    await block.type('中文测试')

    await expect(block).toContainText('中文测试')
  })
})
