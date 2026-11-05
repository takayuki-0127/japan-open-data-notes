"""図を6枚つくる（figures/）。"""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import RAW, RES, FIG, DATA
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
FIG.mkdir(exist_ok=True)
C1, C2, C3, C4 = "#3B6EA8", "#D9822B", "#7A7A7A", "#4E9A62"
res = json.load(open(RES / "main.json", encoding="utf-8"))
ST = ["婚姻", "第1子", "第2子", "第3子以上"]; COL = dict(zip(ST, [C3, C1, C2, C4]))

# 1 出生順位別の合計特殊出生率（全国、1990〜2023年）と主な制度の年
T = pd.read_csv(RAW / "f58_order_tfr_mab.csv").set_index("year").loc[1990:]
T["tfr3p"] = T.tfr3 + T.tfr4 + T.tfr5p
fig, ax = plt.subplots(figsize=(9, 4.8))
for k, lab, c in [("tfr1", "第1子", C1), ("tfr2", "第2子", C2), ("tfr3p", "第3子以上", C4)]:
    ax.plot(T.index, T[k], "-", color=c, lw=2.2, label=lab)
for y, t in [(2010, "子ども手当"), (2015, "子ども・子育て\n支援新制度"), (2019.75, "幼保無償化"), (2023.3, "出産育児\n一時金の増額")]:
    ax.axvline(y, color="#BBBBBB", lw=1, ls="--"); ax.text(y + 0.2, 0.84, t, fontsize=8, color="#555555", va="top")
ax.set_ylim(0, 0.9); ax.set_ylabel("合計特殊出生率（出生順位別）")
ax.set_title("2015年からの下がり方は第1子がいちばん大きく、第3子以上は小さい（全国）")
ax.legend(frameon=False, ncol=3, loc="lower left"); fig.tight_layout(); fig.savefig(FIG / "f204_01_order_tfr.png", dpi=150); plt.close()

# 2 段階ごとの数（全国、2012年＝100）
N = pd.read_csv(RES / "A_national_counts.csv").set_index("year")
fig, ax = plt.subplots(figsize=(9, 4.8))
for k, lab, c in [("marriages", "婚姻件数", C3), ("o1", "第1子", C1), ("o2", "第2子", C2), ("o3p", "第3子以上", C4)]:
    s = N[k].dropna(); ax.plot(s.index, s / s.loc[2012] * 100, "o-", ms=4, color=c, lw=2, label=lab)
ax.axvline(2019.75, color="#BBBBBB", lw=1, ls="--"); ax.text(2019.85, 98, "幼保無償化", fontsize=8, color="#555")
ax.set_ylabel("2012年＝100"); ax.set_title("婚姻・第1子・第2子・第3子以上は、ほぼ同じ速さで減った（全国）")
ax.text(0, -0.16, "2017年は都道府県別の表が取れず欠けている。2018年以降の出生は月報（概数）、婚姻は2023年まで", transform=ax.transAxes, fontsize=8)
ax.legend(frameon=False, ncol=4, loc="lower left"); fig.tight_layout(); fig.savefig(FIG / "f204_02_stages_index.png", dpi=150); plt.close()

# 3 保育の受け皿と段階別の出生（推定の方法を変えた7通り）
B = pd.read_csv(RES / "B_twfe.csv")
specs = list(dict.fromkeys(B.spec))
fig, ax = plt.subplots(figsize=(9.5, 5.4))
for i, st in enumerate(ST):
    g = B[B.stage == st].set_index("spec").loc[specs]
    ys = i + np.linspace(-0.3, 0.3, len(specs))
    ax.errorbar(g.b, ys, xerr=[g.b - g.lo, g.hi - g.b], fmt="o", color=COL[st], ms=4, lw=1.2, capsize=2)
    ax.plot(g.b.iloc[0], ys[0], "D", color="k", ms=6)
ax.axvline(0, color="k", lw=0.8); ax.set_yticks(range(4), ST); ax.invert_yaxis()
ax.set_xlabel("保育所等の定員が0〜5歳100人あたり +10人のときの差（％、95%区間）")
ax.set_title("保育の受け皿と段階別の出生：方法を変えると向きや有無が変わる\n（都道府県×年、2012〜22年）", fontsize=11)
fig.text(0.02, 0.02, "黒い◆が主の推定（二方向固定効果）。各段の点は上から：\n" + "／".join(specs[:4]) + "\n／" + "／".join(specs[4:]), fontsize=8)
fig.tight_layout(); fig.subplots_adjust(bottom=0.25); fig.savefig(FIG / "f204_03_twfe.png", dpi=150); plt.close()

# 4 イベントスタディ：2018年に保育所等に通う子が多かった県ほど、無償化のあとに何が変わったか
Ce = pd.read_csv(RES / "C_event_study.csv")
fig, axs = plt.subplots(1, 4, figsize=(12, 4.2), sharey=True)
for ax, st in zip(axs, ST):
    g = Ce[Ce.stage == st]
    ax.fill_between(g.year, g.lo, g.hi, color=COL[st], alpha=0.2); ax.plot(g.year, g.b, "o-", color=COL[st], ms=3.5)
    pf = res["C_pretrend_extrap"][st]; gp = g[g.year <= 2018]; sl, ic = np.polyfit(gp.year, gp.b, 1)
    xs = np.array([2012, 2025]); ax.plot(xs, ic + sl * xs, ":", color="k", lw=1.2)
    ax.axhline(0, color="k", lw=0.6); ax.axvline(2019.75, color="#BBBBBB", lw=1, ls="--"); ax.set_title(st)
    ta = res["C_trend_adjusted"][st]; ax.text(0.03, 0.04, f"傾きを除いた差 {ta['post']:+.2f}%\n（p={ta['p']:.2f}）", transform=ax.transAxes, fontsize=8)
axs[0].set_ylabel("2018年との差（％、在所の多さ1SDあたり）")
fig.suptitle("無償化のあとに上がって見える第3子以上は、前からの傾き（点線）の延長だった")
fig.tight_layout(); fig.savefig(FIG / "f204_04_event_study.png", dpi=150); plt.close()

# 5 2040年の出生数のシナリオ（9通り）
D = pd.read_csv(RES / "D_scenarios_2040.csv")
mp = list(dict.fromkeys(D.married)); fm = list(dict.fromkeys(D.marital))
fig, ax = plt.subplots(figsize=(9.5, 5))
w = 0.26
for j, f in enumerate(fm):
    g = D[D.marital == f].set_index("married").loc[mp]
    ax.bar(np.arange(3) + (j - 1) * w, g.births2040 / 1e4, w, color=[C2, C3, C1][j], label=f)
    for i, v in enumerate(g.births2040 / 1e4): ax.text(i + (j - 1) * w, v + 0.8, f"{v:.0f}", ha="center", fontsize=8)
ax.axhline(res["D"]["b25_actual"] / 1e4, color="k", ls="--", lw=1); ax.text(-0.45, res["D"]["b25_actual"] / 1e4 + 1, "2025年（概数）67万人", ha="left", fontsize=8)
ax.set_xticks(range(3), [m.replace("有配偶の割合が", "有配偶の割合が\n").replace("2040年までに", "2040年までに\n") for m in mp], fontsize=9)
ax.set_ylabel("2040年の出生数（万人）"); ax.set_ylim(0, 90)
ax.set_title("2040年の出生数は、前提しだいで43万〜76万人（予測ではなく、前提を振った幅）")
ax.legend(frameon=False, fontsize=9, title="夫婦の出生率（2025年が基準）", title_fontsize=9, loc="upper left", bbox_to_anchor=(0, 1.0)); ax.set_ylim(0, 100); fig.tight_layout(); fig.savefig(FIG / "f204_05_scenarios.png", dpi=150); plt.close()

# 6 2025年の出生数を2040年も保つのに、夫婦の出生率は何倍必要か
need = res["D"]["need_mult_to_keep_2025"]
fig, ax = plt.subplots(figsize=(9.5, 3.8))
ks = list(need.keys()); vs = [need[k] for k in ks]
ax.barh(range(3), vs, color=[C2, C3, C1]); ax.axvline(1, color="k", lw=0.8)
for i, v in enumerate(vs): ax.text(v + 0.01, i, f"{v:.2f}倍", va="center", fontsize=10)
ax.set_yticks(range(3), ks, fontsize=9); ax.invert_yaxis(); ax.set_xlim(0.8, 1.5)
ax.set_xlabel("2025年の夫婦の出生率に対する倍率")
ax.set_title("2040年も2025年と同じ数の出生になるには、夫婦の出生率が何倍になればよいか", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f204_06_needed.png", dpi=150); plt.close()
print("ok")
