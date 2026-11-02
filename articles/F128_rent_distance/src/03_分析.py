"""03 分析：家賃は都心・駅からの距離でどれだけ下がるか"""
import json
import numpy as np
import pandas as pd
from pygam import LinearGAM, s, f, l
from sklearn.model_selection import KFold
from common import DATA, RES, SEED, RADIUS

RES.mkdir(exist_ok=True)
np.random.seed(SEED)
out = {}
log = []


def P(*a):
    t = " ".join(str(x) for x in a)
    print(t)
    log.append(t)


# ============ 1) 距離帯の表：民営借家の1畳当たり家賃 ============
band = pd.read_csv(DATA / "band_rent_by_age.csv")
bb = band[band.band_lo.notna()].copy()
bb["mid"] = (bb.band_lo + bb.band_hi) / 2
tot = bb[bb.age == "00_総数"]
curve = tot.pivot_table(index=["metro", "mid"], columns="year", values="private").reset_index()
curve.to_csv(RES / "band_curve_private.csv", index=False)
P("== 距離帯ごとの民営借家の1畳当たり家賃（円）")
P(curve.to_string(index=False))

rows = []
for (m, y), g in tot.groupby(["metro", "year"]):
    g = g.sort_values("mid")
    v0 = g.private.iloc[0]
    for _, r in g.iterrows():
        rows.append(dict(metro=m, year=y, mid=r.mid, private=r.private, rel=r.private / v0,
                         wood_rel=r.wood / g.wood.iloc[0], nonwood_rel=r.nonwood / g.nonwood.iloc[0]))
    # 対数の傾き（10km あたり）
    b = np.polyfit(g.mid, np.log(g.private), 1)[0] * 10
    out[f"band_slope_{m}_{y}"] = b
rel = pd.DataFrame(rows)
rel.to_csv(RES / "band_relative.csv", index=False)
P("== 0〜10km を1としたときの比（民営借家）")
P(rel.pivot_table(index=["metro", "mid"], columns="year", values="rel").round(3).to_string())

# 建築の時期をそろえた比較：時期ごとに 0〜10km との対数差をとり、時期で平均する
adj = []
ages = [a for a in bb.age.unique() if a not in ("00_総数",) and "不詳" not in a]
for (m, y), g in bb.groupby(["metro", "year"]):
    for mid, gg in g.groupby("mid"):
        diffs = []
        for a in ages:
            base = g[(g.age == a) & (g.mid == g.mid.min())].private
            cur = gg[gg.age == a].private
            if len(base) and len(cur) and base.iloc[0] > 0 and cur.iloc[0] > 0:
                diffs.append(np.log(cur.iloc[0]) - np.log(base.iloc[0]))
        adj.append(dict(metro=m, year=y, mid=mid, rel_raw=float(np.exp(np.log(gg[gg.age == "00_総数"].private.iloc[0]) - np.log(g[(g.age == "00_総数") & (g.mid == g.mid.min())].private.iloc[0]))),
                        rel_age_adj=float(np.exp(np.mean(diffs))), n_age=len(diffs)))
adj = pd.DataFrame(adj)
adj.to_csv(RES / "band_age_adjusted.csv", index=False)
P("== 建築の時期をそろえた比（0〜10km=1）")
P(adj.round(3).to_string(index=False))

# ============ 2) 市区町村：延べ面積1m2当たり家賃（民営借家）と都心からの距離 ============
df = pd.read_csv(DATA / "muni_analysis.csv", dtype={"code": str, "pref": str})
df["rad"] = df.metro3.map(RADIUS)
M = df[(df.dist3 <= df.rad) & df.rent_m2_2023.notna()].copy()
M["y"] = np.log(M.rent_m2_2023)
M["mcode"] = M.metro3.map({"東京": 0, "名古屋": 1, "大阪": 2})
P("== 3大都市圏の圏内の市区町村数", len(M), M.metro3.value_counts().to_dict())


grid = np.arange(1, 71, 1.0)


def cv_rmse(make, X, y, k=5):
    kf = KFold(k, shuffle=True, random_state=SEED)
    e = []
    for tr, te in kf.split(X):
        m = make().fit(X[tr], y[tr])
        e.append(np.sqrt(np.mean((m.predict(X[te]) - y[te]) ** 2)))
    return float(np.mean(e))


pred = []
for nm in ["東京", "名古屋", "大阪"]:
    g = M[M.metro3 == nm]
    Xg, yg = g[["dist3"]].values, g.y.values
    gm = LinearGAM(s(0, n_splines=10)).gridsearch(Xg, yg, progress=False)
    lam = gm.lam[0][0]
    out[f"cv_gam_{nm}"] = cv_rmse(lambda: LinearGAM(s(0, n_splines=10, lam=lam)), Xg, yg)
    out[f"cv_lin_{nm}"] = cv_rmse(lambda: LinearGAM(l(0), lam=0.0001), Xg, yg)
    out[f"edf_{nm}"] = float(gm.statistics_["edof"])
    gg = grid[(grid <= RADIUS[nm]) & (grid >= np.floor(g.dist3.min()))]
    p = gm.predict(gg[:, None])
    ci = gm.confidence_intervals(gg[:, None], width=0.95)
    for d, pp, (lo, hi) in zip(gg, p, ci):
        pred.append(dict(metro=nm, dist=d, rent=np.exp(pp), lo=np.exp(lo), hi=np.exp(hi)))
    P(nm, "CV RMSE GAM", round(out[f"cv_gam_{nm}"], 4), "直線", round(out[f"cv_lin_{nm}"], 4), "edf", round(out[f"edf_{nm}"], 1))
pred = pd.DataFrame(pred)
pred.to_csv(RES / "gam_curve_2023.csv", index=False)
for nm in ["東京", "名古屋", "大阪"]:
    g = pred[pred.metro == nm].set_index("dist").rent
    base = g.loc[5.0]
    out[f"gam_{nm}_5km_rent"] = float(base)
    for d in [10, 20, 30, 40, 50, 60, 70]:
        if float(d) in g.index:
            out[f"gam_{nm}_{d}km_vs5"] = float(g.loc[float(d)] / base)
    P(nm, "5km の家賃", round(base), "円/m2 →", {d: round(g.loc[float(d)] / base, 3) for d in [10, 20, 30, 40, 50, 60, 70] if float(d) in g.index})

# 傾きの変わり目：区分線形（折れ点を 5〜40km で探す）
brk = []
for nm in ["東京", "名古屋", "大阪"]:
    g = M[M.metro3 == nm]
    best = None
    for k in np.arange(5, 41, 1.0):
        Z = np.c_[np.ones(len(g)), g.dist3, np.clip(g.dist3 - k, 0, None)]
        b, res, *_ = np.linalg.lstsq(Z, g.y, rcond=None)
        sse = float(np.sum((Z @ b - g.y) ** 2))
        if best is None or sse < best[1]:
            best = (k, sse, b)
    k, _, b = best
    brk.append(dict(metro=nm, knot=k, slope_in_per10=b[1] * 10, slope_out_per10=(b[1] + b[2]) * 10))
brk = pd.DataFrame(brk)
brk.to_csv(RES / "piecewise.csv", index=False)
P("== 区分線形（対数家賃、10km あたり）")
P(brk.round(3).to_string(index=False))

# ============ 3) 駅からの距離と都心からの距離を一緒に入れる ============
import statsmodels.formula.api as smf
Ms = M.dropna(subset=["share_st1000", "income", "density", "aged"]).copy()
Ms["d10"] = Ms.dist3 / 10
Ms["st10"] = Ms.share_st1000 * 10  # 10ポイントあたり
r0 = smf.ols("y ~ d10 + C(metro3)", Ms).fit(cov_type="HC1")
r1 = smf.ols("y ~ d10 + st10 + C(metro3)", Ms).fit(cov_type="HC1")
r2 = smf.ols("y ~ d10 + st10 + income + density + aged + C(metro3)", Ms).fit(cov_type="HC1")
r3 = smf.ols("y ~ st10 + C(metro3)", Ms).fit(cov_type="HC1")
reg = []
for nm, r in [("距離だけ", r0), ("距離＋駅1km以内の割合", r1), ("＋所得・人口密度・高齢化", r2), ("駅だけ", r3)]:
    reg.append(dict(model=nm, n=int(r.nobs), r2=r.rsquared,
                    b_dist10=r.params.get("d10", np.nan), se_dist10=r.bse.get("d10", np.nan),
                    b_st10=r.params.get("st10", np.nan), se_st10=r.bse.get("st10", np.nan)))
reg = pd.DataFrame(reg)
reg.to_csv(RES / "regression_station.csv", index=False)
P("== 回帰（対数家賃。距離は10km、駅は1km以内の世帯割合10ポイントあたり）")
P(reg.round(4).to_string(index=False))
out["n_station_models"] = int(r0.nobs)
out["dist_shrink_with_station"] = float(1 - r1.params["d10"] / r0.params["d10"])
out["dist_shrink_with_all"] = float(1 - r2.params["d10"] / r0.params["d10"])
out["corr_dist_station"] = float(np.corrcoef(Ms.dist3, Ms.share_st1000)[0, 1])

# GAM で2つを一緒に（部分依存）
X2 = Ms[["dist3", "share_st1000", "mcode"]].values
gam2 = LinearGAM(s(0, n_splines=10) + s(1, n_splines=8) + f(2)).gridsearch(X2, Ms.y.values, progress=False)
pdp = []
for term, grid_ in [(0, np.linspace(2, 70, 69)), (1, np.linspace(0.05, 0.95, 46))]:
    XX = gam2.generate_X_grid(term=term, n=len(grid_))
    XX[:, term] = grid_
    pd_, ci = gam2.partial_dependence(term=term, X=XX, width=0.95)
    for g_, v, (lo, hi) in zip(grid_, pd_, ci):
        pdp.append(dict(term=["dist", "station"][term], x=g_, eff=v, lo=lo, hi=hi))
pd.DataFrame(pdp).to_csv(RES / "gam2_partial.csv", index=False)
out["gam2_r2"] = float(gam2.statistics_["pseudo_r2"]["explained_deviance"])

# ============ 4) 頑健性 ============
rob = []


def slope_ols(d, ycol, dcol="dist3"):
    d = d.dropna(subset=[ycol])
    r = smf.ols(f"np.log({ycol}) ~ I({dcol}/10) + C(metro3)", d).fit(cov_type="HC1")
    return r.params.iloc[-1], r.bse.iloc[-1], int(r.nobs)


def add(name, d, ycol, dcol="dist3"):
    b, se, n = slope_ols(d, ycol, dcol)
    rob.append(dict(check=name, n=n, slope10=b, se=se, pct_per10=np.expm1(b) * 100))


base_set = df[(df.dist3 <= df.rad)].copy()
add("基本（2023年・民営借家・家賃0円を除く）", base_set, "rent_m2_2023")
add("年：2018年", base_set, "rent_m2_2018")
add("家賃0円を含む", base_set, "rent_m2_incl0_2023")
add("借家の総数（公営・給与住宅を含む）", base_set, "rent_m2_all_2023")
add("東京23区を除く", base_set[~base_set.code.str.startswith("131")], "rent_m2_2023")
add("圏の半径を一律40km", df[df.dist3 <= 40], "rent_m2_2023")
for nm in ["東京", "名古屋", "大阪"]:
    g = base_set[base_set.metro3 == nm].dropna(subset=["rent_m2_2023"])
    r = smf.ols("np.log(rent_m2_2023) ~ I(dist3/10)", g).fit(cov_type="HC1")
    rob.append(dict(check=f"都市圏別：{nm}", n=int(r.nobs), slope10=r.params.iloc[1], se=r.bse.iloc[1], pct_per10=np.expm1(r.params.iloc[1]) * 100))
# 距離の定義：全国・16の中心のうち最も近い中心（地方都市圏を含む、半径50km）
W = df[(df.distW <= 50) & df.rent_m2_2023.notna()].copy()
r = smf.ols("np.log(rent_m2_2023) ~ I(distW/10) + C(metroW)", W).fit(cov_type="HC1")
rob.append(dict(check="中心を16都市に広げる（半径50km）", n=int(r.nobs), slope10=r.params.iloc[-1], se=r.bse.iloc[-1], pct_per10=np.expm1(r.params.iloc[-1]) * 100))
W2 = W[~W.metroW.isin(["東京", "名古屋", "大阪"])]
r = smf.ols("np.log(rent_m2_2023) ~ I(distW/10) + C(metroW)", W2).fit(cov_type="HC1")
rob.append(dict(check="地方の13都市圏だけ（半径50km）", n=int(r.nobs), slope10=r.params.iloc[-1], se=r.bse.iloc[-1], pct_per10=np.expm1(r.params.iloc[-1]) * 100))
# 距離帯の表（市区町村ではなく、調査の集計そのもの）
for y in [2023, 2018]:
    g = tot[tot.year == y]
    r = smf.ols("np.log(private) ~ I(mid/10) + C(metro)", g).fit()
    rob.append(dict(check=f"距離帯の表（{y}年、1畳当たり）", n=int(r.nobs), slope10=r.params.iloc[-1], se=r.bse.iloc[-1], pct_per10=np.expm1(r.params.iloc[-1]) * 100))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
P("== 頑健性（対数家賃の 10km あたりの傾き、都市圏の固定効果つき）")
P(rob.round(4).to_string(index=False))

# 2018→2023 の変化：都心に近いほど上がったか
ch = base_set.dropna(subset=["rent_m2_2023", "rent_m2_2018"]).copy()
ch["g"] = np.log(ch.rent_m2_2023 / ch.rent_m2_2018)
r = smf.ols("g ~ I(dist3/10) + C(metro3)", ch).fit(cov_type="HC1")
out["growth_slope10"] = float(r.params.iloc[-1])
out["growth_slope10_se"] = float(r.bse.iloc[-1])
out["growth_median"] = float(np.expm1(ch.g.median()))
bins = pd.cut(ch.dist3, [0, 10, 20, 30, 50, 70])
gt = ch.groupby([bins, "metro3"], observed=True).g.median().unstack().apply(np.expm1)
gt.to_csv(RES / "growth_2018_2023_by_band.csv")
P("== 2018→2023 の家賃の伸び（中央値）")
P(gt.round(3).to_string())
P("伸びの傾き（10km あたり）", round(out["growth_slope10"], 4), "se", round(out["growth_slope10_se"], 4))

out["n_muni_metro"] = int(len(M))
out["rent_med_0_10_tokyo"] = float(M[(M.metro3 == "東京") & (M.dist3 <= 10)].rent_m2_2023.median())
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
open(RES / "log_03.txt", "w").write("\n".join(log))
P(json.dumps(out, ensure_ascii=False, indent=1, default=float))
