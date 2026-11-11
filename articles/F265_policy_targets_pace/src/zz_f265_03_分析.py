"""F265 03 分析：ペースの延ばし方3つ（M1 直近5点の直線・M2 直近5点のロジット直線・M3 直近10点の直線）で
策定時（2020年5月）といま（2026年11月）から目標の年を予測し、過去の外れで幅と「届く確率」を出す。"""
import json, pathlib
import numpy as np, pandas as pd

base = pathlib.Path(__file__).resolve().parents[1]
S = pd.read_csv(base / "data" / "processed" / "series.csv")
res = base / "results"; res.mkdir(exist_ok=True)
NAMES = {"male_leave": "男性の育児休業取得率", "paid_leave": "年次有給休暇取得率", "female_emp": "25〜44歳の女性の就業率"}
VINTAGE_2020 = 2020.41   # 2020年5月29日（大綱の閣議決定）
NOW = 2026.86            # 2026年11月11日

def logit(p): p = np.clip(p / 100, 1e-4, 1 - 1e-4); return np.log(p / (1 - p))
def expit(z): return 100 / (1 + np.exp(-z))

def fit_predict(years, vals, target_year, method, k=None):
    """直近 k 点で直線（またはロジット直線）を当て、target_year の値を返す。"""
    if method == "M1": k = k or 5; tr = "lin"
    elif method == "M2": k = k or 5; tr = "logit"
    elif method == "M3": k = k or 10; tr = "lin"
    else: raise ValueError(method)
    if len(years) < k: return np.nan
    x = np.asarray(years[-k:], float); y = np.asarray(vals[-k:], float)
    if tr == "logit": y = logit(y)
    b, a = np.polyfit(x, y, 1)
    p = a + b * target_year
    return float(expit(p)) if tr == "logit" else float(min(p, 100.0))

def series(ind, until=None, drop_break=False):
    d = S[S.indicator == ind].sort_values("year")
    if until is not None: d = d[d.published <= until]
    if drop_break == "paid_post2015": d = d[d.year >= 2014]  # 2015年調査以降（参照年2014〜）
    return d.year.to_numpy(), d.value.to_numpy()

def backtest_errors(ind, method, k=None, known_by=None, drop_break=False):
    """すべての起点 T（その点までの値で予測）から h 年先の外れ（実績−予測）。known_by 以前に結果が出たものだけ。"""
    d = S[S.indicator == ind].sort_values("year")
    if drop_break == "paid_post2015": d = d[d.year >= 2014]
    yrs, vals, pub = d.year.to_numpy(), d.value.to_numpy(), d.published.to_numpy()
    rows = []
    for i in range(len(yrs)):
        for j in range(i + 1, len(yrs)):
            if known_by is not None and pub[j] > known_by: continue
            h = int(yrs[j] - yrs[i])
            if h < 1 or h > 10: continue
            p = fit_predict(yrs[:i + 1], vals[:i + 1], yrs[j], method, k)
            if np.isnan(p): continue
            rows.append({"indicator": ind, "method": method, "origin": int(yrs[i]), "h": h, "pred": p, "actual": vals[j], "err": vals[j] - p})
    return pd.DataFrame(rows)

def interval(pred, errs, target):
    e = np.asarray(errs)
    lo, hi = np.percentile(e, 10), np.percentile(e, 90)
    prob = float(np.mean(np.minimum(pred + e, 100.0) >= target))
    return min(pred + lo, 100.0), min(pred + hi, 100.0), prob

TG = pd.read_csv(base / "data" / "raw" / "targets.csv")
out = {}

# ---------- 1. 策定時（2020年5月）の見通しと2025年の実績 ----------
rows = []
for ind in ["male_leave", "paid_leave", "female_emp"]:
    t = TG[(TG.indicator == ind) & (TG.plan.str.contains("2020"))].iloc[0]
    yrs, vals = series(ind, until=VINTAGE_2020)
    last_y, last_v = int(yrs[-1]), float(vals[-1])
    actual = S[(S.indicator == ind) & (S.year == t.target_year)].value
    actual = float(actual.iloc[0]) if len(actual) else np.nan
    for meth in ["M1", "M2", "M3"]:
        pred = fit_predict(yrs, vals, t.target_year, meth)
        h = int(t.target_year - last_y)
        E = backtest_errors(ind, meth, known_by=VINTAGE_2020)
        e = E[E.h == h].err
        pool = "own"
        if len(e) < 5:
            e = pd.concat([backtest_errors(x, meth, known_by=VINTAGE_2020) for x in NAMES]).query("h==@h").err; pool = "pooled"
        lo, hi, prob = interval(pred, e, t.target_value)
        rows.append({"indicator": ind, "name": NAMES[ind], "method": meth, "last_year": last_y, "last_value": last_v,
                     "target": t.target_value, "target_year": int(t.target_year), "h": h, "pred": round(pred, 2),
                     "lo80": round(lo, 2), "hi80": round(hi, 2), "p_reach": round(prob, 3), "n_err": int(len(e)), "err_pool": pool,
                     "actual": actual, "actual_in80": (lo <= actual <= hi) if not np.isnan(actual) else None,
                     "needed_per_year": round((t.target_value - last_v) / h, 2),
                     "past5_slope": round(np.polyfit(yrs[-5:], vals[-5:], 1)[0], 2)})
V20 = pd.DataFrame(rows); V20.to_csv(res / "A_vintage2020.csv", index=False)
print(V20.to_string())

# ---------- 2. いま（2026年11月）の見通し ----------
rows = []
future = [("male_leave", 85, 2030, "こども未来戦略（2023）"), ("paid_leave", 70, 2028, "過労死等防止大綱（2024）"),
          ("paid_leave", 70, 2025, "少子化社会対策大綱（2020）")]
for ind, tv, ty, plan in future:
    yrs, vals = series(ind, until=NOW)
    last_y, last_v = int(yrs[-1]), float(vals[-1])
    for meth in ["M1", "M2", "M3"]:
        pred = fit_predict(yrs, vals, ty, meth)
        h = int(ty - last_y)
        E = backtest_errors(ind, meth)
        e = E[E.h == h].err; pool = "own"
        if len(e) < 5:
            e = pd.concat([backtest_errors(x, meth) for x in NAMES]).query("h==@h").err; pool = "pooled"
        lo, hi, prob = interval(pred, e, tv)
        rows.append({"indicator": ind, "name": NAMES[ind], "plan": plan, "method": meth, "last_year": last_y, "last_value": last_v,
                     "target": tv, "target_year": ty, "h": h, "pred": round(pred, 2), "lo80": round(lo, 2), "hi80": round(hi, 2),
                     "p_reach": round(prob, 3), "n_err": int(len(e)), "err_pool": pool,
                     "needed_per_year": round((tv - last_v) / h, 2), "past5_slope": round(np.polyfit(yrs[-5:], vals[-5:], 1)[0], 2)})
NOWDF = pd.DataFrame(rows); NOWDF.to_csv(res / "B_now.csv", index=False)
print(NOWDF.to_string())

# ---------- 3. 過去の外れ（全部） ----------
ALL = pd.concat([backtest_errors(i, m) for i in NAMES for m in ["M1", "M2", "M3"]])
ALL.to_csv(res / "C_backtest_errors.csv", index=False)
summ = ALL.groupby(["indicator", "method", "h"]).err.agg(n="count", mean="mean", mae=lambda x: np.mean(np.abs(x)),
                                                           p10=lambda x: np.percentile(x, 10), p90=lambda x: np.percentile(x, 90)).reset_index()
summ.round(3).to_csv(res / "C_backtest_summary.csv", index=False)

# ---------- 4. 仮説の判定 ----------
m1 = V20[V20.method == "M1"]
H1_n = int((m1.pred >= m1.target).sum())
known = m1[m1.actual.notna()]
H2_in = int(known.actual_in80.sum()); H2_n = len(known)
mm = NOWDF[(NOWDF.indicator == "male_leave") & (NOWDF.method == "M1")].iloc[0]
H3_p = float(mm.p_reach)
flip = {}
for (ind, ty), g in NOWDF.groupby(["indicator", "target_year"]):
    verdict = (g.pred >= g.target).tolist(); flip[f"{ind}_{ty}"] = {"methods": g.method.tolist(), "reach": verdict, "flip": len(set(verdict)) > 1}
H4_any = any(v["flip"] for k, v in flip.items() if k in ("male_leave_2030", "paid_leave_2028"))
out["hypotheses"] = {
    "H1": {"reach_count_M1": H1_n, "of": 3, "supported": H1_n <= 1},
    "H2": {"in80": H2_in, "of": H2_n, "supported": H2_in > H2_n / 2},
    "H3": {"p_reach_male_2030_M1": H3_p, "supported": H3_p >= 0.5},
    "H4": {"detail": flip, "supported": H4_any},
}

# ---------- 5. 頑健性 ----------
rob = []
for k in [3, 5, 7, 10]:
    for ind, tv, ty, until, tag in [("male_leave", 30, 2025, VINTAGE_2020, "2020時点→2025"), ("paid_leave", 70, 2025, VINTAGE_2020, "2020時点→2025"),
                                    ("female_emp", 82, 2025, VINTAGE_2020, "2020時点→2025"), ("male_leave", 85, 2030, NOW, "いま→2030"),
                                    ("paid_leave", 70, 2028, NOW, "いま→2028")]:
        yrs, vals = series(ind, until=until)
        rob.append({"check": f"窓{k}点（直線）", "indicator": ind, "tag": tag, "pred": round(fit_predict(yrs, vals, ty, "M1", k), 2), "target": tv})
        rob.append({"check": f"窓{k}点（ロジット）", "indicator": ind, "tag": tag, "pred": round(fit_predict(yrs, vals, ty, "M2", k), 2), "target": tv})
# 段差：男性育休 2022年度まで（産後パパ育休の前）で 2030
yrs, vals = series("male_leave", until=NOW); msk = yrs <= 2022
for meth in ["M1", "M2", "M3"]:
    rob.append({"check": "男性育休 2022年度までで延ばす", "indicator": "male_leave", "tag": "→2030", "pred": round(fit_predict(yrs[msk], vals[msk], 2030, meth), 2), "target": 85, "method": meth})
# 段差：有給 2015年調査以降だけで外れを作る
for ty in [2025, 2028]:
    yrs, vals = series("paid_leave", until=NOW)
    pred = fit_predict(yrs, vals, ty, "M1"); h = int(ty - yrs[-1])
    e = backtest_errors("paid_leave", "M1", drop_break="paid_post2015").query("h==@h").err
    if len(e) >= 3:
        lo, hi, pr = interval(pred, e, 70)
        rob.append({"check": "有給 外れを2015年調査以降だけで", "indicator": "paid_leave", "tag": f"→{ty}", "pred": round(pred, 2), "lo80": round(lo, 2), "hi80": round(hi, 2), "p_reach": round(pr, 3), "n_err": len(e), "target": 70})
# 外れを3指標まとめる
for ind, tv, ty, until in [("male_leave", 85, 2030, NOW), ("paid_leave", 70, 2028, NOW), ("male_leave", 30, 2025, VINTAGE_2020), ("paid_leave", 70, 2025, VINTAGE_2020), ("female_emp", 82, 2025, VINTAGE_2020)]:
    yrs, vals = series(ind, until=until); pred = fit_predict(yrs, vals, ty, "M1"); h = int(ty - yrs[-1])
    kb = VINTAGE_2020 if until == VINTAGE_2020 else None
    e = pd.concat([backtest_errors(x, "M1", known_by=kb) for x in NAMES]).query("h==@h").err
    lo, hi, pr = interval(pred, e, tv)
    rob.append({"check": "外れを3指標まとめる", "indicator": ind, "tag": f"→{ty}", "pred": round(pred, 2), "lo80": round(lo, 2), "hi80": round(hi, 2), "p_reach": round(pr, 3), "n_err": len(e), "target": tv})
# 女性就業率：公表値（四捨五入）を使った場合の2020時点予測
off = pd.read_csv(base / "data" / "processed" / "female_emp_check.csv")
oy = off[off.year.between(2015, 2019)]
b, a = np.polyfit(oy.year, oy.official, 1)
rob.append({"check": "女性就業率 公表値（2015〜19）で直線", "indicator": "female_emp", "tag": "2020時点→2025", "pred": round(a + b * 2025, 2), "target": 82})
ROB = pd.DataFrame(rob); ROB.to_csv(res / "D_robustness.csv", index=False)

# ---------- 6. 問いの立て直し：目標は「それまでのペースの何倍」を求めていたか ----------
VINT = {"少子化社会対策大綱（2015）": 2015.21, "少子化社会対策大綱（2020）": VINTAGE_2020, "こども未来戦略（2023）": 2023.97, "過労死等の防止のための対策に関する大綱（2024）": 2024.59}
rows = []
for _, t in TG.iterrows():
    v = VINT[t.plan]; yrs, vals = series(t.indicator, until=v)
    last_y, last_v = int(yrs[-1]), float(vals[-1]); h = int(t.target_year - last_y)
    slope5 = float(np.polyfit(yrs[-5:], vals[-5:], 1)[0])
    need = (t.target_value - last_v) / h
    act = S[(S.indicator == t.indicator) & (S.year == t.target_year)].value
    act = float(act.iloc[0]) if len(act) else np.nan
    later = S[(S.indicator == t.indicator) & (S.year > last_y) & (S.year <= t.target_year)].sort_values("year")
    act_slope = (float(later.value.iloc[-1]) - last_v) / (int(later.year.iloc[-1]) - last_y) if len(later) else np.nan
    rows.append({"indicator": t.indicator, "name": NAMES[t.indicator], "plan": t.plan, "target": t.target_value, "target_year": int(t.target_year),
                 "info_last_year": last_y, "info_last_value": last_v, "years_left": h, "past5_slope": round(slope5, 3),
                 "needed_slope": round(need, 3), "ratio_needed_to_past": round(need / slope5, 2) if slope5 > 0 else np.nan,
                 "actual_at_target": act, "reached": (act >= t.target_value) if not np.isnan(act) else None,
                 "actual_slope_so_far": round(act_slope, 3) if not np.isnan(act_slope) else np.nan,
                 "latest_year": int(later.year.iloc[-1]) if len(later) else None})
RQ = pd.DataFrame(rows); RQ.to_csv(res / "E_reask_required_pace.csv", index=False)
print(RQ.to_string())
out["reask"] = RQ.to_dict(orient="records")

# ---------- 7. レビュー後の追加：2020年時点の有給 2024年の幅（実績 66.9% と同じ年で比べる） ----------
rows = []
yrs, vals = series("paid_leave", until=VINTAGE_2020)
for meth in ["M1", "M2", "M3"]:
    pred = fit_predict(yrs, vals, 2024, meth); h = int(2024 - yrs[-1])
    e = backtest_errors("paid_leave", meth, known_by=VINTAGE_2020).query("h==@h").err
    lo, hi, pr = interval(pred, e, 70)
    rows.append({"method": meth, "year": 2024, "h": h, "pred": round(pred, 2), "lo80": round(lo, 2), "hi80": round(hi, 2), "n_err": len(e),
                 "actual": float(S[(S.indicator == "paid_leave") & (S.year == 2024)].value.iloc[0])})
pd.DataFrame(rows).to_csv(res / "F_ref_paid2024_vintage2020.csv", index=False)

out["vintage2020"] = V20.to_dict(orient="records")
out["now"] = NOWDF.to_dict(orient="records")
(res / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
print(json.dumps(out["hypotheses"], ensure_ascii=False, indent=1, default=float))
print(ROB.to_string())
