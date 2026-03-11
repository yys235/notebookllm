<script setup lang="ts">
interface Props {
  loading?: boolean
  tip?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: true,
  tip: 'Loading...',
})
</script>

<template>
  <div v-if="loading" class="global-loading">
    <div class="loading-backdrop" />
    <div class="loading-content">
      <a-spin :tip="tip" />
    </div>
  </div>
</template>

<style scoped>
.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  pointer-events: none;
}

.loading-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
}

.loading-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
</style>
