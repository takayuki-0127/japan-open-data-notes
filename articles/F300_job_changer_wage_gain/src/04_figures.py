"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC = "出典：厚生労働省「雇用動向調査」「一般職業紹介状況」、総務省「労働力調査」（e-Stat）をもとに作成者が加工"
wc = pd.read_csv(ROOT / "data" / "wage_change_by_age.csv")
ts = pd.read_csv(RES / "timeseries_all.csv")
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))

def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：全体の推移（増加・減少）
a = wc[wc.age == "all"]
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.85, top=0.84, bottom=0.14)
ax.axvspan(1990.5, 2006.5, color="#f0efec", lw=0)
ax.text(1998.7, 41, "2006年まで：割合の分母の\n定義が違う（比べない）", fontsize=8, color=INK2, ha="center")
ax.plot(a.year, a.up10, color=C[0], lw=2, marker="o", ms=3.5)
ax.plot(a.year, a.down10, color=C[1], lw=2, marker="o", ms=3.5)
ax.text(2025.4, a.up10.iloc[-1], f"1割以上増加\n{a.up10.iloc[-1]:.1f}%", color="#0b0b0b", va="center", fontsize=9)
ax.text(2025.4, a.down10.iloc[-1] - 1.5, f"1割以上減少\n{a.down10.iloc[-1]:.1f}%", color="#0b0b0b", va="center", fontsize=9)
ax.set_ylim(0, 45); ax.set_xlim(1990.5, 2025.5); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.set_ylabel("転職入職者に占める割合（%）"); ax.set_xlabel("年")
fig.suptitle("賃金が1割以上増えた転職者は、2023年から3年続けて減った人を上回った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"2007〜09年の平均 {m['H1']['observed_start']:.1f}% → 2023〜25年 {m['H1']['observed_end']:.1f}%。差し引き（増加−減少）は {m['H4']['net_start']:+.1f} → {m['H4']['net_end']:+.1f}ポイント", fontsize=9, color=INK2)
save(fig, "fig1_trend_up_down.png")

# 図2：年齢別
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.84, top=0.84, bottom=0.14)
lab = {"20_29": "20〜29歳", "30_44": "30〜44歳", "45_59": "45〜59歳", "60p": "60歳以上"}
b = wc[wc.year >= 2007]
for k, (ag, nm) in enumerate(lab.items()):
    s = b[b.age == ag]
    ax.plot(s.year, s.up10, color=C[k], lw=2, marker="o", ms=3)
    ax.text(2025.4, s.up10.iloc[-1], f"{nm} {m['H2'][ag]['change']:+.1f}", color="#0b0b0b", va="center", fontsize=9)
ax.set_ylim(0, 45); ax.set_xlim(2006.5, 2025.5); ax.set_xticks(range(2007, 2026, 3)); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.set_ylabel("1割以上増加の割合（%）"); ax.set_xlabel("年")
fig.suptitle("増えた人の割合は、どの年齢でも上がった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, "右端の数字は 2007〜09年 → 2023〜25年の変化（ポイント）。19歳以下は人数が少なく省いた", fontsize=9, color=INK2)
save(fig, "fig2_by_age.png")

# 図3：シフト・シェア分解
h = m["H1"]
items = [("全体の変化\n（重みで組み立て）", h["implied_change"]), ("年齢の中の変化\n（重みは2007〜09年）", h["within_fixed_start"]),
         ("年齢構成の変化", h["composition"]), ("交差の項", h["interaction"])]
fig, ax = plt.subplots(figsize=(7.8, 4.8)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.2)
cols = [GRAY, C[0], C[1], C[1]]
bars = ax.bar([i[0] for i in items], [i[1] for i in items], color=cols, width=0.55)
for bb, (_, v) in zip(bars, items):
    ax.text(bb.get_x() + bb.get_width() / 2, v + (0.3 if v >= 0 else -0.9), f"{v:+.1f}", ha="center", fontsize=10)
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylim(-3, 13); ax.set_ylabel("1割以上増加の割合の変化（ポイント）")
ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("年齢構成の変化は、上昇をむしろ小さく見せていた", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.87, "2007〜09年 → 2023〜25年。転職者が60歳以上に寄った分（−1.1ポイント）を除くと、上昇は +11.0ポイント", fontsize=9, color=INK2)
save(fig, "fig3_shift_share.png")

# 図4：倍率と増加の割合（問い直し）
d = ts[ts.year >= 2007]
fig, ax = plt.subplots(figsize=(7.6, 5.4)); fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.14)
ax.plot(d.jobs_ratio, d.up10, color="#cfcdc8", lw=1, zorder=1)
sc = ax.scatter(d.jobs_ratio, d.up10, c=d.year, cmap="Blues", vmin=2000, vmax=2025, s=60, edgecolor="#52514e", lw=0.6, zorder=2)
for r in d.itertuples():
    if r.year in (2007, 2009, 2013, 2018, 2019, 2020, 2021, 2024, 2025, 2015):
        left = r.year in (2018, 2019)
        ax.annotate(str(r.year), (r.jobs_ratio, r.up10), xytext=(-8 if left else 6, -3), textcoords="offset points", fontsize=8,
                    color="#0b0b0b", ha="right" if left else "left")
ax.set_xlabel("有効求人倍率（年平均、倍）"); ax.set_ylabel("1割以上増加の割合（%）"); ax.grid(color="#e6e5e1", lw=0.6)
cb = fig.colorbar(sc, ax=ax, pad=0.01); cb.set_label("年（色が濃いほど最近）")
fig.suptitle("同じくらいの求人倍率でも、最近の年ほど増えた人が多い", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"2007〜09 → 2023〜25年の上昇 {q['observed_change']:.1f}ポイントのうち、倍率の分は {q['part_jobs_ratio']:.1f}、時間の流れの分は {q['part_trend']:.1f}", fontsize=9, color=INK2)
save(fig, "fig4_jobs_ratio_scatter.png")
print("ok")
