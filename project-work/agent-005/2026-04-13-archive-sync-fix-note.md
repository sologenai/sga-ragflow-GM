# 2026-04-13 Archive Sync Fix Note

- Agent: `agent-005`
- Topic: `档案同步接口联调修正`
- Status: `implemented / pending runtime verification`

## Inputs

- 接口材料位置：`docs/档案系统接口文档汇总20260115.pdf`
- 同步报错日志：`docs/[root@ocr-dgpu35 ocruser]# docker l.txt`
- 业务分类：按用户提供图片中的 19 个固定分类

## Root Cause

1. 现网日志显示同步时把“分类名”当成了 `doctype` 去调用 `queryDataDetail`
2. 例如请求中出现了 `doctype=工会 / 综合行政事务 / 财务管理`
3. 这类值不属于接口文档中的 doctype 代码，因此返回 0 条数据

## Implemented Changes

1. 档案分类改为固定分类集，不再依赖临时抽取结果
2. 同步单分类时按 `docclassfyname` 本地过滤，不再把分类名传给 `doctype`
3. `queryViewData` 的 `userid` 改为沿用配置/默认档案员工号，不再使用 `system`
4. 新增过滤规则：
   - 标题或文件名包含 `存证` 的跳过
   - 标题或文件名以 `_0` 结尾的跳过
5. 补齐档案自动调度启动：
   - 服务启动时自动启动 Archive Sync Scheduler
   - 按 `enabled`、`sync_time`、`graph_regen_time`、频率配置执行同步和图谱重建

## Files Changed

- `api/db/services/archive_sync_service.py`
- `api/apps/sync_app.py`
- `api/ragflow_server.py`
