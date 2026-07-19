# Nemotron Domain Selection Plots

This directory contains the PR90 Nemotron domain-selection summaries and plot
artifacts.

Regenerate the standard-library SVG plots and metrics:

```bash
python persona/curation/existing_data/scripts/render_nemotron_domain_selection_plots.py
```

Regenerate the Matplotlib PNG/PDF/SVG cluster figure as well:

```bash
python persona/curation/existing_data/scripts/render_nemotron_domain_selection_plots.py --matplotlib
```

`--matplotlib` requires `matplotlib`; the default command only uses the Python
standard library and writes generated plots to
`persona/curation/existing_data/outputs/nemotron_domain_selection/` by default.
If `nemotron_test_users_50_per_domain.json` is present, the script will use it
to regenerate the metrics CSVs before rendering; otherwise it uses the existing
committed CSV summaries.
