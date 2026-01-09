# RAGFlow 完整使用手册

**版本**: v0.23.1  
**更新日期**: 2026-01-08  
**文档类型**: 完整使用指南

---

## 📋 目录

- [第一章：系统概述](#第一章系统概述)
- [第二章：安装部署](#第二章安装部署)
- [第三章：核心功能](#第三章核心功能)
- [第四章：知识库管理](#第四章知识库管理)
- [第五章：Agent 工作流](#第五章agent-工作流)
- [第六章：知识图谱 GraphRAG](#第六章知识图谱-graphrag)
- [第七章：API 接口](#第七章api-接口)
- [第八章：高级功能](#第八章高级功能)
- [第九章：最佳实践](#第九章最佳实践)
- [第十章：故障排除](#第十章故障排除)
- [附录](#附录)

---

## 第一章：系统概述

### 1.1 什么是 RAGFlow？

RAGFlow 是一款领先的开源检索增强生成（RAG）引擎，通过融合前沿的 RAG 技术与 Agent 能力，为大型语言模型提供卓越的上下文层。它提供可适配任意规模企业的端到端 RAG 工作流，凭借融合式上下文引擎与预置的 Agent 模板，助力开发者以极致效率与精度将复杂数据转化为高可信、生产级的人工智能系统。

### 1.2 核心特性

#### 🍭 "Quality in, quality out"
- **深度文档理解**：基于先进的文档布局分析，从各类复杂格式的非结构化数据中提取真知灼见
- **无限上下文**：真正在无限上下文（token）的场景下快速完成大海捞针测试

#### 🍱 基于模板的文本切片
- **智能可控**：不仅仅是智能，更重要的是可控可解释
- **丰富模板**：多种文本切片模板可供选择（naive, book, email, laws, manual, one, paper, picture, presentation, qa, table, tag）

#### 🌱 有理有据、降低幻觉
- **可视化切片**：文本切片过程可视化，支持手动调整
- **引用追溯**：答案提供关键引用的快照并支持追根溯源

#### 🍔 兼容异构数据源
支持丰富的文件类型：
- 文档：Word、PDF、TXT、Markdown
- 表格：Excel、CSV
- 演示：PPT、PPTX
- 图片：JPEG、PNG、GIF、TIF
- 网页：HTML
- 结构化数据：JSON

#### 🛀 全程无忧的 RAG 工作流
- **全面优化**：支持从个人应用到超大型企业的各类生态系统
- **灵活配置**：LLM 和 Embedding 模型均支持配置
- **智能检索**：多路召回、融合重排序
- **易于集成**：提供易用的 API，可轻松集成到各类企业系统

### 1.3 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAGFlow 系统架构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Web UI     │  │   API 服务   │  │  Agent 引擎  │         │
│  │  (React)     │  │  (Flask)     │  │  (Workflow)  │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐         │
│  │              核心 RAG 引擎                         │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │         │
│  │  │文档解析器│  │ 检索引擎 │  │ GraphRAG │        │         │
│  │  └──────────┘  └──────────┘  └──────────┘        │         │
│  └───────────────────────────────────────────────────┘         │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐         │
│  │              数据存储层                            │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │         │
│  │  │  MySQL   │  │  Redis   │  │  MinIO   │        │         │
│  │  └──────────┘  └──────────┘  └──────────┘        │         │
│  │  ┌──────────┐  ┌──────────┐                      │         │
│  │  │Elasticsearch│ │ Infinity │                     │         │
│  │  └──────────┘  └──────────┘                      │         │
│  └───────────────────────────────────────────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 技术栈

**后端**：
- Python 3.10+
- Flask (API 服务)
- Elasticsearch / Infinity (文档引擎)
- MySQL (元数据存储)
- Redis (缓存和任务队列)
- MinIO (对象存储)

**前端**：
- React 18+
- TypeScript
- Ant Design
- D3.js / AntV G6 (图谱可视化)

**AI 模型**：
- 支持 OpenAI、Azure、Anthropic、Google Gemini 等主流 LLM
- 支持多种 Embedding 模型
- 支持本地部署（Ollama、Xinference、LocalAI）

### 1.5 应用场景

1. **企业知识库问答**：构建企业内部文档的智能问答系统
2. **客户服务**：智能客服机器人，基于产品文档回答用户问题
3. **法律咨询**：法律文书检索和智能分析
4. **医疗诊断辅助**：基于医学文献的诊断建议
5. **研究助手**：学术论文检索和总结
6. **代码助手**：代码库检索和开发辅助
7. **内容创作**：基于知识库的内容生成

### 1.6 版本更新历史

- **2025-11-19**：支持 Gemini 3 Pro
- **2025-11-12**：支持从 Confluence、S3、Notion、Discord、Google Drive 进行数据同步
- **2025-10-23**：支持 MinerU 和 Docling 作为文档解析方法
- **2025-10-15**：支持可编排的数据管道
- **2025-08-08**：支持 OpenAI 最新的 GPT-5 系列模型
- **2025-08-01**：支持 agentic workflow 和 MCP
- **2025-05-23**：Agent 新增 Python/JS 代码执行器组件
- **2025-05-05**：支持跨语言查询
- **2025-03-19**：PDF 和 DOCX 中的图支持用多模态大模型解析

---

## 第二章：安装部署

### 2.1 系统要求

#### 硬件要求
- **CPU**：≥ 4 核心（推荐 8 核心）
- **内存**：≥ 16 GB（推荐 32 GB）
- **磁盘**：≥ 50 GB（推荐 SSD，100 GB+）
- **GPU**：可选，用于加速文档解析（支持 NVIDIA GPU）

#### 软件要求
- **操作系统**：Linux（推荐 Ubuntu 20.04+）、macOS、Windows（WSL2）
- **Docker**：≥ 24.0.0
- **Docker Compose**：≥ v2.26.1
- **gVisor**：仅在使用代码执行器（沙箱）功能时需要

### 2.2 Docker 部署（推荐）

#### 2.2.1 准备工作

1. **设置 vm.max_map_count**（Linux/macOS）

```bash
# 检查当前值
sysctl vm.max_map_count

# 临时设置（重启后失效）
sudo sysctl -w vm.max_map_count=262144

# 永久设置
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**macOS Docker Desktop 用户**：
```bash
docker run --rm --privileged --pid=host alpine sysctl -w vm.max_map_count=262144
```

**Windows WSL2 用户**：
```bash
wsl -d docker-desktop -u root
sysctl -w vm.max_map_count=262144
```

2. **克隆代码仓库**

```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/docker
git checkout v0.23.1  # 使用稳定版本
```

#### 2.2.2 配置环境变量

编辑 `.env` 文件：

```bash
# 基础配置
RAGFLOW_IMAGE=infiniflow/ragflow:v0.23.1
SVR_HTTP_PORT=9380
TIMEZONE=Asia/Shanghai

# 数据库配置
MYSQL_PASSWORD=infini_rag_flow
MYSQL_DBNAME=rag_flow
MYSQL_USER=root

# MinIO 配置
MINIO_USER=rag_flow
MINIO_PASSWORD=infini_rag_flow

# Elasticsearch 配置
ELASTIC_PASSWORD=infini_rag_flow

# Redis 配置
REDIS_PASSWORD=infini_rag_flow

# 可选：使用 GPU 加速
# DEVICE=gpu

# 可选：使用国内镜像
# HF_ENDPOINT=https://hf-mirror.com
```

#### 2.2.3 启动服务

```bash
# 使用 CPU 版本
docker compose -f docker-compose.yml up -d

# 使用 GPU 版本（需要 NVIDIA GPU 和 nvidia-docker）
sed -i '1i DEVICE=gpu' .env
docker compose -f docker-compose.yml up -d
```

#### 2.2.4 验证部署

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker logs -f docker-ragflow-cpu-1

# 等待以下输出表示启动成功：
#      ____   ___    ______ ______ __
#     / __ \ /   |  / ____// ____// /____  _      __
#    / /_/ // /| | / / __ / /_   / // __ \| | /| / /
#   / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ /
#  /_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/
#
#  * Running on all addresses (0.0.0.0)
```

#### 2.2.5 访问系统

打开浏览器访问：`http://localhost:9380`

默认管理员账号：
- 邮箱：`admin@ragflow.io`
- 密码：`admin`（首次登录后请修改）

### 2.3 源码部署（开发环境）

#### 2.3.1 安装依赖

```bash
# 安装 uv 和 pre-commit
pipx install uv pre-commit

# 设置国内镜像（可选）
export UV_INDEX=https://mirrors.aliyun.com/pypi/simple

# 克隆代码
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/

# 安装 Python 依赖
uv sync --python 3.10
uv run download_deps.py
pre-commit install
```

#### 2.3.2 启动基础服务

```bash
# 启动 MySQL、Redis、MinIO、Elasticsearch
docker compose -f docker/docker-compose-base.yml up -d

# 配置 hosts（将服务名解析到本地）
echo "127.0.0.1 es01 infinity mysql minio redis sandbox-executor-manager" | sudo tee -a /etc/hosts
```

#### 2.3.3 配置 HuggingFace 镜像（可选）

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

#### 2.3.4 安装 jemalloc

```bash
# Ubuntu
sudo apt-get install libjemalloc-dev

# CentOS
sudo yum install jemalloc

# macOS
brew install jemalloc
```

#### 2.3.5 启动后端服务

```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh
```

#### 2.3.6 启动前端服务

```bash
cd web
npm install
npm run dev
```

访问：`http://localhost:5173`

### 2.4 配置 LLM 模型

#### 2.4.1 配置文件位置

- Docker 部署：`docker/service_conf.yaml.template`
- 源码部署：`conf/service_conf.yaml`

#### 2.4.2 配置示例

```yaml
user_default_llm:
  default_models:
    # Embedding 模型
    embedding_model:
      api_key: 'your-api-key'
      base_url: 'http://localhost:80'
      model_name: 'BAAI/bge-large-zh-v1.5'

    # Chat 模型
    chat_model:
      factory: 'OpenAI'
      api_key: 'sk-xxx'
      model_name: 'gpt-4'

    # 图像理解模型
    image2text_model:
      factory: 'OpenAI'
      api_key: 'sk-xxx'
      model_name: 'gpt-4-vision-preview'

    # 重排序模型（可选）
    rerank_model:
      factory: 'Jina'
      api_key: 'jina-xxx'
      model_name: 'jina-reranker-v1-base-en'
```

#### 2.4.3 支持的模型厂商

- **OpenAI**：GPT-4、GPT-3.5、GPT-5 系列
- **Azure OpenAI**：Azure 托管的 OpenAI 模型
- **Anthropic**：Claude 系列
- **Google**：Gemini 系列
- **国内厂商**：通义千问、文心一言、智谱 AI、DeepSeek 等
- **本地部署**：Ollama、Xinference、LocalAI、LM Studio

### 2.5 切换文档引擎

RAGFlow 支持两种文档引擎：

#### 2.5.1 Elasticsearch（默认）

优点：成熟稳定，功能丰富
缺点：资源占用较大

#### 2.5.2 Infinity

优点：轻量级，性能更好
缺点：功能相对较少

**切换到 Infinity**：

```bash
# 停止所有容器
docker compose -f docker/docker-compose.yml down -v

# 修改 .env 文件
echo "DOC_ENGINE=infinity" >> docker/.env

# 重新启动
docker compose -f docker-compose.yml up -d
```

⚠️ **注意**：切换引擎会清空现有数据！

---

## 第三章:核心功能

### 3.1 用户管理

#### 3.1.1 注册与登录

1. **首次访问**:访问 `http://localhost:9380`
2. **注册账号**:
   - 点击"Sign up"
   - 填写邮箱、昵称、密码
   - 点击"Sign up"完成注册
3. **登录系统**:
   - 输入邮箱和密码
   - 点击"Sign in"

#### 3.1.2 用户设置

**修改个人信息**:
- 点击右上角头像 → "Settings"
- 可修改:昵称、头像、密码

**API Key 管理**:
- Settings → "API Keys"
- 点击"Create new key"生成 API 密钥
- 用于 API 调用认证

### 3.2 模型配置

#### 3.2.1 添加模型

1. **进入模型管理**:
   - 点击右上角头像 → "Model Providers"

2. **添加 LLM 模型**:
   - 点击"Add model"
   - 选择厂商(如 OpenAI)
   - 填写配置:
     ```
     Factory: OpenAI
     Model name: gpt-4
     API Key: sk-xxx
     Base URL: https://api.openai.com/v1 (可选)
     ```
   - 点击"Save"

3. **添加 Embedding 模型**:
   - 同样流程,选择 Embedding 类型
   - 推荐模型:
     - 中文:`BAAI/bge-large-zh-v1.5`
     - 英文:`text-embedding-ada-002`
     - 多语言:`multilingual-e5-large`

#### 3.2.2 模型测试

- 添加模型后,点击"Test"按钮
- 输入测试文本,验证模型是否正常工作

#### 3.2.3 设置默认模型

- 在模型列表中,点击星标图标
- 设置为默认模型,新建知识库时自动使用

### 3.3 文件上传与解析

#### 3.3.1 支持的文件类型

| 类型 | 格式 | 说明 |
|------|------|------|
| 文档 | PDF, DOCX, DOC, TXT, MD | 支持扫描件 OCR |
| 表格 | XLSX, XLS, CSV | 自动识别表格结构 |
| 演示 | PPTX, PPT | 提取文本和图片 |
| 图片 | JPG, PNG, GIF, TIF, BMP | 支持 OCR 和多模态理解 |
| 网页 | HTML | 保留结构化信息 |
| 代码 | JSON, XML | 结构化解析 |

#### 3.3.2 文档解析方法

RAGFlow 提供多种解析方法:

1. **Naive**:
   - 适用:纯文本文档
   - 特点:快速,简单,不保留格式

2. **Paper**:
   - 适用:学术论文
   - 特点:识别标题、摘要、章节、参考文献

3. **Book**:
   - 适用:书籍、长文档
   - 特点:识别章节结构,保留层级关系

4. **Laws**:
   - 适用:法律文书
   - 特点:识别条款、编号、层级结构

5. **Presentation**:
   - 适用:PPT、演示文稿
   - 特点:按页解析,保留标题和内容

6. **Manual**:
   - 适用:产品手册、技术文档
   - 特点:识别步骤、列表、表格

7. **QA**:
   - 适用:问答对
   - 特点:自动识别问题和答案

8. **Table**:
   - 适用:表格数据
   - 特点:保留表格结构,支持跨行跨列

9. **Picture**:
   - 适用:图片为主的文档
   - 特点:使用多模态模型理解图片内容

10. **One**:
    - 适用:单页文档
    - 特点:整个文档作为一个切片

11. **Email**:
    - 适用:邮件
    - 特点:识别发件人、收件人、主题、正文

12. **Tag**:
    - 适用:带标签的文档
    - 特点:基于 HTML 标签解析

#### 3.3.3 高级解析选项

**MinerU**:
- 基于深度学习的文档解析
- 更准确的布局识别
- 适合复杂排版的文档

**Docling**:
- IBM 开源的文档解析工具
- 支持多种文档格式
- 高质量的结构化提取

**配置方法**:
```yaml
# service_conf.yaml
doc_engine:
  parser: "minerU"  # 或 "docling"
```

### 3.4 文本切片

#### 3.4.1 切片策略

**为什么需要切片?**
- LLM 有上下文长度限制
- 提高检索精度
- 减少无关信息干扰

**切片原则**:
- 保持语义完整性
- 适当的切片大小(推荐 300-800 tokens)
- 切片之间有重叠(推荐 50-150 tokens)

#### 3.4.2 切片参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| Chunk size | 切片大小 | 512 tokens |
| Chunk overlap | 切片重叠 | 100 tokens |
| Min chunk size | 最小切片大小 | 50 tokens |
| Max chunk size | 最大切片大小 | 2048 tokens |

#### 3.4.3 手动调整切片

1. **查看切片结果**:
   - 上传文档后,点击"Chunks"标签
   - 查看自动生成的切片

2. **编辑切片**:
   - 点击切片卡片
   - 修改切片内容
   - 点击"Save"

3. **合并切片**:
   - 选择多个切片
   - 点击"Merge"

4. **删除切片**:
   - 选择切片
   - 点击"Delete"

5. **添加切片**:
   - 点击"Add chunk"
   - 输入内容
   - 点击"Save"

### 3.5 向量化与索引

#### 3.5.1 向量化流程

```
文档上传 → 解析 → 切片 → Embedding → 存储到向量数据库
```

#### 3.5.2 Embedding 模型选择

**中文场景**:
- `BAAI/bge-large-zh-v1.5` (推荐)
- `BAAI/bge-base-zh-v1.5`
- `text2vec-large-chinese`

**英文场景**:
- `text-embedding-ada-002` (OpenAI)
- `text-embedding-3-large` (OpenAI,最新)
- `BAAI/bge-large-en-v1.5`

**多语言场景**:
- `multilingual-e5-large`
- `paraphrase-multilingual-mpnet-base-v2`

#### 3.5.3 索引优化

**重建索引**:
- 当切换 Embedding 模型时需要重建
- 知识库设置 → "Rebuild index"

**索引状态**:
- ✅ Indexed:已索引
- ⏳ Indexing:索引中
- ❌ Failed:索引失败

---

## 第四章:知识库管理

### 4.1 创建知识库

#### 4.1.1 基础创建流程

1. **进入知识库页面**:
   - 点击左侧菜单"Knowledge Base"

2. **创建新知识库**:
   - 点击"Create knowledge base"
   - 填写基本信息:
     ```
     Name: 我的知识库
     Description: 用于存储产品文档
     Permission: Private (私有) / Team (团队) / Public (公开)
     ```

3. **选择解析方法**:
   - 根据文档类型选择合适的解析方法
   - 例如:技术文档选择"Manual",论文选择"Paper"

4. **配置切片参数**:
   ```
   Chunk method: General
   Chunk size: 512
   Chunk overlap: 100
   ```

5. **选择模型**:
   - Embedding model: BAAI/bge-large-zh-v1.5
   - (可选) Rerank model: bge-reranker-large

6. **点击"Create"完成创建**

#### 4.1.2 高级配置

**权限设置**:
- **Private**:仅创建者可见
- **Team**:团队成员可见
- **Public**:所有人可见(仅查看)

**解析配置**:
```yaml
# 自定义解析规则
parser_config:
  layout_recognize: true  # 启用布局识别
  formula_enable: true    # 识别数学公式
  table_min_rows: 2       # 表格最小行数
```

### 4.2 上传文档

#### 4.2.1 本地上传

1. **进入知识库**:
   - 点击知识库名称进入详情页

2. **上传文件**:
   - 点击"Upload"按钮
   - 选择文件(支持批量上传)
   - 或拖拽文件到上传区域

3. **配置解析选项**:
   - 选择解析方法(可覆盖知识库默认设置)
   - 设置切片参数

4. **开始解析**:
   - 点击"Start parsing"
   - 等待解析完成

#### 4.2.2 从网页抓取

1. **点击"Web Crawl"**:
   - 输入网页 URL
   - 设置抓取深度(1-3 层)
   - 设置最大页面数

2. **配置抓取规则**:
   ```
   Include patterns: /docs/*, /blog/*
   Exclude patterns: /admin/*, /login
   ```

3. **开始抓取**:
   - 点击"Start crawling"
   - 系统自动抓取并解析网页

#### 4.2.3 从云存储同步

**支持的数据源**:
- Amazon S3
- Google Drive
- Notion
- Confluence
- Discord
- 本地文件夹

**配置 S3 同步**:
```yaml
datasource:
  type: s3
  config:
    bucket: my-bucket
    region: us-east-1
    access_key: xxx
    secret_key: xxx
    prefix: documents/
```

**自动同步**:
- 设置同步频率(每小时/每天/每周)
- 自动检测文件变化
- 增量更新

### 4.3 文档管理

#### 4.3.1 文档列表

**查看文档**:
- 文档名称、大小、上传时间
- 解析状态、切片数量
- 操作:编辑、删除、重新解析

**搜索文档**:
- 按文件名搜索
- 按标签筛选
- 按状态筛选

#### 4.3.2 文档详情

**基本信息**:
- 文件名、大小、类型
- 上传时间、解析时间
- 切片数量、向量数量

**切片预览**:
- 查看所有切片
- 编辑切片内容
- 调整切片顺序

**元数据**:
- 自定义标签
- 文档分类
- 优先级设置

#### 4.3.3 批量操作

**批量上传**:
- 选择多个文件
- 统一解析设置
- 并行处理

**批量删除**:
- 选择多个文档
- 确认删除
- 同时删除向量索引

**批量重新解析**:
- 选择文档
- 修改解析参数
- 重新生成切片和向量

### 4.4 检索配置

#### 4.4.1 检索策略

**向量检索**:
- 基于语义相似度
- 使用 Embedding 模型
- 快速、准确

**全文检索**:
- 基于关键词匹配
- 使用 Elasticsearch/Infinity
- 支持布尔查询

**混合检索**:
- 结合向量和全文检索
- 融合排序(Fusion Ranking)
- 最佳效果

#### 4.4.2 检索参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| Top K | 返回结果数量 | 5-10 |
| Similarity threshold | 相似度阈值 | 0.3-0.7 |
| Rerank | 是否重排序 | 开启 |
| Rerank top N | 重排序候选数 | 20-50 |

**配置示例**:
```yaml
retrieval:
  vector:
    enabled: true
    top_k: 10
    similarity_threshold: 0.5

  keyword:
    enabled: true
    top_k: 10

  rerank:
    enabled: true
    model: bge-reranker-large
    top_n: 30
```

#### 4.4.3 高级检索

**多路召回**:
```python
# 同时使用多种检索方式
retrieval_config = {
    "vector": {"weight": 0.6, "top_k": 10},
    "keyword": {"weight": 0.3, "top_k": 10},
    "graph": {"weight": 0.1, "top_k": 5}
}
```

**查询改写**:
- 自动扩展查询词
- 同义词替换
- 多语言翻译

**过滤条件**:
```python
# 按元数据过滤
filters = {
    "category": "技术文档",
    "date": {"$gte": "2024-01-01"},
    "tags": {"$in": ["Python", "AI"]}
}
```

### 4.5 知识库测试

#### 4.5.1 测试检索

1. **进入测试页面**:
   - 知识库详情 → "Test"标签

2. **输入测试问题**:
   - 例如:"如何安装 RAGFlow?"

3. **查看检索结果**:
   - 相关切片列表
   - 相似度分数
   - 来源文档

4. **调整参数**:
   - 修改 Top K、相似度阈值
   - 重新测试
   - 对比效果

#### 4.5.2 评估指标

**准确率(Precision)**:
- 检索结果中相关文档的比例
- 计算公式:`相关文档数 / 总检索文档数`

**召回率(Recall)**:
- 相关文档被检索出的比例
- 计算公式:`检索到的相关文档数 / 总相关文档数`

**MRR (Mean Reciprocal Rank)**:
- 第一个相关结果的排名倒数
- 评估排序质量

**NDCG (Normalized Discounted Cumulative Gain)**:
- 考虑排序位置的综合指标
- 越高越好

#### 4.5.3 优化建议

**检索效果不佳时**:
1. 检查 Embedding 模型是否合适
2. 调整切片大小和重叠
3. 启用重排序
4. 增加 Top K 值
5. 降低相似度阈值

**检索速度慢时**:
1. 减少 Top K 值
2. 优化索引结构
3. 使用 GPU 加速
4. 考虑使用 Infinity 引擎

---

## 第五章:Agent 工作流

### 5.1 Agent 概述

#### 5.1.1 什么是 Agent?

Agent 是 RAGFlow 的智能工作流引擎,可以:
- 编排多个步骤的复杂任务
- 调用外部工具和 API
- 执行代码(Python/JavaScript)
- 实现自主决策和规划

#### 5.1.2 Agent 架构

```
┌─────────────────────────────────────────┐
│           Agent Workflow                │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────┐   ┌──────┐   ┌──────┐       │
│  │ 开始 │──→│ 节点 │──→│ 结束 │       │
│  └──────┘   └──┬───┘   └──────┘       │
│                │                        │
│           ┌────┴────┐                  │
│           │         │                  │
│        ┌──▼──┐   ┌──▼──┐              │
│        │节点A│   │节点B│              │
│        └─────┘   └─────┘              │
│                                         │
└─────────────────────────────────────────┘
```

#### 5.1.3 核心组件

**节点类型**:
- **Begin**:工作流起点
- **Answer**:生成回答
- **Retrieval**:检索知识库
- **Generate**:调用 LLM 生成内容
- **Categorize**:分类判断
- **Message**:发送消息
- **Relevant**:相关性判断
- **RewriteQuestion**:问题改写
- **KeywordExtract**:关键词提取
- **Baidu**:百度搜索
- **DuckDuckGo**:DuckDuckGo 搜索
- **Wikipedia**:维基百科搜索
- **PubMed**:医学文献搜索
- **ArXiv**:学术论文搜索
- **Google**:Google 搜索
- **Bing**:Bing 搜索
- **GitHub**:GitHub 搜索
- **StackOverflow**:StackOverflow 搜索
- **WeatherAPI**:天气查询
- **ExeSQL**:执行 SQL 查询
- **ExePython**:执行 Python 代码
- **ExeJS**:执行 JavaScript 代码
- **Switch**:条件分支
- **Template**:模板渲染
- **Concentrator**:结果聚合
- **Email**:发送邮件
- **Webhook**:调用 Webhook
- **HTTP**:HTTP 请求

### 5.2 创建 Agent

#### 5.2.1 使用模板创建

1. **进入 Agent 页面**:
   - 点击左侧菜单"Agent"

2. **选择模板**:
   - **Simple RAG**:基础问答
   - **Deep RAG**:深度检索问答
   - **Self RAG**:自我反思 RAG
   - **Agentic RAG**:智能 Agent RAG
   - **Research Assistant**:研究助手
   - **Customer Service**:客服机器人
   - **Code Assistant**:代码助手
   - **Data Analyst**:数据分析师

3. **配置 Agent**:
   ```
   Name: 我的客服机器人
   Description: 基于产品文档的智能客服
   Prologue: 您好!我是智能客服,有什么可以帮您?
   ```

4. **点击"Create"**

#### 5.2.2 从空白创建

1. **创建空白 Agent**:
   - 点击"Create from scratch"

2. **添加节点**:
   - 从左侧工具栏拖拽节点到画布
   - 或点击"+"按钮添加

3. **连接节点**:
   - 拖拽节点的输出端口到另一个节点的输入端口
   - 形成工作流

4. **配置节点**:
   - 点击节点打开配置面板
   - 设置节点参数

### 5.3 节点详解

#### 5.3.1 Begin 节点

**作用**:工作流的起点,接收用户输入

**配置**:
```yaml
begin:
  inputs:
    - name: question
      type: string
      required: true
    - name: user_id
      type: string
      required: false
```

**输出变量**:
- `question`:用户问题
- `user_id`:用户 ID
- `session_id`:会话 ID

#### 5.3.2 Retrieval 节点

**作用**:从知识库检索相关文档

**配置**:
```yaml
retrieval:
  knowledge_bases:
    - kb_id_1
    - kb_id_2
  top_k: 10
  similarity_threshold: 0.5
  rerank: true
  rerank_model: bge-reranker-large
```

**输入变量**:
- `query`:检索查询(通常来自 Begin 或 RewriteQuestion)

**输出变量**:
- `chunks`:检索到的文档切片列表
- `references`:引用信息

#### 5.3.3 Generate 节点

**作用**:调用 LLM 生成内容

**配置**:
```yaml
generate:
  model: gpt-4
  prompt: |
    基于以下上下文回答问题:

    上下文:
    {context}

    问题:
    {question}

    回答:
  temperature: 0.7
  max_tokens: 2000
  stream: true
```

**输入变量**:
- `context`:上下文(通常来自 Retrieval)
- `question`:问题
- 其他自定义变量

**输出变量**:
- `content`:生成的内容
- `tokens_used`:使用的 token 数

#### 5.3.4 Answer 节点

**作用**:返回最终答案给用户

**配置**:
```yaml
answer:
  content: "{generate.content}"
  references: "{retrieval.references}"
```

**输入变量**:
- `content`:答案内容
- `references`:引用来源

#### 5.3.5 Categorize 节点

**作用**:对输入进行分类

**配置**:
```yaml
categorize:
  categories:
    - name: 产品咨询
      description: 关于产品功能、价格、使用方法的问题
    - name: 技术支持
      description: 关于技术问题、故障排查的问题
    - name: 投诉建议
      description: 投诉或建议
    - name: 其他
      description: 其他类型的问题
  model: gpt-4
```

**输出变量**:
- `category`:分类结果
- `confidence`:置信度

#### 5.3.6 RewriteQuestion 节点

**作用**:改写用户问题,提高检索效果

**配置**:
```yaml
rewrite_question:
  model: gpt-4
  prompt: |
    将以下问题改写为更适合检索的形式:

    原问题:{question}

    改写后的问题:
  chat_history: true  # 考虑对话历史
```

**输出变量**:
- `rewritten_question`:改写后的问题

#### 5.3.7 ExePython 节点

**作用**:执行 Python 代码

**配置**:
```yaml
exe_python:
  code: |
    import json

    # 处理数据
    data = json.loads(input_data)
    result = sum(data['numbers'])

    # 返回结果
    output = {"sum": result}
  timeout: 30  # 超时时间(秒)
  sandbox: true  # 使用沙箱环境
```

**输入变量**:
- 代码中可以使用的变量(如 `input_data`)

**输出变量**:
- `output`:代码执行结果
- `stdout`:标准输出
- `stderr`:标准错误

#### 5.3.8 Switch 节点

**作用**:条件分支

**配置**:
```yaml
switch:
  conditions:
    - condition: "{categorize.category} == '产品咨询'"
      next: product_kb_retrieval
    - condition: "{categorize.category} == '技术支持'"
      next: tech_kb_retrieval
    - condition: "default"
      next: general_answer
```

#### 5.3.9 HTTP 节点

**作用**:调用外部 API

**配置**:
```yaml
http:
  method: POST
  url: https://api.example.com/v1/analyze
  headers:
    Content-Type: application/json
    Authorization: Bearer {api_key}
  body: |
    {
      "text": "{question}",
      "language": "zh"
    }
  timeout: 30
```

**输出变量**:
- `response`:响应内容
- `status_code`:HTTP 状态码
- `headers`:响应头

### 5.4 工作流示例

#### 5.4.1 简单 RAG 工作流

```
Begin → Retrieval → Generate → Answer
```

**配置**:
1. **Begin**:接收用户问题
2. **Retrieval**:从知识库检索相关文档
3. **Generate**:基于检索结果生成答案
4. **Answer**:返回答案

#### 5.4.2 智能客服工作流

```
Begin → Categorize → Switch
                       ├→ 产品咨询 → Product KB → Generate → Answer
                       ├→ 技术支持 → Tech KB → Generate → Answer
                       └→ 其他 → General Answer → Answer
```

**流程说明**:
1. 接收用户问题
2. 分类问题类型
3. 根据类型路由到不同的知识库
4. 生成针对性的答案

#### 5.4.3 研究助手工作流

```
Begin → RewriteQuestion → Parallel Search
                            ├→ ArXiv Search
                            ├→ PubMed Search
                            └→ Wikipedia Search
                          → Concentrator → Generate Summary → Answer
```

**流程说明**:
1. 改写研究问题
2. 并行搜索多个数据源
3. 聚合搜索结果
4. 生成综合摘要

#### 5.4.4 数据分析工作流

```
Begin → ExeSQL → ExePython → Generate Insights → Answer
```

**流程说明**:
1. 接收分析需求
2. 执行 SQL 查询获取数据
3. 用 Python 进行数据分析
4. 生成分析报告

### 5.5 Agent 调试与测试

#### 5.5.1 调试模式

**启用调试**:
- 点击工作流编辑器右上角的"Debug"按钮
- 输入测试问题
- 查看每个节点的执行结果

**调试信息**:
- 节点输入/输出
- 执行时间
- 错误信息
- 变量值

#### 5.5.2 日志查看

**查看执行日志**:
- Agent 详情页 → "Logs"标签
- 查看历史执行记录
- 筛选错误日志

**日志内容**:
```json
{
  "session_id": "xxx",
  "timestamp": "2026-01-08T10:30:00Z",
  "nodes": [
    {
      "name": "begin",
      "status": "success",
      "duration": 10,
      "input": {"question": "如何安装?"},
      "output": {"question": "如何安装?"}
    },
    {
      "name": "retrieval",
      "status": "success",
      "duration": 150,
      "input": {"query": "如何安装?"},
      "output": {"chunks": [...]}
    }
  ]
}
```

#### 5.5.3 性能优化

**优化建议**:
1. **减少节点数量**:合并相似功能的节点
2. **并行执行**:使用并行分支加速处理
3. **缓存结果**:对重复查询启用缓存
4. **异步处理**:长时间任务使用异步节点
5. **限制检索数量**:减少 Top K 值

---

## 第六章:知识图谱 GraphRAG

### 6.1 GraphRAG 概述

#### 6.1.1 什么是 GraphRAG?

GraphRAG 是 RAGFlow 的知识图谱增强检索功能,通过构建实体和关系的图谱,提供更精准的知识检索和推理能力。

**优势**:
- **关系推理**:发现实体之间的隐含关系
- **多跳查询**:支持复杂的多步推理
- **知识融合**:整合多个文档的知识
- **可解释性**:提供清晰的推理路径

#### 6.1.2 GraphRAG 架构

```
文档 → 实体抽取 → 关系抽取 → 图谱构建 → 图谱检索 → 答案生成
```

**核心组件**:
- **实体识别**:识别文档中的实体(人名、地名、组织等)
- **关系抽取**:抽取实体之间的关系
- **图谱存储**:使用图数据库存储知识图谱
- **图谱查询**:基于图结构的检索和推理

### 6.2 创建知识图谱

#### 6.2.1 启用 GraphRAG

1. **创建知识库时启用**:
   - 创建知识库 → 高级设置
   - 勾选"Enable GraphRAG"

2. **配置图谱参数**:
   ```yaml
   graph_config:
     entity_types:
       - Person
       - Organization
       - Location
       - Product
       - Concept

     relation_types:
       - works_for
       - located_in
       - produces
       - related_to

     extraction_model: gpt-4
     min_confidence: 0.7
   ```

#### 6.2.2 实体和关系抽取

**自动抽取**:
- 上传文档后自动进行实体和关系抽取
- 使用 LLM 识别实体和关系
- 构建知识图谱

**手动标注**:
- 查看抽取结果
- 修正错误的实体和关系
- 添加遗漏的信息

**抽取示例**:
```
文本:"张三在北京的阿里巴巴公司工作。"

实体:
- 张三 (Person)
- 北京 (Location)
- 阿里巴巴 (Organization)

关系:
- 张三 --works_for--> 阿里巴巴
- 阿里巴巴 --located_in--> 北京
```

### 6.3 图谱可视化

#### 6.3.1 查看图谱

1. **进入图谱页面**:
   - 知识库详情 → "Graph"标签

2. **图谱展示**:
   - 节点:实体
   - 边:关系
   - 颜色:实体类型
   - 粗细:关系强度

#### 6.3.2 交互操作

**缩放和平移**:
- 鼠标滚轮:缩放
- 拖拽:平移
- 双击节点:展开相关节点

**筛选**:
- 按实体类型筛选
- 按关系类型筛选
- 按置信度筛选

**搜索**:
- 搜索特定实体
- 高亮显示相关路径

### 6.4 图谱检索

#### 6.4.1 基于图谱的检索

**单跳查询**:
```
问题:"张三在哪个公司工作?"

图谱查询:
MATCH (p:Person {name: "张三"})-[:works_for]->(o:Organization)
RETURN o.name

结果:"阿里巴巴"
```

**多跳查询**:
```
问题:"张三的公司在哪个城市?"

图谱查询:
MATCH (p:Person {name: "张三"})-[:works_for]->(o:Organization)-[:located_in]->(l:Location)
RETURN l.name

结果:"北京"
```

#### 6.4.2 混合检索

**结合向量和图谱**:
1. 向量检索:找到相关文档
2. 图谱检索:找到相关实体和关系
3. 融合排序:综合两种结果
4. 生成答案:基于融合结果

**配置**:
```yaml
hybrid_retrieval:
  vector_weight: 0.6
  graph_weight: 0.4
  fusion_method: rrf  # Reciprocal Rank Fusion
```

### 6.5 高级功能

#### 6.5.1 社区检测

**发现实体社区**:
- 使用 Louvain 算法
- 识别紧密相关的实体群
- 用于主题聚类

**应用场景**:
- 发现研究领域
- 识别业务模块
- 分析组织结构

#### 6.5.2 路径查询

**最短路径**:
```
问题:"张三和李四有什么关系?"

查询:找到张三到李四的最短路径

结果:
张三 --works_for--> 阿里巴巴 <--works_for-- 李四
```

**所有路径**:
- 查找两个实体之间的所有路径
- 发现隐含关系

#### 6.5.3 图谱推理

**传递关系推理**:
```
已知:
- A located_in B
- B located_in C

推理:
- A located_in C (传递)
```

**对称关系推理**:
```
已知:
- A married_to B

推理:
- B married_to A (对称)
```

---

## 第七章:API 接口

### 7.1 API 概述

#### 7.1.1 认证方式

**API Key 认证**:
```bash
curl -X POST http://localhost:9380/api/v1/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

**获取 API Key**:
- 登录系统 → Settings → API Keys
- 点击"Create new key"
- 复制并保存 API Key

#### 7.1.2 API 基础信息

**Base URL**:
```
http://localhost:9380/api/v1
```

**请求格式**:
- Content-Type: `application/json`
- 编码: UTF-8

**响应格式**:
```json
{
  "code": 0,
  "message": "success",
  "data": {...}
}
```

**错误码**:
- `0`:成功
- `400`:请求参数错误
- `401`:未授权
- `404`:资源不存在
- `500`:服务器错误

### 7.2 知识库 API

#### 7.2.1 创建知识库

**请求**:
```bash
POST /api/v1/knowledge_bases

{
  "name": "我的知识库",
  "description": "用于存储产品文档",
  "permission": "private",
  "parser_method": "manual",
  "chunk_size": 512,
  "chunk_overlap": 100,
  "embedding_model": "BAAI/bge-large-zh-v1.5"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "kb_id": "kb_123456",
    "name": "我的知识库",
    "created_at": "2026-01-08T10:00:00Z"
  }
}
```

#### 7.2.2 上传文档

**请求**:
```bash
POST /api/v1/knowledge_bases/{kb_id}/documents

Content-Type: multipart/form-data

file: <binary>
parser_method: manual (可选)
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "doc_id": "doc_123456",
    "name": "document.pdf",
    "status": "parsing"
  }
}
```

#### 7.2.3 查询知识库

**请求**:
```bash
POST /api/v1/knowledge_bases/{kb_id}/retrieval

{
  "query": "如何安装 RAGFlow?",
  "top_k": 10,
  "similarity_threshold": 0.5,
  "rerank": true
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "chunks": [
      {
        "chunk_id": "chunk_123",
        "content": "安装 RAGFlow 的步骤...",
        "score": 0.85,
        "doc_id": "doc_123",
        "doc_name": "安装指南.pdf"
      }
    ]
  }
}
```

### 7.3 对话 API

#### 7.3.1 创建对话

**请求**:
```bash
POST /api/v1/chats

{
  "name": "客服对话",
  "agent_id": "agent_123",
  "knowledge_base_ids": ["kb_123", "kb_456"]
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "chat_id": "chat_123456",
    "name": "客服对话",
    "created_at": "2026-01-08T10:00:00Z"
  }
}
```

#### 7.3.2 发送消息

**请求**:
```bash
POST /api/v1/chats/{chat_id}/messages

{
  "question": "如何安装 RAGFlow?",
  "stream": false
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "安装 RAGFlow 的步骤如下:\n1. 安装 Docker...",
    "references": [
      {
        "chunk_id": "chunk_123",
        "content": "...",
        "doc_name": "安装指南.pdf"
      }
    ]
  }
}
```

#### 7.3.3 流式对话

**请求**:
```bash
POST /api/v1/chats/{chat_id}/messages

{
  "question": "如何安装 RAGFlow?",
  "stream": true
}
```

**响应**(SSE 格式):
```
data: {"answer": "安装", "delta": "安装"}

data: {"answer": "安装 RAGFlow", "delta": " RAGFlow"}

data: {"answer": "安装 RAGFlow 的步骤", "delta": " 的步骤"}

...

data: {"done": true, "references": [...]}
```

### 7.4 Agent API

#### 7.4.1 运行 Agent

**请求**:
```bash
POST /api/v1/agents/{agent_id}/run

{
  "inputs": {
    "question": "分析最近一周的销售数据"
  },
  "stream": false
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "session_123",
    "output": {
      "answer": "最近一周的销售数据分析...",
      "charts": [...]
    }
  }
}
```

### 7.5 SDK 使用

#### 7.5.1 Python SDK

**安装**:
```bash
pip install ragflow-sdk
```

**基础使用**:
```python
from ragflow import RAGFlow

# 初始化客户端
client = RAGFlow(
    api_key="YOUR_API_KEY",
    base_url="http://localhost:9380"
)

# 创建知识库
kb = client.create_knowledge_base(
    name="我的知识库",
    parser_method="manual"
)

# 上传文档
doc = kb.upload_document("document.pdf")

# 等待解析完成
doc.wait_for_parsing()

# 检索
results = kb.retrieve(
    query="如何安装?",
    top_k=5
)

# 对话
chat = client.create_chat(
    knowledge_base_ids=[kb.id]
)

answer = chat.ask("如何安装 RAGFlow?")
print(answer.content)
```

**流式对话**:
```python
for chunk in chat.ask_stream("如何安装 RAGFlow?"):
    print(chunk.delta, end="", flush=True)
```

#### 7.5.2 JavaScript SDK

**安装**:
```bash
npm install ragflow-sdk
```

**基础使用**:
```javascript
import { RAGFlow } from 'ragflow-sdk';

// 初始化客户端
const client = new RAGFlow({
  apiKey: 'YOUR_API_KEY',
  baseURL: 'http://localhost:9380'
});

// 创建知识库
const kb = await client.createKnowledgeBase({
  name: '我的知识库',
  parserMethod: 'manual'
});

// 上传文档
const doc = await kb.uploadDocument('document.pdf');

// 等待解析完成
await doc.waitForParsing();

// 检索
const results = await kb.retrieve({
  query: '如何安装?',
  topK: 5
});

// 对话
const chat = await client.createChat({
  knowledgeBaseIds: [kb.id]
});

const answer = await chat.ask('如何安装 RAGFlow?');
console.log(answer.content);
```

**流式对话**:
```javascript
const stream = await chat.askStream('如何安装 RAGFlow?');

for await (const chunk of stream) {
  process.stdout.write(chunk.delta);
}
```

---

## 第八章:高级功能

### 8.1 多模态理解

#### 8.1.1 图片理解

**配置图片理解模型**:
```yaml
image2text_model:
  factory: OpenAI
  model_name: gpt-4-vision-preview
  api_key: sk-xxx
```

**使用场景**:
- 解析包含图表的 PDF
- 理解产品图片
- 分析设计稿

**示例**:
```python
# 上传包含图片的文档
doc = kb.upload_document(
    "product_manual.pdf",
    parser_method="picture"  # 使用图片解析模式
)

# 系统会自动使用多模态模型理解图片内容
```

#### 8.1.2 表格理解

**表格解析**:
- 自动识别表格结构
- 保留行列关系
- 支持跨行跨列

**配置**:
```yaml
table_config:
  min_rows: 2
  min_cols: 2
  preserve_structure: true
```

### 8.2 跨语言查询

#### 8.2.1 启用跨语言

**配置**:
```yaml
cross_language:
  enabled: true
  source_languages: [zh, en, ja, ko]
  translation_model: gpt-4
```

**工作原理**:
1. 检测查询语言
2. 翻译为目标语言
3. 在多语言文档中检索
4. 翻译结果回源语言

#### 8.2.2 使用示例

```python
# 中文查询,检索英文文档
results = kb.retrieve(
    query="如何安装?",
    cross_language=True
)

# 系统会自动:
# 1. 将"如何安装?"翻译为"How to install?"
# 2. 在英文文档中检索
# 3. 将结果翻译回中文
```

### 8.3 数据管道

#### 8.3.1 创建数据管道

**什么是数据管道?**
- 可编排的数据处理流程
- 支持多种数据源
- 自动化数据同步

**创建管道**:
```yaml
pipeline:
  name: 文档同步管道

  source:
    type: s3
    config:
      bucket: my-bucket
      prefix: documents/

  processors:
    - type: filter
      config:
        extensions: [pdf, docx]

    - type: transform
      config:
        rename_pattern: "{date}_{name}"

  destination:
    type: knowledge_base
    config:
      kb_id: kb_123
      parser_method: auto

  schedule:
    cron: "0 */6 * * *"  # 每 6 小时执行一次
```

#### 8.3.2 数据源集成

**支持的数据源**:
- **S3**:Amazon S3、MinIO、阿里云 OSS
- **Google Drive**:Google 云端硬盘
- **Notion**:Notion 工作区
- **Confluence**:Atlassian Confluence
- **Discord**:Discord 频道
- **GitHub**:GitHub 仓库
- **本地文件夹**:监控本地目录

**配置示例 - Notion**:
```yaml
source:
  type: notion
  config:
    token: secret_xxx
    database_id: xxx
    filter:
      property: Status
      value: Published
```

**配置示例 - GitHub**:
```yaml
source:
  type: github
  config:
    token: ghp_xxx
    repo: owner/repo
    branch: main
    paths:
      - docs/
      - README.md
```

### 8.4 代码执行器

#### 8.4.1 沙箱环境

**gVisor 沙箱**:
- 安全隔离的代码执行环境
- 支持 Python 和 JavaScript
- 限制资源使用

**安装 gVisor**:
```bash
# Ubuntu
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list
sudo apt-get update && sudo apt-get install -y runsc

# 配置 Docker
sudo runsc install
sudo systemctl restart docker
```

#### 8.4.2 Python 代码执行

**示例**:
```python
# 在 Agent 中使用 ExePython 节点
code = """
import pandas as pd
import json

# 读取数据
data = json.loads(input_data)
df = pd.DataFrame(data)

# 数据分析
summary = {
    'total': len(df),
    'mean': df['value'].mean(),
    'max': df['value'].max(),
    'min': df['value'].min()
}

# 返回结果
output = json.dumps(summary)
"""

# 配置节点
exe_python_node = {
    "type": "ExePython",
    "config": {
        "code": code,
        "timeout": 30,
        "sandbox": True
    }
}
```

**可用的 Python 库**:
- pandas
- numpy
- matplotlib
- scikit-learn
- requests
- beautifulsoup4

#### 8.4.3 JavaScript 代码执行

**示例**:
```javascript
// 在 Agent 中使用 ExeJS 节点
const code = `
const data = JSON.parse(inputData);

// 数据处理
const result = data.map(item => ({
  ...item,
  processed: true,
  timestamp: new Date().toISOString()
}));

// 返回结果
output = JSON.stringify(result);
`;

// 配置节点
const exeJsNode = {
  type: "ExeJS",
  config: {
    code: code,
    timeout: 30,
    sandbox: true
  }
};
```

### 8.5 MCP (Model Context Protocol)

#### 8.5.1 什么是 MCP?

MCP 是 Anthropic 提出的模型上下文协议,用于:
- 标准化 AI 应用的上下文管理
- 提供统一的工具调用接口
- 支持多模型协作

#### 8.5.2 在 RAGFlow 中使用 MCP

**配置 MCP 服务器**:
```yaml
mcp:
  enabled: true
  servers:
    - name: filesystem
      command: npx
      args: [-y, @modelcontextprotocol/server-filesystem, /path/to/allowed/files]

    - name: github
      command: npx
      args: [-y, @modelcontextprotocol/server-github]
      env:
        GITHUB_TOKEN: ghp_xxx
```

**在 Agent 中使用**:
```python
# MCP 工具会自动注册到 Agent
# 可以在 Generate 节点的 prompt 中引用

prompt = """
使用 filesystem 工具读取 /data/report.txt 文件,
然后总结其内容。
"""
```

---

## 第九章:最佳实践

### 9.1 知识库设计

#### 9.1.1 知识库划分原则

**按主题划分**:
- ✅ 好:产品文档、技术文档、FAQ 分别建库
- ❌ 差:所有文档混在一个库

**按更新频率划分**:
- ✅ 好:静态文档和动态文档分开
- ❌ 差:频繁更新的文档影响整个库的索引

**按权限划分**:
- ✅ 好:公开文档和内部文档分开
- ❌ 差:权限混乱,安全风险

#### 9.1.2 文档准备

**文档质量**:
- 确保文档内容准确、完整
- 避免扫描件质量差导致 OCR 错误
- 统一文档格式和命名规范

**文档结构**:
- 使用清晰的标题层级
- 添加目录和索引
- 保持段落结构清晰

**元数据**:
- 添加文档标签
- 记录文档版本
- 标注文档来源

### 9.2 切片优化

#### 9.2.1 选择合适的切片大小

**根据文档类型**:
- 长文档(书籍):800-1200 tokens
- 中等文档(文章):400-800 tokens
- 短文档(FAQ):200-400 tokens

**根据查询类型**:
- 精确查询:较小切片(300-500 tokens)
- 概括查询:较大切片(800-1200 tokens)

#### 9.2.2 切片重叠策略

**重叠比例**:
- 推荐:10%-20% 的切片大小
- 例如:切片 500 tokens,重叠 50-100 tokens

**为什么需要重叠?**
- 避免关键信息被切断
- 保持上下文连贯性
- 提高检索召回率

#### 9.2.3 手动优化切片

**何时需要手动优化?**
- 自动切片效果不理想
- 关键信息被切断
- 需要特殊处理的文档

**优化方法**:
1. 查看自动切片结果
2. 识别问题切片
3. 手动调整切片边界
4. 测试检索效果
5. 迭代优化

### 9.3 检索优化

#### 9.3.1 选择合适的 Embedding 模型

**中文场景**:
- 首选:`BAAI/bge-large-zh-v1.5`
- 备选:`text2vec-large-chinese`

**英文场景**:
- 首选:`text-embedding-3-large` (OpenAI)
- 备选:`BAAI/bge-large-en-v1.5`

**多语言场景**:
- 首选:`multilingual-e5-large`

#### 9.3.2 启用重排序

**为什么需要重排序?**
- 向量检索可能不够精确
- 重排序模型专门优化排序任务
- 显著提升 Top 5 的准确率

**推荐模型**:
- `bge-reranker-large`
- `jina-reranker-v1-base-en`

**配置**:
```yaml
rerank:
  enabled: true
  model: bge-reranker-large
  top_n: 30  # 从 30 个候选中重排序选出 Top K
```

#### 9.3.3 混合检索策略

**向量 + 关键词**:
```yaml
hybrid_retrieval:
  vector:
    enabled: true
    weight: 0.7
    top_k: 20

  keyword:
    enabled: true
    weight: 0.3
    top_k: 20

  fusion: rrf  # Reciprocal Rank Fusion
```

**向量 + 图谱**:
```yaml
hybrid_retrieval:
  vector:
    enabled: true
    weight: 0.6

  graph:
    enabled: true
    weight: 0.4
    max_hops: 2
```

### 9.4 Prompt 工程

#### 9.4.1 系统 Prompt 设计

**基础模板**:
```
你是一个专业的客服助手,基于提供的上下文回答用户问题。

规则:
1. 只基于上下文回答,不要编造信息
2. 如果上下文中没有相关信息,明确告知用户
3. 回答要准确、简洁、友好
4. 提供具体的步骤或示例
5. 必要时引用来源文档

上下文:
{context}

问题:
{question}

回答:
```

**领域定制**:
```
你是一个医疗咨询助手,基于医学文献回答问题。

重要提示:
- 提供的信息仅供参考,不能替代专业医疗建议
- 建议用户咨询专业医生
- 引用权威医学文献

上下文:
{context}

问题:
{question}

回答:
```

#### 9.4.2 Few-shot 示例

**添加示例**:
```
以下是一些示例:

问题:如何安装 Docker?
回答:安装 Docker 的步骤如下:
1. 更新系统包:sudo apt-get update
2. 安装依赖:sudo apt-get install ca-certificates curl
3. 添加 Docker 官方 GPG 密钥...
[来源:Docker 官方文档]

问题:Docker 和虚拟机有什么区别?
回答:Docker 和虚拟机的主要区别:
1. 架构:Docker 使用容器技术,虚拟机使用 Hypervisor
2. 资源占用:Docker 更轻量,启动更快
3. 隔离性:虚拟机隔离性更强...
[来源:Docker 技术白皮书]

现在回答用户的问题:
{question}
```

#### 9.4.3 输出格式控制

**结构化输出**:
```
请按以下格式回答:

## 简短回答
[一句话总结]

## 详细说明
[详细步骤或解释]

## 相关资源
[相关文档链接]

## 注意事项
[需要注意的点]
```

**JSON 输出**:
```
请以 JSON 格式返回结果:

{
  "answer": "简短回答",
  "steps": ["步骤1", "步骤2", "步骤3"],
  "references": ["文档1", "文档2"],
  "confidence": 0.95
}
```

### 9.5 性能优化

#### 9.5.1 索引优化

**定期重建索引**:
```bash
# 当数据量增长到一定程度时重建索引
# 提高检索速度
```

**分片策略**:
- Elasticsearch:合理设置分片数
- 推荐:每个分片 20-50GB

**缓存策略**:
```yaml
cache:
  enabled: true
  ttl: 3600  # 缓存 1 小时
  max_size: 1000  # 最多缓存 1000 个查询
```

#### 9.5.2 并发控制

**限流配置**:
```yaml
rate_limit:
  requests_per_minute: 60
  concurrent_requests: 10
```

**批处理**:
```python
# 批量上传文档
docs = kb.upload_documents_batch([
    "doc1.pdf",
    "doc2.pdf",
    "doc3.pdf"
], batch_size=10)
```

#### 9.5.3 资源监控

**监控指标**:
- CPU 使用率
- 内存使用率
- 磁盘 I/O
- 网络带宽
- 请求延迟
- 错误率

**告警设置**:
```yaml
alerts:
  - metric: cpu_usage
    threshold: 80
    action: email

  - metric: error_rate
    threshold: 5
    action: slack
```

---

## 第十章:故障排除

### 10.1 常见问题

#### 10.1.1 安装问题

**问题:Docker 启动失败**

```bash
# 错误信息
ERROR: max virtual memory areas vm.max_map_count [65530] is too low

# 解决方案
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

**问题:端口被占用**

```bash
# 错误信息
Error starting userland proxy: listen tcp4 0.0.0.0:9380: bind: address already in use

# 解决方案 1:修改端口
# 编辑 .env 文件
SVR_HTTP_PORT=9381

# 解决方案 2:停止占用端口的进程
sudo lsof -i :9380
sudo kill -9 <PID>
```

**问题:容器无法启动**

```bash
# 查看日志
docker logs docker-ragflow-cpu-1

# 常见原因:
# 1. 内存不足:增加 Docker 内存限制
# 2. 磁盘空间不足:清理磁盘空间
# 3. 依赖服务未启动:检查 MySQL、Redis、ES 状态
```

#### 10.1.2 文档解析问题

**问题:PDF 解析失败**

```
可能原因:
1. PDF 是扫描件,需要 OCR
2. PDF 加密或有密码保护
3. PDF 格式损坏

解决方案:
1. 使用 picture 解析方法启用 OCR
2. 先解密 PDF
3. 尝试重新生成 PDF
```

**问题:中文乱码**

```
可能原因:
1. 编码问题
2. 字体缺失

解决方案:
1. 确保文档使用 UTF-8 编码
2. 安装中文字体包
   sudo apt-get install fonts-wqy-zenhei
```

**问题:表格识别不准确**

```
解决方案:
1. 使用 table 解析方法
2. 调整表格识别参数
3. 考虑使用 MinerU 或 Docling
```

#### 10.1.3 检索问题

**问题:检索结果不相关**

```
可能原因:
1. Embedding 模型不合适
2. 切片大小不合适
3. 相似度阈值设置不当

解决方案:
1. 更换 Embedding 模型
2. 调整切片参数
3. 降低相似度阈值
4. 启用重排序
```

**问题:检索速度慢**

```
可能原因:
1. 数据量太大
2. Top K 设置过大
3. 索引未优化

解决方案:
1. 减少 Top K 值
2. 启用缓存
3. 重建索引
4. 考虑使用 Infinity 引擎
5. 增加硬件资源
```

**问题:检索结果为空**

```
可能原因:
1. 文档未索引完成
2. 相似度阈值过高
3. 查询语言与文档语言不匹配

解决方案:
1. 检查文档索引状态
2. 降低相似度阈值
3. 启用跨语言查询
```

#### 10.1.4 API 问题

**问题:401 Unauthorized**

```
可能原因:
1. API Key 错误
2. API Key 过期
3. 权限不足

解决方案:
1. 检查 API Key 是否正确
2. 重新生成 API Key
3. 检查用户权限
```

**问题:429 Too Many Requests**

```
可能原因:
1. 超过速率限制

解决方案:
1. 减少请求频率
2. 使用批处理
3. 联系管理员提高限额
```

**问题:500 Internal Server Error**

```
可能原因:
1. 服务器错误
2. 模型调用失败
3. 数据库连接失败

解决方案:
1. 查看服务器日志
2. 检查模型配置
3. 检查数据库连接
```

### 10.2 日志分析

#### 10.2.1 查看日志

**Docker 部署**:
```bash
# 查看主服务日志
docker logs -f docker-ragflow-cpu-1

# 查看 Elasticsearch 日志
docker logs -f docker-es01-1

# 查看 MySQL 日志
docker logs -f docker-mysql-1
```

**源码部署**:
```bash
# 后端日志
tail -f logs/ragflow.log

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

#### 10.2.2 日志级别

**配置日志级别**:
```yaml
# service_conf.yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/ragflow.log
  max_bytes: 10485760  # 10MB
  backup_count: 5
```

#### 10.2.3 常见错误日志

**Embedding 模型错误**:
```
ERROR: Failed to get embedding: Connection timeout
解决:检查模型服务是否正常,网络是否通畅
```

**数据库连接错误**:
```
ERROR: (2003, "Can't connect to MySQL server on 'mysql'")
解决:检查 MySQL 服务状态,检查连接配置
```

**内存不足**:
```
ERROR: Out of memory
解决:增加系统内存或 Docker 内存限制
```

### 10.3 性能调优

#### 10.3.1 数据库优化

**MySQL 优化**:
```sql
-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query_log';
SET GLOBAL slow_query_log = 'ON';

-- 添加索引
CREATE INDEX idx_kb_id ON documents(kb_id);
CREATE INDEX idx_created_at ON documents(created_at);

-- 优化表
OPTIMIZE TABLE documents;
```

**Elasticsearch 优化**:
```bash
# 调整 JVM 堆内存
# docker-compose.yml
environment:
  - "ES_JAVA_OPTS=-Xms4g -Xmx4g"

# 调整刷新间隔
PUT /ragflow_index/_settings
{
  "index": {
    "refresh_interval": "30s"
  }
}
```

#### 10.3.2 缓存优化

**Redis 配置**:
```yaml
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

**应用层缓存**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(text):
    # 缓存 Embedding 结果
    return embedding_model.encode(text)
```

#### 10.3.3 并发优化

**异步处理**:
```python
import asyncio

async def process_documents(docs):
    tasks = [process_doc(doc) for doc in docs]
    results = await asyncio.gather(*tasks)
    return results
```

**队列处理**:
```python
# 使用 Celery 处理耗时任务
from celery import Celery

app = Celery('ragflow', broker='redis://localhost:6379')

@app.task
def parse_document(doc_id):
    # 异步解析文档
    pass
```

### 10.4 备份与恢复

#### 10.4.1 数据备份

**备份脚本**:
```bash
#!/bin/bash

BACKUP_DIR="/backup/ragflow/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份 MySQL
docker exec docker-mysql-1 mysqldump -u root -pinfini_rag_flow rag_flow > $BACKUP_DIR/mysql.sql

# 备份 MinIO
docker exec docker-minio-1 mc mirror /data $BACKUP_DIR/minio

# 备份 Elasticsearch
docker exec docker-es01-1 curl -X PUT "localhost:9200/_snapshot/backup/snapshot_$(date +%Y%m%d)" -H 'Content-Type: application/json' -d'
{
  "indices": "ragflow_*",
  "ignore_unavailable": true,
  "include_global_state": false
}'

echo "Backup completed: $BACKUP_DIR"
```

**定时备份**:
```bash
# 添加到 crontab
0 2 * * * /path/to/backup.sh
```

#### 10.4.2 数据恢复

**恢复 MySQL**:
```bash
docker exec -i docker-mysql-1 mysql -u root -pinfini_rag_flow rag_flow < backup/mysql.sql
```

**恢复 MinIO**:
```bash
docker exec docker-minio-1 mc mirror backup/minio /data
```

**恢复 Elasticsearch**:
```bash
docker exec docker-es01-1 curl -X POST "localhost:9200/_snapshot/backup/snapshot_20260108/_restore"
```

---

## 附录

### A. 配置文件参考

#### A.1 service_conf.yaml

```yaml
# RAGFlow 服务配置文件

# 服务器配置
server:
  host: 0.0.0.0
  port: 9380
  workers: 4
  timeout: 300

# 数据库配置
database:
  type: mysql
  host: mysql
  port: 3306
  user: root
  password: infini_rag_flow
  database: rag_flow
  pool_size: 10
  max_overflow: 20

# Redis 配置
redis:
  host: redis
  port: 6379
  password: infini_rag_flow
  db: 0
  max_connections: 50

# MinIO 配置
minio:
  endpoint: minio:9000
  access_key: rag_flow
  secret_key: infini_rag_flow
  secure: false
  bucket: ragflow

# Elasticsearch 配置
elasticsearch:
  hosts:
    - es01:9200
  username: elastic
  password: infini_rag_flow
  index_prefix: ragflow_

# 文档引擎
doc_engine:
  type: elasticsearch  # 或 infinity
  parser: auto  # auto, minerU, docling

# 默认模型配置
user_default_llm:
  default_models:
    embedding_model:
      factory: Xinference
      api_key: xxx
      base_url: http://localhost:80
      model_name: BAAI/bge-large-zh-v1.5

    chat_model:
      factory: OpenAI
      api_key: sk-xxx
      model_name: gpt-4

    image2text_model:
      factory: OpenAI
      api_key: sk-xxx
      model_name: gpt-4-vision-preview

    rerank_model:
      factory: Jina
      api_key: jina-xxx
      model_name: jina-reranker-v1-base-en

# 日志配置
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/ragflow.log
  max_bytes: 10485760
  backup_count: 5

# 安全配置
security:
  secret_key: your-secret-key-here
  jwt_expiration: 86400  # 24 小时
  password_hash_rounds: 12

# 限流配置
rate_limit:
  enabled: true
  requests_per_minute: 60
  concurrent_requests: 10

# 缓存配置
cache:
  enabled: true
  ttl: 3600
  max_size: 1000
```

### B. API 参考

#### B.1 完整 API 列表

**知识库 API**:
- `POST /api/v1/knowledge_bases` - 创建知识库
- `GET /api/v1/knowledge_bases` - 列出知识库
- `GET /api/v1/knowledge_bases/{kb_id}` - 获取知识库详情
- `PUT /api/v1/knowledge_bases/{kb_id}` - 更新知识库
- `DELETE /api/v1/knowledge_bases/{kb_id}` - 删除知识库
- `POST /api/v1/knowledge_bases/{kb_id}/documents` - 上传文档
- `GET /api/v1/knowledge_bases/{kb_id}/documents` - 列出文档
- `DELETE /api/v1/knowledge_bases/{kb_id}/documents/{doc_id}` - 删除文档
- `POST /api/v1/knowledge_bases/{kb_id}/retrieval` - 检索

**对话 API**:
- `POST /api/v1/chats` - 创建对话
- `GET /api/v1/chats` - 列出对话
- `GET /api/v1/chats/{chat_id}` - 获取对话详情
- `DELETE /api/v1/chats/{chat_id}` - 删除对话
- `POST /api/v1/chats/{chat_id}/messages` - 发送消息
- `GET /api/v1/chats/{chat_id}/messages` - 获取消息历史

**Agent API**:
- `POST /api/v1/agents` - 创建 Agent
- `GET /api/v1/agents` - 列出 Agent
- `GET /api/v1/agents/{agent_id}` - 获取 Agent 详情
- `PUT /api/v1/agents/{agent_id}` - 更新 Agent
- `DELETE /api/v1/agents/{agent_id}` - 删除 Agent
- `POST /api/v1/agents/{agent_id}/run` - 运行 Agent

**用户 API**:
- `POST /api/v1/auth/register` - 注册
- `POST /api/v1/auth/login` - 登录
- `POST /api/v1/auth/logout` - 登出
- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户信息
- `POST /api/v1/users/api_keys` - 创建 API Key
- `GET /api/v1/users/api_keys` - 列出 API Key
- `DELETE /api/v1/users/api_keys/{key_id}` - 删除 API Key

### C. 术语表

- **RAG (Retrieval-Augmented Generation)**: 检索增强生成,结合检索和生成的 AI 技术
- **Embedding**: 向量嵌入,将文本转换为数值向量
- **Chunk**: 文本切片,将长文档分割成的小段
- **LLM (Large Language Model)**: 大型语言模型
- **Rerank**: 重排序,对检索结果进行二次排序
- **GraphRAG**: 基于知识图谱的 RAG
- **Agent**: 智能代理,可以自主执行任务的 AI 系统
- **MCP (Model Context Protocol)**: 模型上下文协议
- **OCR (Optical Character Recognition)**: 光学字符识别
- **Top K**: 返回前 K 个结果
- **Similarity Threshold**: 相似度阈值

### D. 资源链接

**官方资源**:
- 官网: https://ragflow.io
- GitHub: https://github.com/infiniflow/ragflow
- 文档: https://ragflow.io/docs
- Discord: https://discord.gg/ragflow

**相关项目**:
- Infinity: https://github.com/infiniflow/infinity
- MinerU: https://github.com/opendatalab/MinerU
- Docling: https://github.com/DS4SD/docling

**学习资源**:
- RAG 论文: https://arxiv.org/abs/2005.11401
- GraphRAG 论文: https://arxiv.org/abs/2404.16130
- Embedding 模型排行榜: https://huggingface.co/spaces/mteb/leaderboard

### E. 常见问题 FAQ

**Q: RAGFlow 是免费的吗?**
A: RAGFlow 是开源项目,可以免费使用。但使用的 LLM 和 Embedding 模型可能需要付费。

**Q: RAGFlow 支持私有化部署吗?**
A: 支持,可以完全在本地部署,不依赖外部服务。

**Q: RAGFlow 支持哪些语言?**
A: 支持中文、英文、日文、韩文等多种语言,具体取决于使用的模型。

**Q: 如何选择 Embedding 模型?**
A: 根据文档语言选择:中文用 bge-large-zh,英文用 text-embedding-3-large,多语言用 multilingual-e5-large。

**Q: 检索效果不好怎么办?**
A: 尝试:1) 更换 Embedding 模型 2) 调整切片参数 3) 启用重排序 4) 使用混合检索。

**Q: RAGFlow 和 LangChain 有什么区别?**
A: RAGFlow 是完整的 RAG 系统,开箱即用;LangChain 是开发框架,需要自己组装。

**Q: 可以使用本地模型吗?**
A: 可以,支持 Ollama、Xinference、LocalAI 等本地部署方案。

**Q: 数据安全吗?**
A: 私有化部署时,所有数据都在本地,不会上传到外部服务器。

**Q: 支持多租户吗?**
A: 支持,可以为不同用户/团队创建独立的知识库和权限。

**Q: 如何升级 RAGFlow?**
A: Docker 部署:拉取新镜像并重启容器。源码部署:git pull 并重新安装依赖。

---

## 结语

本手册涵盖了 RAGFlow 的核心功能和使用方法,从基础安装到高级特性,从知识库管理到 Agent 工作流,从 API 集成到性能优化。

RAGFlow 是一个功能强大且不断发展的 RAG 平台,建议:

1. **从简单开始**: 先创建一个小型知识库,熟悉基本流程
2. **逐步优化**: 根据实际效果调整参数和策略
3. **关注更新**: RAGFlow 更新频繁,关注新功能和改进
4. **参与社区**: 在 GitHub 和 Discord 与其他用户交流经验

如有问题,欢迎:
- 查阅官方文档: https://ragflow.io/docs
- 提交 Issue: https://github.com/infiniflow/ragflow/issues
- 加入 Discord: https://discord.gg/ragflow

祝使用愉快! 🎉

---

**文档版本**: v1.0
**最后更新**: 2026-01-08
**作者**: RAGFlow 社区
**许可**: CC BY-SA 4.0

