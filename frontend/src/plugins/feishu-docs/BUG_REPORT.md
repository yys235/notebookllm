# 飞书文档编辑器 Bug 报告

## 测试日期: 2026-03-13

## 已修复的 Bug

### Bug #1: slashCommands 中 editor.focusedBlockId 未定义 ✅ 已修复

**位置**: `/src/plugins/feishu-docs/composables/useBlockEditor.ts`

**修复内容**:
- 在 useBlockEditor 返回对象中添加 `focusedBlockId: computed(() => store.focusedBlockId)`

---

### Bug #2: 斜杠命令菜单选择后没有正确执行 ✅ 已修复

**位置**: `/src/plugins/feishu-docs/FeishuDocsEditor.vue`

**修复内容**:
- 添加 `handleSlashCommandSelect` 函数
- 执行命令前清除斜杠命令文本
- 正确调用 `cmd.action(editor)`

---

### Bug #3: 输入字母反向 ✅ 已修复

**位置**: `/src/plugins/feishu-docs/components/BlockRenderer.vue`

**原因**: Vue 响应式更新与 contenteditable 冲突

**修复内容**:
- 移除所有 `{{ blockContent }}` 模板插值
- 使用 `ref` 引用 DOM 元素
- 通过 `initContent` 函数初始化内容
- 只在外部更新且元素未聚焦时更新 DOM

---

### Bug #4: 拖拽功能无效 ✅ 已修复

**位置**: `/src/plugins/feishu-docs/components/BlockRenderer.vue`

**修复内容**:
1. 添加完整的拖拽事件处理：
   - `handleDragStart` - 开始拖拽
   - `handleDragEnd` - 拖拽结束
   - `handleDragEnter` - 拖拽进入
   - `handleDragLeave` - 拖拽离开
   - `handleDragOver` - 拖拽悬停
   - `handleDrop` - 放下

2. 使用全局变量存储拖拽块 ID（解决 dragover 无法读取 dataTransfer 的问题）

3. 修复 `moveBlock` 函数的索引计算问题：
   - 先计算目标位置
   - 再从原位置移除
   - 处理索引偏移问题

---

### Bug #5: 拖拽无位置预览 ✅ 已修复

**位置**: `/src/plugins/feishu-docs/components/BlockRenderer.vue`

**修复内容**:
- 添加拖拽位置指示器 `<div class="drag-indicator">`
- 根据鼠标位置显示不同放置位置：
  - `drag-before` - 上方蓝线
  - `drag-after` - 下方蓝线
  - `drag-child` - 蓝色背景

---

### Bug #6: 正文区域消失 ✅ 已修复

**位置**: `/src/plugins/feishu-docs/stores/document.ts` 和 `BlockRenderer.vue`

**原因**: `store.dragState` 未定义但在组件中被引用

**修复内容**:
1. 从 store 的 return 语句中移除未定义的 `isDragging`
2. 移除 BlockRenderer.vue 中所有 `store.dragState` 引用
3. 使用局部状态 `isDragging` 和 `isDragOver` ref 替代 store 状态

---

## 当前测试清单

### 基础功能
- [x] 创建飞书文档
- [x] 输入文本正常显示
- [ ] 中文输入（IME 兼容性）
- [ ] 页面刷新后内容保持

### 块操作
- [ ] Enter 创建新块
- [ ] Backspace 删除空块
- [ ] Tab 缩进
- [ ] 上下键导航

### 斜杠命令
- [ ] 输入 `/` 打开菜单
- [ ] 搜索过滤命令
- [ ] 选择执行命令

### 拖拽功能
- [ ] 拖拽手柄显示
- [ ] 拖拽开始效果
- [ ] 拖拽位置指示器显示
- [ ] 释放后块移动到正确位置

---

## 测试环境
- **开发服务器**: http://localhost:5173/
- **构建状态**: ✅ 成功
- **TypeScript**: ✅ 无错误
