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
