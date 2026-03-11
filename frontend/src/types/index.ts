/**
 * API Response wrapper
 */
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  code?: number
}

/**
 * User entity
 */
export interface User {
  id: string
  email: string
  name: string
  avatar?: string
  createdAt: string
  updatedAt: string
}

/**
 * Login DTO
 */
export interface LoginDto {
  username: string
  password: string
}

/**
 * Register DTO
 */
export interface RegisterDto {
  email: string
  password: string
  name: string
}

/**
 * Auth response (matches backend response)
 */
export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/**
 * Note entity (matches backend response)
 * Supports both camelCase and snake_case properties from backend
 */
export interface Note {
  id: string
  title: string
  content: string
  preview?: string  // For list view
  userId: string
  user_id?: string  // snake_case from backend
  isPinned: boolean
  is_pinned?: boolean  // snake_case from backend
  visibility: 'private' | 'public'
  categoryId?: string | null
  category_id?: string | null  // snake_case from backend
  createdAt: string
  created_at?: string  // snake_case from backend
  updatedAt: string
  updated_at?: string  // snake_case from backend
}

/**
 * Create Note DTO
 */
export interface CreateNoteDto {
  title: string
  content: string
  isPinned?: boolean
  visibility?: 'private' | 'public'
  categoryId?: string | null
}

/**
 * Update Note DTO
 */
export interface UpdateNoteDto {
  title?: string
  content?: string
  isPinned?: boolean
  visibility?: 'private' | 'public'
  categoryId?: string | null
}

/**
 * RAG Query DTO
 */
export interface RagQueryDto {
  query: string
  noteIds?: string[]
  topK?: number
}

/**
 * RAG Response
 */
export interface RagResponse {
  answer: string
  sources: Array<{
    noteId: string
    title: string
    content: string
    relevance: number
  }>
  queryId: string
}

/**
 * Share options
 */
export interface ShareOptions {
  expiresIn?: number // in seconds
  password?: string
}
