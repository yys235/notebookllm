import { Page } from '@playwright/test'

/**
 * 测试辅助函数
 */

// 测试用户凭据
export const TEST_USER = {
  email: 'test@example.com',
  password: 'password123',
}

// 登录辅助函数
export async function login(page: Page, email = TEST_USER.email, password = TEST_USER.password) {
  await page.goto('/login')
  await page.fill('input[type="text"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/notes')
}

// 设置认证 token
export async function setAuthToken(page: Page, token = 'fake-test-token') {
  await page.addInitScript((t) => {
    localStorage.setItem('token', t)
  }, token)
}

// 创建新笔记
export async function createNote(page: Page, type: string = 'feishu-docs') {
  await page.goto(`/notes/new?type=${type}`)
  await page.waitForSelector('.feishu-docs-editor, .editor-container')
}

// 获取块元素
export async function getBlock(page: Page, index: number = 0) {
  return page.locator('[data-block-id] .block-content').nth(index)
}

// 获取所有块
export async function getAllBlocks(page: Page) {
  return page.locator('[data-block-id] .block-content')
}

// 在块中输入文本
export async function typeInBlock(page: Page, index: number, text: string) {
  const block = await getBlock(page, index)
  await block.click()
  await block.type(text, { delay: 50 })
}

// 按 Enter 创建新块
export async function pressEnter(page: Page) {
  await page.keyboard.press('Enter')
}

// 按退格删除
export async function pressBackspace(page: Page) {
  await page.keyboard.press('Backspace')
}

// 等待块数量
export async function waitForBlockCount(page: Page, count: number) {
  const blocks = await getAllBlocks(page)
  await blocks.waitFor({ state: 'visible' })
  // 等待块数量达到预期
  await page.waitForFunction(
    ({ expected }) => {
      const blocks = document.querySelectorAll('[data-block-id] .block-content')
      return blocks.length === expected
    },
    { expected: count }
  )
}

// 获取光标位置
export async function getCursorPosition(page: Page): Promise<number> {
  return await page.evaluate(() => {
    const selection = window.getSelection()
    if (!selection || selection.rangeCount === 0) return 0

    const range = selection.getRangeAt(0)
    const element = range.startContainer.parentElement
    if (!element) return 0

    const preCaretRange = range.cloneRange()
    preCaretRange.selectNodeContents(element)
    preCaretRange.setEnd(range.startContainer, range.startOffset)
    return preCaretRange.toString().length
  })
}

// 设置光标位置
export async function setCursorPosition(page: Page, offset: number) {
  await page.evaluate((pos) => {
    const selection = window.getSelection()
    if (!selection) return

    const activeElement = document.activeElement
    if (!activeElement) return

    // 获取所有文本节点
    const textNodes: Text[] = []
    function traverse(node: Node) {
      if (node.nodeType === Node.TEXT_NODE) {
        textNodes.push(node as Text)
      } else {
        node.childNodes.forEach(traverse)
      }
    }
    traverse(activeElement)

    let currentOffset = 0
    for (const node of textNodes) {
      const length = node.textContent?.length || 0
      if (currentOffset + length >= pos) {
        const range = document.createRange()
        range.setStart(node, pos - currentOffset)
        range.collapse(true)
        selection.removeAllRanges()
        selection.addRange(range)
        return
      }
      currentOffset += length
    }
  }, offset)
}

// 检查是否显示斜杠菜单
export async function isSlashMenuVisible(page: Page): Promise<boolean> {
  const menu = page.locator('.slash-menu')
  return await menu.isVisible()
}

// 截图保存（用于调试）
export async function saveScreenshot(page: Page, name: string) {
  await page.screenshot({ path: `test-results/${name}.png`, fullPage: true })
}
