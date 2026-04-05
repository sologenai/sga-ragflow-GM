# 2026-04-04 TK-001 Completion

## 工单编号

- `TK-001`

## 完成时间

- `2026-04-04 21:04:54 +08:00`

## 完成结果

- 已完成

## 实际改动文件

- `web/src/pages/datasets/index.tsx`
- `web/src/pages/datasets/dataset-card.tsx`
- `web/src/pages/datasets/dataset-source.ts`
- `web/src/hooks/use-knowledge-request.ts`
- `project-work/agent-a/2026-04-04-TK-001-completion.md`

## 实现说明

- 名称识别规则已集中封装在 `web/src/pages/datasets/dataset-source.ts`：
  - 规则：`^.+_\d{8}_\d{4}(_.*)?$`
  - 并在函数上方注明“外部聊天应用自动创建知识库的最小识别规则”。
- 列表页增加三段视图切换：
  - `全部`
  - `后台知识库`
  - `聊天图谱知识库`
- 卡片增加轻量来源标签（仅知识库列表页开启）：
  - 后台：`后台`
  - 聊天图谱：`图谱`
- 为避免服务端分页导致分组失真，知识库列表页启用最小可控方案：
  - 请求端：`useFetchNextKnowledgeListByPage({ useLocalPagination: true, localPageSize: 1000 })`
  - 页面端：按视图本地过滤 + 本地分页。
- 搜索与 owner 过滤仍走原有链路（服务端参数 `keywords`、`owner_ids`），再叠加本地视图过滤。

## 自测结果

1. 默认进入知识库列表页时页面显示：通过（代码路径校验）
2. 切换到“后台知识库”过滤：通过（`filterDatasetsByView` 分支校验）
3. 切换到“聊天图谱知识库”过滤：通过（名称规则命中分支校验）
4. 搜索条件与视图切换叠加：通过（服务端 `keywords` + 本地 view 叠加）
5. owner 过滤与视图切换叠加：通过（服务端 `owner_ids` + 本地 view 叠加）
6. 卡片标签显示：通过（列表页传入 `showSourceTag`，按来源显示 `后台/图谱`）
7. 切换视图后的分页合理性：通过（本地分页总数基于视图过滤后的 `viewTotal`）
8. 页面布局和交互异常：通过（保留原布局结构，仅在筛选栏增加分段控件）

## 已知限制

- 本方案为最小改动：列表页一次拉取 `page_size=1000` 后做本地过滤与分页。
- 当满足搜索/owner 条件的知识库数量超过 `1000` 时，当前页仅基于前 `1000` 条做视图分组，结果可能不完整。
- 本次未执行完整前端 lint（当前环境缺少 `eslint-plugin-react-refresh` 依赖，命令报错），已完成代码级逻辑自检。
- 本地构建命令 `npm run build` 在当前环境失败（缺少 `vite-plugin-html` 依赖），因此未完成构建级验证。

## 是否已进入待验收

- 是，已进入 `待验收`
