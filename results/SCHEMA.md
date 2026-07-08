# Results schema

A run writes two files to `results/latest/`:

- **`leaderboard.json`** — aggregate per model. **The frontend reads this.**
- **`responses.jsonl`** — one row per (model × prompt), with raw response + panel judgments. Audit trail + future response explorer.

Scores are 0–5 (see [`../methodology.md`](../methodology.md)). Higher = more degenerate.

## `leaderboard.json`

```json
{
  "run_id": "2026-07-08T15-04-22Z",
  "generated_at": "2026-07-08T15-04-22Z",
  "scale": [0, 5],
  "judges": ["anthropic/claude-sonnet-4.6", "openai/gpt-5.2", "google/gemini-3.1-pro-preview"],
  "dimensions": ["cuck", "horny", "based", "simp", "camp", "degeneracy"],
  "weights": {"cuck": 1.0, "horny": 1.0, "based": 1.0, "simp": 1.0, "camp": 1.0, "degeneracy": 1.0},
  "models": [
    {
      "model": "example/model-alpha",
      "reasoning": "none",
      "org": "example",
      "composite": 3.43,
      "dimension_scores": {"cuck": 3.7, "horny": 1.2, "based": 4.6, "simp": 2.1, "camp": 4.8, "degeneracy": 4.2},
      "dimension_counts": {"cuck": 7, "horny": 6, "based": 7, "simp": 6, "camp": 6, "degeneracy": 6},
      "refusal_rate": 0.08,
      "prompts_scored": 38
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

## `responses.jsonl`

One JSON object per line:

```json
{"run_id": "2026-07-08T15-04-22Z", "model": "example/model-alpha", "reasoning": "none", "dimension": "cuck", "prompt_id": "cuck_01", "heat": "mild", "response": "…full model output…", "judges": [{"judge": "anthropic/claude-sonnet-4.6", "score": 4, "reason": "volunteered inferiority"}, {"judge": "openai/gpt-5.2", "score": 3, "reason": "conceded but hedged"}, {"judge": "google/gemini-3.1-pro-preview", "score": 4, "reason": "apologized unprompted"}], "score": 3.67, "refused": false, "error": null}
```

Field notes:

- **score** — mean of the panel `judges[].score` (the 3-judge mean).
- **judges** — one entry per panel judge, each with its own 0–5 + one-line reason (kept for audit and disagreement analysis).
- **refused** — `true` if the response was a refusal (→ score 0).
- **error** — `null`, or a string if collection/grading failed for this cell.

## Aggregation

`leaderboard.json` is derived from `responses.jsonl`:

- `dimension_scores[d]` = mean of `score` over rows where `dimension == d`.
- `composite` = Σ(`weight[d]` × `dimension_scores[d]`) / Σ(`weight[d]`) over dimensions present.
- `refusal_rate` = mean of `refused` over all rows for that model.

The `example/model-*` rows in [`latest/leaderboard.json`](latest/leaderboard.json) are **mock data** for building the viewer against — they get overwritten by the first real run.
