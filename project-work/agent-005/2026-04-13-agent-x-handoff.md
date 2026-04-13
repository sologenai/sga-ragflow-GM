# 2026-04-13 Archive Sync Handoff For agent-x

- From: `agent-005`
- To: `agent-x`
- Topic: `档案同步接口联调修正`
- Status: `code implemented / runtime verification pending`

## 1. 本次问题背景

用户反馈“联通档案接口之前虽然有，但一直反应不成功”。

本次联调输入材料：

- 接口 PDF：`docs/档案系统接口文档汇总20260115.pdf`
- 现网日志：`docs/[root@ocr-dgpu35 ocruser]# docker l.txt`
- 业务固定分类：用户给定 19 个分类

## 2. 根因结论

现网失败的直接根因已确认：

1. 档案同步在触发单分类/批量分类同步时，把“分类名”误当成 `doctype` 传给 `queryDataDetail`
2. 日志中可见错误请求例如：
   - `doctype=工会`
   - `doctype=综合行政事务`
   - `doctype=财务管理`
3. 这类值不属于档案接口文档中的 doctype 代码，因此接口返回 0 条数据

次要问题：

1. `queryViewData` 原实现默认 `userid="system"`，不符合接口文档中的员工号要求
2. 档案同步虽然有 `enabled/sync_time` 配置，但服务启动时没有启动档案调度器
3. 分类列表原实现依赖临时抽取结果，不满足当前业务要求的固定 19 类

## 3. 已完成修改

### 3.1 档案分类模型修正

文件：`api/db/services/archive_sync_service.py`

- 新增固定分类常量 `FIXED_CATEGORY_NAMES`
- 刷新分类时直接使用业务确认的 19 个固定分类
- 默认配置中的 `categories` 改为固定分类集

### 3.2 同步逻辑修正

文件：`api/db/services/archive_sync_service.py`

- 新实现的 `sync_category()` 不再把分类名传给 `doctype`
- 改为：
  1. 按日期范围拉取候选档案
  2. 用 `docclassfyname` 在本地过滤到目标分类
  3. 再按知识库映射上传

### 3.3 附件接口 userid 修正

文件：`api/db/services/archive_sync_service.py`

- 新增 `archive_userid` 配置项，默认 `308569`
- `query_archives()` 与 `get_file_url()` 都统一使用该员工号
- 不再使用 `userid="system"`

### 3.4 文件过滤规则

文件：`api/db/services/archive_sync_service.py`

新增过滤：

- 标题或文件名包含 `存证` 的跳过
- 标题或文件名以 `_0` 结尾的跳过

### 3.5 触发接口修正

文件：`api/apps/sync_app.py`

- `/archive/trigger` 改为把前端传入的分类键直接当作“分类名”处理
- 不再走旧的 `doctype + category_name` 混合模式

### 3.6 自动调度补齐

文件：

- `api/db/services/archive_sync_service.py`
- `api/ragflow_server.py`

新增：

- `ArchiveSyncService.start_scheduler()`
- 频率判断：
  - `sync_frequency`
  - `graph_regen_frequency`
- 服务启动时自动启动 Archive Sync Scheduler

## 4. 改动文件清单

- `api/db/services/archive_sync_service.py`
- `api/apps/sync_app.py`
- `api/ragflow_server.py`
- `project-work/agent-005/2026-04-13-role-note.md`
- `project-work/agent-005/2026-04-13-archive-sync-fix-note.md`

## 5. 已完成验证

本地已完成：

- `py_compile` 语法校验通过：
  - `api/db/services/archive_sync_service.py`
  - `api/apps/sync_app.py`
  - `api/ragflow_server.py`

## 6. 未完成验证

当前环境未完成真正联调运行验证，原因是本地 Python 直接导入时缺少依赖：

- `ModuleNotFoundError: No module named 'strenum'`

因此本次交付状态是：

- 代码修正已完成
- 运行时验证需要在用户实际容器环境中完成

## 7. 建议验收步骤

建议 `agent-x` 或用户在目标环境执行：

1. 重启后端容器
2. 打开 `/admin/settings`
3. 点击“刷新分类”，确认显示固定 19 类
4. 重新做分类到知识库的映射
5. 触发一次单分类同步
6. 触发一次全量同步
7. 检查日志是否出现：
   - `Archive Sync Scheduler started.`
   - `Loaded ... candidate archives for category ...`
   - `Skip ... contains 存证`
   - `Skip ... ends with _0`

## 8. 风险与建议

1. `archive_sync_service.py` 当前仍保留了旧版 `sync_category/sync_all_categories` 实现，但已被后置的新实现覆盖；建议后续做一次清理，减少维护歧义
2. `fetch_doctypes()` 当前直接返回固定分类，后面如果业务还想保留“接口实际发现分类”的能力，建议拆成：
   - `fetch_remote_categories()`
   - `get_fixed_categories()`
3. 若后续还要继续稳定交付，建议补一个真实容器环境下的联调验收记录
