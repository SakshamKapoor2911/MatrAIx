# Optional Packages

This directory contains optional packages that extend the PersonaBench Harbor
runtime without becoming part of the default install path.

Rules:

- Keep each package independently installable and testable.
- Do not restore the legacy `matraix` Python package namespace.
- Package-specific publish scripts and credentials stay out of the default
  runtime path.
- Import optional packages one PR at a time unless their dependency graph
  requires a combined change.

Current packages:

- `harbor-langsmith/`: LangSmith plugin for Harbor jobs.
