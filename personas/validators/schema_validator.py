#!/usr/bin/env python3
"""
Schema validator for dimensions+new.json

Validates that all dimensions conform to the expected schema:
{
  "id": str,
  "label": str,
  "category": str,
  "description": str,
  "values": list[str]
}

Reports deprecated fields and schema violations.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def load_dimensions(filepath):
    """Load dimensions from JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    return data.get("dimensions", [])


def validate_dimension(dim, idx):
    """Validate a single dimension. Returns (is_valid, errors)."""
    errors = []

    # Required fields
    required = {"id", "label", "category", "description", "values"}
    missing = required - set(dim.keys())
    if missing:
        errors.append(f"  Missing required fields: {missing}")

    # Type checks
    if "id" in dim and not isinstance(dim["id"], str):
        errors.append(f"  'id' must be string, got {type(dim['id']).__name__}")
    if "label" in dim and not isinstance(dim["label"], str):
        errors.append(f"  'label' must be string, got {type(dim['label']).__name__}")
    if "category" in dim and not isinstance(dim["category"], str):
        errors.append(f"  'category' must be string, got {type(dim['category']).__name__}")
    if "description" in dim and not isinstance(dim["description"], str):
        errors.append(f"  'description' must be string, got {type(dim['description']).__name__}")
    if "values" in dim and not isinstance(dim["values"], list):
        errors.append(f"  'values' must be list, got {type(dim['values']).__name__}")

    # Deprecated fields (from old schema)
    deprecated_fields = {"contrib_id", "synthlab", "source_id"}
    found_deprecated = deprecated_fields & set(dim.keys())
    if found_deprecated:
        errors.append(f"  ⚠️  Deprecated fields found: {found_deprecated}")

    # Extra fields (informational only)
    extra_fields = set(dim.keys()) - required - deprecated_fields

    return len(errors) == 0, errors, extra_fields


def main():
    dimensions_file = Path(__file__).parent.parent / "dimensions+new.json"

    if not dimensions_file.exists():
        print(f"❌ Error: {dimensions_file} not found")
        sys.exit(1)

    print(f"📋 Validating schema: {dimensions_file}\n")

    dimensions = load_dimensions(dimensions_file)
    print(f"Total dimensions: {len(dimensions)}\n")

    # Collect statistics
    valid_count = 0
    invalid_count = 0
    deprecated_count = 0
    extra_fields_by_dim = defaultdict(list)
    all_errors = []

    # Validate each dimension
    for idx, dim in enumerate(dimensions):
        is_valid, errors, extra_fields = validate_dimension(dim, idx)

        if not is_valid:
            invalid_count += 1
            dim_id = dim.get("id", f"[unknown at index {idx}]")
            all_errors.append((dim_id, errors))
        else:
            valid_count += 1

        if extra_fields:
            extra_fields_by_dim[idx] = extra_fields

        # Check for deprecated fields
        if any(field in dim for field in {"contrib_id", "synthlab"}):
            deprecated_count += 1

    # Print results
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    if invalid_count == 0:
        print(f"✅ All {valid_count} dimensions valid!")
    else:
        print(f"❌ Found {invalid_count} invalid dimensions:")
        for dim_id, errors in all_errors:
            print(f"\n  Dimension: {dim_id}")
            for error in errors:
                print(error)

    print(f"\n📊 Deprecated fields check:")
    if deprecated_count == 0:
        print(f"✅ No deprecated fields found (contrib_id, synthlab)")
    else:
        print(f"⚠️  Found {deprecated_count} dimensions with deprecated fields")

    print(f"\n📝 Extra fields (non-standard, but allowed):")
    if extra_fields_by_dim:
        sample_idx = next(iter(extra_fields_by_dim))
        sample_fields = extra_fields_by_dim[sample_idx]
        print(f"  Found extra fields: {sample_fields}")
        print(f"  ({len(extra_fields_by_dim)} dimensions have extra fields)")
    else:
        print(f"  None (all dimensions use standard schema)")

    print("\n" + "=" * 70)
    print("DEPRECATED FIELD COUNT")
    print("=" * 70)
    contrib_id_count = sum(1 for dim in dimensions if "contrib_id" in dim)
    synthlab_count = sum(1 for dim in dimensions if "synthlab" in dim)
    print(f"  contrib_id entries: {contrib_id_count}")
    print(f"  synthlab entries: {synthlab_count}")
    print(f"  ✅ Expected: 0 of each (Phase 1 cleanup done)")

    # Exit code
    sys.exit(0 if invalid_count == 0 and contrib_id_count == 0 and synthlab_count == 0 else 1)


if __name__ == "__main__":
    main()
