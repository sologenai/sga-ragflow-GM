# GraphRAG 断点续生成 + Invalid KB ID 修复 实施计划（v2 修订版）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复知识图谱生成时 "Invalid Knowledgebase ID" 误报，并为大规模知识图谱（50000+ 节点）实现断点续生成、文档级进度追踪和结构化日志。

**Architecture:** 分三层改造：(1) 前端 trace 轮询加 guard 防止无效请求；(2) 后端利用 `does_graph_contains()` 跳过 + Redis Hash 实现文档级进度持久化；(3) `trace_graphrag` 扩展返回 `doc_summary`，前端展示文档级进度。

**Tech Stack:** Python (Flask backend), TypeScript/React (frontend), Redis Hash (progress persistence), Peewee ORM (DB models)

---

## 背景与现状

### 已有能力
- `does_graph_contains(tenant_id, kb_id, doc_id)` — 检查文档子图是否已存在于 docStore，可跳过（`rag/graphrag/utils.py:389`）
- `GraphRAGTaskMonitor` — Redis 进度监控类，已实现但**未集成到执行流**（`rag/graphrag/task_monitor.py`）
- `max_parallel_docs=4` — 并行处理 4 个文档（`rag/graphrag/general/index.py:155`）
- 任务取消机制 — Redis flag `{task_id}-cancel`
- 失败隔离 — 单个文档失败不影响其他文档

### 当前问题
1. **"Invalid Knowledgebase ID" 误报** — 前端 `useTraceGenerate` 轮询不判断 `id` 有效性
2. **无断点续生成** — 重新点击创建全新 task，虽有隐式跳过但无显式进度恢复
3. **进度不精确** — 只有 0-1 的 float，无文档级明细
4. **日志 3000 行截断** — 大规模任务前期日志丢失
5. **前端无文档级进度展示** — 只有滚动文本

### Codex 审查反馈（已采纳）
- **不复用 task_id** — 用 `new_task_id` + `resume_from_task_id` 模式，而非重入旧任务
- **只有 `merged` 是持久化检查点** — `subgraph_done` 只在内存中，不能作为恢复点
- **Redis Hash 替代 JSON blob** — 避免 KEYS 扫描，用预计算计数器
- **resolution/community 是 task 级操作** — 不放在文档级状态里
- **不新增 API 端点** — 直接在 `trace_graphrag` 返回 `doc_summary`
- **SDK API 同步** — `api/apps/sdk/dataset.py` 也需要更新

---

## Task 1: 修复前端 trace 轮询 "Invalid Knowledgebase ID" 误报

**Files:**
- Modify: `web/src/pages/dataset/dataset/generate-button/hook.ts:42-78`

**根因:** `useTraceGenerate` 中 `useParams().id` 可能为 `undefined`，`kbService.traceGraphRag({ kb_id: id })` 发送了无效参数。

**Step 1: 修改 `useTraceGenerate` hook 加 guard**

在 `hook.ts` 的两个 `useQuery` 中修改 `enabled` 条件和 `queryFn`：

```typescript
// hook.ts:46-61 — graphRag trace query
const { data: graphRunData, isFetching: graphRunloading } =
  useQuery<ITraceInfo>({
    queryKey: [GenerateType.KnowledgeGraph, id, open],
    gcTime: 0,
    refetchInterval: isLoopGraphRun ? 5000 : false,
    retry: 3,
    retryDelay: 1000,
    enabled: open && !!id,  // 关键修改：id 必须存在
    queryFn: async () => {
      if (!id) return {} as ITraceInfo;  // 防御性检查
      const { data } = await kbService.traceGraphRag({ kb_id: id });
      return data?.data || {};
    },
  });

// hook.ts:63-78 — raptor trace query（同样修改）
const { data: raptorRunData, isFetching: raptorRunloading } =
  useQuery<ITraceInfo>({
    queryKey: [GenerateType.Raptor, id, open],
    gcTime: 0,
    refetchInterval: isLoopRaptorRun ? 5000 : false,
    retry: 3,
    retryDelay: 1000,
    enabled: open && !!id,  // 关键修改
    queryFn: async () => {
      if (!id) return {} as ITraceInfo;
      const { data } = await kbService.traceRaptor({ kb_id: id });
      return data?.data || {};
    },
  });
```

**Step 2: 验证**

打开 dataset 页面，打开 Generate dropdown，确认无 "Invalid Knowledgebase ID" 报错。

**Step 3: Commit**

```bash
git add web/src/pages/dataset/dataset/generate-button/hook.ts
git commit -m "fix: 修复知识图谱轮询时 Invalid Knowledgebase ID 误报"
```

---

## Task 2: 扩展 GraphRAGTaskMonitor 支持文档级进度（Redis Hash）

**Files:**
- Modify: `rag/graphrag/task_monitor.py`

**目标:** 用 Redis Hash（每个 task_id 一个 Hash）追踪文档级进度，支持原子更新和预计算计数器。

**设计决策（基于 Codex 反馈）：**
- 文档状态只有 4 种：`pending` | `extracting` | `merged` | `failed` | `skipped`
- 不用 `subgraph_done`（不持久化，不可恢复）
- 用 Redis Hash 而非 JSON blob，key = `graphrag:docs:{task_id}`，field = doc_id
- 用单独的计数器 key `graphrag:counts:{task_id}` 记录统计
- `resume_from_task_id` 字段记录恢复来源

**Step 1: 添加文档级进度数据结构**

在 `task_monitor.py` 添加：

```python
import time

DOC_HASH_PREFIX = "graphrag:docs:"
COUNTS_PREFIX = "graphrag:counts:"
RESUME_PREFIX = "graphrag:resume:"
DOC_TTL = 86400 * 3  # 3 days


@dataclass
class DocProgress:
    """Per-document progress within a GraphRAG task."""
    doc_id: str
    doc_name: str
    status: str  # "pending" | "extracting" | "merged" | "failed" | "skipped"
    entity_count: int = 0
    relation_count: int = 0
    chunk_count: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    error: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "status": self.status,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "chunk_count": self.chunk_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "DocProgress":
        d = json.loads(raw)
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})
```

**Step 2: 在 GraphRAGTaskMonitor 中添加 Hash 方法**

```python
# 在 GraphRAGTaskMonitor 类中添加：

def _doc_hash_key(self, task_id: str) -> str:
    return f"{DOC_HASH_PREFIX}{task_id}"

def _counts_key(self, task_id: str) -> str:
    return f"{COUNTS_PREFIX}{task_id}"

def _resume_key(self, task_id: str) -> str:
    return f"{RESUME_PREFIX}{task_id}"

def init_doc_progress(self, task_id: str, docs: list[dict],
                      resume_from_task_id: str = "") -> None:
    """Initialize per-document progress using Redis Hash.

    Args:
        task_id: The new graphrag task ID
        docs: List of {"doc_id": str, "doc_name": str, "chunk_count": int}
        resume_from_task_id: Previous task ID to resume from (if any)
    """
    try:
        hash_key = self._doc_hash_key(task_id)
        pipe = self.redis_conn.pipeline()
        for doc in docs:
            dp = DocProgress(
                doc_id=doc["doc_id"],
                doc_name=doc.get("doc_name", doc["doc_id"][:8]),
                status="pending",
                chunk_count=doc.get("chunk_count", 0),
            )
            pipe.hset(hash_key, doc["doc_id"], dp.to_json())
        pipe.expire(hash_key, DOC_TTL)

        # Precompute counters
        counts_key = self._counts_key(task_id)
        pipe.hset(counts_key, mapping={
            "total": len(docs),
            "pending": len(docs),
            "extracting": 0,
            "merged": 0,
            "failed": 0,
            "skipped": 0,
        })
        pipe.expire(counts_key, DOC_TTL)

        # Store resume link
        if resume_from_task_id:
            pipe.setex(self._resume_key(task_id), DOC_TTL, resume_from_task_id)

        pipe.execute()
    except Exception as e:
        logging.error(f"Failed to init doc progress: {e}")

def update_doc_status(self, task_id: str, doc_id: str,
                      new_status: str, **kwargs) -> None:
    """Update status for a specific document, adjusting counters atomically.

    kwargs: entity_count, relation_count, start_time, end_time, error
    """
    try:
        hash_key = self._doc_hash_key(task_id)
        raw = self.redis_conn.hget(hash_key, doc_id)
        if not raw:
            return

        dp = DocProgress.from_json(raw)
        old_status = dp.status
        dp.status = new_status
        for k, v in kwargs.items():
            if hasattr(dp, k):
                setattr(dp, k, v)

        pipe = self.redis_conn.pipeline()
        pipe.hset(hash_key, doc_id, dp.to_json())

        # Adjust counters
        if old_status != new_status:
            counts_key = self._counts_key(task_id)
            pipe.hincrby(counts_key, old_status, -1)
            pipe.hincrby(counts_key, new_status, 1)

        pipe.execute()
    except Exception as e:
        logging.error(f"Failed to update doc status: {e}")

def get_doc_progress_all(self, task_id: str) -> Dict[str, Dict]:
    """Get all document progress for a task."""
    try:
        hash_key = self._doc_hash_key(task_id)
        raw_map = self.redis_conn.hgetall(hash_key)
        if not raw_map:
            return {}
        return {
            doc_id: json.loads(val)
            for doc_id, val in raw_map.items()
        }
    except Exception as e:
        logging.error(f"Failed to get doc progress: {e}")
        return {}

def get_counts(self, task_id: str) -> Dict[str, int]:
    """Get precomputed status counters for a task."""
    try:
        counts_key = self._counts_key(task_id)
        raw = self.redis_conn.hgetall(counts_key)
        if not raw:
            return {}
        return {k: int(v) for k, v in raw.items()}
    except Exception as e:
        logging.error(f"Failed to get counts: {e}")
        return {}

def get_merged_doc_ids(self, task_id: str) -> list[str]:
    """Get doc_ids that have been merged (durable checkpoint)."""
    progress_map = self.get_doc_progress_all(task_id)
    return [
        doc_id for doc_id, info in progress_map.items()
        if info.get("status") in ("merged", "skipped")
    ]

def get_resumable_summary(self, task_id: str) -> Dict[str, Any]:
    """Get summary for resume decision using precomputed counters."""
    counts = self.get_counts(task_id)
    if not counts:
        return {"has_progress": False}

    total = int(counts.get("total", 0))
    merged = int(counts.get("merged", 0))
    skipped = int(counts.get("skipped", 0))
    failed = int(counts.get("failed", 0))

    return {
        "has_progress": True,
        "total_docs": total,
        "completed": merged + skipped,
        "merged": merged,
        "skipped": skipped,
        "failed": failed,
        "pending": int(counts.get("pending", 0)) + int(counts.get("extracting", 0)),
    }

def get_resume_from_task_id(self, task_id: str) -> str:
    """Get the previous task_id this task is resuming from."""
    try:
        return self.redis_conn.get(self._resume_key(task_id)) or ""
    except Exception:
        return ""
```

**Step 3: Commit**

```bash
git add rag/graphrag/task_monitor.py
git commit -m "feat: 扩展 GraphRAGTaskMonitor 用 Redis Hash 追踪文档级进度"
```

---

## Task 3: 集成 monitor 到执行流 + 断点续生成

**Files:**
- Modify: `rag/graphrag/general/index.py:144-391` (`run_graphrag_for_kb` 函数)

**设计决策：**
- 用 `does_graph_contains()` 作为主要跳过信号（它检查 docStore 中的持久化数据）
- monitor 作为补充，记录进度供前端展示和续跑参考
- 文档状态流转：`pending → extracting → merged`（成功）或 `failed`（失败）
- `subgraph_done` 不作为状态（内存态，不持久化）

**Step 1: 在函数开头添加 import 和 monitor 初始化**

在 `rag/graphrag/general/index.py` 顶部添加 `import time`（如尚无）。

修改 `run_graphrag_for_kb` 函数入口：

```python
import time
from rag.graphrag.task_monitor import GraphRAGTaskMonitor

# 在 run_graphrag_for_kb 函数体开头，tenant_id/kb_id 之后：
    task_id = row["id"]
    monitor = GraphRAGTaskMonitor()

    # 检查是否有 resume_from_task_id（由 API 层传入 row）
    resume_from = row.get("resume_from_task_id", "")
    if resume_from:
        # 获取上次已 merged 的文档列表
        prev_merged = set(monitor.get_merged_doc_ids(resume_from))
        original_count = len(doc_ids)
        doc_ids = [d for d in doc_ids if d not in prev_merged]
        callback(msg=f"[GraphRAG] 断点续生成: 跳过 {original_count - len(doc_ids)} 个已合并文档, 剩余 {len(doc_ids)} 个")
```

**Step 2: load_doc_chunks 之后初始化文档级进度**

在 `all_doc_chunks` 构建完成后：

```python
    # 初始化文档级进度
    doc_info_list = []
    for doc_id in doc_ids:
        try:
            _, doc_obj = DocumentService.get_by_id(doc_id)
            doc_name = doc_obj.name if doc_obj else doc_id[:8]
        except Exception:
            doc_name = doc_id[:8]
        doc_info_list.append({
            "doc_id": doc_id,
            "doc_name": doc_name,
            "chunk_count": len(all_doc_chunks.get(doc_id, [])),
        })
    monitor.init_doc_progress(task_id, doc_info_list, resume_from_task_id=resume_from)
```

**Step 3: 在 build_one 中更新文档状态**

```python
    async def build_one(doc_id: str):
        # ... 现有取消检查 ...
        chunks = all_doc_chunks.get(doc_id, [])
        if not chunks:
            monitor.update_doc_status(task_id, doc_id, "skipped")
            # ... 现有回调 ...
            return

        monitor.update_doc_status(task_id, doc_id, "extracting", start_time=time.time())

        # ... 现有子图生成逻辑 ...

        # 在成功分支 (sg 不为 None 时)：
        if sg:
            subgraphs[doc_id] = sg
            # 注意：这里只是内存态，不标记为 merged，等合并后才标记
            callback(msg=f"{msg} done")
        else:
            # does_graph_contains 返回 None 表示已存在
            monitor.update_doc_status(task_id, doc_id, "skipped", end_time=time.time())

        # 在失败分支：
        except Exception as e:
            monitor.update_doc_status(task_id, doc_id, "failed", error=repr(e), end_time=time.time())
```

**Step 4: 在合并阶段更新为 merged（持久化检查点）**

```python
        for doc_id in ok_docs:
            sg = subgraphs[doc_id]
            union_nodes.update(set(sg.nodes()))
            new_graph = await merge_subgraph(
                tenant_id, kb_id, doc_id, sg, embedding_model, callback,
            )
            if new_graph is not None:
                final_graph = new_graph
            # 合并写入 docStore 后才标记为 merged — 这是持久化检查点
            monitor.update_doc_status(task_id, doc_id, "merged", end_time=time.time())
```

**Step 5: 添加精确进度计算**

```python
    # 子图生成完成后（asyncio.gather 之后）
    processed_count = len(subgraphs) + len(failed_docs)
    total_count = len(doc_ids)
    callback(prog=0.6 * (processed_count / max(total_count, 1)),
             msg=f"[GraphRAG] 子图生成: {processed_count}/{total_count}")

    # 合并循环中
    for i, doc_id in enumerate(ok_docs):
        # ... 合并逻辑 ...
        merge_progress = 0.6 + 0.2 * ((i + 1) / max(len(ok_docs), 1))
        callback(prog=merge_progress, msg=f"[GraphRAG] 合并: {i + 1}/{len(ok_docs)}")

    # resolution 占 10%，community 占 10%（在各自的 callback 中调整）
```

**Step 6: 最终摘要**

```python
    # return 前添加
    counts = monitor.get_counts(task_id)
    callback(msg=f"[GraphRAG] 完成: 总计 {counts.get('total', 0)} 文档, "
             f"合并 {counts.get('merged', 0)}, 跳过 {counts.get('skipped', 0)}, "
             f"失败 {counts.get('failed', 0)}")
```

**Step 7: Commit**

```bash
git add rag/graphrag/general/index.py
git commit -m "feat: 集成文档级进度追踪到 GraphRAG 执行流，支持断点续生成"
```

---

## Task 4: 后端 API 支持续跑

**Files:**
- Modify: `api/apps/kb_app.py:1170-1236`
- Modify: `api/apps/sdk/dataset.py` (SDK API 同步，如有对应端点)

**设计决策（基于 Codex 反馈）：**
- 续跑时创建新 task_id，通过 `resume_from_task_id` 字段关联旧任务
- 不新增 API 端点，在 `trace_graphrag` 中附加 `doc_summary`

**Step 1: 修改 `run_graphrag` 支持续跑参数**

```python
@manager.route("/run_graphrag", methods=["POST"])
@login_required
async def run_graphrag():
    req = await get_request_json()
    kb_id = req.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    resume = req.get("resume", False)
    old_task_id = kb.graphrag_task_id

    if old_task_id:
        ok, task = TaskService.get_by_id(old_task_id)
        if not ok:
            logging.warning(f"A valid GraphRAG task id is expected for kb {kb_id}")

        if task and task.progress not in [-1, 1]:
            return get_error_data_result(
                message=f"Task {old_task_id} in progress. A Graph Task is already running."
            )

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id, page_number=0, items_per_page=0,
        orderby="create_time", desc=False, keywords="",
        run_status=[], types=[], suffix=[],
    )
    if not documents:
        return get_error_data_result(message=f"No documents in Knowledgebase {kb_id}")

    sample_document = documents[0]
    document_ids = [document["id"] for document in documents]

    # 创建新任务（始终新 task_id）
    task_id = queue_raptor_o_graphrag_tasks(
        sample_doc_id=sample_document, ty="graphrag", priority=0,
        fake_doc_id=GRAPH_RAPTOR_FAKE_DOC_ID, doc_ids=list(document_ids),
    )

    # 如果是续跑，记录 resume_from_task_id（通过 Redis）
    resumed = False
    if resume and old_task_id:
        from rag.graphrag.task_monitor import GraphRAGTaskMonitor
        monitor = GraphRAGTaskMonitor()
        summary = monitor.get_resumable_summary(old_task_id)
        if summary.get("has_progress") and summary.get("completed", 0) > 0:
            # 在 Redis 中记录新任务的 resume 来源
            from rag.utils.redis_conn import REDIS_CONN
            REDIS_CONN.setex(f"graphrag:resume:{task_id}", 86400 * 3, old_task_id)
            resumed = True

    if not KnowledgebaseService.update_by_id(kb.id, {"graphrag_task_id": task_id}):
        logging.warning(f"Cannot save graphrag_task_id for kb {kb_id}")

    return get_json_result(data={"graphrag_task_id": task_id, "resumed": resumed})
```

**Step 2: 在 task_executor 中传递 resume_from_task_id**

在 `rag/svr/task_executor.py` 的 graphrag 处理分支中，调用 `run_graphrag_for_kb` 前检查 Redis：

```python
# 在 graphrag 处理分支中，传入 resume_from_task_id
from rag.graphrag.task_monitor import GraphRAGTaskMonitor
monitor = GraphRAGTaskMonitor()
resume_from = monitor.get_resume_from_task_id(task_id)
row["resume_from_task_id"] = resume_from

result = await run_graphrag_for_kb(
    row=row,
    doc_ids=task.get("doc_ids", []),
    ...
)
```

**Step 3: 修改 `trace_graphrag` 返回 `doc_summary`**

```python
@manager.route("/trace_graphrag", methods=["GET"])
@login_required
def trace_graphrag():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.graphrag_task_id
    if not task_id:
        return get_json_result(data={})

    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return get_json_result(data={})

    result = task.to_dict()

    # 附加文档级进度摘要（不新增 API 端点）
    from rag.graphrag.task_monitor import GraphRAGTaskMonitor
    monitor = GraphRAGTaskMonitor()
    result["doc_summary"] = monitor.get_resumable_summary(task_id)

    return get_json_result(data=result)
```

**Step 4: Commit**

```bash
git add api/apps/kb_app.py rag/svr/task_executor.py
git commit -m "feat: 后端支持知识图谱断点续生成（new task_id + resume_from 模式）"
```

---

## Task 5: 前端续跑按钮和文档进度展示

**Files:**
- Modify: `web/src/pages/dataset/dataset/generate-button/hook.ts`
- Modify: `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- Modify: `web/src/locales/zh.ts`
- Modify: `web/src/locales/en.ts`

**Gemini 审查建议（已采纳）：**
- "续跑"为主按钮（带 Play 图标），"重新生成"为次要按钮（防止误操作全量重跑）
- 文档进度摘要放在进度条下方（进度条给视觉感受，数字给具体事实）
- 显示当前阶段（实体提取 / 合并 / 社区发现）

**Step 1: 扩展 ITraceInfo 接口**

在 `hook.ts` 的 `ITraceInfo` 中添加：

```typescript
export interface ITraceInfo {
  // ... 现有字段 ...
  doc_summary?: {
    has_progress: boolean;
    total_docs: number;
    completed: number;
    merged: number;
    skipped: number;
    failed: number;
    pending: number;
  };
}
```

**Step 2: 修改 `useDatasetGenerate` 支持 resume 参数**

```typescript
mutationFn: async ({ type, resume = false }: { type: GenerateType; resume?: boolean }) => {
  const func =
    type === GenerateType.KnowledgeGraph
      ? kbService.runGraphRag
      : kbService.runRaptor;
  const { data } = await func({ kb_id: id, resume });
  if (data.code === 0) {
    message.success(t('message.operated'));
    queryClient.invalidateQueries({ queryKey: [type] });
  }
  return data;
},
```

**Step 3: 修改 `generate.tsx` 失败态 UI（续跑为主按钮）**

在 `MenuItem` 的 `status === generateStatus.failed` 分支，替换现有的单个重试图标：

```tsx
{status === generateStatus.failed && (
  <div className="flex gap-2 items-center justify-end w-full">
    {/* 续跑为主按钮（Gemini 建议：鼓励节省资源的行为） */}
    <span
      className="text-accent-primary cursor-pointer text-sm font-medium flex items-center gap-1"
      onClick={(e) => {
        e.stopPropagation();
        runGenerate({ type, resume: true });
      }}
    >
      <IconFontFill name="play" className="text-accent-primary" />
      {t('knowledgeDetails.resumeGenerate')}
    </span>
    {/* 重新生成为次要按钮（较小，防止误触） */}
    <span
      className="text-text-secondary cursor-pointer text-xs opacity-70 hover:opacity-100"
      onClick={(e) => {
        e.stopPropagation();
        runGenerate({ type });
      }}
    >
      <IconFontFill name="reparse" />
    </span>
  </div>
)}
```

**Step 4: 添加文档进度摘要展示（进度条下方）**

在进度条区域之后、日志区域之前，显示文档进度和当前阶段：

```tsx
{/* 文档进度摘要 — 放在进度条下方（Gemini 建议） */}
{data?.doc_summary?.has_progress && (
  <div className="text-xs text-text-secondary px-2.5 flex justify-between">
    <span>
      {t('knowledgeDetails.docProgress', {
        completed: data.doc_summary.completed || 0,
        total: data.doc_summary.total_docs || 0,
        failed: data.doc_summary.failed || 0,
      })}
    </span>
  </div>
)}
```

**Step 5: 添加国际化文案**

zh.ts（在 `knowledgeDetails` 下）：
```typescript
resumeGenerate: '续跑',
docProgress: '文档进度: {{completed}}/{{total}} 完成, {{failed}} 失败',
```

en.ts：
```typescript
resumeGenerate: 'Resume',
docProgress: 'Doc Progress: {{completed}}/{{total}} completed, {{failed}} failed',
```

**Step 6: Commit**

```bash
git add web/src/pages/dataset/dataset/generate-button/hook.ts
git add web/src/pages/dataset/dataset/generate-button/generate.tsx
git add web/src/locales/zh.ts web/src/locales/en.ts
git commit -m "feat: 前端支持知识图谱续跑按钮和文档级进度展示"
```

---

## Task 6: 单元测试

**Files:**
- Modify: `test/test_graphrag.py`

**Step 1: 添加 Redis Hash 文档级进度测试**

```python
class TestDocProgress:
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis with Hash support."""
        redis = MagicMock()
        redis.pipeline.return_value = MagicMock()
        redis.pipeline.return_value.execute.return_value = []
        return redis

    @pytest.fixture
    def monitor(self, mock_redis):
        return GraphRAGTaskMonitor(redis_conn=mock_redis)

    def test_init_doc_progress(self, monitor, mock_redis):
        docs = [
            {"doc_id": "d1", "doc_name": "test.pdf", "chunk_count": 10},
            {"doc_id": "d2", "doc_name": "test2.pdf", "chunk_count": 5},
        ]
        monitor.init_doc_progress("task1", docs)
        pipe = mock_redis.pipeline.return_value
        assert pipe.hset.call_count == 3  # 2 docs + 1 counts
        assert pipe.expire.call_count == 2  # hash + counts

    def test_get_counts(self, monitor, mock_redis):
        mock_redis.hgetall.return_value = {
            "total": "3", "pending": "1", "merged": "1", "failed": "1",
            "extracting": "0", "skipped": "0",
        }
        counts = monitor.get_counts("task1")
        assert counts["total"] == 3
        assert counts["merged"] == 1

    def test_resumable_summary(self, monitor, mock_redis):
        mock_redis.hgetall.return_value = {
            "total": "10", "pending": "2", "extracting": "1",
            "merged": "5", "skipped": "1", "failed": "1",
        }
        summary = monitor.get_resumable_summary("task1")
        assert summary["total_docs"] == 10
        assert summary["completed"] == 6  # merged + skipped
        assert summary["failed"] == 1
        assert summary["pending"] == 3  # pending + extracting
```

**Step 2: 运行测试**

```bash
cd E:/sga-ragflow-GM && python -m pytest test/test_graphrag.py -v
```

**Step 3: Commit**

```bash
git add test/test_graphrag.py
git commit -m "test: 添加文档级进度 Redis Hash 追踪的单元测试"
```

---

## 实施顺序

```
Task 1 (前端 fix, 独立)    ──→ Gemini 执行
Task 2 (monitor 扩展)      ──→ Codex 执行
Task 3 (执行流集成)         ──→ 依赖 Task 2, Codex 执行
Task 4 (后端 API)           ──→ 依赖 Task 3, Codex 执行
Task 5 (前端 UI)            ──→ 依赖 Task 4, Gemini 执行
Task 6 (测试)               ──→ 依赖 Task 2-4, Codex 执行
```

**并行路径:**
- 路径 A: Task 1 (Gemini)
- 路径 B: Task 2 → Task 3 → Task 4 → Task 6 (Codex)
- Task 5 在 Task 4 完成后由 Gemini 执行（可与 Task 6 并行）
