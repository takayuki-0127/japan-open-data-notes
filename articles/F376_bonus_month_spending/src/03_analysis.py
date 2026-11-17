"""03_analysis.py : ボーナスの月の上乗せ、使う割合（見かけ・限界）、黒字の内訳、品目、頑健性（オフライン）。"""
import json
import numpy as np
import pandas as pd
from common import (RES, YEARS, BONUS, CATS10, SURPLUS_PARTS, load_wide, excess, ols, theil_sen)

ITEMS = ["外食", "酒類", "菓子類", "交際費のうち食料", "洋服", "家庭用耐久財", "交通", "自動車等購入", "通信", "授業料等",
         "教養娯楽用耐久財", "教養娯楽用品", "教養娯楽サービス", "宿泊料", "パック旅行費", "こづかい(使途不明)", "交際費", "贈与金", "仕送り金"]
FLOW = ["実収入", "世帯主の臨時収入・賞与", "非消費支出", "可処分所得", "消費支出", "黒字"]


def r1(x, k=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def shares(E, num="消費支出", den="可処分所得"):
    return E[num].sum() / E[den].sum()


def main():
    w, _ = load_wide()
    cols = FLOW + SURPLUS_PARTS + CATS10 + ITEMS
    E = excess(w, cols)
    E["A_y"] = E["消費支出"] / E["可処分所得"]
    E["bonus_share_of_income"] = E["実収入"] / w.loc[2000:2025, "実収入"].groupby(level=0).sum()
    E.round(4).to_csv(RES / "excess_by_year.csv")

    A = shares(E)
    a0, b, se = ols(E["可処分所得"], E["消費支出"])
    M = {"years": [YEARS[0], YEARS[-1]], "bonus_months": list(BONUS)}
    M["mean_excess_yen_per_year"] = {c: r1(E[c].mean(), 0) for c in FLOW}
    M["A_pooled"] = r1(A, 4)
    M["slope_b"] = r1(b, 4); M["slope_se"] = r1(se, 4); M["intercept_yen"] = r1(a0, 0)
    M["slope_ci95"] = [r1(b - 1.96 * se, 4), r1(b + 1.96 * se, 4)]
    # 季節の分：平均の上乗せ消費のうち切片の占める割合
    M["intercept_share_of_mean_excess_C"] = r1(a0 / E["消費支出"].mean(), 4)
    # 黒字の内訳
    dec = {c: r1(E[c].sum() / E["可処分所得"].sum(), 4) for c in ["消費支出", "黒字"] + SURPLUS_PARTS}
    M["decomp_share_of_excess_Yd"] = dec
    M["decomp_sum_check"] = r1(sum(dec[c] for c in SURPLUS_PARTS) + dec["消費支出"], 4)
    M["deposit_share_of_excess_surplus"] = r1(E["預貯金純増"].sum() / E["黒字"].sum(), 4)
    # 期間
    p1 = E.loc[2000:2009, "A_y"].mean(); p2 = E.loc[2016:2025, "A_y"].mean()
    M["A_y_mean_2000_2009"] = r1(p1, 4); M["A_y_mean_2016_2025"] = r1(p2, 4)
    M["A_y_min"] = {"year": int(E.A_y.idxmin()), "value": r1(E.A_y.min(), 4)}
    M["A_y_max"] = {"year": int(E.A_y.idxmax()), "value": r1(E.A_y.max(), 4)}
    M["excess_Yd_2000"] = r1(E.loc[2000, "可処分所得"], 0); M["excess_Yd_2025"] = r1(E.loc[2025, "可処分所得"], 0)
    M["excess_C_2000"] = r1(E.loc[2000, "消費支出"], 0); M["excess_C_2025"] = r1(E.loc[2025, "消費支出"], 0)
    M["A_2025"] = r1(E.loc[2025, "A_y"], 4)
    M["bonus_share_of_income_2000"] = r1(E.loc[2000, "bonus_share_of_income"], 4)
    M["bonus_share_of_income_2025"] = r1(E.loc[2025, "bonus_share_of_income"], 4)

    # 仮説
    H = {}
    H["H1"] = {"A": M["A_pooled"], "rule": "A<0.50", "result": "支持" if A < 0.5 else "外れ"}
    H["H2"] = {"A": M["A_pooled"], "b": M["slope_b"], "rule": "b < A-0.10", "result": "支持" if b < A - 0.10 else "外れ"}
    loan = dec["土地家屋借金純減"]
    H["H3"] = {"deposit_share_of_surplus": M["deposit_share_of_excess_surplus"], "loan_share_of_Yd": loan,
               "biggest_part": max(SURPLUS_PARTS, key=lambda c: E[c].sum()),
               "rule": "預貯金が黒字の上乗せの最大で半分以上、かつ住宅ローン返済が可処分所得の上乗せの10%以上",
               "result": "支持" if (M["deposit_share_of_excess_surplus"] >= 0.5 and loan >= 0.10 and
                                   max(SURPLUS_PARTS, key=lambda c: E[c].sum()) == "預貯金純増") else "外れ"}
    H["H4"] = {"mean_2000_2009": M["A_y_mean_2000_2009"], "mean_2016_2025": M["A_y_mean_2016_2025"],
               "rule": "後の期間が5ポイント以上低い", "result": "支持" if p2 <= p1 - 0.05 else "外れ"}
    M["hypotheses"] = H

    # 品目：夏（6・7月）と冬（12月）の上乗せ（1年あたり平均、円）と消費の上乗せに占める割合
    rows = []
    Es = excess(w, ["消費支出"] + CATS10 + ITEMS, bonus=(6, 7))
    Ew = excess(w, ["消費支出"] + CATS10 + ITEMS, bonus=(12,))
    for c in CATS10 + ITEMS:
        rows.append({"item": c, "level": "10大費目" if c in CATS10 else "中・小分類",
                     "summer_yen": round(Es[c].mean(), 0), "winter_yen": round(Ew[c].mean(), 0),
                     "all_yen": round(E[c].mean(), 0),
                     "summer_share": round(Es[c].sum() / Es["消費支出"].sum(), 4),
                     "winter_share": round(Ew[c].sum() / Ew["消費支出"].sum(), 4),
                     "all_share": round(E[c].sum() / E["消費支出"].sum(), 4)})
    it = pd.DataFrame(rows)
    it.to_csv(RES / "items_excess.csv", index=False)
    c10 = it[it.level == "10大費目"]
    M["summer_excess_C_yen"] = r1(Es["消費支出"].mean(), 0); M["winter_excess_C_yen"] = r1(Ew["消費支出"].mean(), 0)
    M["top_cats_summer"] = c10.sort_values("summer_yen", ascending=False).head(3)[["item", "summer_yen", "summer_share"]].to_dict("records")
    M["top_cats_winter"] = c10.sort_values("winter_yen", ascending=False).head(3)[["item", "winter_yen", "winter_share"]].to_dict("records")
    sub = it[it.level != "10大費目"]
    M["top_items_summer"] = sub.sort_values("summer_yen", ascending=False).head(5)[["item", "summer_yen", "summer_share"]].to_dict("records")
    M["top_items_winter"] = sub.sort_values("winter_yen", ascending=False).head(5)[["item", "winter_yen", "winter_share"]].to_dict("records")
    # 夏・冬それぞれの見かけの割合
    Es2 = excess(w, ["消費支出", "可処分所得"], bonus=(6, 7)); Ew2 = excess(w, ["消費支出", "可処分所得"], bonus=(12,))
    M["A_summer"] = r1(shares(Es2), 4); M["A_winter"] = r1(shares(Ew2), 4)

    # 頑健性
    rb = []

    def add(name, Ex, note=""):
        A_ = shares(Ex)
        a_, b_, s_ = ols(Ex["可処分所得"], Ex["消費支出"])
        rb.append({"check": name, "A": round(A_, 4), "b": round(b_, 4), "b_se": round(s_, 4), "n_years": len(Ex), "note": note})

    add("基本（9か月の平均を基準、2000〜2025年）", E)
    add("基準を近い月にする", excess(w, ["消費支出", "可処分所得"], base="near"))
    Er = E.copy(); Er["可処分所得"] = E["実収入"]
    add("分母を実収入にする", Er, "A と b は実収入の上乗せに対する割合")
    add("2020・2021年を除く", E.drop([2020, 2021]))
    add("2018年以降だけ", E.loc[2018:2025])
    add("2000〜2017年だけ", E.loc[2000:2017])
    add("夏（6・7月）だけ", Es2)
    add("冬（12月）だけ", Ew2)
    rbd = pd.DataFrame(rb)
    # 傾きの別の出し方
    dE = E[["可処分所得", "消費支出"]].diff().dropna()
    _, b_fd, s_fd = ols(dE["可処分所得"], dE["消費支出"])
    b_ts = theil_sen(E["可処分所得"], E["消費支出"])
    X = np.column_stack([np.ones(len(E)), E["可処分所得"].values, np.arange(len(E), dtype=float)])
    beta, *_ = np.linalg.lstsq(X, E["消費支出"].values, rcond=None)
    res_ = E["消費支出"].values - X @ beta
    cov = (res_ @ res_ / (len(E) - 3)) * np.linalg.inv(X.T @ X)
    b_tr, s_tr = float(beta[1]), float(np.sqrt(cov[1, 1]))
    extra = pd.DataFrame([
        {"check": "傾き：前年との差どうしの回帰", "A": np.nan, "b": round(b_fd, 4), "b_se": round(s_fd, 4), "n_years": len(dE), "note": ""},
        {"check": "傾き：年の直線の傾向を入れた回帰", "A": np.nan, "b": round(b_tr, 4), "b_se": round(s_tr, 4), "n_years": len(E), "note": ""},
        {"check": "傾き：Theil-Sen", "A": np.nan, "b": round(b_ts, 4), "b_se": np.nan, "n_years": len(E), "note": ""},
        {"check": "年ごとの比 A_y の中央値", "A": round(E["A_y"].median(), 4), "b": np.nan, "b_se": np.nan, "n_years": len(E), "note": ""},
    ])
    rbd = pd.concat([rbd, extra], ignore_index=True)
    rbd.to_csv(RES / "robustness.csv", index=False)
    M["robustness"] = [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()} for r in rbd.to_dict("records")]
    # 2026年夏（計画外の参考：年の途中のため基準は1〜5・8〜9月）
    g = w.loc[2026]
    base26 = g.loc[[1, 2, 3, 4, 5, 8, 9]].mean()
    e26 = (g.loc[[6, 7]] - base26).sum()
    M["summer_2026_A"] = r1(e26["消費支出"] / e26["可処分所得"], 4)
    (RES / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(M, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
