"""推計方法の変更による段差を推定する

A. 労働力調査：ベンチマーク人口の切替え月に、月々の変化がいつもよりどれだけ跳ねたか
B. 毎月勤労統計：①2024年のベンチマーク更新（指数から計算した前年同月比と公表値の差）
                 ②2018年からの部分入替え（公表の前年同月比と共通事業所の前年同月比の差）
C. 接続のしかた：平行移動・比率・三角修正で、切替え年の増減と長期の増減がどう変わるか
"""
import json
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from common import DATA, RAW, RES

warnings.filterwarnings("ignore")
np.random.seed(66)

lfs = pd.read_csv(DATA / "lfs_monthly.csv", index_col=0, parse_dates=True)
lfs["pop15_m"] = lfs["lf_m"] + lfs["nilf_m"]
lfs["pop15_f"] = lfs["lf_f"] + lfs["nilf_f"]
gaps = pd.read_csv(RAW / "official_lfs_gaps.csv")

# 切替え月（2005年10月・2010年10月・2015年10月は、長期時系列表で接続用数値に置き換えられた期間の境目）
SWITCH = ["1982-01", "1987-01", "1992-01", "1997-01", "2002-01", "2007-01", "2012-01", "2017-01", "2022-01"]
BORDER = ["2005-10", "2010-10", "2015-10"]
CAND = SWITCH + BORDER
cand_ts = pd.to_datetime([c + "-01" for c in CAND])
EXCL = (lfs.index.year == 2011)  # 震災の補完推計の年は雑音の推定から外す


def step_baseline(s, lags=(12, 24)):
    """月々の変化 − 同じ月の前後の年の変化の平均（季節と傾向を取り除いた『いつもとの違い』）"""
    d = s.diff()
    base = sum(d.shift(k) + d.shift(-k) for k in lags) / (2 * len(lags))
    return d - base


def step_uc(s, t, half=60):
    """局所線形トレンド＋季節（12か月）＋段差ダミーの状態空間モデルで段差を推定"""
    w = s.loc[t - pd.DateOffset(months=half): t + pd.DateOffset(months=half - 1)].dropna()
    if len(w) < 60:
        return np.nan, np.nan
    x = (w.index >= t).astype(float).reshape(-1, 1) if hasattr(w.index >= t, "reshape") else np.asarray(w.index >= t, float).reshape(-1, 1)
    mod = sm.tsa.UnobservedComponents(w.values, level="local linear trend", freq_seasonal=[{"period": 12, "harmonics": 3}], exog=x)
    r = mod.fit(disp=False, maxiter=200)
    return float(r.params[-1]), float(r.bse[-1])


VARS = {"pop15": "15歳以上人口", "emp": "就業者", "nilf": "非労働力人口", "unemp": "完全失業者",
        "pop15_m": "15歳以上人口（男）", "pop15_f": "15歳以上人口（女）"}
OFF = {"pop15": "pop15", "emp": "employed", "nilf": "nilf", "unemp": "unemployed"}

rows = []
noise = {}
for v in VARS:
    e = step_baseline(lfs[v])
    mask = (~e.index.isin(cand_ts)) & (~EXCL)
    sd = e[mask].std()
    noise[v] = sd
    e1 = step_baseline(lfs[v], lags=(12,))
    e3 = step_baseline(lfs[v], lags=(12, 24, 36))
    for c, t in zip(CAND, cand_ts):
        rec = {"var": v, "name": VARS[v], "month": c, "kind": "切替え" if c in SWITCH else "接続の境目",
               "step": e.get(t, np.nan), "z": e.get(t, np.nan) / sd, "noise_sd": sd,
               "step_lag12": e1.get(t, np.nan), "step_lag123": e3.get(t, np.nan)}
        if v in ("pop15", "emp"):
            rec["step_uc"], rec["step_uc_se"] = step_uc(lfs[v], t)
        g = gaps[gaps["switch"] == c]
        rec["official"] = float(g[OFF[v]].iloc[0]) if (v in OFF and len(g)) else np.nan
        rows.append(rec)
steps = pd.DataFrame(rows)
steps.to_csv(RES / "lfs_steps.csv", index=False, float_format="%.2f")

# 15歳以上人口の「跳ね」の大きい月の順位（全期間・2011年を除く）
e = step_baseline(lfs["pop15"])
rank = e[~EXCL].abs().rank(ascending=False)
top = e[~EXCL].abs().sort_values(ascending=False).head(15)
pd.DataFrame({"month": top.index.strftime("%Y-%m"), "abs_step": top.values,
              "z": top.values / noise["pop15"]}).to_csv(RES / "lfs_pop15_top_jumps.csv", index=False, float_format="%.2f")
cand_rank = {c: int(rank.get(t, np.nan)) for c, t in zip(CAND, cand_ts) if t in rank.index}

# ---- C. 接続のしかた（就業者、切替えが接続されていない 1982〜2002年）----
emp = lfs["emp"].copy()
g5 = gaps.set_index("switch").loc[["1982-01", "1987-01", "1992-01", "1997-01", "2002-01"], "employed"]


def connect(series, gapser, how):
    s = series.copy().astype(float)
    for sw, gap in gapser.items():
        t = pd.Timestamp(sw + "-01")
        before = s.index < t
        if how == "parallel":
            s[before] = s[before] + gap
        elif how == "ratio":
            lvl = series[series.index < t].iloc[-1]
            s[before] = s[before] * (1 + gap / lvl)
        elif how == "triangle":
            start = t - pd.DateOffset(years=5)
            seg = (s.index >= start) & before
            n = seg.sum()
            s[seg] = s[seg] + gap * np.arange(1, n + 1) / (n + 1)
            s[s.index < start] = s[s.index < start] + 0  # 5年より前は動かさない（ここが三角修正の特徴）
    return s


conn = pd.DataFrame({"raw": emp, "parallel": connect(emp, g5, "parallel"),
                     "ratio": connect(emp, g5, "ratio"), "triangle": connect(emp, g5, "triangle")})
ann = conn.groupby(conn.index.year).mean()
ann = ann[(ann.index >= 1973) & (ann.index <= 2025)]
chg = ann.diff()
sw_years = [1982, 1987, 1992, 1997, 2002]
conn_tab = chg.loc[sw_years].round(1)
conn_tab["gap"] = g5.values
long = {k: float(ann.loc[2002, k] - ann.loc[1980, k]) for k in ann}
long2 = {k: float(ann.loc[2025, k] - ann.loc[1980, k]) for k in ann}
conn_tab.to_csv(RES / "connect_switch_years.csv")
ann.to_csv(RES / "emp_annual_by_method.csv", float_format="%.1f")

# 接続済みの切替え（2012・2017・2022年）を「接続しなかったら」：切替え年の年平均の増減に公表のギャップが乗る
c_ann = lfs["emp"].groupby(lfs.index.year).mean().diff()
noconn = []
for sw in ["2012-01", "2017-01", "2022-01"]:
    y = int(sw[:4]); gap = float(gaps.set_index("switch").loc[sw, "employed"])
    noconn.append({"year": y, "connected_change": round(float(c_ann.loc[y]), 1), "gap": gap,
                   "if_not_connected": round(float(c_ann.loc[y]) + gap, 1)})
pd.DataFrame(noconn).to_csv(RES / "connected_counterfactual.csv", index=False)

# ---- B. 毎月勤労統計 ----
mk = pd.read_csv(DATA / "maikin_monthly.csv", index_col=0, parse_dates=True)
ITEMS = {"cash_total": "現金給与総額", "scheduled": "きまって支給する給与", "scheduled_base": "所定内給与"}
x = mk["2018":]
bench, kyo = [], []
for k, nm in ITEMS.items():
    di = (x[f"pub_{k}"] - x[f"idxyoy_{k}"])
    dk = (x[f"pub_{k}"] - x[f"kyo_{k}"])
    for y, g in x.groupby(x.index.year):
        bench.append({"item": nm, "year": y, "pub": g[f"pub_{k}"].mean(), "idx_yoy": g[f"idxyoy_{k}"].mean(),
                      "pub_minus_idx": di[g.index].mean(), "max_abs": di[g.index].abs().max()})
        kyo.append({"item": nm, "year": y, "pub": g[f"pub_{k}"].mean(), "kyotsu": g[f"kyo_{k}"].mean(),
                    "pub_minus_kyotsu": dk[g.index].mean(),
                    "pub_gt_kyo_months": int((dk[g.index] > 0).sum()), "months": int(dk[g.index].notna().sum())})
bench = pd.DataFrame(bench); kyo = pd.DataFrame(kyo)
bench.to_csv(RES / "maikin_bench2024.csv", index=False, float_format="%.2f")
kyo.to_csv(RES / "maikin_vs_kyotsu.csv", index=False, float_format="%.2f")

# 期間全体の比較（2018年1月〜2026年8月）とコロナ期を除く場合
summ = {}
for k, nm in ITEMS.items():
    dk = (x[f"pub_{k}"] - x[f"kyo_{k}"]).dropna()
    nocovid = dk[~((dk.index >= "2020-04-01") & (dk.index <= "2021-12-01"))]
    cum_pub = float(x[f"idx_{k}"].dropna().iloc[-1] / x[f"idx_{k}"].dropna().loc["2017-12-01":].iloc[0])
    summ[nm] = {"mean_diff": float(dk.mean()), "mean_abs_diff": float(dk.abs().mean()),
                "sd_diff": float(dk.std()), "corr": float(np.corrcoef(x[f"pub_{k}"].loc[dk.index], x[f"kyo_{k}"].loc[dk.index])[0, 1]),
                "mean_diff_no_covid": float(nocovid.mean()),
                "jan_mean_diff": float(dk[dk.index.month == 1].mean()), "other_mean_diff": float(dk[dk.index.month != 1].mean())}

# 2009年・2012年の抽出替え（厚労省資料の数値）
old = pd.read_csv(RAW / "mhlw_gap_2009_2012.csv")
old["sample_effect_pct"] = (old["new_sample_old_bench_yen"] / old["old_sample_old_bench_yen"] - 1) * 100
old["bench_effect_pct"] = (old["new_sample_new_bench_yen"] / old["new_sample_old_bench_yen"] - 1) * 100
old["total_pct"] = (old["new_sample_new_bench_yen"] / old["old_sample_old_bench_yen"] - 1) * 100
old.to_csv(RES / "maikin_old_gaps.csv", index=False, float_format="%.3f")

out = {"lfs_noise_sd": {VARS[k]: round(v, 2) for k, v in noise.items()},
       "pop15_switch_rank_among_months": cand_rank,
       "emp_change_1980_2002": {k: round(v, 1) for k, v in long.items()},
       "emp_change_1980_2025": {k: round(v, 1) for k, v in long2.items()},
       "maikin_pub_vs_kyotsu": {k: {a: round(b, 3) for a, b in v.items()} for k, v in summ.items()},
       "maikin_old_gaps": old.round(3).to_dict(orient="records")}
(RES / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
print(steps[steps["var"].isin(["pop15", "emp"])][["name", "month", "step", "z", "official", "step_lag12", "step_lag123", "step_uc", "step_uc_se"]].round(1).to_string())
print(conn_tab); print(pd.DataFrame(noconn))
print(bench[bench.year.isin([2023, 2024, 2025])].round(2).to_string())
print(kyo.pivot(index="year", columns="item", values="pub_minus_kyotsu").round(2))
