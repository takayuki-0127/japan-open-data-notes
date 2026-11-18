"""山（上乗せ）と谷（不足）の大きさを測る。結果は results/ に出す（オフライン、乱数なし）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
m = pd.read_csv(ROOT / "data" / "monthly_machinery.csv", index_col="ym")
g = pd.read_csv(ROOT / "data" / "monthly_appliance_goods.csv", index_col="ym")

EVENTS = {  # 先に決めた窓（PLAN.md）
    "E1": {"name": "エコポイント・地デジ", "peak": ("2009-05", "2011-07"), "trough": ("2011-08", "2013-09"),
           "trough_short": ("2011-08", "2012-07")},
    "E2": {"name": "2014年の税率引き上げ", "peak": ("2013-10", "2014-03"), "trough": ("2014-04", "2015-03"),
           "trough_short": ("2014-04", "2014-08")},
    "E3": {"name": "2019年の税率引き上げ", "peak": ("2019-04", "2019-09"), "trough": ("2019-10", "2020-02"),
           "trough_short": ("2019-10", "2020-02")},
}
NORMAL = [2007, 2016, 2017, 2018]


def tnum(idx):
    y = np.array([int(s[:4]) for s in idx]); mo = np.array([int(s[5:7]) for s in idx])
    return (y - 2000) * 12 + mo - 1, mo


def design(idx, trend=True):
    t, mo = tnum(idx)
    X = [np.ones(len(idx))]
    if trend:
        X.append(t / 12.0)
    for k in range(2, 13):
        X.append((mo == k).astype(float))
    return np.column_stack(X)


def counterfactual(series, fit_years, pred_from="2005-01", pred_to="2020-02", trend=True):
    s = series.dropna()
    fit = s[[int(i[:4]) in fit_years for i in s.index]]
    beta, *_ = np.linalg.lstsq(design(fit.index, trend), np.log(fit.values), rcond=None)
    pidx = [i for i in s.index if pred_from <= i <= pred_to]
    cf = np.exp(design(pidx, trend) @ beta)
    resid = np.log(fit.values) - design(fit.index, trend) @ beta
    return pd.Series(cf, index=pidx), beta, float(resid.std(ddof=len(beta)))


def window_sum(ex, a, b):
    w = ex[(ex.index >= a) & (ex.index <= b)]
    return float(w.sum()), int(len(w))


def summarize(ex, label):
    out = {}
    for k, e in EVENTS.items():
        pk, npk = window_sum(ex, *e["peak"])
        tr, ntr = window_sum(ex, *e["trough"])
        ts, nts = window_sum(ex, *e["trough_short"])
        out[k] = {"peak": pk, "peak_months": npk, "trough": tr, "trough_months": ntr,
                  "trough_short": ts, "trough_short_months": nts,
                  "payback": -tr / pk if pk > 0 else None, "payback_short": -ts / pk if pk > 0 else None}
    return out


# ---- 結果を見てから足した本線：直前の「平常の1年」と同じ月を基準にする（計画からの変更）----
PRE_YEAR = {"E1": ("2007-05", "2008-04"), "E2": ("2012-10", "2013-09"), "E3": ("2018-04", "2019-03")}
AFTER2 = {"E1": ("2012-08", "2013-07"), "E2": ("2015-04", "2016-03")}  # 締め切りから13〜24か月後


def local_excess(series, pre, a, b):
    """窓 [a,b] の各月を、pre の1年のうち同じ暦月の値で割って 1 を引く。"""
    s = series.dropna()
    base = {i[5:7]: s[i] for i in s.index if pre[0] <= i <= pre[1]}
    w = s[(s.index >= a) & (s.index <= b)]
    return pd.Series([w[i] / base[i[5:7]] - 1 for i in w.index], index=w.index)


def local_summary(series, pre_year=PRE_YEAR, sa=False):
    out = {}
    for k, e in EVENTS.items():
        pre = pre_year[k]
        if sa:
            s = series.dropna()
            lvl = s[(s.index >= pre[0]) & (s.index <= pre[1])].mean()
            f = lambda a, b: (s[(s.index >= a) & (s.index <= b)] / lvl - 1)
        else:
            f = lambda a, b: local_excess(series, pre, a, b)
        pk = f(*e["peak"]); tr = f(*e["trough"]); ts = f(*e["trough_short"])
        d = {"peak": float(pk.sum()), "trough": float(tr.sum()), "trough_short": float(ts.sum()),
             "peak_months": int(len(pk)), "trough_months": int(len(tr)), "trough_short_months": int(len(ts))}
        d["payback"] = -d["trough"] / d["peak"] if d["peak"] > 0 else None
        d["payback_short"] = -d["trough_short"] / d["peak"] if d["peak"] > 0 else None
        d["trough_short_mean"] = float(ts.mean())
        if k in AFTER2:
            d["after13_24_mean"] = float(f(*AFTER2[k]).mean())
        out[k] = d
    return out


res = {"normal_years": NORMAL, "pre_year": {k: list(v) for k, v in PRE_YEAR.items()},
       "events": {k: {"name": v["name"], **{x: list(v[x]) for x in ("peak", "trough", "trough_short")}} for k, v in EVENTS.items()}}
orig = m["index_orig"]

# 本線（結果を見てから変えた）：直前の平常の1年の同じ月を基準
res["main"] = local_summary(orig)
# 計画どおりの方法：平常の年 2007・2016〜2018 のトレンドと月のダミー
cf, beta, sd = counterfactual(orig, NORMAL)
ex_plan = orig.loc[cf.index] / cf - 1
res["planned"] = summarize(ex_plan, "")
res["planned_model"] = {"trend_per_year_pct": float((np.exp(beta[1]) - 1) * 100), "resid_sd_pct": sd * 100, "fit_months": 48}

rows = []
for k, e in EVENTS.items():
    ex = local_excess(orig, PRE_YEAR[k], e["peak"][0], e["trough"][1])
    for i, v in ex.items():
        rows.append({"ym": i, "event": k, "part": "peak" if i <= e["peak"][1] else "trough", "excess": float(v)})
mon = pd.DataFrame(rows)
mon.to_csv(R / "monthly_excess_local.csv", index=False, float_format="%.5f")
pd.DataFrame({"index_orig": orig.loc[cf.index], "counterfactual_planned": cf, "excess_planned": ex_plan}).to_csv(
    R / "monthly_excess_planned.csv", float_format="%.5f")
for k in EVENTS:
    w = mon[mon.event == k].set_index("ym").excess
    res["main"][k]["max_month"] = [w.idxmax(), float(w.max())]
    res["main"][k]["min_month"] = [w.idxmin(), float(w.min())]
e1 = mon[(mon.event == "E1") & (mon.part == "peak")].set_index("ym").excess
res["E1_top_months"] = [[i, float(v)] for i, v in e1.sort_values(ascending=False).head(6).items()]
parts = {"2009-05..2010-02": ("2009-05", "2010-02"), "2010-03": ("2010-03", "2010-03"),
         "2010-04..2010-10": ("2010-04", "2010-10"), "2010-11": ("2010-11", "2010-11"),
         "2010-12..2011-03": ("2010-12", "2011-03"), "2011-04..2011-07": ("2011-04", "2011-07")}
res["E1_parts"] = {p: float(e1[(e1.index >= a) & (e1.index <= b)].sum()) for p, (a, b) in parts.items()}

rob = []
def add(label, s, keys=("E1", "E2", "E3")):
    for k in keys:
        d = s[k]
        rob.append({"check": label, "event": k, "peak": d["peak"], "trough": d["trough"], "trough_short": d["trough_short"],
                    "payback": d["payback"], "payback_short": d["payback_short"]})
add("本線：直前の平常の1年の同じ月が基準（原指数）", res["main"])
alt = dict(PRE_YEAR); alt["E1"] = ("2008-05", "2009-04")
add("E1 の基準をリーマン・ショック後の1年（2008年5月〜2009年4月）に", local_summary(orig, alt), ("E1",))
alt2 = dict(PRE_YEAR); alt2["E2"] = ("2015-10", "2016-09"); alt2["E3"] = ("2016-04", "2017-03")
add("E2・E3 の基準を別の平常の1年に（E2：2015年10月〜2016年9月、E3：2016年4月〜2017年3月）", local_summary(orig, alt2), ("E2", "E3"))
add("季節調整済指数・直前の1年の平均の水準が基準", local_summary(m["index_sa"], sa=True))
add("業種別商業販売額（金額）で同じ計算", local_summary(m["sales_bil_yen"]))
add("計画どおり：平常の年 2007・2016〜2018 のトレンドと月のダミー", res["planned"])
cf2, _, _ = counterfactual(orig, [2005, 2006, 2007, 2016, 2017, 2018])
add("計画どおりの方法で平常の年に 2005・2006 を足す", summarize(orig.loc[cf2.index] / cf2 - 1, ""))
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False, float_format="%.4f")
res["robustness"] = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items()} for r in rob.to_dict("records")]

gname = {"total": "商品販売額（計）", "av": "AV家電", "info": "情報家電", "comm": "通信家電", "camera": "カメラ類",
         "living": "生活家電", "other": "その他"}
grow = []
P3 = PRE_YEAR["E3"]
for c, nm in gname.items():
    pk = local_excess(g[c], P3, *EVENTS["E3"]["peak"])
    tr = local_excess(g[c], P3, *EVENTS["E3"]["trough"])
    grow.append({"goods": c, "name": nm, "peak": float(pk.sum()), "trough": float(tr.sum()),
                 "payback": float(-tr.sum() / pk.sum()) if pk.sum() > 0 else None,
                 "sep2019": float(pk.loc["2019-09"]), "oct2019": float(tr.loc["2019-10"]),
                 "share_pre_year": float(g[c].loc[P3[0]:P3[1]].sum() / g["total"].loc[P3[0]:P3[1]].sum())})
grow = pd.DataFrame(grow)
tot_peak = grow.loc[grow.goods == "total", "peak"].iloc[0]
tot_tr = grow.loc[grow.goods == "total", "trough"].iloc[0]
grow["contrib_peak_share"] = [(r.peak * r.share_pre_year) / tot_peak for r in grow.itertuples()]
grow["contrib_trough_share"] = [(r.trough * r.share_pre_year) / tot_tr for r in grow.itertuples()]
grow.to_csv(R / "goods_E3.csv", index=False, float_format="%.4f")
res["goods_E3"] = {r.goods: {"peak": r.peak, "trough": r.trough, "payback": None if pd.isna(r.payback) else r.payback, "sep2019": r.sep2019, "oct2019": r.oct2019,
                             "share_pre_year": r.share_pre_year, "contrib_peak_share": r.contrib_peak_share,
                             "contrib_trough_share": r.contrib_trough_share} for r in grow.itertuples()}
gplan = []
for c, nm in gname.items():
    cfg, _, sdg = counterfactual(g[c], [2016, 2017, 2018], pred_from="2014-01", pred_to="2020-02")
    sg = summarize(g[c].loc[cfg.index] / cfg - 1, "")
    for k in ("E2", "E3"):
        gplan.append({"goods": c, "name": nm, "event": k, "peak": sg[k]["peak"], "trough": sg[k]["trough"], "resid_sd_pct": sdg * 100})
pd.DataFrame(gplan).to_csv(R / "goods_planned_reference.csv", index=False, float_format="%.4f")

# 問い直し：山の前（2007年5月〜2008年4月）の水準に戻ったのか（季節調整済指数）
sa = m["index_sa"].dropna()
pre_lvl = float(sa.loc["2007-05":"2008-04"].mean())
yr = sa.groupby([i[:4] for i in sa.index]).agg(["mean", "count"])
rq = pd.DataFrame({"year": yr.index, "months": yr["count"].values, "sa_mean": yr["mean"].values,
                   "ratio_to_pre": yr["mean"].values / pre_lvl})
rq.to_csv(R / "requestion_level.csv", index=False, float_format="%.4f")
after = sa.loc["2011-08":]
reach = [i for i in after.index if after[i] >= pre_lvl]
ry = rq.set_index("year")
res["requestion"] = {"pre_level_sa": pre_lvl, "months_at_or_above_pre_since_2011_08": len(reach),
                     "first_month_at_or_above": reach[0] if reach else None, "month_list_at_or_above": reach,
                     "ratio_2012": float(ry.loc["2012", "ratio_to_pre"]), "ratio_2016": float(ry.loc["2016", "ratio_to_pre"]),
                     "ratio_2019": float(ry.loc["2019", "ratio_to_pre"]), "ratio_2025": float(ry.loc["2025", "ratio_to_pre"]),
                     "min_year": str(ry["ratio_to_pre"].loc["2011":].idxmin()), "min_year_ratio": float(ry["ratio_to_pre"].loc["2011":].min()),
                     "last_month": sa.index[-1], "ratio_last_12m": float(sa.iloc[-12:].mean() / pre_lvl)}
# レビューで追加：2012〜2019年の年平均の幅、全ての確かめでの H1 と税率の戻り率の幅（題名の数字のもと）
r1219 = ry.loc[[str(y) for y in range(2012, 2020)], "ratio_to_pre"]
res["requestion"]["ratio_2012_2019_min"] = float(r1219.min())
res["requestion"]["ratio_2012_2019_max"] = float(r1219.max())
pk = rob.pivot(index="check", columns="event", values="peak")
pk = pk.dropna()
tx = rob[rob.event.isin(["E2", "E3"])]
res["across_checks"] = {"checks_with_all_events": int(len(pk)),
                        "H1_holds_all": bool((pk["E1"] > pk["E2"] + pk["E3"]).all()),
                        "E1_peak_min": float(rob[rob.event == "E1"].peak.min()), "E1_peak_max": float(rob[rob.event == "E1"].peak.max()),
                        "E2E3_peak_sum_min": float((pk["E2"] + pk["E3"]).min()), "E2E3_peak_sum_max": float((pk["E2"] + pk["E3"]).max()),
                        "tax_payback_min": float(tx.payback.min()), "tax_payback_max": float(tx.payback.max())}

def judge(S):
    return {
        "H1": {"E1_peak": S["E1"]["peak"], "E2_plus_E3_peak": S["E2"]["peak"] + S["E3"]["peak"],
               "result": "支持" if S["E1"]["peak"] > S["E2"]["peak"] + S["E3"]["peak"] else "外れ"},
        "H2": {"E1_payback": S["E1"]["payback"], "result": "支持" if S["E1"]["payback"] >= 0.5 else "外れ"},
        "H3": {"E2_payback": S["E2"]["payback"], "result": "支持" if S["E2"]["payback"] >= 1 else "外れ"},
        "H4": {"ratio_E3_to_E2": S["E3"]["peak"] / S["E2"]["peak"], "result": "支持" if S["E3"]["peak"] < 0.5 * S["E2"]["peak"] else "外れ"},
    }
res["hypotheses_planned"] = judge(res["planned"])
res["hypotheses_main"] = judge(res["main"])
json.dump(res, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: res[k] for k in ("main", "hypotheses_planned", "hypotheses_main", "E1_parts", "E1_top_months")}, ensure_ascii=False, indent=1))
print({k: v for k, v in res["requestion"].items() if k != "month_list_at_or_above"})
print(rob.round(3).to_string()); print(grow.round(3).to_string())
