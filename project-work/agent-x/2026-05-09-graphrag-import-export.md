# 2026-05-09 GraphRAG 图谱导入导出功能记录

## 背景

大图谱生成成本高，远端重新部署、误点重新生成、环境迁移时都可能导致已生成图谱丢失或需要重跑。

本次新增 GraphRAG 图谱资产导入导出 V1，用于在同一套 RAGFlow 或不同环境之间迁移已生成图谱。

## UI 入口

知识库左侧菜单中的“知识图谱”改为常驻显示，不再依赖是否已有图谱。

进入“知识图谱”页面后：

1. 没有图谱时显示空状态，并提供“导入图谱”按钮。
2. 有图谱时显示图谱预览，并提供“导入图谱”“导出图谱”“删除图谱”。

这样空知识库或已有文档但尚未生成图谱的知识库，也可以直接导入图谱包。

## 后端接口

新增接口：

```text
GET /kb/<kb_id>/knowledge_graph/export
POST /kb/<kb_id>/knowledge_graph/import/preview
POST /kb/<kb_id>/knowledge_graph/import
```

导出包为 zip，包含：

```text
manifest.json
graph_chunks.jsonl
```

`manifest.json` 记录源知识库、源文件清单、图谱记录数量、图谱类型统计。

`graph_chunks.jsonl` 记录 docStore 中的 GraphRAG 图谱资产：

```text
graph
subgraph
entity
relation
community_report
ty2ents
```

## 导入预检逻辑

导入必须先预检，不直接写库。

预检会检查：

1. 图谱包格式是否正确。
2. 目标知识库是否存在正在运行的 GraphRAG 任务。
3. 目标知识库是否已有图谱。
4. 源文件能否映射到目标知识库文件。
5. 是否存在缺失文件。
6. 是否存在冲突匹配。
7. 图谱向量维度是否被当前 doc engine 支持。

文件映射优先级：

1. `sha256`
2. `name + size + parser_id + suffix`
3. `name + size`
4. `name`

## 场景处理

### 目标文件少了

阻断导入。

原因：图谱里的 `source_id/doc_id` 无法完整映射，节点关联文件、原文下载、增量续跑都会不可靠。

### 目标文件多了

允许导入。

多出的文件不会写入导入图谱，导入后由“增量更新”继续处理。

### 目标已有图谱

默认阻断导入。

前端必须勾选“覆盖当前图谱”，后端收到 `overwrite=true` 后才会先删除旧图谱，再写入导入图谱。

### 文件 ID 不一致但内容一致

允许导入。

导入时会按预检结果重写 `source_id/doc_id`，让图谱映射到目标知识库的新文件 ID。

### 向量维度不兼容

预检阻断。

例如导出包含 6144/8192/10240 维向量，但目标 doc engine 是 Elasticsearch，预检会提前返回不支持，避免写入一半后失败。

## 当前验证

已完成：

```bash
python -m py_compile api\apps\kb_app.py
npm.cmd run build
```

结果：

1. 后端语法校验通过。
2. 前端 production build 通过。
3. build 仅出现既有的大包、Tailwind line-clamp、pdfjs eval 警告。

## 待 Docker/UI 回归

用户已说明本地 Docker 中有 `test` 知识库，且已生成图谱。

后续回归路径：

1. 构建包含本次改动的新镜像。
2. 启动本地 Docker。
3. 登录本地 UI。
4. 进入 `test` 知识库。
5. 导出图谱 zip。
6. 删除当前图谱。
7. 导入刚才导出的 zip。
8. 确认预检通过、导入成功、图谱页面可重新显示。
