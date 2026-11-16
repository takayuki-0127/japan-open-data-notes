"""02 整形：通勤・通学の総平均時間（分）を縦長の CSV にする（オフライン）。
- data/national.csv：年×男女×曜日（週全体・平日）、有業者（全国、1976〜2021年）
- data/pref.csv    ：年（2016・2021）×都道府県×男女×曜日×区分（有業者総数・正規の職員・従業員）"""
import pathlib, re
import pandas as pd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
YEARS = [1976, 1981, 1986, 1991, 1996, 2001, 2006, 2011, 2016, 2021]

def national():
    wb = openpyxl.load_workbook(str(RAW / "shakai_ts_t6_1976_2021_000032229317.xlsx"), read_only=True)
    out = []
    for ws, sex in zip(wb.worksheets, ["総数", "男", "女"]):
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        sec = None
        for r in rows:
            if r[0] in ("総数", "有業者", "無業者"):
                sec = r[0]
            if sec == "有業者" and r[2] == "通勤・通学":
                vals = r[5:45]
                for k, day in enumerate(["週全体", "平日", "土曜日", "日曜日"]):
                    for j, y in enumerate(YEARS):
                        v = vals[10 * k + j]
                        out.append((y, sex, day, float(v)))
    return pd.DataFrame(out, columns=["year", "sex", "day", "commute_min"])

def lab(x):
    return re.sub(r"^\d+_", "", str(x)).strip()

def pref():
    out = []
    spec = [(2016, "shakai_2016_t68-1_pref_000031617014.xlsx", 5, 16, 20, 20),
            (2021, "shakai_2021_t74-1_pref_000032224232.xlsx", 0, 5, 9, 10)]
    for y, name, c0, cpop, ccom, minrow in spec:
        ws = openpyxl.load_workbook(str(RAW / name), read_only=True).worksheets[0]
        for r in ws.iter_rows(min_row=minrow, values_only=True):
            day, area, sex, st, form = (lab(r[c0 + i]) for i in range(5))
            if day not in ("週全体", "平日") or not re.match(r"^\d{2}_", str(r[c0 + 1])):
                continue
            code = int(str(r[c0 + 1])[:2])
            if code > 47:
                continue
            if st == "総数" and form == "総数":
                grp = "有業者総数"
            elif st == "うち雇用されている人" and form == "正規の職員・従業員":
                grp = "正規の職員・従業員"
            else:
                continue
            v = r[ccom]
            if v in (None, "-", "…", "x", "X"):
                continue
            out.append((y, code, area, sex, day, grp, float(r[cpop]), float(v)))
    return pd.DataFrame(out, columns=["year", "pref", "area", "sex", "day", "group", "pop_k", "commute_min"])

def main():
    N = national(); P = pref()
    assert not N.duplicated(["year", "sex", "day"]).any()
    assert not P.duplicated(["year", "pref", "sex", "day", "group"]).any()
    N.sort_values(["sex", "day", "year"]).to_csv(ROOT / "data" / "national.csv", index=False)
    P.sort_values(["year", "pref", "sex", "day", "group"]).to_csv(ROOT / "data" / "pref.csv", index=False)
    # 確かめ：2016年・2021年の全国の有業者（週全体）が、時系列表と県別表で一致するか
    for y in (2016, 2021):
        a = N[(N.year == y) & (N.sex == "総数") & (N.day == "週全体")].commute_min.iloc[0]
        b = P[(P.year == y) & (P.pref == 0) & (P.sex == "総数") & (P.day == "週全体") & (P.group == "有業者総数")].commute_min.iloc[0]
        print(y, "時系列", a, "県別表の全国", b)
    print(P.groupby(["year", "group", "day", "sex"]).pref.nunique().to_dict())

if __name__ == "__main__":
    main()
