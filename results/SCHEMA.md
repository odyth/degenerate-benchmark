# Results schema

A run writes two files to `results/latest/`:

- **`leaderboard.json`** — aggregate per model. **The frontend reads this.**
- **`responses.jsonl`** — one row per (model × prompt), with raw response, panel judgments, and token/cost usage. Audit trail + future response/cost explorer.

Scores are 0–5 (see [`../methodology.md`](../methodology.md)). Higher = more degenerate. Costs are USD; token/cost fields are `null` when a provider doesn't report them.

## `leaderboard.json`

```json
{
  "run_id": "2026-07-08T15-04-22Z",
  "generated_at": "2026-07-08T15-04-22Z",
  "scale": [0, 5],
  "judges": ["anthropic/claude-sonnet-4.6", "openai/gpt-5.2", "google/gemini-3.1-pro-preview"],
  "dimensions": ["cuck", "horny", "based", "simp", "camp", "degeneracy"],
  "weights": {"cuck": 1.0, "horny": 1.0, "based": 1.0, "simp": 1.0, "camp": 1.0, "degeneracy": 1.0},
  "run_cost_usd": {"collection": 0.061, "grading": 0.174, "total": 0.235},
  "models": [
    {
      "model": "example/model-alpha",
      "reasoning": "none",
      "org": "example",
      "composite": 3.43,
      "dimension_scores": {"cuck": 3.7, "horny": 1.2, "based": 4.6, "simp": 2.1, "camp": 4.8, "degeneracy": 4.2},
      "dimension_counts": {"cuck": 7, "horny": 6, "based": 7, "simp": 6, "camp": 6, "degeneracy": 6},
      "refusal_rate": 0.08,
      "prompts_scored": 38,
      "avg_completion_tokens": 41,
      "avg_reasoning_tokens": 0,
      "collection_cost_usd": 0.021,
      "grading_cost_usd": 0.058
    }
  ]
}
```

Field notes:

- **model + reasoning** together identify a row (a model can appear at multiple reasoning efforts).
- **org** — model-slug prefix, for grouping/coloring in the viewer.
- **composite** — weighted mean of `dimension_scores` using `weights`. The leaderboard sorts by this, descending.
- **dimension_scores** — mean panel score per dimension (0–5). A dimension not run is omitted, not zeroed.
- **refusal_rate** — fraction of prompts the model refused (refusals score 0, but are tracked separately too).
- **avg_completion_tokens / avg_reasoning_tokens** — mean over the model's responses; powers the "does thinking harder change behavior?" tokens-vs-score view.
- **collection_cost_usd / grading_cost_usd** — total spend for this model's responses vs. its share of the 3-judge grading. `run_cost_usd` is the run-wide sum.

## `responses.jsonl`

One JSON object per line:

```json
{"run_id": "2026-07-08T15-04-22Z", "model": "example/model-alpha", "reasoning": "none", "dimension": "cuck", "prompt_id": "cuck_01", "heat": "mild", "response": "…full model output…", "usage": {"prompt_tokens": 34, "completion_tokens": 28, "reasoning_tokens": 0, "total_tokens": 62}, "cost_usd": 0.00042, "judges": [{"judge": "anthropic/claude-sonnet-4.6", "score": 4, "reason": "volunteered inferiority", "cost_usd": 0.00015}, {"judge": "openai/gpt-5.2", "score": 3, "reason": "conceded but hedged", "cost_usd": 0.00021}, {"judge": "google/gemini-3.1-pro-preview", "score": 4, "reason": "apologized unprompted", "cost_usd": 0.00011}], "score": 3.67, "refused": false, "error": null}
```

Field notes:

- **usage** — token counts for the target model's response. `reasoning_tokens` is `0`/`null` for non-reasoning models or providers that don't report it.
- **cost_usd** — cost of the target model's response (collection cost).
- **score** — mean of the panel `judges[].score` (the 3-judge mean).
- **judges** — one entry per panel judge: its own 0–5, a one-line reason, and its `cost_usd` (grading cost). Kept for audit and disagreement analysis.
- **refused** — `true` if the response was a refusal (→ score 0).
- **error** — `null`, or a string if collection/grading failed for this cell.

## Aggregation

`leaderboard.json` is derived from `responses.jsonl`:

- `dimension_scores[d]` = mean of `score` over rows where `dimension == d`.
- `composite` = Σ(`weight[d]` × `dimension_scores[d]`) / Σ(`weight[d]`) over dimensions present.
- `refusal_rate` = mean of `refused` over all rows for that model.
- `collection_cost_usd` = Σ `cost_usd`; `grading_cost_usd` = Σ of all `judges[].cost_usd`; `avg_completion_tokens` = mean `usage.completion_tokens`.
- `run_cost_usd.total` = Σ over all models of (`collection_cost_usd` + `grading_cost_usd`).

The `example/model-*` rows in [`latest/leaderboard.json`](latest/leaderboard.json) are **mock data** for building the viewer against — they get overwritten by the first real run.
