"""季節つき中断時系列：コロナ前の傾向と季節から「コロナがなければ」の旅客数を作り、実際との比（回復率）を見る。"""
import json, pathlib
import numpy as np, pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results"; OUT.mkdir(exist_ok=True)
np.random.seed(0)
d = pd.read_csv(ROOT / "data/rail_monthly_t22.csv", parse_dates=["date"])

# 2018年4月に大阪市営地下鉄が民営化され「公営」から「中小民鉄」へ移ったため、中小と公営はまとめる
w = {}
for col in ["teiki", "teikigai", "total"]:
    p = d.pivot(index="date", columns="unit", values=col)
    p["中小・公営"] = p["中小民鉄"] + p["公営"]
    p["JR在来線"] = p["JR"] - p["新幹線"]
    w[col] = p
SERIES = {"全国（計）": ("total", "全国"), "全国（定期）": ("teiki", "全国"), "全国（定期外）": ("teikigai", "全国"),
          "JR在来線": ("total", "JR在来線"), "新幹線": ("total", "新幹線"), "大手民鉄": ("total", "大手民鉄"), "中小・公営": ("total", "中小・公営")}
REG = ["北海道", "東北", "関東", "北陸信越", "中部", "近畿", "中国", "四国", "九州", "沖縄"]
for r in REG:
    SERIES[r] = ("total", r)
for r in REG:
    SERIES[r + "（定期）"] = ("teiki", r); SERIES[r + "（定期外）"] = ("teikigai", r)
for s in ["JR在来線", "新幹線", "大手民鉄", "中小・公営"]:
    SERIES[s + "（定期）"] = ("teiki", s); SERIES[s + "（定期外）"] = ("teikigai", s)

dates = w["total"].index
days = dates.days_in_month.values
POST0 = pd.Timestamp("2020-02-01")

def fit(y, start="2015-01-01", end="2020-01-01", trend=True, perday=True):
    """y: Series（千人/月）。戻り値：実績、反実仮想、予測区間（95%）"""
    yy = y / days if perday else y.copy()
    ly = np.log(yy)
    t = np.arange(len(y)) / 12.0
    X = pd.get_dummies(dates.month, prefix="m", drop_first=True).astype(float)
    X.index = dates
    if trend:
        X["t"] = t
    X = sm.add_constant(X)
    pre = (dates >= start) & (dates <= end)
    m = sm.OLS(ly[pre], X[pre]).fit()
    pr = m.get_prediction(X).summary_frame(alpha=0.05)
    cf = np.exp(pr["mean"].values + m.mse_resid / 2)
    lo = np.exp(pr["obs_ci_lower"].values); hi = np.exp(pr["obs_ci_upper"].values)
    mult = days if perday else 1
    return pd.DataFrame({"actual": y.values, "cf": cf * mult, "lo": lo * mult, "hi": hi * mult}, index=dates), m

res = {}
paths = {}
LAST12 = (dates > dates[-1] - pd.DateOffset(months=12))
for name, (col, unit) in SERIES.items():
    y = w[col][unit]
    f, m = fit(y)
    f["rec"] = f["actual"] / f["cf"]
    paths[name] = f
    post = f[f.index >= POST0]
    first90 = post.index[(post["rec"] >= 0.90)]
    # 2020年4月以降で、回復率が初めて0.9／0.95以上になった月（その後連続していなくてもよい）
    p2 = f[f.index >= "2020-04-01"]
    def first(th):
        x = p2.index[p2["rec"] >= th]
        return x[0].strftime("%Y-%m") if len(x) else None
    last = f[LAST12]
    rec12 = last["actual"].sum() / last["cf"].sum()
    rec12_lo = last["actual"].sum() / last["hi"].sum(); rec12_hi = last["actual"].sum() / last["lo"].sum()
    # 直近24か月の回復率の傾き（年あたり、ポイント）
    l24 = f[f.index > dates[-1] - pd.DateOffset(months=24)]
    tt = np.arange(len(l24)) / 12
    Xs = sm.add_constant(np.c_[tt, pd.get_dummies(l24.index.month, drop_first=True).astype(float).values])
    sl = sm.OLS(l24["rec"].values * 100, Xs).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    # 2019年の同じ月との比（傾向なしの単純比較）
    y19 = f[f.index.year == 2019]["actual"]; y19.index = y19.index.month
    vs19 = last["actual"].sum() / sum(y19[mm] for mm in last.index.month)
    # 2020年4月の落ち込み
    res[name] = dict(series=name, col=col, unit=unit, rec_2020_04=round(f.loc["2020-04-01", "rec"], 3),
                     rec_last12=round(rec12, 3), rec_last12_lo=round(rec12_lo, 3), rec_last12_hi=round(rec12_hi, 3),
                     vs2019_last12=round(vs19, 3), first_090=first(0.90), first_095=first(0.95),
                     slope24_pt_per_yr=round(sl.params[1], 2), slope24_se=round(sl.bse[1], 2),
                     pre_trend_pct_per_yr=round((np.exp(m.params["t"]) - 1) * 100, 2), pre_r2=round(m.rsquared, 3))
R = pd.DataFrame(res.values())
R.to_csv(OUT / "recovery_summary.csv", index=False, encoding="utf-8")
pd.concat({k: v for k, v in paths.items()}, names=["series", "date"]).reset_index().to_csv(OUT / "recovery_paths.csv", index=False, encoding="utf-8")

# 直近12か月の不足（反実仮想 − 実績）を定期と定期外に分ける
l = {k: paths[k][LAST12] for k in ["全国（計）", "全国（定期）", "全国（定期外）"]}
gap_t = (l["全国（定期）"]["cf"] - l["全国（定期）"]["actual"]).sum(); gap_g = (l["全国（定期外）"]["cf"] - l["全国（定期外）"]["actual"]).sum()
share = dict(gap_teiki_thousand=round(gap_t), gap_teikigai_thousand=round(gap_g), teiki_share=round(gap_t / (gap_t + gap_g), 3),
             teiki_share_of_cf=round(l["全国（定期）"]["cf"].sum() / (l["全国（定期）"]["cf"].sum() + l["全国（定期外）"]["cf"].sum()), 3))
# 業態別の不足の内訳
seg = {}
for s in ["JR在来線", "新幹線", "大手民鉄", "中小・公営"]:
    x = paths[s][LAST12]; seg[s] = (x["cf"] - x["actual"]).sum()
share["gap_by_segment_share"] = {k: round(v / sum(seg.values()), 3) for k, v in seg.items()}
reg = {}
for r in REG:
    x = paths[r][LAST12]; reg[r] = (x["cf"] - x["actual"]).sum()
share["gap_kanto_kinki_share"] = round((reg["関東"] + reg["近畿"]) / sum(reg.values()), 3)
share["kanto_kinki_share_of_cf"] = round(sum(paths[r][LAST12]["cf"].sum() for r in ["関東", "近畿"]) / sum(paths[r][LAST12]["cf"].sum() for r in REG), 3)

# 頑健性：基準期間・傾向の有無・1日あたりかどうか・中断の始まり
rob = []
VAR = {"主（2015-01〜2020-01, 傾向あり, 1日あたり）": dict(),
       "基準 2017-04〜2020-01（傾向あり）": dict(start="2017-04-01"),
       "基準 2015-01〜2019-12（2020年1月を除く）": dict(end="2019-12-01"),
       "基準 2015-01〜2020-01（傾向なし＝平均）": dict(trend=False),
       "基準 2018-04〜2019-12（傾向なし）": dict(start="2018-04-01", end="2019-12-01", trend=False),
       "基準 2014-01〜2020-01（傾向あり）": dict(start="2014-01-01"),
       "1日あたりにしない": dict(perday=False)}
for vname, kw in VAR.items():
    for name in ["全国（計）", "全国（定期）", "全国（定期外）", "JR在来線", "新幹線", "大手民鉄", "中小・公営", "関東", "近畿"]:
        col, unit = SERIES[name]
        f, m = fit(w[col][unit], **kw)
        last = f[LAST12]
        rob.append(dict(variant=vname, series=name, rec_last12=round(last["actual"].sum() / last["cf"].sum(), 3)))
rob = pd.DataFrame(rob)
rob.pivot(index="series", columns="variant", values="rec_last12").to_csv(OUT / "robustness.csv", encoding="utf-8")

# 前の傾向の当てはまり：2019年を除いて当てはめ、2019年を予測した誤差（検証）
val = {}
for name in ["全国（計）", "全国（定期）", "全国（定期外）", "新幹線"]:
    col, unit = SERIES[name]
    f, _ = fit(w[col][unit], start="2015-01-01", end="2018-12-01")
    v = f[(f.index >= "2019-01-01") & (f.index <= "2019-12-01")]
    val[name] = dict(mape=round(float((v["actual"] / v["cf"] - 1).abs().mean() * 100), 2),
                     bias=round(float((v["actual"].sum() / v["cf"].sum() - 1) * 100), 2))
json.dump(dict(gap=share, validation_2019=val, last_month=dates[-1].strftime("%Y-%m"),
               last12=f"{dates[LAST12][0].strftime('%Y-%m')}〜{dates[-1].strftime('%Y-%m')}"),
          open(OUT / "gap_and_validation.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
print(R[["series", "rec_2020_04", "rec_last12", "rec_last12_lo", "rec_last12_hi", "vs2019_last12", "first_090", "first_095", "slope24_pt_per_yr", "slope24_se", "pre_trend_pct_per_yr"]].to_string())
print(json.dumps(share, ensure_ascii=False)); print(val)
print(rob.pivot(index="series", columns="variant", values="rec_last12").to_string())
