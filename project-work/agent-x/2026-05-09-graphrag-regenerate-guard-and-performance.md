# 2026-05-09 GraphRAG 重新生成保护与大图谱降载记录

## 背景

远端大图谱已生成到 10 万级实体/关系后，系统出现整体响应变慢；同时在部署新镜像、重启服务后，存在图谱被重新生成任务覆盖的风险。

本次处理目标：

1. 允许验收方按新逻辑从头重建图谱。
2. 防止已有图谱被默认 `regenerate`、旧任务重放或前端误判无确认地删除。
3. 降低大图谱完成后 trace 轮询和统计接口对 API/ES 的持续压力。

## 主要改动

### 1. 重新生成必须显式确认

接口：`POST /kb/run_graphrag`

当知识库已经存在任意 GraphRAG 数据（`graph/subgraph/entity/relation/community_report/ty2ents`）时，如果请求 `mode=regenerate` 但没有携带 `confirm_regenerate=true`，后端会拒绝请求。

这样可以挡住三类风险：

1. 前端普通“生成”路径误触发默认 `regenerate`。
2. 外部调用方没有传 mode 时落到默认重建。
3. Worker 重启后旧的未确认 regenerate 任务被重新消费。

SDK 接口 `POST /datasets/<dataset_id>/run_graphrag` 同步加了同样保护。

### 2. 前端只在确认框路径发送 confirm

前端 GraphRAG 调用新增：

```json
{
  "confirm_regenerate": true
}
```

仅“重新生成”确认框按钮会发送该字段。普通生成、增量更新、中断续跑不会发送该字段。

### 3. GraphRAG trace 统计缓存

新增 Redis 缓存：

```text
graphrag:graph_summary:<kb_id>
```

默认缓存 60 秒，可用环境变量调整：

```bash
GRAPHRAG_SUMMARY_CACHE_SECONDS=60
```

大图谱完成后，trace 面板不再每次打开都扫描 10 万级图谱统计。

### 4. 运行中 trace 不扫图谱索引

GraphRAG 任务运行中，`trace_graphrag` 只返回：

1. Redis 中的文档进度。
2. 已有缓存的图谱统计。

如果没有缓存，不再强制扫描 ES/Opensearch 图谱索引。任务完成或失败后才允许重新构建统计。

### 5. 前端 GraphRAG 轮询降频

GraphRAG 运行中 trace 轮询从 5 秒一次调整为 10 秒一次。RAPTOR 不变。

### 6. 百分比改为整条任务链条口径

此前抽取器会把“单个文档内部 50%-60% 的局部进度”直接写入任务进度，导致 162 个文件只开始少量文件时，UI 仍可能显示 50%+。

本次改为：

1. 百分比表示整条 GraphRAG 任务链路，而不是单文件局部进度。
2. 抽取阶段按 Redis 文档状态计数计算全库进度。
3. 处理中任务按 0.5 个文档权重计入。
4. 抽取阶段固定落在 2%-55%。
5. 合并/写索引阶段固定落在 55%-80%；如果未启用实体去重和社区，则合并/写索引可推进到 98%。
6. 实体去重解析和社区报告按启用情况分享 80%-98% 的后处理区间。
7. 只有任务真正完成时才写入 100%。

因此 `已开始 5/162、待处理 157` 时，进度条不会再错误显示 58%。

## 对当前远端的操作建议

如果远端旧图谱已经被重新生成任务删除或覆盖，不能再靠代码恢复，只能按新逻辑重新生成。

建议顺序：

1. 先部署包含本次保护的新镜像。
2. 确认后台没有旧 GraphRAG 任务还在 pending/running。
3. 在 UI 里点“重新生成”，确认框确认一次。
4. 后续失败用“中断续跑”，新增文件用“增量更新”，不要再点“重新生成”。

## 验收点

1. 已有图谱时，未携带 `confirm_regenerate=true` 的 `mode=regenerate` 应被拒绝。
2. “中断续跑”请求不应删除旧图谱。
3. “增量更新”请求不应删除旧图谱。
4. 运行中打开生成面板，trace 不应每次触发图谱索引全量统计扫描。
5. 大图谱页面仍走预览加载，不应拉取完整 10 万级图谱 JSON。

## 本地验证

已完成：

```bash
python -m py_compile api\apps\kb_app.py api\apps\sdk\dataset.py
python -m py_compile rag\graphrag\general\index.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_entity_resolution_merge.py test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py test\unit_test\test_vector_mapping_compatibility.py
npm.cmd run build
```

结果：

1. Python 编译通过。
2. GraphRAG/vector 相关单测 27 passed。
3. 前端 production build 通过；仅存在既有的大包、Tailwind line-clamp、pdfjs eval 警告。
