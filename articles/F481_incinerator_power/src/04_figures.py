"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：環境省「一般廃棄物処理実態調査結果」（焼却施設、2005〜2024年度）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
Y = pd.read_csv(R / "yearly.csv").set_index("fy")
fac = pd.read_csv(ROOT / "data" / "facilities.csv", low_memory=False)

# ---- 図1：2005年度＝100 の指数 -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
series = [("gen_twh", "総発電量", C[1]), ("kwh_per_t_all", "燃やしたごみ1トンあたりの発電量", C[0]), ("tons_mt", "燃やしたごみの量", C[2])]
for col, lab, c in series:
    v = Y[col] / Y[col].loc[2005] * 100
    ax.plot(Y.index, v, color=c, lw=2.2)
    ax.text(2024.3, v.loc[2024], f"{lab}\n{v.loc[2024]:.0f}", va="center", fontsize=9, color=INK)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(2005, 2030.5); ax.set_ylim(60, 210)
ax.set_xticks(range(2005, 2025, 3))
ax.set_ylabel("2005年度＝100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"燃やすごみは{abs(main['tons_change_pct']):.0f}%減ったが、発電は{main['gen_growth_pct']:.0f}%増えた", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：総発電量は{main['gen_twh_2005']:.2f}TWh（2005年度）→{main['gen_twh_2024']:.2f}TWh（2024年度）。単位の書き間違いとみられる{main['n_rows_fixed_kwh']}行は1000で割った。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_index.png")

# ---- 図2：増加の分解 -----------------------------------------------------------------------------
d = main["decomp_pct"]
labs = ["燃やしたごみの量", "発電する施設で燃やす割合", "発電する施設の1トンあたりの発電量"]
vals = [d["tons"], d["share_at_gen"], d["kwh_per_t_gen"]]
fig, ax = plt.subplots(figsize=(8.8, 4.4))
cols = [C[2], C[0], C[1]]
ax.barh(range(3), vals, color=cols, height=0.55)
for i, v in enumerate(vals):
    ax.text(v + (2 if v >= 0 else -2), i, f"{v:+.0f}%".replace("-", "−"), va="center", ha="left" if v >= 0 else "right", fontsize=10, color=INK)
ax.set_yticks(range(3)); ax.set_yticklabels(labs); ax.invert_yaxis()
ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-90, 120)
ax.set_xlabel("総発電量の増加（2005→2024年度）に対する寄与（%、合計100）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("ごみの減少を、発電施設の割合と1トンあたりの発電量の伸びが上回った", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, f"注：発電量＝ごみの量×発電施設で燃やす割合（{main['share_tons_at_gen_2005']:.0f}%→{main['share_tons_at_gen_2024']:.0f}%）×発電施設の1トンあたりの発電量（{main['kwh_per_t_gen_2005']:.0f}→{main['kwh_per_t_gen_2024']:.0f}kWh）。対数で分けた。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.31, right=0.97, top=0.89, bottom=0.2)
save(fig, "fig2_decomposition.png")

# ---- 図3：使い始めた年代と1トンあたりの発電量（2024年度） ------------------------------------------
fx = fac[fac.fy == 2024].copy()
for c in ["tons", "gen_mwh", "gen_kw", "start_fy"]:
    fx[c] = pd.to_numeric(fx[c], errors="coerce").fillna(0)
cfx = fx.gen_mwh / (fx.gen_kw / 1000 * 8784)
fx.loc[(fx.gen_kw > 0) & (cfx > 10), "gen_mwh"] /= 1000
fx = fx[(fx.gen_mwh > 0) & (fx.tons > 0)]
fx["kwh_t"] = fx.gen_mwh * 1000 / fx.tons
eras = [("〜1999年度", fx.start_fy <= 1999), ("2000〜2009年度", (fx.start_fy >= 2000) & (fx.start_fy <= 2009)), ("2010年度〜", fx.start_fy >= 2010)]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for i, (lab, m) in enumerate(eras):
    v = fx.loc[m, "kwh_t"].clip(upper=1100).values
    jit = (np.arange(len(v)) % 15 - 7) / 40.0
    ax.scatter(np.full(len(v), i) + jit, v, s=12, color=C[0], alpha=0.45, edgecolors="none")
    med = main["era_median_kwh_t"][lab]
    ax.plot([i - 0.3, i + 0.3], [med, med], color=C[1], lw=3)
    ax.text(i + 0.33, med, f"中央値 {med:.0f}\n（{main['era_count'][lab]}施設）", va="center", fontsize=9, color=INK)
ax.set_xticks(range(3)); ax.set_xticklabels([e[0] + "に使い始めた" for e in eras])
ax.set_xlim(-0.5, 2.9); ax.set_ylim(0, 1150)
ax.set_ylabel("燃やしたごみ1トンあたりの発電量（kWh、2024年度）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"新しい施設ほど1トンあたり多く発電する（2010年度〜は1999年度以前の{main['hypotheses']['H2_new_vs_old_median_ge_1_5']['value']:.2f}倍）", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：2024年度に発電量があり、ごみを燃やした施設。点は施設（1,100kWh を超える点は上端に寄せた）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_kwh_per_t_by_era.png")

# ---- 図4：施設の入れ替えと続いている施設 -------------------------------------------------------
parts = list(req["links"][0]["parts_gwh"].keys())
short = ["続く施設（両年発電）の増減", "続く施設で発電を始めた", "続く施設で発電をやめた", "新しいコードの施設", "なくなったコードの施設"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
yb = np.arange(len(parts)); h = 0.36
for k, lk in enumerate(req["links"]):
    vals = [lk["parts_gwh"][p] / 1000 for p in parts]
    pos = yb + (k - 0.5) * (h + 0.03)
    ax.barh(pos, vals, height=h, color=C[k], label=f"{lk['period'].replace('-', '→')}年度（計 {lk['total_change_gwh']/1000:+.2f}TWh）")
    for p_, v in zip(pos, vals):
        ax.text(v + (0.03 if v >= 0 else -0.03), p_, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.6, color=INK)
ax.set_yticks(yb); ax.set_yticklabels(short); ax.invert_yaxis()
ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-1.2, 1.6)
ax.set_xlabel("総発電量の増減（TWh）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2020年度以降、続いている施設の発電は減り、新設・建て替えが増加を支えた", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：施設コードでつないだ。コードの書き方が2020年度に変わったため期間を二つに分けた。建て替えでコードが変わると「新しいコード」に入る。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.24, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_entry_exit.png")
print("ok")
