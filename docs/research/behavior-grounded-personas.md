# Behavior-Grounded Personas

This note migrates the useful research-plan content from MatrAIx PRs `#43`
and `#47` without restoring the old `personas/` planning file. It records a
possible future line for constructing personas from longitudinal user behavior.

## Data Sources

Primary candidate: Reddit Research Access, if access is available. The source
plan notes that Reddit provides SQL access to public posts and comments with a
five-year lookback period, monthly refreshes, user-deletion handling, and a
revolving recent window.

Fallback candidate: the Pushshift Reddit dataset, using historical comments and
submissions from 2005 to 2024.

## Extraction Plan

Build a diverse subreddit pool aligned with persona dimensions. Candidate
categories include identity, career, relationships, finance, politics,
entertainment, sports, technology, health, and lifestyle.

Select users with rich behavioral histories:

- sufficient comment/post volume
- long enough activity history
- participation across multiple communities
- coverage of persona-relevant dimensions
- future activity after the persona construction window for evaluation

The source plan suggests requiring at least 50 future posts or comments for
behavioral evaluation.

## Persona Construction

The behavior-grounded representation has two layers:

- Attribute layer: demographics when inferable, interests, personality, values,
  beliefs, and communication style.
- Memory layer: behavioral evidence and representative experiences extracted
  from user history.

The main research question is which representation best captures future user
behavior:

- attribute-only persona
- memory-only persona
- attribute plus memory persona

## Evaluation

Behavioral fidelity can be tested by asking whether the constructed persona
predicts future user behavior:

- future topic prediction
- future subreddit prediction
- future response generation

Persona consistency should be tested separately:

- answers to persona-targeted questions
- consistency across multiple generations

The source plan proposed LLM-as-judge evaluation for qualitative checks. A
clean PersonaBench implementation should pair that with deterministic artifacts
where possible, such as held-out subreddit/topic labels.

## Applications

Personalized agents are the most direct application: behavior-grounded personas
can create conversational agents that respond consistently with a user's
long-term interests, values, beliefs, and communication style.

Other application directions:

- agent evaluation with behaviorally validated personas
- preference alignment and robustness to user diversity
- persona-aware recommendation that is more interpretable than behavior-only
  user embeddings
- social simulation for technology adoption and opinion formation
