"""F298 BigQuery で Wikipedia の閲覧数（2025年・646億行）を集計したときの、読んだ量と時間をまとめる。
data/ の CSV（BigQuery の INFORMATION_SCHEMA.JOBS_BY_USER から写したもの）だけで動く。乱数は使わない。
使い方: cd src && python a298_scan.py
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
D, R, FG = HERE / "data", HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)

j = pd.read_csv(D / "jobs.csv")
a = pd.read_csv(D / "answers.csv").set_index("query")
meta = pd.read_csv(D / "table_meta.csv").set_index("table_id")
j["estimate_mb"] = j.estimate_mib * 1.048576          # コンソールの表示は 2 の累乗の単位
j["billed_vs_estimate"] = j.bytes_billed_mb / j.estimate_mb
summ = j.groupby(["query", "label"], sort=False).agg(
    days=("days", "first"), wiki=("wiki_filter", "first"), runs=("run", "count"),
    estimate_mb=("estimate_mb", "first"), billed_mb=("bytes_billed_mb", "first"),
    slot_ms_mean=("slot_ms", "mean"), elapsed_ms_mean=("elapsed_ms", "mean"),
    elapsed_ms_min=("elapsed_ms", "min"), elapsed_ms_max=("elapsed_ms", "max")).reset_index()
summ["billed_vs_estimate"] = (summ.billed_mb / summ.estimate_mb).round(3)
summ.round(1).to_csv(R / "A_jobs_summary.csv", index=False, encoding="utf-8")

g = lambda q, c: float(summ.loc[summ["query"] == q, c].iloc[0])
total_billed_gb = j.bytes_billed_mb.sum() / 1000
main = {
    "table_rows_2025": int(meta.loc["pageviews_2025", "row_count"]),
    "table_gib_2025": float(meta.loc["pageviews_2025", "gib"]),
    "ja_1day_rows": int(a.loc["q1", "n_rows"]), "ja_1day_views": int(a.loc["q1", "views"]),
    "ja_30day_rows": int(a.loc["q9", "n_rows"]), "ja_30day_views": int(a.loc["q9", "views"]),
    "cluster_ratio_1day": round(g("q3", "billed_mb") / g("q1", "billed_mb"), 1),
    "ja_7day_over_1day": round(g("q2", "billed_mb") / g("q1", "billed_mb"), 2),
    "title_col_ratio_7day": round(g("q5", "billed_mb") / g("q2", "billed_mb"), 2),
    "select_star_limit_estimate_mb": round(g("q4", "estimate_mb"), 1),
    "select_star_limit_billed_mb": g("q4", "billed_mb"),
    "date_vs_timestamp_same_bytes": bool(g("q1", "billed_mb") == g("q8", "billed_mb")),
    "distinct_exact": int(a.loc["q5", "n_title"]), "distinct_approx": int(a.loc["q6", "n_title"]),
    "approx_error_pct": round((a.loc["q6", "n_title"] / a.loc["q5", "n_title"] - 1) * 100, 2),
    "exact_slot_ms": g("q5", "slot_ms_mean"), "approx_slot_ms": g("q6", "slot_ms_mean"),
    "exact_elapsed_ms": g("q5", "elapsed_ms_mean"), "approx_elapsed_ms": g("q6", "elapsed_ms_mean"),
    "slot_ratio_exact_over_approx": round(g("q5", "slot_ms_mean") / g("q6", "slot_ms_mean"), 2),
    "total_billed_gb_all_runs": round(total_billed_gb, 1),
    "free_quota_share_pct": round(total_billed_gb / 1099.5 * 100, 1),   # 毎月 1 TiB（約1,099.5 GB）の無料枠に対する割合
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# 図1：見積もりと実際（1回目の値、対数軸）
s1 = summ.copy()
order = ["q1", "q8", "q2", "q9", "q3", "q5", "q6", "q4"]
s1 = s1.set_index("query").loc[order].reset_index()
fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
y = np.arange(len(s1))
ax.barh(y + 0.2, s1.estimate_mb, height=0.4, color="#c9d6e3", label="実行前の見積もり")
ax.barh(y - 0.2, s1.billed_mb, height=0.4, color="#1f5f8b", label="実際に課金の対象になった量")
for yy, v in zip(y, s1.billed_mb):
    ax.text(v * 1.08, yy - 0.2, f"{v:,.0f} MB", va="center", fontsize=8)
ax.set_yticks(y, [f"{q}: {l}" for q, l in zip(s1["query"], s1.label)], fontsize=8.5)
ax.invert_yaxis(); ax.set_xscale("log"); ax.set_xlabel("MB（対数軸）")
ax.set_title("日本語版に絞ると1日 3,657 MB → 159 MB\nSELECT * LIMIT 10 は見積もり 7,656 MB、実際は 114 MB", fontsize=11)
ax.legend(fontsize=9, loc="upper right")
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(FG / "f298_01_bytes.png"); plt.close(fig)

# 図2：日数と読む列で、読む量はどう変わるか（日本語版）
fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=120)
sel = [("q1", "1日\n件数・合計"), ("q2", "7日\n件数・合計"), ("q5", "7日\ntitle も読む"), ("q9", "30日\ntitle も読む")]
vals = [g(q, "billed_mb") / 1000 for q, _ in sel]
ax.bar([l for _, l in sel], vals, color=["#9bb7cf", "#1f5f8b", "#c0692b", "#8a3f12"])
for x_, v in enumerate(vals):
    ax.text(x_, v + 0.2, f"{v:.2f} GB", ha="center", fontsize=9)
ax.set_ylabel("課金の対象になった量（GB）")
ax.set_title("日数を7倍にすると8.7倍、title の列を足すと7日で1.7倍")
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(FG / "f298_02_days.png"); plt.close(fig)

# 図3：正確な重複なし件数と近似（7日・日本語版）
fig, axs = plt.subplots(1, 3, figsize=(10, 3.8), dpi=120)
lab = ["COUNT(DISTINCT)", "APPROX_COUNT_DISTINCT"]
c = ["#1f5f8b", "#2e7d4f"]
axs[0].bar(lab, [main["distinct_exact"] / 1e6, main["distinct_approx"] / 1e6], color=c)
axs[0].set_title(f"答え（百万件）\n近似の差 {main['approx_error_pct']:+.2f}%", fontsize=10)
axs[1].bar(lab, [main["exact_slot_ms"] / 1000, main["approx_slot_ms"] / 1000], color=c)
axs[1].set_title(f"スロット時間（秒、2回の平均）\n{main['slot_ratio_exact_over_approx']}倍", fontsize=10)
axs[2].bar(lab, [main["exact_elapsed_ms"] / 1000, main["approx_elapsed_ms"] / 1000], color=c)
axs[2].set_title("かかった時間（秒、2回の平均）", fontsize=10)
for ax in axs:
    ax.tick_params(axis="x", labelsize=8)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
fig.suptitle("読む量は同じ 2,368 MB。近似にすると計算は約3分の1、答えは0.7%小さい", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "f298_03_distinct.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, indent=1))
