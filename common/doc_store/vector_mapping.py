REQUIRED_VECTOR_DIMS = (
    128,
    256,
    384,
    512,
    768,
    1024,
    1536,
    2048,
    2560,
    3072,
    4096,
    6144,
    8192,
    10240,
)

ELASTICSEARCH_MAX_VECTOR_DIM = 4096
ELASTICSEARCH_VECTOR_DIMS = tuple(dim for dim in REQUIRED_VECTOR_DIMS if dim <= ELASTICSEARCH_MAX_VECTOR_DIM)


def supported_vector_dims(engine: str) -> tuple[int, ...]:
    if engine == "elasticsearch":
        return ELASTICSEARCH_VECTOR_DIMS
    if engine == "opensearch":
        return REQUIRED_VECTOR_DIMS
    raise ValueError(f"Unsupported vector mapping engine: {engine}")


def vector_dims_for_index(engine: str, vector_size: int = 0) -> tuple[int, ...]:
    """Return baseline dimensions plus the current model dimension when supported."""
    dimensions = supported_vector_dims(engine)
    if vector_size <= 0:
        return dimensions
    if engine == "elasticsearch" and vector_size > ELASTICSEARCH_MAX_VECTOR_DIM:
        raise ValueError(
            f"Elasticsearch dense_vector dimensions cannot exceed {ELASTICSEARCH_MAX_VECTOR_DIM}; "
            "use OpenSearch/Infinity/OceanBase or configure a smaller embedding output dimension."
        )
    return tuple(sorted(set(dimensions + (vector_size,))))


def vector_field_name(vector_size: int) -> str:
    return f"q_{vector_size}_vec"


def vector_mapping(engine: str, vector_size: int) -> dict:
    if engine == "elasticsearch":
        return {
            "type": "dense_vector",
            "index": True,
            "similarity": "cosine",
            "dims": vector_size,
        }
    if engine == "opensearch":
        return {
            "type": "knn_vector",
            "index": True,
            "space_type": "cosinesimil",
            "dimension": vector_size,
        }
    raise ValueError(f"Unsupported vector mapping engine: {engine}")


def vector_dynamic_template(engine: str, vector_size: int) -> dict:
    template_name = "dense_vector" if engine == "elasticsearch" else "knn_vector"
    return {
        template_name: {
            "match": f"*_{vector_size}_vec",
            "mapping": vector_mapping(engine, vector_size),
        }
    }


def extract_vector_dims(mapping: dict, engine: str) -> set[int]:
    dim_key = "dims" if engine == "elasticsearch" else "dimension"
    dims = set()
    for template in mapping.get("mappings", {}).get("dynamic_templates", []):
        for cfg in template.values():
            field_mapping = cfg.get("mapping", {})
            if field_mapping.get("type") in ("dense_vector", "knn_vector") and dim_key in field_mapping:
                dims.add(int(field_mapping[dim_key]))
    for field, field_mapping in mapping.get("mappings", {}).get("properties", {}).items():
        if not field.startswith("q_") or not field.endswith("_vec"):
            continue
        if field_mapping.get("type") in ("dense_vector", "knn_vector") and dim_key in field_mapping:
            dims.add(int(field_mapping[dim_key]))
    return dims


def missing_vector_dims(mapping: dict, engine: str, dimensions=None) -> list[int]:
    if dimensions is None:
        dimensions = supported_vector_dims(engine)
    present = extract_vector_dims(mapping, engine)
    return [dim for dim in dimensions if dim not in present]


def ensure_vector_dynamic_templates(mapping: dict, engine: str, dimensions=None) -> bool:
    if dimensions is None:
        dimensions = supported_vector_dims(engine)
    templates = mapping.setdefault("mappings", {}).setdefault("dynamic_templates", [])
    missing_dims = missing_vector_dims(mapping, engine, dimensions)
    if not missing_dims:
        return False

    insert_at = len(templates)
    for i, template in enumerate(templates):
        if "binary" in template:
            insert_at = i
            break

    for offset, dim in enumerate(missing_dims):
        templates.insert(insert_at + offset, vector_dynamic_template(engine, dim))
    return True


def build_existing_index_vector_mapping_update(
    current_mapping: dict,
    engine: str,
    dimensions=None,
) -> dict:
    if dimensions is None:
        dimensions = supported_vector_dims(engine)
    properties = current_mapping.get("properties", current_mapping)
    update = {}
    for dim in dimensions:
        field_name = vector_field_name(dim)
        if field_name not in properties:
            update[field_name] = vector_mapping(engine, dim)
    return {"properties": update} if update else {}


def format_vector_mapping_error(
    model_name: str | None,
    vector_size: int,
    doc_engine: str,
    index_name: str,
    reason: str | None = None,
) -> str:
    field_name = vector_field_name(vector_size)
    model = model_name or "unknown"
    msg = (
        f"Embedding vector mapping is missing or incompatible: model={model}, "
        f"returned_dimension={vector_size}, document_engine={doc_engine}, "
        f"index={index_name}, missing_mapping={field_name}. "
        "Recommended action: restart the backend with the updated mappings so RAGFlow can "
        "repair the existing index non-destructively, or add this vector field to the index mapping manually."
    )
    if reason:
        msg += f" Cause: {reason}"
    return msg
