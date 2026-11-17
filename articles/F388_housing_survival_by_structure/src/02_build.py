"""02 整形：各回の「住宅の種類、構造、建築の時期別住宅数－全国」から、住宅総数の行を
構造（総数・木造・非木造）× 建築の時期の長い表にする（data/stock_by_period.csv）。オフライン。"""
import pathlib, re
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"

# 各回の「住宅総数」ブロックの行の並び（建築の時期の始まりの年・終わりの年）。None は「不詳」
PERIODS = {
    1998: [(1900, 1945), (1946, 1950), (1951, 1960), (1961, 1970), (1971, 1980), (1981, 1990), (1991, 1993),
           (1994, 1994), (1995, 1995), (1996, 1996), (1997, 1997), (1998, 1998), None],
    2003: [(1900, 1950), (1951, 1960), (1961, 1970), (1971, 1980), (1981, 1985), (1986, 1990), (1991, 1995),
           (1996, 1998), (1999, 1999), (2000, 2000), (2001, 2001), (2002, 2002), (2003, 2003), None],
    2008: [(1900, 1950), (1951, 1960), (1961, 1970), (1971, 1980), (1981, 1990), (1991, 1995), (1996, 2000),
           (2001, 2003), (2004, 2004), (2005, 2005), (2006, 2006), (2007, 2007), (2008, 2008), None],
    2013: [(1900, 1950), (1951, 1960), (1961, 1970), (1971, 1980), (1981, 1990), (1991, 1995), (1996, 2000),
           (2001, 2005), (2006, 2008), (2009, 2009), (2010, 2010), (2011, 2011), (2012, 2012), (2013, 2013), None],
    2018: [(1900, 1950), (1951, 1970), (1971, 1980), (1981, 1990), (1991, 1995), (1996, 2000), (2001, 2005),
           (2006, 2010), (2011, 2013), (2014, 2014), (2015, 2015), (2016, 2016), (2017, 2017), (2018, 2018), None],
    2023: [(1900, 1950), (1951, 1970), (1971, 1980), (1981, 1990), (1991, 2000), (2001, 2005), (2006, 2010),
           (2011, 2015), (2016, 2018), (2019, 2019), (2020, 2020), (2021, 2021), (2022, 2022), (2023, 2023), None],
}

def num(v):
    if isinstance(v, (int, float)) and not pd.isna(v):
        return float(v)
    s = str(v).strip().replace(",", "")
    if s in ("-", "－", "…", ""):
        return 0.0
    return float(s)

def rows_after_total(df, total_pat, nvals, label_col_pat=None):
    """「住宅総数」の行から下の行について、右端の nvals 個の数値を返す。"""
    out = []
    start = None
    for i in range(len(df)):
        cells = [str(c) for c in df.iloc[i].tolist() if pd.notna(c)]
        joined = "".join(cells).replace(" ", "").replace("　", "")
        if start is None and re.search(total_pat, joined):
            start = i
        if start is not None:
            vals = [c for c in df.iloc[i].tolist() if pd.notna(c) and str(c).strip() != ""]
            texts = [str(c).replace(" ", "").replace("\u3000", "") for c in vals
                     if isinstance(c, str) and re.search(r"[年詳戦数]", str(c))]
            out.append((texts[-1] if texts else "", [num(v) for v in vals[-nvals:]]))
    return out

def parse(year, path):
    df = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
    if year == 2023:
        rows = [r for r in rows_after_total(df, r"00000_全国0_総数00_総数", 6)]
        # 列：総数, 木造, 非木造, RC, 鉄骨, その他
        conv = lambda v: (v[0], v[1], v[2])
    elif year == 2018:
        rows = [r for r in rows_after_total(df, r"00000_全国10_総数100_総数", 8)]
        # 列：総数, 木造(計), 木造(防火除く), 防火木造, 非木造, RC, 鉄骨, その他
        conv = lambda v: (v[0], v[1], v[4])
    else:
        rows = rows_after_total(df, r"住宅総数", 6)
        # 列：総数, 木造, 防火木造, 鉄筋・鉄骨コンクリート造, (ブロック造|鉄骨造), その他
        conv = lambda v: (v[0], v[1] + v[2], v[0] - v[1] - v[2])
    per = PERIODS[year]
    rows = rows[: len(per) + 1]
    recs = []
    tot = conv(rows[0][1])
    for (lab, v), p in zip(rows[1:], per):
        t, w, nw = conv(v)
        recs.append(dict(year=year, start=p[0] if p else -1, end=p[1] if p else -1,
                         label=lab, total=t, wood=w, nonwood=nw))
    d = pd.DataFrame(recs)
    # 確かめ：建築の時期の合計（不詳を含む）が住宅総数に一致
    for k, c in zip(("total", "wood", "nonwood"), tot):
        assert abs(d[k].sum() - c) <= 1000, (year, k, d[k].sum(), c)  # 公表値は百戸単位の丸めで合計が少しずれる
    assert (d["total"] - d["wood"] - d["nonwood"]).abs().max() <= 1000, year
    d.attrs["tot"] = tot
    return d

def main():
    files = sorted(RAW.glob("jutaku_*_kind_structure_period_*"))
    parts = []
    for f in files:
        year = int(f.name.split("_")[1])
        parts.append(parse(year, f))
    out = pd.concat(parts, ignore_index=True)
    long = out.melt(id_vars=["year", "start", "end", "label"], value_vars=["total", "wood", "nonwood"],
                    var_name="structure", value_name="dwellings")
    long["dwellings"] = long["dwellings"].round(0).astype("int64")
    long = long.sort_values(["structure", "year", "start", "end"], kind="mergesort").reset_index(drop=True)
    (BASE / "data").mkdir(exist_ok=True)
    long.to_csv(BASE / "data" / "stock_by_period.csv", index=False, lineterminator="\n")
    print(long.groupby(["structure", "year"])["dwellings"].sum().unstack())

if __name__ == "__main__":
    main()
