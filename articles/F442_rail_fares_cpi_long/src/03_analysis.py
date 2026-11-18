"""月次の「値段が変わった月」、税を除いた水準、仮説の判定、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
m = pd.read_csv(ROOT / "data" / "monthly.csv").set_index("period")
a = pd.read_csv(ROOT / "data" / "annual.csv").set_index("year")
TAXM = [198904, 199704, 201404, 201910]


def taxrate(p):
    return 0.0 if p < 198904 else 0.03 if p < 199704 else 0.05 if p < 201404 else 0.08 if p < 201910 else 0.10


tax = pd.Series([taxrate(p) for p in m.index], index=m.index)
KEYS = ["jr_regular", "jr_commuter", "jr_school", "jr_class", "pr_regular", "pr_commuter", "pr_school", "pr_class", "bus", "taxi", "services", "public_services", "all_items"]
mom = (m[KEYS] / m[KEYS].shift(1) - 1) * 100
ex = m[KEYS].div(1 + tax, axis=0) * 1.10           # 税を除いた指数（2025年の税率10%の水準にそろえる）
# 段差で割る方法：消費税の月の前月比をなかったことにしてつなぐ
ex2 = m[KEYS].copy()
for k in KEYS:
    r = (m[k] / m[k].shift(1)).copy()
    r.loc[TAXM] = 1.0
    ex2[k] = r.fillna(1.0).cumprod() * np.nan
    s = m[k].first_valid_index()
    rr = r.loc[s:]; rr.iloc[0] = 1.0
    ex2.loc[s:, k] = m.loc[s, k] * rr.cumprod()
ex2 = ex2 / ex2.loc[202501:202512].mean() * 100   # 2025年平均＝100 に


def changes(k, thr=0.5, start=197502, end=202609):
    s = mom.loc[start:end, k].dropna()
    c = s[s.abs() >= thr]
    return pd.DataFrame({"item": k, "period": c.index, "mom": c.values.round(3), "tax_month": [p in TAXM for p in c.index]})


ch = pd.concat([changes(k) for k in ["jr_regular", "jr_commuter", "jr_school", "pr_regular", "pr_commuter", "pr_school", "bus", "taxi"]])
ch.to_csv(R / "change_months.csv", index=False)


def pct(s, p0, p1):
    return float((s.loc[p1] / s.loc[p0] - 1) * 100)


# 仮説
h1 = changes("jr_regular", 0.5, 199705, 202302)
h1_up = h1[h1.mom >= 0.5]
h1_nontax = h1_up[~h1_up.tax_month]
h2 = pct(ex.jr_regular, 199704, 202302)
h3 = float(mom.loc[202603, "jr_regular"])
h4_jr = pct(ex.jr_regular, 199704, 202609); h4_pr = pct(ex.pr_regular, 199704, 202609)
hyp = {
    "H1": {"up_months": [int(p) for p in h1_up.period], "non_tax_up_months": [int(p) for p in h1_nontax.period],
           "result": "支持" if len(h1_nontax) == 0 else "外れ"},
    "H2": {"taxex_change_199704_202302": round(h2, 2), "result": "支持" if abs(h2) <= 3 else "外れ"},
    "H3": {"mom_202603": round(h3, 2), "result": "支持" if h3 >= 5 else "外れ"},
    "H4": {"jr_taxex_199704_202609": round(h4_jr, 2), "pr_taxex_199704_202609": round(h4_pr, 2), "result": "支持" if h4_pr > h4_jr else "外れ"},
}

# 主な数字
ev = {}
for p in [198904, 199704, 201404, 201910, 202303, 202603]:
    ev[p] = {k: round(float(mom.loc[p, k]), 2) for k in ["jr_regular", "jr_commuter", "jr_school", "pr_regular", "pr_commuter", "pr_school", "bus", "taxi", "services"]}
# 期間の変化（税込み・税抜き）
spans = [(198704, 202602), (199704, 202602), (199704, 202609), (198704, 202609), (202202, 202609)]
lv = []
for p0, p1 in spans:
    for k in ["jr_regular", "jr_commuter", "pr_regular", "pr_commuter", "bus", "taxi", "services", "all_items"]:
        lv.append({"span": f"{p0}-{p1}", "item": k, "with_tax": round(pct(m[k], p0, p1), 2), "tax_excluded": round(pct(ex[k], p0, p1), 2),
                   "tax_month_removed": round(pct(ex2[k], p0, p1), 2)})
lvdf = pd.DataFrame(lv); lvdf.to_csv(R / "span_changes.csv", index=False)
L = lvdf.set_index(["span", "item"])

# 年平均（暦年の表）で並べる
ann = a[["jr_regular", "pr_regular", "bus", "taxi", "services", "all_items"]]
ann_tbl = {f"{y0}-{y1}": {k: round(float((ann.loc[y1, k] / ann.loc[y0, k] - 1) * 100), 1) for k in ann.columns} for y0, y1 in [(1975, 1987), (1987, 1997), (1997, 2025), (1987, 2025)]}
# 税を除いた年平均（月次の税抜き指数の暦年平均）
ex_y = ex.groupby(ex.index // 100).mean()
ex_y.loc[1975:2025, ["jr_regular", "jr_commuter", "pr_regular", "pr_commuter", "bus", "taxi", "services", "all_items"]].round(3).to_csv(R / "annual_tax_excluded.csv")
# 「変わらなかった」期間の長さ：普通運賃（JR）の前月比が |0.5%| 未満のまま続いた最長の月数（税の月を除いて数える）
def longest_flat(k, thr=0.5, skip_tax=True):
    s = mom.loc[197502:, k].dropna()
    best = cur = 0; best_end = None
    for p, v in s.items():
        if abs(v) < thr or (skip_tax and p in TAXM):
            cur += 1
            if cur > best:
                best, best_end = cur, p
        else:
            cur = 0
    return best, int(best_end)
flat = {k: longest_flat(k) for k in ["jr_regular", "jr_commuter", "pr_regular", "bus", "taxi"]}

# 頑健性
rob = []
for thr in [0.3, 0.5, 1.0]:
    c = changes("jr_regular", thr, 199705, 202302); up = c[c.mom >= thr]
    rob.append({"check": f"しきい値 {thr}%（普通運賃 JR）", "up_months_non_tax": int((~up.tax_month).sum()), "up_months_tax": int(up.tax_month.sum()),
                "taxex_change": round(h2, 2)})
for k, nm in [("jr_commuter", "通勤定期 JR"), ("jr_school", "通学定期 JR"), ("jr_class", "鉄道運賃（JR の類）")]:
    c = changes(k, 0.5, 199705, 202302); up = c[c.mom >= 0.5]
    rob.append({"check": f"品目を{nm}に", "up_months_non_tax": int((~up.tax_month).sum()), "up_months_tax": int(up.tax_month.sum()),
                "taxex_change": round(pct(ex[k], 199704, 202302), 2)})
c = changes("jr_regular", 0.5, 198705, 202302); up = c[c.mom >= 0.5]
rob.append({"check": "始まりを1987年4月（JR の発足）に", "up_months_non_tax": int((~up.tax_month).sum()), "up_months_tax": int(up.tax_month.sum()),
            "taxex_change": round(pct(ex.jr_regular, 198704, 202302), 2)})
rob.append({"check": "税の月の段差をなかったことにして計算（1997年4月→2023年2月）", "up_months_non_tax": np.nan, "up_months_tax": np.nan,
            "taxex_change": round(pct(ex2.jr_regular, 199704, 202302), 2)})
robdf = pd.DataFrame(rob); robdf.to_csv(R / "robustness.csv", index=False)

# 2026年3月以降の水準
lev26 = {k: {"202602": round(float(m.loc[202602, k]), 1), "202603": round(float(m.loc[202603, k]), 1), "202609": round(float(m.loc[202609, k]), 1)} for k in ["jr_regular", "jr_commuter", "jr_school", "pr_regular"]}
main = {
    "hypotheses": hyp,
    "events_mom": {str(k): v for k, v in ev.items()},
    "span_changes": {f"{s}|{i}": L.loc[(s, i)].to_dict() for s, i in L.index},
    "annual_cy_changes": ann_tbl,
    "longest_flat_months": {k: {"months": v[0], "ended": v[1]} for k, v in flat.items()},
    "levels_2026": lev26,
    "n_change_months_jr_regular_197502_202609": int(len(changes("jr_regular"))),
    "jr_regular_change_months_all": [[int(r.period), float(r.mom), bool(r.tax_month)] for r in changes("jr_regular").itertuples()],
    "pr_regular_change_months_all": [[int(r.period), float(r.mom), bool(r.tax_month)] for r in changes("pr_regular").itertuples()],
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: main[k] for k in ["hypotheses", "events_mom", "annual_cy_changes", "longest_flat_months", "levels_2026", "jr_regular_change_months_all", "pr_regular_change_months_all"]}, ensure_ascii=False))
print(robdf.to_string()); print(lvdf.to_string())
