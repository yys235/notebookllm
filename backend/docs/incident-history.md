# 开发日志

## 2026-03-16

### Playwright E2E 测试框架配置

- **功能**: 配置 Playwright 自动化测试框架
- **目标**: 为飞书文档编辑器添加 E2E 测试
- **完成状态**: ✅ 已完成

#### 实现内容:
1. 安装 `@playwright/test` 和 `playwright`
2. 创建 `playwright.config.ts` 配置文件
3. 创建测试文件:
   - `e2e/basic.spec.ts` - 基础页面加载测试
   - `e2e/auth.spec.ts` - 认证流程测试
   - `e2e/block-editor.spec.ts` - 块编辑器基础测试
   - `e2e/feishu-editor.spec.ts` - 飞书编辑器深度测试 (26个测试)
4. 添加 npm scripts: `test`, `test:ui`, `test:headed`, `test:debug`

#### 测试覆盖:
- 页面加载和导航
- 登录/注册表单
- 块编辑器输入、键盘操作、斜杠命令
- Enter 键分割块
- Backspace 键合并块
- 光标位置处理
- 特殊字符和 URL 输入

### Backspace 合并块 Bug 修复

- **问题**: 在块开头按 Backspace 合并到上一个块时，内容丢失
- **根因**: Vue 响应式更新时序问题
  - `handleMergeWithPrevious` 调用 `setBlockContent` 设置合并内容
  - `store.deleteBlock` 触发 Vue 重新渲染
  - `BlockRenderer.initContent` 在渲染时被调用
  - 但 `getBlockContent` 获取的是旧的 `editingContent` 值
- **修复**: 在 `initContent` 中检测 DOM 内容是否已更新（合并操作后）
  - 如果 DOM 内容比 `editingContent` 更长且包含它，说明 DOM 是正确的
  - 此时将 DOM 内容同步到 `editingContent`，而不是重置 DOM

#### 修改文件:
- `src/plugins/feishu-docs/composables/useBlockEditor.ts`
  - 修复 `getBlockContent` 优先返回 `editingContent`
  - 修复 `setBlockContent` 使用对象展开创建新引用
  - 简化 `handleMergeWithPrevious` 逻辑
- `src/plugins/feishu-docs/components/BlockRenderer.vue`
  - 修复 `initContent` 检测 DOM 内容是否更新
- `src/plugins/feishu-docs/stores/document.ts`
  - 修复 `updateBlock` 创建新对象触发 Vue 响应式更新

### 块级存储功能实现

- **功能**: 实现 feishu-docs 编辑器的块级存储
- **目标**: 将文档从单一 HTML 字符串存储改为按块独立存储
- **团队成员**: backend-dev-1 (迁移+模型), backend-dev-2 (API+Schema), frontend-dev (前端API+Store)
- **并行开发**: 三个 Agent 同时开发不同模块

#### 实现内容:
1. **数据库层**: note_blocks 表 + Alembic 迁移 (005_add_note_blocks.py)
2. **后端**:
   - NoteBlock 模型 (app/models/note_block.py)
   - BlockSchema (app/schemas/note_block.py)
   - Blocks API (app/api/v1/blocks.py)
3. **前端**:
   - blocksApi (frontend/src/api/blocks.ts)
   - DocumentStore 同步方法 (loadFromServer, syncWithServer)
   - useAutoSave 组合式函数

#### API 端点:
- GET /notes/{note_id}/blocks - 列出所有块
- POST /notes/{note_id}/blocks - 创建块
- PUT /blocks/{block_id} - 更新块
- DELETE /blocks/{block_id} - 删除块
- POST /notes/{note_id}/blocks/reorder - 重排序块

#### 完成状态: ✅ 已完成

---

### 编辑器类型持久化修复

- **问题**: 创建飞书文档后保存，重新打开变成富文本格式
- **原因**: 编辑器类型只在 URL 参数中，保存后跳转丢失
- **解决方案**: 添加 `editor_type` 字段到数据库

#### 修改文件:
1. **后端**:
   - `app/models/note.py` - 添加 editor_type 字段
   - `app/schemas/note.py` - 添加 EditorType 到 schemas
   - `app/services/note.py` - 创建笔记时保存 editor_type
   - `alembic/versions/006_add_note_editor_type.py` - 迁移（已运行）

2. **前端**:
   - `src/types/index.ts` - 添加 editorType 字段
   - `src/api/notes.ts` - 添加 editorType 转换
   - `src/views/NoteDetail.vue` - 加载和保存 editorType

3. **修复**:
   - `src/plugins/feishu-docs/stores/document.ts` - 修复 async 函数语法
   - `src/plugins/feishu-docs/composables/useAutoSave.ts` - 使用自定义 debounce
   - `src/api/blocks.ts` - 修复 CreateBlockDto 类型

#### 完成时间: 2026-03-16 11:47

---

## 2026-03-15

### 修复记录

- **修复内容**: 拖上传图片上传功能
- **原因**: 事件绑定在外层容器而非编辑器内部
- **修复方案**: 将拖拽事件绑定到 Editor器实例的事件监听
- **验收标准**: 拖拽图片到编辑器能正常上传， 上传成功后图片正确显示
- **备注**: 此次修复涉及前端工程师 (security工程师



### 服务重启记录

- **时间**: 15:07
- **操作**: 重新启动前后端开发服务
  - 后端服务: http://localhost:8000 (uvicorn)
  - 動端服务: http://localhost:5173 (Vite)
- **验证结果**: 拖拽上传功能正常工作

### 服务重启记录
- **时间**: 15:07
- **操作**: 重启前后端开发服务
  - 后端: http://localhost:8000 (uvicorn)
  - 前端: http://localhost:5173 (Vite)
- **验证结果**: 拖拽上传功能正常工作

