# TK-008 Acceptance

- Ticket ID: `TK-008`
- Reviewed By: `agent-x`
- Acceptance Time: `2026-04-06 01:45:00 +08:00`
- Validation Image: `ragflow-custom:tk006-tk007-tk008-r5`
- Result: `accepted`

## Acceptance Conclusion

This ticket is accepted.

The graph-evidence card now keeps all major evidence sections compact by default.
This includes both:

- community summary
- the combined entity / relation block

## Verification Performed

### 1. Code-scope verification

Confirmed touched scope stayed within the intended frontend-only boundary:

- `web/src/components/message-item/index.tsx`
- `web/src/components/message-item/index.module.less`
- `web/src/locales/en.ts`
- `web/src/locales/zh.ts`

No retrieval logic, backend graph-evidence contract, or chat layout framework was changed.

### 2. Frontend build verification

Executed production frontend build successfully:

- `npm.cmd run build`

Result:

- build passed
- updated `web/dist` was produced

### 3. Rebuilt-image verification

Rebuilt and restarted the local GPU Docker runtime with the updated frontend bundle twice during closure polish, with final validation on:

- image: `ragflow-custom:tk006-tk007-tk008-r5`

Health checks after restart:

- `http://127.0.0.1:9380/v1/system/ping` -> `200`
- `http://127.0.0.1:8880/v1/system/ping` -> `200`

## Accepted Behavior

- community summary is collapsed by default as a whole block
- entity / relation evidence is also collapsed by default as a whole block
- users have clear expand / collapse controls for both blocks
- full summary remains available when expanded
- entity and relation sections remain available inside their expanded evidence block

## Residual Notes

- This acceptance used rebuilt-image/runtime verification plus frontend build verification, not a browser automation harness.
- The local Docker startup path still depends on the `.venv` volume state and may spend time on first-boot runtime checks.

## Final Judgment

`TK-008` is accepted.
