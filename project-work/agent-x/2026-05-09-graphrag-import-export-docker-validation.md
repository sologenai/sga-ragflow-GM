# 2026-05-09 GraphRAG Import/Export Docker Validation

## Image

Local Docker image was rebuilt with the GraphRAG import/export changes and the
required TK-013/TK-014 dependency files:

```text
ragflow-custom:GM202604-70fbf766a-graph-import-v2
ragflow-custom:latest
ragflow:GM202604
```

The local `ragflow-gpu` container was recreated and the backend recovered from
502 to application-level responses.

## Regression Target

```text
kb name: test
kb id: 6b23ee1e30c311f1b9e4f584472b9517
documents: 2
```

## Verified Flow

1. `GET /knowledge_graph?exists_only=1` returned `has_graph=true`.
2. `GET /knowledge_graph/export` produced a 5,347,584-byte zip package.
3. `POST /knowledge_graph/import/preview` matched 2/2 source documents by `sha256`.
4. `DELETE /knowledge_graph` removed the graph; `exists_only` then returned an empty graph object.
5. `POST /knowledge_graph/import` inserted 567 graph records.
6. `GET /knowledge_graph?exists_only=1` returned `has_graph=true`.
7. `GET /trace_graphrag` returned `graph_document_count=2`, `entity_count=268`, `relation_count=230`, `community_count=10`.

## Frontend/Browser Note

The production frontend build passed. Browser automation against the in-app
browser reached the local login page, but the browser automation bridge timed
out during login and reset, so this run treats API-level Docker regression as
the reliable completed verification.
