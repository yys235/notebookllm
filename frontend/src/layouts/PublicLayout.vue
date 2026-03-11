<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goToHome() {
  router.push('/')
}

function goToLogin() {
  router.push('/login')
}

function goToRegister() {
  router.push('/register')
}
</script>

<template>
  <div class="public-layout">
    <!-- Header -->
    <header class="public-header">
      <div class="header-content">
        <div class="logo" @click="goToHome">
          <div class="logo-icon">N</div>
          <span class="logo-text">NotebookLLM</span>
        </div>

        <nav class="header-nav">
          <a @click="goToHome">Home</a>
          <a @click="goToLogin">Login</a>
          <a-button type="primary" @click="goToRegister">
            Get Started
          </a-button>
        </nav>
      </div>
    </header>

    <!-- Page Content -->
    <main class="public-content">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="public-footer">
      <div class="footer-content">
        <div class="footer-section">
          <div class="footer-logo">
            <div class="logo-icon">N</div>
            <span class="logo-text">NotebookLLM</span>
          </div>
          <p class="footer-desc">
            AI-powered note-taking with intelligent search and sharing.
          </p>
        </div>

        <div class="footer-section">
          <h4>Product</h4>
          <a href="#">Features</a>
          <a href="#">Pricing</a>
          <a href="#">Security</a>
        </div>

        <div class="footer-section">
          <h4>Company</h4>
          <a href="#">About</a>
          <a href="#">Blog</a>
          <a href="#">Careers</a>
        </div>

        <div class="footer-section">
          <h4>Support</h4>
          <a href="#">Help Center</a>
          <a href="#">Contact</a>
          <a href="#">Status</a>
        </div>
      </div>

      <div class="footer-bottom">
        <p>&copy; 2026 NotebookLLM. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.public-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.public-header {
  background: white;
  border-bottom: 1px solid #e8e8e8;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 16px;
}

.logo-text {
  font-weight: 700;
  font-size: 18px;
  color: #1a1a1a;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 32px;
}

.header-nav a {
  color: #666;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.header-nav a:hover {
  color: #667eea;
}

.public-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.public-footer {
  background: white;
  border-top: 1px solid #e8e8e8;
  margin-top: auto;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px 24px;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 48px;
}

.footer-section h4 {
  margin: 0 0 16px;
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.footer-section a {
  display: block;
  color: #666;
  text-decoration: none;
  margin-bottom: 12px;
  transition: color 0.2s;
}

.footer-section a:hover {
  color: #667eea;
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.footer-logo .logo-icon {
  width: 32px;
  height: 32px;
  font-size: 14px;
}

.footer-logo .logo-text {
  font-size: 16px;
}

.footer-desc {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.footer-bottom {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 0 16px;
  }

  .header-nav {
    gap: 16px;
  }

  .header-nav a:not(.ant-btn) {
    display: none;
  }

  .footer-content {
    grid-template-columns: 1fr;
    gap: 32px;
  }
}
</style>
