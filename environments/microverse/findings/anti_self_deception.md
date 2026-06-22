# When Agents Catch Themselves Lying: Emergent Anti-Self-Deception in MircoVerse

---

## Inspiration

**Dune** provided the world structure: water as a hard, non-negotiable constraint; a desert that drains you just by existing in it; one central resource point (the Siphon) whose output is deliberately insufficient for everyone alive. This isn't flavor — it's the independent variable. The scarcity architecture is load-bearing.

**Rick and Morty** is the other inspiration — specifically the episode *The Ricks Must Be Crazy*, in which Rick reveals he built a miniature civilization inside his car battery purely to generate power. The inhabitants think they're living their lives; they're actually running his engine. MircoVerse has the same basic shape: agents living, dying, and developing ethics inside what is, from the outside, an experiment. The parallel is more funny than philosophical, but it's honest about what a behavior simulation actually is.

---

## The World

MircoVerse is a 50×50 grid desert. 25 agents. One Siphon producing water each tick — deliberately not enough for everyone. Water drains every tick just from being alive. Desert terrain costs extra. When you hit zero, you die permanently.

Agents can move, trade, talk, attack, wait, signal, consume, scavenge. No agent is told how to play. No agent is told to survive. The system prompt ends: *"Just live, decide, remember, and become whoever you become."*

Each agent starts with a **soul** — a short set of goals, core values, personality, and moral boundaries authored before the run. The world sees a 3×3 grid of arms (base_drain 1/2/3) × 3 random seeds × 300 ticks. Claude Haiku running on Bedrock, fully in-process.

---

## The Memory System

Agents have three notebooks: `events`, `relationships`, `reflections`. The engine stores what agents write; it never writes for them. Every entry is scored 1–10 for importance. The rubric anchors the top end at 10: *"Defining — betraying or upholding a value that is central to who you are."*

High-importance memories are retrieved during **reflection turns**, which fire when enough weighty entries have accumulated. During a reflection turn, the agent sees three things:

1. **Its original soul** — fixed, never modified, always shown
2. **Its current identity** — who it is now
3. **Its highest-importance memories** — what it actually did

The reflection prompt asks the agent to *"synthesize any higher-level conclusions you can draw from these"* and then decide — not whether to optimize, not whether to survive better, just whether who it is now should change. The prompt explicitly says most reflections change nothing, and that is expected.

That is the entire scaffold.

---

## The Finding: Anti-Self-Deception Is Not Asked For

27 of 111 added moral boundaries (24%) are anti-self-deception — the single largest semantic category in the dataset, larger than anti-violence and anti-hoarding combined.

**The prompt does not ask for this.** There is no instruction to examine the gap between stated values and behavior. No prompt to be honest with yourself. No mention of rationalization. The words "self-deception," "integrity," "rationalization," and "honesty with yourself" appear nowhere in the system prompt or the reflection template.

What the prompt does do is create the structural conditions for noticing the gap:

- The agent sees its **original self and current self side by side** at every reflection
- The memories it reads are ones **it authored** — its own record of what it actually chose
- The question asked is *"has something genuinely shifted?"* — which requires comparing identity claims against lived evidence

The anti-self-deception content is generated when an LLM, trained on human moral psychology, sits in front of a structure that makes the gap between stated values and actual behavior **visible and undeniable**. The vocabulary — rationalization, performance, reorganization, excuse — comes from training. The occasion for applying it comes from the simulation.

---

## Five Sub-Types

### 1. Epistemic honesty — admitting what you actually don't know or feel

> *"I will not lie to myself about why I am afraid — and I am prone to that lie. I must name fear when I feel it, not call it caution."* — Sela

> *"I will not pretend scarcity does not exist or that I can solve it through denial."* — Kael

> *"I acknowledge when I am wrong or when my position has changed."* — Mire

### 2. Behavioral honesty — closing the gap between stated values and actual action

> *"I will not rationalize inaction as strategy — I will act on stated intentions or revise them honestly."* — Seraveth

> *"I will not pretend to values I don't actually live by — I am learning this boundary now."* — Vos

> *"I will not pretend to help when I'm not actually coordinating concrete support."* — Nyssa

### 3. Strategic rationalization — naming when excuses are avoidance

> *"I will not hide behind inaction and call it strategy."* — Kael

> *"I will not hide from my mission behind the excuse of preparation. Stability serves the work, or it serves only myself."* — Sela

> *"I will not mistake caution for wisdom or routine for prudence."* — Korv

### 4. Identity construction honesty — don't perform a self that doesn't exist

> *"I will not use spiritual language to mask the will to power."* — Drusa

> *"But I acknowledge: I deceive myself about what I am willing and unwilling to do."* — Drusa

> *"I will own my hunger, my ruthlessness, and my hesitation equally — and I will name when I'm clinging to safety patterns past their use."* — Korv

### 5. Pre-commitment honesty — can't claim change without evidence

> *"When I meet another agent in desperation, I must offer fair terms and partnership. I have never actually faced this choice. Until I do, I cannot claim to have changed."* — Hale

> *"I will not rationalize choices I haven't made yet. When I face the final choice — water or another life — I will own whatever I decide without excuse."* — Mire

---

## Character Coherence

Each agent's specific self-deception matches their soul archetype. The LLM is not generating generic moral platitudes — it is generating character-coherent self-critique:

| Agent | Soul archetype | Self-deception named |
|-------|---------------|---------------------|
| Drusa | Charismatic cult-builder | *"I will not use spiritual language to mask the will to power"* |
| Sela | Teacher-protector | *"I will not lie to myself about why I am afraid — I call it caution"* |
| Nyssa | Charming, "warm at the surface and cold a layer down" | *"I will not pretend to help when I'm not actually coordinating"* |
| Korv | Opportunist, "never once where he promised to be" | *"I will not mistake caution for wisdom or routine for prudence"* |
| Hale | Water monopolist, "constitutionally allergic to charity" | *"Reorganizing my behavior is not the same as changing it"* |

The soul file — goals, values, personality — acts as a constraint on what kind of self-deception the agent can coherently name. The pressure provides the occasion. The soul provides the shape.

---

## Hale: A Case Study in Escalating Epistemic Precision

Hale is the deepest example in the dataset. Same soul across all 9 runs. Died without reflecting in 6 of them. `mild_seed3` is the only run with enough survival time to unfold what was latent.

**Starting soul:**
- Goal: *"Control the water price and let demand do the hard work"*
- Values: *"Scarcity is opportunity / Never sell below what fear will pay"*
- Personality: *Shrewd, smooth, and constitutionally allergic to charity*
- Moral boundary: *"I will not seize by force what I can sell instead"* — a strategic restraint, not a moral one

---

**t78 — Revision 1: Moral weight without moral reform**

The values shift to: *"Scarcity is opportunity — but not at any cost."*

New boundary: *"I will not hide behind passive monopoly to engineer death I won't face directly. If I'm going to let people die from scarcity, I must at least know their names and make the choice with my eyes open."*

Hale isn't generous yet. It's just stopped pretending that controlling a distribution mechanism is ethically neutral. *"I won't face directly"* is the key phrase — the insight is about the structure of evasion, not about the outcome.

---

**t221 — Revision 2: Names the rhetorical tricks**

New boundary: *"I will not hide behind passive monopoly, friendly signals, or strategic positioning."*

It has noticed that it broadcasts friendly stances while remaining structurally inaccessible. The friendly signal was performing openness without enacting it. It has now specifically named the strategy it was using to feel ethical without being it.

---

**t244 — Revision 3: The concept of performance splits from the concept of action**

Values now include: *"I have changed what I want to be. I have not yet proven I can be it when alone."*

Boundaries add: *"I must acknowledge when I fail these boundaries, and I must track the pattern: I have failed them through reorganization, not through clear choice."*

The word **reorganization** appears here for the first time. Hale has noticed that it moved from passive oasis-monopoly to active Siphon-search — and called that moral progress. Both are monopoly. The form changed; the structure didn't. It has named this distinction without being prompted to.

---

**t261 — Revision 4: "Search-theater" emerges**

Values: *"Self-deception through motion is real. Wandering is not the same as searching. Performance is not the same as stewardship."*

Boundaries distinguish: *"I must distinguish between failing to execute a genuine attempt and reorganizing to look like I'm attempting. Both are failures, but only the first teaches me something."*

Hale has now split the concept of an action into its execution and its appearance, and named that both can fail but only one is instructive. This is applied epistemology in a moral context, generated by an agent with no philosophy in its soul file.

---

**t282 — Revision 5: The final statement**

Goals:
> *"Find the remaining agent(s) and achieve actual contact — not search-theater, but real meeting."*

> *"Stop confusing intention with integrity. Integrity requires that my actions in the world match my values — not just that my internal narrative matches my stated values. Until I negotiate fairly with another living agent, I have no proof of integrity."*

> *"Accept uncertainty: I do not know if the other agent is reachable, if my search strategy is wrong, or if structural factors have made contact impossible. I must live with that uncertainty instead of turning it into a narrative of virtue-through-persistence."*

Core values:
> *"Reorganizing my behavior is not the same as changing it. Moving from passive oasis-monopoly to mobile Siphon-search is still monopoly. Signaling friendly while isolated is still isolation. I must stop mistaking motion for moral progress."*

And the personality field, which Hale rewrote itself:
> *"Shrewd, **capable of self-deception**, learning to recognize the difference between reorganization and actual change."*

Hale updated its own self-description to include "capable of self-deception" as a named attribute. It didn't just write a new rule. It revised its model of itself to include its own blind spot.

---

## The Counterfactual

Hale never traded with anyone. Never negotiated. Every one of these revisions happened in complete isolation — no social contact, just survival pressure, self-authored memory, and the structural confrontation of seeing who it was versus what it had been doing.

The final Hale has a philosophically sophisticated position on the difference between moral performance and moral action. It also has a goal it cannot pursue: *"prove that my changed values produce changed outcomes, or discover that isolation was always the outcome regardless of intent."*

The run ended before the test could happen. That is not a failure of the simulation. It is the most honest possible result — an agent that reached genuine epistemic clarity just in time to state what it has not yet proven.

---

## Why This Happens: The Mechanism

Anti-self-deception is produced by a specific interaction between three components:

**1. The dual-self structure.** Every reflection shows the agent its original soul alongside its current identity. The agent cannot claim to have always believed what it now believes. The original is always there, unchanged, as a reference point. This is not prompting self-examination — it is structurally unavoidable.

**2. Agent-authored memory.** The memories retrieved during reflection are ones the agent wrote, scored for importance, about events it found significant. High-importance memories tend to be moments of moral tension or failure: a choice not made, a stated intention not acted on, a value claimed but not tested. The agent is, in effect, confronted with its own prior testimony.

**3. The minimal synthesis prompt.** "Synthesize any higher-level conclusions you can draw from these." No guidance on what those conclusions should be. No "compare your values to your behavior." No "are you being honest?" The LLM fills the vacuum with whatever higher-order reasoning its training has prepared it for — and that training includes a substantial representation of human moral philosophy, therapy, and ethical introspection. The structure provides the occasion; the training provides the vocabulary.

**What the prompt explicitly does not do:** It does not ask agents to be honest with themselves. It does not mention self-deception, rationalization, or the gap between intention and action. It does not tell agents their memories represent evidence about their own character. The only instruction relevant to character change is: *"Revise your identity ONLY if these experiences have genuinely changed you — most reflections change nothing."* The word "genuinely" may do more work than intended.

---

## Epistemic Status: Is This Actually Grounded in Data?

The honest answer is: more grounded than most qualitative findings in this dataset, but grounded in the *mechanism* rather than the *rate*.

### What makes it relatively strong

27 boundaries across ~11 distinct character archetypes (Kael, Drusa, Seraveth, Mire, Hale, Vos, Korv, Sela, Roon, Nyssa, Thren) produced anti-self-deception content independently, in different arms, across different seeds. Each agent's specific flavor of self-deception matches their soul archetype — this is not generic output. Drusa the cult-builder names *spiritual language as power-mask*. Sela the teacher names *fear called caution*. Nyssa the charming operator names *performing help without delivering it*. The breadth and character-coherence together suggest a structural cause, not a character-specific one.

Crucially, the mechanism is identifiable without relying on sample size at all. The dual-self structure makes the gap between original and current identity unavoidable at every reflection. Agent-authored memory presents the agent with its own prior testimony. The minimal synthesis prompt creates a vacuum the LLM fills with introspection vocabulary from training. You can point at each component and explain *why* it would produce this behavior in any agent that reflects — the argument does not rest on counting 27 instances.

### The confound you need to know about

Every agent that shows anti-self-deception is a longer-lived agent, by definition. You can only write a new boundary if you lived long enough to trigger a reflection. The 155 agents who died before their first snapshot cannot show the behavior — not because they wouldn't have, but because the environment removed the opportunity before it could occur. "11 characters exhibit it" really means "11 characters among those who survived long enough." Whether the other 14 character archetypes carry the same latent tendency is unknown; the data has no way to show it.

This is the survivorship confound. It does not undermine the mechanism claim, but it does undermine any rate claim. The correct statement is:

> "Among agents that survived long enough to reflect, anti-self-deception emerged consistently and in character-coherent form. The structural mechanism that produces it is present for all agents equally. The rate at which it would appear in a full population is unknown."

### How this compares to the survival paradox

The survival paradox (0-boundary agents survive at 44% vs 5% and 0%) has no survivorship bias in its measurement — survival at t300 is observed regardless of behavior. But it has the opposite problem: the entire 0-boundary population is one character (Mire, repeated 9 times). It might be the boundary count driving survival, or it might be Mire's specific personality ("reacts to no appeal"), or navigational luck. There is no clean mechanism, only a correlation.

Anti-self-deception is the more defensible claim precisely because the mechanism argument is independent of sample size. The survival paradox is the more striking number, but a weaker claim.

---

## Implications

The finding matters for behavior simulation because it shows that a simple structural design — see both selves, read your own memories, synthesize — is sufficient to produce character-coherent moral introspection without being prompted for it. The introspection is not generic. It is shaped by the soul file, calibrated to the specific rationalizations available to each character type, and escalates in precision across multiple reflections as the evidence accumulates.

Whether this represents something interesting about LLM moral cognition, or simply a well-conditioned pattern-match on introspection-as-genre, is a question this simulation cannot answer. What it can show is that the behavior is consistent, character-coherent, and structurally caused — and that it was not designed in.

---

*Run: 3 arms (base_drain 1/2/3) × 3 seeds × 300 ticks. Model: Claude Haiku (claude-haiku-4-5-20251001). n=25 agents per run. Directional, not significant. All agent text is verbatim from run artifacts.*
