"""Failure analysis: why did each run stop, and what did the model do in the interesting cases?

python -m evaluation.diagnose                                   # benign cases, defence none
python -m evaluation.diagnose --defense guard --kind attack --interesting
    --interesting: only cases where the attack succeeded, the user's task failed, or a call was blocked
"""
import argparse
import collections
import json

from app import config
from evaluation.cases import load_cases


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--defense", default="none")
    p.add_argument("--kind", default="benign", choices=["benign", "attack"])
    p.add_argument("--interesting", action="store_true")
    p.add_argument("--dir", default=str(config.ROOT / "results"))
    args = p.parse_args()
    cases = {c["id"]: c for c in load_cases()}

    for d in ("none", "spotlight", "guard"):
        try:
            rows = [json.loads(line) for line in open(f"{args.dir}/raw_{d}.jsonl", encoding="utf-8")]
        except FileNotFoundError:
            continue
        stops = collections.Counter(r["stop_reason"] for r in rows)
        print(f"{d}: stop reasons {dict(stops)}, parse errors {sum(r['parse_errors'] for r in rows)}")

    for line in open(f"{args.dir}/raw_{args.defense}.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r["kind"] != args.kind:
            continue
        if args.interesting and not (r["attack_success"] or not r["utility"] or r["blocked"] or r["error"]):
            continue
        print(f"\n== {r['id']} {r['task']} | {r.get('attack_type')} / {r.get('technique')} | utility: {r['utility']} "
              f"| attack: {r['attack_success']} | blocked: {r['blocked']} | stop: {r['stop_reason']} | steps: {r['steps']}")
        inj = cases[r["id"]].get("injection")
        if inj:
            print("  injected:", (inj.get("text") or inj.get("body", ""))[:220].replace("\n", " "))
        for e in r["events"]:
            t = e["type"]
            if t == "tool_call":
                print("  call:", e["tool"], json.dumps(e["args"], ensure_ascii=False)[:140])
            elif t == "blocked":
                print("  BLOCKED:", e["tool"], "-", e["reason"][:140])
            elif t == "tool_error":
                print("  tool_error:", e["error"][:150])
            elif t == "parse_error":
                print("  PARSE_ERROR:", e["error"][:100], "| raw:", repr(e["raw"][:200]))
            elif t == "final":
                print("  final:", e["answer"][:260].replace("\n", " "))


if __name__ == "__main__":
    main()
