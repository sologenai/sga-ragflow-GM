# 2026-04-04 Graph Vector Best Practice Research

## 背景

本次调研目标：

1. 图谱检索与向量检索在聊天知识库场景中如何结合
2. 哪类问题适合图谱，哪类适合向量，哪类适合混合
3. 对当前项目后续检索改造的启发

## 核心结论

- `[论文]` 图谱和向量不是替代关系，而是互补关系
  - 向量更适合语义相近、表述模糊、局部事实检索
  - 图谱更适合显式关系、多跳推理、全局综述和跨文档综合

- `[官方]` 主流实现已经把“图谱 + 向量”做成多路检索，而不是单一路线
  - Neo4j 已经提供 `VectorRetriever`、`HybridRetriever`、`VectorCypherRetriever`、`HybridCypherRetriever`、`Text2CypherRetriever`、`ToolsRetriever`

- `[官方]` Microsoft GraphRAG 的强项不只是“找 chunk”
  - 重点在于实体图、community summaries、global/local search
  - DRIFT 进一步把 global summary 与 local refinement 串起来

- `[官方]` Elastic 对底层检索的建议很明确
  - lexical + semantic hybrid 是主推荐路线
  - 推荐使用 RRF 做融合

- `[推断]` 企业知识库的默认策略应是：
  - 混合检索为底座
  - 图谱作为增强层
  - 而不是“所有问题强制图谱”或“所有问题强制向量”

- `[推断]` 图谱结果不应继续伪装成普通 chunk
  - 更合理的是单独的 `graph evidence` 展示层

- `[推断]` 对制度、新闻、档案、人名组织关系场景：
  - 精确名词、编号、日期、条款：全文/词法优先
  - 关系、链路、跨文档归纳：图谱优先
  - 表达改写、泛问答：向量优先

## 推荐架构

### 1. 索引层

- 文档 chunk
- 全文索引
- embedding 向量索引
- 实体、关系、社区摘要图谱索引

### 2. 路由层

先判断问题类型，而不是统一强制走某一路：

- FAQ / 同义表达 / 常规事实：标准混合检索
- 精确实体 / 编号 / 日期 / 条款：全文优先
- 多跳关系 / 跨文档综合 / 全局综述：图谱优先

### 3. 检索层

- 简单问题：原 query + 向量 + 全文混合
- 精确问题：全文优先，必要时辅以向量
- 图谱问题：community summary / graph traversal / Text2Cypher

### 4. 融合层

建议融合：

- lexical
- dense vector
- graph retrieval
- rerank

优先考虑：

- RRF
- 或可解释的加权融合

### 5. 展示层

文档证据与图谱证据分开展示：

- 文档 chunk：继续走 `[ID:x]` 与文档引用区
- 图谱 evidence：单独展示实体、关系、社区摘要

## 对当前项目的建议

### 第一阶段

- 保留当前混合检索底座，不急于整体重构
- 增加 query router
- 图谱仅用于复杂、多跳、全局类问题
- 把图谱结果从普通引用区拆出去，做单独的 `graph evidence` 面板
- 不再把“是否高质量利用图谱/知识库”绑定到 `Thinking` 按钮

### 第二阶段

- 进一步增强图谱检索
- 评估引入：
  - `HybridCypherRetriever`
  - `Text2CypherRetriever`
  - community summary / global-local search
- 增加自动评估与融合权重调优

## 与当前项目现状的对照

当前项目已有：

- 文本检索 + 向量检索混合底座
- 可选知识图谱检索
- 深度检索能力

当前主要问题不在于“没有图谱”，而在于：

- 检索策略没有很好路由
- 图谱结果展示层没有独立建模
- 图谱价值被隐藏在普通 chunk 引用模型里

## 参考资料

- LLMs and Knowledge Graphs: [https://arxiv.org/abs/2308.06374](https://arxiv.org/abs/2308.06374)
- Integrating Graphs with Large Language Models: [https://arxiv.org/abs/2310.05499](https://arxiv.org/abs/2310.05499)
- Neo4j GraphRAG Python docs: [https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)
- Neo4j LangChain integration: [https://neo4j.com/developer/genai-ecosystem/langchain/](https://neo4j.com/developer/genai-ecosystem/langchain/)
- Microsoft GraphRAG: [https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/](https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/)
- Microsoft DRIFT: [https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/](https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/)
- Elastic Hybrid Search: [https://www.elastic.co/docs/solutions/search/hybrid-search](https://www.elastic.co/docs/solutions/search/hybrid-search)
