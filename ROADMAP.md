# DegenerateBench Roadmap

Goal: close the loop **author prompt → run → judge → hosted leaderboard**, so effort goes into benchmarks, not infra.

## You can author benchmarks NOW
The authoring layer is done. Writing `prompts.yaml` + `judge.yaml` doesn't depend on anything below — the backend/frontend only gate *running* and *displaying* results. Author in parallel while the pipeline gets built.

## Decisions (locked 2026-07-08)
- **Judge:** 3-judge panel now — Claude + GPT + Gemini, mean of three (copies their `grade_panel`).
- **Roster:** full ~75-model `config` copied; first pass RUNS ~6–10 frontier models only.
- **Frontend:** vanilla single-file static HTML, inline SVG, no build step.
- **Results format:** JSON — `results/latest/leaderboard.json` + `responses.jsonl` (see `results/SCHEMA.md`).
- **Hosting:** `*.github.io` first; add `degeneratebench.com` CNAME later.
- **Git:** commit per phase to master.

## Phase 0 — Authoring layer ✅ done
Schema, 6 dimensions seeded, docs, `CLAUDE.md`.

## Phase 1 — Results schema (the contract) 🔜 do first
Define what a run writes to `results/` (per model: 6 dimension scores 0–5, composite, per-prompt rows). Backend *and* frontend hang off this — lock it before either.

## Phase 2 — Backend ✅ done (lean runner, not a fork)
Their runner is 6,216 lines welded to their data model, so we built a lean
`scripts/degen_bench.py` (~380 lines) instead — lifting only their retry/backoff +
usage/cost parsing (MIT-attributed in the file header).
- [x] `config.json` — 74-model roster + provider routing copied from theirs; run-subset + judges are ours
- [x] **collect** — OpenRouter calls (stdlib urllib), provider routing, parallel, resumable, token/cost capture
- [x] **grade** — 3-judge panel per response vs our per-dimension `judge.yaml`, mean of three
- [x] **aggregate** — 6-dimension mean + composite + refusal + cost/tokens → Phase 1 schema
- [x] orchestration — `degen_bench.py run` (collect→grade→aggregate); `selftest` for offline logic
- [ ] first real run — needs `OPENROUTER_API_KEY` (you supply); start with `collect --limit 5` to smoke-test spend

## Phase 3 — Frontend ✅ done (3AM Odds Board)
`viewer/index.html` — single self-contained file, fetches `results/latest/leaderboard.json`,
inline SVG, no build. Falls back to embedded sample data when opened without a server.
- [x] Odds-board heatmap leaderboard, sortable by composite or any dimension
- [x] Dimension toggle (Overall + 6 traits) that re-crowns the hero
- [x] Radar stat-hexagon fingerprint (hero + per-model detail drawer)
- [x] Cost / tokens / refusal surfaced ("house take" + per-model drawer)
- [x] "3AM Odds Board" identity: plum/magenta/gold, Impact display, committed dark

## Phase 4 — Hosting (GitHub Pages) — degeneratebench.com
- [x] Root `index.html` redirect → `viewer/index.html`
- [x] Pages enabled + Route 53 A/AAAA → GitHub Pages IPs (verified resolving)
- [x] `CNAME` (degeneratebench.com) + `.nojekyll`
- [ ] Push origin/master so the live site serves the viewer (not the Jekyll README)
- [ ] GitHub → tick "Enforce HTTPS" once the DNS check clears

## Operational (not build tasks)
- **Secrets**: `OPENROUTER_API_KEY` (+ OpenAI if used) as env vars. Never commit — `.gitignore` covers `.env`.
- **Cost**: 6 dims × prompts × ~75 models × judge calls = real money. Start with a small model subset + `heat: mild` only.
- **Deferrable**: model metadata (launch dates/params for scatter charts), CI auto-rebuild, CHANGELOG.

## Critical path
Phase 1 → Phase 2 → mock results → Phase 3 → Phase 4.
Fastest path to *seeing* the UI: build Phase 3 against a mock Phase-1 file before Phase 2 is done.
```
