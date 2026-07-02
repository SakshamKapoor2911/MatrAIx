# Saved persona groups for Harbor jobs and paper reproducibility.
#
# Each cohort is a directory with `cohort.json`:
#   persona/datasets/cohorts/<cohort-id>/cohort.json
#
# Kinds:
#   recipe — filters + seed + sampleSize (re-sample on launch)
#   frozen — explicit personaIds (fixed group for sign-off)
#
# Create via PersonaEval UI (Harbor batch panel) or POST /api/persona-pool/cohorts.
