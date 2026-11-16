"""H1〜H4 と頑健性（オフライン）。結果は results/ に書く。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
mk = pd.read_csv(ROOT / "data" / "maikin_monthly.csv", dtype={"size": str})
tr = pd.read_csv(ROOT / "data" / "truck_monthly.csv")
r4 = lambda x: round(float(x), 4)
POST = 2024 * 12 + 3  # 2024年4月（ym = year*12 + month - 1）
mk["ym"] = mk.year * 12 + mk.month - 1
tr["ym"] = tr.year * 12 + tr.month - 1
VARS = {"ot_hours": "所定外労働時間", "total_hours": "総実労働時間", "sched_pay": "所定内給与", "total_pay": "現金給与総額", "days": "出勤日数"}

def series(ind, size="T"):
    return mk[(mk.ind == ind) & (mk["size"] == size)].set_index("ym").sort_index()

def control_pool(size="T"):
    mid = mk[(mk["size"] == size) & mk.ind.str.match(r"^[A-Z]\d{2}$") & ~mk.ind.isin(["H43", "H44"])].copy()
    rows = []
    for v in VARS:
        p = mid.pivot(index="ym", columns="ind", values=v)
        p = p.loc[:, p.loc[(2019 * 12):].notna().all()]  # 2019年以降そろっている中分類だけ
        rows.append(np.log(p).mean(axis=1).rename(v))
    return pd.concat(rows, axis=1), p.shape[1]

def did(var, ctrl="TL", size="T", start=(2019, 1), trend=1, end=None):
    h = series("H44", size)
    if ctrl == "TL":
        c = np.log(series("TL", size)[var])
    else:
        c = control_pool(size)[0][var]
    D = (np.log(h[var]) - c).dropna()
    s = start[0] * 12 + start[1] - 1
    D = D[D.index >= s]
    if end is not None:
        D = D[D.index <= end]
    X = pd.DataFrame(index=D.index)
    X["post"] = (D.index >= POST).astype(float)
    mon = (D.index % 12) + 1
    for m in range(2, 13):
        X[f"m{m}"] = (mon == m).astype(float)
    tt = (D.index - s) / 12.0
    if trend >= 1: X["trend"] = tt
    if trend >= 2: X["trend2"] = tt ** 2
    X = sm.add_constant(X)
    m = sm.OLS(D, X).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    b = m.params["post"]
    return dict(var=var, label=VARS[var], ctrl=ctrl, size=size, start=f"{start[0]}-{start[1]:02d}", trend=trend, n=int(m.nobs),
                coef_log=r4(b), pct=r4(100 * (np.exp(b) - 1)), se=r4(m.bse["post"]), p=r4(m.pvalues["post"]))

out = {}
main = {v: did(v) for v in VARS}
out["did_main"] = main
out["H1"], out["H2"], out["H3"] = main["ot_hours"], main["total_hours"], main["sched_pay"]
out["H1_verdict"] = "支持" if (main["ot_hours"]["coef_log"] < 0 and main["ot_hours"]["p"] < 0.05) else "外れ"
out["H2_verdict"] = "支持" if (main["total_hours"]["coef_log"] < 0 and main["total_hours"]["p"] < 0.05) else "外れ"
out["H3_verdict"] = "支持" if (main["sched_pay"]["coef_log"] > 0 and main["sched_pay"]["p"] < 0.05) else "外れ"

# 水準（年度平均）
h, c = series("H44"), series("TL")
def fy_mean(s, fy, v):
    return float(s[(s.index >= fy * 12 + 3) & (s.index <= fy * 12 + 14)][v].mean())
lv = []
for fy in range(2019, 2026):
    lv.append(dict(fy=fy, **{f"H44_{v}": round(fy_mean(h, fy, v), 2) for v in ["ot_hours", "total_hours", "sched_pay"]},
                   **{f"TL_{v}": round(fy_mean(c, fy, v), 2) for v in ["ot_hours", "total_hours", "sched_pay"]}))
lv = pd.DataFrame(lv); lv.to_csv(RES / "fy_levels.csv", index=False)
out["fy_levels"] = lv.to_dict("records")

# イベントスタディ：前年同月比の差（H44 − TL、%pt）
es = pd.DataFrame(index=h.index)
for v in ["ot_hours", "total_hours", "sched_pay"]:
    es[f"yoy_H44_{v}"] = 100 * (np.log(h[v]) - np.log(h[v].shift(12)))
    es[f"yoy_TL_{v}"] = 100 * (np.log(c[v]) - np.log(c[v].shift(12)))
    es[f"yoy_diff_{v}"] = es[f"yoy_H44_{v}"] - es[f"yoy_TL_{v}"]
es["event_month"] = es.index - POST
es = es[es.index >= 2020 * 12].reset_index()
es.round(4).to_csv(RES / "event_yoy.csv", index=False)
def win(a, b, col):
    return r4(es[(es.event_month >= a) & (es.event_month <= b)][col].mean())
out["yoy_diff_ot_pre12"] = win(-12, -1, "yoy_diff_ot_hours"); out["yoy_diff_ot_post12"] = win(0, 11, "yoy_diff_ot_hours")
out["yoy_diff_ot_post13_24"] = win(12, 23, "yoy_diff_ot_hours")
out["yoy_diff_total_pre12"] = win(-12, -1, "yoy_diff_total_hours"); out["yoy_diff_total_post12"] = win(0, 11, "yoy_diff_total_hours")
out["yoy_diff_pay_pre12"] = win(-12, -1, "yoy_diff_sched_pay"); out["yoy_diff_pay_post12"] = win(0, 11, "yoy_diff_sched_pay")

# ---------- H4：運ぶ量 ----------
def its(col, start=(2021, 4), trend=1, transform=np.log):
    s = start[0] * 12 + start[1] - 1
    d = tr[tr.ym >= s].set_index("ym").sort_index()
    y = transform(d[col]) if transform is not None else d[col]
    X = pd.DataFrame(index=d.index)
    mon = (d.index % 12) + 1
    for m in range(2, 13):
        X[f"m{m}"] = (mon == m).astype(float)
    if trend >= 1: X["trend"] = (d.index - s) / 12.0
    X = sm.add_constant(X)
    pre = d.index < POST
    m = sm.OLS(y[pre], X[pre]).fit()
    pred = m.predict(X)
    dev = (y - pred)
    post = ~pre
    resid_sd = float(np.std(m.resid, ddof=X.shape[1]))
    devp = dev[post]
    # 1年目・2年目
    y1 = devp[devp.index < POST + 12]; y2 = devp[devp.index >= POST + 12]
    se_mean = resid_sd / np.sqrt(post.sum())  # 残差が独立とした目安
    return dict(col=col, start=f"{start[0]}-{start[1]:02d}", trend=trend, n_pre=int(pre.sum()), n_post=int(post.sum()),
                mean_dev_pct=r4(100 * (np.exp(devp.mean()) - 1)) if transform is not None else r4(devp.mean()),
                year1_dev_pct=r4(100 * (np.exp(y1.mean()) - 1)) if transform is not None else r4(y1.mean()),
                year2_dev_pct=r4(100 * (np.exp(y2.mean()) - 1)) if transform is not None else r4(y2.mean()),
                resid_sd_pct=r4(100 * resid_sd) if transform is not None else r4(resid_sd),
                approx_z=r4(devp.mean() / se_mean), trend_per_year_pct=r4(100 * m.params.get("trend", np.nan))), (y, pred)
h4, (y_ton, p_ton) = its("ton_commercial")
out["H4"] = h4
out["H4_verdict"] = "支持" if h4["mean_dev_pct"] < -2 else "外れ"
tr["dist_commercial"] = tr.tonkm_commercial * 1000 / tr.ton_commercial  # km（百万トンキロ÷千トン×1000）
pd.DataFrame({"ym": y_ton.index, "log_ton": y_ton.values, "pred": p_ton.values}).round(6).to_csv(RES / "truck_its_ton.csv", index=False)
# 前年度比（年度の合計）
fy = tr.copy(); fy["fy"] = np.where(fy.month >= 4, fy.year, fy.year - 1)
fyt = fy.groupby("fy")[["ton_commercial", "tonkm_commercial", "ton_total", "tonkm_total"]].agg(["sum", "count"])
fyt.columns = [f"{a}_{b}" for a, b in fyt.columns]
fyt = fyt.reset_index(); fyt.to_csv(RES / "truck_fy.csv", index=False)
out["truck_fy"] = fyt.to_dict("records")
fx = fyt.set_index("fy")
out["truck_fy_change_pct"] = {f"{c}_{a}_{b}": r4(100 * (fx.loc[b, c + "_sum"] / fx.loc[a, c + "_sum"] - 1))
                              for c in ["ton_commercial", "tonkm_commercial"] for a, b in [(2023, 2024), (2024, 2025), (2023, 2025)]}
hl = lv.set_index("fy")
out["fy_change_pct"] = {f"{ind}_{v}_2023_2025": r4(100 * (hl.loc[2025, f"{ind}_{v}"] / hl.loc[2023, f"{ind}_{v}"] - 1))
                        for ind in ["H44", "TL"] for v in ["ot_hours", "total_hours", "sched_pay"]}

# ---------- 頑健性 ----------
rob = []
for v in ["ot_hours", "total_hours", "sched_pay"]:
    rob += [main[v] | {"spec": "主"},
            did(v, ctrl="pool") | {"spec": "R1 対照を中分類の平均（H43・H44を除く）"},
            did(v, start=(2021, 1)) | {"spec": "R2 2021年1月から"},
            did(v, trend=0) | {"spec": "R3a 時間の流れなし"},
            did(v, trend=2) | {"spec": "R3b 2次の時間の流れ"},
            did(v, size="0") | {"spec": "R4 規模30人以上"}]
rob_df = pd.DataFrame(rob); rob_df.to_csv(RES / "robustness_did.csv", index=False)
out["robustness_did"] = rob
out["n_control_industries"] = int(control_pool()[1])
tr_rob = [h4 | {"spec": "主（輸送トン数）"},
          its("tonkm_commercial")[0] | {"spec": "R5a 輸送トンキロ"},
          its("dist_commercial")[0] | {"spec": "R5b 1トンあたりの距離"},
          its("ton_total")[0] | {"spec": "R5c 自家用を含む合計のトン数"},
          its("ton_commercial", trend=0)[0] | {"spec": "R3 時間の流れなし"},
          its("ton_commercial", start=(2020, 4))[0] | {"spec": "R2' 2020年4月から推定"}]
pd.DataFrame(tr_rob).to_csv(RES / "robustness_truck.csv", index=False)
out["robustness_truck"] = tr_rob

# R6 標本の入れ替え（2024年1月）の段差：12月→1月の D の変化を年ごとに
jump = []
Dt = (np.log(h["total_hours"]) - np.log(c["total_hours"]))
Do = (np.log(h["ot_hours"]) - np.log(c["ot_hours"]))
for y in range(2016, 2027):
    a, b = y * 12 - 1, y * 12  # 前年12月、1月
    if a in Dt.index and b in Dt.index:
        jump.append(dict(year=y, dec_to_jan_total=r4(100 * (Dt[b] - Dt[a])), dec_to_jan_ot=r4(100 * (Do[b] - Do[a]))))
jump = pd.DataFrame(jump); jump.to_csv(RES / "benchmark_jan_jump.csv", index=False)
out["jan2024_jump_total"] = float(jump.set_index("year").loc[2024, "dec_to_jan_total"])
out["jan_jump_total_other_years_mean"] = r4(jump[jump.year != 2024].dec_to_jan_total.mean())
out["jan_jump_total_other_years_sd"] = r4(jump[jump.year != 2024].dec_to_jan_total.std())
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: out[k] for k in out if k not in ("robustness_did", "robustness_truck", "truck_fy", "fy_levels")}, ensure_ascii=False, indent=0))
print(rob_df[["spec", "var", "pct", "se", "p"]].to_string())
print(pd.DataFrame(tr_rob)[["spec", "mean_dev_pct", "year1_dev_pct", "year2_dev_pct", "resid_sd_pct", "approx_z", "trend_per_year_pct"]].to_string())
print(lv.to_string()); print(jump.to_string())
