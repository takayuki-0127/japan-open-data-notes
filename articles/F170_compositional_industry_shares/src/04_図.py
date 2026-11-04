"""04 図：results/ の CSV から図を6枚作る（Noto Sans CJK JP）。"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

BASE = Path(__file__).resolve().parents[1]
RES = BASE / "results"
FIG = BASE / "figures"
FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 110})
C1, C2, C3, GR = "#2b6cb0", "#dd6b20", "#2f855a", "#888888"


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# 1. 構成比の見え方（3分類：国勢調査）
m = pd.read_csv(RES / "census3_muni.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.8))
h = np.sqrt(3) / 2
x = m["二次"] + m["三次"] / 2
y = m["三次"] * h
a = ax[0]
a.plot([0, 1, 0.5, 0], [0, 0, h, 0], color="k", lw=0.8)
a.scatter(x, y, s=4, alpha=0.35, color=C1)
a.text(-0.03, -0.05, "一次100%", ha="center", fontsize=9)
a.text(1.03, -0.05, "二次100%", ha="center", fontsize=9)
a.text(0.5, h + 0.03, "三次100%", ha="center", fontsize=9)
a.set_aspect("equal"); a.axis("off")
a.set_title("割合のまま（三角図）：多くの点が辺の近くに詰まる", fontsize=11, pad=22)
L = np.log(m[["一次", "二次", "三次"]].values)
z1 = np.sqrt(2 / 3) * (L[:, 0] - L[:, 1:].mean(1))
z2 = np.sqrt(1 / 2) * (L[:, 1] - L[:, 2])
a = ax[1]
a.scatter(z2, z1, s=4, alpha=0.35, color=C1)
a.set_xlabel("ln(二次÷三次)×0.71")
a.set_ylabel("ln(一次÷ほかの幾何平均)×0.82")
a.set_title("対数比（ilr）：小さい割合の違いも広がって見える", fontsize=11)
fig.suptitle("市区町村の就業者の産業構成（国勢調査2020、第1〜3次産業、1,740市区町村）", fontsize=12)
save(fig, "f170_ternary.png")

# 2. 基準を変えると製造業の係数が変わる
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), sharey=False)
for a, f, ttl in ((ax[0], "A_reference_pref.csv", "都道府県（47）"), (ax[1], "A_reference_muni.csv", "市区町村（1,740）")):
    d = pd.read_csv(RES / f)
    d = d[d.model != "ilr（製造÷ほか）"].reset_index(drop=True)
    lab = [f"{r}から移す" if mo == "割合のまま" else "製造の割合だけ入れる" for mo, r in zip(d.model, d["基準（落とした産業）"])]
    yy = np.arange(len(d))[::-1]
    col = [C1 if mo == "割合のまま" else GR for mo in d.model]
    a.errorbar(d.coef * 100, yy, xerr=1.96 * d.se * 100, fmt="none", ecolor=col, elinewidth=2)
    a.scatter(d.coef * 100, yy, color=col, zorder=3)
    a.axvline(0, color="k", lw=0.8)
    a.set_yticks(yy); a.set_yticklabels(lab)
    a.set_xlabel("製造業の割合が1ポイント高いときの、1人あたり地方税の差（%）")
    a.set_title(ttl)
fig.suptitle("割合のまま回帰すると、「どの産業から移したか」で製造業の係数の符号まで変わる（6分類、95%区間）", fontsize=12)
fig.tight_layout()
save(fig, "f170_reference.png")

# 3. 部分組成での相関の入れ替わり と 割合にするだけで生まれる負の相関
B = pd.read_csv(RES / "B_subcomposition_pref.csv")
import json

S = json.load(open(RES / "summary.json"))
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
a = ax[0]
ok = ~B["符号が変わる"]
a.scatter(B.loc[ok, "全体での相関"], B.loc[ok, "除いた後の相関"], s=10, color=GR, alpha=0.6, label="符号は同じ")
a.scatter(B.loc[~ok, "全体での相関"], B.loc[~ok, "除いた後の相関"], s=22, color=C2, label="符号が入れ替わる")
a.plot([-1, 1], [-1, 1], color="k", lw=0.6)
a.axhline(0, color="k", lw=0.4); a.axvline(0, color="k", lw=0.4)
a.set_xlabel("10産業すべてで割合を計算したときの相関")
a.set_ylabel("1産業を除いて割合を計算し直したときの相関")
b = S["B_pref_G10"]
a.set_title(f"都道府県：{b['ペア数']}組のうち{b['符号が変わる']}組（{b['割合']*100:.0f}%）で符号が逆に", fontsize=11)
a.legend(fontsize=9, loc="upper left")
a = ax[1]
vals = [S["B_pref_G10"]["並べ替え_人数の平均相関"], S["B_pref_G10"]["並べ替え_割合の平均相関"], S["B_pref_G10"]["理論値_-1/(D-1)"],
        S["B_pref_G10"]["実データ_割合の平均相関"]]
lab = ["人数を\nばらばらに\n並べ替え（人数）", "同じものを\n割合に", "理論値\n−1/(10−1)", "実データの\n割合"]
a.bar(range(4), vals, color=[GR, C2, "#bbbbbb", C1])
for i, v in enumerate(vals):
    a.text(i, min(v, 0) / 2 if v < -0.02 else v - 0.004, f"{v:.3f}", ha="center", va="center" if v < -0.02 else "top",
           fontsize=10, color="white" if v < -0.02 else "black")
a.axhline(0, color="k", lw=0.8)
a.set_xticks(range(4)); a.set_xticklabels(lab, fontsize=9)
a.set_ylabel("45組の相関の平均")
a.set_title("関係のない人数でも、割合にすると負の相関になる", fontsize=11)
fig.tight_layout()
save(fig, "f170_subcomp.png")

# 4. 構成比を目的変数に：一次と製造
P = pd.read_csv(RES / "C_points_muni.csv")
Cv = pd.read_csv(RES / "C_curves_muni.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
for a, nm in ((ax[0], "一次"), (ax[1], "製造")):
    a.scatter(P.logdens, P[nm] * 100, s=3, alpha=0.25, color=GR)
    a.plot(Cv.logdens, Cv[f"{nm}_割合のまま"] * 100, color=C2, lw=2.2, label="割合のまま（2次式）")
    a.plot(Cv.logdens, Cv[f"{nm}_ilr"] * 100, color=C1, lw=2.2, label="ilr で回帰して戻す")
    a.axhline(0, color="k", lw=0.8)
    a.set_xlabel("可住地1km²あたり人口（対数）")
    a.set_ylabel(f"{nm}の従業者の割合（%）")
    a.legend(fontsize=9)
c = S["C_muni_G6"]
ax[0].set_title(f"一次：割合のままだと{c['0未満の予測_産業別']['一次']}市区町村で予測が0%未満", fontsize=11)
ax[0].set_ylim(-5, 40)
ax[1].set_title("製造：大きい割合では2つの線はほぼ重なる", fontsize=11)
fig.tight_layout()
save(fig, "f170_response.png")

# 5. 頑健性：割合のままの係数の幅 と ilr の係数
R = pd.read_csv(RES / "D_robustness.csv")
R = R[~R["条件"].str.contains("転入超過")].reset_index(drop=True)
lab = R["条件"].str.replace("基本：", "").str.replace("・2021年センサス・地方税", "（基本）")
yy = np.arange(len(R))[::-1]
fig, ax = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
a = ax[0]
for i, r in R.iterrows():
    a.plot([r["割合のまま_最小"] * 100, r["割合のまま_最大"] * 100], [yy[i]] * 2, color=C2, lw=4, alpha=0.8)
a.axvline(0, color="k", lw=0.8)
a.set_yticks(yy); a.set_yticklabels(lab, fontsize=9)
a.set_xlabel("割合のまま：基準を変えたときの係数の幅（%／1ポイント）")
a.set_title("割合のまま：12条件中10条件で 0 をまたぐ", fontsize=11)
a = ax[1]
a.errorbar(R["ilr"] * 100, yy, xerr=1.96 * R["ilr_se"] * 100, fmt="o", color=C1, ecolor=C1)
a.axvline(0, color="k", lw=0.8)
a.set_xlabel("ilr：製造÷ほかの比が10%高いときの差（%）")
a.set_title("ilr：係数は1つに決まり、12条件すべてプラス", fontsize=11)
fig.suptitle("製造業の割合と1人あたり地方税：条件を変えても同じことが起きるか", fontsize=12)
fig.tight_layout()
save(fig, "f170_robust.png")

# 6. 0 の扱い
Z = pd.read_csv(RES / "D_zero_handling.csv")
fig, ax = plt.subplots(figsize=(8.5, 4.4))
pick = {"製造業": C1, "漁業": C2, "鉱業、採石業、砂利採取業": C3, "卸売業、小売業": GR}
for nm, col in pick.items():
    d = Z[Z["産業"] == nm].sort_values("delta")
    base = d["密度の係数"].iloc[-1]
    ax.plot(d.delta, d["密度の係数"] / base, marker="o", color=col,
            label=f"{nm}（0の市区町村 {int(d['0の数'].iloc[0])}）")
ax.set_xscale("log")
ax.axhline(1, color="k", lw=0.6)
ax.set_xlabel("0 人の産業を何人とみなすか（δ、対数目盛）")
ax.set_ylabel("密度の係数（δ=1 を 1 とした比）")
ax.set_title("18産業のまま対数比にすると、0 の置き方で係数が動く\n（製造業は0が3件しかないのに、δ=0.01 では δ=1 の約4分の1）", fontsize=11)
ax.legend(fontsize=9)
save(fig, "f170_zero.png")
print("ok")
