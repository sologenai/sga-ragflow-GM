# GraphRAG 续跑修复镜像构建记录

日期：2026-05-06

## 代码版本

分支：`GM202604`

提交：`d2f2125d9142268861d1806652466c51bff89f5c`

提交说明：`fix: resume GraphRAG from persisted subgraphs`

## 构建过程

1. 先尝试使用根目录 `Dockerfile` 完整构建 `ragflow-custom:latest`。
2. 第一次构建在拉取 `ubuntu:24.04` 阶段遇到 Docker Hub TLS/证书解析异常。
3. 单独执行 `docker pull ubuntu:24.04` 后基础镜像拉取成功。
4. 第二次完整构建运行超过 1 小时，BuildKit 仍未完成，已停止该遗留构建进程，避免后续覆盖镜像标签。
5. 为保证及时交付，改用旧的 `ragflow-custom:latest` 作为基础镜像做 overlay 构建，只覆盖本次修改的后端源码和前端已编译 `web/dist`。

## 新镜像标签

同一个镜像 ID 已打以下标签：

1. `ragflow-custom:latest`
2. `ragflow:GM202604`
3. `ragflow-custom:GM202604-d2f2125d9`

## 镜像验证

已在镜像内验证：

```bash
cat /ragflow/VERSION
grep -n "get_subgraphs_by_doc_ids" /ragflow/rag/graphrag/utils.py /ragflow/rag/graphrag/general/index.py
sed -n "440,465p" /ragflow/rag/graphrag/general/index.py
grep -n "docProgressSummary" -A1 /ragflow/web/src/locales/zh.ts
```

验证结果：

1. `/ragflow/VERSION` 为 `GM202604-d2f2125d9`。
2. 镜像内包含 `get_subgraphs_by_doc_ids()`。
3. 镜像内包含 `resume loaded ... persisted subgraphs` 续跑复用逻辑。
4. 镜像内前端文案已更新为“已开始/已完成/已抽取/处理中”。

## 注意

当前本地正在运行的 `docker-ragflow-gpu-1` 容器仍是启动时绑定的旧镜像层。要让本地容器使用新镜像，需要执行 compose recreate；远端部署同理，必须拉取/导入新镜像并重建容器。
