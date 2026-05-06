# GraphRAG 中断续跑真实断点修复记录

日期：2026-05-06

## 背景

远端真实任务中，用户点击“中断续跑”后，页面日志显示任务在继续跑，但任务统计长时间显示“已处理 0/162”，并且用户担心续跑只是重新生成，没有真正从断点继续。

## 根因

1. 旧逻辑只把已经合并进全局图谱的文档视为可跳过断点。
2. 单文档抽取完成后，其子图谱已经以 `knowledge_graph_kwd=subgraph` 持久化到索引，但续跑时没有读取这批持久化子图谱。
3. 因此，如果任务中断发生在“子图谱已抽取、但尚未全部合并”的阶段，续跑会重新走抽取流程，而不是直接从已抽取子图谱进入合并。
4. 前端统计的首个数字使用 `completed`，而 `completed` 不包含正在抽取的文档，导致 4 个文件已经开始处理时仍显示 `0/162`。

## 修复内容

1. 新增 `get_subgraphs_by_doc_ids()`，按 `doc_id` 从索引加载已持久化的 `subgraph`。
2. `resume_failed` 任务启动后，会先读取旧任务对应的已落库子图谱。
3. 对于已经加载到子图谱的文档，直接标记为 `extracted` 并进入 merge 阶段，不再重新抽取。
4. 已经进入全局图谱的文档继续按 `merged/skipped` 跳过。
5. 只有没有全局图谱记录、也没有持久化子图谱的文档，才重新抽取。
6. `doc_summary` 新增 `started = total - pending`，前端展示改为“已开始/已完成/已抽取/处理中”，避免正在运行时看起来归零。

## 续跑语义

当前实现的有效断点层级：

1. 已合并入全局图谱的文档：续跑时跳过。
2. 已抽取并持久化子图谱、但未合并的文档：续跑时复用子图谱，直接合并。
3. 正在抽取但尚未完成子图谱持久化的单个文档：仍需重新抽取该文档，但已完成 chunk 的 LLM/embedding 缓存可减少重复模型调用。

## 验证

已执行：

```bash
python -m py_compile rag\graphrag\utils.py rag\graphrag\general\index.py rag\graphrag\task_monitor.py test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py
npm.cmd run build
git diff --check
```

结果：

1. Python 语法检查通过。
2. GraphRAG 相关单测 `13 passed`。
3. 前端 production build 通过。
4. `git diff --check` 通过，仅有 Windows 换行提示。

补充：

`npm.cmd run lint -- --quiet` 仍失败，但失败项为仓库既有全量 lint 问题，本次改动文件没有出现在错误列表中。
