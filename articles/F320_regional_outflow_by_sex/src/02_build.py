"""02 整形：移動報告（47都道府県、男女×年齢）と人口推計（日本人、男女×年齢）を縦長の CSV にする（オフライン）。"""
import pathlib, re
import pandas as pd, xlrd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
        "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"]
COLS = ["total"] + AGES
SEXES = ["総数", "男", "女"]

def mig_xls(path, year, sheet_idx, nat):
    s = xlrd.open_workbook(str(path)).sheet_by_index(sheet_idx)
    out = []
    for i in range(19, s.nrows):
        code = str(s.cell_value(i, 1)).strip()
        if not re.fullmatch(r"\d{5}", code) or code == "00000":
            continue
        pc = int(code[:2])
        for k, sex in enumerate(SEXES):
            for j, c in enumerate(COLS):
                out.append((year, pc, nat, sex, c, float(s.cell_value(i, 12 + 25 * k + j))))
    return out

def mig_xlsx(path, year):
    ws = openpyxl.load_workbook(str(path), read_only=True).worksheets[0]
    out = []
    for r in ws.iter_rows(min_row=7, values_only=True):
        if r[1] not in (60000, 61000):
            continue
        code = str(r[5]).zfill(5)
        if not code.endswith("000") or not (1 <= int(code[:2]) <= 47):
            continue
        nat = "日本人" if r[1] == 61000 else "外国人を含む"
        for k, sex in enumerate(SEXES):
            for j, c in enumerate(COLS):
                out.append((year, int(code[:2]), nat, sex, c, float(r[7 + 20 * k + j])))
    return out

PAGES = ["total", "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39"]

def pop_2019(path):
    s = xlrd.open_workbook(str(path)).sheet_by_index(0)
    out = []
    # 日本人人口の男（278行目〜）・女（345行目〜）の表
    for start, sex in [(278, "男"), (345, "女")]:
        for i in range(start, min(start + 60, s.nrows)):
            code = str(s.cell_value(i, 8)).strip()
            if re.fullmatch(r"\d{2}", code):
                for j, c in enumerate(PAGES):
                    out.append((2019, int(code), sex, c, float(s.cell_value(i, 12 + j))))
    return out

def pop_2024(path):
    ws = openpyxl.load_workbook(str(path), read_only=True).worksheets[0]
    out = []
    for r in ws.iter_rows(min_row=8, values_only=True):
        if r[9] != "日本人人口" or r[12] not in ("男", "女") or r[10] == "00000":
            continue
        for j, c in enumerate(PAGES):
            out.append((2024, int(str(r[10])[:2]), r[12], c, float(r[15 + j])))
    return out

def main():
    rows = []
    for p in sorted(RAW.glob("jumin_3-3_*")):
        y = int(p.name.split("_")[2])
        if p.suffix == ".xls":
            if y <= 2013:
                rows += mig_xls(p, y, 0, "日本人")
            else:
                rows += mig_xls(p, y, 0, "外国人を含む")
                rows += mig_xls(p, y, 1, "日本人")
        else:
            rows += mig_xlsx(p, y)
    m = pd.DataFrame(rows, columns=["year", "pref", "nat", "sex", "age", "net"])
    assert m.duplicated(["year", "pref", "nat", "sex", "age"]).sum() == 0
    tot = m.groupby(["year", "nat", "sex", "age"]).net.sum().abs().max()
    print("47都道府県の合計（0になるはず）の絶対値の最大", tot)
    m["age"] = pd.Categorical(m.age, categories=COLS, ordered=True)
    m = m.sort_values(["year", "pref", "nat", "sex", "age"]).reset_index(drop=True)
    m["net"] = m.net.astype(int)
    m.to_csv(ROOT / "data" / "netmig_pref_sex_age.csv", index=False)
    pp = []
    for p in sorted(RAW.glob("jinko_suikei_t10_*")):
        pp += pop_2019(p) if "_2019_" in p.name else pop_2024(p)
    P = pd.DataFrame(pp, columns=["year", "pref", "sex", "age", "pop_thousand"])
    print(P.groupby(["year", "sex"]).pref.nunique().to_dict())
    P = P.sort_values(["year", "pref", "sex", "age"]).reset_index(drop=True)
    P.to_csv(ROOT / "data" / "pop_pref_sex_age.csv", index=False)
    print(len(m), len(P))

if __name__ == "__main__":
    main()
