import { http } from './request'

// Types - matching backend snake_case response
export interface ShareLink {
  id: string
  note_id: string
  token: string
  has_password: boolean
  max_access_count: number
  is_active: boolean
  expires_at: string | null
  created_at: string
  last_accessed_at: string | null
  access_count: number
  remaining_accesses: number | null
  is_expired: boolean
  share_url: string
}

export interface CreateShareLinkDto {
  noteId: string
  expiresInHours?: number | null
  password?: string | null
  maxAccessCount?: number
}

export interface UpdateShareLinkDto {
  expiresInHours?: number | null
  password?: string | null
  maxAccessCount?: number
}

export interface ShareLinkInfo {
  token: string
  has_password: boolean
  is_valid: boolean
  error?: string
  expires_at: string | null
  note_visibility: 'private' | 'public'
  requires_password: boolean
}

export const sharesApi = {
  /**
   * List share links for current user
   */
  listShareLinks(params?: { page?: number; pageSize?: number; noteId?: string; activeOnly?: boolean }) {
    // Convert camelCase to snake_case for backend
    const backendParams: any = {}
    if (params?.page) backendParams.page = params.page
    if (params?.pageSize) backendParams.page_size = params.pageSize
    if (params?.noteId) backendParams.note_id = params.noteId
    if (params?.activeOnly !== undefined) backendParams.active_only = params.activeOnly
    return http.get<{ items: ShareLink[]; total: number }>('/v1/shares', { params: backendParams })
  },

  /**
   * Create a new share link
   */
  createShareLink(data: CreateShareLinkDto) {
    return http.post<ShareLink>('/v1/shares', {
      note_id: data.noteId,
      expires_in_hours: data.expiresInHours,
      password: data.password,
      max_access_count: data.maxAccessCount || 0,
    })
  },

  /**
   * Get share link details
   */
  getShareLink(linkId: string) {
    return http.get<ShareLink>(`/v1/shares/${linkId}`)
  },

  /**
   * Update share link
   */
  updateShareLink(linkId: string, data: UpdateShareLinkDto) {
    return http.patch<ShareLink>(`/v1/shares/${linkId}`, {
      expires_in_hours: data.expiresInHours,
      password: data.password,
      max_access_count: data.maxAccessCount,
    })
  },

  /**
   * Revoke (deactivate) share link
   */
  revokeShareLink(linkId: string) {
    return http.post<ShareLink>(`/v1/shares/${linkId}/revoke`)
  },

  /**
   * Reactivate share link
   */
  reactivateShareLink(linkId: string) {
    return http.post<ShareLink>(`/v1/shares/${linkId}/reactivate`)
  },

  /**
   * Delete share link permanently
   */
  deleteShareLink(linkId: string) {
    return http.delete<void>(`/v1/shares/${linkId}`)
  },

  /**
   * Get share link info (public, no auth required)
   */
  getShareLinkInfo(token: string) {
    return http.get<ShareLinkInfo>(`/v1/shares/public/${token}/info`)
  },

  /**
   * Access shared note (public, no auth required)
   */
  accessSharedNote(token: string, password?: string) {
    const body: any = {}
    if (password) {
      body.password = password
    }
    return http.post<{
      id: string
      title: string
      content: string
      created_at: string
      updated_at: string
    }>(`/v1/shares/public/${token}/access`, body)
  },
}
