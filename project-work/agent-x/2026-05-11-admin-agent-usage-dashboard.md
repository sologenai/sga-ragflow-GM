# 2026-05-11 admin 智能体使用看板交付记录

## 背景

业务需要在 admin 路由下新增整体智能体使用看板，覆盖智能体和聊天调用，不统计点击查看数量。重点指标包括总会话数、总对话轮数、活跃用户、Token、耗时、失败数，以及聊天过程中生成知识图谱的数量和用户。

## 本次实现

- 新增 admin 后端统计接口：`GET /api/v1/admin/agent-usage/summary`。
- 新增 admin 后端 Excel 导出接口：`GET /api/v1/admin/agent-usage/export`。
- 统计源包含 `api_4_conversation.source = agent/dialog`。
- 聊天图谱生成统计来自 `knowledgebase.kb_label = chat_graph`。
- 支持按时间范围、来源、关键词、用户、日/周/月维度过滤。
- Excel 支持选择导出维度：总览、趋势、按智能体/聊天、按用户、聊天图谱、调用明细。
- Excel 支持导出当前筛选结果和全量导出；全量导出忽略时间范围，覆盖上线以来数据。
- 新增 admin 前端页面：`/admin/agent-usage`，左侧菜单显示为“智能体看板”。
- 筛选栏采用稳定控件宽度；来源下拉补齐暗色主题，避免不同来源筛选后输入框宽度跳动或下拉选项白底低对比。
- 移除“来源结构”里的 Token 小柱图 hover 层，改为静态 Token 摘要，避免暗色页面出现白色提示块。

## 不做项

- 不统计知识图谱点击查看数量。
- 不改变图谱生成、续跑、导入导出、检索链路。
- 不修改已有业务数据结构，仅复用已有调用日志表和知识库标签字段。

## 验证记录

- `python -m py_compile admin\server\routes.py admin\server\usage_service.py`
- `npx eslint src/pages/admin/agent-usage.tsx src/pages/admin/layouts/navigation-layout.tsx src/routes.tsx src/services/admin-service.ts --max-warnings=0`
- `npx vite build --mode production --minify false`

## 注意

完整 `npm run lint` 当前会命中大量仓库历史 lint 问题，本次只对新增和直接修改的前端文件做了针对性 lint。完整 `npm run build` 在 terser 压缩阶段超过 10 分钟无输出，本次使用 Vite 生产构建且关闭压缩生成 `web/dist`，用于本地镜像验证。

## 2026-05-12 项目经理补充记录：下午以来变更总览

### 变更范围

- GraphRAG 续跑和合并阶段修复：补强从子图谱恢复到全局图谱合并的续跑链路，避免已抽取数据在续跑时被误判为需要重抽。
- 知识库列表统计和运行时当前时间：修正知识库侧数量展示不一致问题，并恢复聊天/智能体运行时注入当前时间的约束。
- 聊天调用日志：新增聊天维度调用日志，用于记录用户、问题、状态、轮次、Token、耗时等核心调用数据。
- admin 智能体使用看板：新增 admin 侧整体看板，聚合智能体会话、聊天会话、活跃用户、Token、平均耗时、失败调用、聊天图谱生成等指标。
- Excel 导出：支持当前筛选导出和全量导出，导出维度可选总览、趋势、按智能体/聊天、按用户、聊天图谱、调用明细。
- 看板前端体验修复：修复筛选栏换行、不同来源切换后表格列宽跳动、下拉框暗色主题对比度不足、来源/状态 badge 被压成竖排、Chrome/Edge 表格表现不一致等问题。

### 本次 2026-05-12 最后一轮 UI 修复

- `web/src/pages/admin/agent-usage.tsx`：筛选栏改为固定单行布局，外层支持横向溢出保护，避免 Chrome 下右侧被截断。
- `web/src/pages/admin/agent-usage.tsx`：三张统计表统一使用固定列宽、`table-layout: fixed`、`colgroup`、表头/表体同步宽度，避免“全部来源/仅智能体/仅聊天”切换后列宽变化。
- `web/src/pages/admin/agent-usage.tsx`：来源和状态 badge 增加最小宽度、居中、`nowrap`，避免 Edge 下“聊天”变成竖排。
- `web/src/pages/admin/agent-usage.tsx`：压缩表格表头和单元格内边距，强制表头不换行，避免“平均耗时/状态”等短列表头竖排。

### 已验证

- `npx.cmd eslint src/pages/admin/agent-usage.tsx src/pages/admin/layouts/navigation-layout.tsx src/routes.tsx src/services/admin-service.ts --max-warnings=0`：通过。
- `npx.cmd vite build --mode production --minify false`：通过。
- 本地容器前端产物已正确覆盖到 `/ragflow/web/dist/`，已确认不再误拷贝到 `/ragflow/web/dist/dist`。
- Chrome 1600/1890 宽度验证：页面无整体横向溢出，筛选栏单行，最近调用明细中“聊天/成功/失败”横排。
- Edge 1600/1890 宽度验证：页面无整体横向溢出，筛选栏单行，最近调用明细中“聊天/成功/失败”横排。

### 验收边界

- 本次 UI 修复不修改后端统计口径。
- 本次 UI 修复不修改调用日志落库逻辑。
- 本次 UI 修复不修改 GraphRAG 生成、续跑、导入导出和检索链路。
- 本次 UI 修复只影响 admin 智能体使用看板页面展示。
