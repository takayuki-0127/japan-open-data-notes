"""主な分析：最高時からの減り方、半分になるまでの年数、一定の率の当てはめ、0ABJ-IPによる置き換わり、仮説、頑健性。
年度末（3月末）の値を「年度」で呼ぶ（例：2026年3月末＝2025年度末）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
s = pd.read_csv(ROOT / "data" / "series.csv")
w = s.pivot(index="date", columns="series", values="value").sort_index()
wp = pd.read_csv(ROOT / "data" / "whitepaper.csv")


def fy_table(w, month="03"):
    a = w[w.index.str.endswith("-" + month)].copy()
    a.index = [int(i[:4]) - (1 if month == "03" else 0) for i in a.index]
    a.index.name = "fy" if month == "03" else "year"
    return a


a = fy_table(w)
a["fixed_plus_0abj"] = a.fixed_total + a.ip_0abj
a["other_than_ntt"] = a.fixed_total - a.ntt_total
a["yoy_fixed_pct"] = (a.fixed_total / a.fixed_total.shift(1) - 1) * 100
cols = ["fixed_total", "fixed_tel", "fixed_isdn", "ntt_total", "other_than_ntt", "ip_0abj", "ip_050",
        "fixed_plus_0abj", "mobile_phs", "mobile_phs_pen_pct", "yoy_fixed_pct"]
a[cols].round(3).to_csv(R / "by_fiscal_year.csv")
LAST = int(a.index.max())


def r(x, k=1):
    return round(float(x), k)


def loglin_rate(series, y0, y1):
    x = series.loc[y0:y1].dropna()
    b = np.polyfit(x.index.values.astype(float), np.log(x.values), 1)[0]
    return r((np.exp(b) - 1) * 100, 2)


def decline(series):
    x = series.dropna()
    pk = int(x.idxmax())
    half = next((int(y) for y in x.loc[pk:].index if x[y] <= x[pk] / 2), None)
    quarter = next((int(y) for y in x.loc[pk:].index if x[y] <= x[pk] / 4), None)
    return {"peak_fy": pk, "peak": r(x[pk]), "last": r(x.iloc[-1]), "change_from_peak_pct": r((x.iloc[-1] / x[pk] - 1) * 100),
            "half_fy": half, "quarter_fy": quarter}


main_dec = decline(a.fixed_total)
comb = decline(a.fixed_plus_0abj.dropna())
comb_all = decline(a.fixed_total.where(a.ip_0abj.isna(), a.fixed_plus_0abj))  # 0ABJ がない年は加入電話だけ
ipd = decline(a.ip_0abj)

# 置き換わりの割合
y0 = int(a.ip_0abj.dropna().index.min())
dec = a.fixed_total[y0] - a.fixed_total[LAST]
inc = a.ip_0abj[LAST] - a.ip_0abj[y0]
repl = {"from_fy": y0, "to_fy": LAST, "fixed_decrease": r(dec), "ip_0abj_increase": r(inc), "ratio_pct": r(100 * inc / dec)}
yoy = a.yoy_fixed_pct.loc[2008:LAST]
rate_main = loglin_rate(a.fixed_total, 2008, LAST)

hyp = {
    "H1": {"change_from_peak_pct": main_dec["change_from_peak_pct"], "verdict": "支持" if main_dec["change_from_peak_pct"] <= -80 else "外れ"},
    "H2": {"ratio_pct": repl["ratio_pct"], "verdict": "支持" if repl["ratio_pct"] >= 50 else "外れ"},
    "H3": {"combined_peak_fy": comb_all["peak_fy"], "combined_peak": comb_all["peak"], "combined_last": comb_all["last"],
           "change_pct": comb_all["change_from_peak_pct"], "verdict": "支持" if comb_all["change_from_peak_pct"] <= -20 else "外れ"},
    "H4": {"yoy_min": r(yoy.min(), 2), "yoy_max": r(yoy.max(), 2), "yoy_min_fy": int(yoy.idxmin()), "yoy_max_fy": int(yoy.idxmax()),
           "verdict": "支持" if (yoy.min() >= -10 and yoy.max() <= -5) else "外れ"},
}

# 頑健性
rob = []
dec_tab = a.copy()
for name, col in [("加入電話＋ISDN（本線）", "fixed_total"), ("加入電話だけ（ISDNを除く）", "fixed_tel"), ("ISDNだけ", "fixed_isdn"),
                  ("NTT東西だけ（2003年度末から）", "ntt_total"), ("NTT東西以外（直収電話・CATV電話など、2003年度末から）", "other_than_ntt")]:
    dd = decline(a[col].dropna())
    rob.append({"check": name, "peak_fy": dd["peak_fy"], "peak": dd["peak"], "last": dd["last"], "change_from_peak_pct": dd["change_from_peak_pct"],
                "rate_2008_2016": loglin_rate(a[col], 2008, 2016), "rate_2016_last": loglin_rate(a[col], 2016, LAST),
                "rate_2008_last": loglin_rate(a[col], 2008, LAST)})
dcm = fy_table(w, "12")
dd = decline(dcm.fixed_total.dropna())
rob.append({"check": f"12月末で比べる（{int(dcm.fixed_total.dropna().index.min())}年12月末から）", "peak_fy": dd["peak_fy"], "peak": dd["peak"], "last": dd["last"],
            "change_from_peak_pct": dd["change_from_peak_pct"], "rate_2008_2016": loglin_rate(dcm.fixed_total, 2008, 2016),
            "rate_2016_last": loglin_rate(dcm.fixed_total, 2016, int(dcm.index.max())), "rate_2008_last": loglin_rate(dcm.fixed_total, 2008, int(dcm.index.max()))})
rb = pd.DataFrame(rob)
rb.to_csv(R / "robustness.csv", index=False)

# 白書の値との照合（白書の年＝年度、最後の年は12月末）
chk = []
for _, q in wp.iterrows():
    y = int(q.year)
    ref = a.fixed_total.get(y) if y < 2025 else w.loc["2025-12", "fixed_total"]
    ref_ip = a.ip_0abj.get(y) if y < 2025 else w.loc["2025-12", "ip_0abj"]
    chk.append({"year": y, "fixed_wp": q.fixed_wp, "fixed_db": r(ref), "diff": r(q.fixed_wp - ref),
                "ip_0abj_wp": q.ip_0abj_wp, "ip_0abj_db": r(ref_ip), "diff_ip": r(q.ip_0abj_wp - ref_ip)})
ck = pd.DataFrame(chk)
ck.to_csv(R / "whitepaper_check.csv", index=False)

main = {
    "last_fy": LAST, "last_date": "2026-03",
    "fixed": main_dec,
    "fixed_yoy_last_pct": r(a.yoy_fixed_pct[LAST], 2),
    "fixed_rate_2008_last_pct": rate_main,
    "fixed_tel_last": r(a.fixed_tel[LAST]), "fixed_isdn_last": r(a.fixed_isdn[LAST]),
    "ip_0abj": ipd,
    "ip_0abj_first_fy": y0, "ip_0abj_first": r(a.ip_0abj[y0]),
    "fixed_plus_0abj": comb_all,
    "fixed_plus_0abj_since_ip": comb,
    "replacement": repl,
    "mobile_last": r(a.mobile_phs[LAST]), "mobile_pen_last_pct": r(a.mobile_phs_pen_pct[LAST]),
    "mobile_over_fixed_last": r(a.mobile_phs[LAST] / a.fixed_total[LAST], 1),
    "mobile_cross_fy": int(a.index[(a.mobile_phs > a.fixed_total)].min()),
    "fixed_per_mobile_peak_fy_ratio": r(a.mobile_phs[main_dec["peak_fy"]] / a.fixed_total[main_dec["peak_fy"]], 2),
    "whitepaper_max_abs_diff": r(ck["diff"].abs().max(), 1), "whitepaper_max_abs_diff_ip": r(ck["diff_ip"].abs().max(), 1),
    "hypotheses": hyp,
    "note": "単位は万（加入・件）。年度末＝翌年3月末。0ABJ-IPは番号の数で契約数ではない。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
