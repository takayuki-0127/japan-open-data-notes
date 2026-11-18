"""図4枚（PNG）。日付などのメタデータは入れない。数字は results から読む。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import ROOT, REGIONS

R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：経済産業省「商業統計」（時系列表、業態別統計編）、総務省統計局「消費者物価指数」をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
nat = pd.read_csv(R / "national_by_year.csv", index_col="year")


def finish(fig, ax, title, sub=None):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=22 if sub else 12)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=INK2)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


# ---- 図1：売場面積と販売額（1991年=100）----
yy = [y for y in nat.index if y >= 1982]
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.82, top=0.85, bottom=0.12)
for col, lab, c in [("floor_m2_idx1991", "売場面積", "#2a78d6"), ("sales_mil_yen_idx1991", "販売額（名目）", "#eb6834")]:
    ys = [nat.loc[y, col] for y in yy]
    ax.plot(yy, ys, color=c, lw=2, marker="o", ms=5.5, mec="#fcfcfb", mew=1.3)
    ax.text(2007.6, ys[-1], f"{lab} {ys[-1]:.1f}", va="center", fontsize=10, color=INK)
ax.axhline(100, color="#b9b8b3", lw=0.8, ls="--")
ax.set_xticks(yy); ax.set_xticklabels([str(y) for y in yy], fontsize=9)
ax.set_ylim(60, 145); ax.set_ylabel("1991年＝100")
finish(fig, ax, "1991年から売場は36%広がり、販売額は4%減った",
       "全国の小売業の売場面積と年間商品販売額（1991年＝100）。1999年は調べる事業所が増えた年")
save(fig, "fig1_floor_sales_index.png")

# ---- 図2：実質の1㎡あたり販売額（1972〜2007年）----
yy = list(nat.index)
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.95, top=0.85, bottom=0.12)
ys = [nat.loc[y, "real_eff_2025yen"] for y in yy]
ax.plot(yy, ys, color="#2a78d6", lw=2, marker="o", ms=5.5, mec="#fcfcfb", mew=1.3, label="実質（2025年の物価）")
ax.plot(yy, [nat.loc[y, "eff_10k_yen_m2"] for y in yy], color="#b9b8b3", lw=2, label="名目")
for y in (1972, 1991, 2007):
    ax.text(y, nat.loc[y, "real_eff_2025yen"] + 5, f"{nat.loc[y, 'real_eff_2025yen']:.1f}", ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 175); ax.set_ylabel("売場1㎡あたりの年間販売額（万円）")
ax.legend(frameon=False, loc="lower right")
finish(fig, ax, "物価をならすと、1㎡あたり販売額は1991年から下がり続けた",
       "全国の小売業の販売額÷売場面積。実質は消費者物価指数（総合、暦年）で2025年の物価にした値")
save(fig, "fig2_real_sales_per_m2.png")

# ---- 図3：業態別の1㎡あたり販売額 ----
YG = [1991, 1994, 1997, 1999, 2002, 2004, 2007]
items = [("cvs", "コンビニ", "#8a63d2"), ("dept", "百貨店", "#eb6834"), ("sm_food", "食料品スーパー", "#1baf7a"),
         ("drug", "ドラッグストア", "#e87ba4"), ("gms", "総合スーパー", "#2a78d6"), ("sm_home", "住関連スーパー", "#eda100")]
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.78, top=0.85, bottom=0.12)
last = []
for g, lab, c in items:
    e = m["gyotai_eff"][g]
    xs = [y for y in YG if str(y) in e]
    ys = [e[str(y)] for y in xs]
    ax.plot(xs, ys, color=c, lw=2, marker="o", ms=5.5, mec="#fcfcfb", mew=1.3)
    if g in m["ref_2014_eff"]:
        ax.plot([2014], [m["ref_2014_eff"][g]], marker="o", ms=6, mfc="#fcfcfb", mec=c, mew=1.6, ls="none")
    last.append([ys[-1], f"{lab} {ys[-1]:.0f}"])
last.sort(); pos = []
for v, lab in last:
    p = v if not pos or v - pos[-1] >= 6 else pos[-1] + 6
    pos.append(p); ax.text(2015.2, p, lab, va="center", fontsize=9.5, color=INK)
ax.axvline(2010.5, color="#b9b8b3", lw=0.8, ls=":")
ax.text(2012.3, 175, "白抜きは2014年\n（調べ方が変わり\n線はつながない）", fontsize=8, color=INK2, ha="center", va="top")
ax.set_xticks(YG + [2014]); ax.set_xticklabels([str(y) for y in YG + [2014]], fontsize=9)
ax.set_xlim(1990, 2015); ax.set_ylim(0, 180)
ax.set_ylabel("売場1㎡あたりの年間販売額（万円、名目）")
finish(fig, ax, "店舗型の業態ではコンビニだけが1㎡あたり販売額を保った",
       "全国、業態別。右の数字は2007年。ドラッグストアは1999年から分かれた")
save(fig, "fig3_by_gyotai.png")

# ---- 図4：地方別（北から南）----
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.16)
x = range(len(REGIONS)); w = 0.38
fl = [m["region"][r]["floor_pct_1991_2007"] for r in REGIONS]
sa = [m["region"][r]["sales_pct_1991_2007"] for r in REGIONS]
ax.bar([i - w / 2 - 0.01 for i in x], fl, width=w, color="#2a78d6", label="売場面積")
ax.bar([i + w / 2 + 0.01 for i in x], sa, width=w, color="#eb6834", label="販売額（名目）")
for i, (a, b) in enumerate(zip(fl, sa)):
    ax.text(i - w / 2, a + 1, f"{a:+.0f}%", ha="center", fontsize=8.5, color=INK)
    ax.text(i + w / 2, b + (1 if b >= 0 else -3.2), f"{b:+.0f}%", ha="center", fontsize=8.5, color=INK)
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_xticks(list(x)); ax.set_xticklabels([f"{r}\n（1㎡ {m['region'][r]['eff_pct_1991_2007']:+.0f}%）" for r in REGIONS], fontsize=9.5)
ax.set_ylim(-20, 50); ax.set_ylabel("1991→2007年の増減（%）"); ax.legend(frameon=False, loc="upper right", ncol=2)
finish(fig, ax, "どの地方でも、売場の伸びが販売額の伸びを上回った",
       "地方別（北から南）、1991→2007年。かっこは1㎡あたり販売額の増減")
save(fig, "fig4_by_region.png")
