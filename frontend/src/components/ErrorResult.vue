<script setup lang="ts">
import { computed } from 'vue'
import {
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  HomeOutlined,
} from '@ant-design/icons-vue'

interface Props {
  status?: 'error' | 'warning' | '403' | '404' | '500'
  title?: string
  description?: string
  showActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  status: 'error',
  title: '',
  description: '',
  showActions: true,
})

const statusConfig = computed(() => {
  const configs = {
    error: {
      icon: CloseCircleOutlined,
      color: '#ff4d4f',
      defaultTitle: 'Error',
      defaultDesc: 'Something went wrong. Please try again later.',
    },
    warning: {
      icon: WarningOutlined,
      color: '#faad14',
      defaultTitle: 'Warning',
      defaultDesc: 'Please check your input and try again.',
    },
    403: {
      icon: WarningOutlined,
      color: '#faad14',
      defaultTitle: '403',
      defaultDesc: 'Sorry, you do not have permission to access this page.',
    },
    404: {
      icon: InfoCircleOutlined,
      color: '#999',
      defaultTitle: '404',
      defaultDesc: 'Sorry, the page you visited does not exist.',
    },
    500: {
      icon: CloseCircleOutlined,
      color: '#ff4d4f',
      defaultTitle: '500',
      defaultDesc: 'Sorry, the server is reporting an error. Please try again later.',
    },
  }
  return configs[props.status]
})

const displayTitle = computed(() => props.title || statusConfig.value.defaultTitle)
const displayDesc = computed(() => props.description || statusConfig.value.defaultDesc)

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'home'): void
}>()

function handleRetry() {
  emit('retry')
}

function handleHome() {
  emit('home')
}
</script>

<template>
  <div class="error-result">
    <div class="error-content">
      <div
        class="error-icon"
        :style="{ color: statusConfig.color }"
      >
        <component :is="statusConfig.icon" />
      </div>

      <h1 class="error-title">{{ displayTitle }}</h1>

      <p class="error-description">
        {{ displayDesc }}
      </p>

      <div v-if="showActions" class="error-actions">
        <a-button type="primary" @click="handleRetry">
          <template #icon><ReloadOutlined /></template>
          Try Again
        </a-button>
        <a-button @click="handleHome">
          <template #icon><HomeOutlined /></template>
          Back Home
        </a-button>
      </div>

      <div v-if="$slots.extra" class="error-extra">
        <slot name="extra" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.error-result {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 48px 24px;
}

.error-content {
  text-align: center;
  max-width: 500px;
}

.error-icon {
  font-size: 72px;
  margin-bottom: 24px;
}

.error-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 16px;
}

.error-description {
  font-size: 16px;
  color: #666;
  margin: 0 0 32px;
  line-height: 1.6;
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 32px;
}

.error-extra {
  padding-top: 24px;
  border-top: 1px solid #e8e8e8;
}

/* Responsive */
@media (max-width: 768px) {
  .error-actions {
    flex-direction: column;
  }

  .error-actions .ant-btn {
    width: 100%;
  }
}
</style>
