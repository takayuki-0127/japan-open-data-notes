"""T001：2026年の値で、元記事141の結論が続いたかを判定し、新しい切り口（4区分の並び）と頑健性を計算する。
先に src/a141_size_gap.py を実行して results/a141_gap_by_year.csv を作っておく。"""
import json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import *

t1 = pd.read_csv(DATA / "table1_rate_by_size.csv")
assert 2026 in set(t1.year), "先に src/a141_size_gap.py を実行する（2026年を足した表を data/ に書く）"
rate = t1.pivot(index="year", columns="size", values="rate_pct")[SIZES]
amt = t1.pivot(index="year", columns="size", values="amount_yen")[SIZES]
gap = rate["5,000人以上"] - rate["100～299人"]

# 判定（PLAN.md の基準）
g26 = round(float(gap[2026]), 2)
verdict = "続いた" if g26 >= 1.0 else "縮んだが残った" if g26 >= 0.5 else "止まった" if g26 >= 0 else "逆転した"
rank = int((gap.round(2) > g26).sum()) + 1  # 1975〜2026年で何番目に大きいか（同じ値は同順位）
ties = int((gap.round(2) == g26).sum())

# 頑健性
g_mid = rate["1,000～4,999人"] - rate["100～299人"]
ratio = amt["100～299人"] / amt["5,000人以上"]
# 新しい切り口：4区分が規模の順に並んでいる年（5,000人以上 ≥ 1,000〜 ≥ 300〜 ≥ 100〜）
r4 = rate[["5,000人以上", "1,000～4,999人", "300～999人", "100～299人"]]
mono = (r4.diff(axis=1, periods=-1).iloc[:, :3] >= 0).all(axis=1)
strict = (r4.diff(axis=1, periods=-1).iloc[:, :3] > 0).all(axis=1)

out = {
    "gap_2025": round(float(gap[2025]), 2), "gap_2026": g26, "verdict": verdict,
    "gap_2026_rank_1975_2026": rank, "gap_2026_ties": ties,
    "years_gap_ge_0.9": [int(y) for y in gap.index[gap.round(2) >= 0.9]],
    "gap_mean_2013_2022": round(float(gap.loc[2013:2022].mean()), 2),
    "gap_mean_2023_2026": round(float(gap.loc[2023:2026].mean()), 2),
    "rate_2026": {k: float(v) for k, v in rate.loc[2026].items()},
    "rate_2025": {k: float(v) for k, v in rate.loc[2025].items()},
    "amount_gap_yen_2025": float(amt.loc[2025, "5,000人以上"] - amt.loc[2025, "100～299人"]),
    "amount_gap_yen_2026": float(amt.loc[2026, "5,000人以上"] - amt.loc[2026, "100～299人"]),
    "robust_gap_1000_4999_minus_100_299": {str(y): round(float(g_mid[y]), 2) for y in [2022, 2023, 2024, 2025, 2026]},
    "robust_amount_ratio_small_over_large": {str(y): round(float(ratio[y]), 3) for y in [2019, 2022, 2023, 2024, 2025, 2026]},
    "order_monotone_years_since_2013": {str(y): bool(mono[y]) for y in range(2013, 2027)},
    "order_strict_years_since_2013": int(strict.loc[2013:].sum()),
    "order_monotone_share_1975_2012": round(float(mono.loc[1975:2012].mean()), 3),
    # レビューで追加：同じ値を許す（≥）並びと、厳密な（>）並びの年の一覧
    "order_weak_years_all": [int(y) for y in mono.index[mono]],
    "order_strict_years_all": [int(y) for y in strict.index[strict]],
    "order_weak_count_1975_2012": [int(mono.loc[1975:2012].sum()), int(mono.loc[1975:2012].size)],
    "order_weak_count_2013_2022": [int(mono.loc[2013:2022].sum()), int(mono.loc[2013:2022].size)],
    "years_gap_eq_0.7": [int(y) for y in gap.index[gap.round(2) == 0.7]],
}
(RES / "t001_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))

# 記事の図1 元記事との比較：差の推移（2013〜2026年）、元記事の最終年（2025年）と新しい年（2026年）
fig, ax = plt.subplots(figsize=(8.6, 4.0))
g = gap.loc[2013:]
colors = [ORANGE if y == 2026 else (GRAY if y == 2025 else "#d9d8d4") for y in g.index]
ax.bar(g.index, g.values, color=colors, width=0.7)
for y, v in g.items():
    ax.text(y, v + 0.03, f"{v:.1f}", ha="center", fontsize=9, color=INK)
ax.axhline(1.0, color=INK, lw=0.8, ls="--"); ax.text(2012.6, 1.03, "「続いた」の基準 1.0", fontsize=8.5, color=INK)
ax.axhline(0.5, color=GRAY, lw=0.8, ls=":"); ax.text(2012.6, 0.53, "「止まった」の境 0.5", fontsize=8.5, color=GRAY)
ax.set_ylabel("改定率の差（ポイント）"); ax.set_xticks(list(g.index)); ax.tick_params(axis="x", labelsize=8.5)
ax.set_title("5,000人以上と100〜299人の改定率の差：元記事の最終年2025年（濃い灰）と2026年（橙）", loc="left", fontsize=12)
fig.text(0.0, -0.03, SOURCE + "（2026年は令和8年調査の第2表）", fontsize=7.5, color=GRAY)
fig.savefig(FIG / "t001_compare.png"); plt.close(fig)

# 記事の図2 4区分の改定率：2025年→2026年
fig, ax = plt.subplots(figsize=(7.2, 4.2))
cols = {"5,000人以上": ORANGE, "1,000～4,999人": "#f3a77f", "300～999人": LIGHT, "100～299人": BLUE}
for s, c in cols.items():
    a, b = rate.loc[2025, s], rate.loc[2026, s]
    ax.plot([0, 1], [a, b], color=c, lw=2.2, marker="o")
    ax.text(-0.04, a, f"{s} {a:.1f}", ha="right", va="center", fontsize=9, color=c)
    ax.text(1.04, b, f"{b:.1f}", ha="left", va="center", fontsize=9, color=c)
ax.set_xlim(-0.75, 1.25); ax.set_xticks([0, 1]); ax.set_xticklabels(["2025年", "2026年"])
ax.set_ylabel("1人平均賃金の改定率（％）")
ax.set_title("企業規模別の改定率：大きい企業は下がり、小さい企業は上がった", loc="left", fontsize=12)
fig.text(0.0, -0.03, SOURCE + "（令和8年調査の第2表）", fontsize=7.5, color=GRAY)
fig.savefig(FIG / "t001_sizes_2025_2026.png"); plt.close(fig)
