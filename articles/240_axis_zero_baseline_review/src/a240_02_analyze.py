"""data/ の表から集計と図を作る（clone は不要）"""
import os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import GROUPS

here = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(here, "..")
cs = pd.read_csv(f"{B}/data/code_scan.csv")
fl = pd.read_csv(f"{B}/data/bar_with_positive_ylim.csv")
ck = pd.read_csv(f"{B}/data/bar_flags_checked.csv")
cf = pd.read_csv(f"{B}/data/a227_home_coffee_grams_price.csv")
sq = pd.read_csv(f"{B}/data/f244_b9_december_sales.csv")


def lie(v0, v1, base):
    """棒グラフの lie factor：見える変化 ÷ データの変化（F70 と同じ定義）"""
    seen = ((v1 - base) - (v0 - base)) / (v0 - base)
    real = (v1 - v0) / v0
    return seen / real

# 例1：コーヒー（227）2019→2025 の購入量
g19, g25 = cf.set_index("year").grams[[2019, 2025]]
lo1 = 2400
ex1 = {"2019_g": g19, "2025_g": g25, "change_pct": round((g25 / g19 - 1) * 100, 2), "cut_lower": lo1,
       "lie_factor_cut": round(lie(g19, g25, lo1), 1), "height_ratio_cut": round((g25 - lo1) / (g19 - lo1), 3)}
# 例2：F244 の12月の売上（BETWEEN と >= <）
bad, good = sq.value_yen / 1e6
lo2 = 55
ex2 = {"bad_mil": round(bad, 2), "good_mil": round(good, 2), "gap_pct": round((bad / good - 1) * 100, 2), "cut_lower": lo2,
       "lie_factor_cut": round(lie(good, bad, lo2), 1), "height_ratio_cut": round((bad - lo2) / (good - lo2), 3)}

tot = cs[["plot_files", "bar", "barh", "line", "ylim", "ylim_zero", "ylim_neg", "ylim_pos", "ylim_var"]].sum().astype(int).to_dict()
summary = {"commit": "996936a", "folders": int(len(cs)), "folders_with_plots": int((cs.plot_files > 0).sum()), "totals": tot,
           "bar_files_with_positive_ylim_flags": int(len(fl)), "checked_candidates": int(len(ck)),
           "checked_by_class": ck.class_name.value_counts().to_dict(),
           "articles_with_cut_bars": sorted(ck[ck["class"] == "A"].folder.unique().tolist()),
           "example_coffee_227": ex1, "example_sql_F244": ex2}
json.dump(summary, open(f"{B}/results/summary.json", "w"), ensure_ascii=False, indent=1, default=int)

# 図1：同じ数字を、0から始めた棒と、下端を切った棒で
fig, ax = plt.subplots(1, 4, figsize=(11, 3.9), gridspec_kw=dict(wspace=0.55))
yrs = cf.year.astype(str)
for a, lo, t in [(ax[0], 0, "0から"), (ax[1], lo1, f"{lo1:,}gから")]:
    a.bar(yrs, cf.grams, color="#8c6d4f", width=0.7)
    a.set_ylim(lo, 2900); a.set_title(f"家で淹れるコーヒー（227）\n縦軸を{t}", fontsize=9.5)
    a.tick_params(axis="x", rotation=60, labelsize=8); a.set_ylabel("1世帯の年間購入量（g）", fontsize=8.5)
lab = ["BETWEEN", ">= と <"]
for a, lo, t in [(ax[2], 0, "0から"), (ax[3], lo2, f"{lo2}から（元の図）")]:
    a.bar(lab, [bad, good], color=["#c0392b", "#2e86c1"], width=0.6)
    for i, v in enumerate([bad, good]): a.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5)
    a.set_ylim(lo, 67); a.set_title(f"SQL の期間の区切り（F244）\n縦軸を{t}", fontsize=9.5)
    a.set_ylabel("12月の売上（百万円）", fontsize=8.5); a.tick_params(axis="x", labelsize=8.5)
for a in ax: a.spines[["top", "right"]].set_visible(False)
fig.suptitle(f"同じ数字でも、下端を切ると差が大きく見える（コーヒー −{abs(ex1['change_pct']):.1f}% が約{ex1['lie_factor_cut']:.0f}倍、"
             f"売上 −{abs(ex2['gap_pct']):.1f}% が約{ex2['lie_factor_cut']:.0f}倍に）", fontsize=10.5, y=1.02)
fig.savefig(f"{B}/figures/a240_replot.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図2：シリーズのコードで、縦軸の下端をどう決めていたか
k = ["ylim_zero", "ylim_neg", "ylim_pos", "ylim_var"]
nm = ["0 から", "0 より下から\n（0 を含む）", "0 より上から\n（下端を切る）", "変数で指定"]
fig, ax = plt.subplots(figsize=(7.5, 3.8))
v = [tot[x] for x in k]
ax.bar(nm, v, color=["#4C72B0", "#8da0cb", "#DD8452", "#bbbbbb"])
for i, x in enumerate(v): ax.text(i, x + 5, f"{x}", ha="center", fontsize=10)
ax.set_ylabel("縦軸の範囲を指定した回数")
ax.set_title(f"記事のコードで縦軸の範囲を指定した {tot['ylim']} 回の内訳（{summary['folders_with_plots']} 本の記事）\n"
             f"指定しないときは matplotlib の自動（棒は0から、折れ線はデータの近くから）", fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{B}/figures/a240_ylim_counts.png", dpi=150); plt.close(fig)

# 図3：棒グラフで下端を0より上にしていた候補を、コードを読んで分けた結果
vc = ck.class_name.value_counts()
order = ["下端を切った縦の棒", "100や1などを基準にした棒", "対数目盛", "二軸のもう一方の軸", "コードだけでは判断できない"]
vc = vc.reindex(order).fillna(0).astype(int)
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.barh(vc.index[::-1], vc.values[::-1], color=["#bbbbbb", "#8da0cb", "#8da0cb", "#8da0cb", "#DD8452"])
for i, x in enumerate(vc.values[::-1]): ax.text(x + 0.2, i, str(x), va="center", fontsize=10)
ax.set_xlabel("か所")
ax.set_title(f"縦の棒と「0より上の下端」が同じ図にあった {len(ck)} か所を、コードを読んで分けた\n"
             f"下端を切った棒は {vc.iloc[0]} か所・{len(summary['articles_with_cut_bars'])} 本の記事", fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{B}/figures/a240_bar_check.png", dpi=150); plt.close(fig)
print(json.dumps(summary, ensure_ascii=False, default=int)[:1500])
