# PersonaEval Core

This package contains the shared PersonaEval core library:

- persona loading
- user simulation
- in-process Harbor host-native runners (`persona_eval.inprocess`)
- scoring helpers

This package is the shared PersonaEval core library used by the app backend and
runtime adapters.

The current package still relies on the in-repo PersonaEval backend source tree for
some modules such as `backend.*`; this extraction is a layout cleanup, not a full
backend packaging split.
