"""04 図：figures/ に5枚の PNG を出す。"""
import json, logging, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

warnings.filterwarnings("ignore"); logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#3aa07a", "#7a5bd6"
SRC = "出典：国土交通省「宅配便等取扱個数の調査」、総務省「家計消費状況調査」「国勢調査」「人口推計」、日本郵便「引受物数」を加工して作成"
S = json.load(open(RES / "summary.json"))
d = pd.read_csv(RES / "fy_panel_with_splices.csv")


def foot(fig, extra="", y=-0.02):
    fig.text(0.01, y, (extra + "\n" if extra else "") + SRC, fontsize=7.5, color=GRAY, ha="left", va="top")


# 1. 長い推移（FY2004=100、対数目盛）
fig, ax = plt.subplots(figsize=(9, 5.4))
base = d.iloc[0]
for col, lab, c, ls in [("lN_spl", "ネット通販への支出（二人以上の世帯、定義の切れ目をつないだ値）", ORANGE, "-"),
                        ("net_share", "ネットで注文した世帯の割合", ORANGE, "--"),
                        ("parcels_adj_mil", "宅配便の取扱個数", BLUE, "-"),
                        ("one_person_thou", "単独世帯（国勢調査を補間）", GREEN, "-"),
                        ("pop_total", "総人口", GRAY, "-")]:
    v = np.exp(d[col] - d[col].iloc[0]) * 100 if col == "lN_spl" else d[col] / base[col] * 100
    ax.plot(d.fy, v, color=c, ls=ls, lw=2.4 if col == "parcels_adj_mil" else 1.6, label=lab)
    off = {"parcels_adj_mil": 0.93, "one_person_thou": 1.06}.get(col, 1.0)
    ax.text(2024.3, v.iloc[-1] * off, f"{v.iloc[-1]:,.0f}", color=c, va="center", fontsize=9)
ax.set_yscale("log"); ax.set_yticks([50, 100, 200, 500, 1000, 1500]); ax.set_yticklabels(["50", "100", "200", "500", "1,000", "1,500"])
ax.set_xlim(2003.5, 2025.5); ax.set_ylabel("2004年度＝100（対数目盛）"); ax.set_xticks(range(2004, 2025, 4)); ax.set_xlabel("年度")
ax.set_title("宅配便は1.6倍、ネット通販への支出は13倍（2004〜2024年度）", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
foot(fig, "注：宅配便は2003〜2006年度にゆうパックを足した値。ネット支出は2015年に品目の定義が変わったため、2014・2015年度の伸びを前後3年の平均の伸びで置きかえてつないだ")
fig.savefig(FIG / "f185_1_long_run.png"); plt.close(fig)

# 2. 前年度比の散布図
dd = pd.DataFrame({"fy": d.fy, "dP": np.log(d.parcels_adj_mil).diff() * 100, "dN": d.lN.diff() * 100, "dD": d.D.diff()}).dropna()
fig, ax = plt.subplots(figsize=(8.4, 5.6))
brk = dd.dD > 0
ax.scatter(dd.dN[~brk], dd.dP[~brk], color=BLUE, s=46, zorder=3)
ax.scatter(dd.dN[brk], dd.dP[brk], color=GRAY, s=46, marker="s", zorder=3, label="定義が変わった年度（FY2014・2015）")
for r in dd.itertuples():
    ax.annotate(str(r.fy), (r.dN, r.dP), xytext=(4, 3), textcoords="offset points", fontsize=8, color=ORANGE if r.fy == 2020 else INK)
b, c0 = S["diff_main"]["beta_net"], S["diff_main"]["const"]
xs = np.linspace(0, 27, 50); ax.plot(xs, (c0 + b * xs / 100) * 100, color=ORANGE, lw=1.6, label=f"当てはめた線（弾力性 {b:.2f}、R² {S['diff_main']['r2']:.2f}）")
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xlabel("ネット通販への支出の伸び（前年度比、%・対数差）"); ax.set_ylabel("宅配便の個数の伸び（前年度比、%・対数差）")
ax.set_title("年ごとの伸びは、ほとんどそろっていない", loc="left"); ax.legend(frameon=False, fontsize=9, loc="upper left")
foot(fig, f"注：FY2005〜2024 の20年度。並べ替え検定で p={S['perm']['p_two_sided']:.2f}。FY2020 を除くと弾力性は {S['loo']['beta_min']:.2f}")
fig.savefig(FIG / "f185_2_growth_scatter.png"); plt.close(fig)

# 3. 水準と変化の説明力
lv = pd.read_csv(RES / "level_models.csv"); cb = pd.read_csv(RES / "diff_combinations.csv")
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.8), gridspec_kw={"width_ratios": [1, 1.25]})
lv_show = lv.set_index("model").loc[["ネット支出だけ", "トレンドだけ", "単独世帯＋人口だけ", "注文世帯の割合だけ"]]
axs[0].barh(lv_show.index[::-1], lv_show.r2[::-1], color=[ORANGE, GREEN, GRAY, ORANGE])
for i, v in enumerate(lv_show.r2[::-1]): axs[0].text(v - 0.01, i, f"{v:.2f}", va="center", ha="right", color="white", fontsize=10)
axs[0].set_xlim(0, 1); axs[0].set_title("水準（対数）の R²", loc="left"); axs[0].set_xlabel("R²")
show = cb[cb.k <= 2].sort_values("r2")
cols = [ORANGE if ("ネット" in v or "注文" in v) else GRAY for v in show.vars]
axs[1].barh(show.vars, show.r2, color=cols)
for i, v in enumerate(show.r2): axs[1].text(v + 0.005, i, f"{v:.2f}", va="center", fontsize=9)
axs[1].set_xlim(0, 1); axs[1].set_title("前年度比の R²（変数の組み合わせ）", loc="left"); axs[1].set_xlabel("R²")
fig.suptitle("水準ではどれも9割以上「説明」するが、前年度比では2割前後まで", x=0.01, ha="left", fontsize=13)
fig.tight_layout(); foot(fig, "注：FY2004〜2024。ネット支出を使うモデルには、定義の切れ目のダミー（その年度に新しい定義の月が占める割合）を入れている")
fig.savefig(FIG / "f185_3_r2_levels_vs_changes.png"); plt.close(fig)

# 4. 前半で学んで後半を当てる
o = pd.read_csv(RES / "oos_2016_2024.csv")
fig, ax = plt.subplots(figsize=(8.4, 4.8))
o = pd.concat([pd.DataFrame({"fy": [2015], "actual": [0.0], "pred": [0.0]}), o], ignore_index=True)
ax.plot(o.fy, (np.exp(o.actual.cumsum()) - 1) * 100, color=BLUE, lw=2.4, marker="o", label="実際")
ax.plot(o.fy, (np.exp(o.pred.cumsum()) - 1) * 100, color=ORANGE, lw=1.8, marker="o", label="ネット支出の伸びから予測（FY2005〜2013 で推定）")
cst = S["oos"]["mean_train"]
ax.plot(o.fy, (np.exp(np.arange(0, len(o)) * cst) - 1) * 100, color=GRAY, lw=1.4, ls="--", label="前半の平均と同じだけ毎年伸びるとした場合")
ax.set_ylabel("FY2015 からの累積の伸び（%）"); ax.set_title("前半の関係では、後半の伸びの半分しか当たらない", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper left")
foot(fig, f"注：実際 +{S['oos']['actual_growth_pct']:.1f}%、予測 +{S['oos']['pred_growth_pct']:.1f}%、毎年同じ伸び +{S['oos']['const_only_growth_pct']:.1f}%（FY2015→2024）")
fig.savefig(FIG / "f185_4_out_of_sample.png"); plt.close(fig)

# 5. 頑健性
r = pd.read_csv(RES / "robustness.csv"); r = r[~r.check.str.startswith("1年抜き")].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9.6, 6.2))
y = np.arange(len(r))[::-1]
col = [ORANGE if p < 0.05 else BLUE for p in r.p]
ax.errorbar(r.beta, y, xerr=1.96 * r.se, fmt="none", ecolor=GRAY, elinewidth=1.2)
ax.scatter(r.beta, y, color=col, zorder=3, s=36)
for yi, rr in zip(y, r.itertuples()): ax.text(1.05, yi, f"R² {rr.r2:.2f}・n={rr.n}", va="center", fontsize=8, color=GRAY)
ax.set_yticks(y); ax.set_yticklabels(r.check, fontsize=8.5); ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlim(-0.5, 1.0); ax.set_xlabel("宅配便の伸びの弾力性（ネット側が1%伸びたとき、宅配便が何%伸びるか）")
ax.set_title("条件を変えると、0.0〜0.3 の間で動く", loc="left")
foot(fig, "注：線は95%区間（HAC 標準誤差）。オレンジは p<0.05。「モノだけ」は旅行・チケット・保険・出前・デジタル配信を除いた品目")
fig.savefig(FIG / "f185_5_robustness.png"); plt.close(fig)
print("ok")
