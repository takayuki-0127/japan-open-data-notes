"""仮説 H1〜H4 と頑健性の確かめ。結果は results/ に書く（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
SEED = 20261116
N_PERM = 2000
d = pd.read_csv(ROOT / "data" / "panel_group.csv").sort_values("group_id").reset_index(drop=True)

lg = lambda a, b: 100 * (np.log(d[a]) - np.log(d[b]))
d["g_pay_22_25"] = lg("scheduled_pay_2025", "scheduled_pay_2022")
d["g_pay_23_25"] = lg("scheduled_pay_2025", "scheduled_pay_2023")
d["g_hour_22_25"] = lg("hourly_2025", "hourly_2022")
d["d_age"] = d.age_2025 - d.age_2022
d["d_tenure"] = d.tenure_2025 - d.tenure_2022
d["log_ratio_fy2022_all"] = np.log(d.ratio_fy2022_all)

def wls(y, xs, w=None, data=None):
    data = d if data is None else data
    X = sm.add_constant(data[xs])
    m = sm.WLS(data[y], X, weights=(data[w] if w else np.ones(len(data)))).fit(cov_type="HC3")
    return m

def perm_p(y, x, w, data, n=N_PERM):
    rng = np.random.default_rng(SEED)
    b0 = wls(y, [x], w, data).params[x]
    yv = data[y].to_numpy()
    cnt = 0
    for _ in range(n):
        dd = data.copy(); dd[y] = rng.permutation(yv)
        cnt += abs(wls(y, [x], w, dd).params[x]) >= abs(b0)
    return (cnt + 1) / (n + 1)

def summarize(name, y, x, w="workers_2022", data=None, extra=(), note=""):
    data = d if data is None else data
    m = wls(y, [x, *extra], w, data)
    b, se, p = m.params[x], m.bse[x], m.pvalues[x]
    return dict(spec=name, y=y, x=x, weights=w or "なし", controls="+".join(extra) or "なし", n=int(m.nobs),
                slope=round(float(b), 4), se=round(float(se), 4), p=round(float(p), 4),
                ci_low=round(float(b - 1.96 * se), 4), ci_high=round(float(b + 1.96 * se), 4),
                r2=round(float(m.rsquared), 4), note=note)

out = {}
# 全体の伸び（参考）
out["mean_growth_22_25_weighted"] = round(float(np.average(d.g_pay_22_25, weights=d.workers_2022)), 3)
out["n_groups"] = int(len(d))
out["workers_2022_total"] = int(d.workers_2022.sum())
out["ratio_fy2022_weighted_mean"] = round(float(np.average(d.ratio_fy2022_all, weights=d.workers_2022)), 3)
out["ratio_fy2022_min"] = round(float(d.ratio_fy2022_all.min()), 3)
out["ratio_fy2022_max"] = round(float(d.ratio_fy2022_all.max()), 3)
out["ratio_fy2022_argmax"] = d.loc[d.ratio_fy2022_all.idxmax(), "group_name"]
out["ratio_fy2022_argmin"] = d.loc[d.ratio_fy2022_all.idxmin(), "group_name"]

# ---------- H1 ----------
h1 = summarize("主（H1）", "g_pay_22_25", "ratio_fy2022_all")
h1["perm_p"] = round(float(perm_p("g_pay_22_25", "ratio_fy2022_all", "workers_2022", d)), 4)
out["H1"] = h1
out["H1_verdict"] = "支持" if (h1["slope"] > 0 and h1["p"] < 0.05) else "外れ"
# 相関（重みつき）
def wcorr(x, y, w):
    x, y, w = map(np.asarray, (x, y, w)); mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return float(np.sum(w * (x - mx) * (y - my)) / np.sqrt(np.sum(w * (x - mx) ** 2) * np.sum(w * (y - my) ** 2)))
out["H1_wcorr"] = round(wcorr(d.ratio_fy2022_all, d.g_pay_22_25, d.workers_2022), 3)
out["H1_spearman"] = round(float(d[["ratio_fy2022_all", "g_pay_22_25"]].corr("spearman").iloc[0, 1]), 3)

# ---------- H2：3つに分ける ----------
d["tercile"] = pd.qcut(d.ratio_fy2022_all.rank(method="first"), 3, labels=["低い", "中くらい", "高い"])
ter = (d.groupby("tercile", observed=True)
         .apply(lambda g: pd.Series({"n": len(g), "ratio_min": g.ratio_fy2022_all.min(), "ratio_max": g.ratio_fy2022_all.max(),
                                     "growth_w": np.average(g.g_pay_22_25, weights=g.workers_2022),
                                     "growth_median": g.g_pay_22_25.median(), "workers": g.workers_2022.sum()}),
                include_groups=False).reset_index())
ter.round(4).to_csv(RES / "h2_tercile.csv", index=False)
gap = float(ter.loc[ter.tercile == "高い", "growth_w"].iloc[0] - ter.loc[ter.tercile == "低い", "growth_w"].iloc[0])
out["H2_gap_top_minus_bottom"] = round(gap, 3)
out["H2_tercile_growth"] = {r.tercile: round(float(r.growth_w), 3) for r in ter.itertuples()}
out["H2_verdict"] = "支持" if gap >= 1.0 else "外れ"

# ---------- H3：パネル（職業・年の固定効果） ----------
rows = []
for t in (2023, 2024, 2025):
    for r in d.itertuples():
        rows.append(dict(group_id=r.group_id, year=t,
                         g=100 * (np.log(getattr(r, f"scheduled_pay_{t}")) - np.log(getattr(r, f"scheduled_pay_{t-1}"))),
                         ratio=getattr(r, f"ratio_jun{t}_all"), ratio_ft=getattr(r, f"ratio_jun{t}_ft"),
                         w=r.workers_2022))
p = pd.DataFrame(rows).sort_values(["group_id", "year"]).reset_index(drop=True)
p.to_csv(RES / "h3_panel_long.csv", index=False, float_format="%.6f")
def fe(xvar, weighted=True, fe_group=True):
    X = pd.get_dummies(p[["year"]].astype(str), drop_first=True, dtype=float)
    if fe_group:
        X = X.join(pd.get_dummies(p["group_id"], drop_first=True, dtype=float))
    X.insert(0, xvar, p[xvar]); X = sm.add_constant(X)
    m = sm.WLS(p["g"], X, weights=p["w"] if weighted else np.ones(len(p))).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(p.group_id)[0]})
    return dict(x=xvar, group_fe=fe_group, weighted=weighted, n=int(m.nobs), slope=round(float(m.params[xvar]), 4),
                se=round(float(m.bse[xvar]), 4), p=round(float(m.pvalues[xvar]), 4))
h3 = [fe("ratio"), fe("ratio", fe_group=False), fe("ratio_ft"), fe("ratio", weighted=False)]
pd.DataFrame(h3).to_csv(RES / "h3_panel_fe.csv", index=False)
out["H3"] = h3[0]; out["H3_pooled_no_group_fe"] = h3[1]
out["H3_verdict"] = "支持" if (h3[0]["slope"] > 0 and h3[0]["p"] < 0.05) else "外れ"
# 同じ職業の中で倍率がどれだけ動いたか（自分の平均からのずれの標準偏差）
p["ratio_dm"] = p.ratio - p.groupby("group_id").ratio.transform("mean")
out["H3_within_ratio_sd"] = round(float(p.ratio_dm.std()), 4)
out["H3_between_ratio_sd"] = round(float(d.ratio_fy2022_all.std()), 4)

# ---------- H4：逆向き ----------
d["g_pay_22_23"] = lg("scheduled_pay_2023", "scheduled_pay_2022")
d["d_logratio_23_25"] = 100 * (np.log(d.ratio_jun2025_all) - np.log(d.ratio_jun2023_all))
h4 = summarize("逆向き（H4）", "d_logratio_23_25", "g_pay_22_23")
out["H4"] = h4
out["H4_verdict"] = "支持" if h4["slope"] < 0 else "外れ"

# ---------- 頑健性（H1 の傾き） ----------
small = d.workers_2022 < 10000
rob = [h1,
       summarize("R1 パートを除く常用の倍率", "g_pay_22_25", "ratio_fy2022_ft"),
       summarize("R2 時給に直す", "g_hour_22_25", "ratio_fy2022_all"),
       summarize("R3 重みなし", "g_pay_22_25", "ratio_fy2022_all", w=None),
       summarize("R4 年齢・勤続の変化を制御", "g_pay_22_25", "ratio_fy2022_all", extra=("d_age", "d_tenure")),
       summarize("R5 その他の技術者と1万人未満を除く", "g_pay_22_25", "ratio_fy2022_all",
                 data=d[(d.group_id != "eng_other") & ~small].reset_index(drop=True)),
       summarize("R6a 新規求人倍率", "g_pay_22_25", "newratio_fy2022_all"),
       summarize("R6b 期間 2023→2025（2023年6月までの倍率）", "g_pay_23_25", "ratio_jun2023_all"),
       summarize("R8 一般事務を除く（追加）", "g_pay_22_25", "ratio_fy2022_all",
                 data=d[d.group_id != "clk_general"].reset_index(drop=True), note="計画になかった追加。重みの最も大きい職業"),
       summarize("R7 倍率を対数に（追加）", "g_pay_22_25", "log_ratio_fy2022_all", note="計画になかった追加。1単位＝倍率が約2.7倍"),
       ]
rob_df = pd.DataFrame(rob); rob_df.to_csv(RES / "robustness_h1.csv", index=False)
out["robustness_h1"] = rob
out["n_excluded_small"] = int(small.sum() + (~small & (d.group_id == "eng_other")).sum())

d.round(6).to_csv(RES / "group_table.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: out[k] for k in ["mean_growth_22_25_weighted", "H1", "H1_verdict", "H1_wcorr", "H2_gap_top_minus_bottom", "H2_tercile_growth", "H3", "H3_pooled_no_group_fe", "H3_verdict", "H4", "H4_verdict"]}, ensure_ascii=False, indent=0))
print(rob_df[["spec", "n", "slope", "se", "p"]].to_string())
