"""Shared Arrow schema and categorical encoding for unified persona rows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any

import numpy as np
import pyarrow as pa


ATTRIBUTE_COUNT = 1290
ATTRIBUTE_BYTES = (ATTRIBUTE_COUNT + 1) // 2
NULL_BITMAP_BYTES = (ATTRIBUTE_COUNT + 7) // 8

DESCRIPTION_TYPE = pa.list_(
    pa.struct(
        [
            pa.field("field_index", pa.uint16(), nullable=False),
            pa.field("text", pa.string(), nullable=False),
        ]
    )
)
ATTRIBUTE_OVERRIDE_TYPE = pa.list_(
    pa.struct(
        [
            pa.field("field_index", pa.uint16(), nullable=False),
            pa.field("value", pa.string(), nullable=False),
        ]
    )
)
GROUNDING_TYPE = pa.list_(
    pa.struct(
        [
            pa.field("field_index", pa.uint16(), nullable=False),
            pa.field("evidence", pa.string()),
            pa.field("confidence", pa.float32()),
            pa.field("assignment_type", pa.string()),
        ]
    )
)

UNIFIED_SCHEMA = pa.schema(
    [
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_row_index", pa.uint64(), nullable=False),
        pa.field("source_record_id", pa.string()),
        pa.field("attributes", pa.binary(ATTRIBUTE_BYTES), nullable=False),
        pa.field("null_bitmap", pa.binary(NULL_BITMAP_BYTES)),
        pa.field("attribute_overrides", ATTRIBUTE_OVERRIDE_TYPE),
        pa.field("has_description", pa.bool_(), nullable=False),
        pa.field("descriptions", DESCRIPTION_TYPE),
        pa.field("grounding", GROUNDING_TYPE),
        pa.field("metadata_json", pa.string()),
    ]
)


@dataclass(frozen=True)
class AttributeCodec:
    field_ids: tuple[str, ...]
    value_codes: tuple[dict[str, int], ...]

    @classmethod
    def from_codes_schema(cls, path: Path) -> "AttributeCodec":
        payload = json.loads(path.read_text(encoding="utf-8"))
        columns = payload["columns"]
        if len(columns) != ATTRIBUTE_COUNT:
            raise ValueError(f"Expected {ATTRIBUTE_COUNT} columns, found {len(columns)}")
        return cls(
            field_ids=tuple(column["id"] for column in columns),
            value_codes=tuple(
                {value: index for index, value in enumerate(column["values"])}
                for column in columns
            ),
        )

    def encode_mapping(
        self, values: dict[str, Any]
    ) -> tuple[bytes, bytes | None, list[dict[str, Any]] | None]:
        codes = np.zeros(ATTRIBUTE_COUNT, dtype=np.uint8)
        nulls = np.zeros(ATTRIBUTE_COUNT, dtype=np.uint8)
        overrides = []
        for index, (field_id, value_map) in enumerate(zip(self.field_ids, self.value_codes)):
            value = values.get(field_id)
            if value is None:
                nulls[index] = 1
                continue
            try:
                codes[index] = value_map[value]
            except KeyError:
                overrides.append({"field_index": index, "value": str(value)})
        packed_codes = codes[0::2] | (codes[1::2] << 4)
        packed_nulls = np.packbits(nulls, bitorder="little")
        return (
            packed_codes.tobytes(),
            packed_nulls.tobytes() if nulls.any() else None,
            overrides or None,
        )

    def encode_fields(
        self, fields: list[dict[str, Any]]
    ) -> tuple[bytes, bytes | None, list[dict[str, Any]] | None]:
        known_ids = set(self.field_ids)
        values: dict[str, Any] = {}
        for field in fields:
            field_id = field.get("field_id")
            if field_id in known_ids and field_id not in values:
                values[field_id] = field.get("value")
        return self.encode_mapping(values)


def fixed_binary_array(matrix: np.ndarray, width: int) -> pa.Array:
    contiguous = np.ascontiguousarray(matrix, dtype=np.uint8)
    if contiguous.ndim != 2 or contiguous.shape[1] != width:
        raise ValueError(f"Expected byte matrix with width {width}, found {contiguous.shape}")
    return pa.Array.from_buffers(
        pa.binary(width),
        len(contiguous),
        [None, pa.py_buffer(contiguous)],
    )