"""JMD の各歳データを、年×年齢（0〜99歳と100歳以上）×男女の表にする"""
import json
import io
import numpy as np
import pandas as pd
from common import RAW, DATA, AGE_MAX


def read_jmd(txt):
    df = pd.read_csv(io.StringIO(txt), sep=r"\s+", skiprows=2)
    df["Age"] = df["Age"].astype(str).str.replace("+", "", regex=False).astype(int)
    for c in ["Female", "Male", "Total"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main():
    b = json.loads((RAW / "f86_jmd_bundle.json").read_text(encoding="utf-8"))
    D = read_jmd(b["jmd"]["Deaths_1x1"])
    E = read_jmd(b["jmd"]["Exposures_1x1"])
    rows = []
    for sex, col in [("男", "Male"), ("女", "Female")]:
        d = D.pivot(index="Year", columns="Age", values=col)
        e = E.pivot(index="Year", columns="Age", values=col)
        dd = d.loc[:, :AGE_MAX].copy(); dd[AGE_MAX + 1] = d.loc[:, AGE_MAX + 1:].sum(axis=1)
        ee = e.loc[:, :AGE_MAX].copy(); ee[AGE_MAX + 1] = e.loc[:, AGE_MAX + 1:].sum(axis=1)
        for y in dd.index:
            for a in dd.columns:
                rows.append((sex, int(y), int(a), dd.loc[y, a], ee.loc[y, a]))
    long = pd.DataFrame(rows, columns=["sex", "year", "age", "deaths", "exposure"])
    long["mx"] = long["deaths"] / long["exposure"]
    long.to_csv(DATA / "mx_long.csv", index=False)
    e0 = pd.read_csv(io.StringIO(b["jmd"]["E0per"]), sep=r"\s+", skiprows=2)
    e0 = e0.rename(columns={"Year": "year", "Female": "女", "Male": "男", "Total": "総数"})
    e0.to_csv(DATA / "e0_jmd.csv", index=False)
    # 社人研の表5-12（平均寿命の公表値と、令和5年推計の仮定値）
    t = pd.read_csv(io.StringIO(b["ipss"]["T0512"]), header=None, dtype=str)
    rec = []
    for _, r in t.iterrows():
        y = str(r[0]).strip()
        if y[:4].isdigit() and len(y) == 4:
            try:
                rec.append((int(y), str(r[1]).strip() if isinstance(r[1], str) else "",
                            float(r[2]), float(r[3]), float(r[9]), float(r[10])))
            except ValueError:
                pass
    ipss = pd.DataFrame(rec, columns=["year", "note", "e0_男", "e0_女", "e65_男", "e65_女"])
    ipss["source"] = np.where(ipss["note"] == "2)", "社人研 令和5年推計（中位）", "生命表")
    ipss.to_csv(DATA / "ipss_e0.csv", index=False)
    print(long.groupby("sex").year.agg(["min", "max"]), len(long))
    print(ipss.tail(6))


if __name__ == "__main__":
    main()
