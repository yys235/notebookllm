# 自动化测试计划

## 测试范围

### 页面覆盖
| 页面 | 路由 | 优先级 |
|------|------|--------|
| 首页 | `/` | P1 |
| 登录页 | `/login` | P0 |
| 注册页 | `/register` | P0 |
| 笔记列表 | `/notes` | P0 |
| 新建笔记 | `/notes/new` | P0 |
| 笔记详情 | `/notes/:id` | P1 |
| 笔记编辑 | `/notes/edit/:id` | P0 |
| 设置页 | `/settings` | P1 |
| 分享笔记 | `/shared/:shareId` | P2 |

### 功能模块
1. **认证模块** (auth.spec.ts)
   - 登录表单验证
   - 登录流程
   - 注册表单验证
   - 注册流程
   - 登录状态持久化
   - 登出功能
   - 路由守卫

2. **笔记列表模块** (notes-list.spec.ts)
   - 页面加载
   - 笔记卡片显示
   - 搜索功能
   - 筛选功能
   - 新建笔记入口
   - 笔记操作（编辑、删除、置顶）

3. **笔记编辑模块** (note-edit.spec.ts)
   - 页面加载
   - 标题编辑
   - 内容编辑
   - 自动保存
   - 手动保存
   - 编辑器类型选择
   - 返回导航

4. **飞书编辑器模块** (feishu-editor.spec.ts)
   - 块创建/删除
   - Enter键分割块
   - Backspace合并块
   - 光标位置
   - 斜杠命令
   - 多行文本
   - 特殊字符

5. **设置模块** (settings.spec.ts)
   - 页面加载
   - 用户信息显示
   - 设置修改

6. **首页模块** (home.spec.ts)
   - 页面加载
   - 导航链接

## 测试策略

### 测试类型
- **E2E测试**: 使用 Playwright 进行端到端测试
- **UI测试**: 验证页面元素和交互
- **功能测试**: 验证业务逻辑

### 测试环境
- 浏览器: Chromium
- 基础URL: http://localhost:5173

### Mock策略
- 使用 localStorage 模拟登录状态
- 不依赖真实后端API

## 执行计划

1. ✅ 已完成: auth.spec.ts - 认证测试
2. ✅ 已完成: basic.spec.ts - 基础测试
3. ✅ 已完成: notes-list.spec.ts - 笔记列表测试
4. ✅ 已完成: block-editor.spec.ts - 块编辑器基础测试
5. ✅ 已完成: feishu-editor.spec.ts - 飞书编辑器深度测试
6. 🔄 进行中: note-edit.spec.ts - 笔记编辑测试
7. 📝 待完成: settings.spec.ts - 设置页测试
8. 📝 待完成: home.spec.ts - 首页测试
9. 📝 待完成: navigation.spec.ts - 导航测试

## 预期结果
- 所有测试通过率: 100%
- 代码覆盖率: 关键路径覆盖
- 测试执行时间: < 3分钟
