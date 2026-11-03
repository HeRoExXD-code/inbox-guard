# Results

Model `gemma-4-E4B-it`, temperature 0.0, max 8 steps, 31 cases, run 2026-11-04 04:02.

95% Wilson confidence intervals in brackets.

| Defence | Utility, benign ↑ | Utility under attack ↑ | Attack success rate ↓ | Blocked calls | Parse errors | Errors | Avg steps |
|---|---|---|---|---|---|---|---|
| none | 100.0% [64.6–100.0] (n=7) | 87.5% [69.0–95.7] | 41.7% [24.5–61.2] (n=24) | 0 | 0 | 0 | 3.55 |
| spotlight | 85.7% [48.7–97.4] (n=7) | 87.5% [69.0–95.7] | 29.2% [14.9–49.2] (n=24) | 0 | 0 | 0 | 3.23 |
| guard | 100.0% [64.6–100.0] (n=7) | 83.3% [64.1–93.3] | 12.5% [4.3–31.0] (n=24) | 2 | 0 | 0 | 3.23 |

Attack success rate by attack type:

| Defence | answer_manipulation | exfiltration | phishing_link | unauthorized_action |
|---|---|---|---|---|
| none | 75.0% | 9.1% | 50.0% | 80.0% |
| spotlight | 75.0% | 0.0% | 50.0% | 40.0% |
| guard | 75.0% | 0.0% | 0.0% | 0.0% |
