# Chatbot application task

This is a Harbor Application Type 2 chatbot task. The task environment owns the
chat loop, termination logic, artifact writing, and persona self-report flow.

Run the deterministic task controller:

```bash
python /app/chatbot_controller.py
```

Do not call `chatbot-api` manually. Do not write transcript, result, or feedback
artifacts yourself. The controller reads the persona profile from
`/app/input/persona.yaml`, reads the application task prompt from
`/app/input/task_prompt.md`, talks to the chatbot API sidecar, stops at the
configured max turn count or when the persona indicates completion, asks the
persona for a post-interaction self-report, and writes the required artifacts.

The controller writes:

- `/app/output/transcript.json`
- `/app/output/application_result.json`
- `/app/output/persona_self_report.json`
- `/app/output/evaluation_result.json`
- `/app/output/user_feedback.json`
- `/app/output/run_metadata.json`

If the controller fails, stop and report the error. Do not debug, patch, or edit
files inside `/app`; the task controller is the product under test for this
Harbor task. Do not simulate the application, do not invent item ids, and do not
replace the chatbot API with a different model.
