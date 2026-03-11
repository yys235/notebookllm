import { message } from 'ant-design-vue'

/**
 * Notification composable for consistent user feedback
 */
export function useNotification() {
  const success = (msg: string) => {
    return message.success(msg)
  }

  const error = (msg: string) => {
    return message.error(msg)
  }

  const warning = (msg: string) => {
    return message.warning(msg)
  }

  const info = (msg: string) => {
    return message.info(msg)
  }

  const loading = (msg: string, duration = 0) => {
    return message.loading(msg, duration)
  }

  return {
    success,
    error,
    warning,
    info,
    loading,
  }
}
