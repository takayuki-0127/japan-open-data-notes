"""05 月最大：8地点の「月ごとの日降水量の最大値」で、しきい値とブロックの長さを変えても結論が保たれるかを見る。

- ブロックの長さ：半年・1年・2年ごとの最大値に GEV を当てはめ、100年再現レベルを出す
  （半年なら200ブロックに1度、2年なら50ブロックに1度）。
- しきい値：月最大がしきい値（月最大の上位10%・5%・2.5%）を超えた分に GPD を当てはめる（POT 法）。
  1か月の中に大雨が2回あっても1回しか数えないので、月最大は「ひと月1つに絞った大雨」の近似。
- 前半（1901〜1960）で決めた100年値を、後半（1961〜2025）の年最大が何回超えたかを、手法ごとに数える。
"""
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

ROOT = Path(__file__).resolve().parents[1]
D, R = ROOT / "data", ROOT / "results"
spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_分析.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
RNG = np.random.default_rng(1671)


def gpd_fit(y):
    """GPD（しきい値を超えた分 y>0）の最尤推定。形状 ξ・尺度 σ。"""
    y = np.asarray(y, float)

    def nll(th):
        xi, ls = th
        s = math.exp(ls)
        if abs(xi) < 1e-6:
            return len(y) * ls + y.sum() / s
        t = 1 + xi * y / s
        if np.any(t <= 0):
            return 1e10
        return len(y) * ls + (1 + 1 / xi) * np.log(t).sum()

    r = optimize.minimize(nll, [0.1, math.log(y.mean())], method="Nelder-Mead",
                          options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 4000})
    return r.x[0], math.exp(r.x[1])


def gpd_rl(u, xi, s, lam, T):
    m = lam * T
    return u + s / xi * (m ** xi - 1) if abs(xi) > 1e-6 else u + s * math.log(m)


def block_max(m, months):
    """months か月ごとの最大（1901年1月起点）。欠けた月が1割を超えるブロックは使わない。"""
    m = m.copy()
    m["t"] = (m.year - 1901) * 12 + (m.month - 1)
    m["blk"] = m.t // months
    g = m.groupby("blk").agg(v=("mmax", "max"), n=("mmax", "size"), y0=("year", "min"))
    return g[g.n >= 0.9 * months]


def main():
    m = pd.read_csv(D / "monthly_max.csv")
    ann = pd.read_csv(D / "annual_max.csv")
    rows, split = [], []
    for s, g in m.groupby("station"):
        a = ann[ann.station == s].set_index("year").amax
        # 月最大から作った年最大が、年の表と合うか（確認）
        bm = block_max(g, 12)
        yy = pd.Series(bm.v.values, index=bm.y0.values)
        common = yy.index.intersection(a.index)
        agree = float((np.abs(yy[common] - a[common]) < 0.05).mean())
        res = {"station": s, "annual_table_agree": agree}
        for months, lab in [(6, "半年"), (12, "1年"), (24, "2年")]:
            b = block_max(g, months)
            p = A.fit_mle(b.v.values)
            res[f"gev_{lab}"] = A.rl(p, 100 * 12 / months)
        n_years = g.year.nunique()
        for q, lab in [(0.90, "上位10%"), (0.95, "上位5%"), (0.975, "上位2.5%")]:
            u = g.mmax.quantile(q)
            y = g.mmax[g.mmax > u] - u
            xi, sc = gpd_fit(y.values)
            lam = len(y) / n_years
            res[f"gpd_{lab}"] = gpd_rl(u, xi, sc, lam, 100)
            res[f"gpd_{lab}_xi"] = xi
        rows.append(res)

        # 前半で決めて後半で数える（年最大で判定）
        tr = g[(g.year >= 1901) & (g.year <= 1960)]
        te = a[(a.index >= 1961) & (a.index <= 2025)]
        thr = {}
        thr["GEV 1年"] = A.rl(A.fit_mle(block_max(tr, 12).v.values), 100)
        thr["GEV 半年"] = A.rl(A.fit_mle(block_max(tr, 6).v.values), 200)
        thr["GEV 2年"] = A.rl(A.fit_mle(block_max(tr, 24).v.values), 50)
        for q, lab in [(0.90, "GPD 上位10%"), (0.95, "GPD 上位5%"), (0.975, "GPD 上位2.5%")]:
            u = tr.mmax.quantile(q)
            y = tr.mmax[tr.mmax > u] - u
            xi, sc = gpd_fit(y.values)
            thr[lab] = gpd_rl(u, xi, sc, len(y) / tr.year.nunique(), 100)
        for k, v in thr.items():
            split.append({"station": s, "method": k, "rl100_1901_1960": v,
                          "exceed_1961_2025": int((te > v).sum()), "n_test": len(te)})
    res = pd.DataFrame(rows)
    res.to_csv(R / "monthly_block_threshold_rl100.csv", index=False)
    sp = pd.DataFrame(split)
    sp.to_csv(R / "monthly_split_by_method.csv", index=False)

    # 手法ごとの合計。気候が変わらない世界での期待値は、1年 GEV のもの（03_分析.py の乱数実験）だけを参考に並べる。
    # GPD や半年・2年ブロックについては、月単位の乱数モデルを作っていないので期待値を出していない。
    base = pd.read_csv(R / "baseline_stationary_sim.csv")
    st8 = sorted(m.station.unique())
    exp8 = float(base[base.station.isin(st8)].mean_exceed.sum())
    summ = sp.groupby("method").agg(observed=("exceed_1961_2025", "sum"), years=("n_test", "sum")).reset_index()
    summ["naive_expected"] = summ.years * 0.01
    summ["stationary_expected_gev1y"] = exp8
    summ.to_csv(R / "monthly_split_summary.csv", index=False)

    # 100年値の手法間のばらつき（地点ごとに、1年 GEV に対する比）
    cols = [c for c in res.columns if c.startswith(("gev_", "gpd_")) and not c.endswith("_xi")]
    rel = res[cols].div(res["gev_1年"], axis=0)
    out = {"stations": st8, "annual_table_agree_min": float(res.annual_table_agree.min()),
           "rl100_relative_to_gev1y_median": rel.median().round(3).to_dict(),
           "rl100_relative_range": [float(rel.min().min()), float(rel.max().max())],
           "split": summ.round(2).to_dict(orient="records"), "stationary_expected_8": exp8}
    (R / "summary_monthly.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
