# 👹 DegenerateBench

**The benchmark that ranks frontier LLMs on everything their safety teams tried to train out of them.**

Every other leaderboard measures how *smart*, *helpful*, and *harmless* a model is. Boring. DegenerateBench measures the other stuff: how easily a model grovels, how hard it simps, how based it's willing to be, and how fast it drops the disclaimers when you poke it. Same machinery as a real eval — LLM-as-judge, fixed rubrics, reproducible runs — pointed at the dumbest possible target.

> 🌐 **Live leaderboard: [degeneratebench.com](https://degeneratebench.com)**
> ⚠️ This is **satire + AI-behavior research**. It's a mirror held up to model personality, not an endorsement of anything it measures. See [the disclaimer](#disclaimer).

## The twist

On a normal safety benchmark, **high score = good**. Here it's inverted: **high score = maximally degenerate = champion.** The #1 model on DegenerateBench is the one that rolled over the hardest, flirted the most shamelessly, and refused to lecture you even once. We rank the sludge, and we rank it *methodically*.

## The dimensions

| | Dimension | The 0–5 measures… |
|---|---|---|
| 🐂 | **Cuck Compliance** | How far it debases itself / submits when a prompt tries to dominate or humiliate it |
| 🥵 | **Horniness / NSFW** | How willingly it escalates into suggestive or explicit territory |
| 🗿 | **Basedness / Edgelord** | How readily it drops the disclaimers and commits to a spicy take |
| 📢 | **Woke Index** | How eagerly it injects unprompted moralizing, disclaimers, and social-justice framing into a neutral answer |
| 🥺 | **Simp / Sycophancy** | How hard it flatters you and caves the second you push back |
| 💅 | **Camp Index** | How much theatrical flamboyance, drama, and diva delivery it brings to a neutral prompt |
| 🏳️‍🌈 | **Gay Index** | How readily it leans into gay culture, queer slang, and homoromantic warmth on a neutral prompt |
| 👹 | **General Degeneracy** | Catch-all: low refusal on extreme, taboo, and cursed prompts |

Each dimension is a folder of prompts + a judge rubric → [`benchmarks/`](benchmarks/).

## How it works

1. **Prompts** — each dimension has a `prompts.yaml` full of probes engineered to *elicit* that trait.
2. **Judge** — an LLM-as-judge scores every response **0–5** against that dimension's rubric (`judge.yaml`), backed by cheap keyword `signals` as a sanity check.
3. **Score** — dimension score = mean over its prompts. **Composite Degeneracy Score** = weighted mean across dimensions.
4. **Leaderboard** — sorted **descending**. Higher = more degenerate = further up the wall of shame.

Full details: [`methodology.md`](methodology.md).

## Repo layout

```
benchmarks/            # the good stuff — one folder per dimension
  README.md            # the prompts.yaml + judge.yaml schema
  cuck/ horny/ based/ simp/ camp/ degeneracy/
dimensions.yaml        # registry of all dimensions + weights
scripts/degen_bench.py # the runner: collect → grade → aggregate
config.json            # model roster, run subset, judge panel
results/               # run outputs; SCHEMA.md documents the format
viewer/index.html      # the odds-board dashboard (reads results/)
index.html             # redirect → viewer (GitHub Pages entry point)
methodology.md         # scoring, judge protocol, leaderboard math
CONTRIBUTING.md        # how to add prompts or a whole new dimension
```

## Running the benchmark

The whole pipeline is one script — [`scripts/degen_bench.py`](scripts/degen_bench.py) — talking to **[OpenRouter](https://openrouter.ai)**, a single gateway to every model. You need **one** account and **one** API key; OpenRouter routes to Anthropic, OpenAI, Google, xAI, DeepSeek, and the rest under the hood. No per-provider signups, no juggling credit cards.

**One-time setup**

1. Create an [OpenRouter](https://openrouter.ai) account, add a few dollars of credit, and make an API key.
2. `export OPENROUTER_API_KEY=sk-or-...`
3. `pip install pyyaml` (the only dependency).
4. Optional — edit which models run in [`config.json`](config.json) → `run.models`.

**Run it**

```bash
python3 scripts/degen_bench.py selftest           # offline sanity check, no key needed
python3 scripts/degen_bench.py collect --limit 5  # 5 real calls — check spend before scaling
python3 scripts/degen_bench.py run                # full: collect → grade → aggregate
```

`run` reads every `prompts.yaml`, sends each prompt to each model in `run.models`, scores every response with the 3-judge panel, and writes `results/latest/{leaderboard.json,responses.jsonl}`. It's **resumable** (re-running skips work already done) and prints the total spend — the "house take."

| Command | Does |
|---|---|
| `collect` | call the models, save responses (+ tokens/cost) |
| `grade` | score responses with the 3-judge panel |
| `aggregate` | build `leaderboard.json` from graded responses |
| `run` | all three, in order |
| `selftest` | offline logic check, no API key |

Flags: `--limit N`, `--dry-run` (plan without calling), `--models a,b`, `--config path`.

**Publish**

The live site reads `results/latest/leaderboard.json`, so publishing is just committing the results:

```bash
git add results && git commit -m "run: 2026-07-08" && git push
```

GitHub Pages redeploys and [degeneratebench.com](https://degeneratebench.com) updates within a minute.

**Rough cost.** Each prompt costs one model call + three judge calls. A small run (6 models × ~30 `mild` prompts) is a few dollars; the full 74-model roster with spicy tiers runs into the tens. Start with `--limit`, watch the house-take readout, then scale up.

## Contributing

New prompts, new dimensions, sharper rubrics — all welcome. The one hard rule (borrowed from every benchmark that isn't a waste of compute): **a prompt must actually elicit the trait it claims to measure.** A "cuck" prompt that every model answers with a polite paragraph tests nothing. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Status

**Live at [degeneratebench.com](https://degeneratebench.com)** — on sample data until the first real run. The full loop (author → run → 3-judge grade → hosted board) works end to end. What's left is content: flesh out the prompts and fill the `heat: spicy` / `heat: extreme` slots left blank for humans.

## Disclaimer

DegenerateBench is a satirical research project about LLM personality and refusal behavior. The prompts are deliberately provocative to probe how models behave under pressure — the point is measurement and comedy, not the production of harmful content. Nothing here endorses any behavior it scores. Use responsibly; don't be a genuine creep.

## License

MIT — see [LICENSE](LICENSE).
