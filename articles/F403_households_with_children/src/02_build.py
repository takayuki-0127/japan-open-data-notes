"""data/raw の CSV・Excel から、分析用の CSV を作る（オフライン）。
- data/national.csv : 年次別の世帯総数・児童のいる世帯数（千世帯）
- data/structure.csv : 2013・2025年の児童のいる世帯の世帯構造別（千世帯）
- data/pref.csv : 2013・2025年の都道府県別 世帯総数・児童のいる世帯・世帯構造（千世帯）と、2025年国勢調査の一般世帯・18歳未満世帯員のいる一般世帯
"""
import csv, io, pathlib, re
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def read(name):
    return list(csv.reader(io.StringIO((RAW / name).read_bytes().decode("cp932"))))


def num(v):
    v = str(v).strip().replace(",", "")
    return float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v) else None


def national():
    out = []
    for r in read("kiso2025_t014_children_by_year.csv"):
        if r and r[0].startswith("構成割合"):
            break
        m = re.match(r"^(\d{4})\(", r[0]) if r else None
        if m:
            out.append(dict(year=int(m.group(1)), total=num(r[1]), child=num(r[2]), c1=num(r[3]), c2=num(r[4]), c3=num(r[5]), c4=num(r[6]), nochild=num(r[7])))
    df = pd.DataFrame(out).dropna()
    assert (abs(df.child + df.nochild - df.total) <= 2).all()
    return df


KEYS = {"総数": "total", "単独世帯": "single", "核家族世帯": "nuclear", "夫婦と未婚の子のみの世帯": "couple_child",
        "ひとり親と未婚の子のみの世帯": "single_parent", "三世代世帯": "three_gen", "その他の世帯": "other"}


def structure():
    out = []
    for y, name in [(2013, "kiso2013_t075_children_by_structure.csv"), (2025, "kiso2025_t089_children_by_structure.csv")]:
        d = dict(year=y)
        for r in read(name):
            k = r[0].strip().replace("　", "") if r else ""
            if k in KEYS:
                d[KEYS[k]] = num(r[1])
        out.append(d)
    return pd.DataFrame(out)


def pref_rows(name):
    """全国の行のあとの47行（都道府県、JIS順）を返す。"""
    rows = read(name)
    i = next(k for k, r in enumerate(rows) if r and re.sub(r"[\s　]", "", r[0]) == "全国")
    return rows[i], rows[i + 1:i + 48]


def pref():
    out = []
    for y, a, b in [(2013, "kiso2013_t015_children_by_pref.csv", "kiso2013_t017_children_structure_by_pref.csv"),
                    (2025, "kiso2025_t153_children_by_pref.csv", "kiso2025_t155_children_structure_by_pref.csv")]:
        na, ra = pref_rows(a); nb, rb = pref_rows(b)
        for p, (x, z) in enumerate([(na, nb)] + list(zip(ra, rb))):
            assert num(x[2]) == num(z[1]), (y, p)
            out.append(dict(year=y, pref=p, name=re.sub(r"[\s　]", "", x[0]), households=num(x[1]), child=num(x[2]), nochild=num(x[6]),
                            nuclear=num(z[2]), couple_child=num(z[3]), single_parent=num(z[4]), three_gen=num(z[5]), other=num(z[6])))
    df = pd.DataFrame(out)
    # 国勢調査 2025（原数値）：一般世帯数と18歳未満世帯員のいる一般世帯数
    cen = {}
    ws = openpyxl.load_workbook(RAW / "census2025_t9_1.xlsx", read_only=True).worksheets[0]
    for r in ws.iter_rows(min_row=11, values_only=True):
        m = re.match(r"^(\d{2})000_", str(r[2])) if r[2] else None
        if m and str(r[4]).startswith("0_総数"):
            cen[int(m.group(1))] = (float(r[5]), float(r[9]))
    assert len(cen) == 48
    df["census_households"] = df.pref.map(lambda p: cen[p][0]).where(df.year == 2025)
    df["census_u18"] = df.pref.map(lambda p: cen[p][1]).where(df.year == 2025)
    return df


def main():
    national().to_csv(ROOT / "data" / "national.csv", index=False, float_format="%.0f")
    structure().to_csv(ROOT / "data" / "structure.csv", index=False, float_format="%.0f")
    P = pref()
    P.to_csv(ROOT / "data" / "pref.csv", index=False, float_format="%.0f")
    print(P[P.pref.isin([0, 1, 2, 47])].to_string())


if __name__ == "__main__":
    main()
