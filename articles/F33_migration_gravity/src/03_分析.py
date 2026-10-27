"""重力モデル（PPML と対数の最小二乗法）で、距離の効き方とその推移を推定する。"""
import json, warnings
import numpy as np
import pandas as pd
import pyfixest as pf
from common import DATA, RES

warnings.filterwarnings("ignore")
RES.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(DATA / "panel.csv")
df["ldist"] = np.log(df["dist"])
df["ldist_pref"] = np.log(df["dist_pref"])
df["oy"] = df["o"].astype(str) + "_" + df["year"].astype(str)
df["dy"] = df["d"].astype(str) + "_" + df["year"].astype(str)
df["pair"] = np.minimum(df.o, df.d).astype(str) + "_" + np.maximum(df.o, df.d).astype(str)
df["dpair"] = df["o"].astype(str) + "_" + df["d"].astype(str)
TOKYO = {11, 12, 13, 14}
out = {}


def coef(m, v):
    t = m.tidy().loc[v]
    return dict(b=float(t["Estimate"]), se=float(t["Std. Error"]),
                lo=float(t["2.5%"]), hi=float(t["97.5%"]))


# 1) 年ごとの断面：対数 OLS（ゼロを除く）と PPML。出発県・到着県の固定効果（その年の人口や魅力をまとめて吸収）
rows = []
for y, g in df.groupby("year"):
    gp = g[g.flow > 0].copy(); gp["lflow"] = np.log(gp.flow)
    m_ols = pf.feols("lflow ~ ldist | o + d", data=gp, vcov={"CRV1": "pair"})
    m_ppml = pf.fepois("flow ~ ldist | o + d", data=g, vcov={"CRV1": "pair"})
    m_ppml2 = pf.fepois("flow ~ ldist + adj + same_region | o + d", data=g, vcov={"CRV1": "pair"})
    rows.append(dict(year=y, zeros=int((g.flow == 0).sum()),
                     ols=coef(m_ols, "ldist")["b"], ols_se=coef(m_ols, "ldist")["se"],
                     ppml=coef(m_ppml, "ldist")["b"], ppml_se=coef(m_ppml, "ldist")["se"],
                     ppml_ctrl=coef(m_ppml2, "ldist")["b"], ppml_ctrl_se=coef(m_ppml2, "ldist")["se"],
                     adj=coef(m_ppml2, "adj")["b"], same_region=coef(m_ppml2, "same_region")["b"]))
yr = pd.DataFrame(rows)
yr.to_csv(RES / "distance_by_year.csv", index=False)
print(yr.round(3).to_string())

# 2) まとめた推定（出発県×年・到着県×年の固定効果）
main = pf.fepois("flow ~ ldist + adj + same_region | oy + dy", data=df, vcov={"CRV1": "pair"})
olsd = df[df.flow > 0].copy(); olsd["lflow"] = np.log(olsd.flow)
main_ols = pf.feols("lflow ~ ldist + adj + same_region | oy + dy", data=olsd, vcov={"CRV1": "pair"})
out["main_ppml"] = {v: coef(main, v) for v in ["ldist", "adj", "same_region"]}
out["main_ols"] = {v: coef(main_ols, v) for v in ["ldist", "adj", "same_region"]}
out["zeros_total"] = int((df.flow == 0).sum())
out["n_obs"] = int(len(df))
print("PPML:", out["main_ppml"])
print("OLS :", out["main_ols"])

# 距離が2倍になると何%減るか
def halve(b):
    return 1 - 2 ** b
out["double_distance_ppml"] = halve(out["main_ppml"]["ldist"]["b"])
out["double_distance_ols"] = halve(out["main_ols"]["ldist"]["b"])

# 3) 期間ごとの距離の弾力性（同じモデルに 距離×期間 を入れて、差を検定）
df["period"] = pd.cut(df.year, [1988, 1995, 2002, 2009, 2016, 2019, 2025],
                      labels=["1989_95", "1996_02", "2003_09", "2010_16", "2017_19", "2020_25"]).astype(str)
for p in df.period.unique():
    df[f"ld_{p}"] = df.ldist * (df.period == p)
terms = " + ".join(f"ld_{p}" for p in sorted(df.period.unique()))
mp = pf.fepois(f"flow ~ {terms} + adj + same_region | oy + dy", data=df, vcov={"CRV1": "pair"})
per = pd.DataFrame([dict(period=p, **coef(mp, f"ld_{p}")) for p in sorted(df.period.unique())])
per.to_csv(RES / "distance_by_period.csv", index=False)
print(per.round(3).to_string())
# 最初と最後の期間の差の検定（ワルド）
b = mp.coef(); V = mp._vcov; names = list(b.index)
i0, i1 = names.index("ld_1989_95"), names.index("ld_2020_25")
diff = b.iloc[i1] - b.iloc[i0]
se = float(np.sqrt(V[i0, i0] + V[i1, i1] - 2 * V[i0, i1]))
out["period_diff_2020s_minus_1990s"] = dict(diff=float(diff), se=se, z=float(diff / se))

# 4) 新幹線のつながり：ペアの固定効果を入れて、つながる前後の変化だけで推定
sk = pf.fepois("flow ~ shinkansen | oy + dy + dpair", data=df, vcov={"CRV1": "pair"})
sk2 = pf.fepois("flow ~ shinkansen_mini | oy + dy + dpair", data=df, vcov={"CRV1": "pair"})
out["shinkansen"] = coef(sk, "shinkansen")
out["shinkansen_mini"] = coef(sk2, "shinkansen_mini")
# 新しくつながったペアがどれだけあったか（期間中に 0→1 になった向きつきペア）
chg = df.groupby("dpair").shinkansen.agg(["min", "max"])
out["shinkansen_switch_pairs"] = int(((chg["min"] == 0) & (chg["max"] == 1)).sum())
# イベントスタディ（つながった年からの年数、−5〜+8、それより前後はまとめる）
first = df[df.shinkansen == 1].groupby("dpair").year.min()
switch = chg[(chg["min"] == 0) & (chg["max"] == 1)].index
df["rel"] = np.nan
m = df.dpair.isin(switch)
df.loc[m, "rel"] = df.loc[m, "year"] - df.loc[m, "dpair"].map(first)
df["rel"] = df["rel"].clip(-6, 9)
evs = []
for k in range(-6, 10):
    if k == -1:
        continue
    df[f"ev_{k + 6}"] = (df.rel == k).astype(int)
    evs.append(f"ev_{k + 6}")
es = pf.fepois("flow ~ " + " + ".join(evs) + " | oy + dy + dpair", data=df, vcov={"CRV1": "pair"})
ev = pd.DataFrame([dict(k=int(e.split("_")[1]) - 6, **coef(es, e)) for e in evs])
ev = pd.concat([ev, pd.DataFrame([dict(k=-1, b=0.0, se=0.0, lo=0.0, hi=0.0)])]).sort_values("k")
ev.to_csv(RES / "shinkansen_event.csv", index=False)
print(ev.round(3).to_string())

# 5) 2025年の残差：予測より多い・少ない組（PPML、出発・到着の固定効果＋距離・隣接・同じ地方）
g25 = df[df.year == 2025].copy()
m25 = pf.fepois("flow ~ ldist + adj + same_region | o + d", data=g25)
g25["pred"] = m25.predict(type="response")
g25["ratio"] = g25.flow / g25.pred
g25[["o_name", "d_name", "flow", "pred", "ratio", "dist", "adj"]].sort_values("ratio").to_csv(RES / "residuals_2025.csv", index=False)
big = g25[g25.flow >= 500]
print(big.sort_values("ratio", ascending=False)[["o_name", "d_name", "flow", "pred", "ratio"]].head(10).round(2).to_string())
print(big.sort_values("ratio")[["o_name", "d_name", "flow", "pred", "ratio"]].head(10).round(2).to_string())
# 東京圏への流れ：東京圏以外から東京圏への移動の、実際÷予測（年ごと）
tok = []
for y, g in df.groupby("year"):
    mm = pf.fepois("flow ~ ldist + adj + same_region | o + d", data=g)
    gg = g.copy(); gg["pred"] = mm.predict(type="response")
    into = gg[(~gg.o.isin(TOKYO)) & (gg.d.isin(TOKYO))]
    outof = gg[(gg.o.isin(TOKYO)) & (~gg.d.isin(TOKYO))]
    tok.append(dict(year=y, into_ratio=into.flow.sum() / into.pred.sum(), out_ratio=outof.flow.sum() / outof.pred.sum(),
                    into=int(into.flow.sum()), out=int(outof.flow.sum())))
tok = pd.DataFrame(tok); tok.to_csv(RES / "tokyo_area_ratio.csv", index=False)
print(tok.round(3).to_string())

# 6) 頑健性（まとめた PPML の距離の係数）
rob = []
def add(name, data, f="flow ~ ldist + adj + same_region | oy + dy", var="ldist", kind="ppml"):
    if kind == "ppml":
        mm = pf.fepois(f, data=data, vcov={"CRV1": "pair"})
    else:
        mm = pf.feols(f, data=data, vcov={"CRV1": "pair"})
    rob.append(dict(setting=name, **coef(mm, var)))
add("基本（県庁所在地の距離、1989〜2025年）", df)
d2 = df.copy(); d2["ldist"] = d2["ldist_pref"]
for p_ in sorted(df.period.unique()):
    d2[f"ld_{p_}"] = d2.ldist * (d2.period == p_)
add("距離を県の代表点で測る", d2)
add("東京圏（1都3県）を発着とする移動を除く", df[~df.o.isin(TOKYO) & ~df.d.isin(TOKYO)])
add("コロナ期（2020〜2022年）を除く", df[~df.year.isin([2020, 2021, 2022])])
add("隣接・同じ地方を入れない", df, f="flow ~ ldist | oy + dy")
add("北海道・沖縄を除く", df[~df.o.isin([1, 47]) & ~df.d.isin([1, 47])])
d3 = df.copy(); d3["lflow1"] = np.log(d3.flow + 1)
add("対数の最小二乗法（log(移動者+1)）", d3, f="lflow1 ~ ldist + adj + same_region | oy + dy", kind="ols")
add("対数の最小二乗法（ゼロを除く）", olsd, f="lflow ~ ldist + adj + same_region | oy + dy", kind="ols")
rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)
print(rob.round(3).to_string())

# 頑健性：期間の比較（1990年代と2020年代の差）を、条件を変えても見る
rob2 = []; rob2full = []
for name, data in [("基本", df), ("東京圏を除く", df[~df.o.isin(TOKYO) & ~df.d.isin(TOKYO)]),
                   ("県の代表点の距離", d2), ("北海道・沖縄を除く", df[~df.o.isin([1, 47]) & ~df.d.isin([1, 47])])]:
    mm = pf.fepois(f"flow ~ {terms} + adj + same_region | oy + dy", data=data, vcov={"CRV1": "pair"})
    rob2.append(dict(setting=name, b_1990s=coef(mm, "ld_1989_95")["b"], b_2020s=coef(mm, "ld_2020_25")["b"]))
    for p_ in sorted(df.period.unique()):
        rob2full.append(dict(setting=name, period=p_, **coef(mm, f"ld_{p_}")))
pd.DataFrame(rob2full).to_csv(RES / "robustness_period_full.csv", index=False)
rob2 = pd.DataFrame(rob2); rob2.to_csv(RES / "robustness_period.csv", index=False)
print(rob2.round(3).to_string())

# 頑健性：新幹線（ペアの固定効果つき）
rs = []
for name, data, var in [("基本（フル規格）", df, "shinkansen"), ("ミニ新幹線（山形・秋田）も含める", df, "shinkansen_mini"),
                        ("東京圏を発着とする移動を除く", df[~df.o.isin(TOKYO) & ~df.d.isin(TOKYO)], "shinkansen"),
                        ("1995年以降だけ", df[df.year >= 1995], "shinkansen"),
                        ("コロナ期を除く", df[~df.year.isin([2020, 2021, 2022])], "shinkansen")]:
    mm = pf.fepois(f"flow ~ {var} | oy + dy + dpair", data=data, vcov={"CRV1": "pair"})
    rs.append(dict(setting=name, **coef(mm, var)))
# 期間中に新しくつながったペアだけで比べる（つながる時期の違いだけを使う）
mm = pf.fepois("flow ~ shinkansen | oy + dy + dpair", data=df[df.dpair.isin(switch)], vcov={"CRV1": "pair"})
rs.append(dict(setting="期間中につながったペアだけ（時期の違いだけで比べる）", **coef(mm, "shinkansen")))
rs = pd.DataFrame(rs); rs.to_csv(RES / "robustness_shinkansen.csv", index=False)
print(rs.round(3).to_string())
out["shinkansen_switchers_only"] = rs.iloc[-1][["b", "se", "lo", "hi"]].astype(float).to_dict()

json.dump(out, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
