# Recommender Agent Chat Task

Have a realistic multi-turn conversation with the application under test while staying fully in character as the assigned persona.

This task is specifically about movie discovery. Your need must stay within movies: you are looking for a film to watch, not books, software, legal research tools, financial products, medical advice, or other categories.

Decide on a plausible movie-viewing need, reveal information gradually, react honestly to follow-up questions and recommendations, and continue until you can judge whether the application helped.

If the application asks what matters to you, answer in terms of movie attributes such as genre, tone, themes, pacing, recency, runtime, language, setting, content boundaries, or who you plan to watch with.

Read `input/context.md` for application background. Use `input/protocol.md` for the chat API contract.

Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
