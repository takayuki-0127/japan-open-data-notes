"""定員管理調査（市区町村・指定都市）と住民基本台帳人口を、団体ごとにつなぐ。data/staff_pop.csv：
year, code, pref, name, kind（市区町村/指定都市）, pop, gen_admin（一般管理）, welfare（福祉関係）, general（一般行政計）, education, fire,
ordinary（普通会計計）, enterprise（公営企業等会計）, total"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
COLS = ["gen_admin", "welfare", "general", "education", "police", "fire", "ordinary", "enterprise", "total"]


def norm(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def staff(path, designated):
    x = pd.ExcelFile(path)
    d = pd.read_excel(x, x.sheet_names[0], header=None)
    out = []
    for i in range(len(d)):
        row = d.iloc[i].tolist()
        if designated:
            name = norm(row[0])
            vals = row[1:10]
            if name.endswith("市") and all(isinstance(v, (int, float)) for v in vals):
                out.append([None, None, name] + [float(v) for v in vals])
        else:
            code = norm(row[0])
            if re.fullmatch(r"\d{6}", code):
                out.append([code, norm(row[1]), norm(row[2])] + [float(v) for v in row[3:12]])
    return pd.DataFrame(out, columns=["code", "pref", "name"] + COLS)


def pop(path):
    d = pd.read_excel(path, header=None, dtype=object)
    out = []
    for i in range(len(d)):
        code = norm(d.iloc[i, 0])
        if re.fullmatch(r"\d{6}", code) and not code.endswith("0006") or (re.fullmatch(r"\d{6}", code) and code[2:5] != "000"):
            name = norm(d.iloc[i, 2])
            if name in ("-", "nan"):
                continue
            out.append((code, norm(d.iloc[i, 1]), name, float(d.iloc[i, 5])))
    return pd.DataFrame(out, columns=["code", "pref", "name", "pop"]).drop_duplicates("code")


def main():
    rows = []
    for y, pf in [(2025, "jukijin_2025_municipal.xlsx"), (2020, "jukijin_2020_municipal.xls")]:
        p = pop(RAW / pf)
        m = staff(RAW / f"teiin_{y}_municipal.xlsx", False)
        m = m.merge(p[["code", "pop"]], on="code", how="left")
        m["kind"] = "市区町村"
        ds = staff(RAW / f"teiin_{y}_designated.xlsx", True)
        # 指定都市は名前でつなぐ（行政区ではなく市全体の行。同じ名前の市はない）
        pc = p[p.name.isin(ds.name)]
        assert not pc.name.duplicated().any()
        ds = ds.drop(columns=["code", "pref"]).merge(pc[["code", "pref", "name", "pop"]], on="name", how="left")
        ds["kind"] = "指定都市"
        z = pd.concat([m, ds[m.columns]], ignore_index=True)
        assert z["pop"].notna().all(), z[z["pop"].isna()][["code", "name"]]
        z.insert(0, "year", y)
        rows.append(z)
    out = pd.concat(rows, ignore_index=True).sort_values(["year", "code"]).reset_index(drop=True)
    out.to_csv(ROOT / "data" / "staff_pop.csv", index=False)
    print(out.groupby(["year", "kind"]).size(), out.groupby("year")[["pop", "general", "total"]].sum())


if __name__ == "__main__":
    main()
