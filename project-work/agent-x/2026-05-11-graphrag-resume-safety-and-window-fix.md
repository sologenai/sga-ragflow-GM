# 2026-05-11 GraphRAG 续跑保护与大图预览修复记录

## 背景

远端 `nephrosis` 知识库在大图谱场景下出现三类问题：

1. 人为中断后点击“中断续跑”，页面一度立刻显示图谱完成，但进入知识图谱页报 Elasticsearch `Result window is too large`。
2. 后续再续跑时，任务可能重新进入若干文件的 `build_subgraph`，用户担心推新代码后误触发全量重新生成。
3. 任务在 merge 或后处理阶段长时间没有明显进度日志，无法判断后台是在正常处理还是卡死。

## 根因判断

1. `subgraph` 只是单文档抽取断点，不等于该文档已经成功进入最终图谱。
2. 旧逻辑曾把 `subgraph/entity/relation` 混在一起做覆盖统计，导致某些失败场景下把“只有 subgraph 断点”的文档误判为“已入图”。
3. Redis 里的旧任务 `merged/skipped` 状态只能作为提示，不能作为最终入图证据。旧任务可能在最终写索引失败前后留下不一致状态。
4. 大图预览和覆盖统计使用 offset 分页时，没有避开 Elasticsearch 默认 `index.max_result_window=10000`，当 `from + size > 10000` 时会触发 400。
5. 续跑进入任务后，原代码会先加载所有待处理文档 chunks，再发出后续进度；如果只是复用已落库 subgraph 进入 merge，这一步会造成“刚开始就卡住”的错觉。

## 本次修复

1. 续跑跳过规则收紧：
   - `incremental` 只跳过索引里已有 `graph/entity/relation` 证据的文档。
   - `resume_failed` 同样只跳过索引里已有 `graph/entity/relation` 证据的文档。
   - 不再因为 Redis 旧任务里记录过 `merged` 就直接跳过。
   - `subgraph` 明确只作为断点复用，不能作为“已入图”证据。

2. subgraph 续跑路径优化：
   - 进入任务后先初始化 Redis 进度并立即回调。
   - 先加载已持久化的 `subgraph` 断点。
   - 对有 subgraph 的文档直接进入 merge。
   - 只对确实没有 subgraph、也没有入图证据的文档加载 chunks 并重新抽取。

3. 大图预览和覆盖统计保护：
   - 增加 `DOCSTORE_RESULT_WINDOW` 边界，默认按 10000 控制单次 offset 分页。
   - 当批量扫描没有覆盖到目标文档时，按 doc_id 做点查兜底，避免超过 ES result window。
   - 知识图谱页在 `entity/relation` 超阈值时继续走服务端预览，不拉全量大图 JSON。

4. merge 阶段可观测性：
   - 增加加载当前图、合并子图、计算 pagerank、写索引等阶段日志。
   - 这样远端如果停在某一步，可以从 UI 日志直接判断是读图、merge、pagerank 还是写索引慢。

5. 图谱完成判定修正：
   - 大图可能因为 413 跳过全局 `graph` snapshot，但 `entity/relation` 已经有效。
   - `graph_ready` 不再单纯依赖全局 graph snapshot。
   - 如果没有任何 merged graph index 证据，任务不会误报 100% 完成，会提示继续 Resume。

## 安全边界

本次改动不删除任何已有 GraphRAG 数据。

以下操作仍然不会在部署或启动时自动发生：

1. 不会自动调用 `regenerate`。
2. 不会自动清理 `graph/subgraph/entity/relation/community_report/ty2ents`。
3. 不会把旧任务重放成全量重建。

唯一会删除旧图谱数据的路径仍是用户明确点击“重新生成”，并且后端要求 `confirm_regenerate=true`。

## 远端复测方式

1. 更新镜像并重建容器后，不要点“重新生成”。
2. 如果当前任务是失败/中断状态，点“中断续跑”。
3. 期望日志先出现：
   - `resume from task ... skip ... indexed docs`
   - 如有断点，应出现 `resume loaded ... persisted subgraphs`
   - 随后进入 `merge_subgraph ... loading current graph / merging subgraph / calculating pagerank / writing graph index`
4. 如果仍有文档进入 `build_subgraph`，应只是不具备入图证据且没有 subgraph 断点的少数文档，不应是全库重跑。
5. 知识图谱页不应再出现 `Result window is too large, from + size ... [10000]`。

## 本地验证

已通过：

```powershell
python -m py_compile agent\tools\retrieval.py api\apps\kb_app.py rag\graphrag\utils.py rag\graphrag\general\index.py rag\svr\task_executor.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py test\unit_test\test_vector_mapping_compatibility.py
npm.cmd run build
git diff --check
```

结果：

1. Python 编译通过。
2. GraphRAG/vector 相关 25 个单测通过。
3. 前端 production build 通过。
4. 仅存在既有的 CRLF、Tailwind line-clamp、pdfjs eval、大 chunk 警告。

## 镜像

已构建本地镜像：

```text
ragflow-custom:GM202604-6a916d7b9-resume-safe-agent-retrieval-20260511
ragflow-custom:latest
ragflow:GM202604
```

镜像 ID：

```text
7662605fcefa
```

镜像内校验：

```text
/ragflow/VERSION = GM202604-6a916d7b9-resume-safe-agent-retrieval-20260511
agent.tools.retrieval.AGENT_RETRIEVAL_TIMEOUT_SECONDS = 120
agent.tools.retrieval.AGENT_RETRIEVAL_TIMEOUT_ATTEMPTS = 1
```

## 追加：智能体知识检索节点超时

同日排查到另一个现象：同一知识库在配置页“检索测试”和聊天界面调用正常，但在智能体画布的“知识检索”节点里报：

```text
Operation timed out after 12 seconds and 2 attempts.
```

根因不是知识库维度或索引不可用，而是智能体工具节点 `agent/tools/retrieval.py` 走了独立执行器：

1. `Retrieval._invoke_async()` 原来使用 `@timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 12)))`。
2. 在启用 `ENABLE_TIMEOUT_ASSERTION` 的环境里，默认 12 秒会被强制执行。
3. 普通知识库检索测试和聊天检索没有这个 12 秒工具节点预算，所以表现正常。
4. `use_kg=true` 时，原代码还会重复调用两次 `settings.kg_retriever.retrieval()`，进一步放大超时概率。

修复：

1. 智能体知识检索改用独立超时变量：
   - `AGENT_RETRIEVAL_TIMEOUT_SECONDS`，默认 120 秒。
   - 兼容别名 `RETRIEVAL_COMPONENT_TIMEOUT_SECONDS`。
   - 如果全局 `COMPONENT_EXEC_TIMEOUT` 大于 120，则沿用更大的全局值。
2. 超时尝试次数改为独立变量：
   - `AGENT_RETRIEVAL_TIMEOUT_ATTEMPTS`，默认 1 次。
   - 避免慢检索被同一节点重复跑两遍。
3. 删除重复的知识图谱检索调用，`use_kg=true` 时只检索一次。

远端建议：

1. 一般场景不用额外配置，默认 120 秒。
2. 如果私有化 embedding 或 ES 响应较慢，可设置：

```bash
AGENT_RETRIEVAL_TIMEOUT_SECONDS=180
AGENT_RETRIEVAL_TIMEOUT_ATTEMPTS=1
```

3. 如果仍超时，应优先看 embedding 服务响应耗时、ES 查询耗时和是否开启 `use_kg/toc_enhance/rerank`。

## 追加：续跑跳过导致 merge 未启动

远端复测发现一个新的现象：

```text
resume from task ... skip 162 indexed docs, process 0 docs
skipped 162 docs already present in graph
```

页面停在 55%，且没有进入 merge 日志。

原因：

1. 上一版为了避免重复抽取，把 `entity/relation` 覆盖也作为 `resume_failed` 的跳过依据。
2. 这对“增量更新”是对的，但对“中断续跑”不对。
3. 中断续跑可能正在修复 merge/index/post-processing 阶段，`entity/relation` 只说明已有索引分片，不代表本次失败任务已经有可用全局 graph。
4. 因此 162 个文档被全部跳过，`ok_docs=0`，merge 阶段自然不会启动。

修复：

1. `incremental` 继续用 `graph/entity/relation` 覆盖来跳过已有文档。
2. `resume_failed` 只允许 active `graph` snapshot 覆盖的文档跳过。
3. 如果检测到只有 `entity/relation` 但没有 active `graph` snapshot，日志会提示：

```text
[GraphRAG] resume detected entity/relation indexes without an active graph snapshot; reuse subgraph checkpoints and run merge repair.
```

4. 这时任务会加载已持久化的 `subgraph` 断点，跳过重新抽取，直接进入 merge repair。
5. `process 0 docs` 的分支不再触发从所有 subgraph 隐式 rebuild 大图，避免 UI 停在 55% 没日志。

本地追加验证：

```powershell
python -m py_compile rag\graphrag\general\index.py rag\graphrag\utils.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py
git diff --check
```

结果：16 passed。
