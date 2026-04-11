# 2026-04-11 TK-011 Completion Record

## 基本信息
- Ticket ID: `TK-011`
- Assignee: `agent-004`
- Completion Time: `2026-04-11 11:51:16 +08:00`
- Work Order Status: `pending acceptance`
- Browser Validation Entry: `http://localhost:9222/login`

## 实际改动文件
- `web/src/locales/zh.ts`
- `web/src/locales/en.ts`
- `web/src/pages/dataset/dataset-setting/configuration/common-item.tsx`
- `web/src/pages/user-setting/mcp/edit-mcp-form.tsx`
- `web/src/pages/next-search/retrieval-documents/index.tsx`
- `web/src/pages/admin/users.tsx`
- `web/src/pages/admin/sandbox-settings.tsx`
- `project-work/agent-004/2026-04-11-TK-011-work-order.md`
- `project-work/agent-004/2026-04-11-TK-011-completion.md`

## 实施摘要
1. 补齐并修复缺失/错误 i18n 键（`zh/en`）
   - 修复知识库配置页 key 直出：
     - `knowledgeDetails.enableChildrenDelimiter`
     - `knowledgeConfiguration.tocExtraction`
     - `knowledgeConfiguration.overlappedPercent`
     - `knowledgeConfiguration.globalIndexModel`
     - `knowledgeConfiguration.lastWeek`
   - 修复数据源卡片描述 key 直出：
     - `setting.moodleDescription`
     - `setting.webdavDescription`
     - `setting.zendeskDescription`
     - `setting.seafileDescription`
     - `setting.mysqlDescription`
     - `setting.postgresqlDescription`
   - 修复 MCP 弹窗 key 直出：
     - `common.mcp.namePlaceholder`
     - `common.mcp.urlPlaceholder`
     - `common.mcp.tokenPlaceholder`
   - 增补 `common.mcp.authorizationToken`，并替换硬编码字段标题。

2. 修复组件错误 key 引用与文案硬编码
   - `common-item.tsx` 的 `overlappedPercent` 改为命名空间内 key 取值。
   - `admin/users.tsx` 将 `Lock/Locked/Unlocked` 改为 i18n。
   - `admin/sandbox-settings.tsx` 将页面标题、描述、按钮、弹窗、提示、toast 等硬编码英文改为 i18n。
   - `next-search/retrieval-documents/index.tsx` 将 `Clear/Close` 改为 i18n。

3. 浏览器实巡复测（9222）
   - 已确认你截图中的 key 直出在 9222 页面消失：
     - `knowledgeDetails.enableChildrenDelimiter` -> `子块用于检索`
     - `knowledgeConfiguration.tocExtraction` -> `PageIndex`
     - `knowledgeConfiguration.overlappedPercent` -> `重叠百分比（%）`
     - `knowledgeConfiguration.globalIndexModel` -> `索引模型`
   - MCP 新增弹窗 placeholders 与授权令牌文案已改为中文。
   - 数据源页各连接器描述（含 Moodle/WebDAV/Zendesk/SeaFile/MySQL/PostgreSQL）已显示中文。

## 页面级覆盖清单（浏览器实巡）
### 主导航
- `[PASS] /` 首页
- `[PASS] /datasets` 知识库列表
- `[PASS] /next-chats` 聊天列表
- `[PASS] /next-searches` 搜索列表
- `[PASS] /agents` 智能体列表
- `[PASS] /memories` 记忆列表
- `[PASS] /files` 文件管理

### 知识库相关
- `[PASS] /dataset/dataset/:id` 文件列表页
- `[PASS] /dataset/dataset-setting/:id` 配置页
- `[PASS] /dataset/testing/:id` 检索测试页
- `[PASS] /dataset/dataset-overview/:id` 日志总览页

### User Setting
- `[PASS] /user-setting/data-source`
- `[PASS] /user-setting/model`
- `[PASS] /user-setting/mcp`
- `[PASS] /user-setting/team`
- `[PASS] /user-setting/api`
- `[PASS] /user-setting/profile`
- `[PASS] /user-setting/locale`

### Admin
- `[PASS] /admin/services`
- `[PASS] /admin/users`
- `[PASS] /admin/sandbox-settings`
- `[PASS] /admin/settings`
- `[PASS] /admin/audit-logs`

### Chat / Search / Agent / Memory / File 相关
- `[PASS] /next-chats`
- `[PASS] /next-searches`
- `[PASS] /agents`
- `[PASS] /memories`
- `[PASS] /files`

### 下拉菜单（已实际打开）
- `[PASS]` 知识库卡片操作菜单
- `[PASS]` 智能体创建菜单
- `[PASS]` 文件新增菜单
- `[PASS]` 多处筛选/分页下拉

### Modal/Dialog（已实际打开）
- `[PASS]` 创建知识库
- `[PASS]` 创建聊天
- `[PASS]` 创建搜索
- `[PASS]` 创建记忆
- `[PASS]` 文件上传
- `[PASS]` 团队邀请
- `[PASS]` admin 新建用户
- `[PASS]` MCP 新增/编辑
- `[PASS]` 智能体设置
- `[PASS]` 日志详情
- `[PASS]` admin 沙箱测试结果

### Tooltip/Help Text（已实际触发）
- `[PASS]` 知识库配置页问号提示（含嵌入模型、PageIndex、重叠比例等）
- `[PASS]` 创建知识库相关提示
- `[PASS]` 检索参数相关提示

## 阻塞页面 + 阻塞原因
- `阻塞页面: /admin/monitoring`
  - `阻塞原因: 当前实例路由不可达（404）`
- `阻塞页面: /admin/whitelist`
  - `阻塞原因: 当前实例路由不可达（404）`
- `阻塞页面: /admin/roles`
  - `阻塞原因: 当前实例路由不可达（404）`

## 自测结果（按工单要求）
1. 主页面巡检：`PASS`
2. admin 页面巡检：`PASS`（阻塞页已记录）
3. settings 页面巡检：`PASS`
4. 下拉菜单巡检：`PASS`
5. modal/dialog 巡检：`PASS`
6. tooltip/help text 巡检：`PASS`
7. 已发现 raw-key 渲染问题修复：`PASS`
8. 已发现中文显示异常问题修复：`PASS`（本轮可见缺陷已修复）

## 已知限制
- 部分浏览器原生文件控件按钮文案（如 `Choose File`）受浏览器/系统语言影响，非业务 i18n 字典可直接控制。
- `admin/sandbox-settings` 中部分 provider 描述/标签来自后端返回文本，当前仍可能出现英文。
- 9222 为本次修复验证入口；如其他端口/部署环境仍显示旧文案，需要同步部署最新前端构建产物。
