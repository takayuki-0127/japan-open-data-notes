"""03 分析：7時点で RFM の区分を作り、6か月後の動きと捕捉率を測る（計画 PLAN.md の H1〜H4・頑健性）。"""
import json, sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f279_common import *
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
inv = load()

def run(inv, back=12, fwd=6, **kw):
    out = {}
    for t in SNAPS:
        if t + pd.DateOffset(months=fwd) > pd.Timestamp("2011-12-01"): continue
        out[t] = snapshot(inv, t, back=back, fwd=fwd, **kw)
    return out

def metrics(snaps, kw={}, back=12, fwd=6):
    rows = []
    for t, g in snaps.items():
        g = g.copy(); g["rfm"] = g["r"] + g["f"] + g["m"] + g["M"] / (g["M"].abs().max() * 10 + 1)
        # 6か月後の区分（t+6 が7時点の範囲外でも計算できる：2011-12-01 まで）
        t6 = t + pd.DateOffset(months=6)
        if t6 <= pd.Timestamp("2011-12-01"):
            g6 = snapshot(inv_cur, t6, back=back, fwd=0 if t6 == pd.Timestamp("2011-12-01") else 6, **kw)["seg"]
            g["seg6"] = g6.reindex(g.index).fillna("離脱")
        champ = g[g["seg"] == "Champions"]
        rate_by_r = g.groupby("r")["rebuy"].mean()
        rows.append(dict(t=str(t.date()), n=len(g), n_champ=len(champ),
                         champ_stay=float((champ["seg6"] == "Champions").mean()) if "seg6" in g else np.nan,
                         rebuy=float(g["rebuy"].mean()),
                         rebuy_by_r=[round(float(x), 4) for x in rate_by_r.values],
                         mono_r=bool(rate_by_r.is_monotonic_increasing),
                         capA=capture(g, "M"), capB=capture(g, "rfm")))
    return pd.DataFrame(rows)

inv_cur = inv
S = run(inv)
base = metrics(S)
base.to_csv(RES / "A_snapshots.csv", index=False)

# 区分ごとの表（全時点）
allg = pd.concat(S.values())
seg_tab = (allg.groupby("seg").agg(n=("rebuy", "size"), rebuy=("rebuy", "mean"), fut_mean=("fut", "mean"),
                                    M_mean=("M", "mean"), R_mean=("R", "mean"), F_mean=("F", "mean"))
           .reindex(SEGS))
seg_tab["share"] = seg_tab["n"] / seg_tab["n"].sum()
seg_tab.round(4).to_csv(RES / "B_segments.csv")

# 遷移行列（t → t+6、7時点の合計）
trans = []
for t, g in S.items():
    t6 = t + pd.DateOffset(months=6)
    g6 = snapshot(inv, t6, back=12, fwd=0 if t6 == pd.Timestamp("2011-12-01") else 6)["seg"]
    trans.append(pd.DataFrame({"from": g["seg"], "to": g6.reindex(g.index).fillna("離脱")}))
trans = pd.concat(trans)
tm = pd.crosstab(trans["from"], trans["to"], normalize="index").reindex(index=SEGS, columns=SEGS + ["離脱"]).fillna(0)
tm.round(4).to_csv(RES / "C_transition.csv")

# H4：2010-12 と 2011-06 の区分ごとの率
r0 = S[pd.Timestamp("2010-12-01")].groupby("seg")["rebuy"].mean().reindex(SEGS)
r1 = S[pd.Timestamp("2011-06-01")].groupby("seg")["rebuy"].mean().reindex(SEGS)
h4 = pd.DataFrame({"r_2010_12": r0, "r_2011_06": r1}); h4["diff"] = h4["r_2011_06"] - h4["r_2010_12"]
h4.round(4).to_csv(RES / "D_h4_stability.csv")

# 方法C：2010-12 の結果で区分ごとの平均購入額を学び、2011-06 で並べる
g0 = S[pd.Timestamp("2010-12-01")]; g1 = S[pd.Timestamp("2011-06-01")].copy()
segmean = g0.groupby("seg")["fut"].mean()
g1["c_score"] = g1["seg"].map(segmean).fillna(0) + g1["M"] / (g1["M"].abs().max() * 10 + 1)
g1["rfm"] = g1["r"] + g1["f"] + g1["m"] + g1["M"] / (g1["M"].abs().max() * 10 + 1)
capC = dict(A=capture(g1, "M"), B=capture(g1, "rfm"), C=capture(g1, "c_score"))

H = dict(
    H1=dict(mean_stay=float(base["champ_stay"].mean()), by_t=base["champ_stay"].round(4).tolist(),
            verdict="支持" if base["champ_stay"].mean() < 0.60 else "外れ"),
    H2=dict(mono=base["mono_r"].tolist(), verdict="支持" if base["mono_r"].all() else "外れ"),
    H3=dict(capA=base["capA"].round(4).tolist(), capB=base["capB"].round(4).tolist(),
            mean_diff_pt=float((base["capB"] - base["capA"]).mean() * 100),
            verdict="支持" if abs((base["capB"] - base["capA"]).mean() * 100) < 3 else "外れ"),
    H4=dict(within10=int((h4["diff"].abs() <= 0.10).sum()), n=int(h4["diff"].notna().sum()),
            verdict="支持" if (h4["diff"].abs() <= 0.10).sum() >= 7 else "外れ"),
    methodC_2011_06=capC)

# 頑健性
rob = {}
def summ(name, df):
    rob[name] = dict(champ_stay=float(df["champ_stay"].mean()), mono_all=bool(df["mono_r"].all()),
                     n_mono=int(df["mono_r"].sum()), n=len(df),
                     capA=float(df["capA"].mean()), capB=float(df["capB"].mean()),
                     diff_pt=float((df["capB"] - df["capA"]).mean() * 100), rebuy=float(df["rebuy"].mean()))
summ("base", base)
summ("R1_back6", metrics(run(inv, back=6), back=6))
summ("R2_fwd3", metrics(run(inv, fwd=3), fwd=3))
s12 = {pd.Timestamp("2010-12-01"): snapshot(inv, "2010-12-01", fwd=12)}
summ("R2b_fwd12_201012", metrics(s12, fwd=12))
summ("R3_uk", metrics(run(inv, uk=True), dict(uk=True)))
summ("R4_droptop1", metrics(run(inv, drop_top=True), dict(drop_top=True)))
summ("R5_fixed", metrics(run(inv, fixed=True), dict(fixed=True)))
inv_cur = load(gross=True)
summ("R6_gross", metrics(run(inv_cur)))
inv_cur = inv
H["robustness"] = rob
json.dump(H, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in H.items() if k != "robustness"}, ensure_ascii=False, indent=1, default=float))
print(pd.DataFrame(rob).T.round(3))
print(seg_tab.round(3)); print(tm.round(2))
