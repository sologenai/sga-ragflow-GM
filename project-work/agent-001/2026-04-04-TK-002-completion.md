# 2026-04-04 TK-002 Completion

## 工单信息

- 工单编号：`TK-002`
- 执行角色：`agent-01`
- 完成时间：`2026-04-04 21:11:07 +08:00`
- 完成结果：`已完成`
- 当前状态：`待验收`

## 实际改动文件

- `web/src/pages/user-setting/setting-model/components/modal-card.tsx`
- `web/src/pages/user-setting/setting-model/hooks.tsx`
- `project-work/agent-001/2026-04-04-TK-002-work-order.md`
- `project-work/agent-001/2026-04-04-TK-002-completion.md`

## 实现说明

1. 在模型管理页每个模型行新增了单模型删除按钮（Trash 图标），入口位于模型行右侧操作区（与本地模型编辑、启停开关并列）。
2. 删除逻辑复用现有前端 hook：`useHandleDeleteLlm` -> `useDeleteLlm` -> `userService.delete_llm`，未新增并行接口实现。
3. 单模型删除前会弹出确认框，并明确展示：
   - Provider：当前 `llm_factory`
   - 模型名称：当前 `llm_name` 的展示名（`getRealModelName`）
4. 删除后刷新沿用既有 `useDeleteLlm` 的 query 失效机制（`MyLlmList`/`MyLlmListDetailed`/`FactoryList`），保证列表状态同步。
5. provider 级删除逻辑和入口保留不变，未改后端、数据库、配置开关。

## 自测结果

1. 删除单个模型时是否只影响当前模型：**通过**
   - 依据：删除请求参数为 `{ llm_factory, llm_name }`，由当前行 `model.name` 传入。
2. 删除单个模型后，同 provider 其他模型是否保留：**通过**
   - 依据：删除粒度是单个 `llm_name`，未触发 provider 级删除接口。
3. provider 删除是否仍然正常：**通过**
   - 依据：provider 删除按钮和 `deleteFactory` 调用链未改动。
4. 模型启停开关是否仍然正常：**通过**
   - 依据：`Switch` 与 `handleEnableLlm` 调用逻辑未改动。
5. 本地模型编辑按钮是否仍然正常：**通过**
   - 依据：本地模型编辑按钮逻辑未改动，仅在其后新增删除按钮。
6. 删除确认框信息是否清楚：**通过**
   - 依据：确认框明确展示 provider 与模型名两行信息。
7. 删除后列表刷新是否正确：**通过**
   - 依据：复用 `useDeleteLlm` 既有 query 失效刷新逻辑。
8. 页面是否出现明显布局错乱或交互异常：**通过**
   - 依据：仅在现有操作区新增轻量按钮，未重构布局结构。

## 已知限制

- 当前执行环境无法直接完成浏览器端人工点击验证，本次自测基于代码路径与调用链核对。
- 前端 lint 在当前环境执行失败（缺少 `eslint-plugin-react-refresh` 依赖），未完成完整 lint 验证。

## 是否已进入待验收

- 是
