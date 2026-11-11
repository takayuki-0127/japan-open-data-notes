"""F271 05 分析：04 の数を KLM の時間に換えて、仮説 H1〜H5・頑健性 R1〜R5・読み違い・問い直しをまとめる。"""
import os, json, math
import numpy as np, pandas as pd
from math import erf, sqrt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results")
t = pd.read_csv(os.path.join(R, "tasks.csv"))
p = pd.read_csv(os.path.join(ROOT, "data", "processed", "panel.csv"))
G = ["百貨店", "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "家電大型専門店"]
MAINQ = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]; XQ = ["X1", "X2", "X3", "X4"]
BASE = dict(P=1.1, B=0.1, K=0.28, M=1.35, C=1.35, R=0.3, SCR=1.1, S=0.05)
def tsec(df, k=BASE):
    return (df.P * k["P"] + df.B * k["B"] + df.K * k["K"] + df.M * k["M"] + df.C * k["C"] + df.R * k["R"]
            + df.SCR * k["SCR"] + df.SRCH * k["S"] / 2)
t["sec"] = tsec(t)
out = {"tasks": int(len(t)), "all_answers_correct": bool(t.ok.all()), "n_wrong": int((~t.ok).sum())}
sel = lambda vp="pc", per="main", qs=MAINQ: t[(t.vp == vp) & (t.period == per) & t.q.isin(qs)]
def med(df): return df.groupby("design").sec.median().round(2).to_dict()
# ---- H1
m_pc = med(sel()); r1 = m_pc["d3"] / m_pc["d1"]
out["H1"] = dict(median_sec_pc=m_pc, ratio_d3_d1=round(r1, 3), verdict="支持" if r1 <= 1 / 3 else "外れ")
# ---- H2
fs = sel().groupby("design")["first"].mean().round(3).to_dict()
out["H2"] = dict(first_screen_share_pc=fs, verdict="支持" if fs["d3"] >= 0.75 and fs["d1"] <= 0.25 else "外れ")
# ---- H3
m_sp = med(sel("sp")); r3 = {d: round(m_sp[d] / m_pc[d], 3) for d in m_pc}
out["H3"] = dict(median_sec_sp=m_sp, ratio_sp_pc=r3, verdict="支持" if r3["d2"] >= 2 and r3["d3"] <= 1.5 else "外れ")
# ---- H4 読み違い：D1 の折れ線を位置で読む（「前年同月より多いか」）
Phi = lambda z: 0.5 * (1 + erf(z / sqrt(2)))
MAIN = sorted(t[t.period == "main"].ym.unique()); COVID = sorted(t[t.period == "covid"].ym.unique())
months = sorted(p.ym.unique()); MI = {m: i for i, m in enumerate(months)}
lv = p.pivot(index="ym", columns="g", values="lvl")
def misread(sig, mset, chart="single"):
    res = []
    for L in mset:
        i = MI[L]
        for g in G:
            if chart == "single":
                s = lv[g].iloc[:i + 1]; lo, hi = s.min() * 0.9, s.max() * 1.05
            else:
                s = lv[G].iloc[max(0, i - 59):i + 1]; lo, hi = s.values.min() * 0.9, s.values.max() * 1.05
            d = abs(lv[g].iloc[i] - lv[g].iloc[i - 12]); sv = sig * (hi - lo)
            res.append(dict(ym=L, g=g, p=Phi(-d / (sv * sqrt(2))), yoy=(lv[g].iloc[i] / lv[g].iloc[i - 12] - 1) * 100))
    return pd.DataFrame(res)
mr = misread(0.015, MAIN); mr.to_csv(os.path.join(R, "misread_d1_single.csv"), index=False, float_format="%.5f")
mr_multi = misread(0.015, MAIN, "multi")
out["H4"] = dict(misread_mean_single=round(mr.p.mean(), 4), misread_mean_multi=round(mr_multi.p.mean(), 4),
                 by_g=mr.groupby("g").p.mean().round(3).to_dict(), share_cells_over_10pct=round((mr.p > 0.10).mean(), 3),
                 verdict="支持" if mr.p.mean() >= 0.10 else "外れ")
# ---- H5 想定外の問い
mx = med(sel(qs=XQ)); r5 = mx["d3"] / mx["d1"]
out["H5"] = dict(median_sec_pc_holdout=mx, ratio_d3_d1_holdout=round(r5, 3), ratio_main=round(r1, 3), times=round(r5 / r1, 2),
                 verdict="支持" if r5 >= 2 * r1 else "外れ")
# ---- 問いごとの中央値（パソコン・主な期間）
byq = t[(t.vp == "pc") & (t.period == "main")].groupby(["q", "design"]).sec.median().unstack().round(2)
byq.to_csv(os.path.join(R, "median_sec_by_question_pc.csv"))
byq_sp = t[(t.vp == "sp") & (t.period == "main")].groupby(["q", "design"]).sec.median().unstack().round(2)
byq_sp.to_csv(os.path.join(R, "median_sec_by_question_sp.csv"))
fsq = t[(t.period == "main") & t.vp.isin(["pc", "sp"])].groupby(["vp", "q", "design"])["first"].mean().unstack().round(2)
fsq.to_csv(os.path.join(R, "first_screen_by_question.csv"))
# ---- 頑健性
rob = []
def summ(name, df_main, df_x=None, k=BASE, df_sp=None):
    dm = df_main.assign(sec=tsec(df_main, k)).groupby("design").sec.median()
    row = dict(check=name, d1=round(dm["d1"], 2), d2=round(dm["d2"], 2), d3=round(dm["d3"], 2), H1_ratio=round(dm["d3"] / dm["d1"], 3))
    if df_x is not None:
        dx = df_x.assign(sec=tsec(df_x, k)).groupby("design").sec.median(); row["H5_x_ratio"] = round(dx["d3"] / dx["d1"], 3)
    if df_sp is not None:
        ds = df_sp.assign(sec=tsec(df_sp, k)).groupby("design").sec.median(); row["sp_pc_d2"] = round(ds["d2"] / dm["d2"], 3); row["sp_pc_d3"] = round(ds["d3"] / dm["d3"], 3)
    return row
rob.append(summ("基本", sel(), sel(qs=XQ), BASE, sel("sp")))
for nm, ch in [("R1 K=0.2秒", dict(K=0.2)), ("R1 K=0.5秒", dict(K=0.5)), ("R1 探す0.025秒", dict(S=0.025)), ("R1 探す0.1秒", dict(S=0.1)),
               ("R1 読む0.2秒", dict(R=0.2)), ("R1 読む0.6秒", dict(R=0.6)), ("R1 比べる0.5秒", dict(C=0.5))]:
    rob.append(summ(nm, sel(), sel(qs=XQ), {**BASE, **ch}, sel("sp")))
# 計算を暗算（1回＝M×3）にする：計算の K を 0 にして M を足す
# 計算1回の時間を変える（基本は K×15＋M＝5.55秒。足し算は値1つあたり K×7）
# 初めの版は K を0にしたうえで M に CALC×3 を足していたため、もとの M と合わせて M×4 になっていた（レビューで直した）
def mental(df):
    df = df.copy(); df["K"] = 0; df["M"] = df.M + df.CALC * 2; return df  # 計算1回＝M×3
def calc_m(df):
    df = df.copy(); df["K"] = 0; return df  # 計算1回＝M のみ
def calc_0(df):
    df = df.copy(); df["K"] = 0; df["M"] = df.M - df.CALC; return df  # 計算に時間がかからない
rob.append(summ("R1 計算を暗算（M×3）", mental(sel()), mental(sel(qs=XQ)), BASE, mental(sel("sp"))))
rob.append(summ("R1 計算＝M のみ", calc_m(sel()), calc_m(sel(qs=XQ)), BASE, calc_m(sel("sp"))))
rob.append(summ("R1 計算＝0", calc_0(sel()), calc_0(sel(qs=XQ)), BASE, calc_0(sel("sp"))))
for vp in ["pc_s", "pc_l"]:
    rob.append(summ(f"R2 画面 {vp}", sel(vp), sel(vp, qs=XQ)))
rob.append(summ("R3 コロナの時期（パソコン）", sel(per="covid"), sel(per="covid", qs=XQ), BASE, sel("sp", per="covid")))
# R5：D1 のツールチップなし（マウス当て1回を、位置で読む＝読む＋目盛り2つ読む＋考える に置きかえ）
def notip(df):
    df = df.copy(); m = df.design == "d1"; h = df.HOV
    df.loc[m, "P"] = df.loc[m, "P"] - h[m]; df.loc[m, "R"] = df.loc[m, "R"] + 2 * h[m]; df.loc[m, "M"] = df.loc[m, "M"] + h[m]; return df
rob.append(summ("R5 D1 のツールチップなし", notip(sel()), notip(sel(qs=XQ)), BASE, notip(sel("sp"))))
rob = pd.DataFrame(rob); rob.to_csv(os.path.join(R, "robustness.csv"), index=False)
fs_rob = {vp: t[(t.vp == vp) & (t.period == "main") & t.q.isin(MAINQ)].groupby("design")["first"].mean().round(3).to_dict() for vp in ["pc", "sp", "pc_s", "pc_l"]}
fs_rob["covid_pc"] = t[(t.vp == "pc") & (t.period == "covid") & t.q.isin(MAINQ)].groupby("design")["first"].mean().round(3).to_dict()
out["first_screen_by_vp"] = fs_rob
out["R4_misread"] = {f"sigma_{s}": round(misread(s, MAIN).p.mean(), 4) for s in [0.005, 0.015, 0.03]}
out["R4_misread_covid"] = round(misread(0.015, COVID).p.mean(), 4)
out["robustness"] = rob.to_dict(orient="records")
# ---- 問い直し：時間はどの操作から来ているか（パソコン・主な8問）
def decomp(df, k=BASE):
    parts = dict(探す=df.SRCH * k["S"] / 2, スクロール=df.SCR * k["SCR"], マウス当て=(df.HOV) * k["P"],
                 クリック操作=(df.P - df.HOV) * k["P"] + df.B * k["B"], 読む=df.R * k["R"], 比べる=df.C * k["C"],
                 計算=df.K * k["K"] + df.M * k["M"])
    return pd.DataFrame(parts)
dd = []
for (vp, d), g in t[(t.period == "main") & t.vp.isin(["pc", "sp"])].groupby(["vp", "design"]):
    for qset, nm in [(MAINQ, "主な8問"), (XQ, "想定外4問")]:
        gg = g[g.q.isin(qset)]; dp = decomp(gg).mean()
        dd.append(dict(vp=vp, design=d, qset=nm, **dp.round(2).to_dict(), 合計=round(dp.sum(), 2)))
dd = pd.DataFrame(dd); dd.to_csv(os.path.join(R, "reask_decomposition.csv"), index=False)
# 計算を除いた時間（画面で値を直接読める場合だけに近い比べ方）
nocalc = sel().assign(sec=lambda d: tsec(d) - d.K * BASE["K"] - (d.M) * BASE["M"] - d.C * BASE["C"])
out["reask"] = dict(decomp=dd.to_dict(orient="records"),
                    median_sec_pc_without_calc_compare=nocalc.groupby("design").sec.median().round(2).to_dict(),
                    share_tasks_needing_calc=sel().assign(c=lambda d: d.CALC > 0).groupby("design").c.mean().round(3).to_dict(),
                    share_tasks_needing_fallback=t[(t.vp == "pc") & (t.period == "main")].groupby(["design", t.q.isin(XQ)]).FB.apply(lambda s: (s > 0).mean()).round(3).to_dict().__repr__())
# ---- レビューで足した：問いごとの比（中央値の比は、問いごとにほぼ一定の時間の「8つの塊」の間の値になるため）
pq = sel().groupby(["q", "design"]).sec.median().unstack()
rr = (pq["d3"] / pq["d1"])
out["per_question_ratio_d3_d1"] = dict(by_q=rr.round(4).to_dict(), median=round(rr.median(), 4), geomean=round(float(np.exp(np.log(rr).mean())), 4),
    geomean_excl_Q6=round(float(np.exp(np.log(rr.drop("Q6")).mean())), 4), d1_q_sorted=pq["d1"].sort_values().round(2).to_dict())
def ratio_med(df): m = df.groupby("design").sec.median(); return round(m["d3"] / m["d1"], 4)
out["ratio_by_calc"] = dict(base=ratio_med(sel()), calc_M3=ratio_med(mental(sel()).assign(sec=lambda d: tsec(d))),
    calc_M=ratio_med(calc_m(sel()).assign(sec=lambda d: tsec(d))), calc_0=ratio_med(calc_0(sel()).assign(sec=lambda d: tsec(d))))
dq = decomp(sel()[sel().q != "Q6"]).groupby(sel()[sel().q != "Q6"].design).mean()
out["calc_share_excl_Q6"] = (dq["計算"] / dq.sum(axis=1)).round(3).to_dict()
out["q6_share_of_d1_mean"] = round(float(decomp(sel()[(sel().q == "Q6") & (sel().design == "d1")]).sum().sum() / decomp(sel()[sel().design == "d1"]).sum().sum()), 3)
# ---- 問い直し：D3 に「水準」の部分を足した D4 で、想定外の問いの不利と想定内の問いの速さはどう変わるか（結果を見てから足した）
rq = {}
for vp in ["pc", "sp"]:
    for nm, qs in [("main", MAINQ), ("x", XQ)]:
        rq[f"median_{vp}_{nm}"] = t[(t.vp == vp) & (t.period == "main") & t.q.isin(qs)].groupby("design").sec.median().round(2).to_dict()
        rq[f"first_{vp}_{nm}"] = t[(t.vp == vp) & (t.period == "main") & t.q.isin(qs)].groupby("design")["first"].mean().round(3).to_dict()
rq["x_by_q_pc"] = t[(t.vp == "pc") & (t.period == "main") & t.q.isin(XQ)].groupby(["q", "design"]).sec.median().unstack().round(2).to_dict()
out["reask_d4"] = rq
json.dump(out, open(os.path.join(R, "main.json"), "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["tasks", "all_answers_correct", "n_wrong", "H1", "H2", "H3", "H4", "H5", "R4_misread", "first_screen_by_vp"]}, ensure_ascii=False, indent=1, default=float))
print(rob.to_string()); print(byq.to_string()); print(dd.to_string())
