"""集中度の指標（東京の割合・三大都市圏の割合・HHI・ジニ係数）と、その時系列の傾き。
特化係数（立地係数）と、4つの権利を合わせた「地方の割合」の要因分解（シフトシェア）も出す。
入力: data/pref_ip_long.csv  出力: results/*.csv, results/summary.json
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
np.random.seed(141)

METRO = ["埼玉県","千葉県","東京都","神奈川県","岐阜県","愛知県","三重県","京都府","大阪府","兵庫県","奈良県"]
BLOCK = {"北海道":"北海道","青森県":"東北","岩手県":"東北","宮城県":"東北","秋田県":"東北","山形県":"東北","福島県":"東北",
 "茨城県":"関東","栃木県":"関東","群馬県":"関東","埼玉県":"関東","千葉県":"関東","東京都":"東京都","神奈川県":"関東",
 "新潟県":"中部","富山県":"中部","石川県":"中部","福井県":"中部","山梨県":"中部","長野県":"中部","岐阜県":"中部","静岡県":"中部","愛知県":"中部",
 "三重県":"近畿","滋賀県":"近畿","京都府":"近畿","大阪府":"近畿","兵庫県":"近畿","奈良県":"近畿","和歌山県":"近畿",
 "鳥取県":"中国","島根県":"中国","岡山県":"中国","広島県":"中国","山口県":"中国",
 "徳島県":"四国","香川県":"四国","愛媛県":"四国","高知県":"四国",
 "福岡県":"九州・沖縄","佐賀県":"九州・沖縄","長崎県":"九州・沖縄","熊本県":"九州・沖縄","大分県":"九州・沖縄","宮崎県":"九州・沖縄","鹿児島県":"九州・沖縄","沖縄県":"九州・沖縄"}
APPS = ["特許出願", "実用新案出願", "意匠出願", "商標出願"]
ALL = APPS + ["特許登録", "特許の発明者数"]

d = pd.read_csv(ROOT / "data/pref_ip_long.csv")
W = d.pivot_table(index=["series", "year"], columns="pref", values="count")

def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return (2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())

def metrics(row, top5=None):
    s = row / row.sum()
    ex = row.drop("東京都"); se = ex / ex.sum()
    out = {
        "東京の割合": s["東京都"],
        "三大都市圏の割合": s[METRO].sum(),
        "地方の割合": 1 - s[METRO].sum(),
        "HHI": (s ** 2).sum(),
        "HHI_東京を除く": (se ** 2).sum(),
        "ジニ係数": gini(row.values),
    }
    if top5 is not None:
        out["上位5都府県以外の割合"] = 1 - s[top5].sum()
    return out

top5 = W.loc["特許出願"].loc[2007:2009].sum().sort_values(ascending=False).index[:5].tolist()
M = pd.DataFrame({k: metrics(W.loc[k], top5) for k in W.index}).T
M.index.names = ["series", "year"]
M.to_csv(RES / "concentration_by_series_year.csv", float_format="%.5f")

def trend(y, years, drop=()):
    m = ~np.isin(years, list(drop))
    X = sm.add_constant(years[m] - 2007.0)
    f = sm.OLS(y[m], X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    b, (lo, hi) = f.params[1], f.conf_int()[1]
    return b * 10, lo * 10, hi * 10  # 10年あたり

def window_change(series, metric, a=(2007, 2009), b=(2022, 2024)):
    x = M.loc[series][metric]
    return x.loc[b[0]:b[1]].mean() - x.loc[a[0]:a[1]].mean()

rows = []
for s in ALL:
    years = M.loc[s].index.values.astype(float)
    for met in ["東京の割合", "地方の割合", "HHI", "HHI_東京を除く", "ジニ係数", "上位5都府県以外の割合"]:
        y = M.loc[s][met].values
        b, lo, hi = trend(y, years)
        b2, lo2, hi2 = trend(y, years, drop=(2020, 2021))
        rows.append(dict(series=s, metric=met, v2007_09=M.loc[s][met].loc[2007:2009].mean(),
                         v2022_24=M.loc[s][met].loc[2022:2024].mean(), diff=window_change(s, met),
                         diff_single=M.loc[s][met].loc[2024] - M.loc[s][met].loc[2007],
                         slope10=b, lo=lo, hi=hi, slope10_ex2020_21=b2, lo_ex=lo2, hi_ex=hi2))
T = pd.DataFrame(rows); T.to_csv(RES / "trend_table.csv", index=False, float_format="%.5f")

# 版の切れ目（2009→2010, 2012→2013, 2015→2016, 2018→2019, 2021→2022）の段差を、ほかの年の変化と比べる
br = []
for s in ALL:
    x = M.loc[s]["東京の割合"]; dif = x.diff().dropna()
    cut = dif.loc[[2010, 2013, 2016, 2019, 2022]]
    br.append(dict(series=s, mean_abs_cut=cut.abs().mean(), mean_abs_other=dif.drop(cut.index).abs().mean()))
pd.DataFrame(br).to_csv(RES / "edition_break_check.csv", index=False, float_format="%.5f")

# 地方ブロック別の割合（特許出願・商標出願・発明者数）
P = d[d.series.isin(ALL)].copy(); P["block"] = P.pref.map(BLOCK)
B = P.groupby(["series", "year", "block"])["count"].sum()
B = (B / B.groupby(level=[0, 1]).transform("sum")).unstack("block")
B.to_csv(RES / "block_share.csv", float_format="%.5f")
blk = []
for s in ALL:
    a = B.loc[s].loc[2007:2009].mean(); b = B.loc[s].loc[2022:2024].mean()
    for k in B.columns:
        blk.append(dict(series=s, block=k, s2007_09=a[k], s2022_24=b[k], diff_pt=(b[k] - a[k]) * 100))
pd.DataFrame(blk).to_csv(RES / "block_change.csv", index=False, float_format="%.4f")

# 特化係数（4つの権利の出願の合計を基準にした立地係数）
A = W.loc[APPS]
def lq(years):
    x = A.loc[(slice(None), list(years)), :].groupby(level=0).sum()
    tot_p = x.sum(0); tot_r = x.sum(1); T_ = x.values.sum()
    return (x.div(tot_r, axis=0)).div(tot_p / T_, axis=1)
LQa, LQb = lq(range(2007, 2010)), lq(range(2022, 2025))
lqt = pd.concat({"2007_09": LQa, "2022_24": LQb}).T
lqt.to_csv(RES / "location_quotient.csv", float_format="%.4f")
lq_sum = {}
for r in APPS:
    nm = [p for p in LQa.columns if p not in METRO]
    lq_sum[r] = dict(
        地方で特化係数1超の県数_2007_09=int((LQa.loc[r, nm] > 1).sum()),
        地方で特化係数1超の県数_2022_24=int((LQb.loc[r, nm] > 1).sum()),
        東京の特化係数_2007_09=float(LQa.loc[r, "東京都"]), 東京の特化係数_2022_24=float(LQb.loc[r, "東京都"]))

# 4つの権利を合わせた地方の割合の要因分解（権利ごとの地方割合の変化 vs 権利の構成の変化）
def comp(years):
    x = A.loc[(slice(None), list(years)), :].groupby(level=0).sum()
    w = x.sum(1) / x.values.sum()
    s = 1 - x[METRO].sum(1) / x.sum(1)
    return w, s
w0, s0 = comp(range(2007, 2010)); w1, s1 = comp(range(2022, 2025))
dS = (w1 * s1).sum() - (w0 * s0).sum()
within = (((w0 + w1) / 2) * (s1 - s0)).sum()
mix = (((s0 + s1) / 2) * (w1 - w0)).sum()
decomp = dict(地方の割合_合計_2007_09=float((w0 * s0).sum()), 地方の割合_合計_2022_24=float((w1 * s1).sum()),
              変化=float(dS), 権利ごとの変化=float(within), 構成の変化=float(mix),
              構成_2007_09={k: float(v) for k, v in w0.items()}, 構成_2022_24={k: float(v) for k, v in w1.items()},
              権利ごとの地方割合_2007_09={k: float(v) for k, v in s0.items()}, 権利ごとの地方割合_2022_24={k: float(v) for k, v in s1.items()})

summary = dict(top5=top5, lq=lq_sum, decomp=decomp,
               totals={s: {int(y): int(W.loc[s].loc[y].sum()) for y in (2007, 2024)} for s in ALL})
(RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(T[T.metric.isin(["東京の割合", "地方の割合", "HHI_東京を除く"])].round(4).to_string())
print(pd.read_csv(RES / "edition_break_check.csv").round(4))
print(json.dumps(summary, ensure_ascii=False, indent=1)[:3000])
