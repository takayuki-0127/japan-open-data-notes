"""data/raw の Excel から、分析用の CSV を作る（オフライン）。
- data/flows.csv : year, nat（japanese/all）, city（5桁コード）, partner（相手の都道府県 1〜47）, in, out
    相手の都道府県は「その都道府県のうち当該都市を除く市町村」。
- data/age_net_2025.csv : nat, city, partner（都道府県 1〜47 または 東京圏・名古屋圏・大阪圏・全国）, age, net
"""
import pathlib, re
import openpyxl, xlrd
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CITIES = ["01100", "04100", "34100", "40130"]   # 札幌、仙台、広島、福岡
NAT = {"移動者": "all", "日本人移動者": "japanese"}


def code5(v):
    s = str(v).strip()
    if re.fullmatch(r"\d+(\.0)?", s):
        s = str(int(float(s))).zfill(5)
    return s


def num(v):
    return float(v) if v not in (None, "", "-") and not isinstance(v, str) else (0.0 if v in ("-",) else float(str(v).replace(",", "")))


def old_format(path, year):
    wb = xlrd.open_workbook(path)
    names = [s.name for s in wb.sheets()]
    s = wb.sheet_by_name("日本人") if "日本人" in names else wb.sheet_by_index(0)
    out = []
    for i in range(s.nrows):
        v = s.row_values(i)
        m = re.search(r"(\d{5})", str(v[2]))
        if not m or m.group(1) not in CITIES:
            continue
        p = str(v[8]).strip()
        if not re.fullmatch(r"\d{2}", p) or str(v[9]).strip() != "":
            continue   # 都道府県の行だけ（21大都市の行は除く）
        out.append(dict(year=year, nat="japanese", city=m.group(1), partner=int(p), **{"in": num(v[13]), "out": num(v[16])}))
    return out


def new_format(path, year):
    ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    out = []
    for r in ws.iter_rows(min_row=8, values_only=True):
        if r[0] is None or code5(r[0]) not in CITIES or r[3] not in NAT:
            continue
        p = code5(r[6])
        if not re.fullmatch(r"\d{2}000", p) or not 1 <= int(p[:2]) <= 47:
            continue
        out.append(dict(year=year, nat=NAT[r[3]], city=code5(r[0]), partner=int(p[:2]), **{"in": num(r[8]), "out": num(r[11])}))
    return out


def age_2025():
    ws = openpyxl.load_workbook(RAW / "migration_age_net_2025.xlsx", read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    ages = [str(a) for a in rows[5][9:29]]
    out = []
    for r in rows[7:]:
        if r[1] is None or code5(r[1]) not in CITIES or r[4] not in NAT:
            continue
        p = code5(r[7]); name = str(r[8])
        if name in ("東京圏", "名古屋圏", "大阪圏", "全国"):
            key = name
        elif re.fullmatch(r"\d{2}000", p) and 1 <= int(p[:2]) <= 47:
            key = str(int(p[:2]))
        elif False:
            key = name
        else:
            continue
        for a, v in zip(ages, r[9:29]):
            out.append(dict(nat=NAT[r[4]], city=code5(r[1]), partner=key, age=a, net=num(v)))
    return pd.DataFrame(out)


def main():
    rows = []
    for p in sorted(RAW.glob("migration_city_*")):
        y = int(re.search(r"(\d{4})", p.name).group(1))
        rows += old_format(p, y) if p.suffix == ".xls" else new_format(p, y)
    F = pd.DataFrame(rows).sort_values(["nat", "year", "city", "partner"])
    chk = F.groupby(["nat", "year", "city"]).size()
    assert (chk == 47).all(), chk[chk != 47]
    F.to_csv(ROOT / "data" / "flows.csv", index=False, float_format="%.0f")
    A = age_2025()
    A.to_csv(ROOT / "data" / "age_net_2025.csv", index=False, float_format="%.0f")
    g = F.assign(net=F["in"] - F.out).groupby(["nat", "year", "city"]).net.sum().unstack("city")
    print(g)
    tot = A[(A.partner == "全国") & (A.age == "総数")].set_index(["nat", "city"]).net
    print(tot)


if __name__ == "__main__":
    main()
