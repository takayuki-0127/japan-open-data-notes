"""05 図（サンプルマート（架空）、合成データ）。図6は reports/report_202603_onepage.html を画像にしたもの（playwright）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#2b2b2b", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BLUE, ORANGE, AQUA, GRAY, INK, MUTED, RED = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29d", "#0b0b0b", "#52514e", "#c8423b"
NOTE = "サンプルマート（架空）・合成データ。会社も数字も実在しません。"
m = json.load(open(RES / "main.json"))
A = pd.read_csv(RES / "A_monthly_decomposition_seed0.csv").set_index("ym")
B = pd.read_csv(RES / "B_noise_band90_halfwidth.csv", index_col=0)
MU = pd.read_csv(RES / "B_seed_mean.csv", index_col=0)
IND = pd.read_csv(RES / "F_industry_yoy.csv", index_col=0).iloc[:, 0]
T = m["target"]
lab = lambda ym: f"{int(ym[5:])}月"


def save(fig, name):
    fig.text(0.01, -0.07, NOTE, fontsize=8, color=MUTED)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


# 図1：FY2025 の各月の既存店売上の前年比と、偶然の幅
fy = [ym for ym in A.index if ym >= "2025-04"]
fig, ax = plt.subplots(figsize=(9.2, 4.4))
x = np.arange(len(fy))
ax.fill_between(x, (MU.loc[fy, "sales_yoy"] - B.loc[fy, "sales_yoy"]) * 100, (MU.loc[fy, "sales_yoy"] + B.loc[fy, "sales_yoy"]) * 100,
                color=GRAY, alpha=0.28, step="mid", label="偶然の幅（乱数を変えた20通りの90%）")
cols = [RED if ym == T else BLUE for ym in fy]
ax.bar(x, A.loc[fy, "sales_yoy"] * 100, width=0.55, color=cols, label="既存店売上の前年比（実際）", zorder=3)
ax.plot(x, A.loc[fy, "sales_yoy_all"] * 100, "o", color=INK, ms=4, label="全店（新店・閉店を含む）", zorder=4)
ax.plot(x, IND.loc[fy] * 100, "--", color=ORANGE, lw=1.6, label="業界：商業動態統計 スーパー（全店・名目）", zorder=4)
for i, ym in enumerate(fy):
    v = A.loc[ym, "sales_yoy"] * 100
    ax.text(i, v + (0.25 if v >= 0 else -0.25), f"{v:+.1f}".replace("-", "−"), ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5,
            color=RED if ym == T else INK, weight="bold" if ym == T else None)
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_xticks(x, [lab(ym) for ym in fy]); ax.set_ylabel("前年同月比（%）")
ax.set_title("3月は今年度はじめての前年割れ（既存店 −1.1%）。偶然の幅は毎月 ±1pt 前後", loc="left", fontsize=12)
ax.legend(fontsize=8.4, loc="upper right", ncol=2, frameon=False)
ax.set_ylim(-3, 9)
save(fig, "fig1_monthly_yoy_band.png")

# 図2：2026年3月の要因（滝の図）
t = A.loc[T]; b = B.loc[T]
items = [("一品単価\n（値上がり）", t.c_price, b.c_price), ("1回の\n買上点数", t.c_items, b.c_items),
         ("暦の差\n（土曜が1日少ない）", t.c_calendar, 0), ("客数\n（暦をそろえた）", t.c_receipts_adj, b.c_receipts_adj)]
fig, ax = plt.subplots(figsize=(8.6, 4.6))
cum = 0
for i, (nm, v, e) in enumerate(items):
    c = AQUA if v > 0 else (GRAY if nm.startswith("暦") else ORANGE)
    ax.bar(i, v * 100, bottom=cum * 100, color=c, width=0.6, zorder=3)
    if e > 0:
        ax.errorbar(i, (cum + v) * 100, yerr=e * 100, color=INK, capsize=5, lw=1.2, zorder=4)
    ax.text(i + 0.33, (cum + v / 2) * 100, f"{v * 100:+.1f}pt".replace("-", "−"), va="center", fontsize=10)
    if i < len(items) - 1:
        ax.plot([i + 0.3, i + 0.7], [(cum + v) * 100] * 2, color=MUTED, lw=0.8)
    cum += v
ax.bar(len(items), t.sales_yoy * 100, color=RED, width=0.6, zorder=3)
ax.errorbar(len(items), t.sales_yoy * 100, yerr=b.sales_yoy * 100, color=INK, capsize=5, lw=1.2, zorder=4)
ax.text(len(items) + 0.33, t.sales_yoy * 100 / 2, f"{t.sales_yoy * 100:+.1f}%".replace("-", "−"), va="center", fontsize=10.5, weight="bold", color=RED)
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_xticks(range(len(items) + 1), [n for n, _, _ in items] + ["既存店売上\nの前年比"], fontsize=9.5)
ax.set_ylabel("売上の前年比への寄与（pt）")
ax.set_title("2026年3月：値上がりの +4.1pt を、客数 −3.1pt・点数 −1.3pt・暦 −0.9pt が打ち消した", loc="left", fontsize=11.5)
ax.text(0.99, 0.97, "黒い線＝偶然の幅（90%）", transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=MUTED)
ax.set_xlim(-0.5, len(items) + 0.8)
save(fig, "fig2_waterfall_202603.png")

# 図3：地域の差は1か月では偶然と見分けにくい（3月 vs 年度12か月）
rel = m["rel_target"]; fya = m["fy2025_area_seed0"]; fyb = m["fy2025_area_band90_half"]; fym = m["fy2025_area_seed_mean"]
areas = ["都市", "郊外", "地方"]
truth_m = {a: MU.loc[T, f"rel_area_receipts_adj_yoy_{a}"] for a in areas}
fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)
for ax, ttl, vals, bands, tru in [
        (axs[0], "3月だけ（1か月）", [rel[f"rel_area_receipts_adj_yoy_{a}"][0] for a in areas], [rel[f"rel_area_receipts_adj_yoy_{a}"][1] for a in areas], [truth_m[a] for a in areas]),
        (axs[1], "年度の12か月（FY2025）", [fya[f"rel_fy_receipts_adj_yoy_{a}"] for a in areas], [fyb[f"rel_fy_receipts_adj_yoy_{a}"] for a in areas], [fym[f"rel_fy_receipts_adj_yoy_{a}"] for a in areas])]:
    y = np.arange(len(areas))[::-1]
    for yi, v, e, tr in zip(y, vals, bands, tru):
        ax.add_patch(plt.Rectangle((-e * 100, yi - 0.28), 2 * e * 100, 0.56, color=GRAY, alpha=0.3))
        out = abs(v) > e
        ax.plot(v * 100, yi, "o", ms=9, color=ORANGE if out else BLUE, zorder=3)
        ax.plot(tr * 100, yi, "|", ms=16, mew=2.2, color=INK, zorder=4)
        ax.text(v * 100, yi + 0.33, f"{v * 100:+.1f}".replace("-", "−"), ha="center", fontsize=9, color=ORANGE if out else BLUE)
    ax.axvline(0, color=MUTED, lw=0.8); ax.set_yticks(y, areas); ax.set_title(ttl, fontsize=11)
    ax.set_xlabel("暦をそろえた客数の前年比の、全体との差（pt）"); ax.set_xlim(-4, 4)
axs[0].plot([], [], "o", color=ORANGE, label="偶然の幅（灰色）の外"); axs[0].plot([], [], "o", color=BLUE, label="幅の中")
axs[0].plot([], [], "|", ms=12, mew=2, color=INK, label="設定上の本当の差（答え）"); fig.legend(fontsize=8.5, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.03))
fig.subplots_adjust(bottom=0.22, top=0.86)
fig.suptitle("1か月では郊外が悪く地方は目立たないが、12か月で見ると差は地方 −2.3pt・都市 +2.1pt（設定どおり）", x=0.01, ha="left", fontsize=11.5)
save(fig, "fig3_area_month_vs_year.png")

# 図4：部門と店の差（3月）を偶然の幅と並べる
fig, axs = plt.subplots(1, 2, figsize=(10, 5.2), gridspec_kw={"width_ratios": [1, 1.6]})
cats = [k.replace("rel_cat_sales_yoy_", "") for k in rel if k.startswith("rel_cat")]
ax = axs[0]; y = np.arange(len(cats))[::-1]
for yi, c in zip(y, cats):
    v, e, out = rel[f"rel_cat_sales_yoy_{c}"]
    ax.add_patch(plt.Rectangle((-e * 100, yi - 0.3), 2 * e * 100, 0.6, color=GRAY, alpha=0.3))
    ax.plot(v * 100, yi, "o", color=ORANGE if out else BLUE, ms=7)
ax.axvline(0, color=MUTED, lw=0.8); ax.set_yticks(y, cats); ax.set_xlim(-1.5, 1.5)
ax.set_title("部門：全体との差（pt）", fontsize=10.5); ax.set_xlabel("売上の前年比の、全体との差（pt）")
ax = axs[1]
sk = sorted([k for k in rel if k.startswith("rel_store")], key=lambda k: rel[k][0])
xs = np.arange(len(sk))
for xi, k in zip(xs, sk):
    v, e, out = rel[k]; sid = int(k.split("_")[-1])
    ax.add_patch(plt.Rectangle((xi - 0.32, -e * 100), 0.64, 2 * e * 100, color=GRAY, alpha=0.3))
    ax.plot(xi, v * 100, "o", color=ORANGE if out else BLUE, ms=7, zorder=3)
    ax.plot(xi, MU.loc[T, k] * 100, "_", ms=11, mew=2, color=INK, zorder=4)
ax.set_xticks(xs, [k.split("_")[-1] for k in sk], fontsize=8); ax.set_xlabel("店番号（全体との差の小さい店から順に）")
ax.axhline(0, color=MUTED, lw=0.8); ax.set_ylabel("売上の前年比の、全体との差（pt）")
ax.set_title("店：1店・1か月の偶然の幅は ±3〜7pt", fontsize=10.5)
ax.plot([], [], "_", ms=10, mew=2, color=INK, label="設定上の本当の差（答え）"); ax.legend(fontsize=8, loc="upper left", frameon=False)
fig.suptitle("3月：部門の差はどれも幅の中。店は2つが幅の外に出たが、31項目見れば偶然だけでも平均3つは外に出る", x=0.01, ha="left", fontsize=11.5)
fig.tight_layout()
save(fig, "fig4_category_store_band.png")

# 図5：同じ型を、前年割れの6か月に当てる
E = pd.read_csv(RES / "E_down_months.csv").set_index("ym")
fig, ax = plt.subplots(figsize=(9.4, 4.4))
x = np.arange(len(E)); w = 0.6
parts = [("c_price", "一品単価", AQUA), ("c_items", "1回の買上点数", "#7fb3e6"), ("c_calendar", "暦の差", GRAY), ("c_receipts_adj", "客数（暦をそろえた）", ORANGE)]
pos = np.zeros(len(E)); neg = np.zeros(len(E))
for col, nm, c in parts:
    v = E[col].values * 100
    bot = np.where(v >= 0, pos, neg)
    ax.bar(x, v, bottom=bot, width=w, color=c, label=nm, zorder=3)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(x, E.sales_yoy * 100, "D", color=RED, ms=7, zorder=5, label="既存店売上の前年比")
ax.errorbar(x, E.sales_yoy * 100, yerr=E.band90_sales_yoy * 100, fmt="none", ecolor=RED, capsize=4, lw=1, zorder=5)
for xi, ym in zip(x, E.index):
    ax.text(xi, -9.3, f"{E.loc[ym, 'sales_yoy'] * 100:+.1f}%\n乱数20通りで前年割れ {E.loc[ym, 'share_seeds_negative'] * 100:.0f}%".replace("-", "−"), ha="center", fontsize=8, color=MUTED)
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_xticks(x, [f"{ym[:4]}年{int(ym[5:])}月" for ym in E.index]); ax.set_ylim(-10.3, 6.5)
ax.set_ylabel("売上の前年比への寄与（pt）"); ax.legend(fontsize=8.3, ncol=3, loc="upper center", frameon=False)
ax.set_title("前年割れの6か月はどれも「値上がり＞0、客数＜0」。暦の差が大きかったのは 2024年4月・7月と 2026年3月", loc="left", fontsize=11)
save(fig, "fig5_down_months_same_template.png")
print("figs done")

# 図6：1枚の報告（HTML を画像に）
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=1.6)
    pg.goto((ROOT / "reports" / "report_202603_onepage.html").as_uri()); pg.wait_for_timeout(500)
    h = pg.evaluate("document.body.scrollHeight")
    pg.locator("body").screenshot(path=str(FIG / "fig6_onepage_report.png")); br.close()
print("report height px", h)
