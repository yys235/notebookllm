<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const formRef = ref()

const formState = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const rules = {
  name: [
    { required: true, message: 'Please input your name', trigger: 'blur' as const },
    { min: 2, message: 'Name must be at least 2 characters', trigger: 'blur' as const },
  ],
  email: [
    { required: true, message: 'Please input your email', trigger: 'blur' as const },
    { type: 'email' as const, message: 'Please enter a valid email', trigger: 'blur' as const },
  ],
  password: [
    { required: true, message: 'Please input your password', trigger: 'blur' as const },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' as const },
    {
      pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      message: 'Password must contain uppercase, lowercase, and number',
      trigger: 'blur' as const,
    },
  ],
  confirmPassword: [
    { required: true, message: 'Please confirm your password', trigger: 'blur' as const },
    {
      validator: (_rule: any, value: string) => {
        if (value !== formState.password) {
          return Promise.reject('Passwords do not match')
        }
        return Promise.resolve()
      },
      trigger: 'blur' as const,
    },
  ],
}

const handleRegister = async () => {
  try {
    await formRef.value.validate()
    loading.value = true

    const response = await authApi.register({
      name: formState.name,
      email: formState.email,
      password: formState.password,
    })
    // Response interceptor already unwraps axios response
    if (response.access_token) {
      userStore.setToken(response.access_token)
      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token)
      }
    }
    message.success('Registration successful')
    router.push('/notes')
  } catch (error: any) {
    if (error.errorFields) {
      return
    }
    message.error(error.message || 'Registration failed')
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}

const passwordStrength = computed(() => {
  const pwd = formState.password
  if (!pwd) return { score: 0, text: '', color: '' }

  let score = 0
  if (pwd.length >= 8) score++
  if (pwd.length >= 12) score++
  if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score++
  if (/\d/.test(pwd)) score++
  if (/[^a-zA-Z0-9]/.test(pwd)) score++

  const levels = [
    { text: 'Weak', color: '#ff4d4f' },
    { text: 'Fair', color: '#faad14' },
    { text: 'Good', color: '#1890ff' },
    { text: 'Strong', color: '#52c41a' },
  ]

  return {
    score: Math.min(score, 4),
    ...levels[Math.min(score - 1, 3)],
  }
})
</script>

<template>
  <div class="register-container">
    <div class="register-background"></div>
    <div class="register-content">
      <div class="register-card">
        <div class="logo-section">
          <div class="logo">
            <span class="logo-icon">N</span>
          </div>
          <h1>Create Account</h1>
          <p class="subtitle">Join NotebookLLM and start organizing your notes with AI</p>
        </div>

        <a-form
          ref="formRef"
          :model="formState"
          :rules="rules"
          layout="vertical"
          class="register-form"
        >
          <a-form-item label="Full Name" name="name">
            <a-input
              v-model:value="formState.name"
              placeholder="Enter your full name"
              size="large"
            >
              <template #prefix>
                <UserOutlined class="input-icon" />
              </template>
            </a-input>
          </a-form-item>

          <a-form-item label="Email" name="email">
            <a-input
              v-model:value="formState.email"
              placeholder="Enter your email"
              size="large"
            >
              <template #prefix>
                <MailOutlined class="input-icon" />
              </template>
            </a-input>
          </a-form-item>

          <a-form-item label="Password" name="password">
            <a-input-password
              v-model:value="formState.password"
              placeholder="Create a password"
              size="large"
            >
              <template #prefix>
                <LockOutlined class="input-icon" />
              </template>
            </a-input-password>
            <div v-if="formState.password" class="password-strength">
              <div class="strength-bar">
                <div
                  v-for="i in 4"
                  :key="i"
                  class="strength-segment"
                  :class="{ active: i <= passwordStrength.score }"
                  :style="{
                    backgroundColor: i <= passwordStrength.score ? passwordStrength.color : ''
                  }"
                />
              </div>
              <span class="strength-text" :style="{ color: passwordStrength.color }">
                Password strength: {{ passwordStrength.text || 'Too weak' }}
              </span>
            </div>
          </a-form-item>

          <a-form-item label="Confirm Password" name="confirmPassword">
            <a-input-password
              v-model:value="formState.confirmPassword"
              placeholder="Confirm your password"
              size="large"
            >
              <template #prefix>
                <LockOutlined class="input-icon" />
              </template>
            </a-input-password>
          </a-form-item>

          <a-form-item>
            <a-checkbox>
              I agree to the <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>
            </a-checkbox>
          </a-form-item>

          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              size="large"
              block
              :loading="loading"
              @click="handleRegister"
            >
              Create Account
            </a-button>
          </a-form-item>
        </a-form>

        <div class="login-link">
          Already have an account?
          <a @click="goToLogin">Sign in</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { computed } from 'vue'
export default {
  setup() {
    return { computed }
  },
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.register-background {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  z-index: 0;
}

.register-background::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
}

.register-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  padding: 2rem;
}

.register-card {
  background: white;
  border-radius: 16px;
  padding: 2.5rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.logo-section {
  text-align: center;
  margin-bottom: 2rem;
}

.logo {
  width: 60px;
  height: 60px;
  margin: 0 auto 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
}

.logo-section h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a1a1a;
}

.subtitle {
  margin: 0.5rem 0 0;
  color: #666;
  font-size: 0.9rem;
}

.register-form {
  margin-top: 2rem;
}

:deep(.input-icon) {
  color: rgba(0, 0, 0, 0.25);
}

.password-strength {
  margin-top: 0.5rem;
}

.strength-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 0.25rem;
}

.strength-segment {
  flex: 1;
  height: 4px;
  background: #f0f0f0;
  border-radius: 2px;
  transition: all 0.3s;
}

.strength-segment.active {
  transition: all 0.3s;
}

.strength-text {
  font-size: 0.75rem;
}

.login-link {
  text-align: center;
  margin-top: 1.5rem;
  color: #666;
}

.login-link a {
  color: #667eea;
  font-weight: 500;
  margin-left: 0.25rem;
  transition: color 0.2s;
}

.login-link a:hover {
  color: #764ba2;
}

/* Responsive */
@media (max-width: 480px) {
  .register-content {
    padding: 1rem;
  }

  .register-card {
    padding: 1.5rem;
    border-radius: 12px;
  }
}
</style>
