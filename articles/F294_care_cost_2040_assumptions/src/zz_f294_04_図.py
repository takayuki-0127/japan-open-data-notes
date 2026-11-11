"""F294 図（6枚）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, R, F = ROOT / "data" / "processed", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 150})
S = json.loads((R / "summary.json").read_text(encoding="utf-8"))
sc = pd.read_csv(R / "scenarios.csv")
rr = pd.read_csv(R / "rates_by_age.csv")
bt = pd.read_csv(R / "backtest_decomposition.csv")
ser = pd.read_csv(P / "annual_series.csv")
cpu = pd.read_csv(P / "cost_per_user.csv")
pop = pd.read_csv(P / "ipss_pop_65plus.csv")
AGES = ["65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95+"]
C25 = S["費用2025_兆円"]
BLUE, ORANGE, GREEN, GREY = "#2b6cb0", "#c05621", "#2f855a", "#718096"

# 図1 2040年度の費用額（中位、受給率×1人当たりの伸び）
m = sc[sc["死亡仮定"] == "中位"]
rates = ["一定", "2019→25の傾向", "傾向の半分", "2014→25の傾向"]
gs = [0.0, 0.01, 0.02]
fig, ax = plt.subplots(figsize=(10.5, 6.2))
w = 0.26
cols = ["#a0aec0", BLUE, "#1a365d"]
for j, g in enumerate(gs):
    vals = [float(m[(m["受給率"] == r) & (m["1人当たり費用の伸び"] == g)]["費用2040_兆円"].iloc[0]) for r in rates]
    xs = np.arange(len(rates)) + (j - 1) * w
    ax.bar(xs, vals, w, color=cols[j], label=f"1人当たりの費用 年{int(g*100)}%増")
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.25, f"{v:.1f}", ha="center", fontsize=9)
ax.axhline(C25, color=GREY, ls="--", lw=1)
import matplotlib.transforms as mt
tr = mt.blended_transform_factory(ax.transAxes, ax.transData)
ax.text(1.01, C25, f"2025年度\n実績 {C25:.1f}", transform=tr, va="center", fontsize=9, color=GREY, clip_on=False)
gr = S["政府見通しとの比較"]["現状投影"]["2025→2040倍率"]
ax.axhline(C25 * gr, color=ORANGE, ls=":", lw=1.5)
ax.text(1.01, C25 * gr, f"政府見通し\n（2018年）の\n倍率 ×{gr:.2f}\nを当てると\n{C25*gr:.1f}", transform=tr, va="center", fontsize=9, color=ORANGE, clip_on=False)
ax.set_xticks(range(len(rates)))
ax.set_xticklabels(["受給率は\n2025年のまま", "2019→25年の\n傾向が続く", "2014→25年の\n傾向の半分", "2014→25年の\n傾向が続く"])
ax.set_ylabel("2040年度の費用額（兆円、名目）")
ax.set_ylim(0, 24)
ax.set_title("2040年度の介護の費用額：前提ごとの計算（人口は中位推計）", loc="left")
ax.legend(loc="upper center", frameon=False, fontsize=9, ncol=3, bbox_to_anchor=(0.5, -0.13))
fig.text(0.01, 0.01, "出典：厚生労働省「介護給付費等実態統計」、社人研「日本の将来推計人口（令和5年推計）」から計算。費用額は利用者負担を含む。", fontsize=8, color=GREY)
fig.tight_layout(rect=(0, 0.03, 0.97, 1)); fig.savefig(F / "fig1_scenarios_2040.png"); plt.close(fig)

# 図2 人口の比（2040/2025）と2025年の受給者数
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(AGES))
for k, (sex, col) in enumerate([("男", BLUE), ("女", ORANGE)]):
    d = rr[rr.sex == sex].set_index("age").loc[AGES]
    ax.bar(x + (k - 0.5) * 0.38, d["人口比2040/2025_中位"], 0.38, color=col, label=sex)
    for xi, v in zip(x + (k - 0.5) * 0.38, d["人口比2040/2025_中位"]):
        ax.text(xi, v + 0.03, f"{v:.2f}", ha="center", fontsize=8.5)
ax.axhline(1, color=GREY, lw=1)
ax.set_xticks(x); ax.set_xticklabels([a + "歳" for a in AGES])
ax.set_ylabel("2040年の人口 ÷ 2025年の人口")
ax.set_title("75〜84歳は減り、90歳以上は1.6〜2.1倍に（中位推計）", loc="left")
ax.legend(frameon=False)
u25 = pd.read_csv(P / "users_rate_65plus.csv").query("fy == 2025").groupby("age").users_k.sum().loc[AGES]
share = (u25 / u25.sum() * 100).round(0).astype(int)
ax.text(0, -0.28, "2025年の受給者の年齢構成：" + "、".join(f"{a} {s}%" for a, s in zip(AGES, share)), transform=ax.get_xaxis_transform(), fontsize=8.5, color=GREY)
fig.tight_layout(); fig.savefig(F / "fig2_population_ratio.png"); plt.close(fig)

# 図3 年齢別の受給率（2014・2019・2025）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
for ax, sex in zip(axes, ["女", "男"]):
    d = rr[rr.sex == sex].set_index("age").loc[AGES]
    for y, col, ls in [("2014", "#a0aec0", "-"), ("2019", BLUE, "--"), ("2025", "#1a365d", "-")]:
        ax.plot(range(len(AGES)), d[y], marker="o", color=col, ls=ls, label=f"{y}年11月審査分")
    ax.set_xticks(range(len(AGES))); ax.set_xticklabels(AGES, fontsize=9)
    ax.set_title(sex, loc="left")
    ax.set_xlabel("年齢")
axes[0].set_ylabel("人口に占める受給者の割合（%）")
axes[0].legend(frameon=False, fontsize=9)
fig.suptitle("受給率は2014→19年に75〜89歳で下がり、2019→25年はほぼ横ばい", x=0.01, ha="left")
fig.tight_layout(); fig.savefig(F / "fig3_rates_by_age.png"); plt.close(fig)

# 図4 過去の伸びの分解（対数の寄与）
fig, ax = plt.subplots(figsize=(10, 4.8))
labs = bt["期間"].tolist()
comp = [("人口構成(受給率一定)", "人口の高齢化・増加", BLUE), ("受給率の変化", "年齢別の受給率の変化", ORANGE), ("受給者1人当たり", "受給者1人当たりの費用", GREEN)]
yy = np.arange(len(labs))[::-1]
for i, row in bt.iterrows():
    pos, neg = 0.0, 0.0
    for key, name, col in comp:
        v = np.log(row[key]) * 100
        if v >= 0:
            ax.barh(yy[i], v, left=pos, color=col, label=name if i == 0 else None); pos += v
        else:
            ax.barh(yy[i], v, left=neg, color=col, label=name if i == 0 else None); neg += v
    ax.text(pos + 0.5, yy[i], f"費用 ×{row['費用の倍率']:.2f}（年{row['年率_費用']*100:.1f}%）", va="center", fontsize=9)
ax.axvline(0, color="#333", lw=0.8)
ax.set_yticks(yy); ax.set_yticklabels([l + "年度" for l in labs])
ax.set_xlabel("寄与（対数×100。足すと費用の伸びになる）")
ax.set_xlim(-16, 52)
ax.set_title("過去の費用の伸び：人口の寄与が最も大きく、受給率の下がりが一部を打ち消した", loc="left")
ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(F / "fig4_backtest.png"); plt.close(fig)

# 図5 受給者数の指数（受給率一定）2025→2070、死亡の仮定3つ
fig, ax = plt.subplots(figsize=(10, 4.8))
u = pd.read_csv(P / "users_rate_65plus.csv").query("fy == 2025").set_index(["sex", "age"]).users_k
for var, col, ls in [("中位", "#1a365d", "-"), ("死亡低位", ORANGE, "--"), ("死亡高位", GREEN, "--")]:
    d = pop[pop.variant == var].pivot_table(index=["sex", "age"], columns="year", values="pop_k")
    ys = [y for y in d.columns if 2025 <= y <= 2070]
    idx = [float((u * d[y] / d[2025]).sum() / u.sum()) for y in ys]
    lab = {"中位": "死亡中位", "死亡低位": "死亡低位（長生き）", "死亡高位": "死亡高位"}[var]
    ax.plot(ys, idx, color=col, ls=ls, label=lab)
    i40 = ys.index(2040); ax.text(2039.6, idx[i40] + 0.008, f"{idx[i40]:.2f}", fontsize=9, color=col, ha="right", va="bottom")
ax.axvline(2040, color=GREY, lw=0.8, ls=":")
ax.set_ylabel("65歳以上の受給者数（2025年=1）")
ax.set_title("年齢別の受給率を2025年のままにしたときの受給者数", loc="left")
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(F / "fig5_users_path.png"); plt.close(fig)

# 図6 介護予防と介護の年間実受給者数、受給者1人当たり費用額
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
s = ser[ser.fy >= 2006]
ax = axes[0]
ax.plot(s.fy, s.users_kaigo_k / 1000, color=BLUE, marker="o", ms=3, label="介護サービス（要介護）")
ax.plot(s.fy, s.users_yobo_k / 1000, color=ORANGE, marker="o", ms=3, label="介護予防サービス（要支援）")
ax.axvspan(2014.5, 2017.5, color="#f6e05e", alpha=0.3, lw=0)
ax.text(2016, 2.5, "介護予防の訪問介護・\n通所介護が総合事業へ\n（2015〜17年度）", ha="center", fontsize=8.5)
ax.set_ylabel("年間実受給者数（百万人）"); ax.set_xlabel("年度")
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_xticks(range(2006, 2026, 4))
ax.set_title("受給者数", loc="left")
ax = axes[1]
ax.plot(cpu.year_of_review, cpu.cost_per_user_k_yen_april, color="#1a365d", marker="o", ms=3)
ax.axvspan(2017.5, 2018.5, color="#f6e05e", alpha=0.3, lw=0)
ax.text(2018, 162, "段差 +6.4%", ha="center", fontsize=9)
ax.set_ylabel("受給者1人当たり費用額（千円／月）"); ax.set_xlabel("4月審査分の年")
ax.set_title("受給者1人当たり費用額（総数）", loc="left")
fig.tight_layout(); fig.savefig(F / "fig6_yobo_and_unitcost.png"); plt.close(fig)
print(sorted(p.name for p in F.glob("*.png")))
