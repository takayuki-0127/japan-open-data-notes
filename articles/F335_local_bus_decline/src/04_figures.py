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
SRC = "出典：国土交通省「旅客地域流動調査」（府県相互間旅客輸送人員表・乗合バス）、総務省「国勢調査」をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
MM = M["main"]
A = pd.read_csv(RES / "area_series.csv")
COL = {"三大都市圏": C[0], "地方圏": C[1]}


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# fig1 指数（2000年度＝100）
fig, ax = plt.subplots(figsize=(8, 4.6))
for ar in ["三大都市圏", "地方圏"]:
    g = A[A.area == ar].set_index("year")
    idx = 100 * g.v / g.v.loc[2000]
    ax.plot(idx.index, idx, color=COL[ar], lw=2, marker="o", ms=3.5)
    ax.text(2024.3, idx.loc[2024], f"{ar}\n{idx.loc[2024]:.0f}", color="#0b0b0b", fontsize=8.5, va="center")
    ax.annotate(f"{idx.loc[2019]:.0f}", (2019, idx.loc[2019]), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8, color=INK2)
ax.axhline(100, color=INK2, lw=0.8)
ax.set_ylim(0, 115); ax.set_xlim(1999.5, 2027)
ax.set_xlabel("年度"); ax.set_ylabel("府県の中の乗合バスの輸送人員（2000年度＝100）")
ax.set_title("地方圏の乗合バスは、感染症の前（2019年度）までに3割減っていた", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_index.png", "三大都市圏＝埼玉・千葉・東京・神奈川・岐阜・愛知・三重・京都・大阪・兵庫・奈良。地方圏＝それ以外の36道県。府県の中で乗り降りした分")

# fig2 人口と1人あたりに分ける（2000→2019年度）
D = M["decomp"]
lab = ["人口", "1人あたりの利用", "輸送人員（合計）"]
fig, ax = plt.subplots(figsize=(8, 4.2))
y = np.arange(3)[::-1]
for k, ar in enumerate(["三大都市圏", "地方圏"]):
    v = [D[ar]["pop_chg"], D[ar]["percap_chg"], D[ar]["chg"]]
    yy = y + (0.18 if k == 0 else -0.18)
    ax.barh(yy, v, height=0.34, color=COL[ar], label=ar)
    for yi, vi in zip(yy, v):
        ax.text(vi + (0.6 if vi >= 0 else -0.6), yi, f"{vi:+.1f}%", va="center", ha="left" if vi >= 0 else "right", fontsize=8.5, color="#0b0b0b")
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(y, lab); ax.grid(axis="y", visible=False); ax.set_xlim(-38, 12)
ax.set_xlabel("2000→2019年度の変化（%）")
ax.set_title(f"地方圏の減少は、人口の減少（{D['地方圏']['pop_chg']:.0f}%）より1人あたりの利用の減少（{D['地方圏']['percap_chg']:.0f}%）が大きい", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.subplots_adjust(bottom=0.2, left=0.2, right=0.98, top=0.9)
save(fig, "fig2_decompose.png", "人口は国勢調査の一般世帯人員（間の年は直線でつないだ）。合計の変化率＝（1＋人口の変化率）×（1＋1人あたりの変化率）−1")

# fig3 府県ごと
P = pd.read_csv(RES / "pref_change.csv")
fig, ax = plt.subplots(figsize=(8, 5))
for ar in ["三大都市圏", "地方圏"]:
    g = P[P.area == ar]
    ax.scatter(g.pop_chg_00_19, g.chg_00_19, s=42, color=COL[ar], edgecolor="white", linewidth=1.2, label=ar, zorder=3)
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
for _, r in P[P.pref.isin(["東京", "大阪", "愛知", "北海道", "沖縄", "福岡", "宮城", "埼玉", "千葉", "神奈川"])].iterrows():
    ax.annotate(r.pref, (r.pop_chg_00_19, r.chg_00_19), xytext=(4, 3), textcoords="offset points", fontsize=8, color=INK2)
ax.set_xlabel("人口の変化（%、2000→2019年度）")
ax.set_ylabel("府県の中の乗合バスの輸送人員の変化（%）")
ax.set_title(f"地方圏の36道県すべてで減った（中央値 {M['local_chg_median']:.0f}%）", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.subplots_adjust(bottom=0.17, left=0.11, right=0.98, top=0.92)
save(fig, "fig3_prefectures.png", "1点が1都道府県")

# fig4 1人あたりの年間の乗車回数
fig, ax = plt.subplots(figsize=(8, 4.6))
for ar in ["三大都市圏", "地方圏"]:
    g = A[A.area == ar].set_index("year")
    pc = 1000 * g.v / g["pop"]
    ax.plot(pc.index, pc, color=COL[ar], lw=2, marker="o", ms=3.5)
    ax.text(2024.3, pc.loc[2024], f"{ar}\n{pc.loc[2024]:.1f}回", fontsize=8.5, va="center")
    ax.annotate(f"{pc.loc[2000]:.1f}回", (2000, pc.loc[2000]), xytext=(14, 7), textcoords="offset points", ha="center", fontsize=8, color=INK2)
ax.set_ylim(0, 60); ax.set_xlim(1999.5, 2027)
ax.set_xlabel("年度"); ax.set_ylabel("1人あたりの年間の乗車回数（回）")
ax.set_title("1人が1年に乗る回数は、地方圏では三大都市圏の半分ほど", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_per_capita.png", "府県の中の乗合バスの輸送人員÷一般世帯人員")
