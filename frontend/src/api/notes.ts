import { http } from './request'
import type { Note, CreateNoteDto, UpdateNoteDto } from '@/types'

// Convert frontend camelCase to backend snake_case
function toSnakeCase(data: any): any {
  const result: any = {}
  for (const key in data) {
    if (key === 'isPinned') {
      result.is_pinned = data[key]
    } else if (key === 'categoryId') {
      result.category_id = data[key]
    } else {
      result[key] = data[key]
    }
  }
  return result
}

export const noteApi = {
  /**
   * Get all notes for current user
   */
  getNotes(params?: { page?: number; page_size?: number; search?: string }) {
    return http.get<Note[]>('/v1/notes', { params })
  },

  /**
   * Get a single note by ID
   */
  getNote(id: string) {
    return http.get<Note>(`/v1/notes/${id}`)
  },

  /**
   * Create a new note
   */
  createNote(data: CreateNoteDto) {
    return http.post<Note>('/v1/notes', toSnakeCase(data))
  },

  /**
   * Update an existing note
   */
  updateNote(id: string, data: UpdateNoteDto) {
    return http.patch<Note>(`/v1/notes/${id}`, toSnakeCase(data))
  },

  /**
   * Delete a note
   */
  deleteNote(id: string) {
    return http.delete<void>(`/v1/notes/${id}`)
  },

  /**
   * Search notes
   */
  searchNotes(query: string) {
    return http.get<Note[]>('/v1/notes', { params: { search: query } })
  },
}
