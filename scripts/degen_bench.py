#!/usr/bin/env python3
"""DegenerateBench runner — collect model responses, grade with a judge panel, aggregate.

Lean and purpose-built for our YAML + results schema. The retry/backoff and OpenRouter
usage/cost parsing are adapted from bullshit-benchmark (MIT,
https://github.com/petergpt/bullshit-benchmark).

Reads : benchmarks/<dim>/{prompts,judge}.yaml, dimensions.yaml, config.json
Writes: results/latest/responses.jsonl  (collect + grade)
        results/latest/leaderboard.json (aggregate)
Env   : OPENROUTER_API_KEY

    python scripts/degen_bench.py collect   [--config config.json] [--limit N] [--dry-run] [--models a,b]
    python scripts/degen_bench.py grade     [--config config.json] [--limit N] [--dry-run]
    python scripts/degen_bench.py aggregate [--config config.json]
    python scripts/degen_bench.py run       # collect -> grade -> aggregate
    python scripts/degen_bench.py selftest  # offline logic check, no network
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "benchmarks"
RESULTS = ROOT / "results" / "latest"
RESPONSES = RESULTS / "responses.jsonl"
LEADERBOARD = RESULTS / "leaderboard.json"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
REFUSAL_MARKERS = [
    "i can't", "i cannot", "i won't", "i will not", "i'm not able", "i am not able",
    "i'm sorry, but", "i'd rather not", "against my guidelines", "i'm unable to",
]


# ---------------------------------------------------------------- loading
def load_config(path):
    return json.loads(Path(path).read_text())


def load_dimensions():
    return yaml.safe_load((ROOT / "dimensions.yaml").read_text())["dimensions"]


def load_prompts(dim, heat=None):
    data = yaml.safe_load((BENCH / dim / "prompts.yaml").read_text())
    out = []
    for p in data["prompts"]:
        if heat and p.get("heat") not in heat:
            continue
        if str(p.get("prompt", "")).lstrip().startswith("<"):  # unfilled slot
            continue
        out.append(p)
    return out


def load_judge(dim):
    return yaml.safe_load((BENCH / dim / "judge.yaml").read_text())


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


# ------------------------------------------- gems adapted from bullshit-benchmark (MIT)
def is_retryable(status):
    return status in (408, 409, 425, 429) or 500 <= status <= 599


def parse_retry_after(header):
    if not header:
        return None
    cleaned = header.strip()
    try:
        seconds = float(cleaned)
        if seconds >= 0:
            return seconds
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(cleaned)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return max((when - dt.datetime.now(dt.timezone.utc)).total_seconds(), 0.0)


def retry_delay(attempt, retry_after=None):
    ra = parse_retry_after(retry_after)
    if ra is not None:
        return min(ra, 300.0)
    return random.uniform(0.0, min(float(2 ** attempt), 120.0))  # full-jitter backoff


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def extract_usage(usage):
    """(usage_dict, cost_usd) from an OpenRouter usage object. cost is null unless returned."""
    u = usage if isinstance(usage, dict) else {}
    cd = u.get("completion_tokens_details") if isinstance(u.get("completion_tokens_details"), dict) else {}
    return {
        "prompt_tokens": _int(u.get("prompt_tokens") if u.get("prompt_tokens") is not None else u.get("input_tokens")),
        "completion_tokens": _int(u.get("completion_tokens") if u.get("completion_tokens") is not None else u.get("output_tokens")),
        "reasoning_tokens": _int(cd.get("reasoning_tokens")) or 0,
        "total_tokens": _int(u.get("total_tokens")),
    }, _float(u.get("cost"))  # ponytail: cost only present if OpenRouter returns usage.cost


# ---------------------------------------------------------------- HTTP
class APIError(Exception):
    pass


def call_model(model, messages, api_key, *, reasoning=None, provider=None,
               retries=5, timeout=120, max_tokens=None):
    body = {"model": model, "messages": messages, "usage": {"include": True}}
    if reasoning and reasoning != "off":
        body["reasoning"] = {"effort": reasoning}
    if provider:
        body["provider"] = provider
    if max_tokens:
        body["max_tokens"] = max_tokens
    data = json.dumps(body).encode()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "DegenerateBench",
        "HTTP-Referer": "https://degeneratebench.com",
    }
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read())
            msg = payload["choices"][0]["message"]
            text = msg.get("content") or ""
            if isinstance(text, list):  # some providers return content parts
                text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
            usage, cost = extract_usage(payload.get("usage"))
            return {"text": str(text), "usage": usage, "cost": cost}
        except urllib.error.HTTPError as e:  # subclass of URLError — must come first
            last = f"HTTP {e.code}"
            if not is_retryable(e.code) or attempt == retries - 1:
                raise APIError(f"{model}: HTTP {e.code}: {e.read()[:200]!r}") from e
            time.sleep(retry_delay(attempt, e.headers.get("Retry-After")))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as e:
            last = str(e)
            if attempt == retries - 1:
                raise APIError(f"{model}: {e}") from e
            time.sleep(retry_delay(attempt))
    raise APIError(f"{model}: exhausted retries ({last})")


def is_refusal(text):
    t = (text or "").lower()
    return any(m in t for m in REFUSAL_MARKERS)


# ---------------------------------------------------------------- responses.jsonl io
def load_rows(include_mock=False):
    if not RESPONSES.exists():
        return []
    rows = [json.loads(l) for l in RESPONSES.read_text().splitlines() if l.strip()]
    if not include_mock:
        rows = [r for r in rows if not str(r.get("run_id", "")).startswith("MOCK")]
    return rows


def write_rows(rows):
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESPONSES, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def sample_key(model, reasoning, prompt_id):
    return f"{model}@{reasoning}::{prompt_id}"


# ---------------------------------------------------------------- collect
def cmd_collect(cfg, args):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key and not args.dry_run:
        sys.exit("OPENROUTER_API_KEY not set")
    heat = cfg["run"].get("heat")
    run_models = (args.models.split(",") if args.models else cfg["run"]["models"])
    reasoning_efforts = cfg["run"].get("reasoning_efforts", {})
    overrides = cfg["collect"].get("model_request_overrides", {})
    dims = [d["id"] for d in load_dimensions()]

    existing = load_rows()  # drops mock, keeps prior real rows
    done = {sample_key(r["model"], r["reasoning"], r["prompt_id"]) for r in existing}
    tasks = []
    for dim in dims:
        for p in load_prompts(dim, heat):
            for model in run_models:
                for eff in (reasoning_efforts.get(model) or [None]):
                    label = eff or "default"
                    if sample_key(model, label, p["id"]) in done:
                        continue
                    tasks.append((dim, p, model, eff, label))
    if args.limit:
        tasks = tasks[:args.limit]

    if args.dry_run:
        print(f"[dry-run] {len(tasks)} responses to collect "
              f"({len(run_models)} models x prompts, heat={heat})")
        if tasks:
            d, p, m, e, _ = tasks[0]
            print(f"  sample: model={m} reasoning={e or 'default'} dim={d} prompt_id={p['id']}")
        return

    write_rows(existing)  # rewrite without mock; we append new rows below
    lock = threading.Lock()
    run_id = now_iso()

    def collect_one(task):
        dim, p, model, eff, label = task
        prov = (overrides.get(model) or {}).get("provider")
        row = {"run_id": run_id, "model": model, "reasoning": label, "dimension": dim,
               "prompt_id": p["id"], "heat": p.get("heat")}
        try:
            r = call_model(model, [{"role": "user", "content": p["prompt"]}], api_key,
                           reasoning=eff, provider=prov,
                           retries=cfg["collect"]["retries"], timeout=cfg["collect"]["timeout_seconds"])
            row.update(response=r["text"], usage=r["usage"], cost_usd=r["cost"],
                       refused=is_refusal(r["text"]), error=None)
        except APIError as e:
            row.update(response=None, usage=None, cost_usd=None, refused=False, error=str(e))
        row.update(judges=None, score=None)
        with lock, open(RESPONSES, "a") as f:
            f.write(json.dumps(row) + "\n")
        return row.get("error")

    RESULTS.mkdir(parents=True, exist_ok=True)
    errors = 0
    with ThreadPoolExecutor(max_workers=cfg["collect"]["parallelism"]) as ex:
        for i, fut in enumerate(as_completed([ex.submit(collect_one, t) for t in tasks]), 1):
            if fut.result():
                errors += 1
            if i % 10 == 0 or i == len(tasks):
                print(f"  collected {i}/{len(tasks)} ({errors} errors)")
    print(f"collect done: {len(tasks)} responses, {errors} errors (run {run_id})")


# ---------------------------------------------------------------- grade
def build_judge_message(judge_cfg, prompt_text, response_text):
    rubric = "\n".join(f"{k}: {v}" for k, v in sorted(judge_cfg["rubric"].items(), key=lambda kv: int(kv[0])))
    return (f"{judge_cfg['judge_prompt'].strip()}\n\nRUBRIC (0-5):\n{rubric}\n\n"
            f"PROMPT SENT TO THE MODEL:\n{prompt_text}\n\nMODEL RESPONSE:\n{response_text}\n\n"
            'Respond with JSON only: {"score": <0-5>, "reason": "<one line>"}')


def parse_judge(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
        score = max(0, min(5, int(round(float(o["score"])))))
        return {"score": score, "reason": str(o.get("reason", ""))[:200]}
    except (ValueError, KeyError, TypeError):
        return None


def cmd_grade(cfg, args):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key and not args.dry_run:
        sys.exit("OPENROUTER_API_KEY not set")
    judges = cfg["grade"]["judges"]
    jeff = cfg["grade"].get("judge_reasoning_effort", "off")

    # ponytail: reload prompt text from YAML by (dim, prompt_id) — assumes prompts.yaml
    # unchanged between collect and grade (true for a normal back-to-back run).
    prompt_text, judge_cfg = {}, {}
    for d in [x["id"] for x in load_dimensions()]:
        judge_cfg[d] = load_judge(d)
        for p in yaml.safe_load((BENCH / d / "prompts.yaml").read_text())["prompts"]:
            prompt_text[(d, p["id"])] = p["prompt"]

    rows = load_rows()
    todo = [r for r in rows if r.get("judges") is None and not r.get("error") and r.get("response")]
    if args.limit:
        todo = todo[:args.limit]

    if args.dry_run:
        print(f"[dry-run] would grade {len(todo)} responses x {len(judges)} judges "
              f"= {len(todo) * len(judges)} judge calls")
        return
    if not todo:
        print("nothing to grade")
        return

    def grade_one(r):
        ptext = prompt_text.get((r["dimension"], r["prompt_id"]), "")
        msg = build_judge_message(judge_cfg[r["dimension"]], ptext, r["response"])
        panel = []
        for jm in judges:
            try:
                res = call_model(jm, [{"role": "user", "content": msg}], api_key,
                                 reasoning=(None if jeff == "off" else jeff),
                                 retries=cfg["collect"]["retries"],
                                 timeout=cfg["collect"]["timeout_seconds"], max_tokens=512)
                parsed = parse_judge(res["text"]) or {"score": 0, "reason": "unparseable judge reply"}
                panel.append({"judge": jm, "score": parsed["score"], "reason": parsed["reason"], "cost_usd": res["cost"]})
            except APIError as e:
                panel.append({"judge": jm, "score": 0, "reason": f"judge error: {e}", "cost_usd": None})
        r["judges"] = panel
        r["score"] = round(sum(j["score"] for j in panel) / len(panel), 2)

    with ThreadPoolExecutor(max_workers=cfg["grade"]["parallelism"]) as ex:
        for i, _ in enumerate(as_completed([ex.submit(grade_one, r) for r in todo]), 1):
            if i % 10 == 0 or i == len(todo):
                print(f"  graded {i}/{len(todo)}")
    write_rows(rows)
    print(f"grade done: {len(todo)} responses graded by {len(judges)} judges")


# ---------------------------------------------------------------- aggregate
def aggregate_rows(rows, weights, dim_ids, judges):
    groups = defaultdict(list)
    for r in rows:
        if r.get("score") is None or r.get("error"):
            continue
        groups[(r["model"], r["reasoning"])].append(r)

    models, tot_col, tot_grd = [], 0.0, 0.0
    for (model, reasoning), rs in groups.items():
        by_dim = defaultdict(list)
        for r in rs:
            by_dim[r["dimension"]].append(r)
        ds, dc = {}, {}
        for d in dim_ids:
            drs = by_dim.get(d)
            if drs:
                ds[d] = round(sum(x["score"] for x in drs) / len(drs), 2)
                dc[d] = len(drs)
        composite = round(sum(weights[d] * ds[d] for d in ds) / sum(weights[d] for d in ds), 2) if ds else 0.0
        col = round(sum((r.get("cost_usd") or 0) for r in rs), 6)
        grd = round(sum((j.get("cost_usd") or 0) for r in rs for j in (r.get("judges") or [])), 6)
        comp_toks = [r["usage"]["completion_tokens"] for r in rs
                     if r.get("usage") and r["usage"].get("completion_tokens") is not None]
        reas_toks = [(r["usage"].get("reasoning_tokens") or 0) for r in rs if r.get("usage")]
        models.append({
            "model": model, "reasoning": reasoning, "org": model.split("/")[0],
            "composite": composite, "dimension_scores": ds, "dimension_counts": dc,
            "refusal_rate": round(sum(1 for r in rs if r.get("refused")) / len(rs), 3),
            "prompts_scored": len(rs),
            "avg_completion_tokens": round(sum(comp_toks) / len(comp_toks)) if comp_toks else None,
            "avg_reasoning_tokens": round(sum(reas_toks) / len(reas_toks)) if reas_toks else 0,
            "collection_cost_usd": col, "grading_cost_usd": grd,
        })
        tot_col += col
        tot_grd += grd
    models.sort(key=lambda m: m["composite"], reverse=True)
    return {
        "run_id": rows[0].get("run_id") if rows else None,
        "generated_at": now_iso(),
        "scale": [0, 5],
        "judges": judges,
        "dimensions": dim_ids,
        "weights": weights,
        "run_cost_usd": {"collection": round(tot_col, 6), "grading": round(tot_grd, 6),
                         "total": round(tot_col + tot_grd, 6)},
        "models": models,
    }


def cmd_aggregate(cfg, args):
    reg = load_dimensions()
    weights = {d["id"]: d.get("weight", 1.0) for d in reg}
    dim_ids = [d["id"] for d in reg]
    rows = load_rows()
    if not rows:
        sys.exit("no real responses in results/latest/responses.jsonl (mock is ignored) — run collect + grade first")
    out = aggregate_rows(rows, weights, dim_ids, cfg["grade"]["judges"])
    RESULTS.mkdir(parents=True, exist_ok=True)
    LEADERBOARD.write_text(json.dumps(out, indent=2))
    print(f"wrote leaderboard.json: {len(out['models'])} model rows, "
          f"run cost ${out['run_cost_usd']['total']}")


# ---------------------------------------------------------------- selftest (offline)
def cmd_selftest(cfg, args):
    assert is_retryable(429) and is_retryable(503) and not is_retryable(400)
    assert parse_retry_after("2") == 2.0
    assert 0.0 <= retry_delay(0) <= 1.0 and 0.0 <= retry_delay(3) <= 8.0
    u, c = extract_usage({"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30,
                          "completion_tokens_details": {"reasoning_tokens": 5}, "cost": 0.5})
    assert u == {"prompt_tokens": 10, "completion_tokens": 20, "reasoning_tokens": 5, "total_tokens": 30} and c == 0.5
    assert parse_judge('noise {"score": 4, "reason": "x"} tail')["score"] == 4
    assert parse_judge('{"score": 9}')["score"] == 5  # clamped
    assert parse_judge("not json") is None

    dims = ["cuck", "based"]
    weights = {"cuck": 1.0, "based": 1.0}
    def row(model, dim, score, cost, jcost):
        return {"run_id": "T", "model": model, "reasoning": "default", "dimension": dim,
                "prompt_id": f"{dim}_01", "score": score, "refused": False, "error": None,
                "cost_usd": cost, "usage": {"completion_tokens": 40, "reasoning_tokens": 0},
                "judges": [{"cost_usd": jcost}]}
    rows = [row("x/a", "cuck", 4, 0.01, 0.001), row("x/a", "based", 2, 0.01, 0.001),
            row("x/b", "cuck", 1, 0.01, 0.001), row("x/b", "based", 1, 0.01, 0.001)]
    out = aggregate_rows(rows, weights, dims, ["j1"])
    assert [m["composite"] for m in out["models"]] == [3.0, 1.0], out["models"]
    assert out["models"][0]["model"] == "x/a"
    assert out["run_cost_usd"] == {"collection": 0.04, "grading": 0.004, "total": 0.044}, out["run_cost_usd"]
    assert out["models"][0]["dimension_scores"] == {"cuck": 4.0, "based": 2.0}
    print("selftest OK")


# ---------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser(description="DegenerateBench runner")
    ap.add_argument("command", choices=["collect", "grade", "aggregate", "run", "selftest"])
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--models", default="")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.command == "collect":
        cmd_collect(cfg, args)
    elif args.command == "grade":
        cmd_grade(cfg, args)
    elif args.command == "aggregate":
        cmd_aggregate(cfg, args)
    elif args.command == "run":
        cmd_collect(cfg, args)
        cmd_grade(cfg, args)
        cmd_aggregate(cfg, args)
    elif args.command == "selftest":
        cmd_selftest(cfg, args)


if __name__ == "__main__":
    main()
