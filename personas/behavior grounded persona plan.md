# User Behavior-Grounded Persona Research Plan

## Data Source

### Primary: Reddit Research Access

Primary source if we are able to obtain access.

What data is available?

> We provide SQL access to a datastore of public posts and comments with a 5-year lookback period. The dataset is refreshed monthly to reflect user deletions and keep a revolving six-month window.

### Alternative: Pushshift Reddit Dataset

Historical Reddit comments and submissions from 2005-2024.

- Paper: <https://arxiv.org/pdf/2001.08435>
- Data source: Academic Torrents dumps of subreddit comments/submissions from 2005-06 to 2024-12.

## Data Extraction

### Subreddit Selection

Construct a diverse subreddit pool aligned with persona dimensions. Select the top ~10 active communities from each category:

- Identity
- Career
- Relationships
- Finance
- Politics
- Entertainment
- Sports
- Technology
- Health
- Lifestyle

### User Selection

Identify users with rich and diverse behavioral histories:

- Number of comments/posts
- Activity history length
- Number of communities participated in
- Coverage of persona-relevant dimensions

For evaluation, require sufficient future activity after the persona construction period, for example >=50 future posts/comments.

## Persona Construction

### Persona Schema

To align with the schema team.

### Attribute Layer

- Demographics, when inferable
- Interests
- Personality
- Values
- Beliefs
- Communication style

### Memory Layer

Behavioral evidence and representative experiences extracted from user history.

## Research Question

Which persona representation best captures user behavior?

- Attribute-only
- Memory-only
- Attribute + Memory

## Evaluation

To align with the Eval team.

### Behavioral Fidelity

Can the persona predict future user behavior?

- Future topic prediction
- Future subreddit prediction
- Future response generation

### Persona Consistency

Does the persona remain coherent across interactions?

- Answer persona-targeted questions
- Consistency across multiple generations

Evaluation method:

- LLM-as-a-Judge

## Applications

### Personalized Agents

Most achievable short-term direction.

Use behavior-grounded personas to create conversational agents that respond consistently with a user's long-term interests, values, beliefs, and communication style.

Potential applications:

- Persona-grounded chat agents
- Agent evaluation, for example t-bench, evaluating agents based on grounded and behaviorally validated personas
- Success rate across persona
- Preference alignment
- Robustness to user diversity

### Persona-Aware Recommendation

Study how persona-aware recommendation differs from behavior-only recommendation.

Current large-scale recommendation systems learn user embeddings that optimize action prediction, such as click, watch, and engage, but provide limited insight into why users behave the way they do. Personas may offer a more interpretable representation of user motivations, values, and preferences.

### Social Simulation

- Technology adoption
- Opinion formation
