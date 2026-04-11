# 2026-04-11 TK-010 Agent-B Supplemental Summary (for agent-x)

## Scope

- Ticket: `TK-010`
- Round: supplemental closure after `rework-01`
- Goal of this supplement:
  - close runtime UX gap where GraphRAG menu did not clearly show graph statistics during **running** phase

## Why This Supplement Was Needed

- User-side validation feedback:
  - expected to see generated node/edge counts while generation is ongoing
  - observed only progress percentage/logs previously
- Impact:
  - weak observability in running state
  - easy to misinterpret as missing graph stats

## Root Cause

- Frontend condition in GraphRAG generate menu favored completed/failed state for stats rendering.
- Running state could miss `graphStatsSummary` visibility when counts were not yet materialized.

## Actual Code Change

- File changed:
  - `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- Key code points:
  - around line `39`: `buildGraphStatsSummary(...)` now supports `showWhenEmpty`
  - around line `131`: running-state visibility gate introduced
  - around line `133`: running state forces summary rendering with zero fallback
  - around lines `192-196`: doc progress + graph stats blocks rendered in running phase
- Behavior after patch:
  - while GraphRAG is running:
    - stats row is visible even when backend counts are still zero
    - UI displays `nodes/edges/entities/relations/communities` in one line
  - as trace polling updates backend summary, displayed numbers update naturally

## Non-Regression Statement

- This supplement is UI-only.
- No change to:
  - task monitor runtime chain
  - GraphRAG resume backend logic
  - Redis compatibility layer
  - retrieval/indexing algorithm
- Existing repaired capabilities kept:
  - Resume / Regenerate entry
  - trace polling
  - startup/import compatibility from prior rework

## Verification Performed

1. Static verification
   - `eslint` target check for `generate.tsx`: pass
2. Build and deploy
   - `web` production build: pass
   - copied built assets into running container:
     - `docker-ragflow-gpu-1:/ragflow/web/dist`
   - container restart: pass
3. Browser validation (Playwright CLI)
   - login success
   - open dataset page: `525a9064350911f1b23fe7b0db4c4dee`
   - open `Generate` dropdown during running task
   - observed runtime stats line:
     - `Graph stats: nodes 0 / edges 0 / entities 0 / relations 0 / communities 0`
   - observed percent and progress logs still present (e.g., `60.00%`)

## Audit Evidence

- Screenshot:
  - `output/playwright/tk010-running-stats.png`
- Playwright snapshot with visible runtime stats row:
  - `.playwright-cli/page-2026-04-11T02-54-05-319Z.yml`

## Suggested Review Checklist for agent-x

1. Confirm running-state GraphRAG menu now always shows a graph stats row.
2. Confirm Resume/Regenerate controls remain intact in completed/failed context.
3. Confirm no regression in trace API request/response flow.
4. Confirm startup path remains unaffected by this supplement.

