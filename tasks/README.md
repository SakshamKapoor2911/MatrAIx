# MatrAIx tasks

Executable Harbor tasks for persona simulation scenarios.

## Layout

```
tasks/
├── survey/
├── chat/
├── web/
└── computer-use/
```

Each scenario is a standard Harbor task directory (`task.toml`, `instruction.md`, `environment/`, `tests/`).

Docker tasks use `/app/input/` for seeded assets and `/app/output/` for agent submissions.

## Reference scenarios

| Form | Path | Suggested agent |
|------|------|-----------------|
| survey | `tasks/survey/product-feedback/` | `persona-claude-code` |
| chat | `tasks/chat/acme-support-mcp/` | `persona-claude-code` |
| web (Playwright) | `tasks/web/books-interest-playwright/` | `persona-openhands-sdk` |
| web (browser-use) | `tasks/web/books-interest-browser-use/` | `persona-browser-use` |
| web (Cocoa) | `tasks/web/books-interest-cocoa/` | `persona-cocoa` |
| web (CUA) | `tasks/web/books-interest-cua/` | `persona-computer-1` |
| computer-use | `tasks/computer-use/notification-preferences/` | `persona-computer-1` |

## Docs

How to author tasks: [`docs/applications/`](../docs/applications/README.md)

Harbor upstream examples: `examples/tasks/`
