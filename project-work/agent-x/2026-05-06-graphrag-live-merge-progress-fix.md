# GraphRAG merge 阶段实时百分比修复记录

日期：2026-05-06
负责人：agent-X
分支：GM202604

## 问题

远端图谱生成面板长期显示 `60.00%`，但日志持续输出：

```text
Get embedding of nodes: 5537/32588, batches 262/1953
```

同时顶部文档/节点统计在部分历史任务里不显示，只剩“图谱统计：抽取完成并合并后更新”。

## 根因

GraphRAG 百分比是阶段型进度：

- 子图抽取结束后进入 60%。
- 每个 doc 完成 merge 后才从 60% 向 80% 推进。
- 大文档在单个 `merge_subgraph` 内部可能需要跑几千个 embedding batch，但旧代码没有把这些 batch 映射成 `prog`。

所以日志在动，进度条和百分比不动。远端截图里的 `60%` 不是任务停住，而是当前阶段内部缺少细粒度进度回写。

## 修复

- 为每个 doc 的 merge 分配独立进度区间：`0.6 + 0.2 * doc_index / doc_count` 到 `0.6 + 0.2 * (doc_index + 1) / doc_count`。
- `set_graph` 内部把当前 doc 的进度区间拆成：
  - nodes embedding：前 55%
  - edges embedding：中间 30%
  - index 写入：最后 12%
- `_embed_requests_with_bounded_workers` 在每个 batch 完成时同时回写 `msg` 和 `prog`。
- 前端增加兜底：如果历史任务没有 `doc_summary`，从 `progress_msg` 中解析：
  - `Get embedding of nodes: x/y, batches a/b`
  - `Insert chunks: x/y`
  并在顶部显示当前阶段进度。

## 验收预期

部署新镜像后，大文档 merge 阶段不应再长期卡在固定 `60.00%`。即使还在同一个 doc 内部跑 nodes embedding，百分比也应随 batch 逐步推进。

如果历史任务缺少 `doc_summary`，顶部仍应显示类似：

```text
当前阶段：nodes 向量 5537/32588，批次 262/1953
```
