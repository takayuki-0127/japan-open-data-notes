"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2 = "#52514e"
SRC = "出典：総務省「国勢調査」時系列データ 世帯 第1表、令和7年国勢調査 人口等基本集計 第12-1表・第12-2表（原数値）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 全国の分解
NT = pd.read_csv(RES / "national_decomposition.csv")
fig, ax = plt.subplots(figsize=(8, 4.8))
x = np.arange(len(NT))
pe, se = NT["人口の効果"] / 1e6, NT["人数の効果"] / 1e6
ax.bar(x, se, color=C[1], width=0.6, label="1世帯あたり人員が小さくなった効果", edgecolor="#fcfcfb")
ax.bar(x, pe, bottom=np.where(pe >= 0, se, 0), color=C[0], width=0.6, label="人口（一般世帯の人員）の効果", edgecolor="#fcfcfb")
ax.plot(x, NT["世帯数の変化"] / 1e6, color="#0b0b0b", marker="o", ms=4, lw=1.8, label="世帯数の変化（合計）")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(x, [s.replace("→", "→\n") for s in NT["期間"]], fontsize=8)
ax.set_ylabel("5年間の一般世帯数の変化（百万世帯）")
ax.set_title("2020→25年は人口の効果が−155万に広がったが、世帯の小型化が＋302万で上回った", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper right")
ax.set_ylim(-2, 4.2)
fig.subplots_adjust(bottom=0.2, left=0.09, right=0.98, top=0.9)
save(fig, "fig1_national_decomposition.png", "人口の効果＝人員の変化×平均の（世帯数÷人員）、世帯が小さくなった効果＝平均の人員×（世帯数÷人員）の変化")

# fig2 県別の世帯数の変化率（北から南）
Pf = pd.read_csv(RES / "pref_changes.csv").sort_values("pref")
fig, ax = plt.subplots(figsize=(8, 9.2))
y = np.arange(len(Pf))[::-1]
ax.hlines(y, Pf["世帯変化率_2015_2020_%"], Pf["世帯変化率_2020_2025_%"], color="#c3c2b7", lw=1.5)
ax.plot(Pf["世帯変化率_2015_2020_%"], y, "o", color=C[0], ms=6, label="2015→2020年", mec="#fcfcfb", mew=1)
ax.plot(Pf["世帯変化率_2020_2025_%"], y, "o", color=C[1], ms=6, label="2020→2025年", mec="#fcfcfb", mew=1)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(y, [nm if nm == "北海道" else nm[:-1] for nm in Pf["県"]]); ax.tick_params(axis="y", labelsize=8.5)
ax.set_xlabel("一般世帯数の5年間の変化率（%）")
d = M["H2"]["世帯が減った県の数"]
ax.set_title(f"世帯数が減った県は{d['2015_2020']}から{d['2020_2025']}に増えた（北から南の順）", loc="left", fontsize=10.5)
ax.legend(frameon=False, loc="upper right")
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.09, left=0.1, right=0.98, top=0.95)
save(fig, "fig2_pref_household_change.png")

# fig3 人員の変化率と世帯数の変化率
fig, ax = plt.subplots(figsize=(8, 5))
xv, yv = Pf["人員変化率_2020_2025_%"], Pf["世帯変化率_2020_2025_%"]
neg = yv < 0
ax.scatter(xv[~neg], yv[~neg], s=30, color=C[0], label="世帯が増えた県", edgecolor="#fcfcfb")
ax.scatter(xv[neg], yv[neg], s=30, color=C[1], label="世帯が減った県", edgecolor="#fcfcfb")
b = np.polyfit(xv, yv, 1); xs = np.linspace(xv.min() - 0.3, xv.max() + 0.3, 50)
ax.plot(xs, b[0] * xs + b[1], color=INK2, lw=1, ls="--")
x0 = M["H4"]["世帯が増減ゼロになる人員の変化率_%"]
ax.axhline(0, color="#0b0b0b", lw=0.8); ax.axvline(x0, color=INK2, lw=0.8, ls=":")
ax.annotate(f"回帰直線が0になる点：人員 {x0:.1f}%", (x0, 0), xytext=(x0 + 0.4, -2.2), fontsize=8.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax.set_xlabel("一般世帯の人員の変化率（2020→2025年、%）"); ax.set_ylabel("一般世帯数の変化率（%）")
ax.set_title(f"人員の減少が5年で約{-x0:.0f}%を超えるあたりから、世帯数も減る県が多い（r = {M['H4']['相関_r']:.2f}）", loc="left", fontsize=10)
ax.legend(frameon=False, loc="upper left", fontsize=8.5)
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig3_pop_vs_households.png", "47都道府県。破線は回帰直線")

# fig4 問い直し
q = M["問い直し"]
fig, ax = plt.subplots(figsize=(8, 4.4))
labs = ["人員の変化率", "1世帯あたり人員の変化率", "世帯数の変化率"]
keys = ["人員変化率_%", "1世帯あたり人員の変化率_%", "世帯変化率_%"]
xx = np.arange(3)
a = [q["増えた県の平均"][k] for k in keys]; bb = [q["減った県の平均"][k] for k in keys]
ax.bar(xx - 0.19, a, width=0.38, color=C[0], label=f"世帯が増えた{47 - M['H2']['世帯が減った県の数']['2020_2025']}都府県の平均")
ax.bar(xx + 0.19, bb, width=0.38, color=C[1], label=f"世帯が減った{M['H2']['世帯が減った県の数']['2020_2025']}道県の平均")
for i in range(3):
    for dx, v in [(-0.19, a[i]), (0.19, bb[i])]:
        ax.text(xx[i] + dx, v + (0.15 if v >= 0 else -0.15), f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5, color=INK2)
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(xx, labs); ax.set_ylim(-8, 4)
ax.set_ylabel("2020→2025年の変化率（%、県の単純平均）")
ax.set_title("違いは人口の減り方。世帯の小さくなり方はほぼ同じ", loc="left")
ax.legend(frameon=False, loc="lower right", fontsize=8.5)
fig.subplots_adjust(bottom=0.15, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_requestion.png")
print("figures ok")
