import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

/**
 * Format date to string
 */
export function formatDate(date: string | Date, format = 'YYYY-MM-DD HH:mm'): string {
  return dayjs(date).format(format)
}

/**
 * Format date to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: string | Date): string {
  return dayjs(date).fromNow()
}

/**
 * Check if date is today
 */
export function isToday(date: string | Date): boolean {
  return dayjs(date).isSame(dayjs(), 'day')
}

/**
 * Get calendar time (e.g., "Today at 14:30", "Yesterday at 09:15", or "2024-03-01 14:30")
 */
export function formatCalendarTime(date: string | Date): string {
  const d = dayjs(date)
  const now = dayjs()

  if (d.isSame(now, 'day')) {
    return `Today at ${d.format('HH:mm')}`
  }

  if (d.isSame(now.subtract(1, 'day'), 'day')) {
    return `Yesterday at ${d.format('HH:mm')}`
  }

  return d.format('YYYY-MM-DD HH:mm')
}

export default dayjs
