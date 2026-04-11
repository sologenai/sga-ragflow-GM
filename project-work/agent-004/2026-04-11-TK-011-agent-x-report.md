# TK-011 交付报告（给 agent-x）

## 1) 本次做了什么（Summary）
- 角色：`agent-004`
- 工单：`TK-011`（全系统中文 UI / i18n 巡检与整改）
- 验证入口：`http://localhost:9222/login`
- 结果：完成全量实巡与修复，工单状态已更新为 `pending acceptance`

### 1.1 已完成修复（核心）
1. 修复知识库配置页 key 直出
- `knowledgeDetails.enableChildrenDelimiter` -> `子块用于检索`
- `knowledgeConfiguration.tocExtraction` -> `PageIndex`
- `knowledgeConfiguration.overlappedPercent` -> `重叠百分比（%）`
- `knowledgeConfiguration.globalIndexModel` -> `索引模型`
- `knowledgeConfiguration.lastWeek` -> `最近一周`

2. 修复数据源页 key 直出（setting.*Description）
- `moodleDescription`
- `webdavDescription`
- `zendeskDescription`
- `seafileDescription`
- `mysqlDescription`
- `postgresqlDescription`

3. 修复 MCP 弹窗 key 直出
- `common.mcp.namePlaceholder`
- `common.mcp.urlPlaceholder`
- `common.mcp.tokenPlaceholder`
- 新增 `common.mcp.authorizationToken` 并替换硬编码标题

4. 修复中文模式残留英文（代码硬编码）
- `admin/users`：`Lock/Locked/Unlocked` 改为 i18n
- `admin/sandbox-settings`：页面标题、按钮、弹窗、提示、toast 等改为 i18n
- `next-search/retrieval-documents`：`Clear/Close` 改为 i18n

5. 修复组件 key 引用错误
- `dataset-setting/configuration/common-item.tsx` 中 `overlappedPercent` 改为正确命名空间取值

## 2) 实际改动文件
- `web/src/locales/zh.ts`
- `web/src/locales/en.ts`
- `web/src/pages/dataset/dataset-setting/configuration/common-item.tsx`
- `web/src/pages/user-setting/mcp/edit-mcp-form.tsx`
- `web/src/pages/next-search/retrieval-documents/index.tsx`
- `web/src/pages/admin/users.tsx`
- `web/src/pages/admin/sandbox-settings.tsx`
- `project-work/agent-004/2026-04-11-TK-011-work-order.md`
- `project-work/agent-004/2026-04-11-TK-011-completion.md`

## 3) 覆盖范围（浏览器实巡）
### 主导航
- `/`
- `/datasets`
- `/next-chats`
- `/next-searches`
- `/agents`
- `/memories`
- `/files`

### 知识库相关
- `/dataset/dataset/:id`
- `/dataset/dataset-setting/:id`
- `/dataset/testing/:id`
- `/dataset/dataset-overview/:id`

### user-setting
- `/user-setting/data-source`
- `/user-setting/model`
- `/user-setting/mcp`
- `/user-setting/team`
- `/user-setting/api`
- `/user-setting/profile`
- `/user-setting/locale`

### admin
- `/admin/services`
- `/admin/users`
- `/admin/sandbox-settings`
- `/admin/settings`
- `/admin/audit-logs`

### 下拉 / Modal / Tooltip
- 下拉：知识库卡片菜单、智能体创建菜单、文件新增菜单等已打开
- Modal：创建知识库/聊天/搜索/记忆、上传、邀请、创建用户、MCP、新增日志详情、sandbox 测试结果等已打开
- Tooltip：知识库配置页问号提示等已触发

## 4) 阻塞页面（按要求记录）
- `/admin/monitoring`：404 不可达
- `/admin/whitelist`：404 不可达
- `/admin/roles`：404 不可达

## 5) 怎么弄（给 agent-x 的验收步骤）
### 5.1 启动与入口
1. 前端以 `9222` 为准（本次验证环境）
2. 打开：`http://localhost:9222/login`
3. 登录账号：`zhengys1@xindeco.com.cn / kk.kk.11`

### 5.2 快速验收点（建议按顺序）
1. 知识库配置页
- 路径：`/dataset/dataset-setting/525a9064350911f1b23fe7b0db4c4dee`
- 观察字段：
  - `子块用于检索`
  - `PageIndex`
  - `重叠百分比（%）`
  - `索引模型`
- 预期：不再出现 `knowledgeDetails.* / knowledgeConfiguration.*` key 直出

2. 数据源页
- 路径：`/user-setting/data-source`
- 观察卡片描述：Moodle/WebDAV/Zendesk/SeaFile/MySQL/PostgreSQL
- 预期：均为中文描述，不显示 `setting.xxxDescription`

3. MCP 弹窗
- 路径：`/user-setting/mcp` -> 点击 `添加 MCP`
- 预期：
  - 名称/URL/token placeholder 正常
  - 字段名显示 `授权令牌`
  - 不显示 `common.mcp.*` key

4. admin users
- 路径：`/admin/users`
- 预期：锁定列与状态为中文（`锁定 / 已锁定 / 未锁定`）

5. admin sandbox-settings
- 路径：`/admin/sandbox-settings`
- 预期：页面/按钮/弹窗主要文案为中文（保存配置、测试连接、连接测试结果等）

### 5.3 若仍看到旧文案
- 先强刷：`Ctrl+F5`
- 再确认访问的是 `9222`（不是旧端口）
- 若非本地开发环境，需同步最新前端构建产物

## 6) 已知限制
- 浏览器原生文件控件按钮（如 `Choose File`）受浏览器/系统语言影响，非业务 i18n 字典可直接覆盖。
- `admin/sandbox-settings` 部分 provider 标签/描述来自后端返回，可能仍为英文。
- `Dialog` 组件关闭图标的无障碍文本为 `Close`（`sr-only`），不影响主可视文案。

## 7) 关联文档
- 工单状态：`project-work/agent-004/2026-04-11-TK-011-work-order.md`（已改 `pending acceptance`）
- 完成记录：`project-work/agent-004/2026-04-11-TK-011-completion.md`
