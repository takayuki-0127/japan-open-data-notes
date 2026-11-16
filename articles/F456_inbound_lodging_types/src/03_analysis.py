"""宿泊施設の種類ごとの利用の割合（全体・国籍別）、民泊と滞在日数の関係、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "lodging_stay_long.csv")
W = d.pivot_table(index=["year", "nation"], columns="item", values="share").reset_index()
W["stay7p"] = W[["d7_13", "d14_20", "d21_27", "d28_90", "d91p"]].sum(axis=1)
W["non_hotel_any"] = W[["ryokan", "guesthouse", "capsule", "minpaku"]].sum(axis=1)
N = d[d.item.isin(["d0_3", "d4_6", "d7_13", "d14_20", "d21_27", "d28_90", "d91p"])].groupby(["year", "nation"])["count"].sum()
W = W.set_index(["year", "nation"]); W["n_resp"] = N; W = W.reset_index()
W.to_csv(R / "lodging_by_nation_year.csv", index=False, float_format="%.3f")
nat = sorted([c for c in W.nation.unique() if c not in ("全体", "その他")])
P = lambda col: W.pivot(index="nation", columns="year", values=col)
ho, ry, mi, st = P("hotel"), P("ryokan"), P("minpaku"), P("stay7p")
EA = ["韓国", "台湾", "香港", "中国"]; WEST = ["英国", "ドイツ", "フランス", "イタリア", "スペイン", "米国", "カナダ", "オーストラリア"]
SEA = ["タイ", "シンガポール", "マレーシア", "インドネシア", "フィリピン", "ベトナム", "インド"]
A, B = [2018, 2019], [2023, 2024, 2025]
main = {"overall": {it: {int(y): round(float(P(it).loc["全体", y]), 1) for y in [2018, 2019, 2023, 2024, 2025]} for it in ["hotel", "ryokan", "minpaku", "guesthouse", "capsule", "relatives", "stay7p"]},
        "n_nations": len(nat),
        "n_ryokan_down_19_25": int((ry.loc[nat, 2025] < ry.loc[nat, 2019]).sum()),
        "n_hotel_up_18_25": int((ho.loc[nat, 2025] > ho.loc[nat, 2018]).sum()),
        "minpaku_west_2025": round(float(mi.loc[WEST, 2025].mean()), 1), "minpaku_ea_2025": round(float(mi.loc[EA, 2025].mean()), 1),
        "minpaku_sea_2025": round(float(mi.loc[SEA, 2025].mean()), 1),
        "ryokan_west_2025": round(float(ry.loc[WEST, 2025].mean()), 1), "ryokan_ea_2025": round(float(ry.loc[EA, 2025].mean()), 1),
        "ryokan_west_2019": round(float(ry.loc[WEST, 2019].mean()), 1), "ryokan_ea_2019": round(float(ry.loc[EA, 2019].mean()), 1)}
r, p = stats.pearsonr(st.loc[nat, 2025], mi.loc[nat, 2025]); rs, ps = stats.spearmanr(st.loc[nat, 2025], mi.loc[nat, 2025])
main["corr_stay7_minpaku_2025"] = round(float(r), 3); main["corr_p"] = round(float(p), 4); main["spearman"] = round(float(rs), 3)
main["h2_gap"] = round(main["minpaku_west_2025"] - main["minpaku_ea_2025"], 1)
main["hypotheses"] = {"H1": "支持" if main["n_ryokan_down_19_25"] >= 11 else "外れ", "H2": "支持" if main["h2_gap"] >= 5 else "外れ",
                      "H3": "支持" if r >= 0.5 else "外れ", "H4": "支持" if main["n_hotel_up_18_25"] >= 14 else "外れ"}
tab = pd.DataFrame({"hotel_2018": ho.loc[nat, 2018], "hotel_2025": ho.loc[nat, 2025], "ryokan_2019": ry.loc[nat, 2019], "ryokan_2025": ry.loc[nat, 2025],
                    "minpaku_2019": mi.loc[nat, 2019], "minpaku_2025": mi.loc[nat, 2025], "stay7p_2025": st.loc[nat, 2025]})
tab.to_csv(R / "nation_table.csv", float_format="%.2f")
rb = []
rb.append(dict(check="旅館：2018〜19年平均→2023〜25年平均で下がった国・地域の数", value=int((ry.loc[nat, B].mean(axis=1) < ry.loc[nat, A].mean(axis=1)).sum()), unit=f"/{len(nat)}"))
rb.append(dict(check="ホテル：2018〜19年平均→2023〜25年平均で上がった国・地域の数", value=int((ho.loc[nat, B].mean(axis=1) > ho.loc[nat, A].mean(axis=1)).sum()), unit=f"/{len(nat)}"))
nh = P("non_hotel_any")
rb.append(dict(check="全体の「旅館・ゲストハウス・カプセル・民泊」の合計（上限の目安）2018→2025年", value=round(float(nh.loc["全体", 2025] - nh.loc["全体", 2018]), 1), unit="ポイント"))
Nn = P("n_resp"); big = [c for c in nat if Nn.loc[c].min() >= 300]
rb.append(dict(check=f"回答数が毎年300以上の{len(big)}国・地域だけ：旅館が下がった数（2019→2025年）", value=int((ry.loc[big, 2025] < ry.loc[big, 2019]).sum()), unit=f"/{len(big)}"))
rb.append(dict(check="7日間以上の割合と民泊の割合の順位相関（2025年）", value=main["spearman"], unit="相関係数"))
r19 = stats.pearsonr(st.loc[nat, 2019], mi.loc[nat, 2019])[0]
rb.append(dict(check="同じ相関を2019年で", value=round(float(r19), 3), unit="相関係数"))
rbd = pd.DataFrame(rb); rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = {x.check: x.value for x in rbd.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(tab.round(1).to_string()); print(rbd.to_string())
