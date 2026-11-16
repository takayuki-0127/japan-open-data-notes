"""02 整形：data/raw の Excel（16年分）を、年×地域×国籍×男女×年齢の縦長の CSV にする（オフライン）。"""
import pathlib, re
import pandas as pd, xlrd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
        "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"]
COLS = ["total"] + AGES  # 総数（年齢不詳を含む）+19区分
SEXES = ["総数", "男", "女"]
KEEP = {11: "埼玉県", 12: "千葉県", 13: "東京都", 14: "神奈川県"}

def from_xls(path, year, sheet_idx, nat):
    s = xlrd.open_workbook(str(path)).sheet_by_index(sheet_idx)
    out = []
    for i in range(19, s.nrows):
        code = str(s.cell_value(i, 1)).strip()
        if not re.fullmatch(r"\d{5}", code):
            continue
        pc = int(code[:2])
        if pc not in KEEP and pc != 0:
            continue
        for k, sex in enumerate(SEXES):
            start = 12 + 25 * k
            for j, c in enumerate(COLS):
                out.append((year, "全国" if pc == 0 else KEEP[pc], nat, sex, c, float(s.cell_value(i, start + j))))
    return out

def from_xlsx(path, year):
    ws = openpyxl.load_workbook(str(path), read_only=True).worksheets[0]
    out = []
    for r in ws.iter_rows(min_row=7, values_only=True):
        if r[1] not in (60000, 61000) or r[6] not in list(KEEP.values()) + ["全国"]:
            continue
        nat = "日本人" if r[1] == 61000 else "外国人を含む"
        for k, sex in enumerate(SEXES):
            for j, c in enumerate(COLS):
                out.append((year, r[6], nat, sex, c, float(r[7 + 20 * k + j])))
    return out

def main():
    rows = []
    for p in sorted(RAW.glob("jumin_3-3_*")):
        y = int(p.name.split("_")[2])
        if p.suffix == ".xls":
            if y <= 2013:
                rows += from_xls(p, y, 0, "日本人")  # 2013年までの表は日本人のみ
            else:
                rows += from_xls(p, y, 0, "外国人を含む")
                rows += from_xls(p, y, 1, "日本人")
        else:
            rows += from_xlsx(p, y)
    df = pd.DataFrame(rows, columns=["year", "area", "nat", "sex", "age", "net"])
    df = df.drop_duplicates(["year", "area", "nat", "sex", "age"])  # xlsx の末尾の「全国」の重複行
    ken = df[df.area.isin(["埼玉県", "千葉県", "東京都", "神奈川県"])]
    tk = ken.groupby(["year", "nat", "sex", "age"], as_index=False, sort=True)["net"].sum()
    tk["area"] = "東京圏"
    df = pd.concat([df, tk[df.columns]], ignore_index=True)
    # 確かめ：年齢の合計（不詳を除く）と総数の差、男+女=総数
    chk = df.pivot_table(index=["year", "area", "nat", "sex"], columns="age", values="net", aggfunc="sum")
    gap = (chk["total"] - chk[AGES].sum(axis=1)).abs().max()
    ms = df.pivot_table(index=["year", "area", "nat", "age"], columns="sex", values="net", aggfunc="sum")
    gap2 = (ms["総数"] - ms["男"] - ms["女"]).abs().max()
    print("年齢合計と総数の差の最大", gap, "／男+女と総数の差の最大", gap2)
    df["age"] = pd.Categorical(df.age, categories=COLS, ordered=True)
    df = df.sort_values(["year", "area", "nat", "sex", "age"]).reset_index(drop=True)
    df["net"] = df.net.astype(int)
    df.to_csv(ROOT / "data" / "netmig_tokyo_age.csv", index=False)
    print(len(df), "行", df.year.min(), "-", df.year.max())

if __name__ == "__main__":
    main()
