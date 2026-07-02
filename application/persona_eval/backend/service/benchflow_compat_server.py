"""BenchFlow compat server (re-exported from environment integrations)."""

import environment.integrations.persona_eval.benchflow.compat_server as _source

globals().update(
    {name: getattr(_source, name) for name in dir(_source) if not name.startswith("__")}
)
