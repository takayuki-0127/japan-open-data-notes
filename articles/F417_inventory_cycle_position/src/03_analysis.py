"""在庫循環図の局面と、景気の山・谷（拡張期・後退期）の照合。
出力：results/*.csv、results/main.json"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
q = pd.read_csv(ROOT / "data" / "iip_quarterly.csv", dtype={"code": str})
mo = pd.read_csv(ROOT / "data" / "iip_monthly.csv", dtype={"code": str, "period": str})
cd = pd.read_csv(ROOT / "data" / "cycle_dates.csv")
r1 = lambda x: float(round(x, 1)); r2 = lambda x: float(round(x, 2)); r3 = lambda x: float(round(x, 3))
SPLICE_MAIN = {2010: ("2009Q1", "2013Q4"), 2015: ("2014Q1", "2018Q4"), 2020: ("2019Q1", "2099Q4")}
SPLICE_ALT = {2010: ("2009Q1", "2013Q4"), 2015: ("2014Q1", "2022Q4"), 2020: ("2023Q1", "2099Q4")}
PHASES = ["回復", "積み増し", "積み上がり", "調整"]
EVAL_END = "2020Q2"  # 景気の谷（2020年5月）が決まっている最後の四半期


def yoy_q(name, series, splice, base_filter=None):
    parts = []
    for base, (a, b) in splice.items():
        d = q[(q.base == base) & (q.series == series) & (q.name == name)].set_index("period").value.sort_index()
        if d.empty:
            continue
        y = (d / d.shift(4) - 1) * 100
        # 四半期が抜けなく続いていること（4期前がちょうど1年前）を確かめる
        per = pd.PeriodIndex(d.index, freq="Q")
        assert all((per[1:] - per[:-1]).map(lambda z: z.n) == 1), (name, series, base)
        parts.append(y[(y.index >= a) & (y.index <= b)])
    return pd.concat(parts).dropna()


def phase(x, y):
    if x > 0 and y <= 0:
        return "回復"
    if x > 0 and y > 0 and x >= y:
        return "積み増し"
    if y > 0 and y > x:
        return "積み上がり"
    return "調整"


# 景気の局面（月）→ 四半期（3か月のうち2か月以上が後退なら後退期）
months = pd.period_range("2008-01", "2026-12", freq="M")
rec = pd.Series(False, index=months)
for _, r in cd.iterrows():
    pk = pd.Period(r.peak, "M"); tr = pd.Period(r.trough_end, "M")
    rec[(rec.index > pk) & (rec.index <= tr)] = True
recq = rec.groupby(rec.index.asfreq("Q")).sum() >= 2
recq.index = [str(p) for p in recq.index]


def auc(score, lab):
    """後退期（lab=True）の score が拡張期より大きい確率（同点は半分）"""
    s1 = score[lab].values; s0 = score[~lab].values
    gt = (s1[:, None] > s0[None, :]).sum() + 0.5 * (s1[:, None] == s0[None, :]).sum()
    return gt / (len(s1) * len(s0))


def evaluate(x, y, end=None, label=""):
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    if end:
        df = df[df.index <= end]
    df["phase"] = [phase(a, b) for a, b in zip(df.x, df.y)]
    df["recession"] = recq.reindex(df.index).fillna(False).astype(bool)
    df["gap"] = df.x - df.y
    rec_ = df[df.recession]; exp_ = df[~df.recession]
    exp_eval = exp_[exp_.index <= EVAL_END]
    res = {
        "label": label, "n": int(len(df)), "n_rec": int(len(rec_)), "n_exp_designated": int(len(exp_eval)),
        "rec_in_upper_or_adjust_pct": float(rec_.phase.isin(["積み上がり", "調整"]).mean() * 100),
        "exp_in_recovery_or_build_pct": float(exp_eval.phase.isin(["回復", "積み増し"]).mean() * 100),
        "auc_gap": float(auc(-df.gap, df.recession)), "auc_x": float(auc(-df.x, df.recession)),
        "auc_y": float(auc(df.y, df.recession)),
    }
    return df, res


# ---- 本線：鉱工業、出荷 × 在庫（期末）、つなぎ方は本線
X = yoy_q("鉱工業", "shipment", SPLICE_MAIN)
Y = yoy_q("鉱工業", "inventory", SPLICE_MAIN)
P = yoy_q("鉱工業", "production", SPLICE_MAIN)
main_df, main_res = evaluate(X, Y, label="本線：鉱工業・出荷×在庫")
main_df["production_yoy"] = P.reindex(main_df.index)
main_df.round(4).to_csv(RES / "quarterly_cycle.csv", index_label="quarter")

# 局面ごとの数（拡張・後退）
tab = pd.crosstab(main_df.phase, main_df.recession.map({True: "後退期", False: "拡張期"})).reindex(PHASES).fillna(0).astype(int)
tab.to_csv(RES / "phase_by_cycle.csv")

# 反時計回り：連続する2期の位置ベクトルの外積が正
v = main_df[["x", "y"]].values
cross = v[:-1, 0] * v[1:, 1] - v[:-1, 1] * v[1:, 0]
ccw_share = float((cross > 0).mean() * 100)

# 先行・遅行：gap(t) と 生産の伸び(t+k)
lag = []
for k in range(-4, 5):
    g = main_df.gap; pr = main_df.production_yoy.shift(-k)
    ok = g.notna() & pr.notna()
    lag.append({"k_quarters_ahead": k, "r": float(np.corrcoef(g[ok], pr[ok])[0, 1]), "n": int(ok.sum())})
lag = pd.DataFrame(lag)
lag.round(4).to_csv(RES / "lead_lag.csv", index=False)
best = lag.loc[lag["r"].idxmax()]

# 山の前後：山の四半期を0として、−4〜+4期の gap と局面
peaks = [pd.Period(p, "M").asfreq("Q") for p in cd.peak if p >= "2009-01"]
around = []
for pk in peaks:
    for k in range(-4, 5):
        qq = str(pk + k)
        if qq in main_df.index:
            around.append({"peak": str(pk), "k": k, "quarter": qq, "x": main_df.x[qq], "y": main_df.y[qq], "gap": main_df.gap[qq], "phase": main_df.phase[qq]})
around = pd.DataFrame(around)
around.round(3).to_csv(RES / "around_peaks.csv", index=False)
# 山の何期前に gap が負になったか（山の4期前から見て、最初に gap<0 となった期）
first_neg = {}
for pk, g in around.groupby("peak"):
    neg = g[(g.gap < 0) & (g.k <= 0)]
    first_neg[pk] = int(neg.k.min()) if len(neg) else None

# ---- 頑健性
rob = [main_res]
_, r = evaluate(yoy_q("鉱工業", "production", SPLICE_MAIN), Y, label="横軸を生産に"); rob.append(r)
_, r = evaluate(yoy_q("製造工業", "shipment", SPLICE_MAIN), yoy_q("製造工業", "inventory", SPLICE_MAIN), label="製造工業"); rob.append(r)
_, r = evaluate(yoy_q("鉱工業", "shipment", SPLICE_ALT), yoy_q("鉱工業", "inventory", SPLICE_ALT), label="つなぎ方：2014〜2022年を2015年基準"); rob.append(r)
_, r = evaluate(X, Y, end=EVAL_END, label="2020年4〜6月期まで（山が未定の期間を除く）"); rob.append(r)
# 月次：前年同月比の3か月平均
def yoy_m(name, series):
    parts = []
    win = {2010: ("200901", "201312"), 2015: ("201401", "201812"), 2020: ("201901", "209912")}
    for base, (a, b) in win.items():
        d = mo[(mo.base == base) & (mo.series == series) & (mo.name == name)].set_index("period").value.sort_index()
        y = (d / d.shift(12) - 1) * 100
        parts.append(y[(y.index >= a) & (y.index <= b)])
    s = pd.concat(parts).dropna()
    return s.rolling(3).mean().dropna()
xm = yoy_m("鉱工業", "shipment"); ym = yoy_m("鉱工業", "inventory")
dm = pd.DataFrame({"x": xm, "y": ym}).dropna()
dm["phase"] = [phase(a, b) for a, b in zip(dm.x, dm.y)]
dm["recession"] = [bool(rec.get(pd.Period(f"{p[:4]}-{p[4:]}", "M"), False)) for p in dm.index]
dm["gap"] = dm.x - dm.y
rm = dm[dm.recession]; em = dm[(~dm.recession) & (dm.index <= "202006")]
rob.append({"label": "月次（前年同月比の3か月平均）", "n": int(len(dm)), "n_rec": int(len(rm)), "n_exp_designated": int(len(em)),
            "rec_in_upper_or_adjust_pct": float(rm.phase.isin(["積み上がり", "調整"]).mean() * 100),
            "exp_in_recovery_or_build_pct": float(em.phase.isin(["回復", "積み増し"]).mean() * 100),
            "auc_gap": float(auc(-dm.gap, dm.recession)), "auc_x": float(auc(-dm.x, dm.recession)), "auc_y": float(auc(dm.y, dm.recession))})
rob = pd.DataFrame(rob)
rob.round(3).to_csv(RES / "robustness.csv", index=False)

# ---- 業種別（2014年1〜3月期以降、2015・2020年基準で区分が同じ）
inds = [n for n in q[(q.base == 2020)].drop_duplicates("code").sort_values("code").name
        if n not in ("鉱工業", "製造工業", "化学工業（除．医薬品）", "産業総合（鉱工業、電力・ガス・熱供給・水道事業）")
        and not n.startswith("<旧分類>")]
SPL_I = {2015: ("2014Q1", "2018Q4"), 2020: ("2019Q1", "2099Q4")}
iph = {}
ixy = []
for n in inds:
    xi = yoy_q(n, "shipment", SPL_I); yi = yoy_q(n, "inventory", SPL_I)
    d = pd.DataFrame({"x": xi, "y": yi}).dropna()
    iph[n] = pd.Series([phase(a, b) for a, b in zip(d.x, d.y)], index=d.index)
    for qq, a, b in zip(d.index, d.x, d.y):
        ixy.append({"industry": n, "quarter": qq, "x": a, "y": b, "phase": phase(a, b)})
iph = pd.DataFrame(iph)
ixy = pd.DataFrame(ixy)
ixy.round(4).to_csv(RES / "industry_cycle.csv", index=False)
tot_ph = main_df.phase.reindex(iph.index)
same = iph.eq(tot_ph, axis=0)
sync = same.mean(axis=1) * 100
ind_same = (same.mean(axis=0) * 100).round(1)
# 業種の局面の分布（各四半期で何業種が調整・積み上がりか）
cnt = iph.apply(lambda r: r.value_counts(), axis=1).reindex(columns=PHASES).fillna(0).astype(int)
cnt["total_phase"] = tot_ph
cnt["same_share_pct"] = sync.round(2)
cnt.to_csv(RES / "industry_phase_counts.csv", index_label="quarter")

# ---- 問い直し：「積み上がり」が3期以上続いた時期のあとに、景気の山が来たか
ph = main_df.phase
runs = []
start = None
idx = list(ph.index)
for i, qq in enumerate(idx):
    if ph[qq] == "積み上がり" and start is None:
        start = i
    if start is not None and (i == len(idx) - 1 or ph[idx[i + 1]] != "積み上がり"):
        runs.append((idx[start], qq, i - start + 1)); start = None
peak_q = [str(pd.Period(p, "M").asfreq("Q")) for p in cd.peak]
run_rows = []
for a, b, n in runs:
    pa = pd.Period(a, "Q"); pb = pd.Period(b, "Q")
    hit = [pk for pk in peak_q if pa - 1 <= pd.Period(pk, "Q") <= pb + 2]
    undecided = pd.Period(b, "Q") > pd.Period(EVAL_END, "Q")
    run_rows.append({"start": a, "end": b, "n_quarters": n, "peak_within": hit[0] if hit else "",
                     "status": "山あり" if hit else ("山が未定の期間" if undecided else "山なし")})
runs = pd.DataFrame(run_rows)
runs.to_csv(RES / "pileup_runs.csv", index=False)
runs3 = runs[runs.n_quarters >= 3]
# 拡張期（山・谷が決まっている期間）に「積み上がり・調整」にいた四半期と、そのときの生産の伸び
ee = main_df[(~main_df.recession) & (main_df.index <= EVAL_END)]
ee_cd = ee[ee.phase.isin(["積み上がり", "調整"])]

last = main_df.index.max()
main = {
    "period": [main_df.index.min(), last], "n_quarters": main_res["n"], "n_rec_quarters": main_res["n_rec"],
    "rec_quarters": [k for k, v in main_df.recession.items() if v],
    "phase_table": {p: {"拡張期": int(tab.loc[p].get("拡張期", 0)), "後退期": int(tab.loc[p].get("後退期", 0))} for p in PHASES},
    "H1_rec_in_upper_or_adjust_pct": r1(main_res["rec_in_upper_or_adjust_pct"]),
    "H2_exp_in_recovery_or_build_pct": r1(main_res["exp_in_recovery_or_build_pct"]), "n_exp_designated": main_res["n_exp_designated"],
    "auc_gap": r3(main_res["auc_gap"]), "auc_x": r3(main_res["auc_x"]), "auc_y": r3(main_res["auc_y"]),
    "ccw_share_pct": r1(ccw_share),
    "lead_best_k": int(best.k_quarters_ahead), "lead_best_corr": r2(best["r"]),
    "exp_in_upper_or_adjust_pct": r1(100 - main_res["exp_in_recovery_or_build_pct"]),
    "lead_corr_k1": r2(lag.set_index("k_quarters_ahead")["r"][1]),
    "lead_corr_k0": r2(lag.set_index("k_quarters_ahead")["r"][0]), "lead_corr_k2": r2(lag.set_index("k_quarters_ahead")["r"][2]),
    "first_gap_negative_before_peak": first_neg,
    "latest": {"quarter": last, "x": r1(main_df.x[last]), "y": r1(main_df.y[last]), "phase": main_df.phase[last],
               "prev4": [[k, r1(main_df.x[k]), r1(main_df.y[k]), main_df.phase[k]] for k in main_df.index[-5:-1]]},
    "pileup_runs_ge3": runs3.to_dict(orient="records"),
    "exp_cd_n": int(len(ee_cd)), "exp_cd_prod_neg_n": int((ee_cd.production_yoy < 0).sum()),
    "exp_cd_quarters": list(ee_cd.index),
    "post2020_phase_counts": main_df[main_df.index > EVAL_END].phase.value_counts().reindex(PHASES).fillna(0).astype(int).to_dict(),
    "post2020_n": int((main_df.index > EVAL_END).sum()),
    "industry": {"n_industries": len(inds), "period": [iph.index.min(), iph.index.max()], "sync_mean_pct": r1(sync.mean()),
                 "sync_min_pct": r1(sync.min()), "sync_min_q": sync.idxmin(), "sync_max_pct": r1(sync.max()),
                 "same_by_industry": {k: float(v) for k, v in ind_same.items()},
                 "latest_counts": cnt.loc[last, PHASES].astype(int).to_dict() if last in cnt.index else None},
    "robustness": {r["label"]: {"H1": r1(r["rec_in_upper_or_adjust_pct"]), "H2": r1(r["exp_in_recovery_or_build_pct"]),
                                 "auc_gap": r3(r["auc_gap"]), "auc_x": r3(r["auc_x"]), "n": int(r["n"]), "n_rec": int(r["n_rec"])} for _, r in rob.iterrows()},
}
main["hypotheses"] = {"H1": main["H1_rec_in_upper_or_adjust_pct"] >= 75, "H2": main["H2_exp_in_recovery_or_build_pct"] >= 60,
                      "H3": main["auc_gap"] > main["auc_x"], "H4": main["industry"]["sync_mean_pct"] >= 50}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=1, default=str))
