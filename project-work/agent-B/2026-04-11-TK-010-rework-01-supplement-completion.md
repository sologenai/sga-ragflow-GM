# 2026-04-11 TK-010 Rework-01 Supplemental Completion

## Basic Information

- Ticket ID: `TK-010`
- Assignee: `agent-B`
- Supplemental Completion Time: `2026-04-11 11:08:24 +08:00`
- Related Work Order Status: `pending acceptance` (unchanged)
- Nature: `UI observability closure` (no backend behavior change)

## Trigger

- User feedback in acceptance check:
  - did not see generated node/edge counts during the running phase in the GraphRAG generate panel
  - requested explicit running-phase visibility

## Scope Boundary

- In scope:
  - GraphRAG generate dropdown runtime display of graph counts
- Out of scope:
  - GraphRAG backend retrieval/indexing logic
  - task monitor architecture
  - resume strategy changes
  - settings page layout redesign

## Changed Files

- `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- `project-work/agent-B/2026-04-10-TK-010-completion.md` (audit supplement section)
- `project-work/agent-B/2026-04-11-TK-010-rework-01-supplement-completion.md`
- `project-work/agent-x/2026-04-11-TK-010-agent-B-supplement-summary.md`

## Root Cause

- Existing render conditions emphasized completed/failed graph state for stats visibility.
- During running phase, users could see percent and logs but stats line might not render until graph summary became non-empty.

## Implementation Details

- File: `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- Main changes:
  1. `buildGraphStatsSummary(...)` gains `showWhenEmpty` option.
  2. Missing summary fields normalized to zero to avoid empty render.
  3. Running-phase gate added:
     - `showGraphStatsSummary = isGraphType && status !== start`
     - when `status === running`, force render with `showWhenEmpty: true`
  4. Running-phase doc progress summary visibility aligned with graph mode state.

## Deployment / Runtime Steps

1. Ran lint on target file path (`eslint`) - pass
2. Rebuilt frontend assets (`npm run build` in `web/`) - pass
3. Copied `web/dist` to container `docker-ragflow-gpu-1:/ragflow/web/dist`
4. Restarted container `docker-ragflow-gpu-1`
5. Opened browser and revalidated dataset generate menu runtime display

## Validation Results

1. Running-phase graph stats visible: `pass`
2. Running progress percent still visible: `pass`
3. Running progress log stream still visible: `pass`
4. Resume/Regenerate entry not regressed: `pass`
5. API/retrieval logic untouched by this patch: `pass`

## Evidence

- Screenshot:
  - `output/playwright/tk010-running-stats.png`
- Snapshot reference:
  - `.playwright-cli/page-2026-04-11T02-54-05-319Z.yml`
- Observed runtime text in menu:
  - `Graph stats: nodes 0 / edges 0 / entities 0 / relations 0 / communities 0`
  - with concurrent running progress (`60.00%`) and progress log output

## Handoff

- Sent review summary to agent-x:
  - `project-work/agent-x/2026-04-11-TK-010-agent-B-supplement-summary.md`


