"""03 分析：既存店の売上が前年を下回った月（FY2025 は 2026年3月だけ）の理由を、要因に分けて説明する。

やること
1. FY2024〜FY2025 の各月の既存店売上の前年比（全店も）を出し、前年割れの月を拾う。
2. 2026年3月を分ける：売上 ＝ 客数（レシート枚数）× 1回の買上点数 × 一品単価。客数は「暦（曜日・祝日・日数）」と「暦を除いた客数」に分ける。
   暦の効き方は、前の年度までの店×日のデータから回帰で測る（店×月の固定効果、曜日・平日の祝日・年末）。
3. 偶然の幅：F246 の gen(seed) で乱数の種だけを変えた20通りのデータを作り直し、同じ計算をして、各要因のばらつき（90%の幅）を測る。
   幅を超えたものだけを「理由」として報告し、幅の中のものは「いつもの揺れ」とまとめる。
4. 答え合わせ：合成の設定（曜日の係数・物価・売上の季節の形）から計算できる「本当の」要因と比べる。
5. 頑健性：分け方の順番（6通り）、暦の測り方（回帰・364日前と比べる・前年同月の曜日平均）、回帰の学習期間、種20通り、他の前年割れの月にも同じ型を当てる。
出力：results/*.csv, results/main.json
"""
import importlib.util, itertools, json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
s = importlib.util.spec_from_file_location("prep", ROOT / "src" / "02_整形.py")
prep = importlib.util.module_from_spec(s); s.loader.exec_module(prep)

TARGET = "2026-03"
MONTHS = [str(p) for p in pd.period_range("2024-04", "2026-03", freq="M")]
AREAS = ["都市", "郊外", "地方"]
ST, CAT, DD = prep.dims()
EX = prep.existing_flags(ST, [str(p) for p in pd.period_range("2022-04", "2026-03", freq="M")])
SEEDS = list(range(20))


def fy_of(ym):
    p = pd.Period(ym, "M"); return p.year if p.month >= 4 else p.year - 1


# ---------- 暦の効き方（回帰） ----------
def cal_features(dates):
    d = pd.DatetimeIndex(dates)
    X = np.zeros((len(d), 8))
    dow = d.dayofweek.values
    for k in range(1, 7):
        X[:, k - 1] = dow == k                       # 火〜日（月曜が基準）
    hol = pd.Series(d).map(HOL).fillna(False).values.astype(bool)
    X[:, 6] = hol & (dow < 5)                        # 平日の祝日
    X[:, 7] = (d.month == 12) & (d.day >= 28)        # 年末
    return X


HOL = DD.set_index("date").hol.astype(bool).to_dict()
NAMES = ["火", "水", "木", "金", "土", "日", "平日の祝日", "年末"]


def fit_calendar(sd, fys):
    """店×月の固定効果を除いて（店×月の中の平均を引いて）、曜日などの係数を最小二乗で求める。"""
    d = sd[sd.ym.map(fy_of).isin(fys)].copy()
    y = np.log(d.receipts.values.astype(float))
    X = cal_features(d.date)
    key = d.store_id.astype(str) + "_" + d.ym
    yd = y - pd.Series(y).groupby(key.values).transform("mean").values
    Xd = X - pd.DataFrame(X).groupby(key.values).transform("mean").values
    b, *_ = np.linalg.lstsq(Xd, yd, rcond=None)
    return b


def cal_ratio(b, ym):
    """その月と前年同月の『暦の重み』の合計の比（日数の違いも入る）。"""
    p = pd.Period(ym, "M"); q = p - 12
    w = lambda per: np.exp(cal_features(pd.date_range(per.start_time, per.end_time.normalize())) @ b).sum()
    return w(p) / w(q)


def cal_ratio_dowmean(sd, ym):
    """簡便法：前年同月の曜日ごとの1日平均レシート（既存店計）を重みにして、曜日の並びの差だけを見る。"""
    p = pd.Period(ym, "M"); q = p - 12
    ids = EX[(EX.ym == ym) & (EX.is_existing == 1)].store_id
    d = sd[(sd.ym == str(q)) & sd.store_id.isin(ids)].groupby("date").receipts.sum()
    w = d.groupby(d.index.dayofweek).mean()
    days = lambda per: pd.date_range(per.start_time, per.end_time.normalize()).dayofweek
    return w.reindex(days(p)).sum() / w.reindex(days(q)).sum()


def true_cal_ratio(g, ym):
    """答え合わせ：合成の設定そのものの曜日・祝日・年末・チラシの係数で計算した暦の比。"""
    cal = g._dates()
    f = (g.DOW[cal.dow.values] * np.where(cal.hol.values & (cal.dow.values < 5), 1.07, 1.0)
         * np.where((cal.date.dt.month == 12) & (cal.date.dt.day >= 28), 1.35, 1.0) * np.where(cal.flyer.values, 1.07, 1.0))
    s_ = pd.Series(f, index=cal.ym).groupby(level=0).sum()
    q = str(pd.Period(ym, "M") - 12)
    return s_[ym] / s_[q]


# ---------- 1か月の分解 ----------
def lmdi(a, b):
    """変化 a→b の対数平均の重み（合計が変化率にちょうど一致するように配る）。"""
    return (b - a) / np.log(b / a) if b != a else a


def decompose(sd, sdc, ym, b):
    p = pd.Period(ym, "M"); q = str(p - 12)
    ids = EX[(EX.ym == ym) & (EX.is_existing == 1)].store_id.values
    cur = sd[(sd.ym == ym) & sd.store_id.isin(ids)]; pre = sd[(sd.ym == q) & sd.store_id.isin(ids)]
    S1, S0 = cur.sales.sum(), pre.sales.sum()
    R1, R0 = cur.receipts.sum(), pre.receipts.sum()
    I1, I0 = cur["items"].sum(), pre["items"].sum()
    L = lmdi(S0, S1) / S0
    cr = cal_ratio(b, ym)
    out = {"ym": ym, "n_stores": len(ids), "sales_yoy": S1 / S0 - 1, "receipts_yoy": R1 / R0 - 1,
           "items_per_receipt_yoy": (I1 / R1) / (I0 / R0) - 1, "unit_price_yoy": (S1 / I1) / (S0 / I0) - 1,
           "calendar_receipts": cr - 1, "receipts_adj_yoy": (R1 / R0) / cr - 1,
           # 売上の前年比への寄与（pt、合計＝売上の前年比）
           "c_calendar": L * np.log(cr), "c_receipts_adj": L * np.log((R1 / R0) / cr),
           "c_items": L * np.log((I1 / R1) / (I0 / R0)), "c_price": L * np.log((S1 / I1) / (S0 / I0))}
    # 全店（店の出入りを含む）
    a1 = sd[sd.ym == ym].sales.sum(); a0 = sd[sd.ym == q].sales.sum()
    out["sales_yoy_all"] = a1 / a0 - 1
    # 地域：暦を除いた客数の前年比と、既存店客数の変化への寄与
    for a in AREAS:
        r1 = cur[cur.area == a].receipts.sum(); r0 = pre[pre.area == a].receipts.sum()
        out[f"area_receipts_adj_yoy_{a}"] = (r1 / r0) / cr - 1
        out[f"area_c_receipts_adj_{a}"] = (r1 / cr - r0) / R0
        s1 = cur[cur.area == a].sales.sum(); s0 = pre[pre.area == a].sales.sum()
        out[f"area_sales_yoy_{a}"] = s1 / s0 - 1
    # 部門
    c1 = sdc[(sdc.ym == ym) & sdc.store_id.isin(ids)].groupby("category_id").sales.sum()
    c0 = sdc[(sdc.ym == q) & sdc.store_id.isin(ids)].groupby("category_id").sales.sum()
    for k, nm in zip(CAT.category_id, CAT.category):
        out[f"cat_sales_yoy_{nm}"] = c1[k] / c0[k] - 1
        out[f"cat_c_{nm}"] = (c1[k] - c0[k]) / S0
    # 店
    s1 = cur.groupby("store_id").sales.sum(); s0 = pre.groupby("store_id").sales.sum()
    for k in ids:
        out[f"store_sales_yoy_{k:02d}"] = s1[k] / s0[k] - 1
    return out


def add_relative(r):
    """地域・部門・店が『会社全体の動き』からどれだけ離れたか（pt）。理由の候補になるのは、この差が偶然の幅を超えたときだけ。"""
    for k in list(r):
        if k.startswith("area_receipts_adj_yoy_"):
            r["rel_" + k] = r[k] - r["receipts_adj_yoy"]
        elif k.startswith(("cat_sales_yoy_", "store_sales_yoy_")):
            r["rel_" + k] = r[k] - r["sales_yoy"]
    return r


def fy_area(sd, fy, b):
    """年度の12か月を通した、暦を除いた既存店の客数の前年比（地域別）。1か月では見えない差が見えるか。"""
    out = {"fy": fy}; num = {a: 0.0 for a in AREAS + ["全体"]}; den = dict(num)
    for p in pd.period_range(f"{fy}-04", f"{fy + 1}-03", freq="M"):
        ym = str(p); q = str(p - 12); cr = cal_ratio(b, ym)
        ids = EX[(EX.ym == ym) & (EX.is_existing == 1)].store_id.values
        c = sd[(sd.ym == ym) & sd.store_id.isin(ids)]; o = sd[(sd.ym == q) & sd.store_id.isin(ids)]
        for a in AREAS:
            num[a] += c[c.area == a].receipts.sum() / cr; den[a] += o[o.area == a].receipts.sum()
        num["全体"] += c.receipts.sum() / cr; den["全体"] += o.receipts.sum()
    for a in num:
        out[f"fy_receipts_adj_yoy_{a}"] = num[a] / den[a] - 1
    for a in AREAS:
        out[f"rel_fy_receipts_adj_yoy_{a}"] = out[f"fy_receipts_adj_yoy_{a}"] - out["fy_receipts_adj_yoy_全体"]
    return out


def yoy_364(sd, ym):
    """364日前（同じ曜日）の同じ長さの期間と比べた既存店売上・客数の前年比。"""
    p = pd.Period(ym, "M")
    ids = EX[(EX.ym == ym) & (EX.is_existing == 1)].store_id.values
    d1 = pd.date_range(p.start_time, p.end_time.normalize()); d0 = d1 - pd.Timedelta(days=364)
    x = sd[sd.store_id.isin(ids)].set_index("date")
    a = x.loc[x.index.isin(d1)]; b0 = x.loc[x.index.isin(d0)]
    return a.sales.sum() / b0.sales.sum() - 1, a.receipts.sum() / b0.receipts.sum() - 1


def seq_orders(sd, ym):
    """分け方の順番：客数→点数→単価 などを順に置き換える6通り（LMDI と比べる）。"""
    p = pd.Period(ym, "M"); q = str(p - 12)
    ids = EX[(EX.ym == ym) & (EX.is_existing == 1)].store_id.values
    c = sd[(sd.ym == ym) & sd.store_id.isin(ids)]; o = sd[(sd.ym == q) & sd.store_id.isin(ids)]
    f1 = {"客数": c.receipts.sum(), "点数": c["items"].sum() / c.receipts.sum(), "単価": c.sales.sum() / c["items"].sum()}
    f0 = {"客数": o.receipts.sum(), "点数": o["items"].sum() / o.receipts.sum(), "単価": o.sales.sum() / o["items"].sum()}
    S0 = np.prod(list(f0.values())); rows = []
    for order in itertools.permutations(f0):
        cur = dict(f0); prev = S0; r = {"order": "→".join(order)}
        for k in order:
            cur[k] = f1[k]; v = np.prod(list(cur.values())); r[k] = (v - prev) / S0; prev = v
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    g = prep.load_gen_module()
    sd, sdc = prep.from_mart()
    # 1. 各月の前年比（seed 0 = mart）
    betas = {fy: fit_calendar(sd, list(range(2022, fy))) for fy in (2024, 2025)}
    dec = pd.DataFrame([add_relative(decompose(sd, sdc, ym, betas[fy_of(ym)])) for ym in MONTHS])
    fya0 = fy_area(sd, 2025, betas[2025])
    dec.to_csv(RES / "A_monthly_decomposition_seed0.csv", index=False)
    down = dec[dec.sales_yoy < 0].ym.tolist()

    # 2. 偶然の幅：種20通り
    allseed = []; fya = []
    for sdd in SEEDS:
        a, c = prep.from_gen(g, sdd)
        bb = {fy: fit_calendar(a, list(range(2022, fy))) for fy in (2024, 2025)}
        for ym in MONTHS:
            r = add_relative(decompose(a, c, ym, bb[fy_of(ym)])); r["seed"] = sdd; allseed.append(r)
        f_ = fy_area(a, 2025, bb[2025]); f_["seed"] = sdd; fya.append(f_)
    allseed = pd.DataFrame(allseed); fya = pd.DataFrame(fya); fya.to_csv(RES / "B_seeds_fy2025_area.csv", index=False)
    fyb = (fya.drop(columns=["fy", "seed"]) - fya.drop(columns=["fy", "seed"]).mean()).std() * 1.645
    allseed.to_csv(RES / "B_seeds_decomposition.csv", index=False)
    num = [c for c in allseed.columns if c not in ("ym", "seed", "n_stores")]
    mean = allseed.groupby("ym")[num].mean()
    dev = allseed.set_index(["ym", "seed"])[num] - mean.reindex(allseed.ym).values
    band = (dev.groupby(level=0).std() * 1.645)       # 90%の幅（半分の幅）
    band_q = dev.groupby(level=0).quantile(0.95) - dev.groupby(level=0).quantile(0.05)
    band.to_csv(RES / "B_noise_band90_halfwidth.csv"); mean.to_csv(RES / "B_seed_mean.csv")
    # seed 0 は mart と同じデータか（F247 の整え方で円の丸めだけの差）
    s0 = allseed[allseed.seed == 0].set_index("ym")
    seed0_vs_mart = float((s0.sales_yoy - dec.set_index("ym").sales_yoy).abs().max())

    # 3. 2026年3月：要因と幅
    t = dec.set_index("ym").loc[TARGET]; bt = band.loc[TARGET]
    rows = []
    for k in num:
        if k in ("sales_yoy_all",) or k.startswith(("area_receipts_adj_yoy_", "cat_sales_yoy_", "store_sales_yoy_")):
            continue   # 地域・部門・店は rel_（全体との差）で判定する
        rows.append({"item": k, "value": t[k], "band90_half": bt[k], "beyond_band": bool(abs(t[k]) > bt[k]),
                     "seed_mean": mean.loc[TARGET, k], "share_seeds_negative": float((allseed[allseed.ym == TARGET][k] < 0).mean())})
    tb = pd.DataFrame(rows); tb.to_csv(RES / "C_target_items_vs_band.csv", index=False)

    # 4. 答え合わせ（合成の設定から計算できる本当の値）
    cal_g = g._dates(); pm, vol = g._indices(cal_g); q = str(pd.Period(TARGET, "M") - 12)
    truth = {"calendar_receipts": true_cal_ratio(g, TARGET) - 1,
             "market_volume_receipts(vol^0.85)": (vol[TARGET] / vol[q]) ** 0.85 - 1,
             "items_per_receipt(vol^0.15*price^-0.25)": (vol[TARGET] / vol[q]) ** 0.15 * (pm[TARGET] / pm[q]) ** -0.25 - 1,
             "unit_price(price index)": pm[TARGET] / pm[q] - 1}
    # 地域の客数の流れ（年あたり）を既存店の前年のレシートで重みづけ
    ids = EX[(EX.ym == TARGET) & (EX.is_existing == 1)].store_id.values
    w = sd[(sd.ym == q) & sd.store_id.isin(ids)].groupby("area").receipts.sum()
    truth["area_trend_receipts"] = float(sum(w[a] * (np.exp(g.AREA_TREND[a]) - 1) for a in w.index) / w.sum())
    for a in AREAS:
        truth[f"area_trend_{a}"] = float(np.exp(g.AREA_TREND[a]) - 1)

    # 5. 頑健性
    rob = {}
    seq = seq_orders(sd, TARGET); seq.to_csv(RES / "D_order_sequential.csv", index=False)
    rob["order_range"] = {k: [float(seq[k].min()), float(seq[k].max())] for k in ["客数", "点数", "単価"]}
    y364, r364 = yoy_364(sd, TARGET)
    rob["calendar_methods"] = {"regression_FY2022-24": float(t.calendar_receipts),
                               "same_weekday_364": float((1 + t.receipts_yoy) / (1 + r364) - 1),
                               "prev_year_dow_mean": float(cal_ratio_dowmean(sd, TARGET) - 1),
                               "truth_generator": truth["calendar_receipts"]}
    rob["sales_yoy_364"] = float(y364); rob["receipts_yoy_364"] = float(r364)
    rob["calendar_train_window"] = {f"FY{','.join(map(str, w_))}": float(cal_ratio(fit_calendar(sd, w_), TARGET) - 1)
                                    for w_ in ([2022, 2023, 2024], [2024], [2023, 2024], [2022, 2023, 2024, 2025])}
    bcoef = pd.Series(betas[2025], index=NAMES); bcoef.to_csv(RES / "D_calendar_coefficients_FY2022-24.csv", header=["log_coef"])
    true_coef = pd.Series(np.log(np.r_[g.DOW[1:] / g.DOW[0] * np.array([1, 1.07, 1, 1, 1.07, 1]), 1.07, 1.35]), index=NAMES)
    rob["calendar_coef_est_vs_true"] = {k: [float(bcoef[k]), float(true_coef[k])] for k in NAMES}
    tseeds = allseed[allseed.ym == TARGET]
    rob["seeds_target"] = {"sales_yoy_mean": float(tseeds.sales_yoy.mean()), "sales_yoy_min": float(tseeds.sales_yoy.min()),
                           "sales_yoy_max": float(tseeds.sales_yoy.max()), "share_negative": float((tseeds.sales_yoy < 0).mean()),
                           "receipts_adj_min": float(tseeds.receipts_adj_yoy.min()), "receipts_adj_max": float(tseeds.receipts_adj_yoy.max())}
    # どの種でも「幅を超える地域・部門・店」がいくつ出るか（偶然だけで何個『理由らしきもの』が出るか）
    cols_sub = [c for c in num if c.startswith("rel_") and not np.isnan(t[c])]   # その月に既存店でない店は除く
    false_hits = []
    for sdd in SEEDS:
        r = tseeds[tseeds.seed == sdd].iloc[0]
        dev_ = (r[cols_sub] - mean.loc[TARGET, cols_sub]).abs()   # 種の平均（設定どおりの差）からのずれ＝偶然だけの分
        false_hits.append(int((dev_ > band.loc[TARGET, cols_sub]).sum()))
    rob["chance_beyond_band_per_seed"] = {"items_checked": len(cols_sub), "mean": float(np.mean(false_hits)), "max": int(max(false_hits))}

    # 1か月で見たとき、本当の地域差（設定）がどれくらい「幅の外」に出るか（FY2025 の12か月×種20）
    fy25 = allseed[allseed.ym.map(fy_of) == 2025]
    rob["monthly_area_beyond_band_rate"] = {
        a: float((fy25[f"rel_area_receipts_adj_yoy_{a}"].abs() > band.loc[fy25.ym, f"rel_area_receipts_adj_yoy_{a}"].values).mean())
        for a in AREAS}
    rob["monthly_area_rel_seedmean_FY2025avg"] = {a: float(mean.loc[[m for m in MONTHS if fy_of(m) == 2025], f"rel_area_receipts_adj_yoy_{a}"].mean()) for a in AREAS}

    # 他の前年割れの月にも同じ型を当てる
    oth = dec[dec.ym.isin(down)][["ym", "sales_yoy", "sales_yoy_all", "c_price", "c_items", "c_calendar", "c_receipts_adj"]].copy()
    oth["band90_sales_yoy"] = band.loc[oth.ym, "sales_yoy"].values
    oth["band90_c_receipts_adj"] = band.loc[oth.ym, "c_receipts_adj"].values
    oth["share_seeds_negative"] = [float((allseed[allseed.ym == m].sales_yoy < 0).mean()) for m in oth.ym]
    oth.to_csv(RES / "E_down_months.csv", index=False)

    # 業界（商業動態統計 スーパー、全店ベース・名目）の前年比
    s_ = pd.read_csv(ROOT / "data" / "f246" / "data" / "raw" / "sales_monthly_6types.csv")
    s_ = s_[(s_["業態"] == "スーパー") & (s_["品目"] == "合計")].set_index("ym")["販売額_百万円"]
    ind = (s_ / s_.shift(12) - 1).reindex(MONTHS)
    ind.rename("industry_supermarket_yoy").to_csv(RES / "F_industry_yoy.csv")

    main_ = {"target": TARGET, "down_months": down, "seed0_vs_mart_max_abs_diff": seed0_vs_mart,
             "target_values": {k: float(t[k]) for k in num if not k.startswith(("store_", "cat_c_"))},
             "target_band90_half": {k: float(bt[k]) for k in ["sales_yoy", "receipts_yoy", "receipts_adj_yoy", "items_per_receipt_yoy",
                                                              "unit_price_yoy", "calendar_receipts", "c_receipts_adj"]},
             "band90_sales_yoy_by_month": band.sales_yoy.round(5).to_dict(),
             "band_q90_sales_yoy_target": float(band_q.loc[TARGET, "sales_yoy"]),
             "store_band90_half_median": float(band.loc[TARGET, [c for c in band.columns if c.startswith("store_sales_yoy_")]].median()),
             "cat_band90_half": {c.replace("cat_sales_yoy_", ""): float(band.loc[TARGET, c]) for c in band.columns if c.startswith("cat_sales_yoy_")},
             "area_band90_half": {a: float(band.loc[TARGET, f"area_receipts_adj_yoy_{a}"]) for a in AREAS},
             "rel_target": {c: [float(t[c]), float(bt[c]), bool(abs(t[c]) > bt[c])] for c in cols_sub},
             "rel_beyond_count_seed0": int(sum(abs(t[c]) > bt[c] for c in cols_sub)),
             "fy2025_area_seed0": {k: float(v) for k, v in fya0.items() if k != "fy"},
             "fy2025_area_band90_half": {k: float(v) for k, v in fyb.items()},
             "fy2025_area_seed_mean": {k: float(v) for k, v in fya.drop(columns=["fy", "seed"]).mean().items()},
             "truth": truth, "robustness": rob,
             "industry_yoy_FY2025": ind.loc["2025-04":].round(6).to_dict()}
    json.dump(main_, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(main_, ensure_ascii=False, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
