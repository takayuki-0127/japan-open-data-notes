"""主な分析：H1〜H4 と頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
L = pd.read_csv(D / "national_long.csv")
S = pd.read_csv(D / "by_type.csv")
K = pd.read_csv(D / "by_scale_tofuken.csv")
KIBO = ["0.5ha未満", "0.5～1.0", "1.0～1.5", "1.5～2.0", "2.0～3.0", "3.0～5.0", "5.0～7.0", "7.0～10.0", "10.0ha以上"]


def add_shares(d, sfx=""):
    A = d["ag" + sfx] + d["rel" + sfx]
    d["s_farm"] = 100 * A / d["tot" + sfx]
    d["s_off"] = 100 * d["off" + sfx] / d["tot" + sfx]
    d["s_pen"] = 100 * d["pen" + sfx] / d["tot" + sfx]
    d["dep"] = 100 * A / (A + d["off" + sfx])  # 年金を除いた依存度
    return d


def decompose(a0, a1):
    """s=A/T、T=A+O+P。s の変化を A・O・P の変化の寄与に分ける（平均の点での1次の式＋交差の項）。単位はポイント。"""
    A0, O0, P0 = a0; A1, O1, P1 = a1
    T0, T1 = A0 + O0 + P0, A1 + O1 + P1
    Am, Tm = (A0 + A1) / 2, (T0 + T1) / 2
    dA, dO, dP = A1 - A0, O1 - O0, P1 - P0
    cA = 100 * (dA / Tm - Am * dA / Tm ** 2)
    cO = 100 * (-Am * dO / Tm ** 2)
    cP = 100 * (-Am * dP / Tm ** 2)
    total = 100 * (A1 / T1 - A0 / T0)
    return dict(total=total, farm_up=cA, offfarm_down=cO, pension=cP, cross=total - cA - cO - cP,
                dA=dA, dO=dO, dP=dP)


def vec(d, y0, y1, sfx=""):
    g = d.set_index("year")
    f = lambda y: (float(np.mean([g.loc[t, "ag" + sfx] + g.loc[t, "rel" + sfx] for t in y])),
                   float(np.mean([g.loc[t, "off" + sfx] for t in y])), float(np.mean([g.loc[t, "pen" + sfx] for t in y])))
    return f(y0), f(y1)


M = {}
L = add_shares(L)
L.to_csv(R / "national_shares.csv", index=False, float_format="%.4f")
g = L.set_index("year")
M["national"] = {int(y): {"s_farm": float(g.loc[y, "s_farm"]), "s_off": float(g.loc[y, "s_off"]), "s_pen": float(g.loc[y, "s_pen"]),
                          "dep": float(g.loc[y, "dep"]), "tot": float(g.loc[y, "tot"]), "ag_rel": float(g.loc[y, "ag"] + g.loc[y, "rel"]),
                          "off": float(g.loc[y, "off"]), "pen": float(g.loc[y, "pen"])} for y in [2004, 2008, 2014, 2018]}
dec = decompose(*vec(L, [2004], [2018]))
M["H1"] = {"s2004": float(g.loc[2004, "s_farm"]), "s2018": float(g.loc[2018, "s_farm"]), "change": dec["total"]}
M["H1_verdict"] = "支持" if dec["total"] >= 5 else "外れ"
M["H2"] = dec
M["H2_verdict"] = "支持" if dec["offfarm_down"] > dec["farm_up"] else "外れ"
cross_year = int(L[L.pen > L.off].year.min())
M["pension_exceeds_offfarm_first_year"] = cross_year
M["min_s_farm_year"] = int(L.loc[L.s_farm.idxmin(), "year"]); M["min_s_farm"] = float(L.s_farm.min())
M["max_s_farm_year"] = int(L.loc[L.s_farm.idxmax(), "year"]); M["max_s_farm"] = float(L.s_farm.max())

# H3：主副業別
S = add_shares(S)
S.to_csv(R / "by_type_shares.csv", index=False, float_format="%.4f")
p = S.pivot(index="year", columns="type", values="s_farm")
M["H3"] = {t: {"min": float(p[t].min()), "max": float(p[t].max()), "y2004": float(p.loc[2004, t]), "y2018": float(p.loc[2018, t]),
               "min_year": int(p[t].idxmin()), "max_year": int(p[t].idxmax())} for t in ["主業", "準主業", "副業的"]}
M["H3_verdict"] = "支持" if (p["主業"].min() >= 75 and p["副業的"].max() <= 15) else "外れ"
for t in ["主業", "準主業", "副業的"]:
    d = S[S.type == t].set_index("year")
    M["H3"][t]["s_pen_2004"] = float(d.loc[2004, "s_pen"]); M["H3"][t]["s_pen_2018"] = float(d.loc[2018, "s_pen"])
    M["H3"][t]["s_off_2004"] = float(d.loc[2004, "s_off"]); M["H3"][t]["s_off_2018"] = float(d.loc[2018, "s_off"])
    M["H3"][t]["tot_2004"] = float(d.loc[2004, "tot"]); M["H3"][t]["tot_2018"] = float(d.loc[2018, "tot"])
    M["H3"][t]["n_2004"] = int(d.loc[2004, "n"]); M["H3"][t]["n_2018"] = int(d.loc[2018, "n"])

# H4：規模別の5割の線
K = add_shares(K)
K.to_csv(R / "by_scale_shares.csv", index=False, float_format="%.4f")
thr = []
for y, d in K[K.cls != "平均"].groupby("year", sort=True):
    d = d.set_index("cls").loc[KIBO]
    over = [c for c in KIBO if d.loc[c, "s_farm"] > 50]
    first = over[0] if over else None
    # 5割を超えた区分より大きい区分がすべて5割を超えているか
    mono = first is not None and all(d.loc[c, "s_farm"] > 50 for c in KIBO[KIBO.index(first):])
    thr.append(dict(year=y, first_over50=first, idx=KIBO.index(first) if first else None, all_above_after=mono,
                    s_2_3=float(d.loc["2.0～3.0", "s_farm"]), s_3_5=float(d.loc["3.0～5.0", "s_farm"])))
thr = pd.DataFrame(thr)
thr.to_csv(R / "h4_threshold.csv", index=False, float_format="%.4f")
base = KIBO.index("3.0～5.0")
M["H4"] = {"classes": thr.first_over50.value_counts().sort_index().to_dict(), "max_shift": int((thr.idx - base).abs().max())}
M["H4_verdict"] = "支持" if M["H4"]["max_shift"] <= 1 else "外れ"
k18 = K[K.year == 2018].set_index("cls"); k04 = K[K.year == 2004].set_index("cls")
M["scale_2004_2018"] = {c: {"s04": float(k04.loc[c, "s_farm"]), "s18": float(k18.loc[c, "s_farm"]),
                            "pen18": float(k18.loc[c, "s_pen"]), "off18": float(k18.loc[c, "s_off"])} for c in ["平均"] + KIBO}

# 頑健性
rob = []
rob.append(dict(name="主（農業の割合、2004→2018）", change=dec["total"], farm_up=dec["farm_up"], offfarm_down=dec["offfarm_down"], pension=dec["pension"]))
dep = float(g.loc[2018, "dep"] - g.loc[2004, "dep"])
rob.append(dict(name="年金を除いた農業依存度（2004→2018）", change=dep, farm_up=np.nan, offfarm_down=np.nan, pension=np.nan))
d2 = decompose(*vec(L, [2008], [2018]))
rob.append(dict(name="2008→2018（調査の設計の変更のあとだけ）", change=d2["total"], farm_up=d2["farm_up"], offfarm_down=d2["offfarm_down"], pension=d2["pension"]))
d3 = decompose(*vec(L, [2004, 2005, 2006], [2016, 2017, 2018]))
rob.append(dict(name="3年平均（2004〜06→2016〜18）", change=d3["total"], farm_up=d3["farm_up"], offfarm_down=d3["offfarm_down"], pension=d3["pension"]))
La = add_shares(L.copy(), "_alt2007")
rob.append(dict(name="2007年を旧の減価償却の値に（2007年の割合）", change=float(La.set_index("year").loc[2007, "s_farm"] - g.loc[2007, "s_farm"]),
                farm_up=np.nan, offfarm_down=np.nan, pension=np.nan))
pd_ = S.pivot(index="year", columns="type", values="dep")
rob.append(dict(name="H3 を農業依存度で（主業の最小／副業的の最大）", change=np.nan, farm_up=float(pd_["主業"].min()), offfarm_down=float(pd_["副業的"].max()), pension=np.nan))
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False, float_format="%.4f")
M["robustness"] = rob.to_dict("records")
M["dep_2004"] = float(g.loc[2004, "dep"]); M["dep_2018"] = float(g.loc[2018, "dep"])
M["n_2004"] = int(g.loc[2004, "n"]); M["n_2008"] = int(g.loc[2008, "n"]); M["n_2018"] = int(g.loc[2018, "n"])
json.dump(M, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else o)
print(json.dumps({k: M[k] for k in ["H1", "H1_verdict", "H2", "H2_verdict", "H3_verdict", "H4", "H4_verdict", "pension_exceeds_offfarm_first_year"]}, ensure_ascii=False, indent=0))
print(pd.DataFrame(M["H3"]).round(1).to_string()); print(thr.to_string()); print(rob.round(2).to_string())
print(L[["year", "s_farm", "s_off", "s_pen", "dep"]].round(1).to_string())
