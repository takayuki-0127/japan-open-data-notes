"""02 整形: 住民基本台帳（総計・外国人住民、2014〜2026年1月1日）と
在留外国人統計（市区町村別 国籍・地域別 2015・2022年末）を縦長の CSV にする。
入力: data/raw/f140_foreign_data.json.gz（01_取得.md の手順で作成）
出力: data/juki_panel.csv, data/zairyu_muni_nat.csv, data/zairyu_pref_nat.csv
"""
import gzip, json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = json.load(gzip.open(ROOT / "data/raw/f140_foreign_data.json.gz"))

PREFS = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"]


def num(x):
    if x is None or x == "-" or x == "":
        return 0
    try:
        return float(x)
    except ValueError:
        return 0


# ---------- 住民基本台帳 ----------
rows = []
for key, tab in d["juki"].items():
    year, kind = key.split("_")
    for r in tab:
        c = r[0]
        if not (isinstance(c, str) and re.fullmatch(r"\d{6}", c)):
            continue
        code5 = c[:5]
        name = r[2]
        if name in (None, "-", ""):
            continue  # 都道府県の行
        rec = dict(year=int(year), kind=kind, code5=code5, pref=r[1], name=name,
                   pop=num(r[5]))
        if kind == "for":
            rec.update(in_dom=num(r[7]), in_abr=num(r[8]), births=num(r[10]),
                       oth_in=num(r[13]), out_dom=num(r[15]), out_abr=num(r[16]),
                       deaths=num(r[18]), oth_out=num(r[21]))
        else:
            rec.update(in_dom=num(r[7]), in_abr=num(r[8]), births=num(r[10]),
                       oth_in=num(r[11]), out_dom=num(r[13]), out_abr=num(r[14]),
                       deaths=num(r[16]), oth_out=num(r[17]))
        rows.append(rec)
j = pd.DataFrame(rows)
tot = j[j.kind == "tot"].drop(columns="kind").add_suffix("_tot").rename(
    columns={"year_tot": "year", "code5_tot": "code5"})
fo = j[j.kind == "for"].drop(columns="kind").add_suffix("_for").rename(
    columns={"year_for": "year", "code5_for": "code5"})
p = fo.merge(tot[["year", "code5", "pop_tot", "in_dom_tot", "in_abr_tot", "births_tot",
                  "out_dom_tot", "out_abr_tot", "deaths_tot"]], on=["year", "code5"], how="left")
p = p.rename(columns={"pref_for": "pref", "name_for": "name"})
# 政令指定都市の「市」合計行を除き、区を単位にする（区がある市の合計行は code5 の3桁目が1で末尾00）
ward_cities = set()
for y, nm in zip(p.year, p.name):
    m = re.match(r"(.+?市).+区$", nm)
    if m:
        ward_cities.add((y, m.group(1)))
is_city_total = pd.Series([(y, nm) in ward_cities for y, nm in zip(p.year, p.name)], index=p.index)
p["is_city_total"] = is_city_total
# 「〇〇郡」の合計行を除く（名前が市・区・町・村で終わらない行）
p = p[p.name.str.contains("[市区町村]$")].copy()
p.to_csv(ROOT / "data/juki_panel.csv", index=False)
print("juki rows", len(p), "city totals", int(is_city_total.sum()))

# ---------- 在留外国人統計 市区町村×国籍 ----------
z = d["zairyu"]
out = []
# 2022: コードあり
a = z["m2022"][0]["a"]
hdr = a[1]
for r in a[2:]:
    if not (isinstance(r[0], str) and re.fullmatch(r"\d{5}", r[0])):
        continue
    for k in range(2, 14):
        if hdr[k]:
            out.append(dict(year=2022, code5=r[0], name=r[1], nat=hdr[k], n=num(r[k])))
# 2015: 名前だけ（都道府県・市・区）
a = z["m2015"][0]["a"]
hdr = a[1]
pref = None
city = None
for r in a[2:]:
    if r[0] and isinstance(r[0], str) and not r[0].startswith("注"):
        pref = r[0].replace("　", "").strip()
    if r[1]:
        city = str(r[1]).strip()
    nm = r[2] if r[2] else r[1]
    if nm is None or not isinstance(r[3], (int, float)):
        continue
    for k in range(3, 13):
        if hdr[k]:
            out.append(dict(year=2015, pref=pref, city=city, name=str(nm).strip(),
                            is_ward=bool(r[2]), has_wards=None, nat=hdr[k], n=num(r[k])))
zm = pd.DataFrame(out)
zm.to_csv(ROOT / "data/zairyu_muni_nat_raw.csv", index=False)
print("zairyu muni rows", len(zm))

# ---------- 在留外国人統計 都道府県×国籍（2015・2018） ----------
pr = []
for key, yr in [("p2015", 2015), ("p2018", 2018)]:
    a = z[key][0]["a"]
    hdr = a[1]
    for r in a[3:]:
        nm = r[1]
        if not nm:
            continue
        for k in range(2, len(hdr)):
            if hdr[k]:
                pr.append(dict(year=yr, pref=str(nm).strip(), nat=hdr[k], n=num(r[k])))
pd.DataFrame(pr).to_csv(ROOT / "data/zairyu_pref_nat.csv", index=False)

# ---------- 在留外国人統計 市区町村の総数（2023・2025、確認用） ----------
tt = []
for r in z["a2023"][0]["a"][2:]:
    if isinstance(r[1], str) and re.fullmatch(r"\d{5}", r[1]):
        tt.append(dict(year=2023, code5=r[1], name=r[2], n=num(r[3])))
for r in z["t2025"][0]["a"][5:]:
    if isinstance(r[0], str) and re.fullmatch(r"\d{5}", r[0]):
        tt.append(dict(year=2025, code5=r[0], name=r[3], n=num(r[4])))
pd.DataFrame(tt).to_csv(ROOT / "data/zairyu_muni_total.csv", index=False)
print("done")
