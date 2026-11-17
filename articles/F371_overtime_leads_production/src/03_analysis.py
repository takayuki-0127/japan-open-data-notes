"""03_analysis.py : 所定外労働時間（製造業）と鉱工業生産の時差・山谷・弾力性を計算する。"""
import json
import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
RES.mkdir(exist_ok=True)
LAGS = list(range(-6, 7))
SHOCK = [("200810", "200906"), ("202003", "202012")]


def r3(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 3)


def load():
    d = pd.read_csv(BASE / "data" / "monthly.csv", dtype={"ym": str})
    d["date"] = pd.to_datetime(d["ym"], format="%Y%m")
    for c in ["ot_mfg5", "ot_mfg30", "hours_mfg5", "ot_all5", "iip"]:
        lg = np.log(d[c])
        d[c + "_m1"] = (lg - lg.shift(1)) * 100
        d[c + "_m3"] = (lg - lg.shift(3)) * 100
        d[c + "_ma3"] = d[c].rolling(3, center=True).mean()
    return d


def in_shock(ym):
    return any(a <= ym <= b for a, b in SHOCK)


def xcorr(d, xc, yc, mask=None):
    """corr(x_t, y_{t+k})。k>0 で x が先。"""
    out = []
    for k in LAGS:
        y = d[yc].shift(-k)
        ok = d[xc].notna() & y.notna()
        if mask is not None:
            ok &= mask & mask.shift(-k, fill_value=False)
        out.append({"lag": k, "corr": float(np.corrcoef(d.loc[ok, xc], y[ok])[0, 1]), "n": int(ok.sum())})
    return pd.DataFrame(out)


def best(t):
    i = t["corr"].idxmax()
    return int(t.loc[i, "lag"]), float(t.loc[i, "corr"])


def slope(d, xc, yc, mask=None):
    ok = d[xc].notna() & d[yc].notna()
    if mask is not None:
        ok &= mask
    b = np.polyfit(d.loc[ok, yc], d.loc[ok, xc], 1)[0]
    return float(b), int(ok.sum())


def turning(d, cyc, col, suffix="_ma3", win=12):
    rows = []
    for _, r in cyc.iterrows():
        ref = pd.Timestamp(r["ym"][:4] + "-" + r["ym"][4:] + "-01")
        lo, hi = ref - pd.DateOffset(months=win), ref + pd.DateOffset(months=win)
        if lo < d["date"].min() or hi > d["date"].max():
            continue
        s = d[(d["date"] >= lo) & (d["date"] <= hi)].set_index("date")[col + suffix].dropna()
        t = s.idxmax() if r["kind"] == "山" else s.idxmin()
        rows.append({"kind": r["kind"], "ref": r["ym"], "turn": t.strftime("%Y%m"),
                     "months_from_ref": (t.year - ref.year) * 12 + t.month - ref.month})
    return pd.DataFrame(rows)


def turn_compare(d, cyc, ot, suffix):
    a = turning(d, cyc, ot, suffix)
    b = turning(d, cyc, "iip", suffix)
    m = a.merge(b, on=["kind", "ref"], suffixes=("_ot", "_iip"))
    m["ot_lead_months"] = m["months_from_ref_iip"] - m["months_from_ref_ot"]
    return m


def corr3(d, a, b, mask):
    ok = mask & d["ot_mfg5_m3"].notna() & d["iip_m3"].notna()
    ok &= (d["ym"] >= a) & (d["ym"] <= b)
    return float(np.corrcoef(d.loc[ok, "ot_mfg5_m3"], d.loc[ok, "iip_m3"])[0, 1]), int(ok.sum())


def main():
    d = load()
    cyc = pd.read_csv(BASE / "data" / "cycle_dates.csv", dtype={"ym": str})
    cyc = cyc[cyc["ym"] >= "199801"]
    noshock = ~d["ym"].map(in_shock)

    # H1 時差の相関
    tabs = {}
    for name, xc, yc, mask in [
        ("ot5_m1", "ot_mfg5_m1", "iip_m1", None),
        ("ot5_m3", "ot_mfg5_m3", "iip_m3", None),
        ("ot30_m1", "ot_mfg30_m1", "iip_m1", None),
        ("ot5_m1_noshock", "ot_mfg5_m1", "iip_m1", noshock),
        ("hours5_m1", "hours_mfg5_m1", "iip_m1", None),
        ("otall5_m1", "ot_all5_m1", "iip_m1", None),
    ]:
        tabs[name] = xcorr(d, xc, yc, mask)
    xc_all = pd.concat([t.assign(series=k) for k, t in tabs.items()])[["series", "lag", "corr", "n"]]
    xc_all.to_csv(RES / "xcorr.csv", index=False, float_format="%.4f")

    # H2 山・谷
    tc = turn_compare(d, cyc, "ot_mfg5", "_ma3")
    tc.to_csv(RES / "turning_points.csv", index=False)
    tc_raw = turn_compare(d, cyc, "ot_mfg5", "")
    tc_raw.to_csv(RES / "turning_points_raw.csv", index=False)
    tc30 = turn_compare(d, cyc, "ot_mfg30", "_ma3")
    tc30.to_csv(RES / "turning_points_30.csv", index=False)

    # H3 弾力性
    el = {}
    for name, xc, mask in [("ot5", "ot_mfg5_m3", None), ("ot30", "ot_mfg30_m3", None),
                           ("ot5_noshock", "ot_mfg5_m3", noshock), ("hours5", "hours_mfg5_m3", None)]:
        el[name] = slope(d, xc, "iip_m3", mask)
    # H4 期間別
    ex20 = ~d["ym"].between("202003", "202012")
    periods = [("1998-2008.03", "199801", "200803"), ("2008.04-2009.03", "200804", "200903"),
               ("2009.04-2019.03", "200904", "201903"), ("2019.04-2026.08", "201904", "202608")]
    per = []
    for lab, a, b in periods:
        c, k = corr3(d, a, b, ex20)
        okm = ex20 & d["ym"].between(a, b)
        s, _ = slope(d, "ot_mfg5_m3", "iip_m3", okm)
        per.append({"period": lab, "corr_m3": round(c, 4), "slope_m3": round(s, 4), "n": k})
    per = pd.DataFrame(per)
    per.to_csv(RES / "period_corr.csv", index=False)
    # 問い直し：生産1単位あたりの所定外（年平均）
    d["year"] = d["ym"].str[:4]
    yr = d.groupby("year")[["ot_mfg5", "iip", "hours_mfg5", "emp_mfg5"]].mean()
    yr = yr[d.groupby("year").size() == 12]
    yr["ot_per_iip"] = yr["ot_mfg5"] / yr["iip"] * 100
    # 所定外の総量の目安（1人あたり所定外指数×常用雇用指数）を生産で割る
    yr["ot_total_idx"] = yr["ot_mfg5"] * yr["emp_mfg5"] / 100
    yr["ot_total_per_iip"] = yr["ot_total_idx"] / yr["iip"] * 100
    yr.round(2).to_csv(RES / "annual_ratio.csv")
    # 原系列の水準の比較（大きな落ち込み）
    def drop(col, a, b):
        s = d[(d["ym"] >= a) & (d["ym"] <= b)].set_index("ym")[col]
        return float(s.min() / s.loc[a] * 100 - 100), s.idxmin()
    drops = {}
    for lab, a, b in [("2008", "200802", "200912"), ("2020", "202001", "202012")]:
        drops[lab] = {c: [round(x, 1) if isinstance(x, float) else x for x in drop(c, a, b)]
                      for c in ["ot_mfg5", "iip", "hours_mfg5"]}

    lag1, c1 = best(tabs["ot5_m1"])
    lead_peaks = tc[tc["kind"] == "山"]["ot_lead_months"]
    lead_tr = tc[tc["kind"] == "谷"]["ot_lead_months"]
    h4_pre = float(per.loc[per["period"] == "2009.04-2019.03", "corr_m3"].iloc[0])
    h4_post = float(per.loc[per["period"] == "2019.04-2026.08", "corr_m3"].iloc[0])
    t1 = tabs["ot5_m1"].set_index("lag")["corr"]
    res = {
        "period": [d["ym"].iloc[0], d["ym"].iloc[-1]], "n_months": int(len(d)),
        "H1": {"best_lag": lag1, "best_corr": r3(c1), "corr_lag0": r3(t1[0]), "corr_lag1": r3(t1[1]),
               "corr_lag-1": r3(t1[-1]), "result": "支持" if lag1 == 0 else "外れ"},
        "H1_m3_best": list(map(r3, best(tabs["ot5_m3"]))),
        "H2": {"peaks": tc[tc["kind"] == "山"][["ref", "turn_ot", "turn_iip", "ot_lead_months"]].to_dict("records"),
               "mean_lead_peaks": r3(lead_peaks.mean()),
               "troughs": tc[tc["kind"] == "谷"][["ref", "turn_ot", "turn_iip", "ot_lead_months"]].to_dict("records"),
               "mean_lead_troughs": r3(lead_tr.mean()),
               "result": "支持" if lead_peaks.mean() >= 1 else "外れ"},
        "H3": {"slope_m3": r3(el["ot5"][0]), "n": el["ot5"][1], "result": "支持" if el["ot5"][0] > 1.5 else "外れ"},
        "H4": {"corr_2009_2019": r3(h4_pre), "corr_2019_2026": r3(h4_post), "diff": r3(h4_pre - h4_post),
               "result": "支持" if h4_pre - h4_post >= 0.1 else "外れ"},
        "robust": {
            "R1_ot30_best_lag": list(map(r3, best(tabs["ot30_m1"]))),
            "R1_ot30_slope": r3(el["ot30"][0]),
            "R1_ot30_mean_lead_peaks": r3(tc30[tc30["kind"] == "山"]["ot_lead_months"].mean()),
            "R1_ot30_mean_lead_troughs": r3(tc30[tc30["kind"] == "谷"]["ot_lead_months"].mean()),
            "R2_noshock_best_lag": list(map(r3, best(tabs["ot5_m1_noshock"]))),
            "R2_noshock_slope": r3(el["ot5_noshock"][0]),
            "R3_raw_mean_lead_peaks": r3(tc_raw[tc_raw["kind"] == "山"]["ot_lead_months"].mean()),
            "R3_raw_mean_lead_troughs": r3(tc_raw[tc_raw["kind"] == "谷"]["ot_lead_months"].mean()),
            "R4_hours_best_lag": list(map(r3, best(tabs["hours5_m1"]))),
            "R4_hours_slope": r3(el["hours5"][0]),
            "R5_otall_best_lag": list(map(r3, best(tabs["otall5_m1"]))),
        },
        "drops": drops,
        "ratio": {y: r3(yr.loc[y, "ot_per_iip"]) for y in ["1998", "2007", "2010", "2019", "2023", "2025"] if y in yr.index},
        "ratio_total": {y: r3(yr.loc[y, "ot_total_per_iip"]) for y in ["1998", "2007", "2010", "2019", "2023", "2025"] if y in yr.index},
        "emp": {y: r3(yr.loc[y, "emp_mfg5"]) for y in ["1998", "2007", "2019", "2025"]},
        "period_table": per.to_dict("records"),
    }
    (RES / "main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
