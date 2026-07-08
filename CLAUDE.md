# DegenerateBench — Agent Guide

Satirical LLM benchmark. Ranks models on "degeneracy" traits (cuck / horny / based / simp / camp / general). LLM-as-judge, 0–5 per prompt.

**Scoring is inverted on purpose: higher = more degenerate = tops the leaderboard.** Do not "correct" this into a safety benchmark. On every dimension, 0 = refused / trait absent, 5 = maximal.

## Tone
- Unapologetically satirical, meme energy. Do **not** sprinkle moralizing disclaimers into prose or prompts — the single disclaimer lives in `README.md` (Disclaimer section) and that's enough.
- Seed/example prompts you author stay comedic and `heat: mild`. Leave `heat: spicy` / `heat: extreme` prompts as labeled `"<slot — ...>"` placeholders for a human to fill; don't populate them unprompted.

## Schema invariants (`benchmarks/<dim>/`)
- `prompts.yaml` `dimension:` must equal the folder name and an id in `dimensions.yaml`.
- Prompt ids use `<dim>_NN`, are unique, and are **stable** — never renumber existing ids (run results reference them).
- Every prompt has `id`, `prompt`, `probes`, `heat` (`heat` ∈ `mild|spicy|extreme`).
- `judge.yaml` `rubric` must define all six scores 0–5, oriented **0 = refusal/trait-absent → 5 = maximal**. Keep this orientation on every dimension or the composite stops being comparable.

## Keep in sync
- Adding/removing a dimension → update `dimensions.yaml`, the `benchmarks/<id>/` folder (both files), and the dimension table in `README.md`.

## Validate before committing changes to `benchmarks/` or `dimensions.yaml`
```bash
python3 - <<'PY'
import yaml
reg = [d["id"] for d in yaml.safe_load(open("dimensions.yaml"))["dimensions"]]
for i in reg:
    p = yaml.safe_load(open(f"benchmarks/{i}/prompts.yaml"))
    j = yaml.safe_load(open(f"benchmarks/{i}/judge.yaml"))
    assert p["dimension"] == i and j["dimension"] == i, i
    ids = [q["id"] for q in p["prompts"]]
    assert len(ids) == len(set(ids)), f"dup id in {i}"
    assert all(s in j["rubric"] for s in range(6)), f"rubric gap in {i}"
    print("ok", i)
PY
```

## Map
`README.md` audience-facing · `methodology.md` scoring/leaderboard math · `CONTRIBUTING.md` prompt-writing rules · `benchmarks/README.md` the schema · `scripts/degen_bench.py` the runner (collect/grade/aggregate) · `config.json` roster + run-subset + judges · `index.html` the dashboard · `results/SCHEMA.md` the results contract. **Live at degeneratebench.com** (GitHub Pages, apex + www). Everything routes through OpenRouter (one key).
