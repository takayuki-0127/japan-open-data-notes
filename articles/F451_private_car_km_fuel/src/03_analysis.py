"""自家用乗用車（ガソリン）の1台あたり走行キロ・燃料、燃料の変化の分解、車種の構成。results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "table1_long.csv")
KINDS = ["普通車", "小型車", "乗用車(ハイブリッド)", "軽自動車"]
EN = {"普通車": "regular", "小型車": "small", "乗用車(ハイブリッド)": "hybrid", "軽自動車": "kei"}


def panel(fuel, kinds):
    p = d[(d.fuel == fuel) & (d.biz == "自家用") & (d.grp == "旅客") & (d.kind.isin(kinds))].copy()
    p["cars"] = p.km_thousand * 1000 / (p.km_per_day * 365)        # 台（延べの平均）
    return p


pc = panel("ガソリン", KINDS)
pc["kind_en"] = pc.kind.map(EN)
tot = pc.groupby("fy")[["fuel_kl", "km_thousand", "cars"]].sum()
tot["km_per_car"] = tot.km_thousand * 1000 / tot.cars                 # km/台/年
tot["l_per_car"] = tot.fuel_kl * 1000 / tot.cars                      # ℓ/台/年
tot["l_per_km"] = tot.fuel_kl / tot.km_thousand                       # ℓ/km
km_share = pc.pivot_table(index="fy", columns="kind_en", values="km_thousand").div(tot.km_thousand, axis=0) * 100
car_share = pc.pivot_table(index="fy", columns="kind_en", values="cars").div(tot.cars, axis=0) * 100
lkm_kind = pc.assign(lkm=pc.fuel_kl / pc.km_thousand).pivot_table(index="fy", columns="kind_en", values="lkm")
kmcar_kind = pc.assign(k=pc.km_per_day * 365).pivot_table(index="fy", columns="kind_en", values="k")
out = tot.join(km_share.add_prefix("kmshare_")).join(car_share.add_prefix("carshare_")).join(lkm_kind.add_prefix("lkm_")).join(kmcar_kind.add_prefix("kmcar_"))
out.to_csv(R / "private_car_gasoline_by_fy.csv", float_format="%.5f")

A, B = [2011, 2012, 2013], [2023, 2024, 2025]
mean = lambda s, ys: float(s.loc[ys].mean())
pct = lambda s, a, b: (mean(s, b) / mean(s, a) - 1) * 100


def decomp(T, a, b):
    """燃料 = 台数 × 1台あたり走行キロ × 1kmあたり燃料。対数の差で分け、合計の%変化に比例配分する。"""
    f = lambda s, ys: np.log(mean(s, ys))
    parts = {"cars": f(T.cars, b) - f(T.cars, a), "km_per_car": f(T.km_per_car, b) - f(T.km_per_car, a), "l_per_km": f(T.l_per_km, b) - f(T.l_per_km, a)}
    total = sum(parts.values()); tp = (np.exp(total) - 1) * 100
    return {k: round(v / total * tp, 2) for k, v in parts.items()} | {"total_pct": round(tp, 2)}


main = {
    "km_per_car_A": round(mean(tot.km_per_car, A)), "km_per_car_B": round(mean(tot.km_per_car, B)),
    "km_per_car_chg": round(pct(tot.km_per_car, A, B), 1),
    "l_per_car_A": round(mean(tot.l_per_car, A)), "l_per_car_B": round(mean(tot.l_per_car, B)),
    "l_per_car_chg": round(pct(tot.l_per_car, A, B), 1),
    "l_per_km_A": round(mean(tot.l_per_km, A), 4), "l_per_km_B": round(mean(tot.l_per_km, B), 4),
    "l_per_km_chg": round(pct(tot.l_per_km, A, B), 1),
    "kmpl_A": round(1 / mean(tot.l_per_km, A), 1), "kmpl_B": round(1 / mean(tot.l_per_km, B), 1),
    "cars_A_million": round(mean(tot.cars, A) / 1e6, 2), "cars_B_million": round(mean(tot.cars, B) / 1e6, 2),
    "cars_chg": round(pct(tot.cars, A, B), 1),
    "fuel_A_bn_l": round(mean(tot.fuel_kl, A) / 1e6, 2), "fuel_B_bn_l": round(mean(tot.fuel_kl, B) / 1e6, 2),
    "decomp": decomp(tot, A, B),
    "kmshare_kei_hv_A": round(mean(km_share.kei + km_share.hybrid, A), 1), "kmshare_kei_hv_B": round(mean(km_share.kei + km_share.hybrid, B), 1),
    "kmshare_A": {k: round(mean(km_share[k], A), 1) for k in km_share}, "kmshare_B": {k: round(mean(km_share[k], B), 1) for k in km_share},
    "lkm_kind_A": {k: round(mean(lkm_kind[k], A), 4) for k in lkm_kind}, "lkm_kind_B": {k: round(mean(lkm_kind[k], B), 4) for k in lkm_kind},
    "kmcar_kind_A": {k: round(mean(kmcar_kind[k], A)) for k in kmcar_kind}, "kmcar_kind_B": {k: round(mean(kmcar_kind[k], B)) for k in kmcar_kind},
    "km_per_car_2019": round(float(tot.km_per_car.loc[2019])), "km_per_car_2020": round(float(tot.km_per_car.loc[2020])),
    "km_per_car_2025": round(float(tot.km_per_car.loc[2025])),
    "km_per_car_1719": round(mean(tot.km_per_car, [2017, 2018, 2019])),
}
# 1kmあたり燃料の変化を、車種の構成（走行キロの割合）と車種の中の改善に分ける（シフトシェア）
sA = pd.Series(main["kmshare_A"]) / 100; sB = pd.Series(main["kmshare_B"]) / 100
lA = pd.Series(main["lkm_kind_A"]); lB = pd.Series(main["lkm_kind_B"])
mix = float(((sB - sA) * (lA + lB) / 2).sum()); within = float(((lB - lA) * (sA + sB) / 2).sum())
main["lkm_shift"] = {"total": round(mix + within, 5), "mix": round(mix, 5), "within": round(within, 5),
                     "mix_share_pct": round(mix / (mix + within) * 100, 1)}
H = main
main["hypotheses"] = {
    "H1": "支持" if H["km_per_car_chg"] <= -5 else "外れ",
    "H2": "支持" if H["l_per_car_chg"] < H["km_per_car_chg"] else "外れ",
    "H3": "支持" if min(H["decomp"], key=lambda k: H["decomp"][k] if k != "total_pct" else 1e9) == "l_per_km" else "外れ",
    "H4": "支持" if H["kmshare_kei_hv_B"] - H["kmshare_kei_hv_A"] >= 10 else "外れ",
}
# 頑健性
rb = []
def addr(name, a, b, T=tot):
    rb.append(dict(check=name, km_per_car_chg=round(pct(T.km_per_car, a, b), 1), l_per_car_chg=round(pct(T.l_per_car, a, b), 1),
                   l_per_km_chg=round(pct(T.l_per_km, a, b), 1), cars_chg=round(pct(T.cars, a, b), 1)))
addr("基本：2011〜13年度平均 → 2023〜25年度平均", A, B)
addr("基準を2011年度の1年にする（→2025年度）", [2011], [2025])
addr("基準を2010年度（参考値）にする（→2025年度）", [2010], [2025])
addr("終わりをコロナ前の2017〜19年度平均にする", A, [2017, 2018, 2019])
pd2 = panel("軽油", ["普通車", "小型車"])
g2 = pd.concat([pc[["fy", "fuel_kl", "km_thousand", "cars"]], pd2[["fy", "fuel_kl", "km_thousand", "cars"]]]).groupby("fy").sum()
g2["km_per_car"] = g2.km_thousand * 1000 / g2.cars; g2["l_per_car"] = g2.fuel_kl * 1000 / g2.cars; g2["l_per_km"] = g2.fuel_kl / g2.km_thousand
addr("軽油の自家用乗用車（普通・小型）を含める", A, B, g2)
rbd = pd.DataFrame(rb)
yrs = np.array(tot.index); 
for col in ["km_per_car", "l_per_car", "l_per_km"]:
    sl = np.polyfit(yrs[yrs >= 2011], np.log(tot[col].loc[2011:]), 1)[0] * 100
    main[f"trend_{col}_pct_per_year"] = round(float(sl), 2)
rbd.loc[len(rbd)] = dict(check="年ごとの傾き（2011〜2025年度、対数の回帰、%/年）", km_per_car_chg=main["trend_km_per_car_pct_per_year"],
                         l_per_car_chg=main["trend_l_per_car_pct_per_year"], l_per_km_chg=main["trend_l_per_km_pct_per_year"], cars_chg=np.nan)
rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = rbd.set_index("check").to_dict(orient="index")
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True, default=float)
print(json.dumps(main, ensure_ascii=False, indent=1, default=float))
print(rbd.to_string())
print(tot.round(3).to_string())
