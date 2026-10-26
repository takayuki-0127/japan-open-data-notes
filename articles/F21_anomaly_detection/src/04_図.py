"""04 図：figures/ に5枚"""
from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
EVENTS = import_module("03_分析").EVENTS

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 12.5, "figure.dpi": 150, "savefig.bbox": "tight"})
BLUE, RED, GRAY, ORANGE, GREEN = "#2f6db5", "#c8463d", "#9aa0a6", "#e08a1e", "#3a9a5b"
THR = 4.0

Z = pd.read_csv(RES / "z_scores.csv", parse_dates=["month"], index_col="month")
mon = pd.read_csv(RES / "monthly_scores.csv", parse_dates=["month"], index_col="month")


def shade(ax, alpha=0.12):
    for a, b, lab, cat, exp in EVENTS:
        ax.axvspan(pd.Timestamp(a) - pd.Timedelta(days=15), pd.Timestamp(b) + pd.Timedelta(days=45), color=ORANGE, alpha=alpha, lw=0)


# 1 1系列の例：鉱工業生産と家計の一般外食
fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
for ax, key, title in [(axes[0], "景気:鉱工業生産", "鉱工業生産（前月からの変化）の残差 z スコア"),
                       (axes[1], "家計:一般外食", "家計調査の一般外食（前月からの変化）の残差 z スコア")]:
    z = Z[key]
    shade(ax)
    ax.plot(z.index, z, color=BLUE, lw=1)
    hit = z[z.abs() > THR]
    ax.scatter(hit.index, hit, color=RED, s=22, zorder=3)
    for t in [THR, -THR]:
        ax.axhline(t, color=GRAY, ls="--", lw=0.8)
    ax.set_title(title, loc="left")
    ax.set_ylabel("z")
    shown = []
    for d, v in hit.abs().sort_values(ascending=False).items():
        if any(abs((d - x).days) < 200 for x in shown) or len(shown) >= 4:
            continue
        shown.append(d)
        ax.annotate(f"{d:%Y-%m}", (d, hit[d]), xytext=(4, 4 if hit[d] > 0 else -12), textcoords="offset points", fontsize=8.5, color=RED)
axes[1].text(0.0, -0.22, "橙の帯＝出来事の年表の月。赤い点＝|z|>4。季節と傾向は STL で除いたあとの「いつもと違う」大きさ。",
             transform=axes[1].transAxes, fontsize=9, color="#444")
fig.savefig(FIG / "f21_1_single_series.png"); plt.close(fig)

# 2 ヒートマップ（月×系列）
order = [c for c in Z.columns if c.startswith("景気:")] + [c for c in Z.columns if c.startswith("家計:")] + [c for c in Z.columns if c.startswith("物価:")]
A = Z[order].abs().clip(0, 10).T
fig, ax = plt.subplots(figsize=(11, 7.2))
im = ax.imshow(A.values, aspect="auto", cmap="Blues", vmin=0, vmax=10, interpolation="nearest")
yrs = [i for i, d in enumerate(A.columns) if d.month == 1 and d.year % 2 == 0]
ax.set_xticks(yrs); ax.set_xticklabels([A.columns[i].year for i in yrs])
n1 = sum(c.startswith("景気:") for c in order); n2 = n1 + sum(c.startswith("家計:") for c in order)
for y in [n1 - 0.5, n2 - 0.5]:
    ax.axhline(y, color="#333", lw=0.8)
ax.set_yticks([n1 / 2, (n1 + n2) / 2, (n2 + len(order)) / 2]); ax.set_yticklabels(["景気動向指数の\n個別系列（20）", "家計調査\n（30品目）", "消費者物価\n（48分類）"])
for k, (lab, d) in enumerate([("リーマン", "2008-12"), ("震災", "2011-03"), ("増税8%", "2014-04"), ("増税10%", "2019-10"), ("コロナ", "2020-04")]):
    i = list(A.columns).index(pd.Timestamp(d))
    ax.annotate(lab, (i, -1), xytext=(i - (6 if lab == "増税10%" else 0) + (6 if lab == "コロナ" else 0), -4), ha="right" if lab == "増税10%" else ("left" if lab == "コロナ" else "center"), fontsize=9, color=RED, annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01); cb.set_label("|z|（10で頭打ち）")
ax.set_title("98系列×260か月の「いつもと違う」大きさ（濃いほど異常）", loc="left", pad=22)
fig.savefig(FIG / "f21_2_heatmap.png"); plt.close(fig)

# 3 Isolation Forest の上位の月
top = mon.sort_values("iso_score", ascending=False).head(20).iloc[::-1]
labels = {}
for a, b, lab, *_ in EVENTS:
    for d in pd.date_range(pd.Timestamp(a) - pd.DateOffset(months=1), pd.Timestamp(b) + pd.DateOffset(months=1), freq="MS"):
        labels.setdefault(d, lab)
fig, ax = plt.subplots(figsize=(9.5, 7))
cols = [BLUE if e else RED for e in top.in_event_window]
ax.barh(range(len(top)), top.iso_score, color=cols)
ax.set_yticks(range(len(top))); ax.set_yticklabels([f"{d:%Y-%m}" for d in top.index])
for i, (d, r) in enumerate(top.iterrows()):
    ax.text(r.iso_score + 0.003, i, f"{labels.get(d, '年表になし')}（{int(r.n_flagged)}系列）", va="center", fontsize=8.8,
            color="#333" if r.in_event_window else RED)
ax.set_xlim(top.iso_score.min() * 0.92, top.iso_score.max() * 1.42)
ax.set_xlabel("Isolation Forest の異常スコア（大きいほど、その月の98系列の動き方が珍しい）")
ax.set_title("まとめて見て「珍しい月」の上位20", loc="left")
ax.text(0, -0.15, "青＝出来事の年表の月（前後1か月を含む）、赤＝年表にない月。（ ）は |z|>4 の系列の数。",
        transform=ax.transAxes, fontsize=9, color="#444")
fig.savefig(FIG / "f21_3_top_months.png"); plt.close(fig)

# 4 変化点
cps = json.load(open(RES / "change_points.json"))
fig, axes = plt.subplots(2, 2, figsize=(11, 7.4))
for ax, (key, title) in zip(axes.flat, [("物価:たばこ", "たばこ（物価、対数×100）"), ("物価:授業料等", "授業料等（物価、対数×100）"),
                                         ("物価:電気代", "電気代（物価、対数×100）"), ("物価:通信", "通信（物価、対数×100）")]):
    s = pd.read_csv(RES / f"level_sa_{key.split(':')[1]}.csv", parse_dates=[0], index_col=0).iloc[:, 0]
    ax.plot(s.index, s, color=BLUE, lw=1.2)
    for d in cps[key]:
        ax.axvline(pd.Timestamp(d), color=RED, lw=0.9, ls="--")
    ds = [d[:7].replace("-", "/") for d in cps[key]]
    ax.set_title(title, loc="left", fontsize=11)
    ax.text(0.0, -0.12, "変わり目：" + "、".join(ds[:4]) + ("\n　　　　　" + "、".join(ds[4:]) if len(ds) > 4 else ""),
            transform=ax.transAxes, fontsize=8.8, color=RED, va="top")
fig.suptitle("水準の変わり目（PELT）：赤い線が「新しい水準が始まった月」", x=0.01, ha="left", fontweight="bold", fontsize=12.5)
fig.tight_layout(h_pad=3.2)
fig.savefig(FIG / "f21_4_change_points.png"); plt.close(fig)

# 5 閾値のトレードオフ
t = pd.read_csv(RES / "threshold_tradeoff.csv")
base = json.load(open(RES / "summary.json"))["random_baseline_share_in_event_months"]
fig, ax1 = plt.subplots(figsize=(9, 5))
ax1.bar(t.thr.astype(str), t.n_flags, color="#c9d7ea")
ax1.set_ylabel("印の数（98系列×260か月の中で）")
ax1.set_xlabel("閾値（|z| がこれを超えたら印）")
ax2 = ax1.twinx()
ax2.plot(t.thr.astype(str), t.recall * 100, color=BLUE, marker="o", label="年表の出来事のうち見つかった割合（14件）")
ax2.plot(t.thr.astype(str), t.share_in_event_months * 100, color=RED, marker="s", label="印のうち出来事の月に入る割合")
ax2.axhline(base * 100, color=RED, ls=":", lw=1)
ax2.text(len(t) - 1, base * 100 + 1.5, f"でたらめに印を付けたとき {base*100:.0f}%", ha="right", fontsize=8.5, color=RED)
ax2.set_ylim(0, 105); ax2.set_ylabel("%")
ax2.spines["right"].set_visible(True)
for i, r in t.iterrows():
    ax1.text(i, r.n_flags + 15, f"{int(r.n_flags)}", ha="center", fontsize=8.5, color="#555")
ax2.legend(loc="upper left", bbox_to_anchor=(0.27, 0.9), fontsize=9, frameon=True, facecolor="white", edgecolor="#ddd")
ax1.set_title("閾値を上げると、印は減り、出来事に当たる割合は上がるが、見落としも増える", loc="left")
fig.savefig(FIG / "f21_5_threshold.png"); plt.close(fig)
print("ok")
