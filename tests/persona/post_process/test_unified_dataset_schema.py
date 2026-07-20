from pathlib import Path

import pyarrow as pa

from persona.post_process.unified_dataset.schema import (
    ATTRIBUTE_BYTES,
    NULL_BITMAP_BYTES,
    AttributeCodec,
    fixed_binary_array,
)
from persona.post_process.unified_dataset.materialize import _human_row, _meaningful_grounding


def _schema_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return next(
        (repo_root / "persona/synthesis/generated/full_dag_10b_20260703/shards").glob(
            "*.schema.json"
        )
    )


def test_codec_preserves_values_and_nulls() -> None:
    codec = AttributeCodec.from_codes_schema(_schema_path())
    values = {
        field_id: next(iter(value_codes))
        for field_id, value_codes in zip(codec.field_ids, codec.value_codes)
    }
    values[codec.field_ids[0]] = None

    attributes, null_bitmap, overrides = codec.encode_mapping(values)

    assert len(attributes) == ATTRIBUTE_BYTES
    assert null_bitmap is not None
    assert len(null_bitmap) == NULL_BITMAP_BYTES
    assert null_bitmap[0] & 1
    assert overrides is None


def test_codec_preserves_off_schema_values_as_overrides() -> None:
    codec = AttributeCodec.from_codes_schema(_schema_path())
    values = {
        field_id: next(iter(value_codes))
        for field_id, value_codes in zip(codec.field_ids, codec.value_codes)
    }
    values["age_bracket"] = "65+"

    _, _, overrides = codec.encode_mapping(values)

    assert overrides == [{"field_index": 0, "value": "65+"}]


def test_fixed_binary_array_is_zero_copy_compatible() -> None:
    import numpy as np

    matrix = np.arange(4 * ATTRIBUTE_BYTES, dtype=np.uint8).reshape(4, ATTRIBUTE_BYTES)
    array = fixed_binary_array(matrix, ATTRIBUTE_BYTES)

    assert array.type == pa.binary(ATTRIBUTE_BYTES)
    assert len(array) == 4
    assert array[1].as_py() == matrix[1].tobytes()


def test_codec_null_fills_sparse_field_lists() -> None:
    codec = AttributeCodec.from_codes_schema(_schema_path())

    attributes, null_bitmap, overrides = codec.encode_fields(
        [{"field_id": codec.field_ids[0], "value": next(iter(codec.value_codes[0]))}]
    )

    assert len(attributes) == ATTRIBUTE_BYTES
    assert null_bitmap is not None
    assert null_bitmap[0] & 1 == 0
    assert null_bitmap[0] & 2
    assert overrides is None


def test_codec_ignores_unknown_fields_for_categorical_encoding() -> None:
    codec = AttributeCodec.from_codes_schema(_schema_path())

    _, null_bitmap, overrides = codec.encode_fields(
        [{"field_id": "legacy_removed_field", "value": "legacy value"}]
    )

    assert null_bitmap is not None
    assert all(byte == 0xFF for byte in null_bitmap[:-1])
    assert overrides is None


def test_grounding_normalizes_numeric_string_confidence() -> None:
    grounding = _meaningful_grounding(
        [
            {
                "field_id": "age_bracket",
                "value": "25-34",
                "confidence": "0.8",
                "evidence": "sample",
                "assignment_type": "direct",
            }
        ]
    )

    assert grounding is not None
    assert grounding[0]["confidence"] == 0.8


def test_human_row_aligns_sparse_grounding_to_codebook_index() -> None:
    codec = AttributeCodec.from_codes_schema(_schema_path())
    target_index = 10
    row = _human_row(
        {
            "qid": "Q1",
            "fields": [
                {
                    "field_id": codec.field_ids[target_index],
                    "value": next(iter(codec.value_codes[target_index])),
                    "description": "aligned description",
                    "evidence": "aligned evidence",
                    "confidence": "0.7",
                }
            ],
        },
        codec,
        "wiki",
        1,
    )

    assert row["descriptions"] == [{"field_index": target_index, "text": "aligned description"}]
    assert row["grounding"][0]["field_index"] == target_index