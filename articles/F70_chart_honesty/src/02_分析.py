# 同じデータを見せ方だけ変えたときに、印象（見た目の変化の大きさ）がどれだけ変わるかを数える
import pandas as pd, numpy as np, json, pathlib
R = pathlib.Path(__file__).resolve().parents[1]
ann = pd.read_csv(R/"data/annual.csv", index_col="year")
m = pd.read_csv(R/"data/monthly.csv", parse_dates=["month"])
out = {}

def lie_factor(v0, v1, base):
    """Tufte の lie factor：図で見える変化 ÷ データの変化。base は縦軸の下端"""
    data = (v1 - v0) / v0
    shown = ((v1 - base) - (v0 - base)) / (v0 - base)
    return shown / data, data, shown

# --- 1. 縦軸の切り取り：3系列 × 縦軸の下端4通り
rows = []
cases = {"出生数 2015→2025": ("births", 2015, 2025),
         "就業者 2013→2025": ("employed_sa_10k", 2013, 2025),
         "消費者物価 2020→2025": ("cpi_all", 2020, 2025)}
for name, (col, y0, y1) in cases.items():
    v0, v1 = ann.loc[y0, col], ann.loc[y1, col]
    s = ann.loc[y0:y1, col]; lo, hi = s.min(), s.max(); pad = 0.05 * (hi - lo)
    for bname, base in {"0から": 0, "最小値の半分": lo/2, "最小値の90%": lo*0.9, "最小値−幅の5%（表計算ソフトの自動に近い）": lo - pad}.items():
        lf, d, sh = lie_factor(v0, v1, base)
        rows.append(dict(case=name, axis=bname, base=base, v0=v0, v1=v1, data_change=d, shown_change=sh, lie_factor=lf, height_ratio=(v1-base)/(v0-base)))
r1 = pd.DataFrame(rows); r1.to_csv(R/"results/r1_axis.csv", index=False, float_format="%.4f")
out["axis"] = {c: {a: dict(lie=round(lf,2), height_ratio=round(h,3), data=round(d,4)) for a, lf, h, d in zip(g.axis, g.lie_factor, g.height_ratio, g.data_change)} for c, g in r1.groupby("case")}

# --- 2. 期間の切り取り：実質賃金（12か月平均）の「N年間の変化」を、始まりの月ごとに全部計算
mm = m.dropna(subset=["real_wage_12m"]).set_index("month").real_wage_12m
rows = []
for N in [5, 10, 15, 20]:
    ch = (mm.shift(-12*N) / mm - 1).dropna()
    ch = ch[ch.index >= "1990-01-01"]
    rows.append(dict(N=N, n_start=len(ch), min=ch.min(), p10=ch.quantile(.1), median=ch.median(), p90=ch.quantile(.9), max=ch.max(),
                     share_pos=(ch > 0).mean(), start_min=str(ch.idxmin().date()), start_max=str(ch.idxmax().date())))
    if N == 10: ch.rename("chg10").to_csv(R/"results/r2_window10_series.csv", float_format="%.5f")
r2 = pd.DataFrame(rows); r2.to_csv(R/"results/r2_window.csv", index=False, float_format="%.4f")
out["window"] = r2.round(4).to_dict("records")

# --- 3. 二軸：出生数と消費者物価（2000〜2025年）。水準の相関と、前年からの変化の相関
a = ann.loc[2000:2025]
lev = np.corrcoef(a.births, a.cpi_all)[0, 1]
dif = np.corrcoef(a.births.diff().dropna(), a.cpi_all.diff().dropna())[0, 1]
# 独立なランダムウォーク2本（長さ26）で、水準の |相関| が0.7を超える割合（シミュレーション）
rng = np.random.default_rng(70)
sim = {}
for T in [15, 26, 50]:
    c = []
    for _ in range(5000):
        x = rng.standard_normal(T).cumsum(); y = rng.standard_normal(T).cumsum()
        c.append(abs(np.corrcoef(x, y)[0, 1]))
    c = np.array(c); sim[T] = dict(share_gt07=float((c > .7).mean()), share_gt05=float((c > .5).mean()), median=float(np.median(c)))
out["dual"] = dict(corr_levels=lev, corr_diffs=dif, sim=sim)
pd.DataFrame(sim).T.to_csv(R/"results/r3_randomwalk_sim.csv", float_format="%.4f")

# --- 4. 累積：2000年からの出生数の累計（増え続ける）と、毎年の出生数（減り続ける）
cum = a.births.cumsum()
out["cumulative"] = dict(annual_2000=int(a.births.iloc[0]), annual_2025=int(a.births.iloc[-1]),
                         annual_change=float(a.births.iloc[-1]/a.births.iloc[0]-1), cum_2025=int(cum.iloc[-1]),
                         years_cum_up=int((cum.diff().dropna() > 0).sum()), years_annual_down=int((a.births.diff().dropna() < 0).sum()))
pd.DataFrame(dict(births=a.births, cumulative=cum)).to_csv(R/"results/r4_cumulative.csv")

# --- 5. 割合と実数：合計特殊出生率と出生数（2005→2015年）、失業率と就業者
t = ann.loc[2005:2015]
out["rate_vs_count"] = dict(tfr_2005=float(t.tfr.iloc[0]), tfr_2015=float(t.tfr.iloc[-1]), births_2005=int(t.births.iloc[0]), births_2015=int(t.births.iloc[-1]),
                            tfr_chg=float(t.tfr.iloc[-1]/t.tfr.iloc[0]-1), births_chg=float(t.births.iloc[-1]/t.births.iloc[0]-1),
                            unemp_2019=float(ann.loc[2019,"unemp_rate_sa"]), unemp_2025=float(ann.loc[2025,"unemp_rate_sa"]),
                            emp_2019=float(ann.loc[2019,"employed_sa_10k"]), emp_2025=float(ann.loc[2025,"employed_sa_10k"]))

# --- 6. 面積：出生数2000年と2025年を、棒（長さ）・円（半径を値に比例）・円（面積を値に比例）で描いたときの見た目の比
v0, v1 = a.births.iloc[0], a.births.iloc[-1]; ratio = v1 / v0
shapes = {"棒の長さ": ratio, "円（面積を値に比例）": ratio, "円（半径を値に比例）": ratio**2, "立方体（一辺を値に比例）": ratio**3}
r6 = pd.DataFrame([dict(shape=k, visual_ratio=v, data_ratio=ratio, lie_factor=(v-1)/(ratio-1)) for k, v in shapes.items()])
r6.to_csv(R/"results/r6_area.csv", index=False, float_format="%.4f")
out["area"] = r6.round(3).to_dict("records")

# まとめ（lie factor の一覧）
summ = pd.concat([r1[["case","axis","lie_factor"]].rename(columns={"axis":"how"}),
                  r6.assign(case="出生数 2000→2025").rename(columns={"shape":"how"})[["case","how","lie_factor"]]])
summ.to_csv(R/"results/r7_lie_factor_summary.csv", index=False, float_format="%.3f")
json.dump(out, open(R/"results/summary.json","w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:4000])
