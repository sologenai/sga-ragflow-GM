# 2026-05-15 MCP 检索开启知识图谱参数记录

## 背景

国贸项目需要确认 RAGFlow 自带 MCP 服务是否支持在检索时直接开启知识图谱搜索。代码核查结论：

- RAGFlow 自带 MCP Server，入口为 `mcp/server/server.py`。
- Docker 部署通过 `--enable-mcpserver` 开启，默认端口为 `9382`。
- 后端 `/retrieval` 接口已支持 `use_kg` 参数，并在为 `true` 时调用 `settings.kg_retriever.retrieval(...)`。
- MCP 工具层此前没有暴露 `use_kg`，导致 MCP 客户端无法直接打开知识图谱检索。

## 本次改动

1. 在 `ragflow_retrieval` MCP 工具 schema 中新增 `use_kg` 布尔参数。
2. 在 MCP `call_tool` 参数解析中读取 `use_kg`。
3. 在 `RAGFlowConnector.retrieval(...)` 中透传 `use_kg` 到后端 `/retrieval`。
4. 在 MCP 返回的 `query_info` 中增加 `knowledge_graph_search`，方便调用侧确认本次是否启用图谱检索。
5. 更新 MCP 工具文档，说明 `use_kg=true` 仅用于检索已有图谱，不会自动生成图谱。

## 使用方式

MCP 调用 `ragflow_retrieval` 时传入：

```json
{
  "dataset_ids": ["目标知识库ID"],
  "question": "用户问题",
  "use_kg": true
}
```

## 注意事项

- 目标知识库必须已经完成 GraphRAG 图谱生成。
- `use_kg=true` 不会触发图谱生成任务。
- 如果知识库没有图谱，后端不会返回有效图谱证据，检索仍以普通 chunk 召回为主。

## 验证项

- `python -m py_compile mcp/server/server.py`
- 静态核查 MCP schema、参数解析和 `/retrieval` 请求体均包含 `use_kg`。
