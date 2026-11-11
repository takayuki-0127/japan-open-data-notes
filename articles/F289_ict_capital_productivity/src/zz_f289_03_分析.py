"""03 分析：PLAN.md の H1〜H4 と頑健性 R1〜R6。結果は results/ に書く。"""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "processed" / "panel.csv")
EXCL = {84, 100}                       # 住宅・分類不明
ICT_PROD = {40, 41, 47, 48, 78, 80}    # ICT を作る側（R2）
d = d[(d["market"] == 1) & ~d["code"].isin(EXCL)].copy()
d["LP"] = d["V"] * 1e6 / (d["MH"] * 1e3)           # 円／時間（2015年価格）
for k in ["ict", "sw", "ithw"]:
    d[f"depth_{k}"] = d[f"stk_real_{k}"] * 1e6 / (d["MH"] * 1e3)  # ICT資本 円／時間
P = d.set_index(["code", "year"])
names = d.groupby("code")["name"].first()
rng = np.random.default_rng(289)
B = 1000

def spear(x, y, boot=True):
    m = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[m], np.asarray(y)[m]
    r = stats.spearmanr(x, y).statistic
    p = stats.spearmanr(x, y).pvalue
    lo = hi = np.nan
    if boot:
        bs = []
        n = len(x)
        for _ in range(B):
            i = rng.integers(0, n, n)
            bs.append(stats.spearmanr(x[i], y[i]).statistic)
        lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    return {"rho": round(float(r), 3), "p": round(float(p), 4), "lo": round(float(lo), 3), "hi": round(float(hi), 3), "n": int(len(x))}

def growth(var, a, b, codes):
    va = P[var].reindex([(c, a) for c in codes]).values
    vb = P[var].reindex([(c, b) for c in codes]).values
    with np.errstate(divide="ignore", invalid="ignore"):
        g = (np.log(vb) - np.log(va)) / (b - a)
    return pd.Series(g, index=codes)

def mean_of(var, a, b, codes):
    # 期間内のすべての年に値があるときだけ平均する（欠けた年を飛ばして平均しない）
    s = P[var].unstack()
    return s.loc[codes, [y for y in range(a + 1, b + 1)]].mean(axis=1, skipna=False)

def ratio_of(num, den, a, b, codes):
    s1 = P[num].unstack().loc[codes, list(range(a, b + 1))].sum(axis=1)
    s2 = P[den].unstack().loc[codes, list(range(a, b + 1))].sum(axis=1)
    return s1 / s2

# 比べる産業をひとつに固定する（レビュー後の修正）：
# 1994〜2020年の全年で労働生産性が正の値で求まり、1995〜2020年の全年で TFPva がある産業だけ。
# 外れるのは石炭製品（code 24：付加価値が負の年が多く、TFPva は 2009〜2016年だけ）。
_lp = P["LP"].unstack(); _t = P["TFPva"].unstack()
_ok = (_lp.loc[:, 1994:2020] > 0).all(axis=1) & _t.loc[:, 1995:2019].notna().all(axis=1)
codes_all = sorted(int(c) for c in _ok.index[_ok])
codes_dropped = sorted(int(c) for c in _ok.index[~_ok])
codes_noprod = [c for c in codes_all if c not in ICT_PROD]
PER = {"前半": (1995, 2007), "後半": (2007, 2019)}
res = {"n_sectors": len(codes_all), "codes": {int(c): names[c] for c in codes_all},
       "dropped": {int(c): names[c] for c in codes_dropped}}
rows = []

def block(tag, codes, kind="ict", periods=PER, level_year=2015):
    out = {}
    lp = np.log(P["LP"].reindex([(c, level_year) for c in codes]).values)
    dp = np.log(P[f"depth_{kind}"].reindex([(c, level_year) for c in codes]).values)
    out["H1_level"] = spear(dp, lp)
    for pn, (a, b) in periods.items():
        gd = growth(f"depth_{kind}", a, b, codes)
        glp = growth("LP", a, b, codes)
        tfp = mean_of("TFPva", a, b, codes)
        out[f"H2_{pn}"] = spear(gd.values, glp.values)
        out[f"H3_{pn}"] = spear(gd.values, tfp.values)
    a, b = list(periods.values())[0]
    c2, d2 = list(periods.values())[-1]
    r = ratio_of(f"inv_nom_{kind}", "inv_nom_all", a, b, codes)
    out["H4"] = spear(r.values, growth("LP", c2, d2, codes).values)
    out["H4_TFP"] = spear(r.values, mean_of("TFPva", c2, d2, codes).values)
    for k, v in out.items():
        rows.append({"条件": tag, "指標": k, **v})
    return out

base = block("基本", codes_all)
res["base"] = base
verd = {
    "H1": "支持" if base["H1_level"]["rho"] >= 0.3 else "外れ",
    "H2": "支持" if (base["H2_前半"]["rho"] > 0 and base["H2_後半"]["rho"] > 0) else "外れ",
    "H3": "支持" if (abs(base["H3_前半"]["rho"]) < 0.2 and abs(base["H3_後半"]["rho"]) < 0.2) else "外れ",
    "H4": "支持" if base["H4"]["rho"] < 0.2 else "外れ",
}
res["verdict"] = verd
# 頑健性
res["R1_software"] = block("R1 ソフトウェアだけ", codes_all, kind="sw")
res["R2_noprod"] = block("R2 ICTを作る側を除く", codes_noprod)
res["R4_to2020"] = block("R4 後半を2020年まで", codes_all, periods={"前半": (1995, 2007), "後半": (2007, 2020)})
res["R5_3periods"] = block("R5 3期間", codes_all, periods={"P1": (1995, 2005), "P2": (2005, 2015), "P3": (2015, 2019)})

# R3：マンアワーで重みをつけた回帰の傾き（労働生産性の伸び ～ ICT資本の深さの伸び）
def wls(codes, a, b, y="LP"):
    gd = growth("depth_ict", a, b, codes); 
    gy = growth("LP", a, b, codes) if y == "LP" else mean_of("TFPva", a, b, codes)
    w = P["MH"].reindex([(c, a) for c in codes]).values
    m = np.isfinite(gd.values) & np.isfinite(gy.values) & np.isfinite(w)
    X = np.c_[np.ones(m.sum()), gd.values[m]]; W = w[m] / w[m].mean(); Y = gy.values[m]
    XtW = X.T * W
    beta = np.linalg.solve(XtW @ X, XtW @ Y)
    e = Y - X @ beta
    # HC1 の頑健な標準誤差
    meat = (X * (W * e)[:, None]).T @ (X * (W * e)[:, None]) * len(Y) / (len(Y) - 2)
    bread = np.linalg.inv(XtW @ X)
    se = np.sqrt(np.diag(bread @ meat @ bread))
    return {"slope": round(float(beta[1]), 3), "se": round(float(se[1]), 3), "n": int(m.sum())}
res["R3_wls"] = {pn: {"LP": wls(codes_all, a, b), "TFP": wls(codes_all, a, b, "TFP")} for pn, (a, b) in PER.items()}
# R6：ピアソン（対数・伸び）
def pear(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    r, p = stats.pearsonr(np.asarray(x)[m], np.asarray(y)[m]); return {"r": round(float(r), 3), "p": round(float(p), 4)}
R6 = {}
lp = np.log(P["LP"].reindex([(c, 2015) for c in codes_all]).values)
dp = np.log(P["depth_ict"].reindex([(c, 2015) for c in codes_all]).values)
R6["H1"] = pear(dp, lp)
for pn, (a, b) in PER.items():
    gd = growth("depth_ict", a, b, codes_all)
    R6[f"H2_{pn}"] = pear(gd.values, growth("LP", a, b, codes_all).values)
    R6[f"H3_{pn}"] = pear(gd.values, mean_of("TFPva", a, b, codes_all).values)
res["R6_pearson"] = R6
# 記述：マクロの ICT 投資比率、ICT資本の深さの伸び
tot = d[d["code"].isin(codes_all)].groupby("year")[["inv_nom_ict", "inv_nom_sw", "inv_nom_all", "stk_real_ict", "MH", "V"]].sum()
res["macro"] = {
    "ict_inv_share": {int(y): round(float(v), 4) for y, v in (tot["inv_nom_ict"] / tot["inv_nom_all"]).items() if np.isfinite(v)},
    "sw_inv_share": {int(y): round(float(v), 4) for y, v in (tot["inv_nom_sw"] / tot["inv_nom_all"]).items() if np.isfinite(v)},
}
pd.DataFrame(rows).to_csv(RES / "A_correlations.csv", index=False)
# 部門別の表（図用）
tab = pd.DataFrame(index=codes_all)
tab["name"] = names.reindex(codes_all)
tab["LP2015"] = P["LP"].reindex([(c, 2015) for c in codes_all]).values
tab["depth2015"] = P["depth_ict"].reindex([(c, 2015) for c in codes_all]).values
for pn, (a, b) in PER.items():
    tab[f"g_depth_{pn}"] = growth("depth_ict", a, b, codes_all).values
    tab[f"g_LP_{pn}"] = growth("LP", a, b, codes_all).values
    tab[f"TFP_{pn}"] = mean_of("TFPva", a, b, codes_all).values
tab["ict_inv_ratio_前半"] = ratio_of("inv_nom_ict", "inv_nom_all", 1995, 2007, codes_all).values
tab["MH2007"] = P["MH"].reindex([(c, 2007) for c in codes_all]).values
tab["ict_producer"] = [c in ICT_PROD for c in codes_all]
tab.to_csv(RES / "B_sectors.csv", float_format="%.6g")
json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ["n_sectors", "verdict", "base"]}, ensure_ascii=False, indent=1))
for k in ["R1_software", "R2_noprod", "R4_to2020", "R5_3periods"]:
    print(k, {kk: v["rho"] for kk, v in res[k].items()})
print("R3", res["R3_wls"]); print("R6", res["R6_pearson"])

# ---- 問い直し（結果を見た後に足した）：水準の強い相関は「資本全体が多い産業だから」か？
def partial_spearman(x, y, z):
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    rx, ry, rz = [stats.rankdata(v[m]) for v in (x, y, z)]
    ex = rx - np.polyval(np.polyfit(rz, rx, 1), rz)
    ey = ry - np.polyval(np.polyfit(rz, ry, 1), rz)
    r = float(stats.pearsonr(ex, ey)[0])
    X, Y, Z = x[m], y[m], z[m]; n = len(X); bs = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        a1, a2, a3 = [stats.rankdata(v[i]) for v in (X, Y, Z)]
        e1 = a1 - np.polyval(np.polyfit(a3, a1, 1), a3)
        e2 = a2 - np.polyval(np.polyfit(a3, a2, 1), a3)
        bs.append(stats.pearsonr(e1, e2)[0])
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    return {"rho": round(r, 3), "lo": round(float(lo), 3), "hi": round(float(hi), 3), "n": int(n)}
re = {}
for yr in [1995, 2007, 2015, 2019]:
    idx = [(c, yr) for c in codes_all]
    lp = np.log(P["LP"].reindex(idx).values)
    ict = np.log(P["depth_ict"].reindex(idx).values)
    nonict = np.log(((P["stk_real_all"] - P["stk_real_ict"]) * 1e6 / (P["MH"] * 1e3)).reindex(idx).values)
    share = (P["stk_real_ict"] / P["stk_real_all"]).reindex(idx).values
    r_p = partial_spearman(ict, lp, nonict)
    re[yr] = {"ict_depth_vs_LP": spear(ict, lp, boot=False)["rho"],
              "nonict_depth_vs_LP": spear(nonict, lp, boot=False)["rho"],
              "ict_vs_LP_partial_nonict": r_p,
              "ict_share_of_capital_vs_LP": spear(share, lp, boot=(yr == 2015))}
# 伸び：ICT の割合（資本の中身）を増やした産業は伸びたか
for pn, (a, b) in PER.items():
    sh_a = (P["stk_real_ict"] / P["stk_real_all"]).reindex([(c, a) for c in codes_all]).values
    sh_b = (P["stk_real_ict"] / P["stk_real_all"]).reindex([(c, b) for c in codes_all]).values
    dsh = (sh_b - sh_a) * 100 / (b - a)  # ポイント／年
    re[f"dshare_vs_LPgrowth_{pn}"] = spear(dsh, growth("LP", a, b, codes_all).values)
    re[f"dshare_vs_TFP_{pn}"] = spear(dsh, mean_of("TFPva", a, b, codes_all).values)
res["reask"] = re
tab["ict_share_cap2015"] = (P["stk_real_ict"] / P["stk_real_all"]).reindex([(c, 2015) for c in codes_all]).values
tab["nonict_depth2015"] = ((P["stk_real_all"] - P["stk_real_ict"]) * 1e6 / (P["MH"] * 1e3)).reindex([(c, 2015) for c in codes_all]).values
tab.to_csv(RES / "B_sectors.csv", float_format="%.6g")
json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print("reask", json.dumps(re, ensure_ascii=False))
