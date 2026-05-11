# 2026-05-11 聊天调用日志功能完成记录

## 背景

用户要求在普通聊天链路中补齐调用监控能力，支持按聊天查看用户调用次数、活跃用户数、耗时、Token 估算、错误次数和明细日志。此前智能体有日志页，普通聊天没有对应入口。

## 已完成

- 后端在普通聊天 `/conversation/completion` 和 `ConversationService.async_completion` 中记录调用日志，统一落到 `API4Conversation`，并使用 `source=dialog` 区分智能体运行日志。
- 新增聊天日志接口：
  - `GET /conversation/<dialog_id>/sessions`
  - `GET /conversation/<dialog_id>/sessions/<session_id>`
- 前端在聊天页面增加“日志”入口，新增 `/chat-log-page/:id` 页面。
- 日志页展示核心统计卡片、检索条件、时间范围筛选、分页表格和调用明细弹窗。
- 修复日志页误复用智能体 `AgentLogDetailModal` 导致的 `canvas not found` 问题。
- 修复时间筛选初始请求使用 ISO UTC 导致当天数据短暂显示 0 的问题，统一改为后端接受的本地时间格式 `YYYY-MM-DD HH:mm:ss`。

## 验证

- `python -m py_compile api\db\services\api_service.py api\db\services\conversation_service.py api\apps\conversation_app.py`：通过。
- `npm.cmd run build`：通过，仅保留原有 Tailwind line-clamp、pdfjs eval、chunk size 警告。
- Docker 镜像已构建：
  - `ragflow-custom:GM202604-chat-call-logs-r3-20260511`
  - `ragflow-custom:latest`
  - `ragflow:GM202604`
- 本地容器 `docker-ragflow-gpu-1` 已用 r3 镜像重建并启动。
- Chrome 真实页面验证 `test` 聊天日志页：
  - 调用次数 6
  - 活跃用户 4
  - Token 估算 2121
  - 错误次数 2
  - 未再出现 `/v1/canvas/get` 请求，未再出现 `canvas not found`。

## 注意

- 当前测试数据是为了前端验收手工写入本地 `test` 聊天的 `API4Conversation` 记录，不影响远端真实环境。
- Token 是按聊天消息和引用内容估算，不是模型供应商返回的精确账单 Token。
