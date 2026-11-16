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
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：環境省「自然公園等利用者数調」をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8")); req = json.load(open(R / "requestion.json", encoding="utf-8"))
s = pd.read_csv(R / "series.csv", index_col="year")
fx = pd.read_csv(R / "fixed_parks_2019_2024.csv", index_col="group")
fg = pd.read_csv(R / "requestion_foreign.csv", index_col="year")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：国立・国定・都道府県立の利用者数
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for col, c, nm in [("np_10k", C[0], "国立公園"), ("qnp_10k", C[1], "国定公園"), ("pref_10k", C[2], "都道府県立自然公園")]:
    y = s[col] / 1e4
    ax.plot(y.index, y, color=c, lw=2.3, label=nm)
ax.annotate(f"{main['np_peak_year']}年 {main['np_peak'] / 1e4:.2f}億人", (main["np_peak_year"], main["np_peak"] / 1e4), xytext=(1965, 4.3), fontsize=9, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(2024.5, main["np_2024"] / 1e4, f"{main['np_2024'] / 1e4:.2f}億人", fontsize=9, color=C[0], va="center")
ax.set_xlim(1950, 2030); ax.set_ylim(0, 4.6); ax.set_ylabel("年間利用者数（億人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title(f"国立公園の利用者は1991年がいちばん多く、2024年はそこから{main['np_pct_peak_2024']:.1f}%", loc="left", fontsize=11.5)
foot(fig, "注：公園の数は国立公園で1991年の28から2024年の35に増えている。")
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, "fig1_totals.png")

# 図2：全体とそろえた公園（1991年=100）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
y1 = s.np_10k.loc[1971:] / s.np_10k.loc[1991] * 100; y2 = s.fixed_10k.loc[1971:] / s.fixed_10k.loc[1991] * 100
ax.plot(y1.index, y1, color=C[0], lw=2.3, label="国立公園の合計（公園が増えた分を含む）")
ax.plot(y2.index, y2, color=C[1], lw=2.0, ls="--", label=f"1991年からある{main['n_fixed']}公園にそろえた合計")
ax.text(2024.5, y1.loc[2024], f"{y1.loc[2024]:.1f}", fontsize=9, color=C[0], va="bottom"); ax.text(2024.5, y2.loc[2024], f"{y2.loc[2024]:.1f}", fontsize=9, color=C[1], va="top")
ax.axhline(100, color=INK2, lw=0.7)
ax.set_xlim(1970, 2028); ax.set_ylim(40, 110); ax.set_ylabel("1991年 = 100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title(f"公園をそろえても、1991→2024年に{main['fixed_pct_1991_2024']:.1f}%", loc="left", fontsize=11.5)
foot(fig, "注：名前の変更や分割（霧島屋久→霧島錦江湾・屋久島、日光から尾瀬が分かれた など）はまとめ直した。")
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, "fig2_fixed_parks.png")

# 図3：公園別 2019→2024年（番号順＝北から南）
fig, ax = plt.subplots(figsize=(8.8, 6.4))
ys = np.arange(len(fx))[::-1]
cols = [C[0] if v >= 0 else C[1] for v in fx.pct]
ax.barh(ys, fx.pct.clip(-60, 60), color=cols, height=0.65)
for yv, v in zip(ys, fx.pct):
    ax.text((min(v, 60) + 2) if v >= 0 else (max(v, -60) - 2), yv, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=7.8, color=INK2)
ax.set_yticks(ys); ax.set_yticklabels(fx.index, fontsize=8.3)
ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-75, 75)
ax.set_xlabel("2019→2024年の利用者数の増減（%、±60%で切って表示）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"1991年からある{main['n_fixed']}公園のうち{main['n_fixed_down_2019_2024']}公園で2019年を下回った", loc="left", fontsize=11.5)
foot(fig, "注：並びは公園の番号順（おおむね北から南）で、値の順ではない。南アルプスは+125%（もとの人数が少ない）。")
fig.subplots_adjust(left=0.26, right=0.97, top=0.93, bottom=0.14)
save(fig, "fig3_parks_2019_2024.png")

# 図4：訪日客の利用（推計、参考）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
yrs = list(fg.index)
ax.bar([str(y) for y in yrs], fg.foreign_users / 1e4, color=C[2], width=0.6)
for i, y in enumerate(yrs):
    ax.text(i, fg.loc[y, "foreign_users"] / 1e4 + 15, f"{fg.loc[y, 'foreign_users'] / 1e4:.0f}万人\n（合計の{fg.loc[y, 'foreign_share_pct']:.1f}%）", ha="center", fontsize=8.5)
ax.set_ylim(0, 1100); ax.set_ylabel("訪日外国人の国立公園の利用者数（推計、万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"訪日客の利用は2019年の{req['foreign_2019'] / 1e4:.0f}万人から2024年の{req['foreign_2024'] / 1e4:.0f}万人へ（+{req['foreign_pct_2019_2024']:.0f}%）", loc="left", fontsize=11.5)
foot(fig, "注：環境省の推計（参考値、実利用者数）。2020〜22年は推計なし。合計に対する割合は数え方の違う数どうしの大まかな目安。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_foreign.png")
print("ok")
