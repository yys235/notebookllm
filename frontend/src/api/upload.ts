import { http } from './request'

export interface UploadResult {
  url: string
  filename: string
  size: number
  content_type: string
}

export const uploadApi = {
  /**
   * Upload an image file
   */
  async uploadImage(file: File): Promise<UploadResult> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch('/api/v1/upload/images', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(error.detail || 'Upload failed')
    }

    return response.json()
  },

  /**
   * Delete an uploaded image
   */
  deleteImage(filename: string) {
    return http.delete(`/v1/upload/images/${filename}`)
  },
}
