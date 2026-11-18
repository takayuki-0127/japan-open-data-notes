"""利上げ（と利下げ）の出来事ごとに、預金金利の時差と追随の比を出す（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DEP = ["ordinary", "td3m", "td1y", "td5y", "td1y_large"]
LABEL = {"ordinary": "普通預金", "td3m": "定期3か月（300万円未満）", "td1y": "定期1年（300万円未満）",
         "td5y": "定期5年（300万円未満）", "td1y_large": "定期1年（1千万円以上）",
         "new_td_small": "定期・新規受入（300万円未満）", "new_td_large": "定期・新規受入（1千万円以上）", "new_td_all": "定期・新規受入（総合）"}
CYCLES = {"局面1（2006/6→2008/9）": ("200606", "200809"), "局面2（2024/2→2026/10）": ("202402", "202610")}

def load():
    df = pd.read_csv(ROOT / "data" / "monthly.csv", dtype={"ym": str}).set_index("ym")
    return df

def find_events(call, step=0.07, sign=1, start="199401", end=None):
    d = call.diff()
    idx = list(call.index)
    hits = [m for m in idx if m >= start and (end is None or m <= end) and pd.notna(d[m]) and sign * d[m] >= step]
    events, cur = [], []
    for m in hits:
        if cur and idx.index(m) == idx.index(cur[-1]) + 1:
            cur.append(m)
        else:
            if cur: events.append(cur)
            cur = [m]
    if cur: events.append(cur)
    out = []
    for ev in events:
        s, e = ev[0], ev[-1]
        i_pre = idx.index(s) - 1
        i_post = min(idx.index(e) + 1, len(call.dropna()) - 1)
        out.append({"start": s, "end": e, "pre": idx[i_pre], "post": idx[i_post],
                    "size": float(call.iloc[i_post] - call.iloc[i_pre])})
    # 月末の値は月末だけの振れがあるので、前の月→最後の月の翌月で見ても動いた出来事だけ残す
    out = [o for o in out if sign * o["size"] >= step]
    for k in range(len(out)):
        out[k]["next_pre"] = out[k + 1]["pre"] if k + 1 < len(out) else None
    return out

def event_table(df, call_col="call_avg", thr=0.005, sign=1, start="199401", end=None, deps=DEP):
    call = df[call_col].dropna()
    evs = find_events(call, sign=sign, start=start, end=end)
    idx = list(df.index)
    rows = []
    for ev in evs:
        ip = idx.index(ev["pre"])
        lim = idx.index(ev["next_pre"]) if ev["next_pre"] else len(idx) - 1
        for c in deps:
            s = df[c]
            if pd.isna(s.iloc[ip]):
                continue
            base = s.iloc[ip]
            lag = None
            for h in range(0, 13):
                j = idx.index(ev["start"]) + h
                if j >= len(idx) or pd.isna(s.iloc[j]):
                    break
                if sign * (s.iloc[j] - base) >= thr - 1e-12:
                    lag = h; break
            r = {"event": ev["start"], "pre": ev["pre"], "call_change": round(ev["size"], 4), "series": c, "label": LABEL[c],
                 "base": base, "lag_months": lag}
            for h in (1, 3, 6):
                j = ip + h
                ok = j <= lim and j < len(idx) and pd.notna(s.iloc[j])
                r[f"dep_change_h{h}"] = round(float(s.iloc[j] - base), 4) if ok else None
                r[f"ratio_h{h}"] = round(float((s.iloc[j] - base) / ev["size"]), 3) if ok else None
            rows.append(r)
    return pd.DataFrame(rows), evs

def cycle_table(df, call_col="call_avg", deps=DEP, cycles=CYCLES):
    rows = []
    for name, (a, b) in cycles.items():
        dc = df.loc[b, call_col] - df.loc[a, call_col]
        for c in deps:
            if pd.isna(df.loc[a, c]) or pd.isna(df.loc[b, c]):
                continue
            dd = df.loc[b, c] - df.loc[a, c]
            rows.append({"cycle": name, "from": a, "to": b, "series": c, "label": LABEL[c], "call_change": round(dc, 4),
                         "dep_from": df.loc[a, c], "dep_to": df.loc[b, c], "dep_change": round(dd, 4), "ratio": round(dd / dc, 3)})
    return pd.DataFrame(rows)

def dist_lag(df, c, a, b, K=6, call_col="call_avg"):
    d = df[[call_col, c]].astype(float).diff()
    X = pd.concat({f"L{k}": d[call_col].shift(k) for k in range(K + 1)}, axis=1)
    y = d[c]
    sub = pd.concat([y, X], axis=1).loc[a:b].dropna()
    sub = sub.loc[sub.index > a]
    m = sm.OLS(sub[c], sm.add_constant(sub[[f"L{k}" for k in range(K + 1)]])).fit()
    cum = float(sum(m.params[f"L{k}"] for k in range(K + 1)))
    R = np.zeros(len(m.params)); R[1:] = 1
    se = float(np.sqrt(R @ m.cov_params().values @ R))
    return {"series": c, "n": int(m.nobs), "cum": round(cum, 3), "cum_se": round(se, 3),
            "b0": round(float(m.params["L0"]), 3), "b1": round(float(m.params["L1"]), 3)}

def main():
    df = load()
    ev, evs = event_table(df)
    ev.to_csv(RES / "events_hikes.csv", index=False)
    cyc = cycle_table(df)
    cyc.to_csv(RES / "cycles.csv", index=False)
    # 新規受入分（IR03）も局面で
    cyc_new = cycle_table(df, deps=["new_td_small", "new_td_large"],
                          cycles={"局面1（2006/6→2008/9）": ("200606", "200809"), "局面2（2024/2→2026/9）": ("202402", "202609")})
    cyc_new.to_csv(RES / "cycles_new_deposits.csv", index=False)
    dl = []
    for name, (a, b) in CYCLES.items():
        for c in DEP:
            r = dist_lag(df, c, a, b); r["cycle"] = name; r["label"] = LABEL[c]; dl.append(r)
    dl = pd.DataFrame(dl); dl.to_csv(RES / "dist_lag.csv", index=False)

    # 局面2：出来事ごとの普通預金
    ev2 = ev[(ev.event >= "202401")]
    ordn = ev[ev.series == "ordinary"]
    main = {
        "period": [df.index[0], df.index[-1]],
        "events": [{k: v for k, v in e.items()} for e in evs],
        "n_events": len(evs),
        "cycle": {f"{r.cycle}|{r.series}": {"ratio": r.ratio, "dep_change": r.dep_change, "call_change": r.call_change,
                                            "dep_from": r.dep_from, "dep_to": r.dep_to} for r in cyc.itertuples()},
        "cycle_new": {f"{r.cycle}|{r.series}": {"ratio": r.ratio, "dep_change": r.dep_change, "call_change": r.call_change} for r in cyc_new.itertuples()},
        "lag_ordinary": {r.event: r.lag_months for r in ordn.itertuples()},
        "lag_share_within2": round(float((ev.lag_months.notna() & (ev.lag_months <= 2)).mean()), 3),
        "lag_share_3plus_or_none": round(float((ev.lag_months.isna() | (ev.lag_months >= 3)).mean()), 3),
        "lag_median_cycle2": float(ev2.lag_months.median()),
        "ratio_h3_ordinary_cycle2_mean": round(float(ev2[ev2.series == "ordinary"].ratio_h3.mean()), 3),
        "ratio_h3_ordinary_cycle1_mean": round(float(ev[(ev.series == "ordinary") & (ev.event.between("200601", "200812"))].ratio_h3.mean()), 3),
        "dist_lag": {f"{r.cycle}|{r.series}": {"cum": r.cum, "cum_se": r.cum_se, "n": r.n} for r in dl.itertuples()},
        "latest": {c: float(df[c].dropna().iloc[-1]) for c in DEP + ["call_avg"]},
        "latest_month": {c: df[c].dropna().index[-1] for c in DEP + ["call_avg"]},
    }
    # 仮説の判定
    c1, c2 = "局面1（2006/6→2008/9）", "局面2（2024/2→2026/10）"
    g = lambda cy, s: main["cycle"][f"{cy}|{s}"]["ratio"]
    main["H1_ordinary_cycle2_ratio"] = g(c2, "ordinary")
    main["H1"] = "支持" if g(c2, "ordinary") <= 0.33 else "外れ"
    order_ok = {cy: (g(cy, "td5y") > g(cy, "td1y") > g(cy, "td3m") > g(cy, "ordinary")) for cy in (c1, c2)}
    main["H2_order"] = order_ok
    main["H2"] = "支持" if all(order_ok.values()) else "外れ"
    main["H3"] = "支持" if g(c2, "ordinary") > g(c1, "ordinary") else "外れ"
    main["H4"] = "外れ" if main["lag_share_3plus_or_none"] >= 0.5 else "支持"
    (RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # 頑健性
    rob = []
    for cy in (c1, c2):
        for s in ("ordinary", "td1y"):
            rob.append({"check": "基本（月平均のコール、局面の累計の比）", "cycle": cy, "series": LABEL[s], "value": g(cy, s)})
    cyc_end = cycle_table(df, call_col="call_end")
    for r in cyc_end[cyc_end.series.isin(["ordinary", "td1y"])].itertuples():
        rob.append({"check": "R1 コールを月末の値に", "cycle": r.cycle, "series": r.label, "value": r.ratio})
    for r in cyc_new.itertuples():
        rob.append({"check": "R3 新規受入分の定期預金の平均金利（局面2は2026/9まで）", "cycle": r.cycle, "series": r.label, "value": r.ratio})
    cyc_r4 = cycle_table(df, cycles={c2 + "→2025/12で打ち切り": ("202402", "202512")})
    for r in cyc_r4[cyc_r4.series.isin(["ordinary", "td1y"])].itertuples():
        rob.append({"check": "R4 局面2を2025/12で打ち切る", "cycle": r.cycle, "series": r.label, "value": r.ratio})
    # レビューで追加：直前の利上げが映りきった月（次の利上げの前の月）で打ち切る
    cyc_r5 = cycle_table(df, cycles={c2 + "→2025/11で打ち切り": ("202402", "202511"), c2 + "→2026/5で打ち切り": ("202402", "202605")})
    for r in cyc_r5[cyc_r5.series.isin(["ordinary", "td1y"])].itertuples():
        rob.append({"check": "R5 局面2を次の利上げの前の月で打ち切る（レビューで追加）", "cycle": r.cycle, "series": r.label, "value": r.ratio})
    ev_r2, _ = event_table(df, thr=0.01)
    ev_end, _ = event_table(df, call_col="call_end")
    for name, e in (("基本（0.005ポイント）", ev), ("R2 基準0.01ポイント", ev_r2), ("R1 コール月末で出来事を決める", ev_end)):
        rob.append({"check": f"時差 {name}：3か月以上・動かずの割合", "cycle": "全出来事", "series": "5系列", "value": round(float((e.lag_months.isna() | (e.lag_months >= 3)).mean()), 3)})
        rob.append({"check": f"時差 {name}：時差の中央値（か月）", "cycle": "全出来事", "series": "5系列", "value": float(e.lag_months.median())})
    pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
    print(json.dumps({k: main[k] for k in ["n_events", "H1", "H2", "H3", "H4", "H1_ordinary_cycle2_ratio", "H2_order", "lag_share_within2", "lag_share_3plus_or_none"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
