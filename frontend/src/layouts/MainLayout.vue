<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  FileTextOutlined,
  SettingOutlined,
  LogoutOutlined,
  HomeOutlined,
} from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>([])

const menuItems = [
  {
    key: 'home',
    icon: HomeOutlined,
    label: 'Home',
    path: '/',
  },
  {
    key: 'notes',
    icon: FileTextOutlined,
    label: 'Notes',
    path: '/notes',
  },
  {
    key: 'settings',
    icon: SettingOutlined,
    label: 'Settings',
    path: '/settings',
  },
]

function handleMenuClick(info: { key: string | number }) {
  const key = String(info.key)
  const item = menuItems.find((item) => item.key === key)
  if (item) {
    router.push(item.path)
  }
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

function goToSettings() {
  router.push('/settings')
}

const userName = computed(() => userStore.userName || 'User')
const userInitials = computed(() => {
  const name = userStore.userName || ''
  return name
    .split(' ')
    .map((n) => n.charAt(0))
    .join('')
    .toUpperCase()
    .substring(0, 2)
})
</script>

<template>
  <a-layout class="main-layout">
    <!-- Sidebar -->
    <a-layout-sider
      v-model:collapsed="collapsed"
      :trigger="null"
      collapsible
      class="main-sidebar"
      :collapsed-width="64"
    >
      <div class="logo-section">
        <div v-if="!collapsed" class="logo-full">
          <div class="logo-icon">N</div>
          <span class="logo-text">NotebookLLM</span>
        </div>
        <div v-else class="logo-collapsed">
          <span>N</span>
        </div>
      </div>

      <a-menu
        v-model:selected-keys="selectedKeys"
        :inline-collapsed="collapsed"
        mode="inline"
        class="sidebar-menu"
        @click="handleMenuClick"
      >
        <template v-for="item in menuItems" :key="item.key">
          <a-menu-item>
            <template #icon>
              <component :is="item.icon" />
            </template>
            <span>{{ item.label }}</span>
          </a-menu-item>
        </template>
      </a-menu>
    </a-layout-sider>

    <!-- Main Content -->
    <a-layout class="content-layout">
      <!-- Header -->
      <a-layout-header class="main-header">
        <div class="header-left">
          <a-button
            type="text"
            class="collapse-btn"
            @click="toggleCollapse"
          >
            <template #icon>
              <MenuFoldOutlined v-if="!collapsed" />
              <MenuUnfoldOutlined v-else />
            </template>
          </a-button>
        </div>

        <div class="header-right">
          <a-button type="primary" @click="$router.push('/notes/new')">
            <template #icon><FileTextOutlined /></template>
            New Note
          </a-button>

          <a-dropdown>
            <div class="user-dropdown">
            <a-avatar :size="36" class="user-avatar">
              {{ userInitials }}
            </a-avatar>
            <span v-if="!collapsed" class="user-name">{{ userName }}</span>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="goToSettings">
                  <SettingOutlined />
                  Settings
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item @click="handleLogout">
                  <LogoutOutlined />
                  Logout
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <!-- Page Content -->
      <a-layout-content class="main-content">
        <slot />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<style scoped>
.main-layout {
  min-height: 100vh;
}

.main-sidebar {
  background: white;
  border-right: 1px solid #e8e8e8;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
  transition: width 0.2s;
}

.logo-section {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid #e8e8e8;
}

.logo-full {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 14px;
}

.logo-text {
  font-weight: 700;
  font-size: 16px;
  color: #1a1a1a;
}

.logo-collapsed {
  width: 100%;
  text-align: center;
  font-weight: 700;
  font-size: 20px;
  color: #667eea;
}

.sidebar-menu {
  border-right: none;
  margin-top: 8px;
}

.content-layout {
  margin-left: 200px;
  transition: margin-left 0.2s;
}

.main-layout:has(.main-sidebar.ant-layout-sider-collapsed) ~ .content-layout {
  margin-left: 80px;
}

.main-header {
  background: white;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e8e8e8;
  position: sticky;
  top: 0;
  z-index: 99;
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 18px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-dropdown:hover {
  background: #f5f5f5;
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  flex-shrink: 0;
}

.user-name {
  font-weight: 500;
  color: #1a1a1a;
}

.main-content {
  background: #f5f5f5;
  min-height: calc(100vh - 64px);
}

/* Responsive */
@media (max-width: 768px) {
  .main-sidebar {
    position: fixed;
    transform: translateX(-100%);
  }

  .main-sidebar.ant-layout-sider-has-trigger {
    transform: translateX(0);
  }

  .content-layout {
    margin-left: 0 !important;
  }

  .user-name {
    display: none;
  }
}
</style>
