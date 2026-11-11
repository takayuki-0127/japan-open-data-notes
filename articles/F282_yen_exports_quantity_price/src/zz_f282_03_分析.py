"""03 分析：輸出額の伸びを、数量・構成・契約通貨での値段・為替の換算に分ける（すべて自然対数の差）。"""
import json, pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, R = ROOT / "data" / "processed", ROOT / "results"
R.mkdir(exist_ok=True)
t = pd.read_csv(P / "trade_index.csv", dtype={"period": str})
b = pd.read_csv(P / "boj_monthly.csv", index_col=0)
cs = pd.read_csv(P / "currency_share.csv")
YEN, CC = "PRCG20_2400000000", "PRCG20_2300000000"
CATS = {1: "繊維品", 2: "化学製品", 3: "金属・同製品", 4: "はん用・生産用・業務用機器", 5: "電気・電子機器", 6: "輸送用機器", 7: "その他産品・製品"}
b["year"] = b.index.str[:4].astype(int); b["mon"] = b.index.str[5:7].astype(int)
b["fy"] = np.where(b["mon"] >= 4, b["year"], b["year"] - 1)

def avg(col, y0, y1=None, fy=False):
    k = "fy" if fy else "year"
    return b.loc[b[k] == y0, col].mean()

def tr(area, kind, per):
    r = t[(t.area == area) & (t.kind == kind) & (t.period == str(per))]
    if per == "2020" and kind in ("CY",) and r.empty:
        return dict(V=100.0, Q=100.0, UV=100.0)
    return r.iloc[0][["V", "Q", "UV"]].to_dict()

def decomp(y0, y1, area="WORLD", fy=False):
    kind = "FY" if fy else "CY"
    a, c = tr(area, kind, y0), tr(area, kind, y1)
    dV, dQ, dUV = (np.log(c[k] / a[k]) for k in ("V", "Q", "UV"))
    out = dict(area=area, basis=kind, y0=y0, y1=y1, dV=dV, dQ=dQ, dUV=dUV, resid_index=dV - dQ - dUV,
               V_ratio=c["V"] / a["V"], Q_ratio=c["Q"] / a["Q"], UV_ratio=c["UV"] / a["UV"])
    if area == "WORLD":
        py0, py1 = avg(YEN, y0, fy=fy), avg(YEN, y1, fy=fy)
        pc0, pc1 = avg(CC, y0, fy=fy), avg(CC, y1, fy=fy)
        dPy, dPc = np.log(py1 / py0), np.log(pc1 / pc0)
        out.update(dPyen=dPy, dPcc=dPc, dFX=dPy - dPc, dMix=dUV - dPy,
                   Pyen_ratio=py1 / py0, Pcc_ratio=pc1 / pc0,
                   usdjpy0=avg("FXERM07", y0, fy=fy), usdjpy1=avg("FXERM07", y1, fy=fy),
                   reer0=avg("FX180110002", y0, fy=fy), reer1=avg("FX180110002", y1, fy=fy))
        for k in ("dQ", "dUV", "dPyen", "dPcc", "dFX", "dMix", "resid_index"):
            out["share_" + k] = out[k] / dV
        out["fx_share_of_yenprice"] = out["dFX"] / dPy if dPy != 0 else np.nan
    return out

res = {}
main = decomp(2020, 2025); res["main_2020_2025"] = main
abe = decomp(2012, 2015); res["abe_2012_2015"] = abe
res["H1"] = dict(q_share=main["share_dQ"], verdict="支持" if main["share_dQ"] < 0.25 else "外れ")
res["H1b"] = dict(q_share=abe["share_dQ"], verdict="支持" if abe["share_dQ"] < 1 / 3 else "外れ")
res["H2"] = dict(fx_share=main["fx_share_of_yenprice"], verdict="支持" if main["fx_share_of_yenprice"] >= 0.5 else "外れ")
res["H3"] = dict(pcc_change=main["Pcc_ratio"] - 1, verdict="支持" if main["Pcc_ratio"] - 1 >= 0.05 else "外れ")

# H4：月次、数量指数の前年同月比 vs 実質実効為替レートの前年同月比（0〜12か月前）
m = t[(t.kind == "M") & (t.area == "WORLD")].set_index("period").sort_index()
q = np.log(m["Q"]); qy = (q - q.shift(12)).dropna()
reer = np.log(b["FX180110002"]); ry = (reer - reer.shift(12))
lagc = {}
for L in range(13):
    x = ry.shift(L).reindex(qy.index)
    s = pd.concat([qy, x], axis=1).dropna()
    s = s[(s.index >= "2010-01")]
    lagc[L] = dict(r=float(s.corr().iloc[0, 1]), n=len(s), start=s.index.min(), end=s.index.max())
minr = min(v["r"] for v in lagc.values())
res["H4"] = dict(lags=lagc, min_r=minr, verdict="支持" if minr > -0.3 else "外れ")

# H5：類別
cat = []
for k, nm in CATS.items():
    cy, cc = f"PRCG20_2400{k}20001", f"PRCG20_2300{k}20001"
    py = np.log(avg(cy, 2025) / avg(cy, 2020)); pc = np.log(avg(cc, 2025) / avg(cc, 2020))
    cat.append(dict(cat=nm, dPyen=py, dPcc=pc, dFX=py - pc, Pyen_ratio=np.exp(py), Pcc_ratio=np.exp(pc),
                    fx_share=(py - pc) / py if py else np.nan))
cat = pd.DataFrame(cat); cat.to_csv(R / "C_categories.csv", index=False)
res["H5"] = dict(n_fx_pos=int((cat.dFX > 0).sum()), n_pcc_up=int((cat.dPcc > 0).sum()),
                 verdict="支持" if (cat.dFX > 0).all() and (cat.dPcc > 0).sum() >= 5 else "外れ")

# 頑健性
rob = []
rob.append(dict(name="R0 基本（暦年 2020→2025）", **{k: main[k] for k in ("share_dQ", "fx_share_of_yenprice", "Pcc_ratio", "share_dMix")}))
fyd = decomp(2020, 2025, fy=True)
rob.append(dict(name="R1 年度（2020→2025年度）", **{k: fyd[k] for k in ("share_dQ", "fx_share_of_yenprice", "Pcc_ratio", "share_dMix")}))
b21 = decomp(2021, 2025)
b19 = decomp(2019, 2025)
rob.append(dict(name="R2b 基準を2019年に（コロナ前）", **{k: b19[k] for k in ("share_dQ", "fx_share_of_yenprice", "Pcc_ratio", "share_dMix")}))
res["base2019"] = b19; res["base2021"] = b21; res["fy"] = fyd
rob.append(dict(name="R2 基準を2021年に", **{k: b21[k] for k in ("share_dQ", "fx_share_of_yenprice", "Pcc_ratio", "share_dMix")}))
# R3：為替の換算をドル円 ×（1−円建ての割合）で近似
def yen_share(y):
    s = cs[(cs.area == "WORLD") & (cs.half.str.startswith(str(y)))]
    return s["JPY"].mean() / 100
ys = (yen_share(2020) + yen_share(2025)) / 2
approx = (1 - ys) * np.log(main["usdjpy1"] / main["usdjpy0"])
res["R3"] = dict(yen_share_avg=ys, yen_share_2020=yen_share(2020), yen_share_2025=yen_share(2025),
                 usdjpy0=main["usdjpy0"], usdjpy1=main["usdjpy1"], approx_dFX=approx, boj_dFX=main["dFX"])
rob.append(dict(name="R3 為替の分をドル円×(1−円建て割合)で近似", share_dQ=main["share_dQ"],
                fx_share_of_yenprice=approx / main["dPyen"], Pcc_ratio=np.nan, share_dMix=np.nan))
# R4：3か月平均、地域別の数量
def lagcorr(qs, smooth=1):
    qq = np.log(qs).rolling(smooth).mean(); rr = reer.rolling(smooth).mean()
    qyy = (qq - qq.shift(12)); ryy = (rr - rr.shift(12)); out = {}
    for L in range(13):
        s = pd.concat([qyy, ryy.shift(L).reindex(qyy.index)], axis=1).dropna(); s = s[s.index >= "2010-01"]
        out[L] = float(s.corr().iloc[0, 1])
    return out
r4 = {"WORLD_3mma": lagcorr(m["Q"], 3)}
for ar in ("USA", "CHINA", "ASIA", "EU"):
    mm = t[(t.kind == "M") & (t.area == ar)].set_index("period").sort_index()
    r4[ar] = lagcorr(mm["Q"])
res["R4"] = {k: dict(min_r=min(v.values()), lag_at_min=min(v, key=v.get), max_r=max(v.values())) for k, v in r4.items()}
# 2010-01〜2019-12 だけ（コロナ・半導体不足の前）
qq = q; s_pre = {}
for L in range(13):
    s = pd.concat([qy, ry.shift(L).reindex(qy.index)], axis=1).dropna(); s = s[(s.index >= "2010-01") & (s.index <= "2019-12")]
    s_pre[L] = float(s.corr().iloc[0, 1])
res["R4"]["WORLD_2010_2019"] = dict(min_r=min(s_pre.values()), lag_at_min=min(s_pre, key=s_pre.get), max_r=max(s_pre.values()))
# R5：地域別の分解（数量と価格指数のみ）
area_rows = [decomp(2020, 2025, area=a) for a in ("WORLD", "USA", "EU", "ASIA", "CHINA", "ASEAN", "ASIA NIES")]
ar = pd.DataFrame(area_rows)[["area", "V_ratio", "Q_ratio", "UV_ratio", "dV", "dQ", "dUV"]]
ar["share_dQ"] = ar.dQ / ar.dV; ar.to_csv(R / "B_areas_2020_2025.csv", index=False)
res["R5"] = ar.set_index("area")[["V_ratio", "Q_ratio", "UV_ratio", "share_dQ"]].to_dict(orient="index")
pd.DataFrame(rob).to_csv(R / "D_robustness.csv", index=False)

# 期間ごとの分解（年次の連続）と、2026年1〜9月
yrs = []
for y in range(2006, 2026):
    try:
        d = decomp(y - 1, y); yrs.append(dict(year=y, dV=d["dV"], dQ=d["dQ"], dMix=d["dMix"], dPcc=d["dPcc"], dFX=d["dFX"], resid=d["resid_index"]))
    except Exception as e:
        pass
yrs = pd.DataFrame(yrs); yrs.to_csv(R / "A_yearly_decomp.csv", index=False)
mw = m.copy(); mw["y"] = mw.index.str[:4].astype(int); mw["mo"] = mw.index.str[5:].astype(int)
def ytd(y, upto=9):
    s = mw[(mw.y == y) & (mw.mo <= upto)]; return s[["V", "Q", "UV"]].mean()
a, c = ytd(2025), ytd(2026)
bb = b[(b.mon <= 9)]
py = np.log(bb.loc[bb.year == 2026, YEN].mean() / bb.loc[bb.year == 2025, YEN].mean())
pc = np.log(bb.loc[bb.year == 2026, CC].mean() / bb.loc[bb.year == 2025, CC].mean())
dV = np.log(c.V / a.V); dQ = np.log(c.Q / a.Q); dUV = np.log(c.UV / a.UV)
res["ytd_2026_vs_2025_JanSep"] = dict(V_ratio=c.V / a.V, Q_ratio=c.Q / a.Q, UV_ratio=c.UV / a.UV, dV=dV, dQ=dQ, dUV=dUV,
    dPyen=py, dPcc=pc, dFX=py - pc, dMix=dUV - py, share_dQ=dQ / dV, fx_share_of_yenprice=(py - pc) / py,
    usdjpy_2025=bb.loc[bb.year == 2025, "FXERM07"].mean(), usdjpy_2026=bb.loc[bb.year == 2026, "FXERM07"].mean())
# 月次の分解（図のため）：2020年平均を100とした水準
mm = m[["V", "Q", "UV"]].copy()
mm["Pyen"] = b[YEN].reindex(mm.index); mm["Pcc"] = b[CC].reindex(mm.index); mm["usdjpy"] = b["FXERM07"].reindex(mm.index); mm["reer"] = b["FX180110002"].reindex(mm.index)
mm.to_csv(R / "E_monthly_panel.csv")
json.dump(res, open(R / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
def p(x): return f"{100*x:.1f}%"
print("MAIN 2020→2025: V x%.3f Q x%.3f UV x%.3f | Pyen x%.3f Pcc x%.3f" % (main["V_ratio"], main["Q_ratio"], main["UV_ratio"], main["Pyen_ratio"], main["Pcc_ratio"]))
print(" shares of dV: Q", p(main["share_dQ"]), "Mix", p(main["share_dMix"]), "Pcc", p(main["share_dPcc"]), "FX", p(main["share_dFX"]), "resid", p(main["share_resid_index"]), "| FX of yen price", p(main["fx_share_of_yenprice"]))
print("ABE 2012→2015: V x%.3f Q x%.3f UV x%.3f | Pyen x%.3f Pcc x%.3f" % (abe["V_ratio"], abe["Q_ratio"], abe["UV_ratio"], abe["Pyen_ratio"], abe["Pcc_ratio"]))
print(" shares: Q", p(abe["share_dQ"]), "Mix", p(abe["share_dMix"]), "Pcc", p(abe["share_dPcc"]), "FX", p(abe["share_dFX"]), "| FX of yen price", p(abe["fx_share_of_yenprice"]))
for h in ("H1", "H1b", "H2", "H3", "H5"): print(h, res[h])
print("H4 min r", round(minr, 3), res["H4"]["verdict"], {L: round(v["r"], 2) for L, v in lagc.items()}, lagc[0]["n"])
print(cat.round(3).to_string())
print(pd.DataFrame(rob).round(3).to_string())
print("R3", {k: round(v, 3) for k, v in res["R3"].items()})
print("R4", res["R4"])
print(ar.round(3).to_string())
print("2026 YTD", {k: round(v, 3) for k, v in res["ytd_2026_vs_2025_JanSep"].items()})
print(yrs.round(3).to_string())
