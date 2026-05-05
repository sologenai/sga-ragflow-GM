# GraphRAG 自适应长任务容错修复记录

日期：2026-05-05
负责人：agent-X
分支：GM202604

## 目标

图谱生成应进入“长任务自适应状态”：只要不是人工取消或明确配置硬错误，就尽量在任务内部通过重试、队列、降批处理继续跑到图谱生成完成，而不是因为一次模型超时、限流、私有 embedding 短暂不可用就中断。

## 原实现缺口

- GraphRAG 已有 embedding 批处理、队列和有限重试，但默认只重试固定次数。
- 全局任务已取消硬总超时，但仍有 3 小时无进度 watchdog，极端情况下会取消整条 GraphRAG。
- embedding 单次调用没有独立 attempt timeout，私有化服务如果长时间不返回，任务只能等外层 watchdog。
- 文档子图抽取、merge、实体消歧、社区抽取没有统一的瞬时失败重试策略。
- 批量 embedding 如果是“批量太大导致服务过载”，旧逻辑只会重试同样大小的批次，不会自动拆小。

## 本次修复

### 1. embedding 自适应

新增参数：

- `GRAPHRAG_EMBED_MAX_RETRIES`：默认 `0`，表示瞬时错误无限重试；非瞬时错误仍立即失败。
- `GRAPHRAG_EMBED_ATTEMPT_TIMEOUT_SECONDS`：默认 `3600`，单次 embedding 调用超过该时间视为瞬时超时并进入重试。
- `GRAPHRAG_EMBED_ADAPTIVE_SPLIT_AFTER_RETRIES`：默认 `2`，同一批次连续瞬时失败后自动拆成两半继续处理。

效果：

- 有 batch 进度或 retry 回调时，UI 会持续看到任务仍在推进。
- 私有 embedding 服务短暂限流、超时、502/503/504、连接重置，会在任务内部消化。
- 大批量节点/边 embedding 过载时，会从大批次自动拆小，减少人工调参。

### 2. GraphRAG 阶段级自愈

新增统一 stage retry：

- 文档子图生成 `build_subgraph`
- 子图合并 `merge_subgraph`
- 实体消歧 `entity_resolution`
- 社区抽取 `community_extraction`

新增参数：

- `GRAPHRAG_DOC_MAX_RETRIES`：默认 `0`，文档子图抽取瞬时错误无限重试。
- `GRAPHRAG_STAGE_MAX_RETRIES`：默认 `0`，merge/消歧/社区抽取瞬时错误无限重试。
- `GRAPHRAG_STAGE_RETRY_BASE_SECONDS`：默认 `5`。
- `GRAPHRAG_STAGE_RETRY_MAX_SECONDS`：默认 `300`。

### 3. 全局 watchdog 默认不再杀任务

`GRAPHRAG_NO_PROGRESS_TIMEOUT_SECONDS` 默认从 3 小时改为 `0`，表示不由外层 watchdog 取消 GraphRAG。真正的自愈由内部 stage timeout、retry、queue、batch split 承担。

### 4. GraphRAG 绕开普通解析任务的外层超时

普通解析任务仍保留 `RAGFLOW_TASK_TIMEOUT_SECONDS` 保护。GraphRAG 因为是长任务，改为不走 `do_handle_task` 的普通超时装饰器，只使用 GraphRAG 自己的阶段级容错策略。

## 停止条件

仍然会停止的情况：

- 用户点击人工中断。
- 明确配置硬错误，例如 `not authorized`、`invalid api key`、模型不存在、向量维度/索引 mapping 不匹配。
- 非瞬时数据错误，例如输入结构不可解析、schema 不支持。

不会因为以下瞬时问题直接停：

- 模型超时。
- 私有 embedding 服务限流。
- 502/503/504/429。
- 连接重置、服务短暂不可用。
- 批量过大导致服务过载。

## 验收建议

远端验证时建议重点看：

1. embedding 失败后日志是否出现 `retry ... attempt X/unlimited`。
2. 批量过大时是否出现 `adaptive split ... size A -> B+C`。
3. UI 进度是否持续有 retry 或 batch 回调，不再因为单次超时直接失败。
4. 人工中断仍然必须立即进入可续跑状态。
