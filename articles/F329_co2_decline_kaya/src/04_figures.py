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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK2 = "#52514e"
SRC = "出典：国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ（1990〜2024年度）」をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
D = pd.read_csv(ROOT / "data" / "series.csv").set_index("year")
LAST = int(D.index.max())

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 推移
e = M["エネルギー起源CO2"]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(D.index, D.co2_energy_Mt, color="#0b0b0b", lw=2.4)
ax.annotate(f"{e['山の年度']}年度 {e['山_Mt']:,.0f}", (e["山の年度"], e["山_Mt"]), xytext=(e["山の年度"] - 12, 1270), fontsize=8.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax.annotate(f"{LAST}年度 {e[f'{LAST}_Mt']:,.0f}", (LAST, e[f"{LAST}_Mt"]), xytext=(LAST - 9, 850), fontsize=8.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax.set_ylim(0, 1400); ax.set_ylabel("エネルギー起源 CO2（百万トン）"); ax.set_xlabel("年度")
ax.set_title(f"エネルギー起源 CO2 は{e['山の年度']}年度が山で、{LAST}年度は{-e['山からの変化_%']:.0f}%少ない", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_trend.png")

# fig2 LMDI
K = pd.read_csv(RES / "kaya_lmdi.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
facs = ["人口", "1人あたりGDP", "GDPあたり排出"]; cols = [C[0], C[3], C[2]]
x = np.arange(len(K))
for j, (f, c) in enumerate(zip(facs, cols)):
    ax.bar(x + (j - 1) * 0.22, K[f], width=0.22, color=c, label=f)
    for i in range(len(K)):
        v = K[f].iloc[i]
        ax.text(x[i] + (j - 1) * 0.22, v + (6 if v >= 0 else -6), f"{v:+.0f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8, color=INK2)
ax.scatter(x + 0.42, K["変化_Mt"], marker="D", color="#0b0b0b", s=40, label="変化の合計", zorder=3)
for i in range(len(K)):
    ax.text(x[i] + 0.49, K["変化_Mt"].iloc[i], f"{K['変化_Mt'].iloc[i]:+.0f}", ha="left", va="center", fontsize=8.5, color="#0b0b0b")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(x + 0.1, [f"{p}年度" for p in K["期間"]]); ax.set_ylim(-460, 280); ax.set_xlim(x[0] - 0.5, x[-1] + 0.75)
ax.set_ylabel("エネルギー起源 CO2 の変化への寄与（百万トン）")
ax.set_title("2013年度以降の減少は、GDP あたり排出の低下が経済の伸びを打ち消して余った分", loc="left", fontsize=10)
ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="lower left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig2_kaya.png", "CO2＝人口×1人あたり実質GDP×GDPあたり排出 を対数平均ディビジア指数（LMDI）で分けた")

# fig3 部門
S = pd.read_csv(RES / "sector_series.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8, 4.6))
for k, c in zip(["産業", "業務その他", "家庭", "運輸", "エネルギー転換"], C):
    ax.plot(S.index, S[k], color=c, lw=2, label=k)
ax.axvline(2013, color=INK2, lw=0.6, ls=":")
ax.set_ylabel("電気・熱を使った部門に配った CO2（百万トン）"); ax.set_xlabel("年度"); ax.set_ylim(0, 560)
ds = M["部門_2013→最新_Mt"]
ax.set_title(f"2013→{LAST}年度の減少は産業{ds['産業']:.0f}、業務{ds['業務その他']:.0f}、家庭{ds['家庭']:.0f}、運輸{ds['運輸']:.0f}（百万トン）", loc="left", fontsize=10)
ax.legend(frameon=False, ncol=5, fontsize=8.5, loc="upper right")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig3_sectors.png", "電気・熱の発電時の排出を、それを使った部門に配った値")

# fig4 問い直し：電気の使用に伴う排出とそれ以外
el = D.electricity_alloc_Mt; other = D.co2_energy_Mt - el
q = M["問い直し"]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(D.index, el, color=C[1], lw=2.2, label="電気の使用に伴う排出")
ax.plot(D.index, other, color=C[0], lw=2.2, label="それ以外（燃料を直接燃やすなど）")
ax.axvline(2013, color=INK2, lw=0.6, ls=":")
ax.set_ylim(0, 800); ax.set_ylabel("CO2（百万トン）"); ax.set_xlabel("年度")
ax.set_title(f"2013年度以降の減少{-q['エネルギー起源CO2の変化_Mt']:.0f}百万トンのうち、{q['電気の分の割合_%']:.0f}%は電気の使用に伴う排出", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_electricity.png", "「電気の使用に伴う排出」は燃料別の表で各部門の電力の行を足した値")
print("figures ok")
