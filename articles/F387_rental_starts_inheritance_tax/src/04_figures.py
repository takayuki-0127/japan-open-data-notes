"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F, DATA = ROOT / "results", ROOT / "figures", ROOT / "data"
F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID, BAND = "#0b0b0b", "#52514e", "#e4e3df", "#f1efe8"
SRC = "出典：国土交通省「建築着工統計調査」住宅着工統計（新設住宅の着工戸数、年計）をもとに作成者が加工して作成"
META = {"Software": None}
fmt = matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
rq = json.loads((R / "requestion.json").read_text(encoding="utf-8"))


def finish(fig, title, bottom=0.14, left=0.09):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=left, right=0.97, top=0.88, bottom=bottom)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def mark(ax, ymax):
    ax.axvspan(2012.5, 2018.5, color=BAND, zorder=0)
    ax.axvline(2015, color=INK2, lw=0.8, ls=":")
    ax.text(2015.1, ymax, "2015年1月\n相続税の基礎控除の引き下げ", fontsize=8, color=INK2, va="top")
    ax.text(2012.6, ymax * 0.06 if ymax > 1 else ymax, "", fontsize=8)


# 図1：利用関係別の着工戸数
ng = pd.read_csv(R / "national_gap.csv")
fig, ax = plt.subplots(figsize=(10, 4.8))
for col, lab, c, dy in (("rental", "貸家", C[1], 0), ("owner", "持家", C[0], -7), ("forsale", "分譲住宅", C[2], 7)):
    ax.plot(ng.year, ng[col], color=c, lw=2.2, label=lab)
    ax.annotate(f"{lab} {ng[col].iloc[-1]:,.0f}", (2025, ng[col].iloc[-1]), textcoords="offset points", xytext=(5, dy), va="center", fontsize=8.6, color=c)
mark(ax, 590000)
ax.text(2012.6, 25000, "色の帯：2013〜2018年（見直しの成立から）", fontsize=8, color=INK2)
ax.set_ylim(0, 600000); ax.set_xlim(1999.5, 2028.5); ax.yaxis.set_major_formatter(fmt)
ax.set_ylabel("新設住宅の着工戸数（戸、年）"); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
L = m["levels"]["貸家"]
finish(fig, f"貸家の着工は2010〜12年の年{L['base_2010_12'] / 1e4:.1f}万戸から2014〜17年に{L['post_2014_17'] / 1e4:.1f}万戸（{L['pct']:+.1f}%）。持家は{m['levels']['持家']['pct']:+.1f}%")
save(fig, "fig1_starts_by_tenure.png")

# 図2：貸家と持家・分譲住宅の差（2012年＝0）
ev = pd.read_csv(R / "event_pref.csv")
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.fill_between(ev.year, ev.lo, ev.hi, color=C[1], alpha=0.15, lw=0, label="都道府県の平均の95%区間")
ax.plot(ev.year, ev["mean"], color=C[1], lw=2, marker="o", ms=3.5, label="対持家：47都道府県の平均")
ax.plot(ng.year, ng.G_owner_rel2012, color=INK, lw=1.4, ls="--", label="対持家：全国")
ax.plot(ng.year, ng.G_forsale_rel2012, color=C[2], lw=1.4, ls="-.", label="対分譲住宅：全国")
ax.axhline(0, color=INK2, lw=0.8)
mark(ax, 0.62)
ax.axvspan(2004.5, 2008.5, color="#e8eef8", zorder=0)
ax.text(2004.6, -0.2, "2005〜08年", fontsize=8, color=INK2)
ax.axvspan(2009.5, 2012.5, color="#f6e9e2", zorder=0)
ax.text(2009.6, -0.2, "2010〜12年\n（基準）", fontsize=8, color=INK2)
ax.set_ylim(-0.25, 0.65); ax.set_xlim(1999.5, 2025.5)
ax.set_ylabel("貸家と比べる相手の着工の差\n（対数の差、2012年＝0）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=8.4, loc="upper left", ncol=2)
finish(fig, f"持家と比べた貸家の上乗せは{m['did_national']:+.2f}（2010〜12年比）。ただし2005〜08年も同じくらいの高さだった", left=0.11)
save(fig, "fig2_gap_vs_owner.png")

# 図3：都道府県ごとの差の差（北から南）
pdid = pd.read_csv(R / "pref_did.csv")
d = pd.read_csv(DATA / "starts_pref.csv")
pdid["did_0508"] = pdid.did_owner_base0508
fig, ax = plt.subplots(figsize=(11, 5))
x = np.arange(len(pdid))
ax.bar(x, pdid.did_owner, color=[C[1] if v else "#f2b597" for v in pdid.metro], width=0.75, label="基準2010〜12年")
ax.scatter(x, pdid.did_0508, color=INK, s=14, zorder=3, label="基準2005〜08年")
ax.axhline(0, color=INK2, lw=0.8)
short = [a if a == "北海道" else a[:-1] for a in pdid.area]
ax.set_xticks(x, short, rotation=90, fontsize=8)
ax.set_ylabel("貸家の上乗せ（対持家、対数の差）\n2014〜17年 − 基準の時期")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
from matplotlib.patches import Patch
h = [Patch(color=C[1], label="三大都市圏（基準2010〜12年）"), Patch(color="#f2b597", label="地方圏（基準2010〜12年）"),
     plt.Line2D([], [], marker="o", color=INK, lw=0, ms=4, label="基準を2005〜08年にした値")]
ax.legend(handles=h, frameon=False, fontsize=8.4, loc="upper right", ncol=3)
P = m["pref"]
finish(fig, f"2010〜12年を基準にすると{P['n_positive']}都道府県で上乗せがプラス。2005〜08年を基準にするとプラスは{m['robustness']['基準を2005〜08年（2009年の落ち込みの前）']['pref_n_positive']}（並びは北から南）",
       bottom=0.22, left=0.1)
save(fig, "fig3_pref_did.png")

# 図4：貸家の構造別
r = d[(d.area == "全国") & (d.tenure == "貸家") & (d.type == "計") & (d.struct != "計")].copy()
r["sg"] = r.struct.map({"木造": "木造", "鉄骨造": "鉄骨造", "鉄骨鉄筋コンクリート造": "鉄筋コンクリート系", "鉄筋コンクリート造": "鉄筋コンクリート系",
                        "コンクリートブロック造": "その他", "その他": "その他"})
s = r[r.year >= 2000].pivot_table(index="year", columns="sg", values="units", aggfunc="sum")
fig, ax = plt.subplots(figsize=(10, 4.8))
for col, c in (("木造", C[3]), ("鉄骨造", C[0]), ("鉄筋コンクリート系", INK2)):
    ax.plot(s.index, s[col], color=c, lw=2.2, label=col)
    ax.annotate(f"{col}", (2025, s[col].iloc[-1]), textcoords="offset points", xytext=(5, 0), va="center", fontsize=8.6, color=c)
mark(ax, 275000)
ax.set_ylim(0, 280000); ax.set_xlim(1999.5, 2028.5); ax.yaxis.set_major_formatter(fmt)
ax.set_ylabel("貸家の着工戸数（戸、年）"); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
W = rq["wood_rental_peak"]
finish(fig, f"見直しの後に大きく増えたのは木造の貸家。2017年の{W['units_2017']:,}戸は{W['last_year_above_2017_before'] + 1}年以降で最多")
save(fig, "fig4_rental_by_structure.png")
print("ok")
