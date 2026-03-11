import { http } from './request'
import type { LoginDto, RegisterDto, AuthResponse } from '@/types'

export const authApi = {
  /**
   * User login
   */
  login(data: LoginDto) {
    return http.post<AuthResponse>('/v1/auth/login', data)
  },

  /**
   * User registration
   */
  register(data: RegisterDto) {
    return http.post<AuthResponse>('/v1/auth/register', data)
  },

  /**
   * User logout
   */
  logout() {
    return http.post('/v1/auth/logout')
  },

  /**
   * Get current user profile
   */
  getProfile() {
    return http.get('/v1/auth/me')
  },

  /**
   * Refresh access token
   */
  refreshToken(refreshToken: string) {
    return http.post<AuthResponse>('/v1/auth/refresh', { refresh_token: refreshToken })
  },
}
