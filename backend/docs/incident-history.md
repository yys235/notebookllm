# 开发日志

## 2026-03-16

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

