"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
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
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK2, GRID = "#52514e", "#e4e3df"
META = {"Software": None}
S_H = "出典：農林水産省「畜産統計」をもとに作成者が加工して作成"
S_E = "出典：財務省「貿易統計」、農林水産省「畜産物流通統計」をもとに作成者が加工して作成"
M = json.load(open(R / "main.json", encoding="utf-8"))
L = pd.read_csv(R / "heads_linked.csv").set_index("year")
S = pd.read_csv(R / "export_vs_wagyu.csv").set_index("year")
Q = pd.read_csv(R / "requestion_start_year.csv")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, src, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + src, fontsize=7.6, color=INK2)


def style(ax):
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)


# 図1：品種別の飼養頭数
d = M["H1_decomp_linked"]
fig, ax = plt.subplots(figsize=(8.8, 4.9))
g = L.loc[2005:2025]
for col, c, lab in [("beef_breed", C1, "肉用種（黒毛和種など）"), ("cross", C2, "交雑種（乳牛×和牛）"), ("holstein", C3, "ホルスタイン種他")]:
    v = g[col] / 1e4
    ax.plot(v.index, v.values, color=c, lw=2, label=lab)
    ax.text(2025.4, v[2025], f"{v[2025]:.0f}", color=INK2, fontsize=9, va="center")
ax.axvspan(d["y0"], d["y1"], color="#efeeea", zorder=0)
ax.text((d["y0"] + d["y1"]) / 2, 140, f'底{d["y0"]}年→山{d["y1"]}年\n総頭数 +{d["d_total"]/1e4:.1f}万頭\n肉用種 +{d["d_beef"]/1e4:.1f}万頭', ha="center", fontsize=9, color=INK2, va="top", bbox=dict(fc="#efeeea", ec="none", pad=2))
ax.axvline(2019.5, color=INK2, lw=0.8, ls=":")
ax.text(2019.6, 8, "2020年から集計方法が変更\n（2019年以前は新旧の比でつないだ）", fontsize=7.8, color=INK2)
ax.set_ylim(0, 215); ax.set_xlim(2004.5, 2027); ax.set_ylabel("飼養頭数（万頭、各年2月1日）")
ax.set_title("増えたのは肉用種。ホルスタイン種は減り続けた（肉用牛の飼養頭数、全国）", fontsize=11.5, loc="left")
ax.legend(frameon=False, loc="center left", fontsize=9, bbox_to_anchor=(0, 0.6)); style(ax)
fig.subplots_adjust(bottom=0.15, top=0.9, left=0.09, right=0.95)
foot(fig, S_H); save(fig, "fig1_heads_by_breed.png")

# 図2：輸出（枝肉に直した量）と和牛の枝肉生産量
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.7))
ax = axes[0]
s = S.loc[2009:2024]
ax.bar(s.index, s.wagyu_t / 1e4, color="#c9c8c2", width=0.75, label="和牛の枝肉生産量")
ax.bar(s.index, s.export_carcass_t_y07 / 1e4, color=C2, width=0.75, label="牛肉の輸出（枝肉に直した量）")
ax.set_ylabel("万t"); ax.set_title("和牛の生産と輸出の量", fontsize=11, loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, 1.0)); ax.set_ylim(0, 33); style(ax)
ax = axes[1]
sh = S.loc[2009:2024, "share_of_wagyu_pct_y07"]
lo = S.loc[2009:2024, "share_of_wagyu_pct_y08"]; hi = S.loc[2009:2024, "share_of_wagyu_pct_y06"]
ax.fill_between(sh.index, lo, hi, color=C2, alpha=0.18, lw=0, label="歩留まり0.6〜0.8の幅")
ax.plot(sh.index, sh.values, color=C2, lw=2, label="歩留まり0.7")
ax.text(2024.3, sh[2024], f"{sh[2024]:.1f}%", fontsize=9, color=INK2, va="center")
ax.text(2012, sh[2012] + 0.6, f"{sh[2012]:.1f}%", fontsize=9, color=INK2, ha="center")
ax.set_ylim(0, 10); ax.set_ylabel("和牛の枝肉生産量に対する輸出の割合（%）")
ax.set_title("輸出は和牛の生産の約20分の1", fontsize=11, loc="left"); ax.legend(frameon=False, fontsize=8.5, loc="upper left"); style(ax)
for a in axes:
    a.set_xlim(2008.3, 2025.5)
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.07, right=0.96, wspace=0.28)
foot(fig, S_E, "輸出は HS 0201・0202 の合計（和牛以外の牛肉も含む）。部分肉の歩留まりを0.7と置いて枝肉の重さに直した（置いた値）。")
save(fig, "fig2_export_share.png")

# 図3：数え始めの年で変わる「増産分のうち輸出に回った割合」
fig, ax = plt.subplots(figsize=(8.6, 4.6))
cols = [C2 if r >= 50 else C1 for r in Q.ratio_pct]
ax.bar(Q.start_year, Q.ratio_pct, color=cols, width=0.7)
for x, y in zip(Q.start_year, Q.ratio_pct):
    ax.text(x, y + 1.5, f"{y:.0f}", ha="center", fontsize=8.8, color=INK2)
ax.axhline(50, color=INK2, lw=0.8, ls="--"); ax.text(2020.6, 51.5, "半分", fontsize=8.5, color=INK2, ha="right")
ax.set_xticks(Q.start_year); ax.set_xlabel("数え始めの年（終わりは2024年）")
ax.set_ylabel("和牛の生産の増加に対する輸出の増加（%）"); ax.set_ylim(0, 85)
ax.set_title("増産分のうち輸出に回った割合は、数え始めの年で20〜75%。2016年の底からなら約2割", fontsize=11.5, loc="left"); style(ax)
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.09, right=0.97)
foot(fig, S_E, "いずれも枝肉の重さ（輸出は歩留まり0.7で換算）。2012年は和牛の生産が多かった年で、そこから数えると割合が大きく出る。")
save(fig, "fig3_start_year.png")

# 図4：戸数と1戸当たり頭数
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.4))
g = L.loc[1995:2025]
axes[0].plot(g.index, g.farms / 1e4, color=C1, lw=2)
axes[0].text(2025.4, g.farms[2025] / 1e4, f"{g.farms[2025]/1e4:.1f}", fontsize=9, color=INK2, va="center")
axes[0].set_title("飼養戸数（万戸）", fontsize=11, loc="left"); axes[0].set_ylim(0, None)
axes[1].plot(g.index, g.per_farm, color=C1, lw=2)
axes[1].text(2025.4, g.per_farm[2025], f"{g.per_farm[2025]:.0f}", fontsize=9, color=INK2, va="center")
axes[1].set_title("1戸当たり飼養頭数（頭）", fontsize=11, loc="left"); axes[1].set_ylim(0, None)
for a in axes:
    a.set_xlim(1994, 2028); style(a)
fig.suptitle(f'戸数は2015→2025年に{-M["H4_farms"]["pct_farms_raw"]:.0f}%減り、1戸当たり頭数は{M["H4_farms"]["per_farm_x_raw"]:.2f}倍', x=0.01, ha="left", fontsize=11.5)
fig.subplots_adjust(bottom=0.15, top=0.84, left=0.07, right=0.95, wspace=0.25)
foot(fig, S_H, f'線は2019年以前を2020年からの集計方法との比でつないだ値。題の数字は公表値のまま（つないだ値では{M["H4_farms"]["pct_farms_linked"]:.1f}%、{M["H4_farms"]["per_farm_x_linked"]:.2f}倍）。')
save(fig, "fig4_farms.png")
