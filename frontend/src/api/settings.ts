import { http } from './request'

// Types
export interface AISettings {
  provider: string
  apiKey?: string
  baseUrl: string
  model?: string
  temperature: number
  maxTokens: number
  enableRag: boolean
}

export interface EmbeddingSettings {
  provider: string
  apiKey?: string
  baseUrl: string
  model?: string
}

export interface AppearanceSettings {
  theme: string
  fontSize: string
  editorMode: string
}

export interface UserSettings {
  ai: AISettings
  embedding: EmbeddingSettings
  appearance: AppearanceSettings
}

export const settingsApi = {
  /**
   * Get user settings
   */
  getSettings() {
    return http.get<UserSettings | null>('/v1/settings')
  },

  /**
   * Update user settings
   */
  updateSettings(data: Partial<UserSettings>) {
    return http.put<UserSettings>('/v1/settings', data)
  },

  /**
   * Update only AI settings
   */
  updateAISettings(ai: Partial<AISettings>) {
    return http.put<UserSettings>('/v1/settings', { ai })
  },

  /**
   * Update only embedding settings
   */
  updateEmbeddingSettings(embedding: Partial<EmbeddingSettings>) {
    return http.put<UserSettings>('/v1/settings', { embedding })
  },

  /**
   * Update only appearance settings
   */
  updateAppearanceSettings(appearance: Partial<AppearanceSettings>) {
    return http.put<UserSettings>('/v1/settings', { appearance })
  },
}
