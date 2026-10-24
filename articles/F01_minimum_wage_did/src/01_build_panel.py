"""県×年パネル（2008〜2025年）を作る → data/panel.csv

- 最低賃金：各年10月前後に改定されるため、暦年平均として「前年度の額×9/12 + 当年度の額×3/12」を使う
- bite（最低賃金の効きやすさ、カイツ指標）：2015年6月時点の最低賃金（2014年度の額）÷ 2015年の短時間労働者の平均時給
- 就業率 = 就業者 ÷ 15歳以上人口、失業率、有効求人数 ÷ 15歳以上人口（求人率）、有効求人倍率
"""
import numpy as np, pandas as pd
from common import RAW, DATA, PREFS


def read_lfs():
    tabs, cur = {}, None
    for line in open(RAW / "lfs_pref_model_estimates.txt", encoding="utf-8"):
        line = line.strip()
        if line.startswith("#T"):
            cur = line.split()[0][1:]; tabs[cur] = []
        elif line and not line.startswith("#") and cur:
            v = line.split(",")
            tabs[cur].append([int(v[0])] + [float(x) for x in v[1:]])
    out = []
    for key, name in [("T1", "pop15"), ("T3", "emp"), ("T6", "unemp_rate")]:
        df = pd.DataFrame(tabs[key], columns=["year"] + PREFS).melt("year", var_name="pref", value_name=name)
        out.append(df.set_index(["pref", "year"]))
    return pd.concat(out, axis=1).reset_index()


def main():
    lfs = read_lfs()
    mw = pd.read_csv(RAW / "minimum_wage_2002_2026.csv")
    mwl = mw.melt("pref", value_vars=[str(y) for y in range(2002, 2027)], var_name="fy", value_name="mw_fy")
    mwl["fy"] = mwl["fy"].astype(int)
    w = mwl.pivot(index="pref", columns="fy", values="mw_fy")
    rows = []
    for p in PREFS:
        for y in range(2003, 2026):
            rows.append({"pref": p, "year": y, "mw": w.loc[p, y - 1] * 9 / 12 + w.loc[p, y] * 3 / 12,
                         "mw_fy": w.loc[p, y]})
    mwy = pd.DataFrame(rows)
    wage = pd.read_csv(RAW / "wage_short_2015.csv", comment="#")
    wage["bite"] = wage["pref"].map(w[2014]) / wage["hourly_wage_yen"]
    jo = pd.read_csv(RAW / "job_openings_pref_annual.csv")
    jo["pref"] = jo["都道府県"].str.replace(r"(都|府|県)$", "", regex=True)
    jo = jo.rename(columns={"年": "year", "有効求人": "openings", "有効求人倍率": "jor"})[["pref", "year", "openings", "jor"]]

    df = lfs.merge(mwy, on=["pref", "year"]).merge(jo, on=["pref", "year"], how="left")
    df = df.merge(wage[["pref", "hourly_wage_yen", "bite"]], on="pref")
    df = df[(df.year >= 2008) & (df.year <= 2025)].copy()
    df["emp_rate"] = df["emp"] / df["pop15"] * 100
    df["openings_rate"] = df["openings"] / (df["pop15"] * 1000) * 100
    df["log_mw"] = np.log(df["mw"])
    df["log_emp"] = np.log(df["emp"])
    med = df.drop_duplicates("pref")["bite"].median()
    df["high_bite"] = (df["bite"] > med).astype(int)
    df["code"] = df["pref"].map({p: i + 1 for i, p in enumerate(PREFS)})
    df = df.sort_values(["code", "year"])
    cols = ["code", "pref", "year", "mw_fy", "mw", "log_mw", "bite", "high_bite", "hourly_wage_yen", "pop15", "emp",
            "emp_rate", "log_emp", "unemp_rate", "openings", "openings_rate", "jor"]
    df[cols].round(6).to_csv(DATA / "panel.csv", index=False)
    print(df.shape, "prefs", df.pref.nunique(), "years", df.year.min(), df.year.max(), "bite median", round(med, 4))
    print(df.drop_duplicates("pref")[["pref", "bite"]].sort_values("bite").iloc[[0, 1, -2, -1]])


if __name__ == "__main__":
    main()
