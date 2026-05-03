import json
from pathlib import Path

from common.doc_store.vector_mapping import (
    ELASTICSEARCH_VECTOR_DIMS,
    REQUIRED_VECTOR_DIMS,
    build_existing_index_vector_mapping_update,
    extract_vector_dims,
    vector_dims_for_index,
    vector_field_name,
)


ROOT = Path(__file__).resolve().parents[2]


def load_mapping(name: str) -> dict:
    with (ROOT / "conf" / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def test_elasticsearch_mapping_json_is_valid():
    assert load_mapping("mapping.json")["mappings"]["dynamic_templates"]


def test_opensearch_mapping_json_is_valid():
    assert load_mapping("os_mapping.json")["mappings"]["dynamic_templates"]


def test_elasticsearch_mapping_contains_required_dimensions():
    mapping = load_mapping("mapping.json")
    assert extract_vector_dims(mapping, "elasticsearch") >= set(ELASTICSEARCH_VECTOR_DIMS)


def test_elasticsearch_mapping_documents_backend_limit():
    mapping = load_mapping("mapping.json")
    dims = extract_vector_dims(mapping, "elasticsearch")
    assert 4096 in dims
    assert not ({6144, 8192, 10240} & dims)


def test_opensearch_mapping_contains_required_dimensions():
    mapping = load_mapping("os_mapping.json")
    assert extract_vector_dims(mapping, "opensearch") >= set(REQUIRED_VECTOR_DIMS)


def test_existing_index_repair_is_idempotent():
    current_mapping = {
        "properties": {
            vector_field_name(dim): {
                "type": "dense_vector",
                "index": True,
                "similarity": "cosine",
                "dims": dim,
            }
            for dim in REQUIRED_VECTOR_DIMS
        }
    }

    assert build_existing_index_vector_mapping_update(current_mapping, "elasticsearch") == {}


def test_existing_index_repair_adds_missing_4096_dimension():
    current_mapping = {
        "properties": {
            "q_1024_vec": {
                "type": "dense_vector",
                "index": True,
                "similarity": "cosine",
                "dims": 1024,
            }
        }
    }

    update = build_existing_index_vector_mapping_update(current_mapping, "elasticsearch", (4096,))

    assert update == {
        "properties": {
            "q_4096_vec": {
                "type": "dense_vector",
                "index": True,
                "similarity": "cosine",
                "dims": 4096,
            }
        }
    }


def test_elasticsearch_runtime_dimension_supports_non_mainstream_dimension_under_limit():
    dimensions = vector_dims_for_index("elasticsearch", 2000)

    assert 2000 in dimensions
    assert 4096 in dimensions


def test_elasticsearch_runtime_dimension_rejects_dimension_over_backend_limit():
    try:
        vector_dims_for_index("elasticsearch", 6144)
    except ValueError as e:
        assert "cannot exceed 4096" in str(e)
    else:
        raise AssertionError("Expected Elasticsearch dimension limit error")
