"""小売業の年間商品販売額（2014年・2021年）と国勢調査の人口（2015年・2020年）を市区町村コードでつなぐ。data/muni.csv：
code（5桁）, pref, name, kind（seirei/ku/city/town）, role（中心市/周辺市町村/なし）, sales2014, sales2021（小売業計、百万円）, nonstore2014, nonstore2021（うち無店舗小売業。秘匿は空）, pop2015, pop2020
政令市は市全体の行を使い、行政区は使わない。東京23区はそれぞれの区を1つの単位とする。"""
import pathlib, re, unicodedata
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
NAN = float("nan")


def norm(s):
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s)))


def num(v):
    s = norm(v)
    return float("nan") if s in ("", "-", "X", "x", "None", "…") else float(s)


def rows_of(path, sheet=None):
    wb = openpyxl.load_workbook(path, read_only=True)
    return list(wb[sheet or wb.sheetnames[0]].iter_rows(values_only=True))


def ec2021():
    out = {}
    for f, keep in [("ecensus2021_city.xlsx", {"1", "2", "0"}), ("ecensus2021_town.xlsx", {"3"})]:
        rows = rows_of(RAW / f)
        col = next(j for j in range(len(rows[7])) if norm(rows[7][j]) == "I2_小売業計" and norm(rows[8][j]) == "年間商品販売額")
        cn = next(j for j in range(len(rows[7])) if norm(rows[7][j]) == "61_無店舗小売業" and norm(rows[8][j]) == "年間商品販売額")
        for r in rows[10:]:
            idc, area = norm(r[0]), norm(r[1])
            m = re.fullmatch(r"(\d{5})_(.+)", area)
            if idc not in keep or not m:
                continue
            code, name = m.groups()
            if idc == "0" and not code.startswith("131"):
                continue  # 政令市の行政区は使わない（東京23区だけ使う）
            if code == "13100":
                continue  # 特別区部の合計
            out[code] = (name, num(r[col]), num(r[cn]))
    return out


def nonstore_col(rows, a, b):
    c0 = next(j for j, v in enumerate(rows[a]) if "無店舗" in norm(v))
    return next(j for j in range(c0 - 1, c0 + 4) if "年間商品販売額" in norm(rows[b][j]))


def sh2014():
    out = {}
    # 第1表（区市郡別）：小売業の年間商品販売額の列を見出しで探す
    rows = rows_of(RAW / "shogyo2014_municipal.xlsx", "３巻１表")
    c0 = next(j for j, v in enumerate(rows[6]) if "小売" in norm(v))
    col = next(j for j in range(c0, c0 + 6) if "年間商品販売額" in norm(rows[7][j]))
    cn = nonstore_col(rows, 6, 7)
    for r in rows[10:]:
        p, a = norm(r[1]), norm(r[2])
        mp, ma = re.match(r"(\d{2})", p), re.fullmatch(r"(\d{3})(.+)", a)
        if not (mp and ma):
            continue
        code3, name = ma.groups()
        if name.endswith("区") and mp.group(1) != "13":
            continue  # 政令市の行政区
        if mp.group(1) == "13" and code3 == "100":
            continue
        out[mp.group(1) + code3] = (name, num(r[col]), num(r[cn]))
    rows = rows_of(RAW / "shogyo2014_municipal.xlsx", "３巻２表")
    c0 = next(j for j, v in enumerate(rows[6]) if "小売" in norm(v))
    col = next(j for j in range(c0, c0 + 6) if "年間商品販売額" in norm(rows[7][j]))
    cn = nonstore_col(rows, 6, 7)
    for r in rows[10:]:
        p, a = norm(r[1]), norm(r[3])
        mp, ma = re.match(r"(\d{2})", p), re.fullmatch(r"(\d{3})(.+)", a)
        if mp and ma:
            out[mp.group(1) + ma.group(1)] = (ma.group(2), num(r[col]), num(r[cn]))
    return out


def census():
    rows = rows_of(RAW / "census2020_t1_1.xlsx")
    pop = {}
    for r in rows[15:]:
        if norm(r[0]) in {"0", "1", "2", "3"} and re.fullmatch(r"\d{5}", norm(r[5])):
            code = norm(r[5])
            if norm(r[0]) == "0" and not code.startswith("131"):
                continue
            if code == "13100":
                continue
            pop[code] = (norm(r[4])[3:], re.sub(r"^\d+_", "", norm(r[6])), {"0": "ku", "1": "seirei", "2": "city", "3": "town"}[norm(r[0])], num(r[7]), num(r[10]))
    role = {}
    for f in ["census2020_t1_3.xlsx", "census2020_t1_4.xlsx"]:  # 大都市圏と都市圏。どちらかで中心市なら中心市とする
        for r in rows_of(RAW / f)[14:]:
            if norm(r[2]) in {"0", "1", "2", "3"} and norm(r[1]) in ("中心市", "周辺市町村"):
                c = norm(r[4])
                if role.get(c) != "中心市":
                    role[c] = norm(r[1])
    return pop, role


def main():
    e, s = ec2021(), sh2014()
    # 2014年から2020年までに町から市になって番号が変わった団体
    for old, new in [("04423", "04216"), ("40305", "40231")]:
        s[new] = s.pop(old)
    pop, role = census()
    rows = []
    for code, (pref, name, kind, p20, p15) in sorted(pop.items()):
        rows.append({"code": code, "pref": pref, "name": name, "kind": kind, "role": role.get(code, "なし"),
                     "sales2014": s.get(code, (None, NAN, NAN))[1], "sales2021": e.get(code, (None, NAN, NAN))[1],
                     "nonstore2014": s.get(code, (None, NAN, NAN))[2], "nonstore2021": e.get(code, (None, NAN, NAN))[2], "pop2015": p15, "pop2020": p20})
    d = pd.DataFrame(rows)
    miss14 = sorted(set(s) - set(pop)); miss21 = sorted(set(e) - set(pop))
    print("2014にあって人口にない:", [(c, s[c][0]) for c in miss14]); print("2021にあって人口にない:", [(c, e[c][0]) for c in miss21])
    print(d.kind.value_counts(), d.role.value_counts(), d[["sales2014", "sales2021"]].isna().sum())
    print(d[d.sales2014.isna() | d.sales2021.isna()][["code", "name", "sales2014", "sales2021"]].to_string())
    d.to_csv(ROOT / "data" / "muni.csv", index=False)
    print(d[["sales2014", "sales2021", "pop2015", "pop2020"]].sum())


if __name__ == "__main__":
    main()
