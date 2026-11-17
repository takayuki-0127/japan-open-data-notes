"""保有率×保有世帯あたりの額への分解、倍率、頑健性、問い直し。results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
AGES = ["〜29歳", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳〜", "平均"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def wide(df):
    w = df.pivot_table(index=["household", "year", "age"], columns=["group", "item"], values="value", aggfunc="first")
    out = pd.DataFrame(index=w.index)
    out["p"] = w[("holders", "adj_n")] / w[("all", "adj_n")] * 100          # 負債を持つ世帯の割合（%）
    out["D"] = w[("holders", "housing_debt")]                                # 保有世帯あたり 住宅・土地のための負債（万円）
    out["M"] = w[("all", "housing_debt")]                                    # 全世帯の平均（万円）
    out["M_check"] = out["p"] / 100 * out["D"]
    out["D_income"] = w[("holders", "income")]
    out["ratio"] = out["D"] / out["D_income"]                                 # 保有世帯の 負債÷年収（倍）
    out["M_ratio"] = out["M"] / w[("all", "income")]
    out["H_savings"] = w[("holders", "savings")]
    out["H_debt"] = w[("holders", "debt")]
    out["H_net"] = out["H_savings"] - out["H_debt"]
    out["n_holders"] = w[("holders", "n_hh")]
    out["own_rate_all"] = w[("all", "own_rate")]
    out = out.reset_index()
    out["age"] = pd.Categorical(out["age"], AGES, ordered=True)
    return out.sort_values(["household", "age", "year"]).reset_index(drop=True)


def decomp(w, hh, y0, y1, measure="D"):
    rows = []
    for age in AGES:
        s = w[(w.household == hh) & (w.age == age)].set_index("year")
        a = s.loc[y0[0]:y0[1]].mean(numeric_only=True)
        b = s.loc[y1[0]:y1[1]].mean(numeric_only=True)
        dp = 100 * np.log(b["p"] / a["p"])
        if measure == "D":
            dd = 100 * np.log(b["D"] / a["D"])
            dm = 100 * np.log(b["M"] / a["M"])
        else:  # 倍率（年収に対する比）で分ける
            dd = 100 * np.log(b["ratio"] / a["ratio"])
            dm = 100 * np.log(b["M_ratio"] / a["M_ratio"])
        rows.append(dict(household=hh, age=age, start=f"{y0[0]}-{y0[1]}", end=f"{y1[0]}-{y1[1]}", measure=measure,
                         p0=a["p"], p1=b["p"], D0=a["D"], D1=b["D"], M0=a["M"], M1=b["M"],
                         ratio0=a["ratio"], ratio1=b["ratio"], dlogM=dm, dlogP=dp, dlogD=dd,
                         share_D=dd / (dp + dd) if (dp + dd) != 0 else np.nan, D_mult=b["D"] / a["D"]))
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(ROOT / "data" / "panel_long.csv")
    w = wide(df)
    w.round(4).to_csv(RES / "panel_wide.csv", index=False)
    w["gap_pct"] = 100 * (w["M_check"] / w["M"] - 1)

    base = decomp(w, "two_plus", (2008, 2010), (2023, 2025))
    base.round(4).to_csv(RES / "decomposition_main.csv", index=False)
    B = base.set_index("age")

    # 頑健性
    rob = []
    def add(name, d):
        d = d.set_index("age")
        for age in ["30〜39歳", "40〜49歳", "60〜69歳"]:
            x = d.loc[age]
            rob.append(dict(check=name, age=age, p0=r(x.p0, 1), p1=r(x.p1, 1), D_mult=r(x.D_mult, 3),
                            dlogM=r(x.dlogM, 1), dlogP=r(x.dlogP, 1), dlogD=r(x.dlogD, 1), share_D=r(x.share_D, 3),
                            ratio1=r(x.ratio1, 2)))
    add("0 主（二人以上、2008-10→2023-25、金額）", base)
    add("1 勤労者世帯", decomp(w, "workers", (2008, 2010), (2023, 2025)))
    add("2a 単年（2008→2025）", decomp(w, "two_plus", (2008, 2008), (2025, 2025)))
    add("2b 3年平均をずらす（2009-11→2022-24）", decomp(w, "two_plus", (2009, 2011), (2022, 2024)))
    add("4 倍率（年収に対する比）で分ける", decomp(w, "two_plus", (2008, 2010), (2023, 2025), measure="ratio"))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    # 頑健性3：M ≒ p×D の一致
    chk = w[w.age != "平均"].groupby(["household", "age"], observed=True)["gap_pct"].agg(["mean", "min", "max"]).reset_index()
    chk.round(3).to_csv(RES / "identity_check.csv", index=False)
    allgap = w[w.age != "平均"]["gap_pct"].abs()

    # 問い直し：保有世帯の貯蓄と負債（30代・40代）
    rq = w[(w.household == "two_plus") & (w.age.isin(["30〜39歳", "40〜49歳"]))][["year", "age", "H_savings", "H_debt", "H_net", "D_income"]]
    rq.to_csv(RES / "requestion_savings_vs_debt.csv", index=False)
    def avg(age, col, y0, y1):
        s = rq[rq.age == age].set_index("year")[col]
        return float(s.loc[y0:y1].mean())
    rqj = {}
    for age in ["30〜39歳", "40〜49歳"]:
        rqj[age] = dict(savings0=r(avg(age, "H_savings", 2008, 2010), 0), savings1=r(avg(age, "H_savings", 2023, 2025), 0),
                        debt0=r(avg(age, "H_debt", 2008, 2010), 0), debt1=r(avg(age, "H_debt", 2023, 2025), 0),
                        net0=r(avg(age, "H_net", 2008, 2010), 0), net1=r(avg(age, "H_net", 2023, 2025), 0))
        rqj[age]["sav_mult"] = r(rqj[age]["savings1"] / rqj[age]["savings0"], 3)
        rqj[age]["debt_mult"] = r(rqj[age]["debt1"] / rqj[age]["debt0"], 3)
    # 30代：貯蓄が負債の何割か
    for age in rqj:
        rqj[age]["sav_to_debt0"] = r(rqj[age]["savings0"] / rqj[age]["debt0"], 3)
        rqj[age]["sav_to_debt1"] = r(rqj[age]["savings1"] / rqj[age]["debt1"], 3)

    # 仮説の判定
    b30, b40, b60 = B.loc["30〜39歳"], B.loc["40〜49歳"], B.loc["60〜69歳"]
    H = {
        "H1": dict(value=r(b30.D_mult, 3), rule="30代のDが1.5倍以上", verdict="支持" if b30.D_mult >= 1.5 else "外れ"),
        "H2": dict(value={"30〜39歳": [r(b30.dlogD, 1), r(b30.dlogM, 1)], "40〜49歳": [r(b40.dlogD, 1), r(b40.dlogM, 1)]},
                   rule="log D の変化 ≧ log M の変化×0.5（30代・40代とも）",
                   verdict="支持" if (b30.dlogD >= 0.5 * b30.dlogM and b40.dlogD >= 0.5 * b40.dlogM) else "外れ"),
        "H3": dict(value=[r(b60.p0, 1), r(b60.p1, 1)], rule="60代のpが1ポイント以上上がる",
                   verdict="支持" if b60.p1 - b60.p0 >= 1 else "外れ"),
        "H4": dict(value=r(b30.ratio1, 2), rule="30代の倍率が3倍を超える", verdict="支持" if b30.ratio1 > 3 else "外れ"),
    }

    # 年ごとの代表値
    def at(age, y, col, hh="two_plus"):
        return float(w[(w.household == hh) & (w.age == age) & (w.year == y)][col].iloc[0])
    yearly = {age: {str(y): dict(p=r(at(age, y, "p"), 1), D=r(at(age, y, "D"), 0), M=r(at(age, y, "M"), 0),
                                 ratio=r(at(age, y, "ratio"), 2), n=r(at(age, y, "n_holders"), 0))
                    for y in (2008, 2013, 2019, 2025)} for age in AGES}
    main_json = dict(
        hypotheses=H,
        decomposition={age: {k: r(B.loc[age][k], 3) for k in ["p0", "p1", "D0", "D1", "M0", "M1", "ratio0", "ratio1", "dlogM", "dlogP", "dlogD", "share_D", "D_mult"]} for age in AGES},
        yearly=yearly,
        identity_check=dict(max_abs_gap_pct=r(allgap.max(), 2), mean_abs_gap_pct=r(allgap.mean(), 2)),
        requestion=rqj,
        min_n_holders_under30=r(w[(w.household == "two_plus") & (w.age == "〜29歳")]["n_holders"].min(), 0),
        max_n_holders_under30=r(w[(w.household == "two_plus") & (w.age == "〜29歳")]["n_holders"].max(), 0),
    )
    (RES / "main.json").write_text(json.dumps(main_json, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print(chk.to_string())


if __name__ == "__main__":
    main()
