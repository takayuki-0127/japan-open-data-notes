"""04 図：6枚"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); break
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 150, "svg.hashsalt": "f278"})
R = pathlib.Path(__file__).resolve().parents[1]
F = R / "figures"; F.mkdir(exist_ok=True)
res = json.loads((R / "results/main.json").read_text())
A = pd.read_csv(R / "results/A_decomp_records.csv")
C = pd.read_csv(R / "results/C_sampling_error.csv")
D = pd.read_csv(R / "results/D_pref_records_2023.csv")
E = pd.read_csv(R / "results/E_types_national.csv")
ns = {int(k): v for k, v in res["national_series"].items()}
Y = sorted(ns)
C1, C2, C3, C4 = "#2b6cb0", "#c05621", "#718096", "#2f855a"
META = {"Software": None}


def save(fig, name):
    fig.tight_layout(); fig.savefig(F / name, metadata=META); plt.close(fig)


# 図1 空き家の数と空き家率
fig, ax = plt.subplots(figsize=(8.4, 4.6))
ax.bar(Y, [ns[y]["vacant"] / 1e4 for y in Y], width=3.2, color=C1, alpha=.8, label="空き家の数（左の目盛り）")
ax.set_ylabel("空き家の数（万戸）"); ax.set_xticks(Y); ax.set_xticklabels([str(y) for y in Y], rotation=45)
ax2 = ax.twinx(); ax2.plot(Y, [100 * ns[y]["rate"] for y in Y], "-o", color=C2, label="空き家率（右の目盛り）")
ax2.set_ylabel("空き家率（%）"); ax2.set_ylim(0, 16); ax2.spines["top"].set_visible(False)
for y in [2018, 2023]:
    ax.annotate(f"{ns[y]['vacant']/1e4:.0f}万", (y, ns[y]["vacant"] / 1e4), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9, color=C1)
    ax2.annotate(f"{100*ns[y]['rate']:.1f}%", (y, 100 * ns[y]["rate"]), xytext=(0, -16), textcoords="offset points", ha="center", fontsize=9, color=C2)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
ax.set_title("空き家の数も空き家率も、1963年からの13回すべてで「それまでの最多・最高」", fontsize=12)
ax.text(1958, -170, "1958〜1968年は沖縄を含まない値", fontsize=8, color=C3)
save(fig, "f278_fig1_series.png")

# 図2 5年ごとの増加の分解
fig, ax = plt.subplots(figsize=(8.4, 4.6))
lab = [f"{a}→{str(b)[2:]}" for a, b in zip(A.y0, A.y1)]
x = np.arange(len(A))
ax.bar(x, A.stock_part / 1e4, color=C1, label="住宅が増えた分（率は前後の平均）")
ax.bar(x, A.rate_part / 1e4, bottom=A.stock_part / 1e4, color=C2, label="空き家率が上がった分")
for i, s in enumerate(A.stock_share):
    ax.text(i, A.dV[i] / 1e4 + 3, f"{100*s:.0f}%", ha="center", fontsize=8, color=C1)
ax.set_xticks(x); ax.set_xticklabels(lab, rotation=45, fontsize=9); ax.set_ylabel("空き家の増加（万戸）")
ax.set_title("5年ごとの空き家の増加の内訳（数字は住宅が増えた分の割合）", fontsize=12); ax.legend(frameon=False)
save(fig, "f278_fig2_decomposition.png")

# 図3 空き家率の上がり幅と、2018→2023年の誤差の幅
fig, ax = plt.subplots(figsize=(8.4, 4.4))
dr = 100 * (A.r1 - A.r0)
ax.bar(x, dr, color=[C2 if b == 2023 else C3 for b in A.y1])
m = C[(C.item == "vacant") & (C.cv_stock == "main") & (C.rho == 0)].iloc[0]
ax.errorbar([x[-1]], [m.dr_pt], yerr=[1.96 * m.se_dr_pt], color="k", capsize=6, lw=1.5)
ax.text(x[-1], m.dr_pt + 1.96 * m.se_dr_pt + 0.1, f"+{m.dr_pt:.2f}\n(95%の幅 ±{1.96*m.se_dr_pt:.2f})", ha="center", fontsize=8)
for i, v in enumerate(dr):
    if i < len(dr) - 1: ax.text(i, v + 0.05, f"{v:+.2f}", ha="center", fontsize=8, color=C3)
ax.set_xticks(x); ax.set_xticklabels(lab, rotation=45, fontsize=9); ax.set_ylabel("空き家率の上がり幅（ポイント）")
ax.set_title("空き家率の上がり幅は1990年代より小さい。2018→2023年は誤差の幅を超える", fontsize=12)
save(fig, "f278_fig3_rate_change.png")

# 図4 種類別の空き家率
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.plot(E.year, 100 * E.total, "-o", color="k", label="空き家全体")
ax.plot(E.year, 100 * E.rent_sale, "-o", color=C1, label="賃貸用・売却用")
ax.plot(E.year, 100 * E.other, "-o", color=C2, label="賃貸・売却用及び二次的住宅を除く空き家")
ax.plot(E.year, 100 * E.second, "-o", color=C4, label="二次的住宅（別荘など）")
ax.set_ylabel("住宅全体に占める割合（%）"); ax.set_xticks(E.year); ax.set_ylim(0, 15)
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("2008年以降に上がっているのは「賃貸・売却用及び二次的住宅を除く空き家」", fontsize=12)
save(fig, "f278_fig4_types.png")

# 図5 都道府県：2023年に「それまでの最多・最高」になった数
h = res["H4"]
cats = ["空き家の数", "空き家率", "賃貸・売却用及び\n二次的住宅を除く\n空き家の率"]
v1 = [h["count_rec"], h["rate_rec"], h["other_rate_rec"]]
v2 = [h["count_rec5"], h["rate_rec5"], None]
fig, ax = plt.subplots(figsize=(8.0, 4.4))
xx = np.arange(3)
ax.bar(xx - 0.18, v1, width=0.36, color=C1, label="それまでの最多・最高を上回った")
ax.bar(xx[:2] + 0.18, v2[:2], width=0.36, color=C3, label="5%以上上回った")
for i, v in enumerate(v1): ax.text(i - 0.18, v + 0.5, str(v), ha="center")
for i, v in enumerate(v2[:2]): ax.text(i + 0.18, v + 0.5, str(v), ha="center")
ax.axhline(47, color=C3, lw=.8, ls=":"); ax.text(-0.45, 47.6, "全47都道府県", color=C3, fontsize=9)
ax.set_xticks(xx); ax.set_xticklabels(cats); ax.set_ylabel("都道府県の数"); ax.set_ylim(0, 52)
ax.legend(frameon=False, loc="upper right", fontsize=9)
ax.set_title("2023年に記録を更新した都道府県の数（名前は出していない）", fontsize=12)
save(fig, "f278_fig5_pref_records.png")

# 図6 問い直し：率が前回のままでも「過去最多」になったか
fig, ax = plt.subplots(figsize=(8.4, 4.4))
prevmax, cr = [], []
for _, r in A.iterrows():
    prevmax.append(max(ns[y]["vacant"] for y in Y if y <= r.y0))
    # 1973年は沖縄を含まない値どうしで比べる（03 の A と同じ）
    S1 = ns[r.y1]["stock"] if r.y1 != 1973 else res["stock_1973_excl"]
    cr.append(S1 * r.r0)
ratio = 100 * (np.array(cr) / np.array(prevmax) - 1)
ax.bar(x, ratio, color=C1)
for i, v in enumerate(ratio): ax.text(i, v + 0.5, f"{v:.0f}%", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([str(b) for b in A.y1], rotation=45, fontsize=9)
ax.set_ylabel("それまでの最多を何%上回るか")
ax.set_title("空き家率が前回のままでも、空き家の数は毎回「過去最多」（全国、13回すべて）", fontsize=12)
ax.text(6.5, max(ratio) * 0.75, f"都道府県（2023年）：率が2018年のままでも\n過去最多になるのは47のうち{h['const_rate_rec']}", fontsize=9, color=C2)
save(fig, "f278_fig6_reask_constant_rate.png")
print("ok", sorted(p.name for p in F.glob("*.png")))
