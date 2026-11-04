"""図を5枚作る（figures/）。"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

B = Path(__file__).resolve().parents[1]
D, R, F = B / "data", B / "results", B / "figures"
F.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
C1, C2, C3, G = "#2a6f97", "#e07a5f", "#81b29a", "#9aa0a6"
SRC = "出典：総務省統計局「家計調査」「消費者物価指数」をもとに作成（二人以上の世帯）"

nat = pd.read_csv(D / "annual_national.csv")
mon = pd.read_csv(R / "monthly_vs2021.csv")
gd = pd.read_csv(R / "group_decomposition.csv")
nd = pd.read_csv(R / "national_decomposition.csv")


def foot(fig, s=SRC):
    fig.text(0.01, 0.01, s, fontsize=8, color="#555")


# 1. 全国：電気代・単価・使用量（2021年=100）
n = nat[nat.year >= 2015].set_index("year")
sub = pd.read_csv(R / "national_decomposition.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
for col, lab, c in [("elec", "電気代（年間）", C2), ("yen_per_kwh", "1kWhあたりの単価", C1), ("kwh", "使用量（kWh）", C3)]:
    v = n[col] / n.loc[2021, col] * 100
    ax.plot(v.index, v.values, marker="o", color=c, label=lab, lw=2)
    ax.annotate(f"{v.iloc[-1]:.0f}", (v.index[-1], v.iloc[-1]), xytext=(6, 0), textcoords="offset points", color=c, va="center")
nosub = nd[(nd.base == 2021) & (nd.kind == "補助を足し戻す")].set_index("year")
v0 = n.loc[2021, "elec"]
ns = (v0 + nosub.d_spend) / v0 * 100
ax.plot(ns.index, ns.values, ls="--", color=C2, alpha=0.7, label="電気代（国の値引きがなかった場合の推計）")
ax.axhline(100, color=G, lw=0.8)
ax.set_xticks(range(2015, 2026))
ax.set_ylabel("2021年＝100")
ax.set_title("電気代の上がり方は、ほぼ単価の上がり方だった", loc="left", fontsize=13)
ax.legend(frameon=False, fontsize=9, loc="upper left")
foot(fig)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "f186_1_national.png")
plt.close(fig)

# 2. 月次：電気代の支出と物価指数（2021年の同じ月＝100）
m = mon[mon.year >= 2019].copy()
x = pd.PeriodIndex(m.month, freq="M").to_timestamp()
fig, ax = plt.subplots(figsize=(8.6, 4.6))
ax.plot(x, np.exp(m.d_ln_spend) * 100, color=C2, lw=2, label="電気代の支出（家計調査）")
ax.plot(x, np.exp(m.d_ln_price) * 100, color=C1, lw=2, label="電気代の物価指数（消費者物価指数）")
rates = pd.read_csv(D / "raw" / "subsidy_rates.csv")
for um in rates.usage_month:
    p = pd.Period(um, "M") + 1  # 支払・物価に出るのはおおむね翌月
    ax.axvspan(p.to_timestamp(), (p + 1).to_timestamp(), color="#f2cc8f", alpha=0.35, lw=0)
ax.axhline(100, color=G, lw=0.8)
ax.set_ylabel("2021年の同じ月＝100")
ax.set_title("物価指数は値引き（黄色）で上下し、支出は使用量の季節でも動いた", loc="left", fontsize=13)
ax.legend(frameon=False, fontsize=9, loc="upper left")
foot(fig, SRC.replace("（二人以上の世帯）", "（支出は二人以上の世帯。黄色は値引きが支払いに出るおおむねの月）"))
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "f186_2_monthly.png")
plt.close(fig)

# 3. 区分ごとの増え方を、単価と使用量に分ける（2021→2025、記録どおり）
main = gd[(gd.base == 2021) & (gd.year == 2025) & (gd.kind == "記録どおり")]
order = [("q5", ["Q1", "Q2", "Q3", "Q4", "Q5"]), ("age", ["a29", "a30", "a40", "a50", "a60", "a70"]),
         ("city", ["cbig", "cmid", "csmA", "csmB"])]
rows = []
for tab, gs in order:
    for g_ in gs:
        rows.append(main[(main.tab == tab) & (main.group == g_)].iloc[0])
    rows.append(None)
rows = rows[:-1]
fig, ax = plt.subplots(figsize=(8.4, 6.2))
y = np.arange(len(rows))[::-1]
lab = []
for yi, r in zip(y, rows):
    if r is None:
        lab.append("")
        continue
    ax.barh(yi, r.price_eff / 1000, color=C1, height=0.7)
    ax.barh(yi, r.qty_eff / 1000, left=r.price_eff / 1000 if r.qty_eff > 0 else 0, color=C3, height=0.7)
    ax.text(max(r.price_eff, r.price_eff + r.qty_eff) / 1000 + 0.6, yi, f"+{r.d_yen/1000:.1f}千円", va="center", fontsize=9)
    lab.append(r.label)
ax.set_yticks(y)
ax.set_yticklabels(lab)
ax.axvline(0, color="#333", lw=0.8)
ax.set_xlabel("年間の電気代の増え方（千円、2021年→2025年）")
ax.set_title("どの区分も、増えた分の大半は単価の上昇", loc="left", fontsize=13, pad=26)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C1, label="単価が上がった分"), Patch(color=C3, label="使用量が変わった分")], frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)
foot(fig, SRC.replace("（二人以上の世帯）", "（二人以上の世帯。上から年間収入五分位・世帯主の年齢・都市の大きさ）"))
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "f186_3_decomposition.png")
plt.close(fig)

# 4. 消費支出に占める電気代の割合（2021年と2025年）
fig, ax = plt.subplots(figsize=(8.4, 6.2))
for yi, r in zip(y, rows):
    if r is None:
        continue
    ax.plot([r.share0 * 100, r.share1 * 100], [yi, yi], color=G, lw=2)
    ax.scatter(r.share0 * 100, yi, color=G, zorder=3, s=30)
    ax.scatter(r.share1 * 100, yi, color=C2, zorder=3, s=36)
    ax.text(r.share1 * 100 + 0.06, yi, f"+{r.d_share_pt:.2f}pt", va="center", fontsize=9)
ax.set_yticks(y)
ax.set_yticklabels(lab)
ax.set_xlabel("消費支出に占める電気代の割合（%）　灰：2021年　橙：2025年")
ax.set_title("割合で見ると、収入の低い世帯ほど上がり幅が大きい", loc="left", fontsize=12.5)
foot(fig)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "f186_4_share.png")
plt.close(fig)

# 5. 頑健性：年間収入五分位の割合の上がり幅（期間・補助の扱いを変える）
combos = [(2021, 2025), (2020, 2025), (2021, 2024), (2021, 2023)]
fig, axes = plt.subplots(1, 2, figsize=(9, 4.4), sharey=True)
for ax, kind in zip(axes, ["記録どおり", "補助を足し戻す"]):
    for i, (b0, y1) in enumerate(combos):
        d = gd[(gd.tab == "q5") & (gd.base == b0) & (gd.year == y1) & (gd.kind == kind)].set_index("group")
        vals = [d.loc[f"Q{k}", "d_share_pt"] for k in range(1, 6)]
        ax.plot(range(1, 6), vals, marker="o", lw=1.8, label=f"{b0}→{y1}", color=[C2, C1, C3, "#6d597a"][i])
    ax.set_xticks(range(1, 6))
    ax.set_xticklabels(["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ"])
    ax.set_xlabel("年間収入五分位（Ⅰが低い）")
    ax.set_title(kind if kind == "記録どおり" else "国の値引きを足し戻した場合", fontsize=11)
    ax.axhline(0, color=G, lw=0.8)
axes[0].set_ylabel("電気代の割合の上がり幅（ポイント）")
axes[0].legend(frameon=False, fontsize=9)
fig.suptitle("8通りすべてで、第Ⅰ五分位の上がり幅は第Ⅴ五分位より大きかった", x=0.01, ha="left", fontsize=12.5)
foot(fig)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(F / "f186_5_robustness.png")
plt.close(fig)
print("figs ok")
