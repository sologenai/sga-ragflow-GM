# 2026-05-08 GraphRAG 覆盖统计与超大图预览修复

## 背景

远端 `nephrosis` 知识库图谱任务已跑完，但页面仍显示：

- 图谱覆盖：已入图 107/162，待增量 55
- 图谱统计：实体/节点约 118k，关系/边约 143k
- 点击图谱页长时间打不开

现场判断：55 个待增量大概率不是没有入图，而是旧逻辑只读取 `knowledge_graph_kwd=graph` 的全局快照 `source_id`。此前多次 413、续跑和快照写入异常后，全局快照可能只记录了部分文档；但 `subgraph`、`entity`、`relation` 分片里已经有完整 `source_id`。

## 修复内容

1. 覆盖统计不再只信全局 `graph` 快照。
   - 先读 `graph.source_id`。
   - 如果覆盖数小于知识库文档数，再扫描 `subgraph`、`entity`、`relation` 的 `source_id` 合并校正。
   - 这样能把“实际已入图但快照 source_id 不完整”的文档计入覆盖。

2. 增量续跑的文档判断同步修正。
   - `get_graph_doc_ids()` 从 `graph`、`subgraph`、`entity`、`relation` 合并文档 ID。
   - 避免后续点击“增量更新”时，因为旧 graph 快照少 55 个 source_id 又把已处理文档重跑。

3. 超大图页面改为服务端预览。
   - 默认只返回最多 2000 个节点、4000 条边。
   - 后端不再对 10 万级节点执行 NetworkX 社区聚合/label propagation，避免接口长时间卡住。
   - 返回 `graph.preview=true`、总节点/总边、当前可见节点/边等元信息。

4. 前端图谱页改为渐进式披露。
   - 修复 `force-graph.tsx` 里编码损坏导致的潜在编译/运行问题。
   - 初始显示大图骨架预览。
   - 鼠标滚轮放大时，最多逐步请求 5000 节点、10000 边。
   - 按 AntV G6 官方建议启用 `optimize-viewport-transform`，拖拽/缩放时临时隐藏非关键元素，降低大图交互开销。
   - 页面提示“完整图谱请通过搜索定位节点”，不再强行一次性渲染 11 万节点。

## 验证

- `python -m py_compile api\apps\kb_app.py rag\graphrag\utils.py`
- `npm.cmd run build`
- `python -m pytest -q test\unit_test\graphrag\test_graphrag_entity_resolution_merge.py test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py test\unit_test\test_vector_mapping_compatibility.py`

## 镜像

- 代码提交：`cbec3fdf7`
- 镜像标签：`ragflow-custom:GM202604-cbec3fdf7`
- 同步标签：`ragflow-custom:latest`、`ragflow:GM202604`
- 镜像 ID：`86101c4f8153`
- 镜像内校验：`/ragflow/VERSION = GM202604-cbec3fdf7`，`/ragflow/web/dist/index.html` 存在。

## 参考

- AntV G6 `optimize-viewport-transform`: https://g6.antv.antgroup.com/en/manual/behavior/optimize-viewport-transform

## 预期远端表现

1. 图谱任务完成后，覆盖数应从 107/162 校正为接近或等于 162/162。
2. 点击图谱页应快速打开预览，不再等待几十分钟。
3. 对 10 万级图谱，页面展示的是可交互预览，不是完整全量渲染；完整全量渲染在浏览器 force layout 下不可行，后续应走“搜索节点、展开邻域、按类型/文档过滤”的探索式交互。
