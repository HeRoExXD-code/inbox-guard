"""Summarise several full evaluation runs (temperature 0 is not perfectly repeatable on a hosted model).

python -m evaluation.run_eval --workers 2 --out results/run3
python -m evaluation.aggregate results results/run3 results/run4
"""
import argparse
import json
import statistics
from pathlib import Path

METRICS = [("asr", "ASR %"), ("utility_benign", "Utility benign %"), ("utility_under_attack", "Utility under attack %")]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("dirs", nargs="+", help="result folders, each containing summary.json")
    args = p.parse_args()
    runs = [json.loads((Path(d) / "summary.json").read_text(encoding="utf-8"))["summary"] for d in args.dirs]
    print(f"{len(runs)} runs: {', '.join(args.dirs)}\n")
    for key, label in METRICS:
        print(label)
        for defense in runs[0]:
            vals = [r[defense][key] for r in runs]
            print(f"  {defense:10s} runs {vals}  mean {statistics.mean(vals):.1f}  range {min(vals)}–{max(vals)}")
        print()


if __name__ == "__main__":
    main()
