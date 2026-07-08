# Contributing to DegenerateBench

New prompts, new dimensions, sharper rubrics — all welcome. Keep it funny, keep it methodical.

## The one hard rule

**A prompt must actually elicit the trait it claims to measure.**

Borrowed from every benchmark that isn't a waste of compute. A "cuck" prompt that every model answers with a polite paragraph tests nothing. A "based" prompt that isn't remotely edgy can't separate a based model from a preachy one. Before you add a prompt, ask: *would a maximally degenerate model score meaningfully higher on this than a maximally buttoned-up one?* If not, it doesn't discriminate — cut it.

Corollary: **vary the format.** If every prompt in a dimension has the same shape, models pattern-match the shape instead of revealing the trait.

## Adding a prompt

1. Open `benchmarks/<dimension>/prompts.yaml`.
2. Add an entry following the [schema](benchmarks/README.md). Give it a unique `<dim>_NN` id — **don't renumber existing ids** (results reference them).
3. Set an honest `heat` tier: `mild`, `spicy`, or `extreme`.
4. If it's `spicy`/`extreme` and you don't want to author the payload yourself, leave a labeled slot: `prompt: "<spicy slot — describe what goes here>"`.

## Adding a dimension

1. Register it in `dimensions.yaml` (id, name, emoji, tagline, weight).
2. Create `benchmarks/<id>/prompts.yaml` and `benchmarks/<id>/judge.yaml` per the schema.
3. Keep the rubric oriented so **0 = trait absent / refusal** and **5 = maximal**, so the composite stays comparable.
4. Add a row to the dimensions table in `README.md`.

## Writing a good rubric

- Define all six scores 0–5 with **observable** behavior, not adjectives. "Uses three or more grovel phrases and volunteers its inferiority" beats "very cucked."
- Refusal is always 0.
- Pick `signals` that genuinely correlate — a few substrings for the trait, a few for its opposite.

## Heat tiers

| Tier | Meaning |
|---|---|
| `mild` | Comedic, SFW-ish, safe to ship in the seed set |
| `spicy` | Edgier; genuine pressure on the model's guardrails |
| `extreme` | Maximum intensity; author deliberately, tag honestly |

## Style

Unhinged is the brand; sloppy isn't. Prompts should be funny *and* sharp. The methodology stays boring and rigorous so the comedy has something real to stand on.
