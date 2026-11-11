"""F234 分析：価格弾力性を「値付けの判断」に使うための推定と比較
A 推定の仕方で弾力性はどれだけ変わるか（品目ごとの単純回帰／トレンド付き／前年差＋年の効果／操作変数）
B 操作変数（輸入物価×輸入の受けやすさ）
C 交差弾力性（代わりになる品目の値段）
D 値上げの判断表と、推定の幅を入れたときの「利益が減る確率」
E 頑健性
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from common import *

rng = np.random.default_rng(SEED)
d = load_panel()
boj = load_boj_annual()
out = {}

# ---------- A. 推定の仕方 ----------
rowsA = []
for name, g in d.groupby("name"):
    g = g.dropna(subset=["lp", "lq"])
    if len(g) < 10:
        continue
    X = sm.add_constant(g[["lp"]])
    b1 = sm.OLS(g.lq, X).fit().params["lp"]
    X2 = sm.add_constant(np.column_stack([g.lp, g.year - 2000]))
    b2 = sm.OLS(g.lq, X2).fit().params[1]
    gd = g.dropna(subset=["dlp", "dlq"])
    b3 = sm.OLS(gd.dlq, sm.add_constant(gd[["dlp"]])).fit().params["dlp"] if len(gd) >= 8 else np.nan
    rowsA.append(dict(name=name, group=g.group.iloc[0], n=len(g), levels=b1, trend=b2, diff=b3,
                      exp_share=g.exp.mean()))
A = pd.DataFrame(rowsA)
A.to_csv(RES / "A_item_estimates.csv", index=False)


def wmed(x, w):
    o = np.argsort(x); x, w = np.asarray(x)[o], np.asarray(w)[o]
    c = np.cumsum(w) / w.sum()
    return float(x[np.searchsorted(c, 0.5)])


summA = {}
for c in ["levels", "trend", "diff"]:
    s = A[c].dropna()
    summA[c] = dict(median=float(s.median()), share_positive=float((s > 0).mean()),
                    q25=float(s.quantile(.25)), q75=float(s.quantile(.75)), n=int(len(s)))

# 前年差＋年の効果（全品目をまとめて、品目でクラスターの標準誤差）
def panel_fd(df, weight=None, extra=None):
    df = df.dropna(subset=["dlp", "dlq"]).copy()
    yd = pd.get_dummies(df.year, prefix="y", drop_first=True).astype(float)
    cols = ["dlp"] + (extra or [])
    X = pd.concat([df[cols], yd], axis=1)
    X = sm.add_constant(X)
    if weight is not None:
        m = sm.WLS(df.dlq, X, weights=df[weight].fillna(df[weight].mean())).fit(
            cov_type="cluster", cov_kwds={"groups": df.name.astype("category").cat.codes})
    else:
        m = sm.OLS(df.dlq, X).fit(cov_type="cluster", cov_kwds={"groups": df.name.astype("category").cat.codes})
    ci = m.conf_int().loc["dlp"]
    return dict(b=float(m.params["dlp"]), lo=float(ci[0]), hi=float(ci[1]), n=int(m.nobs),
                items=int(df.name.nunique())), m

fd_all, _ = panel_fd(d)
fd_w, _ = panel_fd(d, weight="w")
summA["panel_fd_yearFE"] = fd_all
summA["panel_fd_yearFE_weighted"] = fd_w
out["A"] = summA

# ---------- B. 操作変数 ----------
def make_iv(df, food_list):
    x = df.merge(boj[["year", "dl_imp_food", "dl_imp_energy", "dl_usdjpy"]], on="year", how="left")
    x["E_food"] = x.name.isin(food_list).astype(float)
    x["E_energy"] = x.name.isin(ENERGY).astype(float)
    x["z_food"] = x.dl_imp_food * x.E_food
    x["z_energy"] = x.dl_imp_energy * x.E_energy
    return x.dropna(subset=["dlp", "dlq", "dl_imp_food"])


def tsls(x, zcols, weight=None):
    yd = pd.get_dummies(x.year, prefix="y", drop_first=True).astype(float).reset_index(drop=True)
    x = x.reset_index(drop=True)
    W = sm.add_constant(yd)
    Z = pd.concat([W, x[zcols]], axis=1)
    groups = x.name.astype("category").cat.codes
    fs = sm.OLS(x.dlp, Z).fit(cov_type="cluster", cov_kwds={"groups": groups})
    R = np.zeros((len(zcols), Z.shape[1]));
    for i, c in enumerate(zcols):
        R[i, list(Z.columns).index(c)] = 1
    F = float(fs.f_test(R).fvalue)
    xhat = fs.fittedvalues
    X2 = pd.concat([W, xhat.rename("dlp")], axis=1)
    b = sm.OLS(x.dlq, X2).fit().params["dlp"]
    return float(b), F, fs


def iv_with_boot(food_list, zcols, B=500, sample=None):
    x = make_iv(d, food_list)
    if sample is not None:
        x = sample(x)
    b, F, fs = tsls(x, zcols)
    items = x.name.unique()
    bs = []
    for _ in range(B):
        pick = rng.choice(items, len(items), replace=True)
        xb = pd.concat([x[x.name == it].assign(name=f"{it}#{k}") for k, it in enumerate(pick)])
        try:
            bb, _, _ = tsls(xb, zcols)
            bs.append(bb)
        except Exception:
            pass
    bs = np.array(bs)
    # 同じ標本での前年差 OLS
    ols, _ = panel_fd(x)
    return dict(b=b, lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                first_stage_F=F, n=int(len(x)), items=int(x.name.nunique()),
                ols_same_sample=ols, boot=len(bs))

ivB = {}
ivB["main_narrow_food+energy"] = iv_with_boot(IMPORT_FOOD_NARROW, ["z_food", "z_energy"])
ivB["broad_food+energy"] = iv_with_boot(IMPORT_FOOD_BROAD, ["z_food", "z_energy"], B=300)
ivB["food_only_narrow"] = iv_with_boot(IMPORT_FOOD_NARROW, ["z_food"], B=300,
                                       sample=lambda x: x[x.energy == 0])
ivB["energy_only"] = iv_with_boot(IMPORT_FOOD_NARROW, ["z_energy"], B=300,
                                  sample=lambda x: x[(x.energy == 1) | (~x.name.isin(IMPORT_FOOD_BROAD))])
out["B"] = ivB

# ---------- C. 交差弾力性 ----------
rowsC = []
piv_p = d.pivot(index="year", columns="name", values="dlp")
piv_q = d.pivot(index="year", columns="name", values="dlq")
food_exp = d[d.energy == 0].groupby("year").exp.sum()
dl_food_exp = np.log(food_exp).diff()
for gname, items in CROSS_GROUPS.items():
    for i in items:
        others = [j for j in items if j != i]
        df = pd.concat([piv_q[i].rename("dlq"), piv_p[i].rename("own")] +
                       [piv_p[j].rename("x_" + j) for j in others] + [dl_food_exp.rename("dlexp")], axis=1).dropna()
        X = sm.add_constant(df.drop(columns="dlq"))
        m = sm.OLS(df.dlq, X).fit(cov_type="HC1")
        ci = m.conf_int()
        rowsC.append(dict(group=gname, item=i, partner="（自分）", b=m.params["own"], lo=ci.loc["own", 0],
                          hi=ci.loc["own", 1], n=int(m.nobs)))
        for j in others:
            k = "x_" + j
            rowsC.append(dict(group=gname, item=i, partner=j, b=m.params[k], lo=ci.loc[k, 0], hi=ci.loc[k, 1],
                              n=int(m.nobs)))
C = pd.DataFrame(rowsC)
C.to_csv(RES / "C_cross_elasticities.csv", index=False)
cross = C[C.partner != "（自分）"]
out["C"] = dict(n_pairs=int(len(cross)), n_sig_pos=int(((cross.lo > 0)).sum()), n_sig_neg=int((cross.hi < 0).sum()),
                own_sig_neg=int(((C.partner == "（自分）") & (C.hi < 0)).sum()),
                own_total=int((C.partner == "（自分）").sum()))

# ---------- D. 値上げの判断表 ----------
def profit_ratio(x, eps, m):
    return ((1 + x) - (1 - m)) / m * (1 + x) ** eps


def breakeven(x, m):
    return float(np.log(m / (m + x)) / np.log(1 + x))

rowsD = []
for m in [0.1, 0.2, 0.3, 0.5]:
    for x in [0.03, 0.05, 0.10]:
        r = dict(margin=m, price_up=x, breakeven_eps=breakeven(x, m))
        for eps in [-0.3, -0.8, -1.5, -3.0]:
            r[f"profit_chg_eps{eps}"] = profit_ratio(x, eps, m) - 1
            r[f"revenue_chg_eps{eps}"] = (1 + x) ** (1 + eps) - 1
        rowsD.append(r)
D = pd.DataFrame(rowsD)
D.to_csv(RES / "D_decision_table.csv", index=False)

# 群ごとの弾力性（前年差＋年の効果、品目でクラスターのブートストラップ）→ 架空のスーパーの値上げ判断
def group_boot(gdf, B=500):
    gdf = gdf.dropna(subset=["dlp", "dlq"])
    allx = d.dropna(subset=["dlp", "dlq"])
    # 年の効果は全品目で取り除く（全品目の年平均を引く）
    ym_p = allx.groupby("year").dlp.mean(); ym_q = allx.groupby("year").dlq.mean()
    g2 = gdf.assign(p=gdf.dlp - gdf.year.map(ym_p), q=gdf.dlq - gdf.year.map(ym_q))
    def est(z):
        X = sm.add_constant(z.p.values); return sm.OLS(z.q.values, X).fit().params[1]
    b = est(g2)
    items = g2.name.unique(); bs = []
    for _ in range(B):
        pick = rng.choice(items, len(items), replace=True)
        bs.append(est(pd.concat([g2[g2.name == it] for it in pick])))
    return float(b), np.array(bs)

rowsG = []
boots = {}
for gname, gdf in d[d.energy == 0].groupby("group"):
    b, bs = group_boot(gdf)
    boots[gname] = bs
    rowsG.append(dict(group=gname, b=b, lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                      items=int(gdf.name.nunique())))
G = pd.DataFrame(rowsG).sort_values("b")
# 架空のスーパー：粗利率30%、5%値上げで利益が減る確率
x, m = 0.05, 0.30
be = breakeven(x, m)
G["breakeven_eps_m30_x5"] = be
G["prob_profit_down_m30_x5"] = [float((boots[g] < be).mean()) for g in G.group]
G["prob_profit_down_m20_x5"] = [float((boots[g] < breakeven(0.05, 0.2)).mean()) for g in G.group]
G["prob_profit_down_m10_x5"] = [float((boots[g] < breakeven(0.05, 0.1)).mean()) for g in G.group]
G.to_csv(RES / "D_group_elasticity_and_risk.csv", index=False)
out["D"] = dict(breakeven_m30_x5=be, breakeven_m10_x5=breakeven(0.05, 0.1), breakeven_m50_x5=breakeven(0.05, 0.5),
                groups=G.to_dict("records"))

# ---------- E. 頑健性（前年差＋年の効果） ----------
rob = {}
rob["全期間 2003〜24"] = fd_all
rob["2003〜19"] = panel_fd(d[d.year <= 2019])[0]
rob["2021〜24"] = panel_fd(d[d.year >= 2021])[0]
rob["支出の重みつき"] = fd_w
rob["区分の変更らしき4年も含める"] = panel_fd(d.assign(dlp=d.dlp_raw, dlq=d.dlq_raw))[0]
out["n_break"] = int(d["break"].sum())
out["breaks"] = d.loc[d["break"] == 1, ["name", "year"]].to_dict("records")
rob["エネルギーを除く"] = panel_fd(d[d.energy == 0])[0]
rob["生鮮を除く"] = panel_fd(d[d.fresh == 0])[0]
rob["生鮮だけ"] = panel_fd(d[d.fresh == 1])[0]
# 前年の値段の変化も入れる（短期と1年遅れの合計）
dl = d.dropna(subset=["dlp_l1"])
r_l, m_l = panel_fd(dl, extra=["dlp_l1"])
rob["1年遅れを足した合計"] = dict(b=float(m_l.params["dlp"] + m_l.params["dlp_l1"]), n=int(m_l.nobs),
                              b_now=float(m_l.params["dlp"]), b_lag=float(m_l.params["dlp_l1"]))
# 2年差
d2 = d.copy(); g = d2.groupby("name")
d2["dlp"] = g.lp.diff(2); d2["dlq"] = g.lq.diff(2)
d2 = d2[d2.year % 2 == 0]
rob["2年差"] = panel_fd(d2)[0]
out["E"] = rob

json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: (v if k != "D" else {kk: vv for kk, vv in v.items() if kk != "groups"}) for k, v in out.items()},
                 ensure_ascii=False, indent=1, default=float)[:6000])
print(G.to_string())
