"""02 整形：ひとり暮らし（単独世帯の世帯主）と15歳以上人口を、年×男女×年齢×配偶関係の表にする（オフライン）。
出力：data/alone_pop.csv（year, sex, age, marital, pop, alone）"""
import pathlib, re
import pandas as pd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AGES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
        "65-69", "70-74", "75-79", "80-84", "85+"]
MAR = ["未婚", "有配偶", "死別", "離別"]

def age_key(s):
    s = re.sub(r"^\d+_", "", str(s))
    m = re.match(r"(\d+)～(\d+)歳", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    if s.startswith("85歳以上"):
        return "85+"
    return None

def num(x):
    return 0.0 if x in (None, "-", "…", "") else float(x)

def rows(name, **kw):
    ws = openpyxl.load_workbook(str(RAW / name), read_only=True).worksheets[0]
    return ws.iter_rows(values_only=True, **kw)

def households():
    out = []
    for r in rows("census_ts_household_marital_1985_2005_000001086181.xlsx", min_row=9):
        if not r[0] or r[2] not in MAR or r[3] not in ("男", "女"):
            continue
        a = age_key(r[4])
        if a:
            out.append((int(r[0][:4]), r[3], a, r[2], num(r[24])))
    for r in rows("census_2020_t12-1_household_marital_000040317884.xlsx", min_row=10):
        if r[1] != "00000_全国":
            continue
        sex = {"1_男": "男", "2_女": "女"}.get(r[2]); mar = re.sub(r"^\d_", "", str(r[3]))
        a = age_key(r[4])
        if sex and mar in MAR and a:
            out.append((2020, sex, a, mar, num(r[24])))
    return pd.DataFrame(out, columns=["year", "sex", "age", "marital", "alone"])

def population():
    out = []
    for r in rows("census_ts_pop_marital_1920_2020_000001085974.xlsx", min_row=11):
        if not r[0] or not str(r[0])[:4].isdigit():
            continue
        y = int(str(r[0])[:4])
        if y not in (1985, 1990, 1995, 2000, 2005, 2020) or r[2] not in ("男", "女"):
            continue
        if y == 2020 and r[4] != "※":   # 2020年は不詳補完値（※）の行を使う
            continue
        a = age_key(r[3])
        if a:
            for k, m in enumerate(MAR):
                out.append((y, r[2], a, m, num(r[6 + k])))
    return pd.DataFrame(out, columns=["year", "sex", "age", "marital", "pop"])

def main():
    H, P = households(), population()
    assert not H.duplicated(["year", "sex", "age", "marital"]).any()
    assert not P.duplicated(["year", "sex", "age", "marital"]).any(), P[P.duplicated(["year", "sex", "age", "marital"], keep=False)].head()
    D = P.merge(H, on=["year", "sex", "age", "marital"], how="outer", validate="1:1")
    assert D.isna().sum().sum() == 0, D[D.isna().any(axis=1)].head()
    D["age"] = pd.Categorical(D.age, AGES, ordered=True); D["marital"] = pd.Categorical(D.marital, MAR, ordered=True)
    D = D.sort_values(["year", "sex", "age", "marital"]).reset_index(drop=True)
    D[["pop", "alone"]] = D[["pop", "alone"]].astype(int)
    D.to_csv(ROOT / "data" / "alone_pop.csv", index=False)
    print(D.groupby("year")[["pop", "alone"]].sum())
    print("alone > pop のセル数", int((D.alone > D["pop"]).sum()))

if __name__ == "__main__":
    main()
