"""03 分析：架空の販促（会員アプリの来店クーポン、8週・6店）の効果を、6つの測り方で測り、答えと比べる。

測り方（どれも「販促がなかったら、対象の店の売上はいくらだったか」の作り方が違う）
  M1 前後比較：期間の8週と、その直前の8週を比べる
  M2 前年比：期間の8週と、52週前の同じ8週を比べる
  M3 前年比の差：対象の店の前年比 − 対象でない店の前年比
  M4 差の差（DiD）：店×週の売上の対数を、店と週の固定効果で回帰（期間の前の52週を使う）
  M5 差の差＋店ごとの傾き：M4 に、店ごとの直線の流れ（期間の前の52週で測る）を足す
  M6 合成対照：対象でない14店に重み（0以上、合計1）を付け、期間の前の52週の動き（各店の平均を引いた対数）が
     対象の6店の合計にいちばん近くなる組み合わせを作る。期間の差（対数）の平均を効果とする
効果は「期間の8週の売上が、販促がなかった場合より何%多いか」。期間の後の4週も同じ形で測る。

確かめること
  A 乱数の種 0（F247 の mart）での6つの値と答え、お金の勘定（増えた粗利 − クーポン − 固定費）
  B プラセボ（偽の販促）：①場所を入れ替える（対象でない14店から6店を選び、偽の対象にする。200通り）
     ②時を入れ替える（同じ6店に、1年前の同じ8週に偽の販促があったことにする。答えは0）
  C 外れの幅：F246 の gen(seed) で乱数の種 0〜19 の20通りを作り直し、同じ選び方・同じ効果で測る（測り方ごとの偏りと90%の幅）
  D 頑健性：店の選び方を無作為にする／効果を0にする／期間の前の長さ 26・52・78週／合成対照に傾きを足す
出力：results/*.csv, results/main.json
"""
import importlib.util, itertools, json, pathlib, time
import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
s = importlib.util.spec_from_file_location("prep", ROOT / "src" / "02_整形.py")
prep = importlib.util.module_from_spec(s); s.loader.exec_module(prep)

METHODS = ["M1_前後", "M2_前年比", "M3_前年比の差", "M4_DiD", "M5_DiD傾き", "M6_合成対照"]
LABEL = {"M1_前後": "前後比較", "M2_前年比": "前年比", "M3_前年比の差": "前年比の差", "M4_DiD": "差の差",
         "M5_DiD傾き": "差の差＋店ごとの傾き", "M6_合成対照": "合成対照"}


def lift(v):
    return float(np.exp(v) - 1)


def twfe(w, treated, pre, post_sets, trend=False):
    """店×週の対数売上 = 店の効果 + 週の効果 (+ 店ごとの傾き) + Σ τ_j × 期間j の対象店。最小二乗。"""
    ks = sorted(set(pre) | set().union(*post_sets))
    x = w[w.k.isin(ks)].copy()
    y = np.log(x.sales.values)
    stores = sorted(x.store_id.unique()); weeks = sorted(x.k.unique())
    S = (x.store_id.values[:, None] == np.array(stores)[None, :]).astype(float)
    W = (x.k.values[:, None] == np.array(weeks)[None, 1:]).astype(float)
    cols = [S, W]
    if trend:   # 店ごとの傾き（1店は週の効果と重なるので除く）
        t = x.k.values.astype(float) / 52
        cols.append(S[:, 1:] * t[:, None])
    tr = x.store_id.isin(treated).values
    D = np.column_stack([(tr & x.k.isin(p).values).astype(float) for p in post_sets])
    X = np.column_stack(cols + [D])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return b[-len(post_sets):]


def synth(w, treated, donors, pre, post_sets, detrend=False):
    """合成対照（各系列の期間の前の平均を引いた対数で合わせる）。返り値：各期間の差の平均、期間の前の当てはまり、重み、週ごとの差。"""
    p = w.pivot_table(index="k", columns="store_id", values="sales", aggfunc="sum")
    yT = np.log(p[treated].sum(1)); Y = np.log(p[donors])
    pre_i = p.index.isin(pre)
    yT = yT - yT[pre_i].mean(); Y = Y - Y[pre_i].mean()
    if detrend:   # 期間の前の直線の流れを、対象と相手それぞれから引く
        kk = p.index.values.astype(float)
        def dt(s):
            c = np.polyfit(kk[pre_i], s[pre_i], 1); return s - np.polyval(c, kk)
        yT = dt(yT.values); Y = Y.apply(lambda c: pd.Series(dt(c.values), index=c.index))
        yT = pd.Series(yT, index=p.index)
    A = Y[pre_i].values; bT = yT[pre_i].values; n = A.shape[1]
    r = minimize(lambda v: ((A @ v - bT) ** 2).sum(), np.full(n, 1 / n), method="SLSQP",
                 bounds=[(0, 1)] * n, constraints=[{"type": "eq", "fun": lambda v: v.sum() - 1}],
                 options={"ftol": 1e-12, "maxiter": 500})
    v = r.x
    gap = yT - Y.values @ v
    eff = [float(gap[p.index.isin(ps)].mean()) for ps in post_sets]
    rmspe_pre = float(np.sqrt((gap[pre_i] ** 2).mean()))
    return eff, rmspe_pre, dict(zip(donors, v)), gap


def estimate_all(w, treated, start=0, pre_len=52, detrend_sc=False):
    """start：期間の1週目の k（本番 0、時のプラセボ −52）。期間8週・後4週。"""
    promo = list(range(start, start + 8)); after = list(range(start + 8, start + 12))
    pre = list(range(start - pre_len, start))
    tr = w[w.store_id.isin(treated)]; ct = w[~w.store_id.isin(treated)]
    donors = sorted(set(ct.store_id.unique()) - set(prep.EXCLUDE))
    ct = ct[ct.store_id.isin(donors)]
    w2 = w[w.store_id.isin(treated + donors)]
    tot = lambda d, ks: d[d.k.isin(ks)].sales.sum()
    out = {}
    out["M1_前後"] = [np.log(tot(tr, promo) / tot(tr, range(start - 8, start))), np.log(tot(tr, after) / tot(tr, range(start - 4, start)))]
    yoyT = [np.log(tot(tr, ks) / tot(tr, [k - 52 for k in ks])) for ks in (promo, after)]
    yoyC = [np.log(tot(ct, ks) / tot(ct, [k - 52 for k in ks])) for ks in (promo, after)]
    out["M2_前年比"] = yoyT
    out["M3_前年比の差"] = [a - b for a, b in zip(yoyT, yoyC)]
    out["M4_DiD"] = list(twfe(w2, treated, pre, [promo, after]))
    out["M5_DiD傾き"] = list(twfe(w2, treated, pre, [promo, after], trend=True))
    eff, rm, wt, gap = synth(w2, treated, donors, pre, [promo, after], detrend=detrend_sc)
    out["M6_合成対照"] = eff
    res = {m: {"promo": lift(v[0]), "after": lift(v[1])} for m, v in out.items()}
    return res, {"sc_rmspe_pre": rm, "sc_weights": wt, "sc_gap": gap}


def money(w, lifts, start=0):
    """測った効果から、お金の勘定を出す（クーポン・固定費は実際にかかった額）。"""
    promo = list(range(start, start + 8)); after = list(range(start + 8, start + 12))
    t = w[w.treated == 1]
    o = {}
    for name, ks in (("promo", promo), ("after", after)):
        x = t[t.k.isin(ks)]
        S, G = x.sales.sum(), x.gross_profit.sum()
        inc = S * (1 - 1 / (1 + lifts[name]))
        o[name] = {"inc_sales": inc, "inc_gp": inc * G / S}
    coupon = t[t.k.isin(promo)].coupon_cost.sum()
    o["coupon"] = coupon; o["fixed"] = prep.FIXED_YEN
    o["net"] = o["promo"]["inc_gp"] + o["after"]["inc_gp"] - coupon - prep.FIXED_YEN
    o["roi"] = o["net"] / (coupon + prep.FIXED_YEN)
    return o


def run_seed(sd, rule="weak", rng=None, eff=True, **kw):
    tr = prep.select_treated(sd, rule, rng)
    d = prep.inject(sd, tr) if eff else prep.inject(sd, tr, 1.0, 1.0, 1.0)
    w = prep.weekly(d)
    tru = prep.truth(d)
    est, extra = estimate_all(w, tr, **kw)
    return tr, w, tru, est, extra


if __name__ == "__main__":
    t0 = time.time()
    ST = prep.dims().set_index("store_id")
    main = {}
    # ---------- A：本番（乱数の種 0、F247 の mart） ----------
    sd0 = prep.from_mart()
    tr, w, tru, est, extra = run_seed(sd0)
    main["treated"] = tr; main["treated_area"] = ST.loc[tr, "area"].tolist()
    main["truth"] = tru
    w.to_csv(RES / "A_store_week_seed0.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    rows = []
    for m in METHODS:
        mo = money(w, est[m])
        rows.append({"method": m, "label": LABEL[m], "promo_lift": est[m]["promo"], "after_lift": est[m]["after"],
                     "inc_sales_promo": mo["promo"]["inc_sales"], "inc_gp_total": mo["promo"]["inc_gp"] + mo["after"]["inc_gp"],
                     "net": mo["net"], "roi": mo["roi"]})
    mt = money(w, {"promo": tru["promo"]["lift_pct"], "after": tru["after"]["lift_pct"]})
    rows.append({"method": "TRUTH", "label": "答え", "promo_lift": tru["promo"]["lift_pct"], "after_lift": tru["after"]["lift_pct"],
                 "inc_sales_promo": tru["promo"]["inc_sales"], "inc_gp_total": tru["promo"]["inc_gp"] + tru["after"]["inc_gp"],
                 "net": tru["net"], "roi": tru["net"] / (tru["promo"]["coupon"] + prep.FIXED_YEN)})
    A = pd.DataFrame(rows); A.to_csv(RES / "A_estimates_seed0.csv", index=False)
    main["money_truth_check"] = {"net_from_lift": mt["net"], "net_truth": tru["net"]}
    main["sc"] = {"rmspe_pre": extra["sc_rmspe_pre"], "weights": {str(k): round(v, 4) for k, v in extra["sc_weights"].items() if v > 1e-4}}
    pd.DataFrame({"k": sorted(w.k.unique()), "gap": extra["sc_gap"].values}).to_csv(RES / "A_sc_gap_seed0.csv", index=False)
    # 対象の店と対象でない店の、週ごとの売上の指数（期間の前52週の平均=100）
    p = w.pivot_table(index="k", columns="treated", values="sales", aggfunc="sum")
    don = sorted(set(w.store_id) - set(tr) - set(prep.EXCLUDE))
    pc = w[w.store_id.isin(don)].groupby("k").sales.sum()
    pT = w[w.treated == 1].groupby("k").sales.sum(); pT0 = w[w.treated == 1].groupby("k").sales0.sum()
    pre = (pT.index >= -52) & (pT.index < 0)
    idx = pd.DataFrame({"treated": pT / pT[pre].mean() * 100, "treated_no_promo": pT0 / pT[pre].mean() * 100,
                        "control": pc / pc[pre].mean() * 100})
    idx.to_csv(RES / "A_weekly_index_seed0.csv")
    # 地域ごとの前年比（選ばれた店が地方に偏ることの確認）
    sel = sd0[sd0.store_id.isin(sorted(set(sd0.store_id) - set(prep.EXCLUDE)))].copy()
    sel["ym"] = sel.date.dt.strftime("%Y-%m")
    a = sel[sel.ym.isin(prep.SEL_MONTHS)].groupby("store_id").sales.sum()
    b = sel[sel.ym.isin([str(pd.Period(m, "M") - 12) for m in prep.SEL_MONTHS])].groupby("store_id").sales.sum()
    yy = (a / b - 1).rename("yoy_jul_sep").to_frame().join(ST[["area", "size"]]); yy["treated"] = yy.index.isin(tr).astype(int)
    yy.sort_values("yoy_jul_sep").to_csv(RES / "A_selection_yoy.csv")

    # 事象研究（週ごとの効果、差の差の形）：期間の前52週〜後4週、k=−1 を基準
    x = w[w.store_id.isin(tr + don) & w.k.between(-52, 11)].copy()
    ev = []
    for trend in (False, True):
        ks = [k for k in range(-52, 12) if k != -1]
        y = np.log(x.sales.values); stores = sorted(x.store_id.unique()); weeks = sorted(x.k.unique())
        S = (x.store_id.values[:, None] == np.array(stores)[None, :]).astype(float)
        Wk = (x.k.values[:, None] == np.array(weeks)[None, 1:]).astype(float)
        trm = x.store_id.isin(tr).values
        D = np.column_stack([(trm & (x.k.values == k)).astype(float) for k in ks])
        cols = [S, Wk]
        if trend:  # 傾きは期間の前だけで決まるように、期間の前の週の差を「傾き＋偶然」と見る（傾きの列を足す）
            cols.append(S[:, 1:] * (x.k.values.astype(float) / 52)[:, None])
            # 期間の前の週ごとのダミーと傾きは重なるので、傾きありは期間の前のダミーを外す
            D = np.column_stack([(trm & (x.k.values == k)).astype(float) for k in ks if k >= 0])
        b, *_ = np.linalg.lstsq(np.column_stack(cols + [D]), y, rcond=None)
        kk = ks if not trend else [k for k in ks if k >= 0]
        for k, v in zip(kk, b[-len(kk):]):
            ev.append({"trend": int(trend), "k": k, "coef": v})
    pd.DataFrame(ev).to_csv(RES / "A_event_study_seed0.csv", index=False)

    # ---------- B：プラセボ ----------
    rng = np.random.default_rng(251)
    combos = list(itertools.combinations(don, 6)); pick = rng.choice(len(combos), 200, replace=False)
    pl = []
    wd = w[w.store_id.isin(don)].copy()
    for i in pick:
        fake = list(combos[i])
        wd["treated"] = wd.store_id.isin(fake).astype(int)
        e, ex = estimate_all(wd, fake)
        pl.append({"stores": "-".join(map(str, fake)), **{m: e[m]["promo"] for m in METHODS}, "sc_rmspe_pre": ex["sc_rmspe_pre"]})
    PL = pd.DataFrame(pl); PL.to_csv(RES / "B_placebo_space.csv", index=False)
    e_time, ex_time = estimate_all(w, tr, start=-52)
    pd.DataFrame([{"method": m, "label": LABEL[m], "fake_lift": e_time[m]["promo"], "fake_after": e_time[m]["after"]} for m in METHODS]).to_csv(RES / "B_placebo_time.csv", index=False)
    main["placebo_space"] = {m: {"q05": float(PL[m].quantile(0.05)), "q95": float(PL[m].quantile(0.95)),
                                 "p_two_sided": float((PL[m].abs() >= abs(est[m]["promo"])).mean())} for m in METHODS}
    main["placebo_time"] = {m: e_time[m]["promo"] for m in METHODS}
    main["placebo_time_sc_rmspe"] = ex_time["sc_rmspe_pre"]
    print("A,B done", round(time.time() - t0, 1))

    # ---------- C・D：乱数の種20通り ----------
    g = prep.load_gen_module()
    cr = []
    for sdd in range(20):
        sdg = prep.from_gen(g, sdd)
        cases = [("weak", True, {}), ("weak", False, {}), ("random", True, {}),
                 ("weak", True, {"pre_len": 26}), ("weak", True, {"pre_len": 78}), ("weak", True, {"detrend_sc": True})]
        for rule, eff, kw in cases:
            r2 = np.random.default_rng(1000 + sdd)
            trs, ws, trus, ests, exs = run_seed(sdg, rule, r2, eff, **kw)
            tag = f"{rule}_{'eff' if eff else 'null'}" + "".join(f"_{k}{v}" for k, v in kw.items())
            for m in METHODS:
                mo = money(ws, ests[m]) if kw == {} and eff else {"net": np.nan}
                cr.append({"seed": sdd, "case": tag, "method": m, "est": ests[m]["promo"], "truth": trus["promo"]["lift_pct"],
                           "net_est": mo["net"], "net_truth": trus["net"],
                           "est_after": ests[m]["after"], "truth_after": trus["after"]["lift_pct"],
                           "n_rural": int(sum(ST.loc[t, "area"] == "地方" for t in trs)), "sc_rmspe_pre": exs["sc_rmspe_pre"]})
        print("seed", sdd, round(time.time() - t0, 1))
    C = pd.DataFrame(cr); C["err"] = C.est - C.truth
    C.to_csv(RES / "C_seeds.csv", index=False)
    summ = C.groupby(["case", "method"]).agg(bias=("err", "mean"), sd=("err", "std"), q05=("err", lambda v: v.quantile(0.05)),
                                             q95=("err", lambda v: v.quantile(0.95)), mae=("err", lambda v: v.abs().mean()),
                                             n_rural=("n_rural", "mean")).reset_index()
    summ["half90"] = 1.645 * summ.sd
    C["net_err"] = C.net_est - C.net_truth
    nm = C[C.case == "weak_eff"].groupby("method").agg(net_bias=("net_err", "mean"), net_sd=("net_err", "std"),
                                                       net_neg=("net_est", lambda v: int((v < 0).sum())), net_truth_mean=("net_truth", "mean"))
    nm.to_csv(RES / "C_money_error.csv")
    main["money_error"] = nm.to_dict(orient="index")
    summ.to_csv(RES / "C_error_summary.csv", index=False)
    main["error_summary"] = {f"{r.case}|{r.method}": {"bias": r.bias, "half90": r.half90, "mae": r.mae, "n_rural": r.n_rural} for r in summ.itertuples()}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
    print("runtime_sec", round(time.time() - t0, 1)); print(A.round(4).to_string()); print(summ[summ.case.isin(["weak_eff", "weak_null", "random_eff"])].round(4).to_string())
