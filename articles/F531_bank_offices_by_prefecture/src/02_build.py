"""02 整形（オフライン）：5つの経済センサスの表から、銀行業・協同組織金融業の民営事業所数と従業者数を
全国・都道府県別に抜き出し、人口と合わせて1つの長い表にする。
- 都道府県の名前は、各表の地域の見出しの文字から読み（空白を除く）、人口推計の表の名前（都道府県コードつき）と照らして付ける。
- 産業は、見出しの文字の先頭の番号と名前（「62 銀行業」「63 協同組織金融業」「622 銀行（中央銀行を除く）」など）で選ぶ。
出力：data/offices_long.csv、data/population.csv、results/build_checks.csv
"""
import csv, io, pathlib, re
import openpyxl, xlrd
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D, R = ROOT / "data" / "raw", ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
IND = {"62": "銀行業", "63": "協同組織金融業", "622": "銀行（中央銀行を除く）", "631": "中小企業等金融業", "632": "農林水産金融業"}


def clean(s):
    return re.sub(r"[\s　]", "", str(s))


def num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "…", "X", "x", "*"):
        return 0.0 if s == "-" else None
    return float(s)


def ind_of(label):
    m = re.match(r"^(\d{2,3})[_\s　]*(.+)$", clean(label))
    if m and m.group(1) in IND and clean(m.group(2)).startswith(IND[m.group(1)][:4]):
        return m.group(1)
    return None


def population():
    rows = []
    wb = openpyxl.load_workbook(RAW / "pop_pref_2020_2024.xlsx", read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    hdr = None
    for r in ws.iter_rows(values_only=True):
        if r[7] == "人口区分":
            hdr = r; continue
        if hdr and r[7] == "総人口" and r[8] == "男女計":
            code = str(r[9])[:2]
            for j, h in enumerate(hdr):
                m = re.match(r"(\d{4})年", str(h))
                if m:
                    rows.append({"pref_code": code, "pref": clean(r[10]), "year": int(m.group(1)), "pop_k": num(r[j])})
    wb = openpyxl.load_workbook(RAW / "pop_pref_2000_2020.xlsx", read_only=True, data_only=True)
    for sh in ["総人口（2000年～2015年）", "総人口 (2015年～2020年)"]:
        ws = wb[sh]
        yrs = None
        for r in ws.iter_rows(values_only=True):
            if yrs is None:
                cand = {j: int(re.fullmatch(r"(\d{4})年?", str(v).strip()).group(1)) for j, v in enumerate(r)
                        if v is not None and re.fullmatch(r"\d{4}年?", str(v).strip())}
                if len(cand) >= 5:
                    yrs = cand
                continue
            if r[1] is not None and re.fullmatch(r"\d{2}", str(r[1]).strip()):
                code, name = str(r[1]).strip(), clean(r[2])
            elif r[0] is not None and clean(r[0]) == "全国":
                code, name = "00", "全国"
            else:
                continue
            for j, y in yrs.items():
                if y < 2020 and r[j] is not None:
                    rows.append({"pref_code": code, "pref": name, "year": y, "pop_k": num(r[j])})
    p = pd.DataFrame(rows).drop_duplicates(["pref_code", "year"])
    return p


def y2009():
    s = xlrd.open_workbook(RAW / "ecensus2009_basic_t1.xls").sheet_by_name("民営事業所")
    names = s.row_values(4); kinds = s.row_values(6)
    cols = {}
    for j in range(s.ncols):
        if clean(names[j]):
            cols[clean(names[j])] = j          # 事業所数の列。次の列が従業者数
    for j, k in cols.items():
        assert clean(kinds[k]) == "事業所数" and clean(kinds[k + 1]) == "従業者数", j
    out = []
    for r in range(s.nrows):
        v = s.row_values(r)
        code = clean(v[1]) or clean(v[2])
        if code in IND and clean(v[5]).startswith(IND[code][:4]):
            for p, j in cols.items():
                out.append({"year": 2009, "survey": "基礎調査", "ind": code, "area": p, "offices": num(v[j]), "workers": num(v[j + 1])})
    return out


def long_csv(name, year, survey, group_label):
    rows = list(csv.reader(io.StringIO((RAW / name).read_bytes().decode("cp932"))))
    hdr_g, hdr_k = rows[9], rows[10]
    g0 = next(j for j, c in enumerate(hdr_g) if clean(c) == group_label)
    assert clean(hdr_k[g0]) == "事業所数" and clean(hdr_k[g0 + 1]).startswith("従業者数"), (name, hdr_k[g0:g0 + 2])
    assert clean(hdr_k[3]) == "地域"
    out = []
    for r in rows[11:]:
        if len(r) < g0 + 2:
            continue
        code = ind_of(r[6])
        if code:
            out.append({"year": year, "survey": survey, "ind": code, "area": clean(r[3]), "offices": num(r[g0]), "workers": num(r[g0 + 1])})
    return out


def xlsx_long(name, year, survey, org_label):
    ws = openpyxl.load_workbook(RAW / name, read_only=True, data_only=True).worksheets[0]
    out, hdr = [], None
    for r in ws.iter_rows(values_only=True):
        if hdr is None and r[0] == "地域識別コード":
            hdr = r
            assert clean(r[1]) == "地域区分" and clean(r[4]) == "産業中分類" and clean(r[5]) == "経営組織"
            continue
        if hdr is None or r[4] is None:
            continue
        code = ind_of(r[4])
        if code and clean(r[5]) == org_label:
            area = clean(str(r[1]).split("_", 1)[1])
            out.append({"year": year, "survey": survey, "ind": code, "area": area, "offices": num(r[6]), "workers": num(r[7]), "area_code": str(r[1])[:5]})
    return out


def main():
    pop = population()
    pop.sort_values(["pref_code", "year"]).to_csv(D / "population.csv", index=False)
    names = pop[pop.year == 2020].set_index("pref")["pref_code"].to_dict()
    assert len(names) == 48, len(names)
    # 2021年・2024年の表の見出し（"0_総数"・"1_民営"）は、それぞれの表の経営組織の区分に合わせる
    rows = y2009() + long_csv("ecensus2014_basic_t2.csv", 2014, "基礎調査", "うち民営") + \
        long_csv("ecensus2016_activity_t4.csv", 2016, "活動調査", "総数(経営組織)") + \
        xlsx_long("ecensus2021_activity_t2_1.xlsx", 2021, "活動調査", "1_民営") + \
        xlsx_long("ecensus2024_basic_t2.xlsx", 2024, "基礎調査", "0_総数")
    df = pd.DataFrame(rows)
    df = df[df["area"].isin(names)].copy()          # 大都市・市区町村の行を除く（都道府県と全国だけ）
    if "area_code" in df:
        # 2021・2024年は地域コードの下3桁が000の行だけが都道府県（市と同名の県を取り違えないため）
        m = df["area_code"].notna()
        df = df[~m | df["area_code"].str.endswith("000")]
    df["pref_code"] = df["area"].map(names)
    df = df.drop(columns=[c for c in ["area_code"] if c in df]).drop_duplicates(["year", "ind", "pref_code"])
    df = df.sort_values(["year", "ind", "pref_code"])
    df.to_csv(D / "offices_long.csv", index=False)
    # 確かめ：都道府県の合計＝全国、47都道府県がそろう
    chk = []
    for (y, ind), g in df.groupby(["year", "ind"]):
        nat = g[g.pref_code == "00"]; pr = g[g.pref_code != "00"]
        chk.append({"year": y, "ind": ind, "n_pref": len(pr), "national_offices": float(nat["offices"].iloc[0]),
                    "sum_pref_offices": float(pr["offices"].sum()), "national_workers": float(nat["workers"].iloc[0]),
                    "sum_pref_workers": float(pr["workers"].sum())})
    c = pd.DataFrame(chk)
    c.to_csv(R / "build_checks.csv", index=False)
    print(c.to_string())
    assert (c["n_pref"] == 47).all() and (c["national_offices"] == c["sum_pref_offices"]).all()


if __name__ == "__main__":
    main()
