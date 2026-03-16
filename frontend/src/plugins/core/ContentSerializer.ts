// @ts-nocheck
import type { DocumentContent, Block, TextElement, BlockType, BlockStyle } from './types'

/**
 * HTML tag to BlockType mapping
 */
const HTML_TO_BLOCK_TYPE: Record<string, BlockType> = {
  'p': 'paragraph',
  'h1': 'heading1',
  'h2': 'heading2',
  'h3': 'heading3',
  'h4': 'heading4',
  'h5': 'heading5',
  'h6': 'heading6',
  'ul': 'bullet-list',
  'ol': 'ordered-list',
  'blockquote': 'quote',
  'pre': 'code-block',
  'hr': 'divider',
  'img': 'image',
  'table': 'table',
  'video': 'video',
  'audio': 'audio'
}

/**
 * BlockType to HTML tag mapping
 */
const BLOCK_TYPE_TO_HTML: Record<BlockType, string> = {
  'paragraph': 'p',
  'heading1': 'h1',
  'heading2': 'h2',
  'heading3': 'h3',
  'heading4': 'h4',
  'heading5': 'h5',
  'heading6': 'h6',
  'bullet-list': 'ul',
  'ordered-list': 'ol',
  'task-list': 'ul',
  'toggle-list': 'ul',
  'quote': 'blockquote',
  'code-block': 'pre',
  'callout': 'div',
  'divider': 'hr',
  'image': 'img',
  'video': 'video',
  'audio': 'audio',
  'file': 'a',
  'embed': 'div',
  'table': 'table',
  'grid': 'div',
  'column': 'div',
  'mindmap': 'div',
  'flowchart': 'div',
  'formula': 'div',
  'diagram': 'div'
}

/**
 * Mark type to HTML tag mapping
 */
const MARK_TO_HTML: Record<string, string> = {
  'bold': 'strong',
  'italic': 'em',
  'underline': 'u',
  'strike': 's',
  'code': 'code',
  'link': 'a'
}

/**
 * ContentSerializer - Handles conversion between HTML and JSON document content
 */
class ContentSerializerClass {
  private idCounter: number = 0

  /**
   * Generate a unique ID for blocks
   */
  generateId(): string {
    this.idCounter++
    const timestamp = Date.now().toString(36)
    const random = Math.random().toString(36).substring(2, 8)
    return `block-${timestamp}-${random}-${this.idCounter}`
  }

  /**
   * Create an empty document content structure
   */
  createEmptyDocument(): DocumentContent {
    return {
      version: '1.0',
      type: 'doc',
      id: `doc-${Date.now()}`,
      blocks: [],
      blockOrder: [],
      metadata: {
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    }
  }

  /**
   * Convert HTML string to DocumentContent JSON structure
   */
  htmlToJson(html: string): DocumentContent {
    const doc = this.createEmptyDocument()

    if (!html || typeof html !== 'string') {
      return doc
    }

    // Clean and normalize HTML
    const cleanHtml = this.normalizeHtml(html)

    // Create a temporary DOM parser
    const parser = new DOMParser()
    const dom = parser.parseFromString(cleanHtml, 'text/html')

    // Process body content
    const body = dom.body

    // Process each child node
    const blocks = this.parseChildren(body)

    doc.blocks = blocks
    doc.blockOrder = blocks.map(b => b.id)

    return doc
  }

  /**
   * Normalize HTML string before parsing
   */
  private normalizeHtml(html: string): string {
    // Wrap plain text in paragraph tags
    let normalized = html.trim()

    // Handle Tiptap specific classes and attributes
    // Remove unnecessary wrapper divs
    normalized = normalized.replace(/<div[^>]*class="[^"]*ProseMirror[^"]*"[^>]*>/gi, '')
    normalized = normalized.replace(/<\/div>/gi, '')

    return normalized
  }

  /**
   * Parse child nodes of an element into blocks
   */
  private parseChildren(element: Element): Block[] {
    const blocks: Block[] = []

    element.childNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const block = this.parseNodeToBlock(node as HTMLElement)
        if (block) {
          if (Array.isArray(block)) {
            blocks.push(...block)
          } else {
            blocks.push(block)
          }
        }
      } else if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent?.trim()
        if (text) {
          // Wrap orphan text in a paragraph
          blocks.push({
            id: this.generateId(),
            type: 'paragraph',
            elements: [{ type: 'text', text }]
          })
        }
      }
    })

    return blocks
  }

  /**
   * Parse a single HTML node to Block structure
   */
  private parseNodeToBlock(node: HTMLElement): Block | Block[] | null {
    const tagName = node.tagName.toLowerCase()
    const blockType = HTML_TO_BLOCK_TYPE[tagName]

    // Handle list containers (ul, ol)
    if (tagName === 'ul' || tagName === 'ol') {
      return this.parseList(node, blockType)
    }

    // Handle table
    if (tagName === 'table') {
      return this.parseTable(node)
    }

    // Handle code block
    if (tagName === 'pre') {
      return this.parseCodeBlock(node)
    }

    // Handle image
    if (tagName === 'img') {
      return this.parseImage(node)
    }

    // Handle video
    if (tagName === 'video') {
      return this.parseVideo(node)
    }

    // Handle audio
    if (tagName === 'audio') {
      return this.parseAudio(node)
    }

    // Handle divider
    if (tagName === 'hr') {
      return {
        id: this.generateId(),
        type: 'divider'
      }
    }

    // Handle blockquote
    if (tagName === 'blockquote') {
      return this.parseBlockquote(node)
    }

    // Default block type mapping
    if (blockType) {
      return {
        id: this.generateId(),
        type: blockType,
        elements: this.parseInlineContent(node),
        style: this.extractBlockStyle(node)
      }
    }

    // Handle unknown elements - try to extract content
    if (node.childNodes.length > 0) {
      const children = this.parseChildren(node)
      if (children.length > 0) {
        return children
      }
    }

    return null
  }

  /**
   * Parse inline content (text with formatting)
   */
  private parseInlineContent(element: Element): TextElement[] {
    const elements: TextElement[] = []

    element.childNodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent || ''
        if (text) {
          elements.push({ type: 'text', text })
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const childElement = node as HTMLElement
        const childElements = this.parseInlineElement(childElement)
        elements.push(...childElements)
      }
    })

    // Merge adjacent plain text elements
    return this.mergeTextElements(elements)
  }

  /**
   * Parse an inline element with formatting
   */
  private parseInlineElement(element: HTMLElement): TextElement[] {
    const tagName = element.tagName.toLowerCase()
    const elements: TextElement[] = []

    // Get base formatting from this element
    const baseFormat = this.getInlineFormatting(element)

    // Process child nodes
    element.childNodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent || ''
        if (text) {
          elements.push({
            type: 'text',
            text,
            ...baseFormat
          })
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const childElement = node as HTMLElement
        const childElements = this.parseInlineElement(childElement)

        // Merge formatting
        childElements.forEach(el => {
          elements.push({
            ...el,
            ...baseFormat,
            ...this.mergeFormatting(baseFormat, el)
          })
        })
      }
    })

    return elements
  }

  /**
   * Get inline formatting from element tag and styles
   */
  private getInlineFormatting(element: HTMLElement): Partial<TextElement> {
    const tagName = element.tagName.toLowerCase()
    const style = element.style
    const result: Partial<TextElement> = {}

    // Tag-based formatting
    switch (tagName) {
      case 'strong':
      case 'b':
        result.bold = true
        break
      case 'em':
      case 'i':
        result.italic = true
        break
      case 'u':
        result.underline = true
        break
      case 's':
      case 'del':
      case 'strike':
        result.strike = true
        break
      case 'code':
        result.code = true
        break
      case 'a':
        result.link = {
          href: element.getAttribute('href') || '',
          title: element.getAttribute('title') || undefined
        }
        break
    }

    // Style-based formatting
    if (style.fontWeight === 'bold' || parseInt(style.fontWeight) >= 700) {
      result.bold = true
    }
    if (style.fontStyle === 'italic') {
      result.italic = true
    }
    if (style.textDecoration?.includes('underline')) {
      result.underline = true
    }
    if (style.textDecoration?.includes('line-through')) {
      result.strike = true
    }
    if (style.color) {
      result.color = style.color
    }
    if (style.backgroundColor) {
      result.backgroundColor = style.backgroundColor
    }

    return result
  }

  /**
   * Merge formatting from two sources
   */
  private mergeFormatting(
    base: Partial<TextElement>,
    override: Partial<TextElement>
  ): Partial<TextElement> {
    const result: Partial<TextElement> = { ...override }

    // Preserve base formatting if not overridden
    if (base.bold && !override.bold) result.bold = base.bold
    if (base.italic && !override.italic) result.italic = base.italic
    if (base.underline && !override.underline) result.underline = base.underline
    if (base.strike && !override.strike) result.strike = base.strike
    if (base.code && !override.code) result.code = base.code
    if (base.color && !override.color) result.color = base.color
    if (base.backgroundColor && !override.backgroundColor) {
      result.backgroundColor = base.backgroundColor
    }

    // Merge links - override takes precedence
    if (base.link && !override.link) {
      result.link = base.link
    }

    return result
  }

  /**
   * Merge adjacent text elements with same formatting
   */
  private mergeTextElements(elements: TextElement[]): TextElement[] {
    if (elements.length === 0) return elements

    const merged: TextElement[] = []
    let current = { ...elements[0] }

    for (let i = 1; i < elements.length; i++) {
      const next = elements[i]

      if (this.hasSameFormatting(current, next)) {
        current.text += next.text
      } else {
        merged.push(current)
        current = { ...next }
      }
    }

    merged.push(current)
    return merged
  }

  /**
   * Check if two text elements have the same formatting
   */
  private hasSameFormatting(a: TextElement, b: TextElement): boolean {
    return (
      a.bold === b.bold &&
      a.italic === b.italic &&
      a.underline === b.underline &&
      a.strike === b.strike &&
      a.code === b.code &&
      a.color === b.color &&
      a.backgroundColor === b.backgroundColor &&
      a.link?.href === b.link?.href
    )
  }

  /**
   * Extract block-level styles from element
   */
  private extractBlockStyle(element: HTMLElement): BlockStyle | undefined {
    const style = element.style
    const blockStyle: BlockStyle = {}

    if (style.textAlign) {
      blockStyle.textAlign = style.textAlign as BlockStyle['textAlign']
    }
    if (style.paddingLeft) {
      const indent = parseInt(style.paddingLeft) / 40
      if (indent > 0) blockStyle.indent = indent
    }
    if (style.lineHeight) {
      blockStyle.lineHeight = parseFloat(style.lineHeight)
    }
    if (style.color) {
      blockStyle.color = style.color
    }
    if (style.backgroundColor) {
      blockStyle.backgroundColor = style.backgroundColor
    }

    return Object.keys(blockStyle).length > 0 ? blockStyle : undefined
  }

  /**
   * Parse list (ul/ol) structure
   */
  private parseList(element: HTMLElement, listType: BlockType): Block {
    const listItems: Block[] = []

    element.querySelectorAll(':scope > li').forEach(li => {
      const itemBlock: Block = {
        id: this.generateId(),
        type: 'paragraph',
        elements: this.parseInlineContent(li)
      }

      // Check for nested lists
      const nestedList = li.querySelector(':scope > ul, :scope > ol')
      if (nestedList) {
        const nestedType = nestedList.tagName.toLowerCase() === 'ul' ? 'bullet-list' : 'ordered-list'
        itemBlock.children = [this.parseList(nestedList as HTMLElement, nestedType)]
      }

      listItems.push(itemBlock)
    })

    return {
      id: this.generateId(),
      type: listType,
      children: listItems
    }
  }

  /**
   * Parse table structure
   */
  private parseTable(element: HTMLElement): Block {
    const rows: Block[] = []

    element.querySelectorAll('tr').forEach(tr => {
      const cells: Block[] = []

      tr.querySelectorAll('td, th').forEach(cell => {
        cells.push({
          id: this.generateId(),
          type: 'paragraph',
          elements: this.parseInlineContent(cell),
          attrs: {
            isHeader: cell.tagName.toLowerCase() === 'th',
            colspan: cell.getAttribute('colspan'),
            rowspan: cell.getAttribute('rowspan')
          }
        })
      })

      rows.push({
        id: this.generateId(),
        type: 'table',
        children: cells
      })
    })

    return {
      id: this.generateId(),
      type: 'table',
      children: rows
    }
  }

  /**
   * Parse code block
   */
  private parseCodeBlock(element: HTMLElement): Block {
    // Get code element inside pre if exists
    const codeElement = element.querySelector('code') || element
    const language = codeElement.getAttribute('data-language') ||
                     codeElement.className.match(/language-(\w+)/)?.[1] || ''

    return {
      id: this.generateId(),
      type: 'code-block',
      content: codeElement.textContent || '',
      attrs: {
        language
      }
    }
  }

  /**
   * Parse image element
   */
  private parseImage(element: HTMLElement): Block {
    return {
      id: this.generateId(),
      type: 'image',
      attrs: {
        src: element.getAttribute('src') || '',
        alt: element.getAttribute('alt') || '',
        title: element.getAttribute('title') || '',
        width: element.getAttribute('width'),
        height: element.getAttribute('height')
      }
    }
  }

  /**
   * Parse video element
   */
  private parseVideo(element: HTMLElement): Block {
    return {
      id: this.generateId(),
      type: 'video',
      attrs: {
        src: element.getAttribute('src') || '',
        poster: element.getAttribute('poster') || '',
        controls: element.hasAttribute('controls'),
        autoplay: element.hasAttribute('autoplay'),
        loop: element.hasAttribute('loop'),
        muted: element.hasAttribute('muted')
      }
    }
  }

  /**
   * Parse audio element
   */
  private parseAudio(element: HTMLElement): Block {
    return {
      id: this.generateId(),
      type: 'audio',
      attrs: {
        src: element.getAttribute('src') || '',
        controls: element.hasAttribute('controls'),
        autoplay: element.hasAttribute('autoplay'),
        loop: element.hasAttribute('loop'),
        muted: element.hasAttribute('muted')
      }
    }
  }

  /**
   * Parse blockquote element
   */
  private parseBlockquote(element: HTMLElement): Block {
    return {
      id: this.generateId(),
      type: 'quote',
      elements: this.parseInlineContent(element),
      style: this.extractBlockStyle(element)
    }
  }

  /**
   * Convert DocumentContent JSON to HTML string
   */
  jsonToHtml(content: DocumentContent): string {
    if (!content || !content.blocks) {
      return ''
    }

    const htmlParts = content.blocks.map(block => this.blockToHtml(block))
    return htmlParts.join('\n')
  }

  /**
   * Convert a single Block to HTML element string
   */
  private blockToHtml(block: Block): string {
    const tagName = BLOCK_TYPE_TO_HTML[block.type] || 'div'
    const styleAttr = this.styleToAttribute(block.style)
    const attrs = this.attrsToString(block.attrs)

    // Handle self-closing tags
    if (tagName === 'hr') {
      return `<hr${attrs}${styleAttr} />`
    }

    if (tagName === 'img') {
      return `<img${attrs}${styleAttr} alt="${block.attrs?.alt || ''}" src="${block.attrs?.src || ''}" />`
    }

    if (tagName === 'video' || tagName === 'audio') {
      return this.mediaToHtml(block, tagName)
    }

    // Handle code block
    if (block.type === 'code-block') {
      const language = block.attrs?.language || ''
      const languageClass = language ? ` class="language-${language}"` : ''
      return `<pre><code${languageClass}>${this.escapeHtml(block.content || '')}</code></pre>`
    }

    // Handle lists
    if (block.type === 'bullet-list' || block.type === 'ordered-list') {
      return this.listToHtml(block)
    }

    // Handle tables
    if (block.type === 'table' && block.children) {
      return this.tableToHtml(block)
    }

    // Handle blocks with text elements
    if (block.elements && block.elements.length > 0) {
      const content = this.elementsToHtml(block.elements)
      return `<${tagName}${attrs}${styleAttr}>${content}</${tagName}>`
    }

    // Handle blocks with plain content
    if (block.content !== undefined) {
      return `<${tagName}${attrs}${styleAttr}>${this.escapeHtml(block.content)}</${tagName}>`
    }

    // Handle blocks with children
    if (block.children && block.children.length > 0) {
      const childrenHtml = block.children.map(child => this.blockToHtml(child)).join('\n')
      return `<${tagName}${attrs}${styleAttr}>\n${childrenHtml}\n</${tagName}>`
    }

    return `<${tagName}${attrs}${styleAttr}></${tagName}>`
  }

  /**
   * Convert TextElement array to HTML string
   */
  private elementsToHtml(elements: TextElement[]): string {
    return elements.map(el => this.elementToHtml(el)).join('')
  }

  /**
   * Convert a single TextElement to HTML string
   */
  private elementToHtml(element: TextElement): string {
    let text = this.escapeHtml(element.text)

    // Apply formatting in reverse order (innermost first)
    if (element.code) {
      text = `<code>${text}</code>`
    }
    if (element.link) {
      const title = element.link.title ? ` title="${this.escapeHtml(element.link.title)}"` : ''
      text = `<a href="${this.escapeHtml(element.link.href)}"${title}>${text}</a>`
    }
    if (element.strike) {
      text = `<s>${text}</s>`
    }
    if (element.underline) {
      text = `<u>${text}</u>`
    }
    if (element.italic) {
      text = `<em>${text}</em>`
    }
    if (element.bold) {
      text = `<strong>${text}</strong>`
    }

    // Apply color styles
    const styles: string[] = []
    if (element.color) {
      styles.push(`color: ${element.color}`)
    }
    if (element.backgroundColor) {
      styles.push(`background-color: ${element.backgroundColor}`)
    }

    if (styles.length > 0) {
      text = `<span style="${styles.join('; ')}">${text}</span>`
    }

    return text
  }

  /**
   * Convert list block to HTML
   */
  private listToHtml(block: Block): string {
    const tagName = block.type === 'ordered-list' ? 'ol' : 'ul'
    const items = block.children || []

    const itemsHtml = items.map(item => {
      let itemContent = ''

      if (item.elements && item.elements.length > 0) {
        itemContent = this.elementsToHtml(item.elements)
      }

      // Handle nested lists
      if (item.children && item.children.length > 0) {
        const nestedHtml = item.children.map(child => this.listToHtml(child)).join('\n')
        itemContent += `\n${nestedHtml}`
      }

      return `<li>${itemContent}</li>`
    }).join('\n')

    return `<${tagName}>\n${itemsHtml}\n</${tagName}>`
  }

  /**
   * Convert table block to HTML
   */
  private tableToHtml(block: Block): string {
    const rows = block.children || []

    const rowsHtml = rows.map(row => {
      const cells = row.children || []
      const cellsHtml = cells.map(cell => {
        const tagName = cell.attrs?.isHeader ? 'th' : 'td'
        const colspan = cell.attrs?.colspan ? ` colspan="${cell.attrs.colspan}"` : ''
        const rowspan = cell.attrs?.rowspan ? ` rowspan="${cell.attrs.rowspan}"` : ''
        const content = cell.elements ? this.elementsToHtml(cell.elements) : ''
        return `<${tagName}${colspan}${rowspan}>${content}</${tagName}>`
      }).join('')

      return `<tr>${cellsHtml}</tr>`
    }).join('\n')

    return `<table>\n${rowsHtml}\n</table>`
  }

  /**
   * Convert media block (video/audio) to HTML
   */
  private mediaToHtml(block: Block, tagName: string): string {
    const attrs: string[] = []

    if (block.attrs?.src) {
      attrs.push(`src="${this.escapeHtml(block.attrs.src)}"`)
    }
    if (block.attrs?.poster) {
      attrs.push(`poster="${this.escapeHtml(block.attrs.poster)}"`)
    }
    if (block.attrs?.controls) {
      attrs.push('controls')
    }
    if (block.attrs?.autoplay) {
      attrs.push('autoplay')
    }
    if (block.attrs?.loop) {
      attrs.push('loop')
    }
    if (block.attrs?.muted) {
      attrs.push('muted')
    }

    return `<${tagName} ${attrs.join(' ')}></${tagName}>`
  }

  /**
   * Convert BlockStyle to HTML attribute string
   */
  private styleToAttribute(style?: BlockStyle): string {
    if (!style) return ''

    const styles: string[] = []

    if (style.textAlign) {
      styles.push(`text-align: ${style.textAlign}`)
    }
    if (style.indent) {
      styles.push(`padding-left: ${style.indent * 40}px`)
    }
    if (style.lineHeight) {
      styles.push(`line-height: ${style.lineHeight}`)
    }
    if (style.color) {
      styles.push(`color: ${style.color}`)
    }
    if (style.backgroundColor) {
      styles.push(`background-color: ${style.backgroundColor}`)
    }

    return styles.length > 0 ? ` style="${styles.join('; ')}"` : ''
  }

  /**
   * Convert attrs object to HTML attribute string
   */
  private attrsToString(attrs?: Record<string, any>): string {
    if (!attrs) return ''

    const parts: string[] = []

    Object.entries(attrs).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== false) {
        if (value === true) {
          parts.push(key)
        } else {
          parts.push(`${key}="${this.escapeHtml(String(value))}"`)
        }
      }
    })

    return parts.length > 0 ? ` ${parts.join(' ')}` : ''
  }

  /**
   * Extract plain text from a block
   */
  extractText(block: Block): string {
    // If block has elements array
    if (block.elements && block.elements.length > 0) {
      return block.elements.map(el => el.text).join('')
    }

    // If block has plain content
    if (block.content !== undefined) {
      return block.content
    }

    // If block has children, recursively extract
    if (block.children && block.children.length > 0) {
      return block.children.map(child => this.extractText(child)).join(' ')
    }

    return ''
  }

  /**
   * Extract all text from a document
   */
  extractDocumentText(content: DocumentContent): string {
    if (!content.blocks) return ''

    return content.blocks
      .map(block => this.extractText(block))
      .filter(text => text.trim())
      .join('\n')
  }

  /**
   * Escape HTML special characters
   */
  private escapeHtml(text: string): string {
    const escapeMap: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }

    return text.replace(/[&<>"']/g, char => escapeMap[char])
  }

  /**
   * Validate document content structure
   */
  validateContent(content: DocumentContent): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (!content.type || content.type !== 'doc') {
      errors.push('Invalid document type')
    }

    if (!content.id) {
      errors.push('Document ID is missing')
    }

    if (!Array.isArray(content.blocks)) {
      errors.push('Blocks must be an array')
    } else {
      const blockIds = new Set<string>()

      content.blocks.forEach((block, index) => {
        if (!block.id) {
          errors.push(`Block at index ${index} is missing ID`)
        } else if (blockIds.has(block.id)) {
          errors.push(`Duplicate block ID: ${block.id}`)
        } else {
          blockIds.add(block.id)
        }

        if (!block.type) {
          errors.push(`Block at index ${index} is missing type`)
        }
      })

      // Validate blockOrder
      if (content.blockOrder) {
        content.blockOrder.forEach(orderId => {
          if (!blockIds.has(orderId)) {
            errors.push(`Block order references non-existent block: ${orderId}`)
          }
        })
      }
    }

    return {
      valid: errors.length === 0,
      errors
    }
  }

  /**
   * Clone document content
   */
  cloneContent(content: DocumentContent): DocumentContent {
    return JSON.parse(JSON.stringify(content))
  }

  /**
   * Merge two document contents
   */
  mergeContents(base: DocumentContent, overlay: DocumentContent): DocumentContent {
    const merged = this.cloneContent(base)

    // Merge blocks by ID
    const blockMap = new Map<string, Block>()
    merged.blocks.forEach(b => blockMap.set(b.id, b))

    overlay.blocks.forEach(block => {
      blockMap.set(block.id, block)
    })

    merged.blocks = Array.from(blockMap.values())
    merged.blockOrder = [...new Set([...merged.blockOrder, ...overlay.blockOrder])]
    merged.metadata = {
      ...merged.metadata,
      ...overlay.metadata,
      updatedAt: new Date().toISOString()
    }

    return merged
  }
}

// Export singleton instance
export const ContentSerializer = new ContentSerializerClass()
export default ContentSerializer
