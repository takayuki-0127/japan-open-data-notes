"""貯蓄率の推移と、世帯の構成を変えた試算。results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
sna = pd.read_csv(D / "sna_household_saving.csv")
lt = pd.read_csv(D / "kakei_longterm.csv").pivot_table(index="year", columns=["type", "item"], values="value")
ba = pd.read_csv(D / "kakei_by_age.csv")


def r(x, k=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


main = {}
S = sna[sna.kind == "可処分所得ベース"].set_index("year")
SA = sna[sna.kind == "調整可処分所得ベース"].set_index("year")
main["sna_saving_rate_pct"] = {str(y): r(S.loc[y, "saving_rate_pct"]) for y in [1994, 2000, 2005, 2010, 2015, 2019, 2020, 2021, 2022, 2023, 2024]}
main["sna_adjusted_saving_rate_pct"] = {str(y): r(SA.loc[y, "saving_rate_pct"]) for y in [1994, 2000, 2024]}
main["sna_change_1994_2024_pt"] = r(S.loc[2024, "saving_rate_pct"] - S.loc[1994, "saving_rate_pct"])
main["sna_change_2000_2024_pt"] = r(S.loc[2024, "saving_rate_pct"] - S.loc[2000, "saving_rate_pct"])
main["sna_consumption_growth_1994_2024_pct"] = r(100 * (S.loc[2024, "consumption_bn"] / S.loc[1994, "consumption_bn"] - 1))
main["sna_income_growth_1994_2024_pct"] = r(100 * ((S.loc[2024, "disposable_income_bn"] + S.loc[2024, "pension_adj_bn"]) / (S.loc[1994, "disposable_income_bn"] + S.loc[1994, "pension_adj_bn"]) - 1))
S[["saving_rate_pct", "consumption_bn", "saving_net_bn", "disposable_income_bn"]].to_csv(R / "sna_series.csv")

# 家計調査：勤労者世帯の黒字率と構成
w = lt["勤労者"]; t = lt["二人以上"]
ser = pd.DataFrame({"worker_surplus_rate_pct": w["黒字率"], "worker_disposable_income": w["可処分所得"],
                    "worker_share_pct": 100 * w["集計世帯数"] / t["集計世帯数"], "head_age_two_plus": t["世帯主の年齢"], "head_age_worker": w["世帯主の年齢"]})
ser.to_csv(R / "kakei_series.csv")
main["worker_surplus_rate_pct"] = {str(y): r(ser.loc[y, "worker_surplus_rate_pct"]) for y in [2000, 2005, 2010, 2015, 2019, 2020, 2025]}
main["worker_share_pct"] = {str(y): r(ser.loc[y, "worker_share_pct"]) for y in [2000, 2005, 2010, 2015, 2019, 2025]}
main["head_age_two_plus"] = {str(y): r(ser.loc[y, "head_age_two_plus"]) for y in [2000, 2025]}

# 2019・2025 の平均（勤労者・無職）
avg = ba[ba.age == "平均"].pivot_table(index=["year", "type"], columns="item", values="value")
def grp(year):
    a = avg.loc[(year, "勤労者")]; j = avg.loc[(year, "無職")]; tt = avg.loc[(year, "二人以上")]
    return {"Yw": a["可処分所得"], "sw": a["黒字率"] / 100, "Yj": j["可処分所得"], "sj": j["黒字率"] / 100,
            "share_w": a["集計世帯数"] / tt["集計世帯数"], "share_j": j["集計世帯数"] / tt["集計世帯数"]}
G = {y: grp(y) for y in (2019, 2025)}
main["groups"] = {str(y): {k: r(v * (100 if k.startswith(("s", "share")) else 1)) for k, v in g.items()} for y, g in G.items()}


def combined(share_w, g, other_rate=None, other_share=None):
    """勤労者と、それ以外（無職の値で代表、または一部を「その他」として別の率）の合わせた黒字率（%）。"""
    nw = 1 - share_w
    if other_rate is None:
        num = share_w * g["Yw"] * g["sw"] + nw * g["Yj"] * g["sj"]
        den = share_w * g["Yw"] + nw * g["Yj"]
    else:
        oj = nw * (1 - other_share); oo = nw * other_share
        num = share_w * g["Yw"] * g["sw"] + oj * g["Yj"] * g["sj"] + oo * g["Yj"] * other_rate
        den = share_w * g["Yw"] + oj * g["Yj"] + oo * g["Yj"]
    return 100 * num / den


sw00, sw25 = ser.loc[2000, "worker_share_pct"] / 100, ser.loc[2025, "worker_share_pct"] / 100
cf = []
for yr in (2025, 2019):
    g = G[yr]
    a0 = combined(sw00, g); a1 = combined(sw25, g)
    cf.append({"rates_year": yr, "variant": "それ以外＝無職の値", "combined_2000_mix": a0, "combined_2025_mix": a1, "change_pt": a1 - a0})
    oth = 1 - g["share_w"] - g["share_j"]; other_share = oth / (1 - g["share_w"])
    b0 = combined(sw00, g, 0.0, other_share); b1 = combined(sw25, g, 0.0, other_share)
    cf.append({"rates_year": yr, "variant": "それ以外の一部（自営など）は0%", "combined_2000_mix": b0, "combined_2025_mix": b1, "change_pt": b1 - b0})
cf = pd.DataFrame(cf)
cf.round(3).to_csv(R / "counterfactual_composition.csv", index=False)
main["counterfactual"] = cf.round(2).to_dict(orient="records")
main["counterfactual_main_change_pt"] = r(cf.iloc[0]["change_pt"], 2)
# 参考：勤労者世帯の黒字率の上がり分を、同じ式に入れたとき（2000年の勤労者の黒字率と2025年の構成…の比較）
g = G[2025]
g00 = dict(g); g00["sw"] = ser.loc[2000, "worker_surplus_rate_pct"] / 100
main["rate_effect_worker_2000_to_2025_pt"] = r(combined(sw25, g) - combined(sw25, g00), 2)

# 年齢別（2025年）の黒字率
age = ba[(ba.year == 2025) & (ba["item"] == "黒字率") & (ba.type.isin(["勤労者", "無職"]))]
age = age[~age.age.str.startswith("(再掲)")]
main["surplus_rate_by_age_2025"] = {f"{t}_{a}": r(v) for t, a, v in age[["type", "age", "value"]].itertuples(index=False)}
age.to_csv(R / "surplus_rate_by_age_2025.csv", index=False)

main["hypotheses"] = {
    "H1": {"2000": main["worker_surplus_rate_pct"]["2000"], "2025": main["worker_surplus_rate_pct"]["2025"], "verdict": "支持" if ser.loc[2025, "worker_surplus_rate_pct"] > ser.loc[2000, "worker_surplus_rate_pct"] else "外れ"},
    "H2": {"change_pt": r(ser.loc[2025, "worker_share_pct"] - ser.loc[2000, "worker_share_pct"]), "verdict": "支持" if ser.loc[2000, "worker_share_pct"] - ser.loc[2025, "worker_share_pct"] >= 5 else "外れ"},
    "H3": {"change_pt": main["counterfactual_main_change_pt"], "verdict": "支持" if main["counterfactual_main_change_pt"] <= -3 else "外れ"},
    "H4": {"change_pt": main["sna_change_1994_2024_pt"], "verdict": "支持" if main["sna_change_1994_2024_pt"] <= -8 else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=0)[:5000])
