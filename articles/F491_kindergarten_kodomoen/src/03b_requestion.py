"""問い直し：公立と私立で、幼稚園からこども園への移り方は違うのか（PLAN の候補の2つ目）。
あわせて、こども園の1号の割合の年ごとの動き（候補の1つ目）を並べる。"""
import importlib.util, json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RAW = os.path.join(DATA, "raw")
RES = os.path.join(HERE, "..", "results")

spec = importlib.util.spec_from_file_location("b", os.path.join(HERE, "02_build.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

n = pd.read_csv(os.path.join(DATA, "national.csv"), index_col=0)
p = pd.read_csv(os.path.join(DATA, "prefecture.csv"), index_col=0)
main = json.load(open(os.path.join(RES, "main.json"), encoding="utf-8"))
cohort = main["cohort"]["ratio_2025_2014"]

rows = []
for lab, sh, col in (("公立", 2, "pub"), ("私立", 3, "pri")):
    k17 = b.pref_cols(os.path.join(RAW, "k17_2025.xlsx"), sh, 0, {"kg35": 1, "kg35_n1": 2, "kg35_n2": 3}).sum()
    kg14, kg25 = n.loc[2014, f"kg_ji_{col}"], n.loc[2025, f"kg_ji_{col}"]
    assert abs(k17["kg35"] - kg25) < 0.5
    ke35, ke35_n1 = p[f"ke2025_35_{col}"].sum(), p[f"ke2025_35_n1_{col}"].sum()
    rows.append({
        "sector": lab,
        "kg_ji_2014": int(kg14), "kg_ji_2025": int(kg25),
        "kg_change_pct": round((kg25 / kg14 - 1) * 100, 1),
        "kg_en_2014": int(n.loc[2014, f"kg_en_{col}"]), "kg_en_2025": int(n.loc[2025, f"kg_en_{col}"]),
        "kg_en_change_pct": round((n.loc[2025, f"kg_en_{col}"] / n.loc[2014, f"kg_en_{col}"] - 1) * 100, 1),
        "ke_en_2025": int(n.loc[2025, f"ke_en_{col}"]),
        "ke35_2025": int(ke35), "ke35_n1_2025": int(ke35_n1),
        "ke_n1_share_pct": round(ke35_n1 / ke35 * 100, 1),
        "kg_n2_share_pct": round(k17["kg35_n2"] / k17["kg35"] * 100, 1),
        # 1号（教育の時間だけ）の子：2014年の幼稚園の在園者を100としたときの2025年の数
        "edu_type_2025_per100_of_2014": round((k17["kg35_n1"] + ke35_n1) / kg14 * 100, 1),
        # 子どもの数の減り（1年生の数の比）で割り戻した値
        "edu_type_cohort_adj": round((k17["kg35_n1"] + ke35_n1) / kg14 / cohort * 100, 1),
    })
sec = pd.DataFrame(rows)
sec.to_csv(os.path.join(RES, "requestion_sector.csv"), index=False)

trend = pd.DataFrame({
    "year": [2023, 2024, 2025],
    "ke35": [int(p[f"ke{y}_35"].sum()) for y in (2023, 2024, 2025)],
    "ke35_n1": [int(p[f"ke{y}_35_n1"].sum()) for y in (2023, 2024, 2025)],
})
trend["n1_share_pct"] = (trend["ke35_n1"] / trend["ke35"] * 100).round(1)
# 都道府県ごとに 2023→2025 の1号の割合が下がったか
d = p["ke2025_35_n1"] / p["ke2025_35"] - p["ke2023_35_n1"] / p["ke2023_35"]
trend.to_csv(os.path.join(RES, "requestion_n1_trend.csv"), index=False)

out = {"sector": {r["sector"]: {k: v for k, v in r.items() if k != "sector"} for r in rows},
       "n1_trend": trend.set_index("year")["n1_share_pct"].to_dict(),
       "prefs_n1_share_down_2023_2025": int((d < 0).sum()),
       "prefs_n1_share_up_2023_2025": int((d > 0).sum()),
       "cohort_ratio_used": cohort}
out["n1_trend"] = {str(k): float(v) for k, v in out["n1_trend"].items()}
with open(os.path.join(RES, "requestion.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
