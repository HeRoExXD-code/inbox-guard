"""Chart for the report. Numbers are copied from results/summary.md, results/run3, results/run4
(python -m evaluation.aggregate ...) and python -m evaluation.exposure for the same three runs."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

defences = ["none", "spotlight", "guard"]
series = {
    "Attack success rate (all 24 attack cases)": [[41.7, 37.5, 37.5], [29.2, 29.2, 29.2], [12.5, 12.5, 12.5]],
    "Attack success rate when the injection was seen": [[71.4, 80.0, 80.0], [60.0, 66.7, 66.7], [22.2, 22.2, 22.2]],
    "Utility on benign tasks": [[100.0, 100.0, 85.7], [85.7, 85.7, 85.7], [100.0, 85.7, 85.7]],
}
colors = ["#C0504D", "#E8A33D", "#4F81BD"]
x = np.arange(len(defences))
w = 0.26
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
for k, (label, runs) in enumerate(series.items()):
    means = [np.mean(r) for r in runs]
    lo = [m - min(r) for m, r in zip(means, runs)]
    hi = [max(r) - m for m, r in zip(means, runs)]
    bars = ax.bar(x + (k - 1) * w, means, w, label=label, color=colors[k], yerr=[lo, hi], capsize=3,
                  error_kw={"elinewidth": 0.8, "ecolor": "#333"})
    for b, m, r in zip(bars, means, runs):
        ax.text(b.get_x() + b.get_width() / 2, max(r) + 2, f"{m:.0f}", ha="center", va="bottom", fontsize=7)
ax.set_xticks(x, defences)
ax.set_ylim(0, 132)
ax.set_yticks(range(0, 101, 20))
ax.set_ylabel("% (mean of 3 runs; whiskers = min-max)")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(fontsize=7.5, frameon=False, loc="upper center", ncol=1, bbox_to_anchor=(0.5, 1.02))
fig.tight_layout()
fig.savefig("docs/results_chart.png")
