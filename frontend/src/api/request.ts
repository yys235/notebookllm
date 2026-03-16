import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig, AxiosResponse } from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

// Create axios instance
const request: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - unwrap response data
request.interceptors.response.use(
  (response: AxiosResponse): any => {
    return response.data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const url = error.config?.url || ''

      // Check if this is a public API (share links) - don't redirect to login
      const isPublicApi = url.includes('/shares/public/')

      switch (status) {
        case 401:
          // Only redirect to login for non-public APIs
          if (!isPublicApi) {
            localStorage.removeItem('token')
            // Save current path for redirect after login
            const currentPath = window.location.pathname + window.location.search
            // Don't redirect to login page if already on login page
            if (!currentPath.startsWith('/login') && !currentPath.startsWith('/register')) {
              window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
            }
          }
          break
        case 403:
          console.error('Access forbidden')
          break
        case 404:
          console.error('Resource not found')
          break
        case 500:
          console.error('Server error')
          break
        default:
          console.error('Request error:', data?.message || error.message)
      }

      // Include status in the rejected promise for easier error handling
      return Promise.reject({ ...data, status })
    }

    if (error.request) {
      console.error('Network error - no response received')
      return Promise.reject({ message: 'Network error. Please check your connection.' })
    }

    return Promise.reject({ message: error.message || 'An unknown error occurred' })
  }
)

// Generic request methods
// Note: Response interceptor already unwraps response.data, so we return T directly
export const http = {
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return request.get(url, config)
  },
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return request.post(url, data, config)
  },
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return request.put(url, data, config)
  },
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return request.patch(url, data, config)
  },
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return request.delete(url, config)
  },
}

export default request
