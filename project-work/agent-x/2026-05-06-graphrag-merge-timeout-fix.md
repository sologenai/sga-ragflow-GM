# GraphRAG merge_subgraph 反复重试修复记录

日期：2026-05-06
负责人：agent-X
分支：GM202604

## 现象

远端实例在知识图谱生成 60% 左右持续重试：

```text
[GraphRAG] retry merge_subgraph doc:... attempt 51/unlimited
(reason=TimeoutError('Operation timed out after 180 seconds and 2 attempts.'))
```

同一时间日志仍在输出：

```text
Get embedding of nodes: 5537/32588, batches 262/1953
```

## 根因

这不是子图谱抽取失败，而是单文档子图已经抽取完成，卡在 `merge_subgraph` 合并写入全局图谱阶段。

代码里 `merge_subgraph` 仍保留旧的 `@timeout(60 * 3)`。远端如果设置了 `ENABLE_TIMEOUT_ASSERTION`，该装饰器会在 180 秒后强制取消整个 merge。

当前这个子图约 32588 个节点、1953 个 embedding batch，180 秒内不可能完成合并和索引写入，所以每次都会：

1. 从 `merge_subgraph` 开始。
2. embedding 跑到几百个 batch。
3. 180 秒硬超时。
4. 外层自适应重试重新开始同一个 doc 的 merge。

因此出现 attempt 51/unlimited，但实际没有进入最终合并完成。

## 修复

- 移除 `merge_subgraph` 的固定 180 秒 timeout 装饰器。
- 同步移除 `resolve_entities`、`extract_community` 的固定 30 分钟 timeout 装饰器，避免大图后处理阶段重复出现同类问题。
- `set_graph` 写索引时不再因为 `ENABLE_TIMEOUT_ASSERTION` 使用 3 秒写入超时，改为独立配置：
  - `GRAPHRAG_INDEX_WRITE_TIMEOUT_SECONDS`，默认 1800 秒；设为 0 表示不限制单批写入时间。
  - `GRAPHRAG_INDEX_BULK_SIZE`，默认 32，减少大图写入时的请求次数。

## 远端验证点

部署新镜像后，原日志不应再出现固定的：

```text
Operation timed out after 180 seconds and 2 attempts
```

预期会继续看到：

- `Get embedding of nodes...`
- `Get embedding of edges...`
- `Insert chunks...`
- `merging subgraph for doc ... into the global graph done...`

如果后续仍有重试，应重点看新的 reason 是 embedding、索引写入、还是模型授权/维度配置问题。
