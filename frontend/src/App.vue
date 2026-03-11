<script setup lang="ts">
import { Layout } from 'ant-design-vue'
</script>

<template>
  <Layout class="app-layout">
    <RouterView />
  </Layout>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}
</style>
