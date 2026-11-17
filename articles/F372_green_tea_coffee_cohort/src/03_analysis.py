"""03_analysis.py : 同じ世代を10年追う比較、茶飲料の割合、全国の時系列の変化を計算する。"""
import json
import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
RES.mkdir(exist_ok=True)
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]
PAIRS = [(2015, 2025), (2014, 2024), (2013, 2023)]


def r3(x):
    return None if x is None or pd.isna(x) else round(float(x), 3)


def lg(a, b):
    return float(np.log(b / a) * 100)


def cohort_table(d, item, var, t0, t1):
    s = d[(d.item == item)].set_index(["year", "age"])[var]
    rows = []
    for i in range(len(AGES) - 1):
        a, a1 = AGES[i], AGES[i + 1]
        A = lg(s[(t0, a)], s[(t1, a1)])        # 同じ世代の10年
        B = lg(s[(t0, a)], s[(t0, a1)])        # はじめの年の10歳上との差（横断）
        C = lg(s[(t0, a1)], s[(t1, a1)])       # 10歳上の年齢の10年の変化（同じ年齢）
        rows.append({"item": item, "var": var, "t0": t0, "t1": t1, "from_age": a, "to_age": a1,
                     "v_t0_a": s[(t0, a)], "v_t0_a1": s[(t0, a1)], "v_t1_a1": s[(t1, a1)],
                     "cohort_10y": round(A, 2), "cross_gap": round(B, 2), "same_age_change": round(C, 2),
                     "main4": i < 4})
    return pd.DataFrame(rows)


def summarize(ct):
    m = ct[ct.main4]
    return {"mean_cohort": r3(m.cohort_10y.mean()), "mean_cross": r3(m.cross_gap.mean()),
            "mean_same_age": r3(m.same_age_change.mean()),
            "ratio_cohort_to_cross": r3(m.cohort_10y.mean() / m.cross_gap.mean())}


def main():
    d = pd.read_csv(BASE / "data" / "by_age.csv")
    nat = pd.read_csv(BASE / "data" / "national.csv")
    # 問い直し用：茶の合計（緑茶＋茶飲料）と、家で飲む茶・コーヒーの合計（金額）
    w0 = d.pivot_table(index=["year", "age"], columns="item", values="amount", observed=True)
    extra = pd.DataFrame({"茶計": w0["緑茶"] + w0["茶飲料"],
                          "茶とコーヒーの計": w0[["緑茶", "茶飲料", "コーヒー", "コーヒー飲料", "紅茶", "他の茶葉"]].sum(axis=1)})
    extra = extra.stack().rename("amount").reset_index().rename(columns={"level_2": "item"})
    extra["qty_g"] = np.nan
    d = pd.concat([d, extra[["year", "age", "item", "amount", "qty_g"]]], ignore_index=True)
    allc = []
    summ = {}
    for t0, t1 in PAIRS:
        for item, var in [("緑茶", "qty_g"), ("コーヒー", "qty_g"), ("緑茶", "amount"), ("コーヒー", "amount"),
                          ("茶飲料", "amount"), ("コーヒー飲料", "amount"), ("茶計", "amount"),
                          ("茶とコーヒーの計", "amount")]:
            ct = cohort_table(d, item, var, t0, t1)
            allc.append(ct)
            summ[f"{item}_{var}_{t0}_{t1}"] = summarize(ct)
    allc = pd.concat(allc)
    allc.to_csv(RES / "cohort_steps.csv", index=False)
    pd.DataFrame(summ).T.to_csv(RES / "cohort_summary.csv")

    # 同じ年齢の10年の変化（全年齢）
    sa = []
    for t0, t1 in PAIRS:
        for item in ["緑茶", "コーヒー"]:
            s = d[d.item == item].set_index(["year", "age"])["qty_g"]
            for a in ["平均"] + AGES:
                sa.append({"item": item, "t0": t0, "t1": t1, "age": a, "q_t0": s[(t0, a)], "q_t1": s[(t1, a)],
                           "pct": round((s[(t1, a)] / s[(t0, a)] - 1) * 100, 1)})
    sa = pd.DataFrame(sa)
    sa.to_csv(RES / "same_age_change.csv", index=False)

    # 茶飲料の割合（金額）
    w = d[~d.item.isin(["茶計", "茶とコーヒーの計"])].pivot_table(index=["year", "age"], columns="item", values="amount", observed=True).reset_index()
    w["tea_bev_share"] = w["茶飲料"] / (w["茶飲料"] + w["緑茶"]) * 100
    w["coffee_bev_share"] = w["コーヒー飲料"] / (w["コーヒー飲料"] + w["コーヒー"]) * 100
    w["coffee_vs_tea"] = (w["コーヒー"] + w["コーヒー飲料"]) / (w["緑茶"] + w["茶飲料"])
    w["home_drinks"] = w[["緑茶", "茶飲料", "コーヒー", "コーヒー飲料", "紅茶", "他の茶葉"]].sum(axis=1)
    w = w.round(2)
    w.to_csv(RES / "shares_by_age.csv", index=False)

    # 全国の時系列
    def natv(item, y, var="qty_g"):
        return float(nat[(nat.item == item) & (nat.year == y)][var].iloc[0])
    h4 = {}
    for y0 in [2000, 2002, 2005]:
        h4[str(y0)] = {"green_qty_pct": r3((natv("緑茶", 2025) / natv("緑茶", y0) - 1) * 100),
                       "coffee_qty_pct": r3((natv("コーヒー", 2025) / natv("コーヒー", y0) - 1) * 100),
                       "teabev_amt_pct": r3((natv("茶飲料", 2025, "amount") / natv("茶飲料", y0, "amount") - 1) * 100),
                       "coffeebev_amt_pct": r3((natv("コーヒー飲料", 2025, "amount") / natv("コーヒー飲料", y0, "amount") - 1) * 100)}
    # 2024年までで見る（2025年の表の形が違うので）
    h4["2000_to_2024"] = {"green_qty_pct": r3((natv("緑茶", 2024) / natv("緑茶", 2000) - 1) * 100),
                          "coffee_qty_pct": r3((natv("コーヒー", 2024) / natv("コーヒー", 2000) - 1) * 100)}

    # 年齢の傾き（30〜39歳=1）
    slope = []
    for y in [2013, 2014, 2015, 2023, 2024, 2025]:
        for item in ["緑茶", "コーヒー"]:
            s = d[(d.item == item) & (d.year == y)].set_index("age")["qty_g"]
            for a in AGES:
                slope.append({"year": y, "item": item, "age": a, "rel_to_30s": round(s[a] / s["30〜39歳"], 3)})
    pd.DataFrame(slope).to_csv(RES / "age_profile_rel30s.csv", index=False)
    sl = pd.DataFrame(slope)

    g = summ["緑茶_qty_g_2015_2025"]
    c15 = sa[(sa.t0 == 2015)].set_index(["item", "age"])["pct"]
    s25 = w[w.year == 2025].set_index("age")
    res = {
        "H1": {**g, "result": "支持" if g["mean_cohort"] < 0.5 * g["mean_cross"] else "外れ"},
        "H2": {"coffee_qty_60s_pct": r3(c15[("コーヒー", "60〜69歳")]), "coffee_qty_70plus_pct": r3(c15[("コーヒー", "70歳以上")]),
               "result": "支持" if c15[("コーヒー", "60〜69歳")] > 0 and c15[("コーヒー", "70歳以上")] > 0 else "外れ"},
        "H3": {"teabev_share_u29": r3(s25.loc["29歳以下", "tea_bev_share"]), "teabev_share_70plus": r3(s25.loc["70歳以上", "tea_bev_share"]),
               "result": "支持" if s25.loc["29歳以下", "tea_bev_share"] >= 80 and s25.loc["70歳以上", "tea_bev_share"] < 50 else "外れ"},
        "H4": {**h4["2000"], "result": "支持" if h4["2000"]["green_qty_pct"] <= -30 and abs(h4["2000"]["coffee_qty_pct"]) <= 15 else "外れ"},
        "H4_other_start": h4,
        "cohort_summary": summ,
        "same_age_2015_2025": {f"{i}_{a}": r3(v) for (i, a), v in c15.items()},
        "shares_2025": s25[["tea_bev_share", "coffee_bev_share", "coffee_vs_tea", "home_drinks"]].to_dict("index"),
        "shares_2015": w[w.year == 2015].set_index("age")[["tea_bev_share", "coffee_vs_tea", "home_drinks"]].to_dict("index"),
        "age_profile_green_70_vs_30": {str(y): r3(sl[(sl.year == y) & (sl.item == "緑茶") & (sl.age == "70歳以上")]["rel_to_30s"].iloc[0]) for y in [2013, 2014, 2015, 2023, 2024, 2025]},
        "national": {str(y): {i: [natv(i, y, "amount"), None if i in ("茶飲料", "コーヒー飲料") else natv(i, y)] for i in ["緑茶", "コーヒー", "茶飲料", "コーヒー飲料"]} for y in [2000, 2005, 2015, 2024, 2025]},
    }
    (RES / "main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
