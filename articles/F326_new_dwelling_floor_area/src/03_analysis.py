"""03 分析：1戸あたり床面積の推移、構成と種類の中の変化への分解、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
D = pd.read_csv(ROOT / "data" / "starts_by_type.csv")
D = D[D.year >= 1956]  # 1955年以前は戸数・床面積の数え方が違う（表の注）
D["m2_per_unit"] = D.floor_m2 / D.units
W = D.pivot(index="year", columns="type", values="m2_per_unit")
U = D.pivot(index="year", columns="type", values="units")
FOUR = ["持家", "貸家", "給与住宅", "分譲住宅"]
def r(x, n=1): return float(round(float(x), n))

per = W.round(2); per.to_csv(RES / "m2_per_unit_by_type.csv")
share = U[FOUR].div(U[FOUR].sum(axis=1), axis=0) * 100
share.round(2).to_csv(RES / "unit_share_by_type.csv")
LAST = int(W.index.max())

def shift_share(y0, y1, types=FOUR, sym=True):
    s0 = U.loc[y0, types] / U.loc[y0, types].sum(); s1 = U.loc[y1, types] / U.loc[y1, types].sum()
    a0 = W.loc[y0, types]; a1 = W.loc[y1, types]
    tot = (s1 * a1).sum() - (s0 * a0).sum()
    if sym:
        comp = ((s1 - s0) * (a0 + a1) / 2).sum(); within = ((s0 + s1) / 2 * (a1 - a0)).sum()
    else:
        comp = ((s1 - s0) * a0).sum(); within = (s1 * (a1 - a0)).sum()
    by_type = {t: r(((s0[t] + s1[t]) / 2 * (a1[t] - a0[t])), 2) for t in types}
    return tot, comp, within, by_type

M = {}
tot = W["総計"]
peak = int(tot.idxmax())
M["全体"] = {"山の年": peak, "山の値_m2": r(tot[peak]), "最新年": LAST, "最新の値_m2": r(tot[LAST]),
           "山からの変化_%": r((tot[LAST] / tot[peak] - 1) * 100), "1956年_m2": r(tot[1956]),
           **{f"{y}年_m2": r(tot[y]) for y in (1975, 1996, 2006, 2016)}}
M["H1"] = {"判定": "支持" if (peak < 2000 and (tot[LAST] / tot[peak] - 1) * 100 <= -10) else "外れ"}
t_, c_, w_, bt = shift_share(peak, LAST)
M["H2"] = {"全体の変化_m2": r(t_, 2), "構成の寄与_m2": r(c_, 2), "種類の中の寄与_m2": r(w_, 2),
           "構成の割合_%": r(c_ / t_ * 100), "種類ごとの寄与_m2": bt,
           "判定": "支持" if c_ / t_ >= 0.5 else "外れ"}
M["戸数の割合_%"] = {str(y): {t: r(share.loc[y, t]) for t in FOUR} for y in (peak, 1996, 2006, LAST)}
own = W["持家"]; op = int(own.idxmax())
M["H3"] = {"持家の山の年": op, "持家の山_m2": r(own[op]), "持家_最新_m2": r(own[LAST]),
           "変化_%": r((own[LAST] / own[op] - 1) * 100), "判定": "支持" if (own[LAST] / own[op] - 1) * 100 <= -5 else "外れ"}
man = W["分譲マンション"].loc[2000:]; mp = int(man.idxmax())
M["H4"] = {"マンションの山の年_2000年以降": mp, "山_m2": r(man[mp]), "最新_m2": r(man[LAST]),
           "変化_%": r((man[LAST] / man[mp] - 1) * 100), "判定": "支持" if (man[LAST] / man[mp] - 1) * 100 <= -5 else "外れ"}
M["種類ごとの最新_m2"] = {t: r(W.loc[LAST, t]) for t in W.columns}
M["貸家"] = {"山の年": int(W["貸家"].idxmax()), "山_m2": r(W["貸家"].max()), "最新_m2": r(W.loc[LAST, "貸家"])}
M["分譲一戸建"] = {"山の年": int(W["分譲一戸建"].dropna().idxmax()), "山_m2": r(W["分譲一戸建"].max()), "最新_m2": r(W.loc[LAST, "分譲一戸建"])}

# ---- 頑健性
rob = []
for y0 in (1996, 2006):
    t2, c2, w2, _ = shift_share(y0, LAST)
    rob.append((f"{y0}年→{LAST}年", r(t2, 2), r(c2, 2), r(w2, 2), r(c2 / t2 * 100), "支持" if c2 / t2 >= 0.5 else "外れ"))
t3, c3, w3, _ = shift_share(peak, LAST, sym=False)
rob.append(("始めの年の構成を固定", r(t3, 2), r(c3, 2), r(w3, 2), r(c3 / t3 * 100), "支持" if c3 / t3 >= 0.5 else "外れ"))
t4, c4, w4, _ = shift_share(peak, LAST, types=["持家", "貸家", "分譲住宅"])
rob.append(("給与住宅を除く", r(t4, 2), r(c4, 2), r(w4, 2), r(c4 / t4 * 100), "支持" if c4 / t4 >= 0.5 else "外れ"))
# 分譲をマンション・一戸建・その他に分ける（データのある年から）
U2 = U.copy(); A2 = D.pivot(index="year", columns="type", values="floor_m2")
U2["分譲その他"] = U2["分譲住宅"] - U2["分譲マンション"] - U2["分譲一戸建"]; A2["分譲その他"] = A2["分譲住宅"] - A2["分譲マンション"] - A2["分譲一戸建"]
first5 = int(U["分譲マンション"].dropna().index.min())
SIX = ["持家", "貸家", "給与住宅", "分譲マンション", "分譲一戸建", "分譲その他"]
y0 = max(first5, peak)
s0 = U2.loc[y0, SIX] / U2.loc[y0, SIX].sum(); s1 = U2.loc[LAST, SIX] / U2.loc[LAST, SIX].sum()
a0 = A2.loc[y0, SIX] / U2.loc[y0, SIX]; a1 = A2.loc[LAST, SIX] / U2.loc[LAST, SIX]
t5 = (s1 * a1).sum() - (s0 * a0).sum(); c5 = ((s1 - s0) * (a0 + a1) / 2).sum(); w5 = ((s0 + s1) / 2 * (a1 - a0)).sum()
rob.append((f"6区分（分譲を分ける、{y0}年→{LAST}年）", r(t5, 2), r(c5, 2), r(w5, 2), r(c5 / t5 * 100), "支持" if c5 / t5 >= 0.5 else "外れ"))
R = pd.DataFrame(rob, columns=["変えたこと", "全体の変化_m2", "構成の寄与_m2", "種類の中の寄与_m2", "構成の割合_%", "H2"])
R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {row[0]: dict(zip(R.columns[1:], row[1:])) for row in rob}
M["分譲の内訳の始まりの年"] = first5

# ---- 問い直し（結果を見てから足した）：床面積の合計の減少は、戸数の減少と1戸あたりの縮小のどちらが大きいか（対数で分ける）
T = D[D.type == "総計"].set_index("year")
rq = {}
for y0 in (peak, 2006):
    lf = np.log(T.loc[LAST, "floor_m2"] / T.loc[y0, "floor_m2"]); lu = np.log(T.loc[LAST, "units"] / T.loc[y0, "units"])
    rq[f"{y0}→{LAST}"] = {"床面積の合計_変化_%": r((np.exp(lf) - 1) * 100), "戸数_変化_%": r((T.loc[LAST, "units"] / T.loc[y0, "units"] - 1) * 100),
                          "1戸あたり_変化_%": r((tot[LAST] / tot[y0] - 1) * 100),
                          "戸数の減少の割合_%（対数）": r(lu / lf * 100), "1戸あたりの縮小の割合_%（対数）": r((lf - lu) / lf * 100),
                          "床面積の合計_始_万m2": r(T.loc[y0, "floor_m2"] / 1e4, 0), "床面積の合計_終_万m2": r(T.loc[LAST, "floor_m2"] / 1e4, 0),
                          "戸数_始": int(T.loc[y0, "units"]), "戸数_終": int(T.loc[LAST, "units"])}
M["問い直し"] = rq

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps(M, ensure_ascii=False, indent=1))
print(per.loc[[1956, 1966, 1976, 1986, 1996, 2006, 2016, LAST]])
