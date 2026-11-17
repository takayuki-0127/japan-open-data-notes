"""市町村別決算状況調から、年度×団体の表 data/muni_year.csv を作る（金額は千円）。
列：year, kind（city/town）, pref, code（2009年度は表に無いので空）, name, pop（住民基本台帳人口）, sfs（標準財政規模）,
rdsr（実質公債費比率、%）, fbr_raw（将来負担比率の表の値。「－」は空）, debt（地方債現在高）, fund（積立金現在高）"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
YEARS = [2009, 2014, 2019, 2024]


def norm(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def num(v):
    s = norm(v)
    if s in ("-", "nan", "", "…", "x", "－"):
        return float("nan")
    return float(s)


def find_cols(d, want):
    """見出しの行（9〜10行目）から、欲しい列の位置を文字で探す。"""
    lab = {j: norm(d.iloc[9, j]) + "|" + norm(d.iloc[10, j]) for j in range(d.shape[1])}
    out = {}
    for k, key in want.items():
        hit = [j for j, s in lab.items() if key in s]
        assert len(hit) >= 1, (k, key)
        out[k] = hit[0]
    return out


def read(path, want):
    d = pd.read_excel(path, header=None, dtype=object)
    c = find_cols(d, {"name": "団体名", **want})
    code_col = c["name"] - 1 if "団体コード" in norm(d.iloc[9, c["name"] - 1]) else None
    rows, pref = [], None
    for i in range(15, len(d)):
        name = norm(d.iloc[i, c["name"]])
        first = list(want)[0]
        v = d.iloc[i, c[first]]
        if name != "nan" and norm(v) == "nan" and re.fullmatch(r".+[都道府県]", name):
            pref = name
            continue
        if name == "nan" or "計" in name or norm(v) == "nan" or name.startswith("("):
            continue  # 空の行・合計・「(うち政令指定都市)」などの内訳の行
        if pref == "東京都" and name.endswith("区"):
            continue  # 東京23区は標準財政規模などが出ない（都と分けて算定）ため除く
        rows.append({"pref": pref, "code": norm(d.iloc[i, code_col]) if code_col is not None else "", "name": name,
                     **{k: num(d.iloc[i, j]) for k, j in c.items() if k != "name"}})
    return pd.DataFrame(rows)


def main():
    out = []
    for y in YEARS:
        for kind in ["city", "town"]:
            ext = "xls" if y <= 2014 else "xlsx"
            a = read(RAW / f"{y}_{kind}_01.{ext}", {"pop": "住民基本台帳登載人口", "sfs": "標準財政規模", "rdsr": "実質公債費比率", "fbr_raw": "将来負担比率"})
            b = read(RAW / f"{y}_{kind}_05.{ext}", {"debt": "地方債現在高", "fund": "積立金現在高"})
            assert len(a) == len(b) and (a.name.values == b.name.values).all() and (a.pref.values == b.pref.values).all(), (y, kind, len(a), len(b))
            z = pd.concat([a, b[["debt", "fund"]]], axis=1)
            z.insert(0, "kind", kind); z.insert(0, "year", y)
            out.append(z)
    d = pd.concat(out, ignore_index=True)
    assert d.pref.notna().all() and d.pref.nunique() == 47
    assert d["pop"].notna().all() and d.sfs.notna().all() and d.rdsr.notna().all()
    d = d[["year", "kind", "pref", "code", "name", "pop", "sfs", "rdsr", "fbr_raw", "debt", "fund"]]
    d.to_csv(ROOT / "data" / "muni_year.csv", index=False)
    print(d.groupby(["year", "kind"]).size().unstack(), d.groupby("year")["pop"].sum(), d.groupby("year").fbr_raw.apply(lambda s: s.isna().mean()))
    print(d[d.name.str.endswith("区")].head())


if __name__ == "__main__":
    main()
