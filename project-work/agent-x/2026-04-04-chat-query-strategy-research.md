# 2026-04-04 Chat Query Strategy Research

## 背景

围绕聊天检索策略，当前需要明确三个问题：

1. 检索时应优先使用用户原始 query，还是拆分关键词后检索
2. 检索底座应优先走全文检索（ES/BM25）还是向量检索
3. 复杂问题是否需要查询改写、子问题拆分、二次检索

## 本地代码现状

当前仓库并不是“只用原 query”或“只拆关键词”二选一，而是已经在走混合路线：

- 在 [rag/nlp/search.py](E:/sga-ragflow-GM/rag/nlp/search.py) 中：
  - `question` 原文 `qst` 会直接送入向量编码
  - 同时会调用 `FulltextQueryer.question()` 生成全文检索表达式
  - 文本检索与向量检索再做融合

- 在 [rag/nlp/query.py](E:/sga-ragflow-GM/rag/nlp/query.py) 中：
  - 英文 query 会做分词、term weight、相邻短语拼接、同义词扩展
  - 中文 query 会做 term weight、细粒度分词、同义词扩展、短语召回增强
  - 也就是说，全文检索用的并不是用户原 query 原封不动下发，而是“关键词化 + 扩展化”的 query

- 在 [rag/utils/es_conn.py](E:/sga-ragflow-GM/rag/utils/es_conn.py) 中：
  - 文本检索落到 ES `query_string`
  - 向量检索落到 `knn`
  - 两者按加权方式融合

- 当前融合权重在 [rag/nlp/search.py](E:/sga-ragflow-GM/rag/nlp/search.py) 中写死为 `0.05,0.95`
  - 这意味着当前融合明显偏向向量召回
  - 对企业知识库里的人名、档号、合同号、年份、制度名称这类精确约束问题，可能会削弱全文检索价值

结论：
- 本地当前方案实际是“原 query 用于向量召回 + 改写 query 用于全文召回 + 融合”

## 外部调研结论

### 1. 是否应始终使用原 query 直接检索

不建议。

研究普遍支持：

- 简单、语义完整的问题，保留原 query 直接做语义检索更稳
- 对实体密集、条件密集、编号精确、时间精确的问题，仅靠原 query 往往不够，通常需要：
  - 关键词抽取
  - 查询改写
  - 子问题拆分

参考：

- RQ-RAG: [https://arxiv.org/abs/2404.00610](https://arxiv.org/abs/2404.00610)
- Unsupervised Question Decomposition for QA: [https://aclanthology.org/2020.emnlp-main.713.pdf](https://aclanthology.org/2020.emnlp-main.713.pdf)
- PruneRAG: [https://arxiv.org/abs/2601.11024](https://arxiv.org/abs/2601.11024)

结论：
- 不应在系统层面强制“只用原 query”
- 也不应在系统层面强制“先拆关键词再检索”
- 更合理的是按问题类型动态选择：
  - 原 query
  - query rewrite
  - 关键词/实体增强
  - 子问题拆分

### 2. 全文检索（ES/BM25）还是向量检索

不建议二选一，推荐混合检索。

Elastic 官方当前明确推荐 hybrid search：

- 全文检索擅长 lexical match
- 向量检索擅长 semantic similarity
- 建议通过 RRF 等方式融合两路结果

参考：

- Hybrid search: [https://www.elastic.co/docs/solutions/search/hybrid-search](https://www.elastic.co/docs/solutions/search/hybrid-search)
- Ranking and reranking: [https://www.elastic.co/docs/solutions/search/ranking](https://www.elastic.co/docs/solutions/search/ranking)

对知识库问答场景，经验上：

- 人名、机构名、合同号、档号、年份、制度名称、会议名称等精确实体
  - 更依赖 BM25 / 全文检索
- 同义表达、自然语言描述、总结类问题
  - 更依赖向量检索
- 企业知识库实际场景通常两类都有
  - 因此混合检索更稳

结论：
- 推荐底座保持“全文 + 向量”的混合检索
- 不建议退回纯 ES
- 也不建议退回纯向量

### 3. 是否需要子问题拆分和多轮检索

对复杂问题，建议需要；但不应默认全量开启。

相关研究支持：

- Active Retrieval / FLARE：在生成过程中决定何时检索、检索什么  
  [https://arxiv.org/abs/2305.06983](https://arxiv.org/abs/2305.06983)
- Adaptive-RAG：根据问题复杂度路由到不同检索策略  
  [https://arxiv.org/abs/2403.14403](https://arxiv.org/abs/2403.14403)
- CRAG：先评估检索质量，再决定纠偏或补检  
  [https://arxiv.org/abs/2401.15884](https://arxiv.org/abs/2401.15884)

结论：

- 简单问题：一次混合检索即可
- 复杂问题：需要 query rewrite / decomposition / 二次检索
- 不应把“深度检索”绑定在用户手工点击 `Thinking` 按钮上

## 推荐落地方向

### 推荐策略

1. 默认保留混合检索
   - 全文检索：使用关键词增强后的 query
   - 向量检索：使用用户原始 query

2. 增加 query 策略分层
   - `raw`
   - `rewritten`
   - `decomposed`

3. 增加检索模式分层
   - `off`
   - `standard`
   - `deep`
   - `auto`

4. 默认走 `auto`
   - 简单问题：`standard`
   - 多约束/多实体/跨文档/比较类问题：升级为 `deep`

### 针对当前项目的具体建议

首期不建议大改检索底座，优先改“策略路由”：

1. 不再把“是否高质量利用知识库”绑定在 `Thinking` 按钮上
2. 默认聊天场景使用：
   - 原 query 向量召回
   - 关键词增强后的全文召回
   - 融合后返回
3. 当满足以下条件时，再自动升级到深度检索：
   - 问题包含多个实体/年份/条件
   - 问题明显需要跨文档综合
   - 首轮召回数量少或分数低
   - 首轮回答不充分

## 项目经理结论

针对“强制检索用原 query 还是拆关键词、检索时走 ES 还是向量”的问题，结论如下：

- 不建议“只用原 query”
- 不建议“只拆关键词”
- 不建议“只走 ES”
- 不建议“只走向量”
- 推荐：
  - 原 query 负责语义召回
  - 关键词增强负责全文召回
  - 两路混合
  - 复杂问题再做 query rewrite / decomposition / deep retrieval

这比“所有问题强制过知识库 + 强制单一路径检索”更符合当前研究和企业知识库实际表现。
