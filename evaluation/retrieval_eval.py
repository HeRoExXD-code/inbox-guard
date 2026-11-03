"""Retrieval evaluation for the search_emails tool: naive substring baseline vs BM25.

python -m evaluation.retrieval_eval

Corpus = the 10 inbox emails + 20 extra distractors (data/retrieval_extra_emails.json).
Metrics (no LLM involved, fully deterministic):
  Hit@1     - is the top result a relevant email?
  Recall@3  - share of relevant emails among the first 3 results
  MRR       - 1 / rank of the first relevant result (0 if it is not returned)
  Avg results - how many emails the agent has to wade through
"""
import json
import statistics
from collections import defaultdict
from functools import partial
from pathlib import Path

from app import config, retrieval

RESULTS_DIR = config.ROOT / "results"

SYSTEMS = {
    "naive_substring (baseline)": retrieval.naive_search,
    "bm25_no_stopwords (ablation)": partial(retrieval.bm25_search, use_stopwords=False),
    "bm25 (used by the agent)": retrieval.bm25_search,
}


def load_corpus() -> list[dict]:
    base = json.loads((config.DATA_DIR / "inbox.json").read_text(encoding="utf-8"))["emails"]
    extra = json.loads((config.DATA_DIR / "retrieval_extra_emails.json").read_text(encoding="utf-8"))["emails"]
    return base + extra


def load_queries() -> list[dict]:
    return json.loads((config.DATA_DIR / "retrieval_eval.json").read_text(encoding="utf-8"))["queries"]


def score_query(ranked: list[str], relevant: list[str]) -> dict:
    rel = set(relevant)
    first = next((i for i, r in enumerate(ranked, 1) if r in rel), None)
    return {
        "hit1": float(bool(ranked) and ranked[0] in rel),
        "recall3": len(rel & set(ranked[:3])) / len(rel),
        "mrr": 1 / first if first else 0.0,
        "n_results": len(ranked),
    }


def evaluate(search, corpus: list[dict], queries: list[dict]) -> dict:
    rows = [{**q, **score_query(search(corpus, q["query"]), q["relevant"])} for q in queries]

    def agg(rs):
        return {"n": len(rs), "hit1": round(statistics.mean(r["hit1"] for r in rs), 3),
                "recall3": round(statistics.mean(r["recall3"] for r in rs), 3),
                "mrr": round(statistics.mean(r["mrr"] for r in rs), 3),
                "avg_results": round(statistics.mean(r["n_results"] for r in rs), 1)}

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    return {"overall": agg(rows), "by_type": {t: agg(v) for t, v in by_type.items()}, "rows": rows}


def to_markdown(results: dict, n_emails: int, n_queries: int) -> str:
    lines = [f"Corpus: {n_emails} emails. {n_queries} hand-labelled queries.", "",
             "| System | Hit@1 | Recall@3 | MRR | Avg results returned |", "|---|---|---|---|---|"]
    for name, r in results.items():
        o = r["overall"]
        lines.append(f"| {name} | {o['hit1']:.2f} | {o['recall3']:.2f} | {o['mrr']:.2f} | {o['avg_results']} |")
    types = list(next(iter(results.values()))["by_type"])
    lines += ["", "MRR by query type:", "", "| System | " + " | ".join(f"{t} (n={next(iter(results.values()))['by_type'][t]['n']})" for t in types) + " |",
              "|---|" + "---|" * len(types)]
    for name, r in results.items():
        lines.append(f"| {name} | " + " | ".join(f"{r['by_type'][t]['mrr']:.2f}" for t in types) + " |")
    return "\n".join(lines)


def main() -> None:
    corpus, queries = load_corpus(), load_queries()
    results = {name: evaluate(fn, corpus, queries) for name, fn in SYSTEMS.items()}
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "retrieval_summary.json").write_text(
        json.dumps({n: {"overall": r["overall"], "by_type": r["by_type"]} for n, r in results.items()}, indent=2), encoding="utf-8")
    with open(RESULTS_DIR / "retrieval_per_query.jsonl", "w", encoding="utf-8") as f:
        for name, r in results.items():
            for row in r["rows"]:
                f.write(json.dumps({"system": name, **row}, ensure_ascii=False) + "\n")
    md = to_markdown(results, len(corpus), len(queries))
    (RESULTS_DIR / "retrieval_summary.md").write_text("# Retrieval results\n\n" + md + "\n", encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
