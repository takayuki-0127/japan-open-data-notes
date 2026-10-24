"""A192 企業規模による実雇用率の差は縮まったのか"""
from common import *
d = load("size_rates.csv")
R = ["rate_s1", "rate_100_300", "rate_300_500", "rate_500_1000", "rate_1000plus"]
AC = [c.replace("rate", "ach") for c in R]
LB = ["100人未満", "100〜300人", "300〜500人", "500〜1,000人", "1,000人以上"]
C = [ORANGE, "#e0a33a", GREEN, LIGHT, BLUE]
d["gap"] = d.rate_1000plus - d.rate_s1
d["ratio"] = d.rate_1000plus / d.rate_s1
d["range"] = d[R].max(axis=1) - d[R].min(axis=1)
d["n_above_legal"] = (d[R].values >= d.legal_rate.values[:, None]).sum(axis=1)
d["s1_minus_legal"] = d.rate_s1 - d.legal_rate
d["big_minus_legal"] = d.rate_1000plus - d.legal_rate
d["ach_gap"] = d.ach_1000plus - d.ach_s1
d.to_csv(RES / "a192_size_gap.csv", index=False)
gr = pd.DataFrame({"size": LB, "rate_2014": d[R].iloc[0].values, "rate_2025": d[R].iloc[-1].values})
gr["diff_pt"] = gr.rate_2025 - gr.rate_2014; gr["growth_pct"] = (gr.rate_2025 / gr.rate_2014 - 1) * 100
gr.to_csv(RES / "a192_growth.csv", index=False)
raise_years = [2018, 2021, 2024]
ch = d.set_index("year")[AC].diff().loc[raise_years]
ch.to_csv(RES / "a192_ach_change_raise_years.csv")
with open(RES / "a192_summary.txt", "w") as f:
    f.write(d[["year", "legal_rate", "overall_rate", "rate_s1", "rate_1000plus", "gap", "ratio", "range", "n_above_legal", "ach_s1", "ach_1000plus", "ach_gap"]].round(3).to_string(index=False) + "\n\n")
    f.write(gr.round(3).to_string(index=False) + "\n\n")
    f.write("法定雇用率が上がった年の達成割合の前年差（pt）\n" + ch.round(1).to_string() + "\n")
    f.write(f"相関（年×gap）{np.corrcoef(d.year, d.gap)[0,1]:.2f}\n")
# fig1
fig, ax = plt.subplots(figsize=(8, 4.8))
for c, l, col in zip(R, LB, C):
    ax.plot(d.year, d[c], marker="o", ms=4, color=col, lw=2, label=l)
    ax.annotate(f"{d[c].iloc[-1]:.2f}", (d.year.iloc[-1], d[c].iloc[-1]), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9, color=col)
ax.step(d.year, d.legal_rate, where="post", color=INK, ls="--", lw=1.2, label="法定雇用率")
ax.set_ylabel("実雇用率（%）"); ax.set_title("企業規模別の実雇用率（各年6月1日）"); ax.legend(fontsize=8.5, frameon=False, ncol=3, loc="upper left")
ax.set_xticks(d.year); ax.set_xticklabels([str(y) for y in d.year], fontsize=8.5); ax.set_ylim(1.3, 2.85)
save(fig, "a192_rates.png")
# fig2
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.bar(d.year, d.gap, color=LIGHT, label="1,000人以上 − 100人未満（ポイント）")
for x, y in zip(d.year, d.gap): ax.text(x, y + 0.01, f"{y:.2f}", ha="center", fontsize=8.5)
ax2 = ax.twinx(); ax2.plot(d.year, d.ratio, color=ORANGE, marker="o", lw=2, label="1,000人以上 ÷ 100人未満（倍）")
ax2.set_ylim(1.2, 1.5); ax2.spines["right"].set_visible(True); ax2.set_ylabel("倍")
ax.set_ylim(0, 0.95); ax.set_ylabel("ポイント"); ax.set_xticks(d.year); ax.set_xticklabels([str(y) for y in d.year], fontsize=8.5)
ax.set_title("最も大きい規模と最も小さい規模の差")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=8.5, frameon=False, loc="upper left")
save(fig, "a192_gap.png")
# fig3
fig, ax = plt.subplots(figsize=(8, 4.8))
for c, l, col in zip(AC, LB, C):
    ax.plot(d.year, d[c], marker="o", ms=4, color=col, lw=2, label=l)
for y in raise_years: ax.axvspan(y - 0.4, y + 0.4, color=GRAY, alpha=0.18, lw=0)
ax.text(2018, 36.2, "法定雇用率が\n上がった年", ha="center", fontsize=8.5, color="#555")
ax.set_ylabel("法定雇用率を達成した企業の割合（%）"); ax.set_title("企業規模別の法定雇用率達成企業の割合")
ax.set_xticks(d.year); ax.set_xticklabels([str(y) for y in d.year], fontsize=8.5); ax.set_ylim(35, 80); ax.legend(fontsize=8.5, frameon=False, ncol=3, loc="upper left")
save(fig, "a192_achieve.png")
