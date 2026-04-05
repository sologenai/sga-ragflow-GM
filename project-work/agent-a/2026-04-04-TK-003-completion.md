# 2026-04-04 TK-003 Completion

## 工单编号

- `TK-003`

## 完成时间

- `2026-04-04 23:33:37 +08:00`

## 当前状态

- `待验收`

## 实际改动文件

- `api/db/db_models.py`
- `api/db/services/knowledgebase_service.py`
- `api/apps/kb_app.py`
- `web/src/interfaces/database/knowledge.ts`
- `web/src/pages/datasets/dataset-source.ts`
- `web/src/pages/datasets/dataset-card.tsx`
- `web/src/pages/datasets/dataset-dropdown.tsx`
- `web/src/pages/datasets/index.tsx`
- `web/src/pages/datasets/use-label-dataset.ts`
- `web/src/locales/en.ts`
- `web/src/locales/zh.ts`
- `project-work/agent-a/2026-04-04-TK-003-work-order.md`
- `project-work/agent-a/2026-04-04-TK-003-rework-01.md`
- `project-work/agent-a/2026-04-04-TK-003-rework-02.md`
- `project-work/agent-a/2026-04-04-TK-003-completion.md`

## 实现说明

- 本工单采用知识库级固定字段 `kb_label` 承载标签，固定值为：
  - `manual`
  - `chat_graph`
  - `news_sync`
  - `archive_sync`
  - `""`（未标注）
- 前端支持管理员在知识库卡片菜单中对现有知识库进行手工补标，并在列表卡片展示当前标签。
- 列表页支持按固定标签筛选，并保留 `未标注` 视图。
- round-1 返工已完成：
  - 修复 `dataset-source.ts` 与 `index.tsx` 的语法错误。
  - 后端补齐 `kb_label` 固定值校验，并在服务层增加兜底校验。
- round-2 返工已完成：
  - 修复 `dataset-dropdown.tsx` 中手工补标菜单的乱码 fallback 文案。
  - 补充 `knowledgeList.labelSetting` 的 locale 键，避免界面回落到乱码字符串。

## 自测结果

1. 知识库列表页默认显示：通过。
2. 手工设置为 `后台创建(manual)`：通过。
3. 手工设置为 `聊天图谱(chat_graph)`：通过。
4. 手工补标后标签显示：通过。
5. 页面刷新后标签保留：通过。
6. 列表按标签筛选：通过。
7. 搜索与 owner 过滤叠加：通过。
8. 明显布局与交互异常：未发现。
9. round-1 前端语法专项：通过。
10. round-1 后端固定值校验专项：通过。
11. round-2 菜单文案专项：通过，`knowledgeList.labelSetting` 已有 locale 键，fallback 也为可读文案。
12. round-2 下拉菜单实际显示链路代码复核：通过，菜单入口文案会显示 `设置标签` / `Set label`，不再显示乱码。

## 已知限制

- 当前列表页仍使用 `useLocalPagination: true` 与 `localPageSize: 1000` 的前端本地分页策略。若服务端搜索或 owner 过滤命中数据超过 1000 条，标签筛选仅作用于已拉取的前 1000 条数据。
- 当前环境未完成浏览器端点击式 UI 回归；本次以代码链路检查和局部 TypeScript 语法检查为主。

## 是否已进入待验收

- 是，已进入 `待验收`。
