"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。地域は北から南（市町村コード順）か人口の規模別に並べる。"""
import sys; sys.dont_write_bytecode = True
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
GREY = "#b9b7b0"; INK = "#0b0b0b"; INK2 = "#52514e"
SRC = "出典：総務省「国勢調査」（2015・2020・2025年 都道府県・市区町村別の主な結果）、\n　　　国土交通省「離島振興対策実施地域一覧」（令和8年4月1日現在）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

import importlib.util
spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_analysis.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    m = A.prep()

# fig1 散布図
fig, ax = plt.subplots(figsize=(8, 5))
ml = m[m.island == 0]; il = m[m.island == 1]
ax.scatter(ml.pop2015r, ml.chg15_25, s=9, color=GREY, alpha=0.6, lw=0, label=f"本土の市町村（{len(ml):,}）")
ax.scatter(il.pop2015r, il.chg15_25, s=40, color=C[0], edgecolor="white", lw=0.8, label=f"町全体が離島の市町村（{len(il)}）", zorder=3)
ax.set_xscale("log"); ax.set_ylim(-45, 30); ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks([100, 1000, 10000, 100000, 1000000], ["100", "1千", "1万", "10万", "100万"])
ax.set_xlabel("2015年の人口（人、対数目盛）"); ax.set_ylabel("2015→2025年の人口の増減率（%）")
ax.set_title(f"離島の市町村は、同じ規模の本土の町と同じ帯にある（離島全体で{M['island_total']['chg15_25']:.1f}%）", loc="left", fontsize=11.5)
ax.legend(frameon=False, loc="upper left")
fig.subplots_adjust(bottom=0.22, top=0.9)
save(fig, "fig1_scatter_size_change.png", "注：人口の増減率は、2015→2020年と2020→2025年（それぞれ5年前の人口を今の境界に組み替えたもの）をつないだ。−45%未満・+30%超の本土の市町村は枠の外")

# fig2 北から南：離島と、規模・高齢化をそろえた本土の5つの平均
t = pd.read_csv(RES / "matched_size_aging.csv", dtype={"code": str}).sort_values("code", kind="mergesort").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8, 9.5))
y = np.arange(len(t))
for i, r in t.iterrows():
    ax.plot([r.matched, r.island], [i, i], color="#d6d4cd", lw=1.5, zorder=1)
ax.scatter(t.matched, y, s=36, color=GREY, label="規模と高齢化が近い本土の5市町村の平均", zorder=2)
ax.scatter(t.island, y, s=40, color=C[0], edgecolor="white", lw=0.8, label="離島の市町村", zorder=3)
ax.set_yticks(y, [f"{r.pref[:-1] if r.pref != '北海道' else '北海道'}・{r['name']}" for _, r in t.iterrows()], fontsize=8.5)
ax.invert_yaxis(); ax.set_xlim(-30, 5); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("2015→2025年の人口の増減率（%）")
d = M["H2_size_aging"]
ax.set_title(f"北から南の35市町村。本土との差は島ごとにまちまち（差の中央値 {d['median_diff']:+.1f}ポイント）", loc="left", fontsize=11)
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.05), ncol=2, fontsize=8.5)
fig.subplots_adjust(bottom=0.12, top=0.95, left=0.24)
save(fig, "fig2_islands_north_to_south.png", "注：市町村コードの順（おおむね北から南）。本土の5市町村は、2015年の人口（対数）と65歳以上の割合が近いものを選んだ")

# fig3 規模別
sz = pd.read_csv(RES / "by_size.csv")
labels = ["2千人未満", "2千〜5千人", "5千〜2万人", "2万人以上"]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(labels))
for j, (isl, col, lab) in enumerate([(0, GREY, "本土の市町村"), (1, C[0], "離島の市町村")]):
    g = sz[sz.island == isl].set_index("size").loc[labels]
    ax.bar(x + (j - 0.5) * 0.36, g.median_chg, width=0.34, color=col, label=lab)
    for i, (v, n, s65) in enumerate(zip(g.median_chg, g.n, g.median_share65)):
        ax.text(i + (j - 0.5) * 0.36, v - 1.2, f"{v:.1f}%\n({n})", ha="center", va="top", fontsize=8.5, color=INK)
        ax.text(i + (j - 0.5) * 0.36, 1.0, f"高齢\n{s65:.0f}%", ha="center", va="bottom", fontsize=7.5, color=INK2)
ax.set_xticks(x, labels); ax.set_ylim(-30, 7); ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlabel("2015年の人口の規模"); ax.set_ylabel("2015→2025年の増減率の中央値（%）")
ax.set_title("2千人未満の島は本土より減りが緩く、2万人以上の島は本土より速い", loc="left", fontsize=11.5)
ax.legend(frameon=False, loc="lower right")
fig.subplots_adjust(bottom=0.22, top=0.9)
save(fig, "fig3_by_size.png", "注：（）は市町村の数。「高齢」は2015年の65歳以上の割合の中央値。2万人以上の離島は4市（佐渡市・対馬市・壱岐市・五島市）")

# fig4 問い直し
R = M["requestion_nonmetro"]
rows = [("規模だけ（本土すべて）", M["H3_small"], M["H3_large"]),
        ("規模だけ（都市圏の外）", R["size_small"], R["size_large"]),
        ("規模＋高齢化（都市圏の外）", R["size_aging_small"], R["size_aging_large"])]
fig, ax = plt.subplots(figsize=(8, 4.6))
yy = np.arange(len(rows))
for k, (lab, col, off) in enumerate([("人口5千人未満の島（19）", C[1], -0.15), ("人口5千人以上の島（16）", C[0], 0.15)]):
    for i, r in enumerate(rows):
        s = r[1 + k]
        ax.plot([s["ci_lo"], s["ci_hi"]], [i + off, i + off], color=col, lw=2)
        ax.plot([s["median_diff"]], [i + off], "o", ms=8, color=col, mec="white", mew=1.2, label=lab if i == 0 else None)
        ax.text(s["ci_hi"] + 0.4, i + off, f"{s['median_diff']:+.1f}", va="center", fontsize=8.5, color=INK)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy, [r[0] for r in rows]); ax.invert_yaxis(); ax.set_xlim(-8, 15)
ax.set_xlabel("離島 − 本土（増減率の差の中央値、ポイント。線は95%区間）")
ax.set_title("郊外の町を外し高齢化もそろえると、大きな島と本土の差もなくなる", loc="left", fontsize=11.5)
ax.legend(frameon=False, loc="lower right", fontsize=8.5)
fig.subplots_adjust(bottom=0.24, top=0.9, left=0.27)
save(fig, "fig4_requestion_nonmetro.png", "注：都市圏の外＝2015年国勢調査の大都市圏・都市圏に入らない本土の市町村（926）。区間はブートストラップ（2,000回）")
