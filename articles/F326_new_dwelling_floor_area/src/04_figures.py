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
SRC = "出典：国土交通省「建築着工統計調査」時系列表 利用関係別－新設住宅の戸数、床面積の合計（年計）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
W = pd.read_csv(RES / "m2_per_unit_by_type.csv").set_index("year")
LAST = M["全体"]["最新年"]; PEAK = M["全体"]["山の年"]

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 推移
fig, ax = plt.subplots(figsize=(8, 4.8))
for t, c, lw in [("総計", "#0b0b0b", 2.4), ("持家", C[0], 1.6), ("分譲住宅", C[2], 1.6), ("貸家", C[1], 1.6)]:
    ax.plot(W.index, W[t], color=c, lw=lw, label="全体（総計）" if t == "総計" else t)
ax.annotate(f"{PEAK}年 {M['全体']['山の値_m2']:.1f}㎡", (PEAK, M["全体"]["山の値_m2"]), xytext=(PEAK - 22, 103), fontsize=8.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax.annotate(f"{LAST}年 {M['全体']['最新の値_m2']:.1f}㎡", (LAST, M["全体"]["最新の値_m2"]), xytext=(LAST - 12, 60), fontsize=8.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax.set_ylabel("新設住宅1戸あたり床面積（㎡）"); ax.set_xlabel("年"); ax.set_ylim(0, 150)
ax.set_title(f"新設住宅の1戸あたり床面積は{PEAK}年が山で、{LAST}年は{-M['全体']['山からの変化_%']:.0f}%小さい", loc="left")
ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="upper left")
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig1_trend.png", "1955年以前は戸数・床面積の数え方が違うため1956年から")

# fig2 分解
h = M["H2"]
labs = ["全体の変化", "構成（貸家などの割合）", "種類の中：持家", "種類の中：分譲住宅", "種類の中：貸家", "種類の中：給与住宅"]
vals = [h["全体の変化_m2"], h["構成の寄与_m2"], h["種類ごとの寄与_m2"]["持家"], h["種類ごとの寄与_m2"]["分譲住宅"],
        h["種類ごとの寄与_m2"]["貸家"], h["種類ごとの寄与_m2"]["給与住宅"]]
cols = [INK2, C[3], C[0], C[2], C[1], C[4]]
fig, ax = plt.subplots(figsize=(8, 4.6))
y = np.arange(len(labs))[::-1]
ax.barh(y, vals, color=cols, height=0.6)
for i, v in enumerate(vals):
    ax.text(v - 0.3, y[i], f"{v:+.1f}㎡", va="center", ha="right", fontsize=8.5, color=INK2)
ax.axvline(0, color="#0b0b0b", lw=0.8); ax.set_xlim(-25, 2)
ax.set_yticks(y, labs)
ax.set_xlabel(f"1戸あたり床面積の変化（{PEAK}→{LAST}年、㎡）")
ax.set_title(f"減少の{h['構成の割合_%']:.0f}%は構成の変化、残りは種類の中で小さくなった分（最大は持家）", loc="left", fontsize=10)
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.17, left=0.24, right=0.98, top=0.9)
save(fig, "fig2_shift_share.png", "構成と種類の中の分け方は、両方の年の平均を使う対称な方法。4区分（持家・貸家・給与住宅・分譲住宅）")

# fig3 1985年以降の持家・分譲の内訳
q = W.loc[1985:]
fig, ax = plt.subplots(figsize=(8, 4.6))
for t, c in [("持家", C[0]), ("分譲一戸建", C[2]), ("分譲マンション", C[4]), ("貸家", C[1])]:
    ax.plot(q.index, q[t], color=c, lw=2, label=t)
ax.set_ylim(0, 150); ax.set_ylabel("1戸あたり床面積（㎡）"); ax.set_xlabel("年")
ax.set_title(f"持家は{M['H3']['持家の山の年']}年から{-M['H3']['変化_%']:.0f}%、分譲マンションは{M['H4']['マンションの山の年_2000年以降']}年から{-M['H4']['変化_%']:.0f}%小さくなった", loc="left", fontsize=10)
ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="upper left")
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig3_types_since1985.png", "分譲住宅の内訳（マンション・一戸建）は表にある年から")

# fig4 問い直し：床面積の合計・戸数・1戸あたり（山の年＝100）
T = pd.read_csv(ROOT / "data" / "starts_by_type.csv"); T = T[(T.type == "総計") & (T.year >= 1990)].set_index("year")
base = T.loc[PEAK]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(T.index, T.floor_m2 / base.floor_m2 * 100, color="#0b0b0b", lw=2.2, label="床面積の合計")
ax.plot(T.index, T.units / base.units * 100, color=C[0], lw=1.8, label="戸数")
ax.plot(T.index, (T.floor_m2 / T.units) / (base.floor_m2 / base.units) * 100, color=C[1], lw=1.8, label="1戸あたり床面積")
ax.axhline(100, color=INK2, lw=0.6, ls=":")
rq = M["問い直し"][f"{PEAK}→{LAST}"]
ax.set_ylabel(f"{PEAK}年＝100"); ax.set_xlabel("年"); ax.set_ylim(0, 150)
ax.set_title(f"床面積の合計は{-rq['床面積の合計_変化_%']:.0f}%減。減り方の{rq['戸数の減少の割合_%（対数）']:.0f}%は戸数、{rq['1戸あたりの縮小の割合_%（対数）']:.0f}%は1戸あたりの縮小", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig4_total_floor_area.png", "割合は対数で分けた（床面積の合計＝戸数×1戸あたり床面積）")
print("figures ok")
