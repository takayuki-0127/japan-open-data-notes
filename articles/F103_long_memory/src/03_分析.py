"""分析：長期記憶の d を、推定法・帯域・期間・系列を変えて推定する

1. シミュレーション：推定法がどれだけ当たるか（本物の長期記憶／ただの AR／水準の段差）
2. 電力需要（東京・関西の日次の残差）
3. 消費者物価（中分類の前月比、季節と消費税の月を除いたもの）
4. 衝撃がどれだけ残るか（ARFIMA と AR の衝撃応答）
"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.tsa.ar_model import ar_select_order, AutoReg
from common import DATA, RAW, RES, SEED
from lm import (gph, local_whittle, whittle_arfima, dfa, rs_hurst, arfima_sim,
                impulse, all_estimates)

warnings.filterwarnings("ignore")
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)


def short_est(x):
    """シミュレーション用の軽い推定量のセット"""
    r = {"LW m=n^0.5": local_whittle(x, 0.5)[0], "LW m=n^0.6": local_whittle(x, 0.6)[0],
         "LW m=n^0.7": local_whittle(x, 0.7)[0], "LW m=n^0.8": local_whittle(x, 0.8)[0],
         "GPH m=n^0.6": gph(x, 0.6)[0], "ARFIMA(1,d,0)": whittle_arfima(x, 1)[0],
         "DFA": dfa(x)[0] - 0.5, "R/S": rs_hurst(x) - 0.5}
    return r


# ---------- 1. シミュレーション ----------
def level_shift(n, rng, k=10, size=1.0):
    """白色雑音＋ランダムな時点の水準の段差（k 回、段差の標準偏差 size）"""
    x = rng.standard_normal(n)
    pts = np.sort(rng.choice(np.arange(1, n), k, replace=False))
    lvl = np.zeros(n)
    for p in pts:
        lvl[p:] += rng.normal(0, size)
    return x + lvl


R = 200
rows = []
for n in (3834, 320):
    cases = {
        "白色雑音（d=0）": lambda: rng.standard_normal(n),
        "本物の長期記憶（d=0.3）": lambda: arfima_sim(n, 0.3, rng=rng),
        "AR(1)、φ=0.8（d=0）": lambda: arfima_sim(n, 0.0, 0.8, rng=rng),
        "長期記憶＋AR（d=0.3, φ=0.5）": lambda: arfima_sim(n, 0.3, 0.5, rng=rng),
        "水準の段差10回（d=0）": lambda: level_shift(n, rng, 10, 0.5),
    }
    for name, gen in cases.items():
        for r in range(R):
            x = gen()
            for k, v in short_est(x).items():
                rows.append({"n": n, "case": name, "rep": r, "estimator": k, "d": v})
    print("sim done n=", n)
sim = pd.DataFrame(rows)
simsum = sim.groupby(["n", "case", "estimator"])["d"].agg(["mean", "std",
                                                          lambda s: s.quantile(0.05), lambda s: s.quantile(0.95)])
simsum.columns = ["mean", "sd", "q05", "q95"]
simsum.round(3).to_csv(RES / "sim_summary.csv")
sim.to_csv(RES / "sim_all.csv.gz", index=False)

# ---------- 2. 電力需要 ----------
pw = pd.read_csv(DATA / "power_resid.csv", parse_dates=["date"])
est = []
for (a, s), g in pw.groupby(["area", "spec"], sort=False):
    r = all_estimates(g["resid"].values)
    r.update(area=a, spec=s, n=len(g), period=f"{g.date.min():%Y-%m}〜{g.date.max():%Y-%m}")
    est.append(r)
# 東京を関西と同じ期間（2024年4月〜）で推定し直す
raw = pd.read_csv(RAW / "daily_tokyo_f67.csv.gz", parse_dates=["date"])
raw = raw[(raw.n == 24) & (raw.date >= "2024-04-01")]
m = smf.ols("log_d ~ cr(temp_mean, df=8) + C(dow) + holiday + obon + nenmatsu + gw + C(month)", data=raw).fit()
r = all_estimates(m.resid.values)
r.update(area="東京", spec="暦と気温（関西と同じ期間）", n=len(raw), period="2024-04〜2026-09")
est.append(r)
# 東京を前半・後半に分ける
tk = pw[(pw.area == "東京") & (pw.spec == "暦と気温")]
for lab, g in [("前半", tk[tk.date < "2021-04-01"]), ("後半", tk[tk.date >= "2021-04-01"])]:
    r = all_estimates(g["resid"].values)
    r.update(area="東京", spec=f"暦と気温（{lab}）", n=len(g), period=f"{g.date.min():%Y-%m}〜{g.date.max():%Y-%m}")
    est.append(r)
# 週平均にしても同じか
w = tk.set_index("date")["resid"].resample("W").mean().dropna()
r = all_estimates(w.values)
r.update(area="東京", spec="暦と気温（週平均）", n=len(w), period="週次")
est.append(r)
pest = pd.DataFrame(est)
pest.to_csv(RES / "power_estimates.csv", index=False)
print(pest[["area", "spec", "n", "lw_0.6", "gph_0.6", "arfima_d", "dfa_d", "rs_d"]].round(3))

# 並べ替え（シャッフル）での帰無分布：順番を壊すと d は 0 付近になるはず
x = tk["resid"].values
shuf = [local_whittle(rng.permutation(x), 0.6)[0] for _ in range(500)]
pd.Series(shuf, name="lw06_shuffled").to_csv(RES / "power_shuffle.csv", index=False)
print("shuffle LW0.6: mean %.3f, 95%%点 %.3f" % (np.mean(shuf), np.quantile(shuf, 0.95)))

# 自己相関（元の系列、AR で当てたもの、ARFIMA で当てたもの）
def acf(x, L):
    x = x - x.mean()
    c0 = np.dot(x, x) / len(x)
    return np.array([np.dot(x[:-k], x[k:]) / len(x) / c0 for k in range(1, L + 1)])

L = 400
ac = pd.DataFrame({"lag": np.arange(1, L + 1)})
for spec in ["暦と気温", "暦と気温＋年度"]:
    x = pw[(pw.area == "東京") & (pw.spec == spec)]["resid"].values
    ac[f"data_{spec}"] = acf(x, L)
    sel = ar_select_order(x, maxlag=30, ic="bic", trend="c")
    p = max(sel.ar_lags) if sel.ar_lags else 0
    ar = AutoReg(x, lags=p, trend="c").fit()
    from statsmodels.tsa.arima_process import ArmaProcess
    proc = ArmaProcess(np.r_[1, -ar.params[1:]], [1])
    ac[f"ar_{spec}"] = proc.acf(L + 1)[1:]
    ac[f"ar_p_{spec}"] = p
    d, phi, _ = whittle_arfima(x, 1)
    y = arfima_sim(400000, d, phi[0], rng=np.random.default_rng(SEED))
    ac[f"arfima_{spec}"] = acf(y, L)
ac.to_csv(RES / "power_acf.csv", index=False)

# ---------- 3. 消費者物価 ----------
mom = pd.read_csv(DATA / "cpi_mom.csv", index_col=0, parse_dates=True)
items = pd.read_csv(DATA / "cpi_items.csv")
TAX = ["1989-04-01", "1997-04-01", "2014-04-01", "2019-10-01"]


def clean(s, tax=True):
    """月のダミー（季節）と消費税の月のダミーを除いた残り"""
    s = s.dropna()
    df = pd.DataFrame({"y": s.values, "m": s.index.month}, index=s.index)
    f = "y ~ C(m)"
    if tax:  # 消費税の月は1か月ずつ個別のダミー
        for t in TAX:
            c = "t" + t[:7].replace("-", "")
            df[c] = (s.index == pd.Timestamp(t)).astype(int)
            if df[c].sum():
                f += " + " + c
    return smf.ols(f, data=df).fit().resid


PERIODS = {"1971〜2026": ("1970-02-01", "2026-12-01"), "1971〜1999": ("1970-02-01", "1999-12-01"),
           "2000〜2026": ("2000-01-01", "2026-12-01"), "2000〜2021": ("2000-01-01", "2021-12-01")}
crow = []
for name in mom.columns:
    for pl, (a, b) in PERIODS.items():
        s = mom.loc[a:b, name].dropna()
        if len(s) < 200:
            continue
        for tax in (True, False):
            x = clean(s, tax).values
            if np.std(x) == 0:
                continue
            r = {"name": name, "period": pl, "tax_dummy": tax, "n": len(x)}
            r["lw_0.5"], _ = local_whittle(x, 0.5)
            r["lw_0.6"], r["lw_0.6_se"] = local_whittle(x, 0.6)
            r["lw_0.7"], _ = local_whittle(x, 0.7)
            r["gph_0.6"], r["gph_0.6_se"] = gph(x, 0.6)
            r["arfima_d"], phi, _ = whittle_arfima(x, 1)
            r["arfima_phi"] = phi[0]
            r["dfa_d"] = dfa(x)[0] - 0.5
            r["sd"] = np.std(x)
            crow.append(r)
cest = pd.DataFrame(crow).merge(items, on="name", how="left")
cest.to_csv(RES / "cpi_estimates.csv", index=False)
main = cest[(cest.period == "2000〜2026") & cest.tax_dummy]
print(main.sort_values("lw_0.6")[["name", "n", "lw_0.6", "arfima_d", "dfa_d", "weight10000"]].round(3).to_string())

# ---------- 4. 衝撃がどれだけ残るか ----------
H = 120
irs = []
def ir_rows(label, x, H):
    d, phi, _ = whittle_arfima(x, 1)
    a = impulse(d, phi, H)
    sel = ar_select_order(x, maxlag=24, ic="bic", trend="c")
    p = max(sel.ar_lags) if sel.ar_lags else 0
    from statsmodels.tsa.arima_process import ArmaProcess
    if p:
        ar = AutoReg(x, lags=p, trend="c").fit()
        b = ArmaProcess(np.r_[1, -ar.params[1:]], [1]).impulse_response(H + 1)
    else:
        b = np.r_[1, np.zeros(H)]
    return [{"series": label, "h": h, "arfima": a[h], "ar": b[h], "d": d, "phi": phi[0], "ar_p": p}
            for h in range(H + 1)]

irs += ir_rows("電力需要（東京、日）", tk["resid"].values, 365)
for nm in ["生鮮食品を除く総合", "生鮮食品及びエネルギーを除く総合", "外食", "家賃"]:
    s = mom.loc["2000-01-01":, nm].dropna()
    irs += ir_rows(f"物価：{nm}（月）", clean(s).values, H)
ir = pd.DataFrame(irs)
ir.to_csv(RES / "impulse.csv", index=False)
for k, g in ir.groupby("series", sort=False):
    hs = [7, 30, 90, 365] if "日" in k else [3, 12, 36, 120]
    print(k, "d=%.2f" % g.d.iloc[0], {h: (round(g.set_index("h").loc[h, "arfima"], 3),
                                          round(g.set_index("h").loc[h, "ar"], 3)) for h in hs if h in g.h.values})
