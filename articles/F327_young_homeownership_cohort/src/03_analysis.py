"""03 分析：年齢×調査年の持ち家率、世代で追う表、仮説、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
D = pd.read_csv(ROOT / "data" / "tenure_by_age.csv")
AGES = ["25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64"]
YEARS = [1978, 1983, 1988, 1993, 1998, 2003, 2008, 2013, 2018, 2023]
def r(x, n=1): return float(round(float(x), n))

D = D[D.year.isin(YEARS) & D.age.isin(AGES)].copy()
D["rate"] = D.owned / (D.owned + D.rented) * 100          # 主：所有の関係「不詳」を除く
D["rate_main"] = D.owned / D["main"] * 100                 # 頑健性：主世帯（不詳を含む）を分母
D["rate_ord"] = D.owned / D["ordinary"] * 100              # 頑健性：普通世帯を分母（2018年まで）
T = D.pivot(index="age", columns="year", values="rate").loc[AGES, YEARS]
T.round(2).to_csv(RES / "rate_age_by_year.csv")
# 世代（生まれ年の近似＝調査年−年齢の中央）
mid = {a: int(a.split("-")[0]) + 2 for a in AGES}
D["cohort"] = D.year - D.age.map(mid)
C = D.pivot(index="cohort", columns="age", values="rate")[AGES]
C.round(2).to_csv(RES / "rate_cohort_by_age.csv")

M = {"年齢別_持ち家率": {a: {str(y): r(T.loc[a, y]) for y in YEARS} for a in AGES}}
d3034 = T.loc["30-34", 2023] - T.loc["30-34", 1983]
M["H1"] = {"30_34_1983": r(T.loc["30-34", 1983]), "30_34_2023": r(T.loc["30-34", 2023]), "差_pt": r(d3034),
           "判定": "支持" if d3034 <= -5 else "外れ"}
# H2：30〜34歳→35〜39歳の伸び（新しい世代：2018年に30〜34歳→2023年に35〜39歳／古い世代：1978→1983年）
g_new = T.loc["35-39", 2023] - T.loc["30-34", 2018]
g_old = T.loc["35-39", 1983] - T.loc["30-34", 1978]
M["H2"] = {"新しい世代_生まれ年": 2018 - 32, "伸び_新_pt": r(g_new), "古い世代_生まれ年": 1978 - 32, "伸び_古_pt": r(g_old),
           "判定": "支持" if g_new > g_old else "外れ"}
# H3：50〜54歳で最も若い世代（2023年に50〜54歳）と30年前（1993年）
d5054 = T.loc["50-54", 2023] - T.loc["50-54", 1993]
M["H3"] = {"50_54_1993": r(T.loc["50-54", 1993]), "50_54_2023": r(T.loc["50-54", 2023]), "差_pt": r(d5054),
           "判定": "支持" if d5054 <= -3 else "外れ"}
d4549 = T.loc["45-49", 2023] - T.loc["45-49", 1983]
M["H4"] = {"差_30_34_pt": r(d3034), "差_45_49_pt": r(d4549), "判定": "支持" if abs(d4549) < abs(d3034) else "外れ"}
# 世代ごとの伸び（5年ごと）
gr = []
for y0, y1 in zip(YEARS[:-1], YEARS[1:]):
    for a0, a1 in zip(AGES[:-1], AGES[1:]):
        gr.append({"世代_生まれ年": y0 - mid[a0], "年齢": f"{a0}→{a1}", "調査年": f"{y0}→{y1}", "伸び_pt": r(T.loc[a1, y1] - T.loc[a0, y0], 2)})
G = pd.DataFrame(gr); G.to_csv(RES / "cohort_growth.csv", index=False)

# ---- 頑健性
rob = []
for lab, col, yrs in [("分母を主世帯（所有の関係の不詳を含む）", "rate_main", YEARS), ("分母を普通世帯（2018年まで）", "rate_ord", YEARS[:-1])]:
    TT = D.pivot(index="age", columns="year", values=col).loc[AGES]
    y1 = yrs[-1]
    rob.append({"変えたこと": lab, "30〜34歳の差": r(TT.loc["30-34", y1] - TT.loc["30-34", 1983]), "比べた年": f"1983→{y1}",
                "45〜49歳の差": r(TT.loc["45-49", y1] - TT.loc["45-49", 1983])})
for base in (1993,):
    rob.append({"変えたこと": f"基準を{base}年に", "30〜34歳の差": r(T.loc["30-34", 2023] - T.loc["30-34", base]), "比べた年": f"{base}→2023",
                "45〜49歳の差": r(T.loc["45-49", 2023] - T.loc["45-49", base])})
for a in ("25-29", "35-39"):
    rob.append({"変えたこと": f"{a}歳で比べる", "30〜34歳の差": r(T.loc[a, 2023] - T.loc[a, 1983]), "比べた年": "1983→2023", "45〜49歳の差": None})
# 2023年の年齢不詳：すべて借家とみなす（下限）／比例配分（＝主の値）
u = pd.read_csv(ROOT / "data" / "tenure_by_age.csv"); u = u[(u.year == 2023)]
unk = u[u.age == "unknown"].iloc[0]; known = u[u.age.isin(AGES)].set_index("age")
w = (known.owned + known.rented) / (known.owned + known.rented).sum()
low = known.owned / (known.owned + known.rented + w * (unk.owned + unk.rented)) * 100
rob.append({"変えたこと": "2023年の年齢不詳を借家として配る（下限）", "30〜34歳の差": r(low["30-34"] - T.loc["30-34", 1983]), "比べた年": "1983→2023",
            "45〜49歳の差": r(low["45-49"] - T.loc["45-49", 1983])})
M["年齢不詳_2023"] = {"主世帯": int(unk["main"]), "持ち家": int(unk.owned), "借家": int(unk.rented),
                      "不詳の持ち家率_%": r(unk.owned / (unk.owned + unk.rented) * 100)}
R = pd.DataFrame(rob); R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {d["変えたこと"]: {k: v for k, v in d.items() if k != "変えたこと"} for d in rob}

# ---- 問い直し（結果を見てから足した）：この15年（2008→2023年）で持ち家率が下がったのはどの年齢か
M["問い直し"] = {"2008_2023_変化_pt": {a: r(T.loc[a, 2023] - T.loc[a, 2008]) for a in AGES},
               "1983_1993_変化_pt": {a: r(T.loc[a, 1993] - T.loc[a, 1983]) for a in AGES},
               "世代比較_1951年ごろ生まれ_対_1971年ごろ生まれ": {a: r(C.loc[1971, a] - C.loc[1951, a]) for a in AGES[:6]}}
gap = pd.DataFrame({"2023年−1983年": T[2023] - T[1983], "2023年−1993年": T[2023] - T[1993]})
gap.index.name = "age"; gap.round(2).to_csv(RES / "gap_by_age.csv")

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps({k: M[k] for k in ["H1", "H2", "H3", "H4", "頑健性", "年齢不詳_2023"]}, ensure_ascii=False, indent=1))
print(T.round(1)); print(C.round(1))
