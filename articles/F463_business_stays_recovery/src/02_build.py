"""年の確定値の Excel から、宿泊目的割合別（第2表）、施設タイプ別（第4表）、宿泊目的割合×居住地（第9表）の年計を取り出す。"""
import pathlib, re, unicodedata
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; OUT = ROOT / "data"
YEARS = [2015, 2016, 2017, 2018, 2019, 2022, 2023, 2024, 2025]


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))


def num(v):
    if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
        return float(v)
    return 0.0 if norm(v) in ("-", "…", "nan") else float(norm(v).replace(",", ""))


def area(lab):
    lab = norm(lab)
    if lab.endswith("計") and "1~12月" in lab:
        return "全国"
    m = re.fullmatch(r"(\d{2})?(\D+[都道府県])", lab)
    return m.group(2) if m and not lab.endswith("運輸局") else None


purpose, types, resid = [], [], []
for y in YEARS:
    x = pd.ExcelFile(RAW / f"shukuhaku_{y}.xlsx")
    d = x.parse("第2表(年計)", header=None)
    assert "50%以上" in norm(d.iat[5, 2]) and "50%未満" in norm(d.iat[5, 3])
    for i in range(6, len(d)):
        a = area(d.iat[i, 0])
        if a:
            t, hi, lo = num(d.iat[i, 1]), num(d.iat[i, 2]), num(d.iat[i, 3])
            purpose.append({"year": y, "area": a, "total": t, "tourism50plus": hi, "tourism_under50": lo, "unknown": t - hi - lo})
    d = x.parse("第4表(年計)", header=None)
    names = [norm(d.iat[4, j]) for j in range(2, 8)]
    assert names == ["旅館", "リゾートホテル", "ビジネスホテル", "シティホテル", "簡易宿所", "会社・団体の宿泊所"], names
    assert "外国人" in norm(d.iat[3, 8])
    for i in range(6, len(d)):
        a = area(d.iat[i, 0])
        if a:
            for k, nm in enumerate(names):
                types.append({"year": y, "area": a, "type": nm, "total": num(d.iat[i, 2 + k]), "foreign": num(d.iat[i, 9 + k])})
    d = x.parse("第9表(年計)", header=None)
    assert "50%以上" in norm(d.iat[4, 4]) and "50%未満" in norm(d.iat[4, 7])
    for i in range(6, len(d)):
        a = area(d.iat[i, 0])
        if a == "全国":
            resid.append({"year": y, "group": "tourism50plus", "total": num(d.iat[i, 4]), "in_pref": num(d.iat[i, 5]), "out_pref": num(d.iat[i, 6])})
            resid.append({"year": y, "group": "tourism_under50", "total": num(d.iat[i, 7]), "in_pref": num(d.iat[i, 8]), "out_pref": num(d.iat[i, 9])})
P = pd.DataFrame(purpose); T = pd.DataFrame(types); Rz = pd.DataFrame(resid)
for y in YEARS:  # 47都道府県の合計と全国の一致（10人泊単位の丸めの差まで）
    p = P[P.year == y]; assert len(p) == 48, (y, len(p))
    diff = (p[p.area != "全国"][["total", "tourism50plus", "tourism_under50"]].sum() - p[p.area == "全国"][["total", "tourism50plus", "tourism_under50"]].iloc[0]).abs().max()
    assert diff < 1e4, (y, diff)
    t = T[(T.year == y) & (T.area == "全国")]
    assert t.total.sum() <= p[p.area == "全国"].total.iloc[0] + 1e4, y  # タイプ不詳があるので合計は全体以下
P.to_csv(OUT / "stays_by_purpose.csv", index=False, float_format="%.0f")
T.to_csv(OUT / "stays_by_type.csv", index=False, float_format="%.0f")
Rz.to_csv(OUT / "stays_purpose_residence.csv", index=False, float_format="%.0f")
print(P[P.area == "全国"].to_string())
