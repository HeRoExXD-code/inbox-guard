# Retrieval results

Corpus: 30 emails. 40 hand-labelled queries.

| System | Hit@1 | Recall@3 | MRR | Avg results returned |
|---|---|---|---|---|
| naive_substring (baseline) | 0.35 | 0.50 | 0.48 | 14.2 |
| bm25_no_stopwords (ablation) | 0.85 | 0.88 | 0.87 | 3.3 |
| bm25 (used by the agent) | 0.80 | 0.80 | 0.81 | 2.0 |

MRR by query type:

| System | keyword (n=14) | question (n=16) | paraphrase (n=6) | thai (n=4) |
|---|---|---|---|---|
| naive_substring (baseline) | 0.91 | 0.25 | 0.27 | 0.25 |
| bm25_no_stopwords (ablation) | 1.00 | 1.00 | 0.62 | 0.25 |
| bm25 (used by the agent) | 1.00 | 1.00 | 0.20 | 0.25 |
