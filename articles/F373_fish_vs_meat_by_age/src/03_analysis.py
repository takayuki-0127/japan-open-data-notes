"""03_analysis.py : 生鮮肉÷生鮮魚介の比、逆転の年（全国・年齢別）、同じ世代を追った比を計算する。"""
import json
import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
RES.mkdir(exist_ok=True)
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]


def r3(x):
    return None if x is None or pd.isna(x) else round(float(x), 3)


def cross_year(s):
    """比が1を超え、その後に1以下に戻らない最初の年。最初から超えていれば '<' を付ける。超えなければ None。"""
    s = s.dropna().sort_index()
    above = s > 1
    if not above.iloc[-1]:
        return None
    k = len(above) - 1
    while k > 0 and above.iloc[k - 1]:
        k -= 1
    y = int(s.index[k])
    return f"{y}以前" if k == 0 else str(y)


def main():
    d = pd.read_csv(BASE / "data" / "by_age.csv")
    t = pd.read_csv(BASE / "data" / "national.csv")
    # 全国
    nat = {}
    for farm in ["除く", "含む"]:
        p = t[t.farm_households == farm].pivot_table(index="year", columns="item", values=["amount", "qty_g"])
        r = pd.DataFrame({"amt_ratio": p[("amount", "生鮮肉")] / p[("amount", "生鮮魚介")],
                          "qty_ratio": p[("qty_g", "生鮮肉")] / p[("qty_g", "生鮮魚介")],
                          "amt_ratio_fresh_fish": p[("amount", "生鮮肉")] / p[("amount", "鮮魚")],
                          "qty_ratio_fresh_fish": p[("qty_g", "生鮮肉")] / p[("qty_g", "鮮魚")],
                          "fish_amt": p[("amount", "生鮮魚介")], "meat_amt": p[("amount", "生鮮肉")],
                          "fish_qty": p[("qty_g", "生鮮魚介")], "meat_qty": p[("qty_g", "生鮮肉")]})
        r["farm_households"] = farm
        nat[farm] = r
    natr = pd.concat([nat["除く"], nat["含む"]]).reset_index()
    natr.round(4).to_csv(RES / "national_ratio.csv", index=False)
    inc = nat["含む"]
    # 1999年以前（除く）と2000年以降（含む）をつないだ系列（2000年は含む値）
    joined = pd.concat([nat["除く"][nat["除く"].index < 2000], inc])
    cy = {k: cross_year(joined[k]) for k in ["amt_ratio", "qty_ratio", "amt_ratio_fresh_fish", "qty_ratio_fresh_fish"]}
    # 年齢別
    rows = []
    for (y, a), g in d.groupby(["year", "age"]):
        g = g.set_index("item")
        rows.append({"year": y, "age": a,
                     "amt_ratio": g.loc["生鮮肉", "amount"] / g.loc["生鮮魚介", "amount"],
                     "qty_ratio": g.loc["生鮮肉", "qty_g"] / g.loc["生鮮魚介", "qty_g"],
                     "amt_ratio_fresh_fish": g.loc["生鮮肉", "amount"] / g.loc["鮮魚", "amount"],
                     "fish_amt": g.loc["生鮮魚介", "amount"], "meat_amt": g.loc["生鮮肉", "amount"],
                     "fish_qty": g.loc["生鮮魚介", "qty_g"], "meat_qty": g.loc["生鮮肉", "qty_g"]})
    ar = pd.DataFrame(rows)
    ar["age"] = pd.Categorical(ar["age"], ["平均"] + AGES, ordered=True)
    ar = ar.sort_values(["age", "year"])
    ar.round(4).to_csv(RES / "ratio_by_age.csv", index=False)
    cya = {}
    for a in ["平均"] + AGES:
        s = ar[ar.age == a].set_index("year")
        ma = s[["amt_ratio", "qty_ratio"]].rolling(3, center=True, min_periods=3).mean()
        cya[a] = {"amt": cross_year(s["amt_ratio"]), "qty": cross_year(s["qty_ratio"]),
                  "amt_fresh_fish": cross_year(s["amt_ratio_fresh_fish"]), "amt_ma3": cross_year(ma["amt_ratio"]),
                  "amt_2013": r3(s.loc[2013, "amt_ratio"]), "amt_2025": r3(s.loc[2025, "amt_ratio"]),
                  "qty_2013": r3(s.loc[2013, "qty_ratio"]), "qty_2025": r3(s.loc[2025, "qty_ratio"])}
    pd.DataFrame(cya).T.to_csv(RES / "crossing_by_age.csv")
    # 同じ世代を10年追う（肉÷魚の比、対数の差）
    coh = []
    for t0, t1 in [(2013, 2023), (2014, 2024), (2015, 2025)]:
        for i in range(5):
            a, a1 = AGES[i], AGES[i + 1]
            g = ar.set_index(["year", "age"])
            for var in ["amt_ratio", "qty_ratio"]:
                coh.append({"t0": t0, "t1": t1, "from_age": a, "to_age": a1, "var": var,
                            "r_t0_a": r3(g.loc[(t0, a), var]), "r_t0_a1": r3(g.loc[(t0, a1), var]),
                            "r_t1_a1": r3(g.loc[(t1, a1), var]),
                            "cohort_10y": round(float(np.log(g.loc[(t1, a1), var] / g.loc[(t0, a), var]) * 100), 2),
                            "cross_gap": round(float(np.log(g.loc[(t0, a1), var] / g.loc[(t0, a), var]) * 100), 2),
                            "same_age": round(float(np.log(g.loc[(t1, a1), var] / g.loc[(t0, a1), var]) * 100), 2)})
    coh = pd.DataFrame(coh)
    coh.to_csv(RES / "cohort_ratio.csv", index=False)
    cs = coh[coh.from_age != "60〜69歳"].groupby(["var", "t0"])[["cohort_10y", "cross_gap", "same_age"]].mean().round(2)
    cs.to_csv(RES / "cohort_ratio_summary.csv")

    # 2013→2025年の魚・肉それぞれの変化（年齢別）
    ch = []
    for g in ["平均"] + AGES:
        x0 = ar[(ar.age == g) & (ar.year == 2013)].iloc[0]
        x1 = ar[(ar.age == g) & (ar.year == 2025)].iloc[0]
        ch.append({"age": g, **{f"{k}_pct": round((x1[k] / x0[k] - 1) * 100, 1) for k in ["fish_amt", "meat_amt", "fish_qty", "meat_qty"]},
                   "fish_qty_2013": x0["fish_qty"], "fish_qty_2025": x1["fish_qty"], "meat_qty_2013": x0["meat_qty"], "meat_qty_2025": x1["meat_qty"]})
    ch = pd.DataFrame(ch)
    ch.to_csv(RES / "change_2013_2025.csv", index=False)
    a = cy["amt_ratio"]
    q = cy["qty_ratio"]
    ay = int(a.replace("以前", "")) if a else None
    qy = int(q.replace("以前", "")) if q else None
    up = {g: r3(ar[(ar.age == g) & (ar.year == 2025)].amt_ratio.iloc[0] - ar[(ar.age == g) & (ar.year == 2013)].amt_ratio.iloc[0]) for g in ["平均"] + AGES}
    upq = {g: r3(ar[(ar.age == g) & (ar.year == 2025)].qty_ratio.iloc[0] - ar[(ar.age == g) & (ar.year == 2013)].qty_ratio.iloc[0]) for g in ["平均"] + AGES}
    s70 = ar[ar.age == "70歳以上"].set_index("year")
    res = {
        "national_cross": cy,
        "national_values": {str(y): {k: r3(inc.loc[y, k]) for k in ["fish_amt", "meat_amt", "fish_qty", "meat_qty", "amt_ratio", "qty_ratio"]} for y in [2000, 2005, 2010, 2011, 2012, 2013, 2024, 2025]},
        "price_per_100g": {str(y): {"fish": r3(inc.loc[y, "fish_amt"] / inc.loc[y, "fish_qty"] * 100),
                                    "meat": r3(inc.loc[y, "meat_amt"] / inc.loc[y, "meat_qty"] * 100)} for y in [2000, 2004, 2006, 2010, 2025]},
        "national_1991": {k: r3(nat["除く"].loc[1991, k]) for k in ["fish_amt", "meat_amt", "fish_qty", "meat_qty", "amt_ratio", "qty_ratio"]},
        "national_2000_step": {"除く_amt_ratio": r3(nat["除く"].loc[2000, "amt_ratio"]), "含む_amt_ratio": r3(inc.loc[2000, "amt_ratio"]),
                               "除く_qty_ratio": r3(nat["除く"].loc[2000, "qty_ratio"]), "含む_qty_ratio": r3(inc.loc[2000, "qty_ratio"])},
        "H1": {"cross_year_amount": a, "result": "支持" if ay and "以前" not in a and 2008 <= ay <= 2013 else "外れ"},
        "H2": {"cross_year_qty": q, "gap_years": (ay - qy) if (ay and qy) else None,
               "result": "支持" if (ay and qy and ay - qy >= 5) else "外れ"},
        "H3": {"ratio_70plus_2013": r3(s70.loc[2013, "amt_ratio"]), "cross_70plus": cya["70歳以上"]["amt"],
               "result": "支持" if (s70.loc[2013, "amt_ratio"] < 1 and cya["70歳以上"]["amt"] and "以前" not in cya["70歳以上"]["amt"]) else "外れ"},
        "H4": {"rise_u29": up["29歳以下"], "rise_70plus": up["70歳以上"],
               "result": "支持" if up["70歳以上"] > up["29歳以下"] else "外れ"},
        "rise_amt_2013_2025": up, "rise_qty_2013_2025": upq,
        "crossing_by_age": cya,
        "change_2013_2025": ch.set_index("age").to_dict("index"),
        "log_rise_amt_2013_2025": {g: r3(np.log(ar[(ar.age == g) & (ar.year == 2025)].amt_ratio.iloc[0] / ar[(ar.age == g) & (ar.year == 2013)].amt_ratio.iloc[0]) * 100) for g in ["平均"] + AGES},
        "cohort_summary": {f"{v}_{t}": row for (v, t), row in cs.to_dict("index").items()},
    }
    (RES / "main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
