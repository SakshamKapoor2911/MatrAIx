# Persona Generation & Validation

**How to generate and validate synthetic personas**

---

## Quick Start

```bash
cd /home/yuexing/MatrAIx/personas
python generate.py --count 100 --output personas.json
```

*Detailed guide coming soon.*

---

## Key Files

- `personas/generate.py` — Main generation script
- `personas/dimensions+new.json` — Schema definition
- `personas/ID0001-ID1000/` — Existing personas
- `tests/test_persona_generation.py` — Validation suite

---

## Validation Checklist

- [ ] All required dimensions present
- [ ] Values match dimension value sets
- [ ] No missing required fields
- [ ] IDs are unique
- [ ] Test suite passes

---

**Last updated**: 2026-06-21

---

**See also**: [../CURRENT_STATE.md](../CURRENT_STATE.md), [SUBMISSION_REQUIREMENTS.md](./SUBMISSION_REQUIREMENTS.md)
