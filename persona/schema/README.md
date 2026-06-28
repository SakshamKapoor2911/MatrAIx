# Persona Schema

This directory contains the persona dimension catalog and schema validation
tools.

## Files

- `dimensions.json`: unified persona dimension catalog imported from MatrAIx.
  The current catalog uses schema version `1.0` and contains 1339
  dimensions.
- `validators/schema_validator.py`: validates required dimension fields and
  checks that deprecated fields are absent.

## Validate

Run from the repository root:

```bash
python3 persona/schema/validators/schema_validator.py
```

The validator also accepts an explicit path:

```bash
python3 persona/schema/validators/schema_validator.py persona/schema/dimensions.json
```
