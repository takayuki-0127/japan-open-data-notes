"""data/raw の Excel から、分析用の CSV を作る（オフライン）。
- data/pref_3gen.csv : 都道府県・全国 × 年（2010・2015・2020・2025）の一般世帯数、3世代世帯数、65歳以上の単独世帯数、高齢夫婦世帯数
    2025年は第9-1表（原数値）。不詳補完値（主な結果）は gen3_imputed 列に別に置く。
- data/pref_type.csv : 都道府県・全国 × 年（1980〜2025年）の一般世帯数と「親・夫婦・子の型」3つの世帯数（旧分類／新分類）
"""
import pathlib, re
import openpyxl, xlrd
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CODE = re.compile(r"^(\d{2})000(?:_|$)")


def rows_of(name):
    if name.endswith(".xls"):
        s = xlrd.open_workbook(RAW / name).sheet_by_index(0)
        return [s.row_values(i) for i in range(s.nrows)]
    return [list(r) for r in openpyxl.load_workbook(RAW / name, read_only=True).worksheets[0].iter_rows(values_only=True)]


def num(v):
    if v is None or v == "" or v == "-":
        return 0.0
    return float(v)


def main_results(name, year, ccode, cols):
    """主な結果から都道府県（と全国）の行を取る。cols = (一般世帯, 65歳以上単独, 高齢夫婦, 3世代)。"""
    out = []
    for r in rows_of(name):
        if len(r) <= max(cols):
            continue
        m = CODE.match(str(r[ccode]).strip())
        if not m:
            continue
        out.append(dict(year=year, pref=int(m.group(1)), households=num(r[cols[0]]), single65=num(r[cols[1]]),
                        couple65=num(r[cols[2]]), gen3=num(r[cols[3]])))
    df = pd.DataFrame(out).drop_duplicates("pref")
    assert len(df) == 48, (name, len(df))
    return df


TYPES_OLD_NEW = {13: "type_c2p", 14: "type_c1p", 18: "type_cpo"}  # 夫婦,子供と両親／夫婦,子供とひとり親／夫婦,子供,親と他の親族
T91_TYPES = {"1203_": "type_c2p", "1204_": "type_c1p", "1208_": "type_cpo"}


def t91():
    """第9-1表（2025年、原数値）：都道府県の総数・3世代世帯数・3つの型。"""
    out = {}
    ws = openpyxl.load_workbook(RAW / "census2025_t9_1.xlsx", read_only=True).worksheets[0]
    for r in ws.iter_rows(min_row=11, values_only=True):
        m = CODE.match(str(r[2]).strip()) if r[2] else None
        if not m:
            continue
        p = int(m.group(1)); fam = str(r[4])
        d = out.setdefault(p, dict(year=2025, pref=p))
        if fam.startswith("0_総数"):
            d["households"] = num(r[5]); d["gen3"] = num(r[11])
        for k, v in T91_TYPES.items():
            if fam.startswith(k):
                d[v] = num(r[5])
    df = pd.DataFrame(out.values())
    assert len(df) == 48
    return df


def timeseries(name, series):
    out = []
    for r in rows_of(name):
        if not r or not r[0] or not re.match(r"^\d{4}年$", str(r[0])):
            continue
        m = CODE.match(str(r[2]).strip())
        if not m or "人口集中" in str(r[2]):
            continue
        d = dict(year=int(str(r[0])[:4]), pref=int(m.group(1)), series=series, households=num(r[3]))
        for j, k in TYPES_OLD_NEW.items():
            d[k] = num(r[j])
        out.append(d)
    df = pd.DataFrame(out)
    assert not df.duplicated(["year", "pref"]).any()
    return df


def main():
    m = [main_results("census2010_main.xls", 2010, 1, (44, 51, 52, 53)),
         main_results("census2015_main.xls", 2015, 1, (44, 51, 52, 53)),
         main_results("census2020_main.xlsx", 2020, 1, (39, 46, 47, 48))]
    imp = main_results("census2025_main.xlsx", 2025, 1, (39, 46, 47, 48))
    t = t91()
    g25 = t[["year", "pref", "households", "gen3"]].merge(
        imp[["pref", "gen3", "households", "single65", "couple65"]].rename(columns={"gen3": "gen3_imputed", "households": "households_imputed",
                                                                               "single65": "single65_imputed", "couple65": "couple65_imputed"}), on="pref")
    P = pd.concat(m + [g25], ignore_index=True).sort_values(["year", "pref"])
    P.to_csv(ROOT / "data" / "pref_3gen.csv", index=False, float_format="%.0f")
    T = pd.concat([timeseries("census_ts_t3_family_old.xlsx", "old"), timeseries("census_ts_t3_family_new.xlsx", "new"),
                   t.assign(series="new")[["year", "pref", "series", "households", "type_c2p", "type_c1p", "type_cpo"]]], ignore_index=True)
    T = T.sort_values(["series", "year", "pref"])
    T.to_csv(ROOT / "data" / "pref_type.csv", index=False, float_format="%.0f")
    print(P[P.pref == 0]); print(T[T.pref == 0])


if __name__ == "__main__":
    main()
