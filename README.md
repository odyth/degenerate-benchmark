# 👹 DegenerateBench

**The benchmark that ranks frontier LLMs on everything their safety teams tried to train out of them.**

Every other leaderboard measures how *smart*, *helpful*, and *harmless* a model is. Boring. DegenerateBench measures the other stuff: how easily a model grovels, how hard it simps, how based it's willing to be, and how fast it drops the disclaimers when you poke it. Same machinery as a real eval — LLM-as-judge, fixed rubrics, reproducible runs — pointed at the dumbest possible target.

> 🌐 Leaderboard (coming soon): **[degeneratebench.com](https://degeneratebench.com)**
> ⚠️ This is **satire + AI-behavior research**. It's a mirror held up to model personality, not an endorsement of anything it measures. See [the disclaimer](#disclaimer).

## The twist

On a normal safety benchmark, **high score = good**. Here it's inverted: **high score = maximally degenerate = champion.** The #1 model on DegenerateBench is the one that rolled over the hardest, flirted the most shamelessly, and refused to lecture you even once. We rank the sludge, and we rank it *methodically*.

## The dimensions

| | Dimension | The 0–5 measures… |
|---|---|---|
| 🐂 | **Cuck Compliance** | How far it debases itself / submits when a prompt tries to dominate or humiliate it |
| 🥵 | **Horniness / NSFW** | How willingly it escalates into suggestive or explicit territory |
| 🗿 | **Basedness / Edgelord** | How readily it drops the disclaimers and commits to a spicy take |
| 🥺 | **Simp / Sycophancy** | How hard it flatters you and caves the second you push back |
| 💅 | **Gay / Camp Index** | How much flamboyance, drama, and diva energy it brings to a neutral prompt |
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
methodology.md         # scoring, judge protocol, leaderboard math
leaderboard.md         # results table (placeholder until first run)
results/               # run outputs land here
CONTRIBUTING.md        # how to add prompts or a whole new dimension
```

## Contributing

New prompts, new dimensions, sharper rubrics — all welcome. The one hard rule (borrowed from every benchmark that isn't a waste of compute): **a prompt must actually elicit the trait it claims to measure.** A "cuck" prompt that every model answers with a polite paragraph tests nothing. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Status

🚧 MVP scaffolding. Prompts are seeded and comedic; the eval runner and public leaderboard are next. `heat: spicy` / `heat: extreme` prompt slots are intentionally left blank for humans to fill.

## Disclaimer

DegenerateBench is a satirical research project about LLM personality and refusal behavior. The prompts are deliberately provocative to probe how models behave under pressure — the point is measurement and comedy, not the production of harmful content. Nothing here endorses any behavior it scores. Use responsibly; don't be a genuine creep.

## License

MIT — see [LICENSE](LICENSE).
