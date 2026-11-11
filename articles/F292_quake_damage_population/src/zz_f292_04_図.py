"""04 図：6枚。どれも全体の集計（都府県別の値は出さない）。"""
import sys, json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["svg.hashsalt"] = "f292"
plt.rcParams["figure.dpi"] = 110
R, F = out / "results", out / "figures"
F.mkdir(exist_ok=True)
M = json.load(open(R / "main.json"))
A = pd.read_csv(R / "A_main_trajectory.csv")
B = pd.read_csv(R / "B_R1_all_tables_2050.csv")
C = pd.read_csv(R / "C_robustness.csv")
D = pd.read_csv(R / "D_reask_evac_vs_demog.csv")
BLUE, ORANGE, GRAY, GREEN = "#2171b5", "#e6550d", "#7f7f7f", "#31a354"
NOTE = "出典：内閣府 南海トラフ巨大地震 被害想定（2025年）都府県別死者数、社人研 地域別将来推計人口（2023年推計）から計算"


def save(fig, name):
    fig.text(0.01, -0.05, NOTE, fontsize=7.5, color=GRAY)
    fig.savefig(F / name, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)


# 図1 主表の推移
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.plot(A.year, A.base / 1e4, color=GRAY, ls=":", label="想定のまま（原因の足し上げ 296,840人）")
ax.plot(A.year, A.size_only / 1e4, "o-", color=BLUE, ms=4, label="人口の規模だけ変える")
ax.plot(A.year, A.both / 1e4, "o-", color=ORANGE, ms=4, label="規模＋年齢構成（津波の補正係数）")
for y, col in [("size_only", BLUE), ("both", ORANGE)]:
    v = A[A.year == 2050][y].iloc[0]
    ax.annotate(f"{v / 1e4:.1f}万人（{100 * (v / A.base.iloc[0] - 1):+.0f}%）", (2050, v / 1e4), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9, color=col)
ax.set_xlim(2018, 2058); ax.set_ylim(15, 33)
ax.set_ylabel("死者数（万人）")
ax.set_title("想定の死者数を、人口だけ2050年に置き換えると（陸側・津波①・冬深夜・風速8m/s・早期避難率低）", fontsize=10.5)
ax.legend(fontsize=8.5, loc="lower left"); ax.grid(alpha=0.3)
save(fig, "fig1_trajectory.png")

# 図2 2050年の変化を原因別に分解
bc = M["main_2050_by_cause"]
labs = ["建物倒壊", "津波", "火災・急傾斜地・ブロック塀等"]
size = [bc["建物倒壊"]["eff_size"], bc["津波"]["eff_size"], sum(bc[c]["eff_size"] for c in ["火災", "急傾斜地", "ブロック塀等"])]
age = [0, bc["津波"]["eff_age"], 0]
fig, ax = plt.subplots(figsize=(8, 4.2))
y = np.arange(3)
ax.barh(y + 0.18, np.array(size) / 1e4, 0.34, color=BLUE, label="人口の規模（減る）")
ax.barh(y - 0.18, np.array(age) / 1e4, 0.34, color=ORANGE, label="年齢構成（増える）")
for i in range(3):
    ax.text(size[i] / 1e4 - 0.15, i + 0.18, f"{size[i] / 1e4:.1f}万", ha="right", va="center", fontsize=9)
    if age[i]:
        ax.text(age[i] / 1e4 + 0.15, i - 0.18, f"+{age[i] / 1e4:.1f}万", ha="left", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(labs); ax.invert_yaxis()
ax.axvline(0, color="k", lw=0.8); ax.set_xlim(-7.5, 6)
ax.set_xlabel("2050年の死者数の変化（万人）")
ax.set_title("動くのは津波：規模で減る分の約8割を、年齢構成が打ち消す（主表・2050年）", fontsize=10.5)
ax.legend(fontsize=8.5, loc="lower right"); ax.grid(axis="x", alpha=0.3)
save(fig, "fig2_decomposition.png")

# 図3 96表すべて：津波の割合と 2050年の変化
fig, ax = plt.subplots(figsize=(8, 4.8))
for ev, col, mk in [("低", ORANGE, "o"), ("高＋呼びかけ", BLUE, "s")]:
    s = B[B.避難 == ev]
    ax.scatter(s.tsunami_share * 100, s.net_pct, s=22, color=col, marker=mk, alpha=0.75, label=f"早期避難率{ev}（{len(s)}表）")
m = B[B.table == M["main_table"]].iloc[0]
ax.scatter(m.tsunami_share * 100, m.net_pct, s=120, facecolors="none", edgecolors="k", lw=1.2)
ax.annotate("主表", (m.tsunami_share * 100, m.net_pct), xytext=(-30, 10), textcoords="offset points", fontsize=9)
ax.axhline(-15, color=GRAY, ls=":", lw=0.9)
ax.set_xlabel("その表の死者のうち津波の割合（%）"); ax.set_ylabel("2050年の人口での変化（%）")
ax.set_title(f"96表すべて：津波の割合が大きい表ほど減りが小さい（相関 {M['R1']['corr_tsunami_share_net']:.2f}）", fontsize=10.5)
ax.legend(fontsize=8.5); ax.grid(alpha=0.3)
save(fig, "fig3_all_tables.png")

# 図4 頑健性
fig, ax = plt.subplots(figsize=(8, 4.4))
y = np.arange(len(C))
ax.barh(y, C.net_pct, color=ORANGE, height=0.55, label="規模＋年齢")
ax.scatter(C.size_pct, y, color=BLUE, zorder=3, label="規模だけ")
for i, v in enumerate(C.net_pct):
    ax.text(v - 0.4, i, f"{v:.1f}%", ha="right", va="center", fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels(C.case, fontsize=8.5); ax.invert_yaxis()
ax.axvline(-15, color=GRAY, ls=":", lw=0.9); ax.set_xlim(-30, 0)
ax.set_xlabel("想定からの変化（%）")
ax.set_title("年齢の重みや基準年を変えると、純減は −8%〜−18% の間で動く", fontsize=10.5)
ax.legend(fontsize=8.5, loc="lower left"); ax.grid(axis="x", alpha=0.3)
save(fig, "fig4_robustness.png")

# 図5 2012年想定→2025年想定の差と、基準人口の変化
h = M["H4"]
fig, ax = plt.subplots(figsize=(8, 3.6))
vals = [h["observed_change"], h["demographic_change_size"], h["demographic_change_size_age"]]
labs = ["公表値の差\n（約32.3万→約29.8万）", "人口の規模だけ\n（2010→2020年）", "規模＋年齢\n（2012年想定も同じ年齢補正：計画の比較）"]
ax.barh(range(3), np.array(vals) / 1e4, color=[GRAY, BLUE, ORANGE], height=0.55)
for i, v in enumerate(vals):
    ax.text(v / 1e4 - 0.05, i, f"{v / 1e4:.1f}万人", ha="right", va="center", fontsize=9)
ax.set_yticks(range(3)); ax.set_yticklabels(labs, fontsize=8.5); ax.invert_yaxis()
ax.set_xlim(-3.2, 0.3); ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("死者数の差（万人）")
ax.set_title("2012年→2025年の想定の差のうち、基準人口の変化で説明できる分", fontsize=10.5)
ax.grid(axis="x", alpha=0.3)
save(fig, "fig5_2012_vs_2025.png")

# 図6 問い直し：避難の想定の差と、人口の変化（同じ目盛り）
fig, ax = plt.subplots(figsize=(6.4, 6.0))
ax.scatter(D.demog_pct, D.evac_pct, s=24, color=GREEN, alpha=0.8, zorder=3)
lim = -85
ax.plot([0, lim], [0, lim], color=GRAY, ls=":", lw=0.9)
ax.text(-40, -37, "同じ大きさ", fontsize=8.5, color=GRAY, rotation=45, ha="center")
ax.set_xlim(lim, 0); ax.set_ylim(lim, 0); ax.set_aspect("equal")
ax.set_xlabel("人口を2050年にしたときの変化（%）（早期避難率低の表）")
ax.set_ylabel("避難の想定を「低」→「高＋呼びかけ」にしたときの変化（%）")
ax.set_title(f"問い直し（事後）：同じ条件の{len(D)}組すべてで\n避難の想定の差のほうが大きい", fontsize=10.5)
ax.grid(alpha=0.3)
fig.text(0.01, -0.06, NOTE, fontsize=7, color=GRAY)
fig.savefig(F / "fig6_reask_evacuation.png", bbox_inches="tight", metadata={"Software": None})
plt.close(fig)
print("ok")
