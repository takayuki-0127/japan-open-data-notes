"""F261 独立レビューを受けて追加した検算（2026-11-11）。結果は results/review_checks.json。

1. 年度ごとの手法の間の幅を、手法をそろえて比べる（BK は FY2023 以降が出ないため、全年度で BK を除く／BK と HAM を除く）
2. 「書き換わりの向きとその後の成長の相関」が、両側のフィルターの仕組みだけでどのくらい出るか
   （周期のない、ドリフトつきランダムウォークで同じ計算をする）
3. 状態空間モデルを計画どおり「ローカル線形トレンド」にした場合の値と、基準（smooth trend）の推定された分散
4. 内閣府と日本銀行の FY2025 の差の、2つの数え方（4期平均の前年比相当と、前期比年率の年度平均）
5. H4 の公表回の数（2次速報で対象四半期 2004Q1〜2023Q2）
"""
import importlib.util
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("m", ROOT / "src" / "zz_f261_methods.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
RES, PROC = ROOT / "results", ROOT / "data" / "processed"
out = {}

# ---- 1. 手法をそろえた幅 ----
fy = pd.read_csv(RES / "fy_pg.csv", index_col=0).loc[2000:2025]


def rng_tab(cols):
    f = fy[cols]
    r = (f.max(axis=1) - f.min(axis=1))
    rank = int((r < r.loc[2025]).sum() + 1)  # 狭い順の順位（1 = いちばん狭い）
    return {"cols": cols, "fy2025": round(float(r.loc[2025]), 3), "rank_narrowest_of_26": rank,
            "median": round(float(r.median()), 3), "min": [int(r.idxmin()), round(float(r.min()), 3)],
            "n_methods_by_fy_min": int(f.notna().sum(axis=1).min())}


allc = list(fy.columns)
out["range_all_methods"] = rng_tab(allc)
out["range_excl_BK"] = rng_tab([c for c in allc if c != "BK"])
out["range_excl_BK_HAM"] = rng_tab([c for c in allc if c not in ("BK", "HAM")])
out["n_methods_fy2025_vs_fy2022"] = [int(fy.loc[2025].notna().sum()), int(fy.loc[2022].notna().sum())]

# ---- 2. ランダムウォークでの相関 ----
VL = pd.read_csv(PROC / "vintage_levels.csv.gz")
rel = pd.read_csv(ROOT / "data" / "raw" / "f50_releases.csv")
latest = VL[VL.rid == rel.rid.iloc[-1]]
lq = latest.quarter.tolist()
ll = np.log(latest.level.values)
E = [q for q in lq if "2004Q1" <= q <= "2021Q2"]
ks = [lq.index(e) for e in E]


def rev_corr(x):
    fin = m.yoy(m.tr_hp(x))
    rev, fut = [], []
    for k in ks:
        if k + 8 < len(x):
            init = m.yoy(m.tr_hp(x[: k + 1]))[k]
            rev.append(fin[k] - init)
            fut.append(100 * (np.exp((x[k + 8] - x[k]) / 2) - 1))
    return float(np.corrcoef(rev, fut)[0, 1])


actual = rev_corr(ll)
g = np.diff(ll)
g_noc = g[(np.array(lq[1:]) < "2020Q2") | (np.array(lq[1:]) > "2020Q4")]
rng = np.random.default_rng(20261111)
sims = []
for _ in range(200):
    x = np.concatenate([[0.0], np.cumsum(rng.normal(g.mean(), g_noc.std(ddof=1), len(g)))])
    sims.append(rev_corr(x))
sims = np.array(sims)
out["revision_future_corr"] = {
    "actual_hp": round(actual, 3),
    "rw_drift_sims": 200, "rw_median": round(float(np.median(sims)), 3),
    "rw_p05": round(float(np.quantile(sims, 0.05)), 3), "rw_p95": round(float(np.quantile(sims, 0.95)), 3),
    "share_rw_ge_actual": round(float((sims >= actual).mean()), 3),
    "note": "ドリフト＝実際の平均成長、ばらつき＝コロナ期（2020Q2〜Q4）を除いた実際の四半期成長の標準偏差、長さ・対象の時点は実データと同じ",
}

# ---- 3. 状態空間モデル ----
P = pd.read_csv(PROC / "panel_q.csv")
l = P["lny"].values
Q = P["quarter"].tolist()


def uc_fit(level):
    r = sm.tsa.UnobservedComponents(l, level=level, autoregressive=2).fit(disp=False, maxiter=500, method="lbfgs")
    t = np.asarray(r.smoothed_state[0])
    pg = pd.Series(m.yoy(t), index=Q)
    fyv = pg.groupby(P["fy"].values).mean()
    return r, pg, fyv


r_st, pg_st, fy_st = uc_fit("smooth trend")
r_ll, pg_ll, fy_ll = uc_fit("local linear trend")
f25 = fy.loc[2025].drop("UC").copy()
f25_ll = pd.concat([f25, pd.Series({"UC_LLT": fy_ll.loc[2025]})])
out["uc"] = {
    "smooth_trend_params": {k: float(v) for k, v in zip(r_st.model.param_names, r_st.params)},
    "smooth_trend_pg_fy2000_2025_min_max": [round(float(fy_st.loc[2000:2025].min()), 3), round(float(fy_st.loc[2000:2025].max()), 3)],
    "llt_params": {k: float(v) for k, v in zip(r_ll.model.param_names, r_ll.params)},
    "llt_fy2025": round(float(fy_ll.loc[2025]), 3),
    "range_fy2025_with_llt": round(float(f25_ll.max() - f25_ll.min()), 3),
}

# ---- 4. 内閣府と日本銀行の FY2025 の差 ----
d = P.set_index("quarter")
cao_roll = d["cao_pg"].rolling(4).mean()
fyq = d["fy"]
out["cao_boj_fy2025"] = {
    "cao_rolling4_fy_mean": round(float(cao_roll[fyq == 2025].mean()), 3),
    "cao_quarterly_fy_mean": round(float(d.loc[fyq == 2025, "cao_pg"].mean()), 3),
    "boj_fy_mean": round(float(d.loc[fyq == 2025, "boj_pg"].mean()), 3),
}
o = out["cao_boj_fy2025"]
o["diff_rolling"] = round(o["boj_fy_mean"] - o["cao_rolling4_fy_mean"], 3)
o["diff_quarterly"] = round(o["boj_fy_mean"] - o["cao_quarterly_fy_mean"], 3)

# ---- 5. 公表回の数 ----
s2 = rel[(rel.stage == 2) & (rel.ref >= "2004Q1") & (rel.ref <= "2023Q2")]
out["h4_releases"] = {"stage2_in_range_all": int(len(s2)), "reissue": s2[s2.reissue].rid.tolist(),
                      "reissue_refs": s2[s2.reissue].ref.tolist(), "used": int((~s2.reissue).sum()),
                      "quarters_in_range": int(len([q for q in lq if "2004Q1" <= q <= "2023Q2"]))}
refs_used = set(s2[~s2.reissue].ref)
out["h4_releases"]["quarters_without_nonreissue_2nd"] = sorted(set(q for q in lq if "2004Q1" <= q <= "2023Q2") - refs_used)

(RES / "review_checks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
