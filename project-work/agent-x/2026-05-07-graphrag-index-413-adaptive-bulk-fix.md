# GraphRAG 索引写入 413 自适应拆批修复记录

日期：2026-05-07

## 现场现象

远端 GraphRAG general 图谱生成已顺利跑过抽取、合并和 edges embedding 阶段，停止在最终写索引阶段：

```text
当前阶段：edges 向量 593/1301，批次 37/82
图谱统计：实体/节点 82053，关系/边 89306，社区 0
Get embedding of edges: 1301/1301, batches 82/82
set_graph converted graph change to 2660 chunks in 104.9s.
set_graph removed 0 nodes and 0 edges from index in 1.20s.
Insert chunks: 32/2660
[ERROR][Exception]: Insert chunk error: ["ApiError(413, 'None')"]
```

## 判断

这不是模型调用失败，也不是 embedding 并发问题。`ApiError(413)` 发生在 `settings.docStoreConn.insert()` 写 Elasticsearch / OpenSearch / Infinity 的 bulk 请求阶段，含义是单次请求体过大。

当前默认 `GRAPHRAG_INDEX_BULK_SIZE=32`。在 8 万实体、8.9 万关系规模下，32 个 GraphRAG chunk 的 JSON + 向量字段合在一个 bulk 请求里可能超过后端网关或索引服务的 HTTP payload 限制。

## 根因

昨晚修复的是“403 后不要破坏续跑检查点”。这次暴露的是另一个写入阶段问题：

1. `set_graph()` 写索引时固定按 `GRAPHRAG_INDEX_BULK_SIZE` 分批。
2. 如果 bulk 返回 413，旧代码直接抛错，没有自动降批。
3. 大图场景下，即使普通 chunks 可以拆批，全局 graph snapshot 单块也可能太大，单独写入也会 413。
4. 如果全局 graph snapshot 因太大无法落库，后续读取 graph 需要能从 subgraph fallback 重建，否则续跑/增量判断会依赖缺失的 graph 快照。

## 本次修复

1. 新增索引写入错误识别：
   - `413`
   - `request entity too large`
   - `payload too large`
   - `content too large`
   - `http.max_content_length`

2. 新增 `_insert_chunks_adaptive()`：
   - 默认按 `GRAPHRAG_INDEX_BULK_SIZE` 写入。
   - 遇到 413 自动将批量减半：`32 -> 16 -> 8 -> 4 -> 2 -> 1`。
   - 每次降批都会输出可见日志，便于远端确认自适应发生。
   - 非 413 错误仍然抛出，避免掩盖真实索引故障。

3. 全局 graph snapshot 单块过大时不再终止任务：
   - 如果单个 graph chunk 写入仍然 413，会跳过该快照。
   - 已写入的 `subgraph/entity/relation` 保留。
   - 图谱搜索和统计主要依赖 entity/relation，不依赖这个大 JSON 快照。

4. 增加 fallback：
   - `get_graph()` 没有可用全局 graph 快照时，从已落库 subgraph 重建。
   - `get_graph_doc_ids()` 没有全局 graph 快照时，从 subgraph 的 `source_id` 汇总。
   - `does_graph_contains()` 也会检查 subgraph，避免无 graph 快照时误判老文档未入图。

## 预期远端行为

再次续跑到同一阶段时，不应再在 `Insert chunks: 32/2660` 直接失败。应看到类似：

```text
[GraphRAGIndex] graph index chunks payload too large at batch=32; retry with batch=16
[GraphRAGIndex] graph index chunks payload too large at batch=16; retry with batch=8
Insert chunks: .../2660 (batch=8)
```

如果最终全局 graph snapshot 单块仍然 413，应看到：

```text
[GraphRAGIndex] global graph snapshot is too large for one index request; skip the snapshot and rely on subgraph/entity/relation indexes for resume/search.
```

这条日志不是失败，而是降级成功。后续会通过 subgraph 重建 graph。

## 已验证

执行通过：

```powershell
python -m py_compile rag\graphrag\utils.py test\unit_test\graphrag\test_graphrag_embed_pipeline.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py test\unit_test\test_vector_mapping_compatibility.py
```

结果：

```text
GraphRAG 单文件测试：14 passed
相关回归：25 passed
```

新增覆盖：

1. bulk 写入返回 413 时自动降批。
2. 全局 graph snapshot 单块 413 时跳过快照但不删除旧 graph。

## 镜像构建记录

代码提交后已基于上一版 `ragflow-custom:latest` 执行 overlay 构建，只覆盖本次 GraphRAG 后端文件：

```dockerfile
COPY rag/graphrag/utils.py rag/graphrag/utils.py
```

提交：

```text
d08ca3a29 fix: adapt GraphRAG index bulk on 413
```

镜像版本文件：

```text
/ragflow/VERSION = GM202604-d08ca3a29
```

本地镜像标签：

1. `ragflow-custom:latest`
2. `ragflow:GM202604`
3. `ragflow-custom:GM202604-d08ca3a29`

本地镜像 ID：`e5041e0a93a7`

镜像内已验证包含：

1. `_insert_chunks_adaptive()`。
2. `payload too large` 识别和自动降批日志。
3. `global graph snapshot is too large` 降级日志。

## 远端复测建议

1. 更新镜像并重建容器后，继续点“中断续跑”，不要点“重新生成”。
2. 重点观察 `Insert chunks` 后是否出现自适应降批日志。
3. 如果看到 `global graph snapshot is too large`，按降级成功处理，不要误判为失败。
4. 如果仍失败，优先看是否是单个非 graph chunk 在 `batch=1` 仍 413；那说明某个 subgraph/entity/relation 单块超限，需要下一步做 subgraph 分片或缩短关系/实体描述。
