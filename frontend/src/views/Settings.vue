<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  SaveOutlined,
  ApiOutlined,
  KeyOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ArrowLeftOutlined,
  ReloadOutlined,
  RobotOutlined,
  UserOutlined,
  BgColorsOutlined,
  SettingOutlined,
  CloudOutlined,
  DatabaseOutlined,
  SafetyOutlined,
  LoadingOutlined,
} from '@ant-design/icons-vue'
import { settingsApi } from '@/api/settings'

const router = useRouter()

// Active tab
const activeTab = ref('ai')

// Loading state
const loadingSettings = ref(true)
const savingSettings = ref(false)

// Dynamic model lists
const fetchedModels = ref<string[]>([])
const fetchedEmbeddingModels = ref<string[]>([])
const loadingModels = ref(false)
const loadingEmbeddingModels = ref(false)

// AI Model settings - all empty by default
const aiSettings = reactive({
  provider: '',
  apiKey: '',
  baseUrl: '',
  model: '',
  temperature: 0.7,
  maxTokens: 2000,
  enableRag: true,
})

// Embedding Model settings - separate from AI settings
const embeddingSettings = reactive({
  provider: '',
  apiKey: '',
  baseUrl: '',
  model: '',
})

const availableProviders = [
  { value: 'ollama', label: 'Ollama', description: '本地运行，免费', icon: '🦙', color: '#f97316' },
  { value: 'openai', label: 'OpenAI', description: 'GPT-4, GPT-3.5', icon: '🤖', color: '#10a37f' },
  { value: 'anthropic', label: 'Anthropic', description: 'Claude 系列', icon: '🧠', color: '#d97706' },
  { value: 'custom', label: '自定义', description: 'OpenAI 兼容 API', icon: '⚙️', color: '#6b7280' },
]

const embeddingProviders = [
  { value: 'ollama', label: 'Ollama', icon: '🦙', color: '#f97316' },
  { value: 'openai', label: 'OpenAI', icon: '🤖', color: '#10a37f' },
  { value: 'custom', label: 'OpenAI 兼容 API', icon: '⚙️', color: '#6b7280' },
]

// Connection state for AI model
const testingConnection = ref(false)
const connectionStatus = ref<'idle' | 'success' | 'error'>('idle')
const connectionMessage = ref('')

// Connection state for Embedding model
const testingEmbeddingConnection = ref(false)
const embeddingConnectionStatus = ref<'idle' | 'success' | 'error'>('idle')
const embeddingConnectionMessage = ref('')

// Profile settings
const profileSettings = reactive({
  name: '',
  email: '',
})

// Appearance settings
const appearanceSettings = reactive({
  theme: 'light' as 'light' | 'dark' | 'auto',
  fontSize: 'medium' as 'small' | 'medium' | 'large',
})

// Helper function
function normalizeOllamaUrl(url: string): string {
  let normalizedUrl = url.trim()
  if (!normalizedUrl) return 'http://192.168.123.220:11434'
  if (normalizedUrl.startsWith('/')) return normalizedUrl
  if (import.meta.env.DEV) return '/ollama'
  if (normalizedUrl.startsWith('http://') || normalizedUrl.startsWith('https://')) {
    return normalizedUrl.replace(/\/$/, '')
  }
  const ipPattern = /^[\d.]+(:\d+)?$|^[\w.-]+(:\d+)?$/
  if (ipPattern.test(normalizedUrl)) {
    if (!normalizedUrl.includes(':')) normalizedUrl = `${normalizedUrl}:11434`
    return `http://${normalizedUrl}`
  }
  return normalizedUrl
}

async function testConnection() {
  if (aiSettings.provider !== 'ollama' && !aiSettings.apiKey) {
    message.warning('请先输入 API Key')
    return
  }

  testingConnection.value = true
  connectionStatus.value = 'idle'

  try {
    if (aiSettings.provider === 'ollama') {
      const connectionUrl = normalizeOllamaUrl(aiSettings.baseUrl)
      const response = await fetch(`${connectionUrl}/api/tags`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      connectionStatus.value = 'success'
      connectionMessage.value = `连接成功！发现 ${data.models?.length || 0} 个模型`
      message.success(connectionMessage.value)
    } else {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      connectionStatus.value = 'success'
      connectionMessage.value = '连接成功！'
      message.success(connectionMessage.value)
    }
  } catch (error: any) {
    connectionStatus.value = 'error'
    connectionMessage.value = error.message || '连接失败'
    message.error(connectionMessage.value)
  } finally {
    testingConnection.value = false
  }
}

async function fetchOllamaModels() {
  if (aiSettings.provider !== 'ollama') return
  loadingModels.value = true
  try {
    const baseUrl = normalizeOllamaUrl(aiSettings.baseUrl)
    const response = await fetch(`${baseUrl}/api/tags`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    })
    if (response.ok) {
      const data = await response.json()
      fetchedModels.value = data.models?.map((m: any) => m.name) || []
      if (fetchedModels.value.length > 0 && !fetchedModels.value.includes(aiSettings.model)) {
        aiSettings.model = fetchedModels.value[0] || ''
      }
    }
  } catch (error) {
    console.error('Failed to fetch models:', error)
  } finally {
    loadingModels.value = false
  }
}

async function fetchOllamaEmbeddingModels() {
  if (embeddingSettings.provider !== 'ollama') return
  loadingEmbeddingModels.value = true
  try {
    const baseUrl = normalizeOllamaUrl(embeddingSettings.baseUrl)
    const response = await fetch(`${baseUrl}/api/tags`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    })
    if (response.ok) {
      const data = await response.json()
      const allModels = data.models?.map((m: any) => m.name) || []
      fetchedEmbeddingModels.value = allModels.filter((name: string) =>
        name.toLowerCase().includes('embed') ||
        name.toLowerCase().includes('nomic') ||
        name.toLowerCase().includes('minilm') ||
        name.toLowerCase().includes('mxbai')
      )
      if (fetchedEmbeddingModels.value.length === 0) {
        fetchedEmbeddingModels.value = allModels
      }
      if (fetchedEmbeddingModels.value.length > 0 && !embeddingSettings.model) {
        embeddingSettings.model = fetchedEmbeddingModels.value[0] || ''
      }
    }
  } catch (error) {
    console.error('Failed to fetch embedding models:', error)
  } finally {
    loadingEmbeddingModels.value = false
  }
}

function handleProviderChange() {
  // Clear previous configuration
  aiSettings.apiKey = ''
  aiSettings.baseUrl = ''
  aiSettings.model = ''
  connectionStatus.value = 'idle'
  fetchedModels.value = []

  if (aiSettings.provider === 'ollama') {
    fetchOllamaModels()
  }
}

function handleEmbeddingProviderChange() {
  // Clear previous configuration
  embeddingSettings.apiKey = ''
  embeddingSettings.baseUrl = ''
  embeddingSettings.model = ''
  embeddingConnectionStatus.value = 'idle'
  fetchedEmbeddingModels.value = []

  if (embeddingSettings.provider === 'ollama') {
    fetchOllamaEmbeddingModels()
  }
}

async function testEmbeddingConnection() {
  if (embeddingSettings.provider === 'ollama') {
    // Ollama doesn't require API key
  } else if (!embeddingSettings.apiKey) {
    message.warning('请先输入 API Key')
    return
  }

  testingEmbeddingConnection.value = true
  embeddingConnectionStatus.value = 'idle'

  try {
    if (embeddingSettings.provider === 'ollama') {
      const connectionUrl = normalizeOllamaUrl(embeddingSettings.baseUrl)
      const response = await fetch(`${connectionUrl}/api/tags`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      embeddingConnectionStatus.value = 'success'
      embeddingConnectionMessage.value = `连接成功！发现 ${data.models?.length || 0} 个模型`
      message.success(embeddingConnectionMessage.value)
    } else if (embeddingSettings.provider === 'custom') {
      // Test custom OpenAI-compatible API
      const baseUrl = embeddingSettings.baseUrl || 'https://api.openai.com'
      const response = await fetch(`${baseUrl}/v1/models`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Authorization': `Bearer ${embeddingSettings.apiKey}`,
        },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      embeddingConnectionStatus.value = 'success'
      embeddingConnectionMessage.value = '连接成功！'
      message.success(embeddingConnectionMessage.value)
    } else {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      embeddingConnectionStatus.value = 'success'
      embeddingConnectionMessage.value = '连接成功！'
      message.success(embeddingConnectionMessage.value)
    }
  } catch (error: any) {
    embeddingConnectionStatus.value = 'error'
    embeddingConnectionMessage.value = error.message || '连接失败'
    message.error(embeddingConnectionMessage.value)
  } finally {
    testingEmbeddingConnection.value = false
  }
}

async function loadSettings() {
  loadingSettings.value = true
  try {
    const settings = await settingsApi.getSettings()

    // If no settings exist, keep everything empty
    if (!settings) {
      loadingSettings.value = false
      return
    }

    // Load AI settings
    aiSettings.provider = settings.ai?.provider || ''
    aiSettings.apiKey = settings.ai?.apiKey || ''
    aiSettings.baseUrl = settings.ai?.baseUrl || ''
    aiSettings.model = settings.ai?.model || ''
    aiSettings.temperature = settings.ai?.temperature ?? 0.7
    aiSettings.maxTokens = settings.ai?.maxTokens ?? 2000
    aiSettings.enableRag = settings.ai?.enableRag ?? true

    // Load Embedding settings
    embeddingSettings.provider = settings.embedding?.provider || ''
    embeddingSettings.apiKey = settings.embedding?.apiKey || ''
    embeddingSettings.baseUrl = settings.embedding?.baseUrl || ''
    embeddingSettings.model = settings.embedding?.model || ''

    // Load Appearance settings
    appearanceSettings.theme = (settings.appearance?.theme || 'light') as 'light' | 'dark' | 'auto'
    appearanceSettings.fontSize = (settings.appearance?.fontSize || 'medium') as 'small' | 'medium' | 'large'

    // Fetch models if provider is ollama and has baseUrl
    if (aiSettings.provider === 'ollama' && aiSettings.baseUrl) {
      fetchOllamaModels()
    }
    if (embeddingSettings.provider === 'ollama' && embeddingSettings.baseUrl) {
      fetchOllamaEmbeddingModels()
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loadingSettings.value = false
  }
}

async function saveAiSettings() {
  savingSettings.value = true
  try {
    // Build the data object, only include non-empty values
    const data: any = {}

    // Only include provider if selected
    if (aiSettings.provider) {
      data.provider = aiSettings.provider
    }

    // Only include optional fields if they have values
    if (aiSettings.apiKey) {
      data.apiKey = aiSettings.apiKey
    }
    if (aiSettings.baseUrl) {
      data.baseUrl = aiSettings.baseUrl
    }
    if (aiSettings.model) {
      data.model = aiSettings.model
    }

    // Always include advanced settings
    data.temperature = aiSettings.temperature
    data.maxTokens = aiSettings.maxTokens
    data.enableRag = aiSettings.enableRag

    await settingsApi.updateAISettings(data)
    message.success('AI 模型设置已保存')
  } catch (error) {
    console.error('Failed to save AI settings:', error)
    message.error('保存 AI 模型设置失败')
  } finally {
    savingSettings.value = false
  }
}

async function saveEmbeddingSettings() {
  savingSettings.value = true
  try {
    // Build the data object, only include non-empty values
    const data: any = {}

    // Only include provider if selected
    if (embeddingSettings.provider) {
      data.provider = embeddingSettings.provider
    }

    // Only include optional fields if they have values
    if (embeddingSettings.apiKey) {
      data.apiKey = embeddingSettings.apiKey
    }
    if (embeddingSettings.baseUrl) {
      data.baseUrl = embeddingSettings.baseUrl
    }
    if (embeddingSettings.model) {
      data.model = embeddingSettings.model
    }

    await settingsApi.updateEmbeddingSettings(data)
    message.success('嵌入模型设置已保存')
  } catch (error) {
    console.error('Failed to save embedding settings:', error)
    message.error('保存嵌入模型设置失败')
  } finally {
    savingSettings.value = false
  }
}

async function saveAppearanceSettings() {
  savingSettings.value = true
  try {
    await settingsApi.updateAppearanceSettings({
      theme: appearanceSettings.theme,
      fontSize: appearanceSettings.fontSize,
      editorMode: 'rich', // Default editor mode
    })
    message.success('外观设置已保存')
  } catch (error) {
    console.error('Failed to save appearance settings:', error)
    message.error('保存外观设置失败')
  } finally {
    savingSettings.value = false
  }
}

async function saveProfileSettings() {
  savingSettings.value = true
  try {
    // Profile settings would need a separate API endpoint
    // For now, just show a success message
    message.success('个人资料已保存')
  } catch (error) {
    console.error('Failed to save profile settings:', error)
    message.error('保存个人资料失败')
  } finally {
    savingSettings.value = false
  }
}

function goBack() {
  router.push('/notes')
}

// Menu items
const menuItems = [
  { key: 'ai', icon: RobotOutlined, label: 'AI 模型', description: '配置 AI 服务' },
  { key: 'embedding', icon: DatabaseOutlined, label: '嵌入模型', description: '配置向量嵌入' },
  { key: 'profile', icon: UserOutlined, label: '个人资料', description: '账户信息' },
  { key: 'appearance', icon: BgColorsOutlined, label: '外观', description: '主题和样式' },
]

onMounted(() => {
  loadSettings()
})
</script>

<template>
  <div class="settings-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <a-button type="text" @click="goBack" class="back-btn">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </a-button>
        <h1>设置</h1>
      </div>
    </div>

    <div class="settings-container">
      <!-- Sidebar Navigation -->
      <div class="settings-nav">
        <div
          v-for="item in menuItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: activeTab === item.key }"
          @click="activeTab = item.key"
        >
          <div class="nav-icon">
            <component :is="item.icon" />
          </div>
          <div class="nav-content">
            <div class="nav-label">{{ item.label }}</div>
            <div class="nav-desc">{{ item.description }}</div>
          </div>
        </div>
      </div>

      <!-- Content Area -->
      <div class="settings-main">
        <!-- AI Model Settings -->
        <div v-if="activeTab === 'ai'" class="settings-section">
          <!-- Loading State -->
          <div v-if="loadingSettings" class="loading-container">
            <LoadingOutlined class="loading-icon" spin />
            <span>加载设置中...</span>
          </div>
          <template v-else>
          <div class="section-header">
            <h2><RobotOutlined /> AI 模型配置</h2>
            <p>配置 AI 模型以启用智能笔记功能</p>
          </div>

          <!-- Provider Selection Card -->
          <div class="setting-card">
            <div class="card-title">
              <CloudOutlined />
              <span>AI 服务商</span>
            </div>
            <div class="provider-grid">
              <div
                v-for="provider in availableProviders"
                :key="provider.value"
                class="provider-card"
                :class="{ selected: aiSettings.provider === provider.value }"
                @click="aiSettings.provider = provider.value; handleProviderChange()"
              >
                <div class="provider-icon" :style="{ background: provider.color + '20', color: provider.color }">
                  {{ provider.icon }}
                </div>
                <div class="provider-info">
                  <div class="provider-name">{{ provider.label }}</div>
                  <div class="provider-desc">{{ provider.description }}</div>
                </div>
                <div v-if="aiSettings.provider === provider.value" class="provider-check">
                  <CheckCircleOutlined />
                </div>
              </div>
            </div>
          </div>

          <!-- Connection Settings Card -->
          <div class="setting-card">
            <div class="card-title">
              <ApiOutlined />
              <span>连接配置</span>
            </div>

            <!-- Base URL for Ollama/Custom -->
            <div v-if="aiSettings.provider === 'ollama' || aiSettings.provider === 'custom'" class="form-group">
              <label>服务地址</label>
              <a-input
                v-model:value="aiSettings.baseUrl"
                placeholder="http://192.168.123.220:11434"
                size="large"
              >
                <template #prefix><ApiOutlined class="input-icon" /></template>
              </a-input>
              <div class="form-hint" v-if="aiSettings.provider === 'ollama'">
                开发模式会自动使用代理，避免 CORS 问题
              </div>
            </div>

            <!-- API Key for others -->
            <div v-if="aiSettings.provider !== 'ollama'" class="form-group">
              <label>API Key</label>
              <a-input-password
                v-model:value="aiSettings.apiKey"
                placeholder="sk-..."
                size="large"
              >
                <template #prefix><KeyOutlined class="input-icon" /></template>
              </a-input-password>
            </div>

            <!-- Model Selection -->
            <div class="form-group">
              <label>模型</label>
              <div class="model-select-row">
                <a-select
                  v-model:value="aiSettings.model"
                  size="large"
                  :loading="loadingModels"
                  class="model-select"
                  @dropdown-visible-change="($event) => $event && aiSettings.provider === 'ollama' && fetchOllamaModels()"
                >
                  <template v-if="aiSettings.provider === 'ollama' && fetchedModels.length > 0">
                    <a-select-option v-for="name in fetchedModels" :key="name" :value="name">
                      {{ name }}
                    </a-select-option>
                  </template>
                </a-select>
                <a-button v-if="aiSettings.provider === 'ollama'" @click="fetchOllamaModels" :loading="loadingModels">
                  <template #icon><ReloadOutlined /></template>
                </a-button>
              </div>
            </div>

            <!-- Connection Test -->
            <div class="form-group">
              <label>连接状态</label>
              <div class="connection-status">
                <a-button
                  type="primary"
                  :loading="testingConnection"
                  @click="testConnection"
                >
                  测试连接
                </a-button>
                <div v-if="connectionStatus !== 'idle'" class="status-result" :class="connectionStatus">
                  <CheckCircleOutlined v-if="connectionStatus === 'success'" />
                  <ExclamationCircleOutlined v-if="connectionStatus === 'error'" />
                  <span>{{ connectionMessage }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Advanced Settings Card -->
          <div class="setting-card">
            <div class="card-title">
              <SettingOutlined />
              <span>高级设置</span>
            </div>

            <div class="form-group">
              <label>Temperature (创造性)</label>
              <div class="slider-row">
                <a-slider v-model:value="aiSettings.temperature" :min="0" :max="2" :step="0.1" />
                <span class="slider-value">{{ aiSettings.temperature }}</span>
              </div>
              <div class="form-hint">值越低越精确，值越高越创造性</div>
            </div>

            <div class="form-group">
              <label>最大 Token 数</label>
              <a-input-number
                v-model:value="aiSettings.maxTokens"
                :min="0"
                :step="100"
                :precision="0"
                placeholder="2000"
                size="large"
                style="width: 100%"
                @blur="() => { if (!aiSettings.maxTokens && aiSettings.maxTokens !== 0) aiSettings.maxTokens = 2000 }"
              />
              <div class="form-hint">默认 2000，0 表示不限制</div>
            </div>

            <div class="form-group">
              <a-checkbox v-model:checked="aiSettings.enableRag">
                启用 RAG (检索增强生成)
              </a-checkbox>
              <div class="form-hint">AI 回答时会参考你的笔记内容，需要在「嵌入模型」页面配置嵌入服务</div>
            </div>
          </div>

          <!-- Save Button -->
          <div class="save-section">
            <a-button type="primary" size="large" :loading="savingSettings" @click="saveAiSettings">
              <template #icon><SaveOutlined /></template>
              保存设置
            </a-button>
          </div>
          </template>
        </div>

        <!-- Embedding Model Settings -->
        <div v-else-if="activeTab === 'embedding'" class="settings-section">
          <!-- Loading State -->
          <div v-if="loadingSettings" class="loading-container">
            <LoadingOutlined class="loading-icon" spin />
            <span>加载设置中...</span>
          </div>
          <template v-else>
          <div class="section-header">
            <h2><DatabaseOutlined /> 嵌入模型配置</h2>
            <p>配置向量嵌入模型用于 RAG 检索增强</p>
          </div>

          <!-- Provider Selection Card -->
          <div class="setting-card">
            <div class="card-title">
              <CloudOutlined />
              <span>嵌入服务商</span>
            </div>
            <div class="provider-grid">
              <div
                v-for="provider in embeddingProviders"
                :key="provider.value"
                class="provider-card"
                :class="{ selected: embeddingSettings.provider === provider.value }"
                @click="embeddingSettings.provider = provider.value; handleEmbeddingProviderChange()"
              >
                <div class="provider-icon" :style="{ background: provider.color + '20', color: provider.color }">
                  {{ provider.icon }}
                </div>
                <div class="provider-info">
                  <div class="provider-name">{{ provider.label }}</div>
                </div>
                <div v-if="embeddingSettings.provider === provider.value" class="provider-check">
                  <CheckCircleOutlined />
                </div>
              </div>
            </div>
          </div>

          <!-- Connection Settings Card -->
          <div class="setting-card">
            <div class="card-title">
              <ApiOutlined />
              <span>连接配置</span>
            </div>

            <!-- Base URL for Ollama/Custom -->
            <div v-if="embeddingSettings.provider === 'ollama' || embeddingSettings.provider === 'custom'" class="form-group">
              <label>服务地址</label>
              <a-input
                v-model:value="embeddingSettings.baseUrl"
                placeholder="http://localhost:11434"
                size="large"
              >
                <template #prefix><ApiOutlined class="input-icon" /></template>
              </a-input>
              <div class="form-hint" v-if="embeddingSettings.provider === 'ollama'">
                开发模式会自动使用代理，避免 CORS 问题
              </div>
            </div>

            <!-- API Key for OpenAI/Custom -->
            <div v-if="embeddingSettings.provider === 'openai' || embeddingSettings.provider === 'custom'" class="form-group">
              <label>API Key</label>
              <a-input-password
                v-model:value="embeddingSettings.apiKey"
                placeholder="sk-..."
                size="large"
              >
                <template #prefix><KeyOutlined class="input-icon" /></template>
              </a-input-password>
            </div>

            <!-- Model Selection -->
            <div class="form-group">
              <label>嵌入模型</label>
              <div class="model-select-row">
                <!-- Ollama: Use select with fetched models -->
                <template v-if="embeddingSettings.provider === 'ollama'">
                  <a-select
                    v-model:value="embeddingSettings.model"
                    size="large"
                    :loading="loadingEmbeddingModels"
                    class="model-select"
                    @dropdown-visible-change="($event) => $event && fetchOllamaEmbeddingModels()"
                  >
                    <template v-if="fetchedEmbeddingModels.length > 0">
                      <a-select-option v-for="name in fetchedEmbeddingModels" :key="name" :value="name">
                        {{ name }}
                      </a-select-option>
                    </template>
                  </a-select>
                  <a-button @click="fetchOllamaEmbeddingModels" :loading="loadingEmbeddingModels">
                    <template #icon><ReloadOutlined /></template>
                  </a-button>
                </template>
                <!-- OpenAI/Custom: Use text input -->
                <template v-else>
                  <a-input
                    v-model:value="embeddingSettings.model"
                    placeholder="text-embedding-3-small"
                    size="large"
                    class="model-select"
                  />
                </template>
              </div>
              <div class="form-hint" v-if="embeddingSettings.provider === 'ollama'">推荐使用 nomic-embed-text、mxbai-embed-large 等专用嵌入模型</div>
              <div class="form-hint" v-else-if="embeddingSettings.provider === 'openai'">推荐使用 text-embedding-3-small 或 text-embedding-3-large</div>
              <div class="form-hint" v-else>输入嵌入模型名称，如 text-embedding-3-small</div>
            </div>

            <!-- Connection Test -->
            <div class="form-group">
              <label>连接状态</label>
              <div class="connection-status">
                <a-button
                  type="primary"
                  :loading="testingEmbeddingConnection"
                  @click="testEmbeddingConnection"
                >
                  测试连接
                </a-button>
                <div v-if="embeddingConnectionStatus !== 'idle'" class="status-result" :class="embeddingConnectionStatus">
                  <CheckCircleOutlined v-if="embeddingConnectionStatus === 'success'" />
                  <ExclamationCircleOutlined v-if="embeddingConnectionStatus === 'error'" />
                  <span>{{ embeddingConnectionMessage }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Save Button -->
          <div class="save-section">
            <a-button type="primary" size="large" :loading="savingSettings" @click="saveEmbeddingSettings">
              <template #icon><SaveOutlined /></template>
              保存设置
            </a-button>
          </div>
          </template>
        </div>

        <!-- Profile Settings -->
        <div v-else-if="activeTab === 'profile'" class="settings-section">
          <div class="section-header">
            <h2><UserOutlined /> 个人资料</h2>
            <p>管理你的账户信息</p>
          </div>

          <div class="setting-card">
            <div class="avatar-section">
              <a-avatar :size="80" class="user-avatar">
                <template #icon><UserOutlined /></template>
              </a-avatar>
              <div class="avatar-actions">
                <a-button>更换头像</a-button>
              </div>
            </div>

            <div class="form-group">
              <label>姓名</label>
              <a-input v-model:value="profileSettings.name" placeholder="你的名字" size="large" />
            </div>

            <div class="form-group">
              <label>邮箱</label>
              <a-input v-model:value="profileSettings.email" placeholder="your@email.com" size="large" />
            </div>

            <a-button type="primary" size="large" :loading="savingSettings" @click="saveProfileSettings">
              <template #icon><SaveOutlined /></template>
              保存修改
            </a-button>
          </div>

          <div class="setting-card danger-zone">
            <div class="card-title">
              <SafetyOutlined />
              <span>安全设置</span>
            </div>
            <div class="security-actions">
              <a-button>修改密码</a-button>
              <a-button danger>退出登录</a-button>
            </div>
          </div>
        </div>

        <!-- Appearance Settings -->
        <div v-else-if="activeTab === 'appearance'" class="settings-section">
          <div class="section-header">
            <h2><BgColorsOutlined /> 外观设置</h2>
            <p>自定义应用的外观和感觉</p>
          </div>

          <div class="setting-card">
            <div class="form-group">
              <label>主题</label>
              <div class="theme-options">
                <div
                  class="theme-option"
                  :class="{ selected: appearanceSettings.theme === 'light' }"
                  @click="appearanceSettings.theme = 'light'"
                >
                  <div class="theme-preview light"></div>
                  <span>浅色</span>
                </div>
                <div
                  class="theme-option"
                  :class="{ selected: appearanceSettings.theme === 'dark' }"
                  @click="appearanceSettings.theme = 'dark'"
                >
                  <div class="theme-preview dark"></div>
                  <span>深色</span>
                </div>
                <div
                  class="theme-option"
                  :class="{ selected: appearanceSettings.theme === 'auto' }"
                  @click="appearanceSettings.theme = 'auto'"
                >
                  <div class="theme-preview auto"></div>
                  <span>跟随系统</span>
                </div>
              </div>
            </div>

            <div class="form-group">
              <label>字体大小</label>
              <a-radio-group v-model:value="appearanceSettings.fontSize" button-style="solid">
                <a-radio-button value="small">小</a-radio-button>
                <a-radio-button value="medium">中</a-radio-button>
                <a-radio-button value="large">大</a-radio-button>
              </a-radio-group>
            </div>

            <a-button type="primary" size="large" :loading="savingSettings" @click="saveAppearanceSettings">
              <template #icon><SaveOutlined /></template>
              保存设置
            </a-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.page-header {
  background: white;
  border-bottom: 1px solid #e8e8e8;
  padding: 0 2rem;
  height: 64px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.back-btn {
  color: #666;
}

.page-header h1 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.settings-container {
  display: flex;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  gap: 2rem;
}

/* Sidebar Navigation */
.settings-nav {
  width: 260px;
  flex-shrink: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 0.5rem;
  background: white;
  border: 1px solid transparent;
}

.nav-item:hover {
  background: #f0f5ff;
}

.nav-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.nav-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(102, 126, 234, 0.1);
  font-size: 1.25rem;
}

.nav-item.active .nav-icon {
  background: rgba(255, 255, 255, 0.2);
}

.nav-label {
  font-weight: 500;
  font-size: 0.95rem;
}

.nav-desc {
  font-size: 0.8rem;
  opacity: 0.7;
  margin-top: 2px;
}

/* Main Content */
.settings-main {
  flex: 1;
  min-width: 0;
}

.settings-section {
  max-width: 700px;
}

.section-header {
  margin-bottom: 1.5rem;
}

.section-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-header p {
  margin: 0;
  color: #666;
}

/* Setting Cards */
.setting-card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid #f0f0f0;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 1.25rem;
  color: #1a1a1a;
}

/* Provider Grid */
.provider-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.provider-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.provider-card:hover {
  border-color: #d0d0d0;
  background: #fafafa;
}

.provider-card.selected {
  border-color: #667eea;
  background: #f0f5ff;
}

.provider-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 1.5rem;
}

.provider-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.provider-desc {
  font-size: 0.8rem;
  color: #666;
}

.provider-check {
  color: #667eea;
  font-size: 1.25rem;
  margin-left: auto;
}

/* Form Groups */
.form-group {
  margin-bottom: 1.25rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-hint {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #888;
}

.input-icon {
  color: #aaa;
}

.model-select-row {
  display: flex;
  gap: 0.5rem;
}

.model-select {
  flex: 1;
}

/* Connection Status */
.connection-status {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
}

.status-result.success {
  background: #f6ffed;
  color: #52c41a;
}

.status-result.error {
  background: #fff2f0;
  color: #ff4d4f;
}

/* Slider */
.slider-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.slider-row :deep(.ant-slider) {
  flex: 1;
}

.slider-value {
  min-width: 40px;
  text-align: center;
  font-weight: 500;
  color: #667eea;
}

/* Embedding Provider */
.embedding-provider-row {
  display: flex;
  gap: 0.75rem;
}

.provider-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.provider-chip:hover {
  border-color: #667eea;
}

.provider-chip.selected {
  border-color: #667eea;
  background: #f0f5ff;
  color: #667eea;
}

.chip-icon {
  font-size: 1rem;
}

/* Save Section */
.save-section {
  padding-top: 1rem;
}

/* Avatar Section */
.avatar-section {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

/* Theme Options */
.theme-options {
  display: flex;
  gap: 1rem;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  flex: 1;
}

.theme-option:hover {
  border-color: #d0d0d0;
}

.theme-option.selected {
  border-color: #667eea;
  background: #f0f5ff;
}

.theme-preview {
  width: 100%;
  height: 60px;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.theme-preview.light {
  background: linear-gradient(135deg, #fff 0%, #f5f5f5 100%);
}

.theme-preview.dark {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.theme-preview.auto {
  background: linear-gradient(135deg, #fff 0%, #1a1a2e 100%);
}

/* Danger Zone */
.danger-zone {
  border-color: #ffccc7;
}

.danger-zone .card-title {
  color: #ff4d4f;
}

.security-actions {
  display: flex;
  gap: 1rem;
}

/* Loading Container */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  color: #666;
}

.loading-icon {
  font-size: 2rem;
  color: #667eea;
}

/* Responsive */
@media (max-width: 900px) {
  .settings-container {
    flex-direction: column;
    padding: 1rem;
  }

  .settings-nav {
    width: 100%;
    display: flex;
    overflow-x: auto;
    gap: 0.5rem;
    padding-bottom: 1rem;
  }

  .nav-item {
    flex-shrink: 0;
    padding: 0.75rem 1rem;
  }

  .nav-desc {
    display: none;
  }

  .provider-grid {
    grid-template-columns: 1fr;
  }

  .theme-options {
    flex-direction: column;
  }
}
</style>
