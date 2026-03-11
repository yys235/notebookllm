<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Button, Typography } from 'ant-design-vue'

const router = useRouter()

const goToNotes = () => {
  router.push('/notes')
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<template>
  <div class="home-container">
    <div class="hero-section">
      <Typography.Title :level="1">NotebookLLM</Typography.Title>
      <Typography.Paragraph class="subtitle">
        AI-powered note-taking with intelligent search and sharing
      </Typography.Paragraph>
      <div class="action-buttons">
        <Button type="primary" size="large" @click="goToNotes">
          Get Started
        </Button>
        <Button size="large" @click="goToLogin">
          Sign In
        </Button>
      </div>
    </div>
    <div class="features-section">
      <div class="feature-card">
        <Typography.Title :level="3">Smart Notes</Typography.Title>
        <Typography.Paragraph>
          Create and organize your notes with a clean, intuitive interface
        </Typography.Paragraph>
      </div>
      <div class="feature-card">
        <Typography.Title :level="3">AI Search</Typography.Title>
        <Typography.Paragraph>
          Find information instantly with powerful AI-powered search
        </Typography.Paragraph>
      </div>
      <div class="feature-card">
        <Typography.Title :level="3">Easy Sharing</Typography.Title>
        <Typography.Paragraph>
          Share your notes securely with custom links and passwords
        </Typography.Paragraph>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.hero-section {
  text-align: center;
  padding: 4rem 0;
}

.subtitle {
  font-size: 1.25rem;
  color: #666;
  margin-bottom: 2rem;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.features-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  padding: 4rem 0;
}

.feature-card {
  text-align: center;
  padding: 2rem;
  border-radius: 8px;
  background: #f5f5f5;
}
</style>
