"""03 分析：来期（FY2026）の売上の予測と幅を作り、予算案の数字にする。

A. 自社の過去で試す（バックテスト）：FY2022〜の店×月の売上で、起点 2024-03〜2025-03 の13回 × 乱数の種20通り。
   12か月先までの合計（＝1年分の予算の数字）の外れを、店・地域・全社で比べる。モデルは F231 と同じ系統
   （季節ナイーブ、季節ナイーブ＋直近の伸び、それに暦の補正、ETS、SARIMA）。全社は「直接」と「店の足し上げ」（F232）。
B. 業界の長い記録で試す：商業動態統計（スーパー、2014-01〜2026-08）で同じモデルを、起点 2015-12〜2025-08 の毎月で回す。
C. 幅の作り方を比べる：①モデルの区間（ETS・SARIMA の乱数シミュレーション）②自社の過去の外れ ③業界の外れを借り、
   自社の偶然の揺れを足す。①と③が、実際をどれだけ覆ったかを、自社（13回×20通り）と業界（時間を進めながら）で確かめる。
D. FY2026 の予算：2026年3月時点（seed 0 ＝ F247 の mart と同じ数字）で、店×月の予測、利益までの予算、下振れ・基本・上振れ。
E. 答え合わせ：2026年4〜8月（02_整形.py で同じ設定のまま足した5か月）と比べる。
F. 頑健性。
出力：results/ の CSV と main.json
"""
import json, pathlib, warnings
from multiprocessing import Pool
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
SEEDS = list(range(20))
Z80 = 1.2816
MODELS = ["季節ナイーブ", "季節ナイーブ＋伸び", "季節ナイーブ＋伸び＋暦", "ETS", "SARIMA"]
COVID = ("2020-03", "2021-12")


def months(a, b):
    return [p.strftime("%Y-%m") for p in pd.period_range(a, b, freq="M")]


ALLM = months("2022-04", "2026-08")
DIM = pd.read_csv(ROOT / "data" / "mart" / "dim_store.csv", encoding="utf-8-sig", parse_dates=["open_date", "close_date"])
FULL20 = sorted(set(DIM.store_id) - {8, 16, 21, 24})          # 2022-04〜2026-03 にずっと営業している20店
FY26 = sorted(set(DIM.store_id) - {21, 24})                    # FY2026 に営業する22店
AREA = DIM.set_index("store_id").area


# ---------- 暦の重み（曜日・祝日・年末）：FY2022〜FY2023 の店×日で推定（どの起点よりも前のデータだけ） ----------
def calendar_weights():
    sd = pd.read_csv(ROOT / "data" / "mart" / "fact_store_day.csv.gz", parse_dates=["biz_date"])
    sd = sd[(sd.biz_date >= "2022-04-01") & (sd.biz_date <= "2024-03-31") & sd.store_id.isin(FULL20)]
    cal = pd.read_csv(ROOT / "data" / "f246" / "data" / "raw" / "calendar_daily.csv.gz", parse_dates=["date"])
    d = sd.merge(cal[["date", "dow", "hol"]], left_on="biz_date", right_on="date")
    d["ym"] = d.date.dt.strftime("%Y-%m")
    d["ly"] = np.log(d.sales)
    d["ly"] -= d.groupby(["store_id", "ym"]).ly.transform("mean")
    X = pd.get_dummies(d.dow, prefix="dow", drop_first=True).astype(float)
    X["wdhol"] = (d.hol & (d.dow < 5)).astype(float)
    X["yearend"] = ((d.date.dt.month == 12) & (d.date.dt.day >= 28)).astype(float)
    Xc = X - X.groupby([d.store_id, d.ym]).transform("mean")
    beta = np.linalg.lstsq(Xc.values, d.ly.values, rcond=None)[0]
    coef = dict(zip(X.columns, beta))
    c = cal[(cal.date >= "2021-04-01") & (cal.date <= "2027-03-31")].copy()
    w = np.zeros(len(c))
    for k in range(1, 7):
        w += coef.get(f"dow_{k}", 0) * (c.dow == k)
    w += coef["wdhol"] * (c.hol & (c.dow < 5)) + coef["yearend"] * ((c.date.dt.month == 12) & (c.date.dt.day >= 28))
    c["w"] = np.exp(w)
    W = c.groupby(c.date.dt.strftime("%Y-%m")).w.sum()
    return W, coef


W, CAL_COEF = calendar_weights()


def cal_ratio(target_months):
    return np.array([W[m] / W[(pd.Period(m, "M") - 12).strftime("%Y-%m")] for m in target_months])


# ---------- モデル ----------
def forecast(y, H, target_months, which=MODELS, sim=False):
    """y：月の売上（古い順、長さ24以上）。戻り値：{モデル: 長さHの予測}（sim=True なら ETS・SARIMA の乱数の道も）"""
    y = np.asarray(y, float)
    out, sims = {}, {}
    last = y[-12:]
    reps = np.tile(last, int(np.ceil(H / 12)))[:H]
    g = y[-12:].sum() / y[-24:-12].sum()
    if "季節ナイーブ" in which:
        out["季節ナイーブ"] = reps
    if "季節ナイーブ＋伸び" in which:
        out["季節ナイーブ＋伸び"] = reps * g ** (1 + np.arange(H) // 12)
    if "季節ナイーブ＋伸び＋暦" in which:
        out["季節ナイーブ＋伸び＋暦"] = reps * g ** (1 + np.arange(H) // 12) * cal_ratio(target_months)
    ly = np.log(y)
    if "ETS" in which:
        r = ExponentialSmoothing(ly, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
                                 initialization_method="estimated").fit()
        out["ETS"] = np.exp(r.forecast(H))
        if sim:
            sims["ETS"] = np.exp(r.simulate(H, repetitions=500, error="add", anchor="end", random_state=1))
    if "SARIMA" in which:
        r = SARIMAX(ly, order=(0, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False, maxiter=50)
        out["SARIMA"] = np.exp(r.forecast(H))
        if sim:
            sims["SARIMA"] = np.exp(r.simulate(H, repetitions=500, anchor="end", rng=np.random.default_rng(1))[:, 0, :])
    return (out, sims) if sim else out


def load():
    m = pd.read_csv(ROOT / "data" / "store_month_seeds.csv.gz")
    return m


ORIGINS = months("2024-03", "2025-03")      # 自社のバックテストの起点（12か月先が2026-03までに収まる）


def company_seed(args):
    seed, m = args
    piv = m.pivot(index="ym", columns="store_id", values="sales").reindex(ALLM)
    rows, mrows, irows = [], [], []
    for o in ORIGINS:
        tr = months("2022-04", o)
        tg = months((pd.Period(o, "M") + 1).strftime("%Y-%m"), (pd.Period(o, "M") + 12).strftime("%Y-%m"))
        store_fc = {}
        for s in FULL20:
            f = forecast(piv.loc[tr, s].values, 12, tg)
            store_fc[s] = f
            a = piv.loc[tg, s].values
            for k, v in f.items():
                rows.append((seed, o, "店", str(s), k, "直接", v.sum(), a.sum()))
        units = {"全社": FULL20, **{a: [s for s in FULL20 if AREA[s] == a] for a in ["都市", "郊外", "地方"]}}
        for u, ss in units.items():
            lvl = "全社" if u == "全社" else "地域"
            y = piv.loc[tr, ss].sum(1).values
            a = piv.loc[tg, ss].sum(1).values
            if u == "全社":
                f, sims = forecast(y, 12, tg, sim=True)
                for k in sims:
                    tot = sims[k].sum(0)
                    irows.append((seed, o, k, *np.quantile(tot, [0.1, 0.5, 0.9]), a.sum()))
            else:
                f = forecast(y, 12, tg)
            for k, v in f.items():
                rows.append((seed, o, lvl, u, k, "直接", v.sum(), a.sum()))
                bu = sum(store_fc[s][k] for s in ss)
                rows.append((seed, o, lvl, u, k, "足し上げ", bu.sum(), a.sum()))
                if u == "全社":
                    for i, t in enumerate(tg):
                        mrows.append((seed, o, k, "直接", t, v[i], a[i]))
                        mrows.append((seed, o, k, "足し上げ", t, bu[i], a[i]))
    return rows, mrows, irows


def industry_backtest(ind, H, window=None):
    y = ind.sales_mil
    idx = list(y.index)
    rows = []
    for o in months("2015-12", (pd.Period("2026-08", "M") - H).strftime("%Y-%m")):
        i = idx.index(o)
        tr = y.iloc[: i + 1] if window is None else y.iloc[max(0, i + 1 - window): i + 1]
        tg = idx[i + 1: i + 1 + H]
        f = forecast(tr.values, H, tg, which=["季節ナイーブ", "季節ナイーブ＋伸び", "ETS", "SARIMA"])
        a = y.loc[tg].values
        covid = any(COVID[0] <= t <= COVID[1] for t in tg)
        for k, v in f.items():
            rows.append((o, tg[-1], k, v.sum(), a.sum(), covid))
    d = pd.DataFrame(rows, columns=["origin", "target_end", "model", "fc", "act", "covid"])
    d["log_err"] = np.log(d.act / d.fc)
    return d


def noise_sd(piv_tot, ind, o, n_months=12):
    """自社の偶然の揺れ（年の合計、対数）：自社の前年比と業界の前年比の差の、月ごとのばらつき÷√12。起点までのデータだけ。"""
    ms = months("2023-04", o)
    c = np.log(piv_tot.loc[ms].values / piv_tot.loc[[(pd.Period(m, "M") - 12).strftime("%Y-%m") for m in ms]].values)
    i = np.log(ind.sales_mil.loc[ms].values / ind.sales_mil.loc[[(pd.Period(m, "M") - 12).strftime("%Y-%m") for m in ms]].values)
    dlt = c - i
    return float(np.std(dlt, ddof=1) / np.sqrt(n_months)), len(ms)


def borrowed_interval(ib, model, o, sdn, z=Z80, covid_ok=False, keep_bias=False):
    """業界の外れ（その起点までに結果が出た回だけ）から幅を借りる。
    keep_bias=False（主）：幅の広さだけ借り、真ん中は自社の予測のまま（左右同じ幅）。
    keep_bias=True（頑健性）：業界の外れの 10%・50%・90% 点をそのまま使う（過去の偏りも借りる）。"""
    e = ib[(ib.model == model) & (ib.target_end <= o)]
    if not covid_ok:
        e = e[~e.covid]
    q10, q50, q90 = np.quantile(e.log_err, [0.1, 0.5, 0.9])
    sdm = (q90 - q10) / (2 * Z80)
    if keep_bias:
        k = z / Z80
        lo = q50 - np.sqrt((k * (q50 - q10)) ** 2 + (z * sdn) ** 2)
        hi = q50 + np.sqrt((k * (q90 - q50)) ** 2 + (z * sdn) ** 2)
        return lo, hi, sdm, len(e)
    half = z * np.sqrt(sdm ** 2 + sdn ** 2)
    return -half, half, sdm, len(e)


def main():
    m = load()
    ind = pd.read_csv(ROOT / "data" / "industry_super_monthly.csv").set_index("ym")
    main_j = {"calendar_coef": {k: round(float(v), 4) for k, v in CAL_COEF.items()}}

    # ---- A. 自社のバックテスト ----
    import sys
    if "--reuse" in sys.argv and (RES / "C_model_interval_company.csv").exists():
        # 時間のかかる A（2コアで約15分）を、前の実行の結果から読み直す（中身は同じ計算）
        A = pd.read_csv(RES / "A_company_backtest_annual.csv.gz", dtype={"unit": str})
        Am = pd.read_csv(RES / "A_company_backtest_monthly_total.csv.gz")
        Ai = pd.read_csv(RES / "C_model_interval_company.csv")
    else:
        with Pool(2) as p:
            res = p.map(company_seed, [(s, m[m.seed == s]) for s in SEEDS])
        A = pd.DataFrame([r for x in res for r in x[0]], columns=["seed", "origin", "level", "unit", "model", "method", "fc", "act"])
        A["log_err"] = np.log(A.act / A.fc); A["ape"] = (A.fc / A.act - 1).abs()
        A.to_csv(RES / "A_company_backtest_annual.csv.gz", index=False, float_format="%.6g")
        Am = pd.DataFrame([r for x in res for r in x[1]], columns=["seed", "origin", "model", "method", "ym", "fc", "act"])
        Am.to_csv(RES / "A_company_backtest_monthly_total.csv.gz", index=False, float_format="%.6g")
        Ai = pd.DataFrame([r for x in res for r in x[2]], columns=["seed", "origin", "model", "q10", "q50", "q90", "act"])
        Ai.to_csv(RES / "C_model_interval_company.csv", index=False, float_format="%.6g")

    s1 = (A.groupby(["level", "method", "model"]).ape.mean().unstack("model")[MODELS] * 100).round(2)
    s1.to_csv(RES / "A_annual_mape_by_level.csv")
    budget_orig = A[A.origin.isin(["2024-03", "2025-03"])]
    s1b = (budget_orig.groupby(["level", "method", "model"]).ape.mean().unstack("model")[MODELS] * 100).round(2)
    s1b.to_csv(RES / "A_annual_mape_by_level_budget_origins.csv")
    Am["ape"] = (Am.fc / Am.act - 1).abs()
    s2 = (Am.groupby(["method", "model"]).ape.mean().unstack("model")[MODELS] * 100).round(2)
    s2.to_csv(RES / "A_monthly_mape_total.csv")
    main_j["A_annual_mape"] = {f"{a}|{b}": r.to_dict() for (a, b), r in s1.iterrows()}
    main_j["A_annual_mape_budget_origins"] = {f"{a}|{b}": r.to_dict() for (a, b), r in s1b.iterrows()}
    main_j["A_monthly_mape_total"] = {k: r.to_dict() for k, r in s2.iterrows()}
    # 全社の外れの年ごとの中身（起点 2024-03 ＝ FY2024 予算、2025-03 ＝ FY2025 予算）
    t = A[(A.level == "全社") & (A.method == "直接") & A.origin.isin(["2024-03", "2025-03"])]
    main_j["A_total_err_budget_origins"] = (t.groupby(["origin", "model"]).log_err.agg(["mean", "std", "min", "max"]) * 100).round(2).reset_index().to_dict("records")

    # ---- B. 業界の長い記録 ----
    ib12 = industry_backtest(ind, 12)
    ib5 = industry_backtest(ind, 5)
    ib12w = industry_backtest(ind, 12, window=36)
    ib12.to_csv(RES / "B_industry_backtest_h12.csv", index=False, float_format="%.6g")
    ib5.to_csv(RES / "B_industry_backtest_h5.csv", index=False, float_format="%.6g")
    ib12w.to_csv(RES / "B_industry_backtest_h12_window36.csv", index=False, float_format="%.6g")
    bsum = []
    for nm, d in [("全期間", ib12), ("直近36か月だけで学習", ib12w)]:
        for cv in [False, True]:
            dd = d if cv else d[~d.covid]
            g = dd.groupby("model").log_err
            r = pd.DataFrame({"n": g.size(), "MAPE%": (dd.assign(a=(dd.fc / dd.act - 1).abs()).groupby("model").a.mean() * 100),
                              "q10%": g.quantile(0.1) * 100, "q90%": g.quantile(0.9) * 100, "mean%": g.mean() * 100})
            r["学習"] = nm; r["コロナ期"] = "含む" if cv else "除く"
            bsum.append(r.reset_index())
    bsum = pd.concat(bsum).round(2)
    bsum.to_csv(RES / "B_industry_annual_error_summary.csv", index=False)
    main_j["B_industry"] = bsum.to_dict("records")

    # ---- C. 幅の作り方と、覆えた割合 ----
    piv0 = {s: m[m.seed == s].pivot(index="ym", columns="store_id", values="sales").reindex(ALLM)[FULL20].sum(1) for s in SEEDS}
    crow = []
    MAINM = "季節ナイーブ＋伸び＋暦"
    for s in SEEDS:
        for o in ORIGINS:
            r = A[(A.seed == s) & (A.origin == o) & (A.level == "全社") & (A.method == "足し上げ")].set_index("model")
            sdn, nn = noise_sd(piv0[s], ind, o)
            for mdl in ["季節ナイーブ＋伸び＋暦", "季節ナイーブ＋伸び", "ETS", "SARIMA"]:
                bm = "季節ナイーブ＋伸び" if mdl.startswith("季節ナイーブ＋伸び") else mdl
                lo, hi, sdm, ne = borrowed_interval(ib12, bm, o, sdn)
                e = r.loc[mdl, "log_err"]
                crow.append((s, o, mdl, "③業界の外れ＋自社の揺れ", lo, hi, e, sdm, sdn, ne))
                lo2, hi2, _, _ = borrowed_interval(ib12, bm, o, 0.0)
                crow.append((s, o, mdl, "③'業界の外れだけ", lo2, hi2, e, sdm, 0.0, ne))
            # ② 自社の過去の外れ（起点までに結果が出た回だけ）
            past = A[(A.seed == s) & (A.level == "全社") & (A.method == "足し上げ") & (A.model == MAINM)]
            past = past[past.origin.map(lambda x: (pd.Period(x, "M") + 12).strftime("%Y-%m")) <= o]
            e = r.loc[MAINM, "log_err"]
            if len(past) >= 2:
                lo, hi = np.quantile(past.log_err, [0.1, 0.9])
            else:
                lo, hi = np.nan, np.nan
            crow.append((s, o, MAINM, "②自社の過去の外れ", lo, hi, e, np.nan, np.nan, len(past)))
    C = pd.DataFrame(crow, columns=["seed", "origin", "model", "method", "lo", "hi", "log_err", "sd_market", "sd_noise", "n_cal"])
    # ① モデルの区間（全社・直接）
    for _, r in Ai.iterrows():
        a = r.act
        C.loc[len(C)] = (r.seed, r.origin, r.model, "①モデルの区間", np.log(r.q10 / r.q50), np.log(r.q90 / r.q50),
                         np.log(a / r.q50), np.nan, np.nan, np.nan)
    C["covered"] = (C.log_err >= C.lo) & (C.log_err <= C.hi)
    C["width_pct"] = (np.exp(C.hi) - np.exp(C.lo)) * 100
    C.to_csv(RES / "C_interval_coverage_company.csv", index=False, float_format="%.6g")
    cs = C.dropna(subset=["lo"]).groupby(["method", "model"]).agg(n=("covered", "size"), covered=("covered", "mean"),
                                                                width=("width_pct", "median")).reset_index()
    cs["covered"] = (cs.covered * 100).round(1); cs["width"] = cs.width.round(2)
    cs2 = C.dropna(subset=["lo"])[C.origin.isin(["2024-03", "2025-03"])].groupby(["method", "model", "origin"]).agg(
        covered=("covered", "mean"), width=("width_pct", "median")).reset_index()
    cs.to_csv(RES / "C_interval_coverage_summary.csv", index=False)
    cs2.to_csv(RES / "C_interval_coverage_budget_origins.csv", index=False)
    main_j["C_coverage"] = cs.to_dict("records")
    main_j["C_coverage_budget_origins"] = cs2.round(4).to_dict("records")
    main_j["C_own_past_n_at_2025-03"] = int(C[(C.method == "②自社の過去の外れ") & (C.origin == "2025-03")].n_cal.iloc[0])
    # 業界そのものでの、時間を進めながらの覆えた割合（その起点までに結果が出た外れで幅を作る）
    irow = []
    for mdl in ["季節ナイーブ＋伸び", "ETS", "SARIMA"]:
        d = ib12[(ib12.model == mdl)].reset_index(drop=True)
        for _, r in d.iterrows():
            if r.covid or r.origin < "2018-12":
                continue
            lo, hi, sdm, ne = borrowed_interval(ib12, mdl, r.origin, 0.0)
            irow.append((mdl, r.origin, lo, hi, r.log_err, ne))
    I = pd.DataFrame(irow, columns=["model", "origin", "lo", "hi", "log_err", "n_cal"])
    I["covered"] = (I.log_err >= I.lo) & (I.log_err <= I.hi)
    I["period"] = np.where(I.origin < "2022-01", "2018-12〜2021", "2022〜2025-08")
    isum = I.groupby(["model", "period"]).agg(n=("covered", "size"), covered=("covered", "mean")).reset_index()
    isum["covered"] = (isum.covered * 100).round(1)
    I.to_csv(RES / "C_interval_coverage_industry.csv", index=False, float_format="%.6g")
    isum.to_csv(RES / "C_interval_coverage_industry_summary.csv", index=False)
    main_j["C_industry_coverage"] = isum.to_dict("records")

    # ---- D. FY2026 の予算（seed 0） ----
    O = "2025-03"  # 予算を立てる時点は 2026-03 だが、表記をそろえるため下で上書き
    O = "2026-03"
    tg = months("2026-04", "2027-03")
    budget, per_model = {}, {}
    m0 = m[m.seed == 0]
    piv = m0.pivot(index="ym", columns="store_id", values="sales").reindex(ALLM)
    tr = months("2022-04", O)
    for s in FULL20:
        budget[s] = forecast(piv.loc[tr, s].values, 12, tg)
    # 新しい店：08（2024-10 開店、18か月）は「前年の同じ月 × 地域の20店の伸び × 暦」。
    #          16（2025-04 開店、12か月、最初の半年は立ち上がり）は「直近3か月の水準（地域の季節で割る）× 地域の季節 × 伸び」
    #          → どちらも決め（推測を含む）。README に書く。
    for s, rule in [(8, "前年×地域の伸び"), (16, "直近3か月×地域の季節")]:
        peers = [x for x in FULL20 if AREA[x] == AREA[s]]
        py = piv.loc[:, peers].sum(1)
        g = py.loc[months("2025-04", "2026-03")].sum() / py.loc[months("2024-04", "2025-03")].sum()
        cr = cal_ratio(tg)
        if rule == "前年×地域の伸び":
            base = piv.loc[months("2025-04", "2026-03"), s].values
        else:
            seas = py.loc[months("2025-04", "2026-03")].values / py.loc[months("2025-04", "2026-03")].mean()
            lvl = (piv.loc[months("2026-01", "2026-03"), s].values / seas[-3:]).mean()
            base = lvl * seas
        f = base * g * cr
        budget[s] = {k: f for k in MODELS}
    # 予算に使うモデル（A の結果で決める：全社・足し上げで、予算の起点での外れが小さいもの → ここでは手で固定して README に理由）
    BM = MAINM
    bt = pd.DataFrame({s: budget[s][BM] for s in FY26}, index=tg)
    tot_fc = bt.sum(1)
    # 範囲：③業界の外れ＋自社の揺れ（2026-03 までの情報だけ）
    sdn, nn = noise_sd(piv0[0], ind, O)
    lo, hi, sdm, ne = borrowed_interval(ib12, "季節ナイーブ＋伸び", O, sdn)
    lo90, hi90, _, _ = borrowed_interval(ib12, "季節ナイーブ＋伸び", O, sdn, z=1.6449)
    # 1年前の実績（FY2025、同じ22店・閉店した店は除く）
    fy25 = piv.loc[months("2025-04", "2026-03"), FY26].sum(1)
    main_j["D_budget"] = {
        "model": BM, "FY2026_sales_base": float(tot_fc.sum()), "FY2025_sales_same22": float(fy25.sum()),
        "growth_base_pct": float((tot_fc.sum() / fy25.sum() - 1) * 100),
        "range80_pct": [float((np.exp(lo) - 1) * 100), float((np.exp(hi) - 1) * 100)],
        "range90_pct": [float((np.exp(lo90) - 1) * 100), float((np.exp(hi90) - 1) * 100)],
        "sd_market_log": sdm, "sd_noise_log": sdn, "n_industry_errors": ne, "n_noise_months": nn,
        "FY2025_all24_sales": float(piv.loc[months("2025-04", "2026-03")].sum(1).sum()),
    }
    # 各モデルでの FY2026（全社22店）
    per = {k: float(sum(budget[s][k].sum() for s in FY26)) for k in MODELS}
    main_j["D_budget_by_model"] = per

    # 利益までの予算：粗利率は FY2025 の店ごとの実績、人時は「店の固定分＋客数に比例」を FY2024〜25 の店×月で推定、
    # 時給と経費の伸びは、直近12か月の前年比（データから）。客数は売上の伸びのうち、一品単価の伸び（直近12か月）を除いた分。
    m0 = m0.copy(); m0["fy"] = m0.ym.str[:4].astype(int) - (m0.ym.str[5:7].astype(int) < 4)
    f25 = m0[m0.fy == 2025]; f24 = m0[m0.fy == 2024]
    fy = m0[m0.ym.isin(months("2024-04", "2026-03"))].copy()
    fy["hpd"] = fy.labor_hours / fy.days; fy["rpd"] = fy.receipts / fy.days
    Xr = fy.rpd - fy.groupby("store_id").rpd.transform("mean"); Yh = fy.hpd - fy.groupby("store_id").hpd.transform("mean")
    b_hours = float((Xr * Yh).sum() / (Xr ** 2).sum())
    same = f25.store_id.isin(FULL20)
    wage_g = float((f25[same].labor_cost.sum() / f25[same].labor_hours.sum()) / (f24[f24.store_id.isin(FULL20)].labor_cost.sum() / f24[f24.store_id.isin(FULL20)].labor_hours.sum()) - 1)
    oth_g = float(f25[same].other_cost.sum() / f24[f24.store_id.isin(FULL20)].other_cost.sum() - 1)
    up_g = float((f25[same].sales.sum() / f25[same]["items"].sum()) / (f24[f24.store_id.isin(FULL20)].sales.sum() / f24[f24.store_id.isin(FULL20)]["items"].sum()) - 1)
    ipr_g = float((f25[same]["items"].sum() / f25[same].receipts.sum()) / (f24[f24.store_id.isin(FULL20)]["items"].sum() / f24[f24.store_id.isin(FULL20)].receipts.sum()) - 1)
    main_j["D_drivers"] = {"hours_per_receipt": b_hours, "wage_growth": wage_g, "other_cost_growth": oth_g,
                           "unit_price_growth": up_g, "items_per_receipt_growth": ipr_g}

    def pl(scale, sales_given=None):
        """scale：売上の全社の倍率（範囲の端で使う）。sales_given（店×月の売上の表）を渡すと、その売上で利益まで計算する。"""
        rows = []
        for s in FY26:
            ref = m0[(m0.store_id == s) & m0.ym.isin(months("2025-04", "2026-03"))].set_index("ym")
            gp_rate = ref.gross_profit.sum() / ref.sales.sum()
            for i, t in enumerate(tg):
                lt = (pd.Period(t, "M") - 12).strftime("%Y-%m")
                r = ref.loc[lt] if lt in ref.index else None
                sales = bt.loc[t, s] * scale if sales_given is None else sales_given.loc[t, s]
                if r is None or r.days < pd.Period(lt, "M").days_in_month:
                    # 前年の同じ月に満足な実績がない店（16店の立ち上がり期間）は、直近3か月の平均で置く
                    rr = ref.loc[months("2026-01", "2026-03")].mean()
                    r = rr
                vol_ratio = (sales / r.sales) / ((1 + up_g) * (1 + ipr_g))   # 客数の前年比
                receipts = r.receipts * vol_ratio
                hours = r.labor_hours + b_hours * (receipts - r.receipts)
                labor = hours * (r.labor_cost / r.labor_hours) * (1 + wage_g)
                other = r.other_cost * (1 + oth_g)
                gp = sales * gp_rate
                rows.append((s, AREA[s], t, sales, receipts, gp, hours, labor, other, gp - labor - other))
        return pd.DataFrame(rows, columns=["store_id", "area", "ym", "sales", "receipts", "gross_profit", "labor_hours",
                                           "labor_cost", "other_cost", "operating_profit"])

    base = pl(1.0); down = pl(np.exp(lo)); up = pl(np.exp(hi))
    base.to_csv(RES / "D_budget_store_month_base.csv", index=False, float_format="%.0f")
    sc = pd.DataFrame({k: d[["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].sum()
                       for k, d in [("下振れ（10%）", down), ("基本", base), ("上振れ（90%）", up)]}).T
    act25 = m0[(m0.fy == 2025) & m0.store_id.isin(FY26)][["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].sum()
    act25all = m0[(m0.fy == 2025)][["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].sum()
    sc.loc["FY2025 実績（同じ22店）"] = act25
    sc.loc["FY2025 実績（全24店）"] = act25all
    sc.to_csv(RES / "D_budget_scenarios.csv", float_format="%.0f")
    main_j["D_scenarios_oku"] = (sc / 1e8).round(3).to_dict("index")
    main_j["D_op_range_pct_vs_base"] = [float(down.operating_profit.sum() / base.operating_profit.sum() - 1) * 100,
                                        float(up.operating_profit.sum() / base.operating_profit.sum() - 1) * 100]
    ar = base.groupby("area")[["sales", "operating_profit"]].sum()
    ar25 = m0[(m0.fy == 2025) & m0.store_id.isin(FY26)].assign(area=lambda d: d.store_id.map(AREA)).groupby("area")[["sales", "operating_profit"]].sum()
    ar["sales_yoy%"] = (ar.sales / ar25.sales - 1) * 100; ar["op_yoy%"] = (ar.operating_profit / ar25.operating_profit - 1) * 100
    ar.to_csv(RES / "D_budget_by_area.csv", float_format="%.4g")
    main_j["D_by_area"] = ar.round(3).to_dict("index")
    # 月割り：暦を入れる・入れないの差（予算の各月）
    nocal = sum(budget[s]["季節ナイーブ＋伸び"] for s in FY26)
    mp = pd.DataFrame({"ym": tg, "with_cal": tot_fc.values, "no_cal": nocal, "cal_ratio": cal_ratio(tg)})
    mp["diff%"] = (mp.with_cal / mp.no_cal - 1) * 100
    mp.to_csv(RES / "D_monthly_phasing.csv", index=False, float_format="%.6g")
    main_j["D_cal_diff_range"] = [float(mp["diff%"].min()), float(mp["diff%"].max())]

    # ---- E. 答え合わせ（2026-04〜08） ----
    em = months("2026-04", "2026-08")
    act = piv.loc[em, FY26].sum(1)
    fc5 = tot_fc.loc[em]
    sdn5 = sdn * np.sqrt(12 / 5)
    lo5, hi5, sdm5, ne5 = borrowed_interval(ib5, "季節ナイーブ＋伸び", O, sdn5)
    e5 = float(np.log(act.sum() / fc5.sum()))
    E = pd.DataFrame({"ym": em, "budget": fc5.values, "actual": act.values})
    E["diff%"] = (E.actual / E.budget - 1) * 100
    E["actual_yoy%"] = (act.values / piv.loc[[(pd.Period(x, "M") - 12).strftime("%Y-%m") for x in em], FY26].sum(1).values - 1) * 100
    iy = ind.sales_mil
    E["industry_yoy%"] = [(iy[x] / iy[(pd.Period(x, "M") - 12).strftime("%Y-%m")] - 1) * 100 for x in em]
    E.to_csv(RES / "E_check_apr_aug_2026.csv", index=False, float_format="%.6g")
    per5 = {k: float((act.sum() / sum(budget[s][k][:5].sum() for s in FY26) - 1) * 100) for k in MODELS}
    # 業界：12か月の前年比（予算時点の直近）と、4〜8月の前年比
    ind_g12 = float(iy.loc[months("2025-04", "2026-03")].sum() / iy.loc[months("2024-04", "2025-03")].sum() - 1) * 100
    ind_g5 = float(iy.loc[em].sum() / iy.loc[months("2025-04", "2025-08")].sum() - 1) * 100
    # 5か月の利益
    act_op5 = m0[m0.ym.isin(em) & m0.store_id.isin(FY26)].operating_profit.sum()
    bud_op5 = base[base.ym.isin(em)].operating_profit.sum()
    # 売上の外れと、費用の見込みの外れを分ける：実績の売上を入れて、同じ作り方で利益を計算する
    ag = pd.DataFrame({x: piv.loc[em, x] for x in FY26})
    ag = pd.concat([ag, pd.DataFrame(index=[t for t in tg if t not in em], columns=FY26, dtype=float).fillna(0)])
    pg = pl(1.0, sales_given=ag)
    pg5 = pg[pg.ym.isin(em)]
    a5 = m0[m0.ym.isin(em) & m0.store_id.isin(FY26)]
    b5 = base[base.ym.isin(em)]
    E2 = pd.DataFrame({"予算": b5[["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].sum(),
                       "実績の売上で計算": pg5[["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].sum(),
                       "実績": a5[["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].sum()}) / 1e8
    E2.to_csv(RES / "E_check_pl_apr_aug_2026.csv", float_format="%.4f")
    main_j["E_pl_split_oku"] = E2.round(4).to_dict()
    lo5b, hi5b, _, _ = borrowed_interval(ib5, "季節ナイーブ＋伸び", O, sdn5, keep_bias=True)
    main_j["E_check_keep_bias_range5_pct"] = [float((np.exp(lo5b) - 1) * 100), float((np.exp(hi5b) - 1) * 100)]
    main_j["E_check"] = {"cum5_diff_pct": float((np.exp(e5) - 1) * 100), "range5_pct": [float((np.exp(lo5) - 1) * 100), float((np.exp(hi5) - 1) * 100)],
                         "inside": bool(lo5 <= e5 <= hi5), "by_model_diff_pct": per5, "industry_yoy_12m_to_2026-03": ind_g12,
                         "industry_yoy_apr_aug_2026": ind_g5, "op5_actual_oku": act_op5 / 1e8, "op5_budget_oku": bud_op5 / 1e8,
                         "op5_diff_pct": float((act_op5 / bud_op5 - 1) * 100)}

    # ---- F. 頑健性 ----
    rob = {}
    # F1 業界の幅：コロナ期を含める
    l, h, sdmc, nc = borrowed_interval(ib12, "季節ナイーブ＋伸び", O, sdn, covid_ok=True)
    rob["F1_covid_included_range80_pct"] = [float((np.exp(l) - 1) * 100), float((np.exp(h) - 1) * 100), nc]
    # F2 業界の学習を直近36か月に限る（自社と同じくらい短い記録）
    l, h, _, nw = borrowed_interval(ib12w, "季節ナイーブ＋伸び", O, sdn)
    rob["F2_window36_range80_pct"] = [float((np.exp(l) - 1) * 100), float((np.exp(h) - 1) * 100), nw]
    # F3 直近5年の外れだけで幅を作る
    e = ib12[(ib12.model == "季節ナイーブ＋伸び") & (ib12.target_end <= O) & ~ib12.covid & (ib12.origin >= "2020-03")]
    q = np.quantile(e.log_err, [0.1, 0.9]); sdm3 = (q[1] - q[0]) / (2 * Z80); hh = Z80 * np.sqrt(sdm3 ** 2 + sdn ** 2)
    rob["F3_recent_errors_only_range80_pct"] = [float((np.exp(-hh) - 1) * 100), float((np.exp(hh) - 1) * 100), int(len(e)), float(e.log_err.mean() * 100)]
    # F4 乱数の種20通りで、FY2026 の基本の予算がどれだけ動くか（過去の偶然の揺れが予算に移る分）
    vals = []
    for s in SEEDS:
        ps = m[m.seed == s].pivot(index="ym", columns="store_id", values="sales").reindex(ALLM)
        v = sum(forecast(ps.loc[tr, x].values, 12, tg, which=[BM])[BM].sum() for x in FULL20)
        a = ps.loc[months("2025-04", "2026-03"), FULL20].sum(1).sum()
        vals.append(v / a - 1)
    rob["F4_seeds_growth_pct"] = {"mean": float(np.mean(vals) * 100), "sd": float(np.std(vals, ddof=1) * 100),
                                  "min": float(np.min(vals) * 100), "max": float(np.max(vals) * 100)}
    # F5 予算の起点を変えると（自社の13回の起点で、全社・足し上げの外れの平均と幅）
    t = A[(A.level == "全社") & (A.method == "足し上げ") & (A.model == BM)]
    rob["F5_origin_mean_err_pct"] = (t.groupby("origin").log_err.mean() * 100).round(2).to_dict()
    # F6 物価（一品単価の伸び）の仮定を ±2pt 変えたときの売上と利益（客数・点数は同じとした場合）
    sens = {}
    for dlt in [-0.02, -0.01, 0.0, 0.01, 0.02]:
        d = pl(1 + dlt)
        sens[f"{dlt*100:+.0f}pt"] = {"sales_oku": float(d.sales.sum() / 1e8), "op_oku": float(d.operating_profit.sum() / 1e8)}
    rob["F6_sales_scale_sensitivity"] = sens
    # F7 業界の過去の偏りも借りる（真ん中を業界の外れの中央値だけずらす）
    l, h, _, _ = borrowed_interval(ib12, "季節ナイーブ＋伸び", O, sdn, keep_bias=True)
    rob["F7_keep_bias_range80_pct"] = [float((np.exp(l) - 1) * 100), float((np.exp(h) - 1) * 100)]
    cb = []
    for s_ in SEEDS:
        for o in ORIGINS:
            e_ = A[(A.seed == s_) & (A.origin == o) & (A.level == "全社") & (A.method == "足し上げ") & (A.model == MAINM)].log_err.iloc[0]
            sdn_, _ = noise_sd(piv0[s_], ind, o)
            l_, h_, _, _ = borrowed_interval(ib12, "季節ナイーブ＋伸び", o, sdn_, keep_bias=True)
            cb.append(l_ <= e_ <= h_)
    rob["F7_keep_bias_company_coverage_pct"] = float(np.mean(cb) * 100)
    # F8 90% の幅にしたときの、自社の覆えた割合
    c9 = []
    for s_ in SEEDS:
        for o in ORIGINS:
            e_ = A[(A.seed == s_) & (A.origin == o) & (A.level == "全社") & (A.method == "足し上げ") & (A.model == MAINM)].log_err.iloc[0]
            sdn_, _ = noise_sd(piv0[s_], ind, o)
            l_, h_, _, _ = borrowed_interval(ib12, "季節ナイーブ＋伸び", o, sdn_, z=1.6449)
            c9.append(l_ <= e_ <= h_)
    rob["F8_z90_company_coverage_pct"] = float(np.mean(c9) * 100)
    main_j["F_robustness"] = rob
    json.dump(main_j, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: main_j[k] for k in ["D_budget", "D_scenarios_oku", "E_check", "C_coverage", "C_industry_coverage"]}, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
