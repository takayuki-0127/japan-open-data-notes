"""F267 03 分析：計画（PLAN.md）の H1〜H4 と頑健性。"""
import json, pathlib
import numpy as np, pandas as pd
BASE = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = BASE / "data", BASE / "results"
RES.mkdir(exist_ok=True)
m = pd.read_csv(DATA / "jfa_cvs_monthly.csv")
a = pd.read_csv(DATA / "jfa_cvs_annual.csv")
L = lambda x: np.log1p(x)
for df in (m, a):
    df["ls"], df["lc"], df["lp"] = L(df.sales_ex_yoy), L(df.cust_ex_yoy), L(df.price_ex_yoy)
    df["resid"] = df.ls - df.lc - df.lp
out = {}
COVID = [2020, 2021, 2022]

def varshare(d, cols=("lc", "lp"), tot="ls"):
    X = d[list(cols)].values; s = d[tot].values
    C = np.cov(np.c_[X, s].T, ddof=1)
    k = len(cols); vs = C[k, k]
    sh = {c: float((C[i, :k].sum()) / vs) for i, c in enumerate(cols)}  # Var(i)+Σcov(i,j)
    sh["var_total"] = float(vs); sh["n"] = int(len(d))
    sh["corr"] = float(np.corrcoef(X[:, 0], X[:, 1])[0, 1]) if k == 2 else None
    sh["resid_share"] = float(1 - sum(sh[c] for c in cols))
    return sh

base = m[m.year.between(2006, 2025)]
out["identity_resid_abs_max_month"] = float(m.resid.abs().max())
out["H1_H2_monthly"] = varshare(base)
out["annual_2006_2025"] = varshare(a[a.year.between(2006, 2025)])
# robustness
rob = {}
rob["exclude_covid"] = varshare(base[~base.year.isin(COVID)])
rob["first_half_2006_2015"] = varshare(base[base.year <= 2015])
rob["second_half_2016_2025"] = varshare(base[base.year >= 2016])
rob["second_half_ex_covid"] = varshare(base[(base.year >= 2016) & ~base.year.isin(COVID)])
# 全店：店舗数×1店あたり客数×客単価
mm = base.copy()
mm["ln_st"] = L(mm.stores_yoy); mm["ln_cps"] = L(mm.cust_all_yoy) - mm.ln_st; mm["ln_pa"] = L(mm.price_all_yoy)
mm["ln_sa"] = L(mm.sales_all_yoy)
rob["all_stores_3level"] = varshare(mm, cols=("ln_st", "ln_cps", "ln_pa"), tot="ln_sa")
rob["all_stores_3level_ex_covid"] = varshare(mm[~mm.year.isin(COVID)], cols=("ln_st", "ln_cps", "ln_pa"), tot="ln_sa")
# そのままの％：s ≈ c + p + c*p
bb = base.copy(); bb["cp"] = bb.cust_ex_yoy * bb.price_ex_yoy
rob["simple_pct"] = varshare(bb.rename(columns={"cust_ex_yoy": "c", "price_ex_yoy": "p"}), cols=("c", "p", "cp"), tot="sales_ex_yoy")
out["robustness"] = rob

# --- H3: 割り付け（年次） ---
A = a.set_index("year")
def past5(col, t):
    w = A.loc[t - 5:t - 1, col]
    return float(w.mean()) if len(w) == 5 else np.nan

rows = []
for t in range(2006, 2026):
    for Xname in ["past5", "0", "+1", "+2"]:
        X = past5("ls", t) if Xname == "past5" else {"0": 0.0, "+1": np.log(1.01), "+2": np.log(1.02)}[Xname]
        if np.isnan(X): continue
        mc, mp = past5("lc", t), past5("lp", t)
        alloc = {"equal": (X / 2, X / 2), "price_only": (0.0, X)}
        # 計画どおり：前5年の平均の伸びの比で割る
        if not np.isnan(mc) and abs(mc + mp) > 1e-9:
            alloc["trend_ratio"] = (X * mc / (mc + mp), X * mp / (mc + mp))
        # 補助：傾向から出発し、目標との差を等分
        if not np.isnan(mc):
            g = X - (mc + mp); alloc["trend_gap"] = (mc + g / 2, mp + g / 2)
        for rule, (xc, xp) in alloc.items():
            rows.append(dict(year=t, X=Xname, rule=rule, Xs=X, Xc=xc, Xp=xp,
                             hit_s=A.loc[t, "ls"] >= X, hit_c=A.loc[t, "lc"] >= xc, hit_p=A.loc[t, "lp"] >= xp,
                             mc=mc, mp=mp))
H = pd.DataFrame(rows)
H.to_csv(RES / "H3_allocation_by_year.csv", index=False)

def summarize(h):
    g = h.groupby(["X", "rule"]).agg(n=("year", "size"), hit_s=("hit_s", "mean"), hit_c=("hit_c", "mean"), hit_p=("hit_p", "mean")).reset_index()
    g["gap_c"] = (g.hit_c - g.hit_s).abs(); g["gap_p"] = (g.hit_p - g.hit_s).abs()
    g["gap_max"] = g[["gap_c", "gap_p"]].max(axis=1)
    return g
S = summarize(H); S["period"] = "all"
S1 = summarize(H[H.year <= 2015]); S1["period"] = "first"
S2 = summarize(H[H.year >= 2016]); S2["period"] = "second"
S3 = summarize(H[~H.year.isin(COVID)]); S3["period"] = "ex_covid"
SS = pd.concat([S, S1, S2, S3])
SS.to_csv(RES / "H3_allocation_summary.csv", index=False)

def h3_verdict(Sx, X):
    e = Sx[(Sx.X == X) & (Sx.rule == "equal")]; tr = Sx[(Sx.X == X) & (Sx.rule == "trend_ratio")]
    if e.empty or tr.empty: return None
    e, tr = e.iloc[0], tr.iloc[0]
    return dict(equal_gap_max=float(e.gap_max), trend_gap_max=float(tr.gap_max), n=int(e.n),
                part1=bool(e.gap_max >= 0.20), part2=bool(tr.gap_max < 0.10),
                support=bool(e.gap_max >= 0.20 and tr.gap_max < 0.10))
out["H3"] = {p: {X: h3_verdict(SS[SS.period == p], X) for X in ["past5", "0", "+1", "+2"]} for p in ["all", "first", "second", "ex_covid"]}

# --- H4: 月次の判定と年次の判定の食い違い（目標：past5、割り付け：trend_ratio と equal） ---
h4 = {}
for rule in ["trend_ratio", "equal"]:
    hh = H[(H.X == "past5") & (H.rule == rule)].set_index("year")
    mm2 = m[m.year.isin(hh.index)].copy()
    for k, col, tg, ann in [("s", "ls", "Xs", "hit_s"), ("c", "lc", "Xc", "hit_c"), ("p", "lp", "Xp", "hit_p")]:
        mon = mm2[col].values >= hh.loc[mm2.year, tg].values
        yr = hh.loc[mm2.year, ann].values
        dis = mon != yr
        h4[f"{rule}_{k}"] = dict(disagree=float(dis.mean()), n=int(len(dis)),
                               disagree_ex_covid=float(dis[~mm2.year.isin(COVID).values].mean()))
out["H4"] = h4

# 2つの出所の照合（全店の売上の前年同月比）
meti = pd.read_csv(DATA / "meti_cvs_monthly.csv").set_index("ym")
meti["yoy"] = meti.meti_sales / meti.meti_sales.shift(12) - 1
j = m.set_index("ym")[["sales_all_yoy"]].join(meti.yoy, how="inner").dropna()
out["source_check"] = dict(n=int(len(j)), period=[j.index.min(), j.index.max()],
                           corr=float(j.corr().iloc[0, 1]), mean_abs_diff=float((j.sales_all_yoy - j.yoy).abs().mean()))
j.to_csv(RES / "source_check_monthly.csv")

# 判定
o = out["H1_H2_monthly"]
out["verdicts"] = {
    "H1": dict(cust_share=o["lc"], support=o["lc"] > 0.5),
    "H2": dict(corr=o["corr"], support=o["corr"] < -0.3),
    "H3": out["H3"]["all"]["past5"],
    "H4": {k: dict(v, support=v["disagree"] >= 0.30) for k, v in h4.items()},
}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=lambda x: bool(x) if isinstance(x, np.bool_) else float(x))
print(json.dumps(out["verdicts"], ensure_ascii=False, indent=1, default=float))
print(SS[SS.period == "all"].round(3).to_string())
