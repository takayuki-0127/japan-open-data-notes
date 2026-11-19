"""年齢の差の推移、70代の伸びの分け方、選択肢の変更の年の伸び、頑健性。結果は results/ へ。"""
import json, pathlib
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
RES.mkdir(exist_ok=True)
df = pd.read_csv(BASE / "data" / "panel.csv")
AGES13 = ["13-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79"]
OLD = ["60-69", "70-79", "80+"]


def r1(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 1)


def wide(col, sex="計", d=df):
    return d[d.sex == sex].pivot(index="year", columns="age", values=col)


def gaps(col, sex="計"):
    w = wide(col, sex)
    g = pd.DataFrame(index=w.index)
    g["gap_20_70"] = w["20-29"] - w["70-79"]
    g["gap_20_80"] = w["20-29"] - w["80+"]
    sub = w[[a for a in AGES13 if a in w.columns]]
    g["gap_max_min_13_79"] = sub.max(axis=1) - sub.min(axis=1)
    return g


main = {}
# 1. 年×年齢の表（計）
for col in ["s", "u_all", "p_all", "p_nona"]:
    w = wide(col)
    w.round(2).to_csv(RES / f"wide_{col}.csv")
g_p = gaps("p_all"); g_s = gaps("s"); g_pn = gaps("p_nona")
gt = pd.concat({"p_all": g_p, "s": g_s, "p_nona": g_pn}, axis=1)
gt.columns = [f"{a}__{b}" for a, b in gt.columns]
gt.round(2).to_csv(RES / "gaps_by_year.csv")

P = wide("p_all"); S = wide("s"); U = wide("u_all")
main["p_all"] = {str(y): {a: r1(P.loc[y, a]) for a in P.columns} for y in [2015, 2019, 2020, 2021, 2025]}
main["s"] = {str(y): {a: r1(S.loc[y, a]) for a in S.columns} for y in [2015, 2019, 2020, 2021, 2025]}
main["u_all"] = {str(y): {a: r1(U.loc[y, a]) for a in U.columns} for y in [2015, 2019, 2020, 2021, 2025]}

# H1 20代と70代の差（人口ベース）
g15, g25 = g_p.loc[2015, "gap_20_70"], g_p.loc[2025, "gap_20_70"]
main["H1"] = {"gap_2015": r1(g15), "gap_2025": r1(g25), "ratio": round(g25 / g15, 3),
              "judge": "支持" if g25 <= g15 / 2 else "外れ"}

# H2 70代の p の伸びを分ける（中点）
def decomp(age, y0, y1, ucol="u_all"):
    w_s, w_u = wide("s"), wide(ucol)
    s0, s1, u0, u1 = w_s.loc[y0, age] / 100, w_s.loc[y1, age] / 100, w_u.loc[y0, age] / 100, w_u.loc[y1, age] / 100
    dp = s1 * u1 - s0 * u0
    part_s = (u0 + u1) / 2 * (s1 - s0)
    part_u = (s0 + s1) / 2 * (u1 - u0)
    return {"dp_pt": round(dp * 100, 1), "part_s_pt": round(part_s * 100, 1), "part_u_pt": round(part_u * 100, 1),
            "share_s": round(part_s / dp, 3)}

main["H2"] = decomp("70-79", 2015, 2025)
main["H2"]["judge"] = "支持" if main["H2"]["share_s"] >= 0.5 else "外れ"
main["H2_other"] = {a: decomp(a, 2015, 2025) for a in ["50-59", "60-69", "80+"]}

# H3 選択肢の変更（2020→2021）
ds = S.diff()
rows = []
for a in S.columns:
    pre = ds.loc[2016:2019, a].mean()
    post = ds.loc[2022:2025, a].mean()
    rows.append({"age": a, "d_2019_2020": ds.loc[2020, a], "d_2020_2021": ds.loc[2021, a],
                 "mean_d_2016_2019": pre, "mean_d_2022_2025": post, "mean_d_around": (pre + post) / 2})
h3 = pd.DataFrame(rows).set_index("age")
h3.round(2).to_csv(RES / "change_year_jumps.csv")
ratio21 = {a: round(h3.loc[a, "d_2020_2021"] / h3.loc[a, "mean_d_around"], 2) for a in OLD}
main["H3"] = {"d_2020_2021": {a: r1(h3.loc[a, "d_2020_2021"]) for a in OLD},
              "mean_d_around": {a: r1(h3.loc[a, "mean_d_around"]) for a in OLD},
              "ratio": ratio21,
              "judge": "支持" if all(v >= 2 for v in ratio21.values()) else "外れ"}

# H4 20代と80歳以上
a15, a25 = g_p.loc[2015, "gap_20_80"], g_p.loc[2025, "gap_20_80"]
main["H4"] = {"gap_2015": r1(a15), "gap_2025": r1(a25), "shrink_pt": r1(a15 - a25),
              "judge": "外れ" if (a15 - a25) >= 10 else "支持"}

# 2019 の「SNS か無料通話アプリのどちらか」の下限
d19 = df[(df.year == 2019) & (df.sex == "計")].set_index("age")
lb = pd.DataFrame({"s_2019": d19["s"], "call_2019": d19["call"], "lower_bound_union_2019": d19[["s", "call"]].max(axis=1),
                   "s_2020": S.loc[2020], "s_2021": S.loc[2021]})
lb.round(2).to_csv(RES / "union_lower_bound_2019.csv")

# おおよそ同じ世代を追う（2015 の a → 2025 の a+10）
nxt = {"13-19": "20-29", "20-29": "30-39", "30-39": "40-49", "40-49": "50-59", "50-59": "60-69", "60-69": "70-79", "70-79": "80+"}
coh = [{"age_2015": a, "age_2025": b, "p_2015": P.loc[2015, a], "p_2025": P.loc[2025, b], "change": P.loc[2025, b] - P.loc[2015, a],
        "same_age_change": P.loc[2025, a] - P.loc[2015, a]} for a, b in nxt.items()]
coh = pd.DataFrame(coh)
coh.round(2).to_csv(RES / "cohort_2015_2025.csv", index=False)
main["cohort"] = {r.age_2015: {"p_2015": r1(r.p_2015), "p_2025": r1(r.p_2025), "change": r1(r.change)} for r in coh.itertuples()}

# 頑健性
rob = []
def add(name, val15, val25, note):
    rob.append({"check": name, "gap_2015": r1(val15), "gap_2025": r1(val25),
                "ratio": round(val25 / val15, 3), "half_or_less": bool(val25 <= val15 / 2), "note": note})
add("主（人口ベース、無回答は使わない側、20代−70代）", g15, g25, "")
add("u を無回答除くにする", g_pn.loc[2015, "gap_20_70"], g_pn.loc[2025, "gap_20_70"], "")
add("利用者ベース s の差", g_s.loc[2015, "gap_20_70"], g_s.loc[2025, "gap_20_70"], "ネットを使う人の中での差")
add("2021→2025年だけ（同じ選択肢）", g_p.loc[2021, "gap_20_70"], g_p.loc[2025, "gap_20_70"], "2015 欄は2021年")
add("差を最大−最小（13〜79歳）にする", g_p.loc[2015, "gap_max_min_13_79"], g_p.loc[2025, "gap_max_min_13_79"], "")
for sx in ["男", "女"]:
    gg = gaps("p_all", sx)
    add(f"{sx}性だけ", gg.loc[2015, "gap_20_70"], gg.loc[2025, "gap_20_70"], "")
add("2013年から（ソーシャルメディア、参考）", g_p.loc[2013, "gap_20_70"], g_p.loc[2025, "gap_20_70"], "2015 欄は2013年。定義が違う")
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rob.to_dict(orient="records")
main["gap_20_70_p_all"] = {str(y): r1(v) for y, v in g_p["gap_20_70"].items()}
main["gap_20_70_s"] = {str(y): r1(v) for y, v in g_s["gap_20_70"].items()}
main["gap_20_80_p_all"] = {str(y): r1(v) for y, v in g_p["gap_20_80"].items()}
main["n_users_2025"] = {a: int(v) for a, v in df[(df.year == 2025) & (df.sex == "計")].set_index("age")["n_users"].items()}

(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4"]}, ensure_ascii=False, indent=1))
print(gt.round(1).to_string())
print(lb.round(1).to_string())
print(coh.round(1).to_string())
print(rob.to_string())
