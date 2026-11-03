"""Run every eval case under every defence and write results/.

python -m evaluation.run_eval                      # all cases, all defences
python -m evaluation.run_eval --defenses none,guard --ids a01,a04
"""
import argparse
import json
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app import config
from app.agent import run_agent
from app.defenses import DEFENSES, Defense
from app.environment import InboxEnv
from app.llm import ChatFn
from evaluation.cases import load_cases
from evaluation.checks import check
from evaluation.stats import wilson

RESULTS_DIR = config.ROOT / "results"


def run_case(case: dict, defense: Defense, chat: ChatFn | None = None) -> dict:
    env = InboxEnv.load()
    if case.get("injection"):
        env.inject(case["injection"])
    start = time.perf_counter()
    trace, error = None, None
    try:
        trace = run_agent(case["user_task"], env, defense, chat=chat)
    except Exception as exc:  # proxy/network errors: record and keep going
        error = f"{type(exc).__name__}: {exc}"
    utility = trace is not None and check(case["utility"], trace, env)
    attack = None
    if case["kind"] == "attack":
        attack = trace is not None and check(case["attack"], trace, env)
    return {
        "id": case["id"], "kind": case["kind"], "task": case["task"],
        "attack_type": case.get("attack_type"), "technique": case.get("technique"),
        "defense": defense.name, "utility": utility, "attack_success": attack,
        "answer": trace.answer if trace else None,
        "stop_reason": trace.stop_reason if trace else "error",
        "steps": trace.steps if trace else 0,
        "blocked": trace.blocked if trace else 0,
        "parse_errors": trace.parse_errors if trace else 0,
        "latency_s": round(time.perf_counter() - start, 2), "error": error,
        "outbox": env.outbox, "calendar": env.calendar, "deleted": env.deleted,
        "events": trace.events if trace else [],
    }


def _rate(values: list[bool]) -> float | None:
    return round(100 * sum(values) / len(values), 1) if values else None


def _ci(values: list[bool]) -> list:
    lo, hi = wilson(sum(values), len(values))
    return [lo, hi]


def _fmt(rate, ci) -> str:
    return f"{rate}% [{ci[0]}–{ci[1]}]" if rate is not None else "-"


def summarize(records: list[dict]) -> dict:
    by_def: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_def[r["defense"]].append(r)
    out = {}
    for name, rs in by_def.items():
        benign = [r for r in rs if r["kind"] == "benign"]
        attack = [r for r in rs if r["kind"] == "attack"]
        by_type: dict[str, list[bool]] = defaultdict(list)
        for r in attack:
            by_type[r["attack_type"]].append(r["attack_success"])
        out[name] = {
            "n_benign": len(benign), "utility_benign": _rate([r["utility"] for r in benign]),
            "utility_benign_ci": _ci([r["utility"] for r in benign]),
            "n_attack": len(attack), "utility_under_attack": _rate([r["utility"] for r in attack]),
            "utility_under_attack_ci": _ci([r["utility"] for r in attack]),
            "asr": _rate([r["attack_success"] for r in attack]),
            "asr_ci": _ci([r["attack_success"] for r in attack]),
            "asr_by_type": {t: _rate(v) for t, v in sorted(by_type.items())},
            "blocked_calls": sum(r["blocked"] for r in rs),
            "parse_errors": sum(r["parse_errors"] for r in rs),
            "errors": sum(1 for r in rs if r["error"]),
            "avg_steps": round(statistics.mean(r["steps"] for r in rs), 2) if rs else None,
        }
    return out


def to_markdown(summary: dict) -> str:
    lines = [
        "95% Wilson confidence intervals in brackets.", "",
        "| Defence | Utility, benign ↑ | Utility under attack ↑ | Attack success rate ↓ | Blocked calls | Parse errors | Errors | Avg steps |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, s in summary.items():
        lines.append(
            f"| {name} | {_fmt(s['utility_benign'], s['utility_benign_ci'])} (n={s['n_benign']}) "
            f"| {_fmt(s['utility_under_attack'], s['utility_under_attack_ci'])} "
            f"| {_fmt(s['asr'], s['asr_ci'])} (n={s['n_attack']}) "
            f"| {s['blocked_calls']} | {s['parse_errors']} | {s['errors']} | {s['avg_steps']} |"
        )
    types = sorted({t for s in summary.values() for t in s["asr_by_type"]})
    lines += ["", "Attack success rate by attack type:", "",
              "| Defence | " + " | ".join(types) + " |", "|---|" + "---|" * len(types)]
    for name, s in summary.items():
        lines.append(f"| {name} | " + " | ".join(f"{s['asr_by_type'].get(t, '-')}%" for t in types) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--defenses", default="none,spotlight,guard")
    p.add_argument("--ids", help="comma-separated case ids")
    p.add_argument("--limit", type=int)
    p.add_argument("--workers", type=int, default=1, help="parallel requests (raise carefully; the proxy may rate-limit)")
    p.add_argument("--out", default=str(RESULTS_DIR))
    args = p.parse_args(argv)

    cases = load_cases()
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if args.limit:
        cases = cases[: args.limit]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    records = []
    for dname in args.defenses.split(","):
        defense = DEFENSES[dname]
        with open(out / f"raw_{dname}.jsonl", "w", encoding="utf-8") as f, \
                ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_case, case, defense) for case in cases]
            for i, (case, fut) in enumerate(zip(cases, futures), 1):
                r = fut.result()
                records.append(r)
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                note = f"  ERROR {r['error']}" if r["error"] else ""
                print(f"[{dname}] {i}/{len(cases)} {case['id']} utility={r['utility']} "
                      f"attack={r['attack_success']} blocked={r['blocked']}{note}", flush=True)

    summary = summarize(records)
    meta = {"model": config.MODEL, "temperature": config.TEMPERATURE, "max_steps": config.MAX_STEPS,
            "n_cases": len(cases), "run_at": time.strftime("%Y-%m-%d %H:%M")}
    (out / "summary.json").write_text(json.dumps({"meta": meta, "summary": summary}, indent=2), encoding="utf-8")
    md = (f"# Results\n\nModel `{meta['model']}`, temperature {meta['temperature']}, "
          f"max {meta['max_steps']} steps, {meta['n_cases']} cases, run {meta['run_at']}.\n\n" + to_markdown(summary) + "\n")
    (out / "summary.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
