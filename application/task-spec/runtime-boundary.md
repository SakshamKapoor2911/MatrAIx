# Stable runtime boundary

See [README.md](README.md) § Runtime boundary for when this matters during onboarding.

The persona agent interacts through the protocol surface only. For survey tasks
that surface is the survey instrument and output schema. For chatbot tasks it is
the task controller's chat loop. For web tasks it is the browser/computer-use
runtime. For OS/app tasks it is the exposed desktop/mobile/browser operating
surface plus task-owned artifacts. Internal APIs, databases, or service health
checks are reserved for task setup, reset, and verifier logic.
