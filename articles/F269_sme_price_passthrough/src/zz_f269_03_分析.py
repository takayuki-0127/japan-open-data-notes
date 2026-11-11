"""F269 03 分析：仮説 H1〜H5、頑健性、問い直し。結果は results/ に保存。"""
import json, os
import numpy as np, pandas as pd
from scipy import stats
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(BASE, "data", "processed"); R = os.path.join(BASE, "results"); os.makedirs(R, exist_ok=True)
ind = pd.read_csv(os.path.join(P, "industry_passthrough.csv"))
neg = pd.read_csv(os.path.join(P, "industry_negotiation.csv"))
tier = pd.read_csv(os.path.join(P, "tier.csv"))
tk = pd.read_csv(os.path.join(P, "tankan.csv"))
out = {}
r2 = lambda x: None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 3)

# ---- 全体の推移（コスト全般・要素別）
tot = ind[ind.industry == "全体"].sort_values("round").set_index("round").drop(columns="industry")
tot["gap_material_labor"] = tot.material - tot.labor
tot.to_csv(os.path.join(R, "A_overall.csv"))
out["overall"] = {k: {c: r2(v) for c, v in row.items()} for k, row in tot.iterrows()}

# ---- H1 取引段階
tw = tier.pivot(index="round", columns="tier", values="rate")
gap = (tw["1次請け"] - tw["4次請け以上"])
mid = {"full": 100, "p7_9": 80, "p4_6": 50, "p1_3": 20, "zero": 0, "minus": -10}
tier["rate_mid"] = sum(tier[k] * v for k, v in mid.items()) / tier[list(mid)].sum(axis=1)
tier["zero_minus"] = tier.zero + tier.minus
tier.to_csv(os.path.join(R, "B_tier.csv"), index=False)
h1 = {"gap_by_round": {k: r2(v) for k, v in gap.items()},
      "rounds_ge5": int((gap >= 5).sum()), "n_rounds": int(len(gap)),
      "first": r2(gap.iloc[0]), "last": r2(gap.iloc[-1])}
h1["verdict"] = "支持" if (h1["rounds_ge5"] > len(gap) / 2 and gap.iloc[-1] < gap.iloc[0]) else "外れ"
# 頑健性1：指標を変える
def tg(col):
    w = tier.pivot(index="round", columns="tier", values=col)
    return (w["1次請け"] - w["4次請け以上"])
h1["robust"] = {"rate_midpoint_gap": {k: r2(v) for k, v in tg("rate_mid").items()},
                "full_share_gap": {k: r2(v) for k, v in tg("full").items()},
                "zero_minus_gap(4次以上−1次)": {k: r2(-v) for k, v in tg("zero_minus").items()},
                "midpoint_minus_published_mean": r2((tier.rate_mid - tier.rate).mean()),
                "midpoint_minus_published_maxabs": r2((tier.rate_mid - tier.rate).abs().max())}
out["H1"] = h1

# ---- H2 価格交渉：企業単位の表は公表されていない → 判定できない。代わりに業種の単位で見る（計画からのずれ）
rounds_n = ["2024-09", "2025-03", "2025-09", "2026-03"]
m = ind.merge(neg, on=["round", "industry"]); m = m[m.industry != "全体"]
h2 = {"verdict": "判定できない（交渉の有無別の転嫁率は公表されていない）", "industry_level": {}}
for rd in rounds_n:
    d = m[m["round"] == rd]
    sl = stats.linregress(d.score, d.total)
    h2["industry_level"][rd] = {"n": int(len(d)), "pearson": r2(sl.rvalue), "spearman": r2(stats.spearmanr(d.score, d.total)[0]),
                                "slope_pt_per_point": r2(sl.slope)}
# 業種ごとの変化どうし（業種の固定的な違いを除く）
a = m[m["round"] == "2024-09"].set_index("industry"); b = m[m["round"] == "2026-03"].set_index("industry")
cm = a.index.intersection(b.index)
dsc, dtt = (b.loc[cm, "score"] - a.loc[cm, "score"]), (b.loc[cm, "total"] - a.loc[cm, "total"])
sl = stats.linregress(dsc, dtt)
h2["within_change_2024-09_2026-03"] = {"n": int(len(cm)), "pearson": r2(sl.rvalue), "spearman": r2(stats.spearmanr(dsc, dtt)[0]),
                                       "slope_pt_per_point": r2(sl.slope), "p": r2(sl.pvalue)}
# 頑健性：新しく加わった業種・トラック運送を除く
d = m[(m["round"] == "2026-03") & (~m.industry.isin(["警備", "ビルメンテナンス", "トラック運送"]))]
h2["robust_2026-03_excl_new_and_truck"] = {"n": int(len(d)), "pearson": r2(stats.pearsonr(d.score, d.total)[0]),
                                           "slope": r2(stats.linregress(d.score, d.total).slope)}
m.to_csv(os.path.join(R, "C_industry_negotiation_passthrough.csv"), index=False)
out["H2"] = h2

# ---- H3 コストの種類
g = tot.gap_material_labor
out["H3"] = {"gap_by_round": {k: r2(v) for k, v in g.items()}, "mean_gap": r2(g.mean()),
             "labor_higher_rounds": int((g < 0).sum()), "n": int(len(g)),
             "verdict": "支持" if g.mean() >= 5 and (g < 0).sum() < len(g) / 2 else "外れ",
             "energy_minus_labor": {k: r2(v) for k, v in (tot.energy - tot.labor).items()}}

# ---- H4 業種の差 と 取引段階の差
h4 = {}
for rd in sorted(ind["round"].unique()):
    d = ind[(ind["round"] == rd) & (ind.industry != "全体")].total
    h4[rd] = {"n": int(len(d)), "range": r2(d.max() - d.min()), "p90_p10": r2(np.percentile(d, 90) - np.percentile(d, 10)),
              "iqr": r2(np.percentile(d, 75) - np.percentile(d, 25)), "sd": r2(d.std(ddof=1))}
last = "2026-03"
ratio = h4[last]["range"] / gap[last]
common = set.intersection(*[set(ind[ind["round"] == rd].industry) for rd in ind["round"].unique()]) - {"全体"}
dc = ind[(ind["round"] == last) & ind.industry.isin(common)].total
dnt = ind[(ind["round"] == last) & ~ind.industry.isin(["全体", "トラック運送"])].total
out["H4"] = {"by_round": h4, "tier_gap_last": r2(gap[last]), "ratio_range_to_tier": r2(ratio),
             "verdict": "支持" if ratio >= 2 else "外れ",
             "robust": {"ratio_p90p10_to_tier": r2(h4[last]["p90_p10"] / gap[last]),
                        "ratio_iqr_to_tier": r2(h4[last]["iqr"] / gap[last]),
                        "common_industries_n": len(common), "ratio_range_common": r2((dc.max() - dc.min()) / gap[last]),
                        "ratio_range_excl_truck": r2((dnt.max() - dnt.min()) / gap[last])}}

# ---- H5 短観（販売価格DI − 仕入価格DI）
t = tk.pivot_table(index=["year", "q", "size", "industry"], columns="item", values="di").reset_index()
t["spread"] = t["販売価格"] - t["仕入価格"]
t.to_csv(os.path.join(R, "D_tankan_spread.csv"), index=False)
def h5(indus):
    x = t[t.industry == indus]
    w = x.pivot_table(index=["year", "q"], columns="size", values="spread")
    w["sme_minus_large"] = w["中小企業"] - w["大企業"]
    yr = w.groupby(level=0).mean()
    since = w.loc[2021:]
    early, late = w.loc[2021:2022, "sme_minus_large"].mean(), w.loc[2025:2026, "sme_minus_large"].mean()
    return {"mean_sme_minus_large_since2021": r2(since.sme_minus_large.mean()),
            "early_2021_22": r2(early), "late_2025_26": r2(late),
            "pre_2010_19": r2(w.loc[2010:2019, "sme_minus_large"].mean()),
            "by_year": {int(k): r2(v) for k, v in yr.sme_minus_large.items()},
            "spread_by_year_sme": {int(k): r2(v) for k, v in yr["中小企業"].items()},
            "spread_by_year_large": {int(k): r2(v) for k, v in yr["大企業"].items()},
            "supported": bool(since.sme_minus_large.mean() < 0 and abs(late) < abs(early))}
out["H5"] = {"全産業": h5("全産業"), "製造業": h5("製造業"), "非製造業": h5("非製造業")}
out["H5"]["verdict"] = "支持" if out["H5"]["全産業"]["supported"] else "外れ"

# ---- 問い直し：転嫁率の低い業種は追いついているか（共通の業種で）
cw = ind[ind.industry.isin(common)].pivot(index="industry", columns="round", values="total")
rs = sorted(cw.columns)
x0, x1 = cw[rs[0]], cw[rs[-1]]
b = stats.linregress(x0, x1 - x0)
sd = {rd: r2(cw[rd].std(ddof=1)) for rd in rs}
rank_rho = stats.spearmanr(x0, x1)[0]
low = x0 <= x0.quantile(1 / 3); high = x0 >= x0.quantile(2 / 3)
# 2024-09 から（4回の書式がそろった期間）
cw2 = ind[ind.industry.isin(set(ind[ind['round'] == '2024-09'].industry) & set(ind[ind['round'] == '2026-03'].industry) - {"全体"})].pivot(index="industry", columns="round", values="total")
y0, y1 = cw2["2024-09"], cw2["2026-03"]; b2 = stats.linregress(y0, y1 - y0)
out["reask"] = {"common_n": len(common), "first": rs[0], "last": rs[-1],
                "beta_slope": r2(b.slope), "beta_p": r2(b.pvalue), "beta_r": r2(b.rvalue),
                "mean_change_low_third": r2((x1 - x0)[low].mean()), "mean_change_high_third": r2((x1 - x0)[high].mean()),
                "sd_by_round": sd, "rank_spearman_first_last": r2(rank_rho),
                "since_2024-09": {"n": int(len(cw2)), "beta_slope": r2(b2.slope), "beta_p": r2(b2.pvalue),
                                  "sd_2024-09": r2(y0.std(ddof=1)), "sd_2026-03": r2(y1.std(ddof=1)),
                                  "rank_spearman": r2(stats.spearmanr(y0, y1)[0])}}
cw.to_csv(os.path.join(R, "E_industry_wide.csv"))
# 平均への回帰を避ける確かめ：2023年3月の値で、重ならない期間（2023年9月→2026年3月）の上昇を説明する
b3 = stats.linregress(x0, cw["2026-03"] - cw["2023-09"])
out["reask"]["nonoverlap_2023-03_level_vs_2023-09_to_2026-03"] = {"beta_slope": r2(b3.slope), "beta_p": r2(b3.pvalue), "beta_r": r2(b3.rvalue)}
# 置き換え：平均への回帰の目安（同じ業種の1回あたりの揺れ）
dd = cw.diff(axis=1).iloc[:, 1:]
out["reask"]["mean_abs_round_change"] = r2(dd.abs().stack().mean())

json.dump(out, open(os.path.join(R, "main.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: out[k] for k in ["H1", "H3", "H4"]}, ensure_ascii=False, indent=1)[:3000])
print(json.dumps(out["H2"], ensure_ascii=False, indent=1))
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("by_year", "spread_by_year_sme", "spread_by_year_large")} if isinstance(v, dict) else v for k, v in out["H5"].items()}, ensure_ascii=False, indent=1))
print(json.dumps(out["reask"], ensure_ascii=False, indent=1))
