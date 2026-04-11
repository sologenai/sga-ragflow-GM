# 2026-04-10 GraphRAG Resume Merge Mismatch Analysis

## Summary

The current startup failure in the GPU image is caused by a source-level mismatch inside the GraphRAG resume path.

This is not primarily a Docker, CPU/GPU, or branch-behind-main issue.

## Observed Failure

When the current GPU image starts, the main RAGFlow API fails during import and `8880` returns `502`.

The blocking error is:

```text
ImportError: cannot import name 'DOC_TTL' from 'rag.graphrag.task_monitor'
```

The stack points to:

- `api/ragflow_server.py`
- `api/apps/kb_app.py`
- `rag/graphrag/task_monitor.py`

## Code-Level Finding

`kb_app.py` still contains GraphRAG resume and trace logic that expects an enhanced task monitor implementation, including:

- `DOC_TTL`
- `RESUME_PREFIX`
- `GraphRAGTaskMonitor.get_resumable_summary()`

However, the current source version of `rag/graphrag/task_monitor.py` had been reduced to a basic progress monitor and no longer exposed those resume-related constants and methods.

This creates an import-time and behavior-time mismatch.

## Why This Looks Like a Merge Regression

The product already had a GraphRAG resume capability before.

Additional evidence observed locally:

- old bytecode artifacts for `task_monitor` still referenced resume-related methods such as:
  - `init_doc_progress`
  - `update_doc_status`
  - `get_merged_doc_ids`
  - `get_resume_from_task_id`
  - `get_resumable_summary`
- current `kb_app.py` still contains the resume entrypoints and resume-related Redis usage

This strongly suggests that an earlier merge or upstream-sync step preserved the `kb_app.py` resume calls but dropped or overwrote the enhanced `task_monitor.py` implementation.

## Judgment

This should be treated as a GraphRAG infrastructure restoration ticket.

The correct remediation direction is not to remove resume usage from `kb_app.py`, but to restore the enhanced compatibility surface in `rag/graphrag/task_monitor.py` and then validate startup plus resume behavior end-to-end.

## Recommended Scope

1. restore the enhanced task-monitor compatibility surface required by `kb_app.py`
2. verify GPU image startup no longer fails on GraphRAG imports
3. verify GraphRAG trace / resume endpoints behave consistently again
4. rebuild and validate the GPU image intended for remote deployment
