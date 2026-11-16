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
SRC = "出典：日本銀行「企業向けサービス価格指数（2020年基準）」をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
m = pd.read_csv(ROOT / "data" / "monthly.csv", index_col="ym").loc[:202609]
t = pd.to_datetime([f"{str(i)[:4]}-{str(i)[4:]}-01" for i in m.index]); m.index = t
yoy = (m / m.shift(12) - 1) * 100


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


def shade(ax):
    ax.axvline(pd.Timestamp("2024-04-01"), color=INK2, lw=0.9, ls=":")


# 図1：前年比
fig, ax = plt.subplots(figsize=(8.8, 5.0))
s = yoy.loc["2016-01":]
ax.plot(s.index, s.road, color=C[0], lw=2.2, label="道路貨物輸送")
ax.plot(s.index, s.all_ex_intl, color=INK2, lw=1.6, ls="--", label="総平均（除く国際運輸）")
shade(ax)
ax.text(pd.Timestamp("2024-05-01"), 6.3, "2024年4月\n時間外労働の上限", fontsize=8.5, color=INK2, va="top")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylim(-2, 7); ax.set_ylabel("前年同月比（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title(f"道路貨物輸送の前年比は2024年度平均{main['fy_road']['2024']:.1f}%、2023年度の{main['fy_road']['2023']:.1f}%から上がった", loc="left", fontsize=11.5)
foot(fig, "注：2016年1月〜2026年9月。直近の月は速報値。")
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.13)
save(fig, "fig1_road_freight_yoy.png")

# 図2：相対価格
rel = pd.read_csv(R / "road_relative_price.csv", index_col="ym")
rel.index = pd.to_datetime([f"{str(i)[:4]}-{str(i)[4:]}-01" for i in rel.index])
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(rel.index, rel.road_relative, color=C[0], lw=2.2)
for d, lab in [("2017-03-01", "201703"), ("2019-03-01", "201903"), ("2023-03-01", "202303"), ("2025-03-01", "202503")]:
    v = req[f"rel_{lab}"]
    ax.plot(pd.Timestamp(d), v, "o", color=C[1], ms=5)
    ax.text(pd.Timestamp(d), v - 0.45, f"{lab[:4]}年{int(lab[4:])}月\n{v:.1f}", ha="center", va="top", fontsize=8.3, color=INK2)
shade(ax)
ax.set_ylim(90, 103); ax.set_ylabel("道路貨物輸送 ÷ 総平均（除く国際運輸）×100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"ほかのサービスと比べた運賃は、2017→19年に{req['wave1_rel_change']:+.1f}、2023→25年は{req['wave2_rel_change']:+.1f}", loc="left", fontsize=11.5)
foot(fig, "注：どちらも2020年=100の指数の比。上がれば、ほかのサービスより速く値上がりしたことを表す。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_relative_price.png")

# 図3：品目別の上昇率（2023年3月→2025年3月）
it = main["item_2303_2503"]
order = [("parcel", "宅配便・メール便"), ("truck_misc", "自動車貨物（軽・雑工業品）"), ("truck_food", "自動車貨物（農林水産・食料）"),
         ("truck_metal", "自動車貨物（金属機械）"), ("truck_chem", "自動車貨物（鉱産品・化学）"), ("road", "道路貨物輸送（全体）"),
         ("warehouse", "倉庫"), ("rail", "鉄道貨物輸送"), ("coastal", "内航貨物輸送"), ("all_ex_intl", "総平均（除く国際運輸）")]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ys = np.arange(len(order))[::-1]
for y, (k, lab) in zip(ys, order):
    col = C[0] if k.startswith("truck") or k in ("parcel", "road") else (INK2 if k == "all_ex_intl" else C[2])
    ax.barh(y, it[k], color=col, height=0.62)
    ax.text(it[k] + 0.15, y, f"{it[k]:.1f}", va="center", fontsize=9)
ax.set_yticks(ys); ax.set_yticklabels([lab for _, lab in order])
ax.axvline(it["all_ex_intl"], color=INK2, lw=0.8, ls=":")
ax.set_xlim(0, 10); ax.set_xlabel("2023年3月→2025年3月の上昇率（%）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2年間で道路貨物輸送は4.7%、サービス全体は6.2%上がった", loc="left", fontsize=11.5)
foot(fig, "注：並びは、道路貨物輸送の品目→ほかの物流→サービス全体の順。点線はサービス全体の上昇率。")
fig.subplots_adjust(left=0.3, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig3_change_by_item.png")

# 図4：4月の前月比
apr = pd.read_csv(R / "april_mom.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = np.arange(len(apr)); w = 0.38
ax.bar(x - w / 2, apr.road, width=w, color=C[0], label="道路貨物輸送")
ax.bar(x + w / 2, apr.all_ex_intl, width=w, color="#a9a8a3", label="総平均（除く国際運輸）")
for xi, v in zip(x - w / 2, apr.road):
    ax.text(xi, v + (0.05 if v >= 0 else -0.05), f"{v:.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.3)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{y}" for y in apr.index])
ax.set_ylabel("4月の前月比（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title(f"4月の値上げは2016〜23年平均{main['apr_road_avg_2016_2023']:.2f}%から、2024年{main['apr_road_2024']:.2f}%、2026年{main['apr_road_2026']:.2f}%へ", loc="left", fontsize=11.5)
foot(fig, "注：各年4月の指数 ÷ 3月の指数 − 1。4月に上がりやすいのは、年度の初めに運賃を改定する契約が多いためとみられる（推測）。")
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_april_jumps.png")
print("ok")
