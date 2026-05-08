# GraphRAG 实体消重合并迭代错误修复记录

日期：2026-05-08

## 现场现象

远端 GraphRAG general 图谱生成已完成文档合并、索引写入和实体候选对判断，停止在实体消重的最终合并阶段：

```text
Resolved 36582 candidate pairs, 7167 of them are selected to merge.
[ERROR][Exception]: dictionary keys changed during iteration
```

## 判断

这不是模型超时，也不是索引 413。候选对已经全部判断完成，错误发生在把重复实体真正合并回 NetworkX graph 的阶段。

## 根因

`Extractor._merge_graph_nodes()` 原逻辑遍历 `graph.neighbors(node1)`，同时在循环里执行：

1. `graph.add_edge(...)`
2. `graph.remove_node(node1)`

`graph.neighbors()` 返回的是 NetworkX 的动态视图。遍历动态视图时修改 graph 结构，会触发 Python 运行时错误：

```text
dictionary keys changed during iteration
```

同时 `EntityResolution.__call__()` 会为多个重复实体 group 创建并发 merge task。即使 group 本身来自不同 connected component，同一个 NetworkX graph 也不是并发结构修改安全对象。并发结构修改会放大这个问题。

## 本次修复

1. `_merge_graph_nodes()` 先过滤已不存在的节点。
2. 遍历邻居时改成 `list(graph.neighbors(node1))` 快照，避免遍历过程中 graph 结构变化影响迭代器。
3. 处理边时增加 `None` 防护，避免并发/历史状态下缺边导致二次异常。
4. 新增 `node0_neighbors.add(neighbor)`，保持主节点邻居集合和新增边同步。
5. 实体消重的候选判断仍保持并发，但真实 graph 结构合并改为 `asyncio.Lock()` 串行执行。
6. 合并 duplicate entity groups 时增加进度日志：

```text
Merging N duplicate entity groups.
Merged duplicate entity groups: x/N
```

## 预期远端行为

再次点“中断续跑”后，进入实体消重阶段时不应再报：

```text
dictionary keys changed during iteration
```

如果重复实体 group 很多，会看到分组合并进度日志，而不是长时间只有一条日志。

## 已验证

执行通过：

```powershell
python -m py_compile rag\graphrag\general\extractor.py rag\graphrag\entity_resolution.py test\unit_test\graphrag\test_graphrag_entity_resolution_merge.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_entity_resolution_merge.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_entity_resolution_merge.py test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py test\unit_test\test_vector_mapping_compatibility.py
```

结果：

```text
实体消重合并测试：2 passed
GraphRAG 相关回归：27 passed
```

新增覆盖：

1. `_merge_graph_nodes()` 使用邻居快照，合并节点时不会因边/节点变化触发迭代错误。
2. `EntityResolution` 对同一 NetworkX graph 的结构合并串行化，避免并发改图。

## 远端复测建议

1. 更新镜像并重建容器后继续点“中断续跑”，不要点“重新生成”。
2. 重点观察实体消重日志是否出现 `Merging ... duplicate entity groups`。
3. 如果继续停在实体消重阶段，记录下一条错误；现在这次的字典迭代错误已被针对性修复。
