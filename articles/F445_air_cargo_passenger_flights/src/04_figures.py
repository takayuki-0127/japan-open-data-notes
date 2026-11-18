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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#8a8984"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：国土交通省「航空輸送統計調査」年報 統計表2・5（日本の航空会社、2014〜2025年）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
rq = json.load(open(R / "requestion.json", encoding="utf-8"))
idx = pd.read_csv(R / "index_monthly.csv")
idx["t"] = idx.year + (idx.month - 0.5) / 12


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


def panel(seg, series, title, name, note, ylim):
    d = idx[(idx.segment == seg) & (idx.year >= 2019)]
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    for (v, lab), c in zip(series, C):
        ax.plot(d.t, d[v + "_idx"], color=c, lw=2.0 if v == "cargo_kg" else 1.6, label=lab)
    ax.axhline(100, color=INK2, lw=0.8, ls="--")
    ax.axvspan(2020.25, 2020.5, color=GRID, alpha=0.6, lw=0)
    ax.set_ylim(*ylim); ax.set_xlim(2019, 2026)
    ax.set_xticks(range(2019, 2026)); ax.set_xticklabels([f"{y}年" for y in range(2019, 2026)])
    ax.set_ylabel("2019年の同じ月 = 100")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_title(title, loc="left", fontsize=12.5)
    ax.legend(frameon=False, loc="lower right", fontsize=9.5)
    fig.subplots_adjust(bottom=0.2, top=0.9, left=0.09, right=0.98)
    foot(fig, note)
    save(fig, name)


panel("total", [("cargo_kg", "貨物の重さ"), ("seat_km", "座席キロ（座席数×距離）"), ("pax", "旅客数")],
      f"国内線の貨物は、2020年5月に2019年の{main['min_total_cargo_kg_idx']:.0f}%まで落ち、旅客便とほぼ一緒に動いた",
      "fig1_domestic_index.png", "灰色の帯は2020年4〜5月。国内定期航空の総合計（幹線＋ローカル線）", (0, 135))
panel("intl", [("cargo_kg", "貨物の重さ"), ("seat_km", "座席キロ（座席数×距離）"), ("flights", "運航回数")],
      f"国際線（日本の会社）の貨物は、座席キロが{main['min_intl_seat_km_idx']:.0f}%まで減った月も{main['min_intl_cargo_kg_idx']:.0f}%までしか落ちなかった",
      "fig2_intl_index.png", "灰色の帯は2020年4〜5月。外国の航空会社の便は入らない", (0, 170))

# 図3：2020年4〜6月の減り方（2019年同月比）
items = [("flights", "運航回数"), ("seat_km", "座席キロ"), ("pax", "旅客数"), ("cargo_kg", "貨物の重さ")]
fig, ax = plt.subplots(figsize=(8.8, 4.9))
w = 0.38
for j, (seg, lab, c) in enumerate([("total", "国内線", C[0]), ("intl", "国際線（日本の会社）", C[1])]):
    vals = [main[f"drop_{seg}_apr_jun_{v}"] for v, _ in items]
    xs = [i + (j - 0.5) * w for i in range(len(items))]
    ax.bar(xs, vals, w * 0.95, color=c, label=lab)
    for x_, v in zip(xs, vals):
        ax.text(x_, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9.5, color=INK2)
ax.set_xticks(range(len(items))); ax.set_xticklabels([l for _, l in items])
ax.set_ylabel("2019年4〜6月からの減少率（%）"); ax.set_ylim(0, 110)
ax.grid(axis="y", color=GRID, lw=0.6)
ax.set_title(f"2020年4〜6月、座席キロに対する貨物の落ち方は国内{main['ratio_total_apr_jun_cargo_vs_seatkm']:.2f}倍、国際{main['ratio_intl_apr_jun_cargo_vs_seatkm']:.2f}倍",
             loc="left", fontsize=12.5)
ax.legend(frameon=False, loc="upper right")
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.09, right=0.98)
foot(fig, "減少率は2020年4〜6月の合計と2019年4〜6月の合計の比から計算")
save(fig, "fig3_drop_apr_jun_2020.png")

# 図4：国内の貨物（年）とコロナ前の減り方の延長
t = pd.read_csv(R / "trend_domestic.csv")
t = t[(t.segment == "total") & (t.fit == "2014-2019")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(t.year, t.actual_t / 1000, color=C[0], lw=2.2, marker="o", ms=4, label="実際の貨物の重さ")
tt = t[t.year >= 2019]
ax.plot(tt.year, tt.trend_t / 1000, color=INK2, lw=1.4, ls="--", label=f"2014〜2019年の減り方（年{-rq['total_2014-2019_trend_pct_per_year']:.1f}%）を延ばした線")
ax.plot(t[t.year <= 2019].year, t[t.year <= 2019].trend_t / 1000, color=INK2, lw=1.0, ls=":")
ax.set_ylim(0, 1000); ax.set_xticks(range(2014, 2026)); ax.set_xticklabels([f"{y % 100:02d}" for y in range(2014, 2026)])
ax.set_xlabel("年（20xx年）"); ax.set_ylabel("千トン")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.annotate(f"2025年：実際 {main['cargo_t_total_2025']/1000:.0f}千トン\n延ばした線 {rq['total_2014-2019_pred2025_t']/1000:.0f}千トン",
            xy=(2025, main['cargo_t_total_2025'] / 1000), xytext=(2021.6, 820), fontsize=9.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_title(f"国内線の貨物の2019→2025年の減り分のうち、約{rq['total_2014-2019_share_of_gap_explained_by_trend_pct']:.0f}%はコロナ前の減り方の延長の範囲",
             loc="left", fontsize=12.5)
ax.legend(frameon=False, loc="lower left")
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.09, right=0.98)
foot(fig, "国内定期航空の総合計。延ばした線は2014〜2019年の年の重さに対数の直線を当てはめたもの（説明ではなく比べるための線）")
save(fig, "fig4_domestic_trend.png")
print("figures saved")
