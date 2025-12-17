# RAGFlow API 完整使用指南

> **版本**: v0.22.1  
> **更新日期**: 2025-12-16  
> **用途**: 前后端联调完整参考文档

## 📋 目录

- [1. 概述](#1-概述)
- [2. 认证方式](#2-认证方式)
- [3. Agent相关接口](#3-agent相关接口)
- [4. 知识库相关接口](#4-知识库相关接口)
- [5. 文件管理接口](#5-文件管理接口)
- [6. 对话管理接口](#6-对话管理接口)
- [7. 知识图谱接口](#7-知识图谱接口)
- [8. 前端调用场景](#8-前端调用场景)

---

## 1. 概述

### 1.1 基础信息

- **Base URL**: `http://localhost:8080/v1` (Web UI接口)
- **SDK Base URL**: `http://localhost:8080/api/v1` (SDK接口)
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

### 1.2 通用响应格式

```json
{
  "retcode": 0,           // 0表示成功，非0表示失败
  "retmsg": "success",    // 响应消息
  "data": {}              // 响应数据
}
```

### 1.3 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 100 | 参数错误 |
| 101 | 数据错误 |
| 102 | 权限错误 |
| 500 | 服务器错误 |

---

## 2. 认证方式

### 2.1 用户登录认证 (Web UI)

**请求头**:
```http
Authorization: <jwt_token>
```

**获取Token**: 通过登录接口获取

```http
POST /v1/user/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "access_token": "jwt_token_here",
    "user_id": "user_id"
  }
}
```

### 2.2 API Token认证 (SDK)

**请求头**:
```http
Authorization: Bearer <api_token>
```

**创建API Token**:

```http
POST /v1/api/new_token
Authorization: <jwt_token>
Content-Type: application/json

{
  "dialog_id": "dialog_id",  // 可选
  "tenant_id": "tenant_id"
}
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "token": "ragflow-xxxxxxxxxxxxxxxx",
    "tenant_id": "xxx"
  }
}
```

---

## 3. Agent相关接口

### 3.1 创建Agent

**接口**: `POST /api/v1/agents`

**认证**: Bearer Token

**请求体**:
```json
{
  "title": "我的智能助手",
  "description": "这是一个智能客服Agent",
  "dsl": {
    "components": [
      {
        "id": "begin",
        "obj": {
          "component_name": "Begin",
          "params": {}
        }
      },
      {
        "id": "llm_1",
        "obj": {
          "component_name": "LLM",
          "params": {
            "model_name": "gpt-3.5-turbo",
            "temperature": 0.7
          }
        }
      }
    ],
    "history": [],
    "path": [["begin", "llm_1"]],
    "answer": ["llm_1"]
  },
  "canvas_category": "Agent"
}
```

**响应**:
```json
{
  "retcode": 0,
  "retmsg": "success",
  "data": true
}
```

### 3.2 获取Agent列表

**接口**: `GET /api/v1/agents`

**查询参数**:
- `page`: 页码 (默认: 1)
- `page_size`: 每页数量 (默认: 30, 最大: 100)
- `orderby`: 排序字段 (update_time, create_time)
- `desc`: 是否降序 (true/false)
- `id`: Agent ID (精确匹配)
- `title`: Agent标题 (模糊匹配)

**示例请求**:
```http
GET /api/v1/agents?page=1&page_size=10&orderby=update_time&desc=true
Authorization: Bearer ragflow-xxx
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "total": 25,
    "agents": [
      {
        "id": "agent_123",
        "title": "智能客服",
        "description": "处理客户咨询",
        "dsl": {},
        "canvas_category": "Agent",
        "create_time": "2025-12-16T10:00:00",
        "update_time": "2025-12-16T15:30:00",
        "user_id": "user_456"
      }
    ]
  }
}
```

### 3.3 更新Agent

**接口**: `PUT /api/v1/agents/<agent_id>`

**请求体**:
```json
{
  "title": "更新后的标题",
  "description": "更新后的描述",
  "dsl": {
    "components": [],
    "history": [],
    "path": [],
    "answer": []
  }
}
```

**响应**:
```json
{
  "retcode": 0,
  "data": true
}
```

### 3.4 删除Agent

**接口**: `DELETE /api/v1/agents/<agent_id>`

**响应**:
```json
{
  "retcode": 0,
  "data": true
}
```

### 3.5 运行Agent (Webhook)

**接口**: `POST /api/v1/webhook/<agent_id>`

**请求体**:
```json
{
  "id": "agent_id",
  "query": "帮我查询订单状态",
  "files": [],
  "user_id": "user_123"
}
```

**响应**: Server-Sent Events (SSE) 流式返回

```
data: {"code": 0, "message": "开始处理", "data": {"step": "begin"}}

data: {"code": 0, "message": "LLM处理中", "data": {"step": "llm", "content": "正在查询..."}}

data: {"code": 0, "message": "完成", "data": {"step": "answer", "content": "您的订单状态是..."}}
```

**Agent返回内容结构**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "step": "component_id",      // 当前执行的组件ID
    "content": "输出内容",        // 组件输出
    "trace": {                    // 执行轨迹
      "component_name": "LLM",
      "input": {},
      "output": {},
      "duration": 1.23
    },
    "logs": ["日志1", "日志2"],  // 执行日志
    "final_answer": "最终答案"    // 最终结果
  }
}
```

### 3.6 获取Agent模板

**接口**: `GET /v1/canvas/templates`

**响应**:
```json
{
  "retcode": 0,
  "data": [
    {
      "id": "template_1",
      "title": "客服助手模板",
      "description": "智能客服场景",
      "dsl": {},
      "category": "Agent"
    }
  ]
}
```

---

## 4. 知识库相关接口

### 4.1 创建知识库

**接口**: `POST /api/v1/datasets`

**请求体**:
```json
{
  "name": "企业文档库",
  "avatar": "",
  "description": "存储企业内部文档",
  "embedding_model": "BAAI/bge-large-zh-v1.5",
  "permission": "me",
  "chunk_method": "naive",
  "parser_config": {
    "chunk_token_num": 128,
    "layout_recognize": true,
    "delimiter": "\n!?。；！？",
    "task_page_size": 12
  }
}
```

**字段说明**:
- `name`: 知识库名称 (必填)
- `embedding_model`: 嵌入模型 (可选，默认使用租户默认模型)
- `permission`: 权限 (me=私有, team=团队共享)
- `chunk_method`: 分块方法 (naive, book, email, laws, manual, one, paper, picture, presentation, qa, table, tag)
- `parser_config`: 解析配置

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "id": "kb_123",
    "name": "企业文档库",
    "embedding_model": "BAAI/bge-large-zh-v1.5",
    "chunk_method": "naive",
    "create_time": "2025-12-16T10:00:00"
  }
}
```

### 4.2 获取知识库列表

**接口**: `GET /v1/kb/list`

**查询参数**:
- `page`: 页码
- `page_size`: 每页数量
- `orderby`: 排序字段
- `desc`: 是否降序
- `name`: 知识库名称 (模糊搜索)

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "total": 10,
    "kbs": [
      {
        "id": "kb_123",
        "name": "企业文档库",
        "chunk_num": 1500,
        "doc_num": 25,
        "embd_id": "BAAI/bge-large-zh-v1.5",
        "parser_id": "naive",
        "create_time": "2025-12-16T10:00:00"
      }
    ]
  }
}
```

### 4.3 获取知识库详情

**接口**: `GET /v1/kb/detail`

**查询参数**:
- `id`: 知识库ID

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "id": "kb_123",
    "name": "企业文档库",
    "description": "存储企业内部文档",
    "chunk_num": 1500,
    "doc_num": 25,
    "embd_id": "BAAI/bge-large-zh-v1.5",
    "parser_id": "naive",
    "parser_config": {},
    "permission": "me",
    "tenant_id": "tenant_123"
  }
}
```

### 4.4 更新知识库

**接口**: `POST /v1/kb/update`

**请求体**:
```json
{
  "id": "kb_123",
  "name": "新名称",
  "description": "新描述"
}
```

### 4.5 删除知识库

**接口**: `POST /v1/kb/rm`

**请求体**:
```json
{
  "ids": ["kb_123", "kb_456"]
}
```

---

## 5. 文件管理接口

### 5.1 上传文件

**接口**: `POST /v1/file/upload`

**请求类型**: `multipart/form-data`

**表单字段**:
- `file`: 文件内容
- `parent_id`: 父文件夹ID (可选，默认根目录)

**示例 (curl)**:
```bash
curl -X POST http://localhost:8080/v1/file/upload \
  -H "Authorization: <jwt_token>" \
  -F "file=@document.pdf" \
  -F "parent_id=folder_123"
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "id": "file_123",
    "name": "document.pdf",
    "size": 1024000,
    "type": "pdf",
    "parent_id": "folder_123",
    "create_time": "2025-12-16T10:00:00"
  }
}
```

### 5.2 文件列表

**接口**: `GET /v1/file/list`

**查询参数**:
- `parent_id`: 父文件夹ID (可选)
- `page`: 页码
- `page_size`: 每页数量

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "total": 50,
    "files": [
      {
        "id": "file_123",
        "name": "document.pdf",
        "size": 1024000,
        "type": "pdf",
        "parent_id": "folder_123",
        "create_time": "2025-12-16T10:00:00"
      }
    ]
  }
}
```

### 5.3 上传文档到知识库

**接口**: `POST /v1/document/upload`

**请求类型**: `multipart/form-data`

**表单字段**:
- `file`: 文件内容
- `kb_id`: 知识库ID
- `parser_id`: 解析器ID (可选)
- `run`: 是否立即解析 (1=是, 0=否)

**示例**:
```bash
curl -X POST http://localhost:8080/v1/document/upload \
  -H "Authorization: <jwt_token>" \
  -F "file=@document.pdf" \
  -F "kb_id=kb_123" \
  -F "run=1"
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "doc_id": "doc_123",
    "name": "document.pdf",
    "kb_id": "kb_123",
    "status": "parsing",
    "progress": 0
  }
}
```

### 5.4 文档解析状态

**接口**: `GET /v1/document/list`

**查询参数**:
- `kb_id`: 知识库ID
- `page`: 页码
- `page_size`: 每页数量

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "total": 25,
    "docs": [
      {
        "id": "doc_123",
        "name": "document.pdf",
        "kb_id": "kb_123",
        "status": "1",           // 0=待解析, 1=解析完成, 2=解析失败
        "progress": 100,
        "chunk_num": 150,
        "token_num": 50000,
        "size": 1024000,
        "create_time": "2025-12-16T10:00:00"
      }
    ]
  }
}
```

### 5.5 删除文档

**接口**: `POST /v1/document/rm`

**请求体**:
```json
{
  "doc_ids": ["doc_123", "doc_456"]
}
```

---

## 6. 对话管理接口

### 6.1 创建对话助手 (Dialog)

**接口**: `POST /api/v1/chats`

**请求体**:
```json
{
  "name": "智能客服",
  "description": "企业客服助手",
  "avatar": "",
  "dataset_ids": ["kb_123", "kb_456"],
  "llm": {
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 2000
  },
  "prompt": {
    "system": "你是一个专业的客服助手...",
    "opener": "您好！我是智能客服，有什么可以帮您？",
    "show_quote": true,
    "parameters": [
      {"key": "knowledge", "optional": false}
    ]
  },
  "similarity_threshold": 0.2,
  "keywords_similarity_weight": 0.3,
  "top_n": 6,
  "rerank_model": ""
}
```

**字段说明**:
- `name`: 助手名称 (必填)
- `dataset_ids`: 关联的知识库ID列表
- `llm`: LLM配置
  - `model_name`: 模型名称
  - `temperature`: 温度 (0-1)
  - `top_p`: 采样参数
  - `max_tokens`: 最大token数
- `prompt`: 提示词配置
  - `system`: 系统提示词
  - `opener`: 开场白
  - `show_quote`: 是否显示引用
  - `parameters`: 提示词参数
- `similarity_threshold`: 相似度阈值
- `keywords_similarity_weight`: 关键词权重
- `top_n`: 检索top N个chunk
- `rerank_model`: 重排序模型

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "id": "dialog_123",
    "name": "智能客服",
    "description": "企业客服助手",
    "dataset_ids": ["kb_123", "kb_456"],
    "llm": {
      "model_name": "gpt-3.5-turbo"
    },
    "prompt": {},
    "create_time": "2025-12-16T10:00:00"
  }
}
```

### 6.2 获取对话助手列表

**接口**: `GET /api/v1/chats`

**查询参数**:
- `page`: 页码
- `page_size`: 每页数量
- `orderby`: 排序字段
- `desc`: 是否降序
- `name`: 助手名称 (模糊搜索)

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "total": 10,
    "chats": [
      {
        "id": "dialog_123",
        "name": "智能客服",
        "kb_ids": ["kb_123"],
        "kb_names": ["企业文档库"],
        "llm_id": "gpt-3.5-turbo",
        "create_time": "2025-12-16T10:00:00"
      }
    ]
  }
}
```

### 6.3 创建会话 (Conversation)

**接口**: `POST /v1/conversation/set`

**请求体**:
```json
{
  "dialog_id": "dialog_123",
  "name": "2025-12-16 客户咨询",
  "message": [
    {
      "role": "user",
      "content": "你好，我想咨询一下产品信息"
    }
  ]
}
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "id": "conv_123",
    "dialog_id": "dialog_123",
    "name": "2025-12-16 客户咨询",
    "message": [
      {
        "role": "user",
        "content": "你好，我想咨询一下产品信息"
      }
    ],
    "create_time": "2025-12-16T10:00:00"
  }
}
```

### 6.4 发送消息 (SSE流式)

**接口**: `GET /v1/conversation/completion`

**查询参数**:
- `conversation_id`: 会话ID
- `question`: 用户问题

**示例**:
```http
GET /v1/conversation/completion?conversation_id=conv_123&question=产品价格是多少
Authorization: <jwt_token>
```

**响应**: Server-Sent Events (SSE)

```
data: {"retcode": 0, "data": {"answer": "根据", "reference": {}}}

data: {"retcode": 0, "data": {"answer": "根据知识库", "reference": {}}}

data: {"retcode": 0, "data": {"answer": "根据知识库，产品价格为...", "reference": {"chunks": [...], "doc_aggs": [...]}}}
```

**完整响应数据结构**:
```json
{
  "retcode": 0,
  "data": {
    "answer": "完整回答内容",
    "reference": {
      "chunks": [
        {
          "id": "chunk_123",
          "content": "相关内容片段",
          "doc_id": "doc_123",
          "doc_name": "文档名称.pdf",
          "similarity": 0.85,
          "positions": [[0, 100]]
        }
      ],
      "doc_aggs": [
        {
          "doc_id": "doc_123",
          "doc_name": "文档名称.pdf",
          "count": 3
        }
      ]
    },
    "prompt": "实际发送给LLM的提示词",
    "message_id": "msg_123"
  }
}
```

### 6.5 获取会话列表

**接口**: `GET /v1/conversation/list`

**查询参数**:
- `dialog_id`: 对话助手ID
- `page`: 页码
- `page_size`: 每页数量

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "total": 50,
    "conversations": [
      {
        "id": "conv_123",
        "dialog_id": "dialog_123",
        "name": "2025-12-16 客户咨询",
        "message": [
          {"role": "user", "content": "问题1"},
          {"role": "assistant", "content": "回答1"}
        ],
        "create_time": "2025-12-16T10:00:00",
        "update_time": "2025-12-16T10:05:00"
      }
    ]
  }
}
```

### 6.6 获取会话详情

**接口**: `GET /v1/conversation/get`

**查询参数**:
- `conversation_id`: 会话ID

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "id": "conv_123",
    "dialog_id": "dialog_123",
    "name": "2025-12-16 客户咨询",
    "message": [
      {
        "role": "user",
        "content": "问题1",
        "id": "msg_1"
      },
      {
        "role": "assistant",
        "content": "回答1",
        "id": "msg_2",
        "reference": {
          "chunks": [],
          "doc_aggs": []
        }
      }
    ],
    "create_time": "2025-12-16T10:00:00"
  }
}
```

### 6.7 删除会话

**接口**: `POST /v1/conversation/rm`

**请求体**:
```json
{
  "conversation_ids": ["conv_123", "conv_456"]
}
```

### 6.8 对话一致性保证

**机制说明**:
1. **会话隔离**: 每个conversation_id对应独立的对话上下文
2. **消息历史**: message数组按时间顺序存储完整对话历史
3. **上下文传递**: 每次请求自动携带历史消息作为上下文
4. **用户隔离**: 通过user_id和tenant_id确保数据隔离

**最佳实践**:
```javascript
// 前端维护会话状态
const conversationState = {
  conversationId: 'conv_123',
  dialogId: 'dialog_123',
  messages: []
};

// 发送消息时传递会话ID
async function sendMessage(question) {
  const response = await fetch(
    `/v1/conversation/completion?conversation_id=${conversationState.conversationId}&question=${encodeURIComponent(question)}`,
    {
      headers: {
        'Authorization': token
      }
    }
  );

  // 处理SSE流
  const reader = response.body.getReader();
  // ...
}
```

---

## 7. 知识图谱接口

### 7.1 获取知识图谱

**接口**: `GET /api/v1/graphrag/kb/<kb_id>/graph`

**认证**: Bearer Token

**查询参数**:
- `top_k`: 返回top K个节点 (可选，默认全部)

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "graph": {
      "nodes": [
        {
          "id": "node_123",
          "entity_name": "厦门国贸股份有限公司",
          "entity_type": "ORGANIZATION",
          "description": "实体描述",
          "pagerank": 0.055,
          "source_id": ["doc_1", "doc_2", "doc_3"]
        }
      ],
      "edges": [
        {
          "source": "node_123",
          "target": "node_456",
          "relationship": "合作关系",
          "weight": 0.8,
          "description": "关系描述"
        }
      ]
    },
    "statistics": {
      "node_count": 256,
      "edge_count": 128,
      "entity_types": {
        "ORGANIZATION": 50,
        "PERSON": 40,
        "EVENT": 41,
        "CATEGORY": 119,
        "GEO": 6
      }
    }
  }
}
```

**实体类型说明**:
- `ORGANIZATION`: 组织/机构
- `PERSON`: 人员
- `EVENT`: 事件
- `CATEGORY`: 类别/概念
- `GEO`: 地理位置

### 7.2 搜索图谱节点

**接口**: `POST /api/v1/graphrag/kb/<kb_id>/search`

**请求体**:
```json
{
  "query": "厦门国贸",
  "entity_type": "ORGANIZATION",
  "top_k": 10
}
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "nodes": [
      {
        "id": "node_123",
        "entity_name": "厦门国贸股份有限公司",
        "entity_type": "ORGANIZATION",
        "similarity": 0.95,
        "pagerank": 0.055
      }
    ]
  }
}
```

### 7.3 获取节点关联文件

**接口**: `GET /api/v1/graphrag/kb/<kb_id>/node/<node_id>/files`

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "files": [
      {
        "doc_id": "doc_123",
        "doc_name": "企业介绍.pdf",
        "chunk_ids": ["chunk_1", "chunk_2"],
        "create_time": "2025-12-16T10:00:00"
      }
    ]
  }
}
```

### 7.4 下载节点内容

**接口**: `POST /api/v1/graphrag/kb/<kb_id>/node/<node_id>/download`

**请求体**:
```json
{
  "format": "json"  // json, txt, csv
}
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "node_info": {
      "entity_name": "厦门国贸股份有限公司",
      "entity_type": "ORGANIZATION",
      "description": "...",
      "pagerank": 0.055
    },
    "related_chunks": [
      {
        "content": "相关内容片段",
        "doc_name": "文档名称.pdf"
      }
    ],
    "relationships": [
      {
        "target": "其他实体",
        "relationship": "关系类型"
      }
    ]
  }
}
```

### 7.5 获取图谱统计信息

**接口**: `GET /api/v1/graphrag/kb/<kb_id>/statistics`

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "total_nodes": 256,
    "total_edges": 128,
    "entity_type_distribution": {
      "ORGANIZATION": 50,
      "PERSON": 40,
      "EVENT": 41,
      "CATEGORY": 119,
      "GEO": 6
    },
    "avg_degree": 1.0,
    "max_pagerank": 0.055,
    "graph_density": 0.002
  }
}
```

### 7.6 运行GraphRAG构建

**接口**: `POST /v1/kb/run_graphrag`

**请求体**:
```json
{
  "kb_id": "kb_123"
}
```

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "task_id": "task_123",
    "status": "running"
  }
}
```

### 7.7 追踪GraphRAG构建进度

**接口**: `GET /v1/kb/trace_graphrag`

**查询参数**:
- `kb_id`: 知识库ID

**响应**:
```json
{
  "retcode": 0,
  "data": {
    "status": "completed",  // running, completed, failed
    "progress": 100,
    "message": "GraphRAG构建完成",
    "node_count": 256,
    "edge_count": 128
  }
}
```

---

## 8. 前端调用场景

### 8.1 Agent工作流场景

#### 场景1: 创建并运行Agent

```javascript
// 1. 创建Agent
async function createAgent() {
  const response = await fetch('/api/v1/agents', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      title: '智能客服Agent',
      description: '处理客户咨询',
      dsl: {
        components: [
          {
            id: 'begin',
            obj: {
              component_name: 'Begin',
              params: {}
            }
          },
          {
            id: 'retrieval_1',
            obj: {
              component_name: 'Retrieval',
              params: {
                kb_ids: ['kb_123'],
                top_n: 6
              }
            }
          },
          {
            id: 'llm_1',
            obj: {
              component_name: 'LLM',
              params: {
                model_name: 'gpt-3.5-turbo',
                temperature: 0.7
              }
            }
          }
        ],
        path: [
          ['begin', 'retrieval_1'],
          ['retrieval_1', 'llm_1']
        ],
        answer: ['llm_1']
      }
    })
  });

  const result = await response.json();
  return result.data;
}

// 2. 运行Agent (SSE流式)
async function runAgent(agentId, query) {
  const response = await fetch(`/api/v1/webhook/${agentId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id: agentId,
      query: query,
      files: [],
      user_id: userId
    })
  });

  // 处理SSE流
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = JSON.parse(line.substring(5));
        console.log('Agent输出:', data);

        // 更新UI
        if (data.data?.content) {
          updateAgentOutput(data.data.content);
        }
      }
    }
  }
}
```

### 8.2 知识库管理场景

#### 场景2: 上传文档并监控解析进度

```javascript
// 1. 上传文档
async function uploadDocument(kbId, file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('kb_id', kbId);
  formData.append('run', '1');  // 立即解析

  const response = await fetch('/v1/document/upload', {
    method: 'POST',
    headers: {
      'Authorization': jwtToken
    },
    body: formData
  });

  const result = await response.json();
  return result.data.doc_id;
}

// 2. 轮询解析进度
async function monitorParsingProgress(kbId, docId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/v1/document/list?kb_id=${kbId}`, {
      headers: {
        'Authorization': jwtToken
      }
    });

    const result = await response.json();
    const doc = result.data.docs.find(d => d.id === docId);

    if (doc) {
      console.log(`解析进度: ${doc.progress}%`);
      updateProgressBar(doc.progress);

      if (doc.status === '1') {
        clearInterval(interval);
        console.log('解析完成！');
        onParsingComplete(doc);
      } else if (doc.status === '2') {
        clearInterval(interval);
        console.error('解析失败');
        onParsingFailed(doc);
      }
    }
  }, 2000);  // 每2秒检查一次
}

// 3. 完整流程
async function uploadAndMonitor(kbId, file) {
  try {
    const docId = await uploadDocument(kbId, file);
    await monitorParsingProgress(kbId, docId);
  } catch (error) {
    console.error('上传失败:', error);
  }
}
```

### 8.3 对话场景

#### 场景3: 创建对话并维护历史记录

```javascript
// 对话状态管理
class ConversationManager {
  constructor(dialogId, jwtToken) {
    this.dialogId = dialogId;
    this.conversationId = null;
    this.messages = [];
    this.token = jwtToken;
  }

  // 创建新会话
  async createConversation() {
    const response = await fetch('/v1/conversation/set', {
      method: 'POST',
      headers: {
        'Authorization': this.token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        dialog_id: this.dialogId,
        name: `会话-${new Date().toLocaleString()}`,
        message: []
      })
    });

    const result = await response.json();
    this.conversationId = result.data.id;
    return this.conversationId;
  }

  // 发送消息 (SSE流式)
  async sendMessage(question, onChunk, onComplete) {
    if (!this.conversationId) {
      await this.createConversation();
    }

    const url = `/v1/conversation/completion?conversation_id=${this.conversationId}&question=${encodeURIComponent(question)}`;

    const response = await fetch(url, {
      headers: {
        'Authorization': this.token
      }
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullAnswer = '';
    let references = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data:')) {
          try {
            const data = JSON.parse(line.substring(5));

            if (data.retcode === 0 && data.data) {
              fullAnswer = data.data.answer || fullAnswer;
              references = data.data.reference || references;

              // 回调：流式更新
              if (onChunk) {
                onChunk(fullAnswer, references);
              }
            }
          } catch (e) {
            console.error('解析SSE数据失败:', e);
          }
        }
      }
    }

    // 更新本地消息历史
    this.messages.push(
      { role: 'user', content: question },
      { role: 'assistant', content: fullAnswer, reference: references }
    );

    // 回调：完成
    if (onComplete) {
      onComplete(fullAnswer, references);
    }

    return { answer: fullAnswer, reference: references };
  }

  // 获取历史会话列表
  async getConversationList() {
    const response = await fetch(`/v1/conversation/list?dialog_id=${this.dialogId}`, {
      headers: {
        'Authorization': this.token
      }
    });

    const result = await response.json();
    return result.data.conversations;
  }

  // 加载历史会话
  async loadConversation(conversationId) {
    const response = await fetch(`/v1/conversation/get?conversation_id=${conversationId}`, {
      headers: {
        'Authorization': this.token
      }
    });

    const result = await response.json();
    this.conversationId = conversationId;
    this.messages = result.data.message;
    return this.messages;
  }
}

// 使用示例
const chatManager = new ConversationManager('dialog_123', jwtToken);

// 发送消息
await chatManager.sendMessage(
  '产品价格是多少？',
  (answer, refs) => {
    // 流式更新UI
    updateChatUI(answer, refs);
  },
  (finalAnswer, refs) => {
    // 完成后的处理
    console.log('回答完成:', finalAnswer);
    displayReferences(refs);
  }
);

// 获取历史会话
const conversations = await chatManager.getConversationList();
displayConversationList(conversations);
```

### 8.4 知识图谱可视化场景

#### 场景4: 获取并展示知识图谱

```javascript
// 知识图谱管理器
class KnowledgeGraphManager {
  constructor(kbId, apiToken) {
    this.kbId = kbId;
    this.token = apiToken;
    this.graph = null;
  }

  // 获取完整图谱
  async fetchGraph() {
    const response = await fetch(`/api/v1/graphrag/kb/${this.kbId}/graph`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });

    const result = await response.json();
    this.graph = result.data.graph;
    return this.graph;
  }

  // 中文化实体类型
  translateEntityType(type) {
    const mapping = {
      'ORGANIZATION': '组织',
      'PERSON': '人员',
      'EVENT': '事件',
      'CATEGORY': '类别',
      'GEO': '地理位置'
    };
    return mapping[type] || type;
  }

  // 准备可视化数据 (适配 ECharts/D3.js)
  prepareVisualizationData() {
    if (!this.graph) return null;

    // 节点数据
    const nodes = this.graph.nodes.map(node => ({
      id: node.id,
      name: node.entity_name,
      type: this.translateEntityType(node.entity_type),
      typeEn: node.entity_type,
      value: node.pagerank * 1000,  // 节点大小
      symbolSize: Math.max(20, node.pagerank * 500),
      category: node.entity_type,
      label: {
        show: node.pagerank > 0.01  // 只显示重要节点的标签
      },
      itemStyle: {
        color: this.getColorByType(node.entity_type)
      },
      tooltip: {
        formatter: `
          <b>${node.entity_name}</b><br/>
          类型: ${this.translateEntityType(node.entity_type)}<br/>
          重要性: ${(node.pagerank * 100).toFixed(2)}%<br/>
          来源文件: ${node.source_id?.length || 0}个
        `
      }
    }));

    // 边数据
    const links = this.graph.edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      name: edge.relationship,
      value: edge.weight,
      lineStyle: {
        width: edge.weight * 3,
        curveness: 0.3
      }
    }));

    // 分类数据
    const categories = [
      { name: '组织', itemStyle: { color: '#5470c6' } },
      { name: '人员', itemStyle: { color: '#91cc75' } },
      { name: '事件', itemStyle: { color: '#fac858' } },
      { name: '类别', itemStyle: { color: '#ee6666' } },
      { name: '地理位置', itemStyle: { color: '#73c0de' } }
    ];

    return { nodes, links, categories };
  }

  // 根据类型获取颜色
  getColorByType(type) {
    const colors = {
      'ORGANIZATION': '#5470c6',
      'PERSON': '#91cc75',
      'EVENT': '#fac858',
      'CATEGORY': '#ee6666',
      'GEO': '#73c0de'
    };
    return colors[type] || '#999';
  }

  // 搜索节点
  async searchNodes(query, entityType = null) {
    const response = await fetch(`/api/v1/graphrag/kb/${this.kbId}/search`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query: query,
        entity_type: entityType,
        top_k: 20
      })
    });

    const result = await response.json();
    return result.data.nodes;
  }

  // 获取节点详情
  async getNodeDetails(nodeId) {
    const response = await fetch(`/api/v1/graphrag/kb/${this.kbId}/node/${nodeId}/files`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });

    const result = await response.json();
    return result.data.files;
  }

  // 获取统计信息
  async getStatistics() {
    const response = await fetch(`/api/v1/graphrag/kb/${this.kbId}/statistics`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });

    const result = await response.json();
    return result.data;
  }
}

// 使用示例 - ECharts可视化
async function renderKnowledgeGraph(kbId, apiToken) {
  const graphManager = new KnowledgeGraphManager(kbId, apiToken);

  // 获取图谱数据
  await graphManager.fetchGraph();
  const vizData = graphManager.prepareVisualizationData();

  // ECharts配置
  const option = {
    title: {
      text: '知识图谱',
      subtext: `节点: ${vizData.nodes.length}, 关系: ${vizData.links.length}`
    },
    tooltip: {},
    legend: [{
      data: vizData.categories.map(c => c.name)
    }],
    series: [{
      type: 'graph',
      layout: 'force',
      data: vizData.nodes,
      links: vizData.links,
      categories: vizData.categories,
      roam: true,
      label: {
        position: 'right'
      },
      force: {
        repulsion: 1000,
        edgeLength: 150
      }
    }]
  };

  // 渲染
  const chart = echarts.init(document.getElementById('graph-container'));
  chart.setOption(option);

  // 节点点击事件
  chart.on('click', async (params) => {
    if (params.dataType === 'node') {
      const files = await graphManager.getNodeDetails(params.data.id);
      displayNodeDetails(params.data, files);
    }
  });
}
```

### 8.5 文件存储与展示场景

#### 场景5: 文件管理与知识库关联

```javascript
// 文件管理器
class FileManager {
  constructor(jwtToken) {
    this.token = jwtToken;
  }

  // 上传文件到文件管理器
  async uploadFile(file, parentId = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (parentId) {
      formData.append('parent_id', parentId);
    }

    const response = await fetch('/v1/file/upload', {
      method: 'POST',
      headers: {
        'Authorization': this.token
      },
      body: formData
    });

    const result = await response.json();
    return result.data;
  }

  // 获取文件列表
  async listFiles(parentId = null, page = 1, pageSize = 20) {
    let url = `/v1/file/list?page=${page}&page_size=${pageSize}`;
    if (parentId) {
      url += `&parent_id=${parentId}`;
    }

    const response = await fetch(url, {
      headers: {
        'Authorization': this.token
      }
    });

    const result = await response.json();
    return result.data;
  }

  // 创建文件夹
  async createFolder(name, parentId = null) {
    const response = await fetch('/v1/file/create', {
      method: 'POST',
      headers: {
        'Authorization': this.token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: name,
        parent_id: parentId,
        type: 'folder'
      })
    });

    const result = await response.json();
    return result.data;
  }

  // 关联文件到知识库
  async connectToKnowledgeBase(fileId, kbId) {
    const response = await fetch('/v1/file2document/convert', {
      method: 'POST',
      headers: {
        'Authorization': this.token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        file_id: fileId,
        kb_id: kbId
      })
    });

    const result = await response.json();
    return result.data;
  }

  // 移动文件
  async moveFile(fileId, targetParentId) {
    const response = await fetch('/v1/file/mv', {
      method: 'POST',
      headers: {
        'Authorization': this.token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        file_id: fileId,
        parent_id: targetParentId
      })
    });

    const result = await response.json();
    return result.data;
  }
}

// 使用示例
const fileManager = new FileManager(jwtToken);

// 上传并关联到知识库
async function uploadAndConnect(file, kbId) {
  // 1. 上传文件
  const fileData = await fileManager.uploadFile(file);
  console.log('文件上传成功:', fileData);

  // 2. 关联到知识库
  const docData = await fileManager.connectToKnowledgeBase(fileData.id, kbId);
  console.log('已关联到知识库:', docData);

  return docData;
}
```

### 8.6 综合应用场景

#### 场景6: 完整的RAG应用流程

```javascript
// RAG应用完整流程
class RAGApplication {
  constructor(jwtToken, apiToken) {
    this.jwtToken = jwtToken;
    this.apiToken = apiToken;
    this.kbId = null;
    this.dialogId = null;
    this.conversationManager = null;
  }

  // 步骤1: 初始化知识库
  async initializeKnowledgeBase(name, embeddingModel) {
    const response = await fetch('/api/v1/datasets', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: name,
        embedding_model: embeddingModel,
        chunk_method: 'naive',
        permission: 'me'
      })
    });

    const result = await response.json();
    this.kbId = result.data.id;
    console.log('知识库创建成功:', this.kbId);
    return this.kbId;
  }

  // 步骤2: 批量上传文档
  async uploadDocuments(files) {
    const uploadPromises = files.map(file => this.uploadSingleDocument(file));
    const results = await Promise.all(uploadPromises);
    console.log(`成功上传 ${results.length} 个文档`);
    return results;
  }

  async uploadSingleDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('kb_id', this.kbId);
    formData.append('run', '1');

    const response = await fetch('/v1/document/upload', {
      method: 'POST',
      headers: {
        'Authorization': this.jwtToken
      },
      body: formData
    });

    const result = await response.json();
    return result.data;
  }

  // 步骤3: 等待所有文档解析完成
  async waitForParsing() {
    return new Promise((resolve) => {
      const checkInterval = setInterval(async () => {
        const response = await fetch(`/v1/document/list?kb_id=${this.kbId}`, {
          headers: {
            'Authorization': this.jwtToken
          }
        });

        const result = await response.json();
        const docs = result.data.docs;

        const allCompleted = docs.every(doc => doc.status === '1');
        const anyFailed = docs.some(doc => doc.status === '2');

        if (allCompleted) {
          clearInterval(checkInterval);
          console.log('所有文档解析完成');
          resolve({ success: true, docs });
        } else if (anyFailed) {
          clearInterval(checkInterval);
          console.error('部分文档解析失败');
          resolve({ success: false, docs });
        } else {
          const avgProgress = docs.reduce((sum, doc) => sum + doc.progress, 0) / docs.length;
          console.log(`解析进度: ${avgProgress.toFixed(1)}%`);
        }
      }, 3000);
    });
  }

  // 步骤4: 构建知识图谱
  async buildKnowledgeGraph() {
    const response = await fetch('/v1/kb/run_graphrag', {
      method: 'POST',
      headers: {
        'Authorization': this.jwtToken,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        kb_id: this.kbId
      })
    });

    const result = await response.json();
    console.log('知识图谱构建任务已启动:', result.data.task_id);

    // 等待构建完成
    return this.waitForGraphBuilding();
  }

  async waitForGraphBuilding() {
    return new Promise((resolve) => {
      const checkInterval = setInterval(async () => {
        const response = await fetch(`/v1/kb/trace_graphrag?kb_id=${this.kbId}`, {
          headers: {
            'Authorization': this.jwtToken
          }
        });

        const result = await response.json();
        const status = result.data.status;

        console.log(`图谱构建进度: ${result.data.progress}%`);

        if (status === 'completed') {
          clearInterval(checkInterval);
          console.log('知识图谱构建完成');
          resolve(result.data);
        } else if (status === 'failed') {
          clearInterval(checkInterval);
          console.error('知识图谱构建失败');
          resolve(null);
        }
      }, 5000);
    });
  }

  // 步骤5: 创建对话助手
  async createChatAssistant(name, systemPrompt) {
    const response = await fetch('/api/v1/chats', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: name,
        dataset_ids: [this.kbId],
        llm: {
          model_name: 'gpt-3.5-turbo',
          temperature: 0.7
        },
        prompt: {
          system: systemPrompt,
          opener: '您好！我是智能助手，有什么可以帮您？',
          show_quote: true
        },
        top_n: 6
      })
    });

    const result = await response.json();
    this.dialogId = result.data.id;
    console.log('对话助手创建成功:', this.dialogId);

    // 初始化会话管理器
    this.conversationManager = new ConversationManager(this.dialogId, this.jwtToken);

    return this.dialogId;
  }

  // 步骤6: 开始对话
  async chat(question, onChunk, onComplete) {
    if (!this.conversationManager) {
      throw new Error('请先创建对话助手');
    }

    return this.conversationManager.sendMessage(question, onChunk, onComplete);
  }

  // 完整流程
  async runFullPipeline(kbName, files, chatName, systemPrompt) {
    console.log('=== 开始RAG应用完整流程 ===');

    // 1. 创建知识库
    await this.initializeKnowledgeBase(kbName, 'BAAI/bge-large-zh-v1.5');

    // 2. 上传文档
    await this.uploadDocuments(files);

    // 3. 等待解析
    const parseResult = await this.waitForParsing();
    if (!parseResult.success) {
      throw new Error('文档解析失败');
    }

    // 4. 构建知识图谱
    await this.buildKnowledgeGraph();

    // 5. 创建对话助手
    await this.createChatAssistant(chatName, systemPrompt);

    console.log('=== RAG应用初始化完成 ===');
    console.log(`知识库ID: ${this.kbId}`);
    console.log(`对话助手ID: ${this.dialogId}`);

    return {
      kbId: this.kbId,
      dialogId: this.dialogId
    };
  }
}

// 使用示例
async function setupRAGApplication() {
  const app = new RAGApplication(jwtToken, apiToken);

  // 准备文件
  const files = [
    document.getElementById('file1').files[0],
    document.getElementById('file2').files[0]
  ];

  // 运行完整流程
  const result = await app.runFullPipeline(
    '企业知识库',
    files,
    '企业智能助手',
    '你是一个专业的企业知识助手，基于企业文档回答问题。'
  );

  // 开始对话
  await app.chat(
    '公司的主营业务是什么？',
    (answer, refs) => {
      // 流式更新
      document.getElementById('answer').innerText = answer;
    },
    (finalAnswer, refs) => {
      // 显示引用
      displayReferences(refs);
    }
  );
}
```

---

## 9. 最佳实践

### 9.1 错误处理

```javascript
async function apiCallWithErrorHandling(url, options) {
  try {
    const response = await fetch(url, options);
    const result = await response.json();

    if (result.retcode !== 0) {
      throw new Error(result.retmsg || '请求失败');
    }

    return result.data;
  } catch (error) {
    console.error('API调用失败:', error);

    // 根据错误类型处理
    if (error.message.includes('401') || error.message.includes('认证')) {
      // Token过期，重新登录
      redirectToLogin();
    } else if (error.message.includes('网络')) {
      // 网络错误，提示用户
      showNetworkError();
    } else {
      // 其他错误
      showErrorMessage(error.message);
    }

    throw error;
  }
}
```

### 9.2 性能优化

```javascript
// 1. 使用防抖处理搜索
const debouncedSearch = debounce(async (query) => {
  const results = await searchNodes(query);
  displayResults(results);
}, 300);

// 2. 分页加载
async function loadMoreConversations(page) {
  const conversations = await fetch(
    `/v1/conversation/list?dialog_id=${dialogId}&page=${page}&page_size=20`
  );
  appendToList(conversations);
}

// 3. 缓存常用数据
const cache = new Map();

async function getCachedKnowledgeBase(kbId) {
  if (cache.has(kbId)) {
    return cache.get(kbId);
  }

  const kb = await fetchKnowledgeBase(kbId);
  cache.set(kbId, kb);
  return kb;
}
```

### 9.3 安全建议

1. **Token管理**:
   - 将JWT Token存储在HttpOnly Cookie中
   - API Token不要暴露在前端代码中
   - 定期刷新Token

2. **输入验证**:
   - 前端验证用户输入
   - 文件上传前检查文件类型和大小
   - 防止XSS攻击

3. **HTTPS**:
   - 生产环境必须使用HTTPS
   - 配置CORS策略

---

## 10. 常见问题

### Q1: SSE流式响应如何处理？

**A**: 使用Fetch API的ReadableStream:

```javascript
const response = await fetch(url);
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  // 处理chunk
}
```

### Q2: 如何保证对话历史的一致性？

**A**:
1. 每个会话使用唯一的conversation_id
2. 后端自动维护message数组
3. 前端同步更新本地状态
4. 切换会话时重新加载历史

### Q3: 知识图谱数据量大如何优化？

**A**:
1. 使用top_k参数限制返回节点数
2. 按实体类型分批加载
3. 使用虚拟滚动渲染大量节点
4. 实现节点懒加载

### Q4: 文档解析失败如何处理？

**A**:
1. 检查文档格式是否支持
2. 查看解析日志获取详细错误
3. 尝试更换解析器 (parser_id)
4. 调整parser_config参数

---

## 11. 附录

### 11.1 完整API端点列表

| 分类 | 方法 | 端点 | 说明 |
|------|------|------|------|
| **认证** | POST | /v1/user/login | 用户登录 |
| | POST | /v1/api/new_token | 创建API Token |
| **Agent** | POST | /api/v1/agents | 创建Agent |
| | GET | /api/v1/agents | 获取Agent列表 |
| | PUT | /api/v1/agents/<id> | 更新Agent |
| | DELETE | /api/v1/agents/<id> | 删除Agent |
| | POST | /api/v1/webhook/<id> | 运行Agent |
| **知识库** | POST | /api/v1/datasets | 创建知识库 |
| | GET | /v1/kb/list | 获取知识库列表 |
| | GET | /v1/kb/detail | 获取知识库详情 |
| | POST | /v1/kb/update | 更新知识库 |
| | POST | /v1/kb/rm | 删除知识库 |
| **文档** | POST | /v1/document/upload | 上传文档 |
| | GET | /v1/document/list | 获取文档列表 |
| | POST | /v1/document/rm | 删除文档 |
| | POST | /v1/document/run | 运行解析 |
| **对话** | POST | /api/v1/chats | 创建对话助手 |
| | GET | /api/v1/chats | 获取助手列表 |
| | POST | /v1/conversation/set | 创建会话 |
| | GET | /v1/conversation/list | 获取会话列表 |
| | GET | /v1/conversation/completion | 发送消息(SSE) |
| **知识图谱** | GET | /api/v1/graphrag/kb/<id>/graph | 获取图谱 |
| | POST | /api/v1/graphrag/kb/<id>/search | 搜索节点 |
| | GET | /api/v1/graphrag/kb/<id>/node/<nid>/files | 节点文件 |
| | POST | /v1/kb/run_graphrag | 构建图谱 |
| | GET | /v1/kb/trace_graphrag | 追踪进度 |

### 11.2 数据模型参考

详见各接口的请求/响应示例。

---

## 12. 总结

本文档涵盖了RAGFlow的核心API接口，重点关注：

✅ **Agent工作流**: 创建、运行、获取返回内容
✅ **知识库管理**: CRUD操作、文件上传、解析状态
✅ **对话系统**: 助手创建、会话管理、历史一致性
✅ **知识图谱**: 构建、查询、可视化展示
✅ **前端集成**: 完整的调用场景和代码示例

**下一步**:
1. 根据实际需求选择合适的API
2. 参考代码示例进行集成
3. 测试各个场景的功能
4. 优化性能和用户体验

如有问题，请参考：
- RAGFlow官方文档: https://ragflow.io/docs
- GitHub仓库: https://github.com/infiniflow/ragflow
- API Swagger文档: http://localhost:8080/apidocs/


