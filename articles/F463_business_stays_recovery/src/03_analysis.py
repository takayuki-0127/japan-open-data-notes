"""仮説 H1〜H4 と頑健性。結果は results/main.json と表 CSV に書く。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
P = pd.read_csv(D / "stays_by_purpose.csv")
T = pd.read_csv(D / "stays_by_type.csv")
METRO = ["埼玉県", "千葉県", "東京都", "神奈川県", "愛知県", "京都府", "大阪府", "兵庫県"]
P["under50_alloc"] = P.tourism_under50 + P.unknown * P.tourism_under50 / (P.tourism_under50 + P.tourism50plus)
P["plus50_alloc"] = P.tourism50plus + P.unknown * P.tourism50plus / (P.tourism_under50 + P.tourism50plus)
N = P[P.area == "全国"].set_index("year")
N.drop(columns="area").to_csv(R / "national_by_year.csv", float_format="%.0f")


def r3(x):
    return round(float(x), 3)


main = {"source": "観光庁「宿泊旅行統計調査」年の確定値 第2表・第4表・第9表"}
main["national"] = {int(y): {"total_m": round(r.total / 1e6, 2), "under50_m": round(r.tourism_under50 / 1e6, 2), "plus50_m": round(r.tourism50plus / 1e6, 2),
                             "unknown_m": round(r.unknown / 1e6, 2), "under50_alloc_m": round(r.under50_alloc / 1e6, 2)} for y, r in N.iterrows()}
ru = N.loc[2025, "tourism_under50"] / N.loc[2019, "tourism_under50"]
rp = N.loc[2025, "tourism50plus"] / N.loc[2019, "tourism50plus"]
main["H1"] = {"ratio_2025_2019": r3(ru), "result": "当たり" if ru < 1.05 else "外れ"}
main["H2"] = {"under50": r3(ru), "plus50": r3(rp), "total": r3(N.loc[2025, "total"] / N.loc[2019, "total"]), "result": "当たり" if ru < rp else "外れ"}
main["pre_growth_2015_2019"] = {"under50": r3(N.loc[2019, "tourism_under50"] / N.loc[2015, "tourism_under50"]), "plus50": r3(N.loc[2019, "tourism50plus"] / N.loc[2015, "tourism50plus"])}
main["unknown_share"] = {int(y): r3(N.loc[y, "unknown"] / N.loc[y, "total"] * 100) for y in N.index}

# 都道府県
Q = P[P.area != "全国"].copy()
pv = Q.pivot(index="area", columns="year", values="tourism_under50")
pa = Q.pivot(index="area", columns="year", values="under50_alloc")
order = list(dict.fromkeys(Q[Q.year == 2025].area))  # 表の順（北から南）
pref = pd.DataFrame({"under50_2019": pv[2019], "under50_2025": pv[2025], "ratio": pv[2025] / pv[2019],
                     "ratio_alloc": pa[2025] / pa[2019], "ratio_2018": pv[2025] / pv[2018],
                     "unknown_share_2025": Q[Q.year == 2025].set_index("area").eval("unknown / total * 100")}).reindex(order)
pref.index.name = "area"
pref.round(4).to_csv(R / "pref_under50.csv")
nb = int((pref.ratio < 1).sum())
main["H3"] = {"n_below_2019": nb, "n_below_2019_alloc": int((pref.ratio_alloc < 1).sum()), "median_ratio": r3(pref.ratio.median()), "result": "当たり" if nb >= 24 else "外れ"}
m = pref.loc[METRO]; o = pref.drop(METRO)
rm, ro = m.under50_2025.sum() / m.under50_2019.sum(), o.under50_2025.sum() / o.under50_2019.sum()
am = pa.loc[METRO, 2025].sum() / pa.loc[METRO, 2019].sum(); ao = pa.drop(METRO)[2025].sum() / pa.drop(METRO)[2019].sum()
main["H4"] = {"metro8": r3(rm), "other39": r3(ro), "metro8_alloc": r3(am), "other39_alloc": r3(ao), "result": "当たり" if rm < ro else "外れ"}
main["pref_examples"] = {a: {"ratio": r3(pref.loc[a, "ratio"]), "ratio_alloc": r3(pref.loc[a, "ratio_alloc"])} for a in ["北海道", "東京都", "愛知県", "大阪府", "福岡県", "沖縄県"]}

# 頑健性
rob = {}
rob["R1_unknown_allocated"] = {"under50": r3(N.loc[2025, "under50_alloc"] / N.loc[2019, "under50_alloc"]), "plus50": r3(N.loc[2025, "plus50_alloc"] / N.loc[2019, "plus50_alloc"])}
rob["R2_end_year"] = {str(y): {"under50": r3(N.loc[y, "tourism_under50"] / N.loc[2019, "tourism_under50"]), "plus50": r3(N.loc[y, "tourism50plus"] / N.loc[2019, "tourism50plus"]),
                               "under50_alloc": r3(N.loc[y, "under50_alloc"] / N.loc[2019, "under50_alloc"])} for y in (2023, 2024)}
rob["R3_base_2018"] = {"under50": r3(N.loc[2025, "tourism_under50"] / N.loc[2018, "tourism_under50"]), "plus50": r3(N.loc[2025, "tourism50plus"] / N.loc[2018, "tourism50plus"])}
t = T[T.area == "全国"].copy(); t["japanese"] = t.total - t.foreign
tj = t.pivot(index="year", columns="type", values="japanese"); tt = t.pivot(index="year", columns="type", values="total")
tj.round(0).to_csv(R / "japanese_by_type.csv")
rob["R4_business_hotel_japanese"] = {"2019_m": round(tj.loc[2019, "ビジネスホテル"] / 1e6, 2), "2025_m": round(tj.loc[2025, "ビジネスホテル"] / 1e6, 2),
                                     "ratio": r3(tj.loc[2025, "ビジネスホテル"] / tj.loc[2019, "ビジネスホテル"]),
                                     "ratio_2023": r3(tj.loc[2023, "ビジネスホテル"] / tj.loc[2019, "ビジネスホテル"]),
                                     "city_hotel_japanese_ratio": r3(tj.loc[2025, "シティホテル"] / tj.loc[2019, "シティホテル"]),
                                     "type_unknown_2025_m": round((N.loc[2025, "total"] - tt.loc[2025].sum()) / 1e6, 2),
                                     "type_unknown_2019_m": round((N.loc[2019, "total"] - tt.loc[2019].sum()) / 1e6, 2)}
rob["R5_pref_alloc"] = {"n_below_2019": int((pref.ratio_alloc < 1).sum())}
main["robustness"] = rob
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print({k: main[k]["result"] for k in ["H1", "H2", "H3", "H4"]})
