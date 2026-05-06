# GraphRAG 动态错误策略修复记录

日期：2026-05-06
负责人：agent-X
分支：GM202604

## 目标

GraphRAG 长任务不只做固定重试，而是根据模型/embedding/服务返回的错误类型动态调整策略：

- 超时：自动增加单次调用 timeout，必要时拆小 batch。
- 限流：拉长退避时间继续重试，但不拆小 batch，避免把请求数打得更多。
- 模型临时错误：继续重试并拉长退避。
- 服务 5xx/连接错误：继续重试，必要时拆小 batch。
- 授权、模型不存在、向量维度、mapping/schema 这类硬配置错误：不重试，直接暴露。

## 改动

### embedding 错误分型

新增 `_embedding_error_kind`，将错误分为：

- `timeout`
- `rate_limit`
- `service`
- `connection`
- `model_retryable`
- `transient`
- `hard_config`

### 动态参数

新增配置：

- `GRAPHRAG_EMBED_MAX_ATTEMPT_TIMEOUT_SECONDS`，默认 21600 秒。
- `GRAPHRAG_EMBED_TIMEOUT_GROWTH_FACTOR`，默认 1.5。
- `GRAPHRAG_EMBED_RATE_LIMIT_BACKOFF_MULTIPLIER`，默认 2.0。
- `GRAPHRAG_EMBED_MODEL_ERROR_BACKOFF_MULTIPLIER`，默认 1.5。
- `GRAPHRAG_STAGE_RATE_LIMIT_BACKOFF_MULTIPLIER`，默认 2.0。
- `GRAPHRAG_STAGE_MODEL_ERROR_BACKOFF_MULTIPLIER`，默认 1.5。

### 行为变化

- embedding timeout 后，下一次重试会把 attempt timeout 按增长系数提高，直到最大值。
- rate limit / quota 错误只增加等待时间，不触发 batch split。
- 模型 busy / overloaded / internal / temporary / retry / try again 等临时错误会被视为可重试。
- model not found / not authorized / invalid api key / dimension / mapping 等错误仍然立即失败。

## 验证

新增单测覆盖：

- timeout 后 attempt timeout 自动增长。
- rate limit 会重试但不会拆 batch。
- 原有大批量批处理、瞬时失败恢复、永久失败、断点续跑安全性仍保留。
