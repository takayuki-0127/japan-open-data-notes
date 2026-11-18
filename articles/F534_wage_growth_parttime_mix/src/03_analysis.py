"""平均の組み立て、構成を固定した伸び、年ごとの分解、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "maikin_tl_cy.csv", dtype={"size_code": str, "form_code": str})
Y0, Y1 = 1993, 2025


def panel(size_code, item="cash"):
    x = d[d.size_code == size_code]
    w = x.pivot(index="year", columns="form_code", values=item)
    h = x.pivot(index="year", columns="form_code", values="hours")
    t = x[x.form_code == "0"].set_index("year")
    p = t.part_workers / t.workers
    return pd.DataFrame({"W": w["0"], "Wg": w["1"], "Wp": w["2"], "p": p,
                         "H": h["0"], "Hg": h["1"], "Hp": h["2"]}).sort_index()


def fixed_growth(P, b, e=Y1, hourly=False):
    """基準年 b の割合で固定した平均の、b→e の伸び（%）と公表の伸び（%）"""
    if not hourly:
        pb = P.loc[b, "p"]
        fx = lambda t: (1 - pb) * P.loc[t, "Wg"] + pb * P.loc[t, "Wp"]
        pub = P.loc[e, "W"] / P.loc[b, "W"] - 1
    else:
        # 時間の重み q＝パートの総時間の割合
        q = lambda t: P.loc[t, "p"] * P.loc[t, "Hp"] / ((1 - P.loc[t, "p"]) * P.loc[t, "Hg"] + P.loc[t, "p"] * P.loc[t, "Hp"])
        qb = q(b)
        fx = lambda t: (1 - qb) * P.loc[t, "Wg"] / P.loc[t, "Hg"] + qb * P.loc[t, "Wp"] / P.loc[t, "Hp"]
        pub = (P.loc[e, "W"] / P.loc[e, "H"]) / (P.loc[b, "W"] / P.loc[b, "H"]) - 1
    fixed = fx(e) / fx(b) - 1
    return 100 * fixed, 100 * pub


def decomp(P):
    """年ごとの分解（2時点平均の重み）。値は前年の組み立て平均に対する%"""
    rows = []
    for t in P.index[1:]:
        a, b = P.loc[t - 1], P.loc[t]
        rec0 = (1 - a.p) * a.Wg + a.p * a.Wp
        sg, sp = 1 - (a.p + b.p) / 2, (a.p + b.p) / 2
        within_g = sg * (b.Wg - a.Wg); within_p = sp * (b.Wp - a.Wp)
        comp = (b.p - a.p) * ((a.Wp + b.Wp) / 2 - (a.Wg + b.Wg) / 2)
        rows.append({"year": t, "within_general": 100 * within_g / rec0, "within_part": 100 * within_p / rec0,
                     "composition": 100 * comp / rec0, "total_rec": 100 * (within_g + within_p + comp) / rec0,
                     "published": 100 * (b.W / a.W - 1), "p": b.p})
    return pd.DataFrame(rows)


P5 = panel("T"); P30 = panel("0")
P5["W_rec"] = (1 - P5.p) * P5.Wg + P5.p * P5.Wp
P5["rec_gap_pct"] = 100 * (P5.W_rec / P5.W - 1)
P5.to_csv(R / "panel_5plus.csv", float_format="%.6f", lineterminator="\n")

fx, pub = fixed_growth(P5, Y0)
g_gen = 100 * (P5.loc[Y1, "Wg"] / P5.loc[Y0, "Wg"] - 1)
g_part = 100 * (P5.loc[Y1, "Wp"] / P5.loc[Y0, "Wp"] - 1)
fxh, pubh = fixed_growth(P5, Y0, hourly=True)
dec = decomp(P5)
dec.to_csv(R / "decomp_5plus.csv", index=False, float_format="%.6f", lineterminator="\n")
per = lambda a, b: float(dec[(dec.year >= a) & (dec.year <= b)].composition.mean())

# 指数（1993=100）
idx = pd.DataFrame({"year": P5.index, "published": 100 * P5.W / P5.loc[Y0, "W"],
                    "fixed1993": 100 * ((1 - P5.loc[Y0, "p"]) * P5.Wg + P5.loc[Y0, "p"] * P5.Wp) / ((1 - P5.loc[Y0, "p"]) * P5.loc[Y0, "Wg"] + P5.loc[Y0, "p"] * P5.loc[Y0, "Wp"]),
                    "general": 100 * P5.Wg / P5.loc[Y0, "Wg"], "part": 100 * P5.Wp / P5.loc[Y0, "Wp"]})
idx.to_csv(R / "index_1993.csv", index=False, float_format="%.4f", lineterminator="\n")

main = {
    "period": [Y0, Y1],
    "p_1993": float(P5.loc[Y0, "p"]), "p_2025": float(P5.loc[Y1, "p"]),
    "p_2007": float(P5.loc[2007, "p"]), "p_2013": float(P5.loc[2013, "p"]),
    "W_1993": float(P5.loc[Y0, "W"]), "W_2025": float(P5.loc[Y1, "W"]),
    "Wg_1993": float(P5.loc[Y0, "Wg"]), "Wg_2025": float(P5.loc[Y1, "Wg"]),
    "Wp_1993": float(P5.loc[Y0, "Wp"]), "Wp_2025": float(P5.loc[Y1, "Wp"]),
    "rec_gap_pct_maxabs": float(P5.rec_gap_pct.abs().max()),
    "growth_published": pub, "growth_fixed1993": fx, "drag_pt": fx - pub,
    "growth_general": g_gen, "growth_part": g_part,
    "hourly_growth_published": pubh, "hourly_growth_fixed1993": fxh, "hourly_drag_pt": fxh - pubh,
    "hourly_to_monthly_drag_ratio": (fxh - pubh) / (fx - pub),
    "comp_mean_1994_2007": per(1994, 2007), "comp_mean_2014_2025": per(2014, 2025),
    "comp_mean_2008_2013": per(2008, 2013),
    "comp_sum_1994_2025": float(dec.composition.sum()),
    "years_comp_negative": int((dec.composition < 0).sum()), "n_years": int(len(dec)),
    "max_abs_total_rec_minus_published": float((dec.total_rec - dec.published).abs().max()),
}
# 仮説
main["H1"] = "支持" if main["drag_pt"] >= 5 else "外れ"
main["H2"] = "支持" if main["comp_mean_2014_2025"] > main["comp_mean_1994_2007"] else "外れ"   # 押し下げ（負）が小さい＝値が大きい
main["H3"] = "支持" if g_gen > pub else "外れ"
main["H4"] = "支持" if abs(main["hourly_drag_pt"]) <= abs(main["drag_pt"]) / 2 else "外れ"

# 頑健性
rob = []
def add(name, fx_, pub_):
    rob.append({"check": name, "fixed": fx_, "published": pub_, "drag_pt": fx_ - pub_})
add("本線：5人以上・現金給与総額・1993年固定", fx, pub)
f30, p30 = fixed_growth(P30, Y0); add("30人以上", f30, p30)
Ps = panel("T", "sched"); f, p = fixed_growth(Ps, Y0); add("所定内給与", f, p)
for b in [2000, 2013]:
    f, p = fixed_growth(P5, b); add(f"{b}年固定（{b}→2025年）", f, p)
# 暗黙の割合：公表の平均に合う p
Pi = P5.copy(); Pi["p"] = (Pi.Wg - Pi.W) / (Pi.Wg - Pi.Wp)
f, p = fixed_growth(Pi, Y0); add("割合を公表の平均から逆算", f, p)
main["p_implied_1993"] = float(Pi.loc[Y0, "p"]); main["p_implied_2025"] = float(Pi.loc[Y1, "p"])
add("1時間あたり（時間の割合で固定）", fxh, pubh)
f, p = fixed_growth(P5, Y0, e=2023); add("1993→2023年（2024年の段差を避ける）", f, p)
main["comp_mean_2014_2023"] = per(2014, 2023)
main["comp_2024"] = float(dec[dec.year == 2024].composition.iloc[0]); main["published_2024"] = float(dec[dec.year == 2024].published.iloc[0])
rob = pd.DataFrame(rob); rob.to_csv(R / "robustness.csv", index=False, float_format="%.4f", lineterminator="\n")
main["robustness"] = rob.set_index("check").round(4).to_dict(orient="index")
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in main.items() if k != "robustness"}, ensure_ascii=False, indent=1))
print(rob.round(2).to_string())
