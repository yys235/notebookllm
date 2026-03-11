<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loading = ref(false)
const formRef = ref()

const formState = reactive({
  username: '',
  password: '',
  remember: true,
})

const rules = {
  username: [
    { required: true, message: 'Please input your username or email', trigger: 'blur' as const },
  ],
  password: [
    { required: true, message: 'Please input your password', trigger: 'blur' as const },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' as const },
  ],
}

const handleLogin = async () => {
  try {
    await formRef.value.validate()
    loading.value = true

    const response = await authApi.login({
      username: formState.username,
      password: formState.password,
    })

    // Backend returns: { access_token, refresh_token, token_type, expires_in }
    // Response interceptor already unwraps axios response
    const { access_token, refresh_token } = response
    userStore.setToken(access_token)

    // Store refresh token
    if (refresh_token) {
      localStorage.setItem('refreshToken', refresh_token)
    }

    message.success('Login successful')

    const redirect = (route.query.redirect as string) || '/notes'
    router.push(redirect)
  } catch (error: any) {
    if (error.errorFields) {
      return
    }
    const errorMsg = error?.detail || error?.message || 'Login failed'
    message.error(errorMsg)
  } finally {
    loading.value = false
  }
}

const goToRegister = () => {
  router.push('/register')
}

const forgotPassword = () => {
  message.info('Password reset functionality coming soon')
}
</script>

<template>
  <div class="login-container">
    <div class="login-background"></div>
    <div class="login-content">
      <div class="login-card">
        <div class="logo-section">
          <div class="logo">
            <span class="logo-icon">N</span>
          </div>
          <h1>NotebookLLM</h1>
          <p class="subtitle">AI-powered note-taking with intelligent search</p>
        </div>

        <a-form
          ref="formRef"
          :model="formState"
          :rules="rules"
          layout="vertical"
          class="login-form"
        >
          <a-form-item label="Username or Email" name="username">
            <a-input
              v-model:value="formState.username"
              placeholder="Enter your username or email"
              size="large"
            >
              <template #prefix>
                <UserOutlined class="input-icon" />
              </template>
            </a-input>
          </a-form-item>

          <a-form-item label="Password" name="password">
            <a-input-password
              v-model:value="formState.password"
              placeholder="Enter your password"
              size="large"
            >
              <template #prefix>
                <LockOutlined class="input-icon" />
              </template>
            </a-input-password>
          </a-form-item>

          <div class="form-actions">
            <a-checkbox v-model:checked="formState.remember">Remember me</a-checkbox>
            <a class="forgot-link" @click="forgotPassword">Forgot password?</a>
          </div>

          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              size="large"
              block
              :loading="loading"
              @click="handleLogin"
            >
              Sign In
            </a-button>
          </a-form-item>
        </a-form>

        <div class="register-link">
          Don't have an account?
          <a @click="goToRegister">Sign up</a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-background {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  z-index: 0;
}

.login-background::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
}

.login-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 2rem;
}

.login-card {
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

.login-form {
  margin-top: 2rem;
}

:deep(.input-icon) {
  color: rgba(0, 0, 0, 0.25);
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.forgot-link {
  color: #667eea;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: #764ba2;
}

.register-link {
  text-align: center;
  margin-top: 1.5rem;
  color: #666;
}

.register-link a {
  color: #667eea;
  font-weight: 500;
  margin-left: 0.25rem;
  transition: color 0.2s;
}

.register-link a:hover {
  color: #764ba2;
}

/* Responsive */
@media (max-width: 480px) {
  .login-content {
    padding: 1rem;
  }

  .login-card {
    padding: 1.5rem;
    border-radius: 12px;
  }
}
</style>
