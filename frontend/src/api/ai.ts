import { http } from './request'
import type { RagQueryDto, RagResponse } from '@/types'

export const aiApi = {
  /**
   * Query notes using AI/RAG
   */
  queryNotes(data: RagQueryDto) {
    return http.post<RagResponse>('/v1/ai/query', data)
  },

  /**
   * Get AI query history
   */
  getQueryHistory(noteId?: string) {
    return http.get<RagResponse[]>('/v1/ai/history', {
      params: noteId ? { noteId } : undefined,
    })
  },

  /**
   * Suggest related notes based on content
   */
  suggestRelated(noteId: string) {
    return http.get<{ notes: Array<{ id: string; title: string; relevance: number }> }>(
      `/v1/ai/related/${noteId}`
    )
  },

  /**
   * Generate summary for a note
   */
  generateSummary(noteId: string) {
    return http.post<{ summary: string }>(`/v1/ai/summary/${noteId}`)
  },

  /**
   * Check if AI is configured
   */
  checkConfig() {
    return http.get<{ configured: boolean; provider: string }>('/v1/ai/config')
  },
}
