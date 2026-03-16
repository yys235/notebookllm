import { http } from './request'
import type { BlockData } from '@/plugins/feishu-docs/types'

// API Response types (backend returns camelCase via model_dump)
export interface BlockDto {
  id: string
  noteId: string
  type: string
  content?: string
  attrs?: Record<string, any>
  parentId?: string
  position: number
  createdAt: string
  updatedAt: string
}

export interface CreateBlockDto {
  type: string
  content?: string
  attrs?: Record<string, any>
  parentId?: string
  position?: number
}

export interface UpdateBlockDto {
  type?: string
  content?: string
  attrs?: Record<string, any>
  parentId?: string
  position?: number
}

// Convert frontend BlockData to backend DTO
function toBlockDto(data: Partial<BlockData>): CreateBlockDto {
  // Type is required for block creation - default to 'text' if not provided
  const result: CreateBlockDto = {
    type: data.type || 'text',
  }

  if (data.content !== undefined) {
    // Convert InlineContent to string for API
    result.content = typeof data.content === 'string'
      ? data.content
      : JSON.stringify(data.content)
  }
  if (data.attrs !== undefined) result.attrs = data.attrs
  if (data.parentId !== undefined) result.parentId = data.parentId

  return result
}

// Convert backend DTO to frontend BlockData
function fromBlockDto(dto: BlockDto): BlockData {
  return {
    id: dto.id,
    type: dto.type as any,
    content: dto.content,
    attrs: dto.attrs,
    children: dto.attrs?.children,
    parentId: dto.parentId,
  }
}

/**
 * Blocks API
 * Handles CRUD operations for document blocks
 */
export const blocksApi = {
  /**
   * Get all blocks for a note
   */
  async getBlocks(noteId: string): Promise<BlockData[]> {
    const response = await http.get<{ blocks: BlockDto[]; total: number }>(`/v1/notes/${noteId}/blocks`)
    return response.blocks.map(fromBlockDto)
  },

  /**
   * Create a new block in a note
   */
  async createBlock(noteId: string, data: Partial<BlockData>): Promise<BlockData> {
    const payload = toBlockDto(data)
    const dto = await http.post<BlockDto>(`/v1/notes/${noteId}/blocks`, payload)
    return fromBlockDto(dto)
  },

  /**
   * Update an existing block
   */
  async updateBlock(blockId: string, data: Partial<BlockData>): Promise<BlockData> {
    const payload: UpdateBlockDto = {}
    if (data.content !== undefined) {
      payload.content = typeof data.content === 'string'
        ? data.content
        : JSON.stringify(data.content)
    }
    if (data.attrs !== undefined) payload.attrs = data.attrs
    if (data.type !== undefined) payload.type = data.type
    if (data.parentId !== undefined) payload.parentId = data.parentId

    const dto = await http.put<BlockDto>(`/v1/blocks/${blockId}`, payload)
    return fromBlockDto(dto)
  },

  /**
   * Delete a block
   */
  async deleteBlock(blockId: string): Promise<void> {
    await http.delete<void>(`/v1/blocks/${blockId}`)
  },

  /**
   * Reorder blocks in a note
   * Updates the position of multiple blocks at once
   */
  async reorderBlocks(noteId: string, blockIds: string[]): Promise<void> {
    const blockOrders = blockIds.map((id, index) => ({
      block_id: id,
      position: index,
    }))
    await http.post<void>(`/v1/notes/${noteId}/blocks/reorder`, { block_orders: blockOrders })
  },
}
