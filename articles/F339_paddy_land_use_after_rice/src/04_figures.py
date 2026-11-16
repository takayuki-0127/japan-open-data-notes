"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
F = ROOT / "figures"
F.mkdir(exist_ok=True)

for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                     "ytick.color": "#52514e", "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "svg.hashsalt": "f339", "path.simplify": False})
C_RICE, C_NON, C_UN = "#2a78d6", "#eb6834", "#1baf7a"
INK2 = "#52514e"
SRC = "出典：農林水産省「作物統計調査（面積調査）」耕地及び作付面積統計（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))

# ---- 図1：田本地の夏の使われ方の推移 --------------------------------------------
sh = pd.read_csv(R / "summer_use_share.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8.6, 5.0))
y = sh.index.values
parts = [sh["rice_field"].values / 1e4, sh["nonrice_only"].values / 1e4, sh["unplanted"].values / 1e4]
ax.stackplot(y, parts, colors=[C_RICE, C_NON, C_UN], edgecolor="#fcfcfb", linewidth=1.0)
ax.plot(y, sh["paddy"].values / 1e4, color="#0b0b0b", lw=1.6)
ax.set_xlim(1966, 2025)
ax.set_ylim(0, 340)
ax.set_ylabel("面積（万ha）")
ax.grid(axis="y", color="#e4e3df", lw=0.8)
ax.set_axisbelow(True)
ax.text(1990, 105, "水稲を作付けした田", color="white", fontsize=11, ha="center")
ax.text(2013, 182, "水稲以外の作物だけの田", color="#0b0b0b", fontsize=10, ha="center")
ax.text(2013, 214, "夏の間ずっと作付けしない田", color="#0b0b0b", fontsize=10, ha="center", va="center")
ax.text(1967, 330, f"田本地（あぜを除く田の面積）：{main['paddy_1969_ha']/1e4:.0f}万ha（1969年）", fontsize=9.5, color="#0b0b0b", va="top")
ax.text(2024.5, 226, f"{main['paddy_2025_ha']/1e4:.0f}万ha\n（2025年）", fontsize=9.5, ha="right", va="bottom", color="#0b0b0b")
ax.set_title("田んぼは3分の2に減り、残った田の3割は夏に稲を作っていない", loc="left", fontsize=12.5)
fig.text(0.01, 0.01, "注：夏期全期はおおむね水稲の栽培期間。水稲には青刈り稲（WCS用稲など）を含む。1973年以前は沖縄県を含まない。\n" + SRC,
         fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.17)
save(fig, "fig1_summer_paddy_use.png")

# ---- 図2：減少の分解と、田がなくなった理由 -------------------------------------
m = main["decomposition"]["main_1969_2025"]
ab = main["abandon"]["cum"]
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.8), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
labs = ["田本地そのものが\n減った", "田のまま、稲以外の\n作物だけになった", "田のまま、夏に\n作付けしなくなった"]
vals = [m["paddy_loss_ha"] / 1e4, m["nonrice_increase_ha"] / 1e4, m["unplanted_increase_ha"] / 1e4]
pcts = [m["share_paddy_loss_pct"], m["share_nonrice_pct"], m["share_unplanted_pct"]]
yy = np.arange(3)[::-1]
ax.barh(yy, vals, color=[INK2, C_NON, C_UN], height=0.6)
for yi, v, p in zip(yy, vals, pcts):
    ax.text(v + 2, yi, f"{v:.0f}万ha（{p:.0f}%）", va="center", fontsize=10)
ax.set_yticks(yy, labs)
ax.set_xlim(0, 140)
ax.set_xlabel("万ha")
ax.set_title(f"水稲作付田の減少 {m['rice_decline_ha']/1e4:.0f}万ha の内訳\n（1969→2025年）", loc="left", fontsize=11)
ax.grid(axis="x", color="#e4e3df", lw=0.8); ax.set_axisbelow(True)

ax = axes[1]
items = [("宅地など", ab["ab_housing"]), ("田畑転換（畑にした）", ab["ab_to_upland"]), ("道路・鉄道", ab["ab_road"]),
         ("工場用地", ab["ab_factory"]), ("植林", ab["ab_forest"]), ("農林道など", ab["ab_farmroad"]),
         ("自然災害", ab["ab_disaster"]), ("その他（荒廃農地を含む）", ab["ab_other"])]
yy = np.arange(len(items))[::-1]
ax.barh(yy, [v / 1e4 for _, v in items], color=INK2, height=0.6)
tot = ab["ab_total"]
for yi, (n, v) in zip(yy, items):
    ax.text(v / 1e4 + 0.8, yi, f"{v/1e4:.1f}万ha（{100*v/tot:.0f}%）", va="center", fontsize=9.5)
ax.set_yticks(yy, [n for n, _ in items])
ax.set_xlim(0, 52)
ax.set_xlabel("万ha（1970〜2016年の累計）")
ax.set_title(f"田がなくなった理由\n（1970〜2016年の累計 {tot/1e4:.0f}万ha）", loc="left", fontsize=11)
ax.grid(axis="x", color="#e4e3df", lw=0.8); ax.set_axisbelow(True)
fig.text(0.01, 0.01, "注：右は要因別が調べられている1970〜2016年。2017年からは荒廃農地以外の要因を調べていない。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.15, right=0.98, top=0.86, bottom=0.2, wspace=0.62)
save(fig, "fig2_decomposition.png")

# ---- 図3：地域別（北から南） ------------------------------------------------------
reg = pd.read_csv(R / "region_shares.csv")
order = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
q = reg[reg.level == "地域"].set_index(["name", "year"])
fig, ax = plt.subplots(figsize=(8.8, 6.0))
ypos, ylabels = [], []
k = 0
for n in order:
    for yr in (2003, 2025):
        yv = -(k * 1.0 + (0.42 if yr == 2025 else 0))
        r_ = q.loc[(n, yr)]
        a, b, c = r_["rice_pct"], r_["nonrice_pct"], r_["unplanted_pct"]
        ax.barh(yv, a, color=C_RICE, height=0.38, edgecolor="#fcfcfb", lw=1)
        ax.barh(yv, b, left=a, color=C_NON, height=0.38, edgecolor="#fcfcfb", lw=1)
        ax.barh(yv, c, left=a + b, color=C_UN, height=0.38, edgecolor="#fcfcfb", lw=1)
        ax.text(101, yv, f"{c:.0f}%", va="center", fontsize=8.5, color="#0b0b0b")
        ypos.append(yv); ylabels.append(f"{n}  {yr}" if yr == 2003 else "2025")
    k += 1
ax.set_yticks(ypos, ylabels, fontsize=8.8)
ax.set_xlim(0, 108)
ax.set_xlabel("田本地に占める割合（%）")
ax.text(101, 0.55, "不作付", fontsize=8.5, color=INK2)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C_RICE, label="水稲を作付け"), Patch(color=C_NON, label="水稲以外の作物だけ"),
                   Patch(color=C_UN, label="夏に作付けしない")], loc="upper center", bbox_to_anchor=(0.45, 1.075), ncol=3, frameon=False, fontsize=9)
ax.set_title("夏に作付けしない田は、近畿・中国・四国で2割前後（2003年と2025年、北から順に）", loc="left", fontsize=11.5, pad=26)
fig.text(0.01, 0.01, "注：沖縄は田本地が700ha 弱と小さく、割合が動きやすい。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.16, right=0.97, top=0.88, bottom=0.12)
save(fig, "fig3_region_shares.png")

# ---- 図4：問い直し（都道府県）-------------------------------------------------------
pf = pd.read_csv(R / "pref_shares.csv", index_col=0)
q1 = req["q1"]["main_2003_2025"]
fig, ax = plt.subplots(figsize=(7.6, 5.2))
ax.scatter(pf["unplanted_pct_2003"], pf["paddy_change_pct"], s=40, color=C_RICE, edgecolor="#fcfcfb", lw=1.5, zorder=3)
x = pf["unplanted_pct_2003"].values; yv = pf["paddy_change_pct"].values
b1, b0 = np.polyfit(x, yv, 1)
xs = np.linspace(x.min(), x.max(), 10)
ax.plot(xs, b0 + b1 * xs, color=INK2, lw=1.5, ls="--")
ax.set_xlabel("2003年に夏の間作付けしなかった田の割合（%）")
ax.set_ylabel("田本地の増減（2003→2025年、%）")
ax.grid(color="#e4e3df", lw=0.8); ax.set_axisbelow(True)
ax.text(0.98, 0.95, f"47都道府県　順位相関 {q1['spearman_rho']:.2f}\n不作付が10ポイント多いと、田本地の減り方は\n約{abs(q1['ols_slope_unplanted'])*10:.0f}ポイント大きい（稲以外の割合を調整）",
        transform=ax.transAxes, ha="right", va="top", fontsize=9, color="#0b0b0b",
        bbox=dict(facecolor="#fcfcfb", edgecolor="#e4e3df"))
ax.set_title("夏に作付けしない田が多かった都道府県ほど、その後に田が減った", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：1点が1都道府県。破線は単純な回帰直線。相関で、原因を示すものではない。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.12, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig4_unplanted_then_loss.png")
print("figures done")
