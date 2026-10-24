"""二方向固定効果（TWFE）と差の差（DID）→ results/twfe.csv, results/did.csv, results/first_stage.csv

TWFE：y_it = 県効果 + 年効果 + β·log(最低賃金)_it  （県クラスター標準誤差）
  β×ln(1.1) を「最低賃金が10%高いときの y の差」として報告する
DID ：y_it = 県効果 + 年効果 + δ·(bite上位半分の県 × 2016年以降)   （2008〜2019年、コロナ前）
"""
import numpy as np, pandas as pd
from common import panel, fe_ols, RES

OUT = {"emp_rate": "就業率（%pt）", "unemp_rate": "完全失業率（%pt）", "openings_rate": "有効求人÷15歳以上人口（%pt）",
       "log_emp": "就業者数（log）"}
K10 = np.log(1.1)


def twfe_rows(df):
    rows = []
    specs = [("基本（2008–2019）", df[df.year <= 2019], False), ("県別トレンド（2008–2019）", df[df.year <= 2019], True),
             ("基本（2008–2025）", df, False), ("県別トレンド（2008–2025）", df, True),
             ("2020–22年を除く（2008–2025）", df[~df.year.between(2020, 2022)], False)]
    for y, lab in OUT.items():
        for name, d, tr in specs:
            m, dd, _ = fe_ols(d, y, ["log_mw"], trends=tr)
            b, se = m.params["log_mw"], m.bse["log_mw"]
            rows.append({"outcome": y, "outcome_ja": lab, "spec": name, "beta_logmw": b, "se": se,
                         "per10pct": b * K10, "lo95": (b - 1.96 * se) * K10, "hi95": (b + 1.96 * se) * K10,
                         "p": m.pvalues["log_mw"], "n": int(m.nobs)})
    return pd.DataFrame(rows)


def did_rows(df):
    d = df[df.year <= 2019].copy()
    d["treat_post"] = d["high_bite"] * (d["year"] >= 2016)
    rows = []
    for y in ["log_mw"] + list(OUT):
        m, _, _ = fe_ols(d, y, ["treat_post"])
        rows.append({"outcome": y, "delta": m.params["treat_post"], "se": m.bse["treat_post"],
                     "lo95": m.conf_int().loc["treat_post", 0], "hi95": m.conf_int().loc["treat_post", 1],
                     "p": m.pvalues["treat_post"], "n": int(m.nobs), "mde80": 2.8 * m.bse["treat_post"]})
    return pd.DataFrame(rows)


def first_stage(df):
    w = df.pivot(index="pref", columns="year", values="log_mw")
    b = df.drop_duplicates("pref").set_index("pref")
    rows = []
    for a, z in [(2015, 2019), (2019, 2025), (2015, 2025)]:
        g = (w[z] - w[a]) * 100
        for grp, name in [(1, "bite上位半分"), (0, "bite下位半分")]:
            rows.append({"period": f"{a}→{z}", "group": name, "mw_growth_pct": g[b.high_bite == grp].mean()})
        rows.append({"period": f"{a}→{z}", "group": "相関（bite と上昇率）", "mw_growth_pct": np.corrcoef(b.loc[g.index, "bite"], g)[0, 1]})
    return pd.DataFrame(rows)


def main():
    df = panel()
    t = twfe_rows(df); t.round(5).to_csv(RES / "twfe.csv", index=False)
    d = did_rows(df); d.round(5).to_csv(RES / "did.csv", index=False)
    f = first_stage(df); f.round(4).to_csv(RES / "first_stage.csv", index=False)
    pd.set_option("display.width", 200)
    print(t[["outcome", "spec", "per10pct", "lo95", "hi95", "p"]].round(3).to_string())
    print(d.round(4).to_string()); print(f.round(3).to_string())


if __name__ == "__main__":
    main()
