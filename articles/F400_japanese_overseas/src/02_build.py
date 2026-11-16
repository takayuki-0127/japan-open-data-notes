"""data/raw の Excel から、分析用の CSV を作る（オフライン）。
- data/national.csv : 1991〜2025年の総数・長期滞在者・永住者（男女別）
- data/country.csv  : 2019年・2025年の国（地域）別（地域、総数、長期滞在者、永住者）
- data/region_2006_2015.csv : 2006〜2015年の地域別（総数・長期滞在者・永住者）
"""
import pathlib, re, unicodedata
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REGIONS = ["アジア", "大洋州", "北米", "中米", "南米", "西欧", "東欧・旧ソ連", "中東", "アフリカ", "南極"]


# 2019年版と2025年版で表記が違う国（地域）名を、2025年版の表記にそろえる
ALIAS = {"アルバ島(蘭領)": "アルバ(蘭領)", "カーボヴェルデ": "カーボベルデ", "キュラカオ島(蘭領)": "キュラソー(蘭領)",
         "グァドループ島(仏領)": "グアドループ(仏領)", "グアム(在ハガッニャ総領事館)": "グアム(米領)",
         "セントクリストファー・ネーヴィス": "セントクリストファー・ネービス", "セントマーティン島(蘭領)": "シント・マールテン(蘭領)",
         "マケドニア旧ユーゴスラビア共和国": "北マケドニア", "マラウィ": "マラウイ", "マルティニーク島(仏領)": "マルチニーク(仏領)",
         "レ・ユニオン(仏領)": "レユニオン(仏領)", "北マリアナ諸島(米領-在サイパン事)": "北マリアナ諸島(米領-サイパン)",
         "イスラエル及びガザ地区等": "イスラエル・パレスチナ", "イスラエル": "イスラエル・パレスチナ", "パレスチナ": "イスラエル・パレスチナ"}


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"\s+", "", s)


def year_of(s):
    m = re.search(r"\((\d{4})年\)", norm(s))
    return int(m.group(1)) if m else None


def num(v):
    return None if v is None or isinstance(v, str) else float(v)


def national():
    ws = openpyxl.load_workbook(RAW / "mofa_overseas_2025.xlsx", read_only=True)["邦人数推移 "]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    out = {}
    for i, r in enumerate(rows):
        if i < 80 and len(r) > 8 and r[3] is not None and year_of(r[3]):
            out.setdefault(year_of(r[3]), {}).update(long=num(r[4]), perm=num(r[6]), total=num(r[8]))
        if i >= 80 and len(r) > 11 and r[2] is not None and year_of(r[2]):
            y = year_of(r[2]); f = rows[i + 1]
            out[y].update(total_m=num(r[5]), long_m=num(r[8]), perm_m=num(r[11]),
                          total_f=num(f[5]), long_f=num(f[8]), perm_f=num(f[11]))
            assert out[y]["total"] == num(r[3]) and out[y]["long"] == num(r[6]) and out[y]["perm"] == num(r[9])
    df = pd.DataFrame(out).T.sort_index()
    df.index.name = "year"
    return df


def country(fname, sheet, year):
    ws = openpyxl.load_workbook(RAW / fname, read_only=True)[sheet]
    reg = None; out = []
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i < 2:
            continue
        c0 = norm(r[0]) if r[0] is not None else ""
        if c0.startswith("合計") or c0.startswith("地域別"):
            break
        if c0:
            reg = re.sub(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVX]+", "", c0)
            assert reg in REGIONS, reg
        if r[1] is None:
            continue
        name = norm(r[1])
        out.append(dict(year=year, region=reg, country=ALIAS.get(name, name), total=num(r[4]), long=num(r[6]), perm=num(r[9])))
    return pd.DataFrame(out)


def region_totals(fname, sheet):
    """表の下にある地域別総数の行（確かめ用）。"""
    ws = openpyxl.load_workbook(RAW / fname, read_only=True)[sheet]
    seen = False; out = {}
    for r in ws.iter_rows(values_only=True):
        c0 = norm(r[0]) if r[0] is not None else ""
        if c0.startswith("合計"):
            seen = True; out["合計"] = (num(r[4]), num(r[6]), num(r[9])); continue
        if seen and c0:
            reg = re.sub(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVX]+", "", c0)
            if reg in REGIONS:
                out[reg] = (num(r[4]), num(r[6]), num(r[9]))
    return out


def region_2015():
    wb = openpyxl.load_workbook(RAW / "mofa_overseas_2015.xlsx", read_only=True)
    out = []
    for kind, sh in [("total", "2.3.1 地域別邦人数推移"), ("perm", "2.3.2 地域別永住者数推移"), ("long", "2.3.3 地域別長期滞在者数推移")]:
        rows = [list(r) for r in wb[sh].iter_rows(values_only=True)]
        for r in rows[38:48]:
            v = [c for c in r if c is not None]
            reg = norm(v[0]); assert reg in REGIONS, reg
            for k, y in enumerate(range(2006, 2016)):
                out.append(dict(year=y, region=reg, kind=kind, n=float(v[1 + k])))
    return pd.DataFrame(out)


def main():
    nat = national()
    nat.to_csv(ROOT / "data" / "national.csv", float_format="%.0f")
    c = pd.concat([country("mofa_overseas_2019.xlsx", "一覧表 ", 2019), country("mofa_overseas_2025.xlsx", "一覧表", 2025)])
    c.to_csv(ROOT / "data" / "country.csv", index=False, float_format="%.0f")
    chk = []
    for y, f, s in [(2019, "mofa_overseas_2019.xlsx", "一覧表 "), (2025, "mofa_overseas_2025.xlsx", "一覧表")]:
        t = region_totals(f, s); cy = c[c.year == y]
        for reg in ["合計"] + REGIONS:
            sub = cy if reg == "合計" else cy[cy.region == reg]
            got = (sub.total.sum(), sub.long.sum(), sub.perm.sum())
            chk.append(dict(year=y, region=reg, table_total=t[reg][0], sum_total=got[0], table_long=t[reg][1], sum_long=got[1], table_perm=t[reg][2], sum_perm=got[2]))
    pd.DataFrame(chk).to_csv(ROOT / "data" / "check_region_sums.csv", index=False, float_format="%.0f")
    region_2015().to_csv(ROOT / "data" / "region_2006_2015.csv", index=False, float_format="%.1f")
    print(nat.tail(3)); print(pd.DataFrame(chk))


if __name__ == "__main__":
    main()
