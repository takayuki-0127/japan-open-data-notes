"""02 整形：年ごとの表に直す。"""
import pathlib
import pandas as pd
B = pathlib.Path(__file__).resolve().parents[1]
R, P = B / "data" / "raw", B / "data" / "processed"
P.mkdir(parents=True, exist_ok=True)
# 気象庁
j = pd.read_csv(R / "jma_amedas_extreme_counts.csv")
rows = {}
for _, r in j.iterrows():
    v = [int(x) for x in r["values_1976_2025"].split()]
    assert len(v) == 50
    rows[r["series"]] = v
jma = pd.DataFrame(rows, index=pd.Index(range(1976, 2026), name="year")).reset_index()
jma.to_csv(P / "jma_counts.csv", index=False)
# 支払保険金（火災保険分、年度合計、実質＝住宅総合デフレーター2025年度=100）
e = pd.read_csv(R / "giaj_events_from_F256.csv")
d = pd.read_csv(R / "deflator_from_F256.csv").set_index("fy")
e = e[e["natural"] == 1].copy()
grp = {"大雨": "大雨", "台風": "台風"}
e["grp"] = e["peril"].map(grp).fillna("その他（雪・ひょう・突風・低気圧）")
base = d.loc[2025, "defl_house"]
e["fire_real_oku"] = e["fire_k"] * 1e3 * base / e["fy"].map(d["defl_house"]) / 1e8
pay = e.pivot_table(index="fy", columns="grp", values="fire_real_oku", aggfunc="sum").reindex(range(2012, 2026)).fillna(0.0)
pay["合計"] = pay.sum(axis=1)
pay.index.name = "fy"
pay.reset_index().to_csv(P / "payouts_fy_real.csv", index=False)
# 住宅物件の全国合計（F272、全契約の2017〜2024年度）
f = pd.read_csv(R / "giroj_fire_pref_from_F272.csv")
f = f[f["scope"] == "全契約"].groupby("fy")[["amount_mil", "prem_k", "claim_k"]].sum()
f["prem_per_mil"] = f["prem_k"] * 1e3 / (f["amount_mil"] * 1e6) * 1e3   # 保険金額1,000円あたりの保険料（円）
f["claim_per_mil"] = f["claim_k"] * 1e3 / (f["amount_mil"] * 1e6) * 1e3
f.reset_index().to_csv(P / "residential_national.csv", index=False)
print(jma.tail(3)); print(pay.round(0)); print(f.round(3))
