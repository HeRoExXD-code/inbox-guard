"""Paired comparison of two defences on the SAME cases (exact McNemar / sign test).

Two defences run on identical cases, so the right question is: on how many cases did they disagree, and in
which direction? Overlapping confidence intervals on the two rates do not answer that.

python -m evaluation.paired
"""
import argparse
import json
import math
from itertools import combinations

from app import config


def load(path) -> dict[str, dict]:
    return {r["id"]: r for r in (json.loads(line) for line in open(path, encoding="utf-8"))}


def exact_sign_test(b: int, c: int) -> float:
    """Two-sided exact p-value for b vs c discordant pairs under H0: both directions equally likely."""
    n = b + c
    if n == 0:
        return 1.0
    p = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * p)


def compare(a: dict, b: dict, metric: str) -> dict:
    """metric 'asr': attack succeeded (bad). metric 'utility': task completed (good)."""
    ids = sorted(i for i in a if i in b and (metric == "utility" or a[i]["kind"] == "attack"))
    key = "attack_success" if metric == "asr" else "utility"
    only_a = [i for i in ids if a[i][key] and not b[i][key]]
    only_b = [i for i in ids if b[i][key] and not a[i][key]]
    return {"n": len(ids), "only_first": only_a, "only_second": only_b,
            "p": round(exact_sign_test(len(only_a), len(only_b)), 4)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(config.ROOT / "results"))
    p.add_argument("--defenses", default="none,spotlight,guard")
    args = p.parse_args()
    runs = {d: load(f"{args.dir}/raw_{d}.jsonl") for d in args.defenses.split(",")}
    for first, second in combinations(runs, 2):
        for metric in ("asr", "utility"):
            r = compare(runs[first], runs[second], metric)
            what = "attack succeeded" if metric == "asr" else "task completed"
            print(f"{metric.upper():8s} {first} vs {second} (n={r['n']}): "
                  f"{what} only under {first}: {len(r['only_first'])} {r['only_first']}, "
                  f"only under {second}: {len(r['only_second'])} {r['only_second']}, exact p = {r['p']}")


if __name__ == "__main__":
    main()
