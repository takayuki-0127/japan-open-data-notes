"""欠損法人の割合：全体・規模別・営業収入での重みづけ・景気との関係・業種別・要因の分解。
出力：results/*.csv、results/main.json"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
t = pd.read_csv(ROOT / "data" / "t2_long.csv")
off = pd.read_csv(ROOT / "data" / "official_table6.csv")
IND_ORDER = ["農林水産業", "鉱業", "建設業", "繊維工業", "化学工業", "鉄鋼金属工業", "機械工業", "食料品製造業",
             "出版印刷業", "その他の製造業", "卸売業", "小売業", "料理飲食旅館業", "金融保険業", "不動産業",
             "運輸通信公益事業", "サービス業"]
GROUP_KINDS = ["renketsu", "tsusan", "tsusan_large", "tsusan_small"]
r1 = lambda x: float(round(x, 1))
r2 = lambda x: float(round(x, 2))
r3 = lambda x: float(round(x, 3))

# ---- 1. 全体（連結・通算を含む合計行）と、連結・通算を除く（資本金階級の合計）
tot = t[(t.industry == "合計") & (t.kind == "sum")].pivot_table(index="year", columns="section", values=["n_corp", "n_period", "sales"], aggfunc="sum")
cls = t[(t.industry == "合計") & (t.kind == "class")].groupby(["year", "section"])[["n_corp", "n_period", "sales"]].sum().unstack("section")
grp = t[(t.industry == "合計") & (t.kind.isin(GROUP_KINDS))].groupby(["year", "section"])[["n_corp"]].sum().unstack("section")
yr = pd.DataFrame(index=tot.index)
yr["n_total"] = tot[("n_corp", "total")]
yr["n_loss"] = tot[("n_corp", "loss")]
yr["n_profit"] = tot[("n_corp", "profit")]
yr["share_all"] = yr.n_loss / yr.n_total * 100
yr["share_excl_group"] = cls[("n_corp", "loss")] / cls[("n_corp", "total")] * 100
yr["share_group_only"] = grp[("n_corp", "loss")] / grp[("n_corp", "total")] * 100
yr["share_period"] = tot[("n_period", "loss")] / tot[("n_period", "total")] * 100
yr["sales_total_oku"] = tot[("sales", "total")] / 100  # 百万円→億円
yr["sales_share_loss"] = tot[("sales", "loss")] / tot[("sales", "total")] * 100
yr["sales_share_loss_excl_group"] = cls[("sales", "loss")] / cls[("sales", "total")] * 100
yr["sales_growth_pct"] = yr.sales_total_oku.pct_change() * 100
yr["d_share"] = yr.share_all.diff()
yr["ratio_sales_to_count"] = yr.sales_share_loss / yr.share_all
o = off[off.basis == "年度分"].drop_duplicates("fiscal_year", keep="last").set_index("fiscal_year")
yr["official_pct"] = o.loss_share_pct.reindex(yr.index)
yr["diff_vs_official"] = yr.share_all.round(1) - yr.official_pct
yr.round(4).to_csv(RES / "yearly.csv")

# ---- 2. 規模（2011年度分以降：区切りが「以下・超」でそろう）
c = t[(t.industry == "合計") & (t.kind == "class")].copy()
def band(lb):
    return "1,000万円以下" if lb < 10 else ("1,000万円超1億円以下" if lb < 100 else "1億円超")
def band_old(lb):
    return "1,000万円未満" if lb < 10 else ("1,000万円以上1億円未満" if lb < 100 else "1億円以上")
c["band"] = [band(lb) if y >= 2011 else band_old(lb) for lb, y in zip(c.lb, c.year)]
b = c.groupby(["year", "band", "section"])["n_corp"].sum().unstack("section")
b["share"] = b.loss / b.total * 100
b["n_total"] = b.total
b = b[["n_total", "share"]].reset_index()
b.round(4).to_csv(RES / "by_size_band.csv", index=False)
bn = b[b.year >= 2011].pivot(index="year", columns="band", values="share")
gap = bn["1,000万円以下"] - bn["1億円超"]
dec = {k: float(bn.loc[2011, k] - bn.loc[2024, k]) for k in bn.columns}
# 細かい階級（2011年度分以降）
c2 = c[c.year >= 2011].copy()
fine = c2.groupby(["year", "label", "lb", "section"])["n_corp"].sum().unstack("section").reset_index()
fine["share"] = fine.loss / fine.total * 100
fine["label"] = fine.label.str.replace(",", "")
fine.sort_values(["year", "lb"]).round(4).to_csv(RES / "by_fine_class.csv", index=False)
fw = fine.pivot(index="year", columns="lb", values="share")
fn = fine.pivot(index="year", columns="lb", values="total")

# ---- 3. 景気（営業収入の前年度比）との関係
d = yr.dropna(subset=["sales_growth_pct", "d_share"])
rr, pp = stats.pearsonr(d.sales_growth_pct, d.d_share)
d2 = d[~d.index.isin([2020, 2021])]
rr2, pp2 = stats.pearsonr(d2.sales_growth_pct, d2.d_share)
sl = stats.linregress(d.sales_growth_pct, d.d_share)
# 規模ごとの景気との相関（2012年度分以降、前年度差）
bd = bn.diff().dropna()
sg = yr.sales_growth_pct.reindex(bd.index)
corr_band = {k: float(np.corrcoef(sg, bd[k])[0, 1]) for k in bn.columns}

# ---- 4. 業種（連結・通算を除く資本金階級の合計）
ic = t[(t.industry != "合計") & (t.kind == "class")].groupby(["year", "industry", "section"])["n_corp"].sum().unstack("section")
ic["share"] = ic.loss / ic.total * 100
ic = ic.reset_index()
ic["order"] = ic.industry.map({k: i for i, k in enumerate(IND_ORDER)})
ic = ic.sort_values(["year", "order"])
ic[["year", "industry", "total", "loss", "share"]].round(4).to_csv(RES / "by_industry.csv", index=False)
iw = ic.pivot(index="industry", columns="year", values="share").reindex(IND_ORDER)
inn = ic.pivot(index="industry", columns="year", values="total").reindex(IND_ORDER)
# 2011年度分以前は「その他の法人（企業組合など）」が17業種の外にあり、2012年度分から業種の中に入るため、業種の比較は2012年度分から
IB = 2012
rho, prho = stats.spearmanr(iw[IB], iw[2024])
rho11, _ = stats.spearmanr(iw[2011], iw[2024])

# ---- 5. 問い直し：2012→2024 の低下を「業種の構成の変化」と「業種の中の変化」に分ける（中点の重み）
def shift_share(df_share, df_n, y0, y1):
    w0 = df_n[y0] / df_n[y0].sum(); w1 = df_n[y1] / df_n[y1].sum()
    s0 = df_share[y0] / 100; s1 = df_share[y1] / 100
    between = float(((w1 - w0) * (s0 + s1) / 2).sum() * 100)
    within = float((((w0 + w1) / 2) * (s1 - s0)).sum() * 100)
    total = float((w1 * s1).sum() * 100 - (w0 * s0).sum() * 100)
    contrib = (((w0 + w1) / 2) * (s1 - s0) * 100)
    return between, within, total, contrib
bt, wi, to, contrib = shift_share(iw, inn, IB, 2024)
# 規模（細かい階級）での分解
fw_t = fw.T; fn_t = fn.T
bt_s, wi_s, to_s, _ = shift_share(fw_t, fn_t, 2011, 2024)
pd.DataFrame({"industry": IND_ORDER, "share_2012": iw[IB].values, "share_2024": iw[2024].values,
              "n_2012": inn[IB].values, "n_2024": inn[2024].values,
              "within_contrib_pt": contrib.values}).round(4).to_csv(RES / "decomposition_industry.csv", index=False)

# ---- 6. 頑健性の表
rob = [
    {"check": "本線：全体（連結・通算を含む）法人数", "y2011": yr.share_all[2011], "y2024": yr.share_all[2024], "peak": yr.share_all.max(), "peak_year": int(yr.share_all.idxmax())},
    {"check": "連結・通算を除く", "y2011": yr.share_excl_group[2011], "y2024": yr.share_excl_group[2024], "peak": yr.share_excl_group.max(), "peak_year": int(yr.share_excl_group.idxmax())},
    {"check": "事業年度数で数える", "y2011": yr.share_period[2011], "y2024": yr.share_period[2024], "peak": yr.share_period.max(), "peak_year": int(yr.share_period.idxmax())},
    {"check": "営業収入で重みづけ", "y2011": yr.sales_share_loss[2011], "y2024": yr.sales_share_loss[2024], "peak": yr.sales_share_loss.max(), "peak_year": int(yr.sales_share_loss.idxmax())},
    {"check": "公表の第6表（PDF）", "y2011": o.loss_share_pct[2011], "y2024": o.loss_share_pct[2024], "peak": o.loss_share_pct.max(), "peak_year": int(o.loss_share_pct.idxmax())},
]
rob = pd.DataFrame(rob)
rob.round(2).to_csv(RES / "robustness.csv", index=False)

# ---- 仮説の判定
h1 = bool((gap >= 20).all())
h2 = max(dec, key=dec.get) == "1,000万円以下"
h3 = bool((yr.sales_share_loss < yr.share_all / 2).all())
h4 = bool(rr < -0.5)

main = {
    "years": [int(yr.index.min()), int(yr.index.max())],
    "share_all": {int(k): r2(v) for k, v in yr.share_all.items()},
    "share_2024": r1(yr.share_all[2024]), "share_2007": r1(yr.share_all[2007]),
    "peak_share": r1(yr.share_all.max()), "peak_year": int(yr.share_all.idxmax()),
    "drop_peak_to_2024_pt": r1(yr.share_all.max() - yr.share_all[2024]),
    "min_share": r1(yr.share_all.min()), "years_ge_60": int((yr.share_all >= 60).sum()), "n_years": int(len(yr)),
    "n_total_2024": int(yr.n_total[2024]), "n_loss_2024": int(yr.n_loss[2024]), "n_total_2011": int(yr.n_total[2011]),
    "n_loss_2011": int(yr.n_loss[2011]), "n_profit_2011": int(yr.n_profit[2011]), "n_profit_2024": int(yr.n_profit[2024]),
    "profit_growth_2011_2024_pct": r1((yr.n_profit[2024] / yr.n_profit[2011] - 1) * 100),
    "loss_growth_2011_2024_pct": r1((yr.n_loss[2024] / yr.n_loss[2011] - 1) * 100),
    "official_max_abs_diff_pt": r2(yr.diff_vs_official.abs().max()),
    "official_2003_calendar": float(off[(off.basis == "年分") & (off.fiscal_year == 2003)].loss_share_pct.iloc[0]),
    "official_2006_fy": float(o.loss_share_pct[2006]),
    "excl_group": {"2011": r1(yr.share_excl_group[2011]), "2024": r1(yr.share_excl_group[2024])},
    "group_only": {"2011": r1(yr.share_group_only[2011]), "2024": r1(yr.share_group_only[2024])},
    "period_basis": {"2011": r1(yr.share_period[2011]), "2024": r1(yr.share_period[2024])},
    "size": {k: {"2011": r1(bn.loc[2011, k]), "2024": r1(bn.loc[2024, k]), "decline_pt": r1(dec[k])} for k in bn.columns},
    "size_gap_min_pt": r1(gap.min()), "size_gap_min_year": int(gap.idxmin()), "size_gap_max_pt": r1(gap.max()),
    "size_n_2024": {k: int(b[(b.year == 2024) & (b.band == k)].n_total.iloc[0]) for k in bn.columns},
    "size_share_small_of_all_2024_pct": r1(b[(b.year == 2024) & (b.band == "1,000万円以下")].n_total.iloc[0] / yr.n_total[2024] * 100),
    "fine_2024": {f"{lb:g}": r1(v) for lb, v in fw.loc[2024].items()},
    "fine_2011": {f"{lb:g}": r1(v) for lb, v in fw.loc[2011].items()},
    "fine_n_2024": {f"{lb:g}": int(v) for lb, v in fn.loc[2024].items()},
    "sales_weighted": {"2011": r1(yr.sales_share_loss[2011]), "2024": r1(yr.sales_share_loss[2024]),
                        "min": r1(yr.sales_share_loss.min()), "max": r1(yr.sales_share_loss.max()),
                        "max_year": int(yr.sales_share_loss.idxmax()),
                        "ratio_to_count_max": r2(yr.ratio_sales_to_count.max()),
                        "excl_group_2024": r1(yr.sales_share_loss_excl_group[2024]),
                        "years_ratio_ge_half": [int(k) for k, v in yr.ratio_sales_to_count.items() if v >= 0.5],
                        "y2012": r1(yr.sales_share_loss[2012]), "y2020": r1(yr.sales_share_loss[2020]), "y2018": r1(yr.sales_share_loss[2018])},
    "cycle": {"r": r2(rr), "p": r3(pp), "n": int(len(d)), "r_excl_2020_21": r2(rr2), "p_excl_2020_21": r3(pp2),
              "slope_pt_per_1pct": r3(sl.slope),
              "g2009": r1(yr.sales_growth_pct[2009]), "d2009": r2(yr.d_share[2009]),
              "g2008": r1(yr.sales_growth_pct[2008]), "d2008": r2(yr.d_share[2008]),
              "g2020": r1(yr.sales_growth_pct[2020]), "d2020": r2(yr.d_share[2020]),
              "g2021": r1(yr.sales_growth_pct[2021]), "d2021": r2(yr.d_share[2021]),
              "corr_by_band": {k: r2(v) for k, v in corr_band.items()}},
    "industry": {"base_year": IB, "2012": {k: r1(v) for k, v in iw[IB].items()}, "2024": {k: r1(v) for k, v in iw[2024].items()},
                 "spearman_2012_2024": r2(rho), "spearman_p": r3(prho), "spearman_2011_2024_ref": r2(rho11),
                 "range_2024": [r1(iw[2024].min()), r1(iw[2024].max())], "range_2012": [r1(iw[IB].min()), r1(iw[IB].max())],
                 "n_down": int((iw[2024] < iw[IB]).sum()), "max_decline": [iw[IB].sub(iw[2024]).idxmax(), r1(iw[IB].sub(iw[2024]).max())],
                 "min_decline": [iw[IB].sub(iw[2024]).idxmin(), r1(iw[IB].sub(iw[2024]).min())],
                 "share17_2012": r1(inn[IB].mul(iw[IB]).sum() / inn[IB].sum()), "share17_2024": r1(inn[2024].mul(iw[2024]).sum() / inn[2024].sum())},
    "decomp_industry": {"total_pt": r2(to), "between_pt": r2(bt), "within_pt": r2(wi),
                        "top_within": [[k, r2(v)] for k, v in contrib.sort_values().head(3).items()]},
    "decomp_size": {"total_pt": r2(to_s), "between_pt": r2(bt_s), "within_pt": r2(wi_s)},
    "size_step": {k: {"d2011_2013": r1(bn.loc[2013, k] - bn.loc[2011, k]), "d2013_2024": r1(bn.loc[2024, k] - bn.loc[2013, k]),
                      "y2013": r1(bn.loc[2013, k]), "y2020": r1(bn.loc[2020, k]), "y2019": r1(bn.loc[2019, k])} for k in bn.columns},
    "old_regime_2010": {k: r1(v) for k, v in b[b.year == 2010].set_index("band").share.items()},
    "hypotheses": {"H1": h1, "H2": h2, "H3": h3, "H4": h4},
}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=1))
