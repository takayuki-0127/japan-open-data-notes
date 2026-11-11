"""05 レビュー検算：独立レビューの指摘に合わせて足した確かめ（結果を見てから計算したもの）。"""
import json, pathlib, sys
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f276_common import PREF, CODE, ADJ, EVENTS
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, PRO = ROOT / "results", ROOT / "data" / "processed"
A = pd.read_csv(RES / "A_affected_uplift.csv"); M = pd.read_csv(RES / "B_monthly_peaks.csv")
main = json.loads((RES / "main.json").read_text(encoding="utf-8"))
an = pd.read_csv(PRO / "annual_pref.csv"); FUT = an[an.code > 0].pivot(index="year", columns="code", values="futai")
out = {}
# U0 の中央値、1〜3月の地震を除く
jm = {e[0]: int(e[2][5:7]) for e in EVENTS}
out["U0_median_all"] = float(A.U0.median()); out["U0_n_all"] = int(A.U0.notna().sum())
late = A.event.map(jm).isin([1, 2, 3])
out["U0_median_excl_JanMar"] = float(A[~late].U0.median()); out["U0_n_excl_JanMar"] = int((~late).sum())
out["JanMar_events"] = sorted(A[late].event.unique().tolist())
# 2011年の遠い県の変化
e = next(x for x in EVENTS if x[0] == "E2011")
aff = [CODE[n] for n in e[3]]; adj = set(q for p in aff for q in ADJ[p]) - set(aff)
ctrl = [c for c in range(1, 48) if c not in aff and c not in adj]
sc = FUT[ctrl].mean(axis=1)
out["ctrl2011"] = {str(y): float(sc[y]) for y in range(2007, 2015)}
out["ctrl2011_diff"] = {f"{y-1}->{y}": float(sc[y] - sc[y - 1]) for y in range(2008, 2015)}
# 問い直しの p 値
x = A[A.full_peak]; r, p = stats.spearmanr(x.base, x.peak)
x5 = A.dropna(subset=["U5"]); r5, p5 = stats.spearmanr(x5.base, x5.U5)
mw = stats.mannwhitneyu(x[x.base < 50].peak, x[x.base >= 50].peak, alternative="two-sided")
out["reask_p"] = dict(spearman_peak=float(r), p_peak=float(p), n=int(len(x)), spearman_U5=float(r5), p_U5=float(p5), n5=int(len(x5)),
                      mannwhitney_p=float(mw.pvalue))
# 隣/被災の比の幅
out["adj_ratio_range"] = [min(v["h3_ratio"] for v in [main["base"]] + list(main["robust"].values())),
                          max(v["h3_ratio"] for v in [main["base"]] + list(main["robust"].values()))]
# R3 から 2008年の岩手も除く
r3 = A[(~A.overlap) & ~((A.event == "E2008") & (A.pref == "岩手"))].dropna(subset=["retention"])
out["R3_excl_2008iwate_retention_median"] = float(r3.retention.median()); out["R3_excl_2008iwate_n"] = int(len(r3))
# 月：半減期がない組、青森の月数
out["monthly_no_halflife"] = M[M.in_plan & M.half_life.isna()][["event", "pref"]].values.tolist()
out["monthly_aomori_months"] = int(M[M.event == "E2025"].months_obs.iloc[0])
# 偶然の幅：5%なら19組で期待は約1組
out["placebo_expected_above_p95"] = 19 * 0.05
out["R1_n_peak"] = main["robust"]["R1_trend_base"]["n_peak"]
out["R4_peak_median"] = main["robust"]["R4_household_rate"]["peak_median"]
(RES / "review_checks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
