# GraphRAG 403 后续跑检查点修复记录

日期：2026-05-06

## 背景

远端 `nephrosis` 知识库在 GraphRAG general 方式生成图谱时，先前代码更新后已经可以在续跑时跳过大部分已处理文档，并复用已落库的 per-document subgraph。随后在最终合并阶段出现一次 403，错误描述指向“找不到节点内容”。用户再次点击续跑后，界面显示重新进入若干文件的 `build_subgraph`，表现为“又从头跑文件”。

## 代码链路复盘

GraphRAG general 的主链路如下：

1. `run_graphrag_for_kb()` 初始化任务，读取 `resume_from_task_id`。
2. 续跑时读取两类检查点：Redis 中旧任务的 `merged` 文档，以及索引里的全局 `graph.source_id`。
3. 续跑时再读取已持久化的 `knowledge_graph_kwd=subgraph`，能读到的文档会跳过 LLM 抽取，直接进入 merge。
4. 对需要处理的文档执行 `generate_subgraph()`，并把单文档 subgraph 写入索引。
5. `merge_subgraph()` 把单文档 subgraph 合入全局 graph。
6. `set_graph()` 把全局 graph、subgraph、entity、relation 写回索引。

## 根因

这次不是“续跑按钮没有生效”，而是最终写图谱阶段的崩溃安全不够：

1. `_graphrag_error_kind()` 把 `forbidden / not found / 403 / 404` 统一当成 `hard_config`。如果错误实际来自索引或节点内容临时不可读，就不会进入自适应重试。
2. `set_graph()` 原来在写新图谱前先删除旧的 `graph + subgraph`。如果删除后插入阶段报 403/404，下次续跑需要的 per-doc subgraph 会被清掉。
3. 更深一层，旧全局 graph 也可能先被删除。Redis 里仍记录某些文档 `merged`，但索引里的 graph 已经不完整，下一次续跑会出现“状态认为已合并，实际图谱没有”的错位风险。

## 本次修复

1. `subgraph` 不再由 `set_graph()` 清理。per-document subgraph 明确作为断点续跑检查点保留。
2. `set_graph()` 生成的 subgraph 改为 deterministic id，重复写入同一内容时覆盖，降低重复检查点膨胀。
3. 全局 graph 改为稳定 id：`graphrag_graph_{kb_id}`。
4. `set_graph()` 先完成 entity/relation/subgraph 写入，再写稳定 id 的全局 graph；只有新 graph 成功写入后，才清理旧的随机 graph id。
5. `get_graph()` 和 `get_graph_doc_ids()` 优先读取稳定 id 的 graph，兼容旧随机 id 残留。
6. 403/404 中如果包含 node/content/chunk/document/graph/index/storage 等上下文，按 transient/service 处理，进入 GraphRAG 阶段级重试；模型未授权、模型不存在、维度/mapping/schema 错误仍然是硬配置错误，避免无意义无限重试。

## 预期效果

1. 远端再遇到“403 找不到节点内容”这类索引/内容临时错误时，会进入重试，不会立即停。
2. 即便最终写全局图失败，旧 graph 和 per-doc subgraph 仍保留；再次点击续跑时应继续复用已有子图，而不是重新抽取全部文件。
3. 如果确实有少数文档没有任何已落库 subgraph，续跑仍会只重跑这部分文档；这不是全量重跑。

## 已验证

执行通过：

```powershell
python -m py_compile rag\graphrag\utils.py rag\graphrag\general\index.py test\unit_test\graphrag\test_graphrag_embed_pipeline.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py test\unit_test\test_vector_mapping_compatibility.py
```

结果：相关回归共 23 个测试全部通过。

补充手工校验：

```powershell
403 node content not found => transient
Model(Qwen) not authorized => hard_config
model not found => hard_config
Operation timed out => timeout
```

## 远端复测建议

1. 更新镜像并重建容器后，不要点“重新生成”，先点“中断续跑”。
2. 观察日志是否出现 `resume loaded ... persisted subgraphs`。
3. 如果仍有若干文件进入 `build_subgraph`，先看数量是否只是缺少 subgraph 的少数文件，不要按 162 个文件全量重跑判断。
4. 观察 403 后日志是否进入 `retry ... kind=transient/service`，而不是立即失败。
5. 如果重复出现真实鉴权错误，例如 `model not authorized`，那仍然应该停下，因为这是后台模型配置问题，不属于可自愈错误。
