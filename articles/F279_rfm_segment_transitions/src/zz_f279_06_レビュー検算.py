"""06 レビュー検算（独立レビューを受けて、結果を見た後で足した確認）
- 月ごとの購入顧客数（季節）と、時点ごとの全体のもう一度買った割合
- H3 の差の偶然の幅：顧客単位の再標本化（7時点まとめて、300回、乱数の種 279）
- 重複行の内訳（2つのシートの重なり）と、顧客IDのない行
- 区分ごとの人数（H4 の比べる2時点）"""
import json, sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f279_common import *
RES = ROOT / "results"; out = {}
inv = load()
buy = inv[~inv["cancel"]].copy(); buy["ym"] = buy["date"].dt.to_period("M").astype(str)
mc = buy.groupby("ym")["cust"].nunique()
out["monthly_buying_customers"] = {k: int(v) for k, v in mc.items()}
S = {t: snapshot(inv, t) for t in SNAPS}
out["overall_rebuy"] = {str(t.date()): round(float(g["rebuy"].mean()), 4) for t, g in S.items()}
out["outcome_window_months"] = {str(t.date()): [str((t + pd.DateOffset(months=k)).to_period("M")) for k in range(6)] for t in SNAPS}
# H3 再標本化
rng = np.random.default_rng(279)
custs = np.array(sorted(set().union(*[set(g.index) for g in S.values()])))
def diff_for(w):
    d = []
    for t, g in S.items():
        g = g.copy(); g["w"] = w.reindex(g.index).fillna(0).values
        g = g[g["w"] > 0]
        g["rfm"] = g["r"] + g["f"] + g["m"] + g["M"] / (g["M"].abs().max() * 10 + 1)
        def cap(score):
            o = g.sort_values(score, ascending=False, kind="mergesort")
            cw = o["w"].cumsum(); n = 0.2 * o["w"].sum()
            sel = cw <= n + 1e-9
            return (o["fut"] * o["w"])[sel].sum() / (g["fut"] * g["w"]).sum()
        d.append(cap("rfm") - cap("M"))
    return float(np.mean(d)) * 100
base = diff_for(pd.Series(1, index=custs))
draws = []
for b in range(300):
    idx = rng.integers(0, len(custs), len(custs))
    w = pd.Series(np.bincount(idx, minlength=len(custs)), index=custs)
    draws.append(diff_for(w))
draws = np.array(draws)
out["H3_bootstrap"] = dict(point_weighted=round(base, 3), mean=round(float(draws.mean()), 3),
                           ci95=[round(float(np.percentile(draws, 2.5)), 3), round(float(np.percentile(draws, 97.5)), 3)],
                           share_below_minus3=round(float((draws <= -3).mean()), 3), n=300, seed=279)
# 重複と顧客ID
xl = pd.read_excel(ROOT / "data" / "raw" / "online_retail_II.xlsx", sheet_name=None, dtype={"Invoice": str, "StockCode": str})
a, b2 = list(xl.values())
dup_within = int(a.duplicated().sum() + b2.duplicated().sum())
both = pd.concat([a.drop_duplicates(), b2.drop_duplicates()])
dup_cross = int(both.duplicated().sum())
allr = pd.concat([a, b2]); allr_d = allr.drop_duplicates()
out["duplicates"] = dict(total=int(len(allr) - len(allr_d)), within_sheets=dup_within, across_sheets=dup_cross,
                         sheet2_first=str(b2["InvoiceDate"].min()), sheet1_last=str(a["InvoiceDate"].max()))
out["no_customer_rows"] = dict(rows=int(allr_d["Customer ID"].isna().sum()), share=round(float(allr_d["Customer ID"].isna().mean()), 4),
                               rows_before_dedup=int(allr["Customer ID"].isna().sum()))
n0 = S[pd.Timestamp("2010-12-01")].groupby("seg").size().reindex(SEGS)
n1 = S[pd.Timestamp("2011-06-01")].groupby("seg").size().reindex(SEGS)
out["seg_n_2010_12"] = {k: int(v) for k, v in n0.items()}; out["seg_n_2011_06"] = {k: int(v) for k, v in n1.items()}
json.dump(out, open(RES / "G_review_checks.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "outcome_window_months"}, ensure_ascii=False, indent=1))
