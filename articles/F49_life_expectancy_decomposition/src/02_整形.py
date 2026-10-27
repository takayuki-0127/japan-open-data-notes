"""JSON の CSV を、年×都道府県×男女×年齢（各歳）の表にする。"""
import json, re
import pandas as pd
from common import RAW, DATA, PREF

AGE_OPEN = re.compile(r"^(\d+)[-－]")


def parse(csv):
    rows = []
    started = False
    for line in csv.splitlines():
        c = [s.strip() for s in line.split(",")]
        if not c or not c[0]:
            continue
        a = c[0].replace("（", "(").replace("）", ")")
        if a.startswith("0(年)"):
            started = True
            age, op = 0, False
        elif not started:
            continue
        else:
            m = AGE_OPEN.match(a)
            if m:
                age, op = int(m.group(1)), True
            elif a.isdigit():
                age, op = int(a), False
            else:
                continue
        vals = [float(x) for x in c[1:7]]
        rows.append(dict(age=age, open=op, qx=vals[0], lx=vals[1], dx=vals[2], Lx=vals[3], Tx=vals[4], ex=vals[5]))
        if op:
            break
    return pd.DataFrame(rows)


def main():
    lt = json.load(open(RAW / "f49_lifetables.json", encoding="utf-8"))["lt"]
    out = []
    for key, v in lt.items():
        y, k = key.split("_")
        lab = v["lab"]
        if not (lab.endswith(" 男") or lab.endswith(" 女")):
            continue
        code = int(k[:2])
        if code > 47:
            continue
        sex = "男" if lab.endswith("男") else "女"
        d = parse(v["csv"])
        d["year"] = int(y)
        d["pref_code"] = code
        d["pref"] = "全国" if code == 0 else PREF[code - 1]
        d["sex"] = sex
        out.append(d)
    df = pd.concat(out, ignore_index=True)
    df = df[["year", "pref_code", "pref", "sex", "age", "open", "qx", "lx", "dx", "Lx", "Tx", "ex"]]
    df.sort_values(["year", "pref_code", "sex", "age"]).to_csv(DATA / "lifetables.csv", index=False)
    chk = df.groupby(["year", "sex"]).pref_code.nunique()
    print(chk.to_string())
    print(df.groupby("year").age.max().to_string())

    # 付録80000：平均寿命の年次推移
    t = lt["2020_80000"]["csv"].splitlines()
    head = None
    recs = []
    sex = None
    years = [1921, 1926, 1935, 1947, 1948, 1950, 1954, 1959, 1965, 1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005,
             2010, 2015, 2020]
    for line in t:
        c = [s.strip() for s in line.split(",")]
        if c[0] in ("男", "女"):
            sex = c[0]
            continue
        name = c[0].replace("　", "").replace(" ", "")
        if sex and name and (name == "全国" or name in PREF):
            for yy, val in zip(years, c[1:21]):
                try:
                    recs.append(dict(sex=sex, pref=name, year=yy, e0=float(val)))
                except ValueError:
                    pass
    tr = pd.DataFrame(recs)
    tr.to_csv(DATA / "e0_trend.csv", index=False)
    print(tr.groupby("sex").pref.nunique().to_string(), tr.year.min(), tr.year.max())


if __name__ == "__main__":
    main()
