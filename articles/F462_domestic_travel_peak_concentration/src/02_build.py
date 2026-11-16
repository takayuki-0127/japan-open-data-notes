"""推移表のシート「旧2-2」から、都道府県×年×月の日本人延べ宿泊者数を取り出す。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))


def era(lab):
    m = re.fullmatch(r"(平成|令和)(元|\d+)年", norm(lab))
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return (1988 if m.group(1) == "平成" else 2018) + n


d = pd.read_excel(RAW / "shukuhaku_suiihyo.xlsx", sheet_name="旧2-2", header=None)
years = d.iloc[2].ffill()
rows = []
for i in range(4, len(d)):
    lab = norm(d.iat[i, 0])
    if lab == "全国":
        code, pref = 0, "全国"
    elif re.fullmatch(r"\d{2}\D+", lab):
        code, pref = int(lab[:2]), lab[2:]
    else:
        continue
    for j in range(1, d.shape[1]):
        m = norm(d.iat[3, j])
        if not m.endswith("月"):
            continue
        rows.append({"code": code, "pref": pref, "year": era(years[j]), "month": int(m[:-1]), "stays": float(d.iat[i, j])})
out = pd.DataFrame(rows).sort_values(["code", "year", "month"])
# 47都道府県の合計が全国と一致するか
chk = out[out.code > 0].groupby(["year", "month"]).stays.sum() - out[out.code == 0].set_index(["year", "month"]).stays
assert chk.abs().max() <= 50 * 47, chk.abs().max()
assert out.groupby("code").size().nunique() == 1 and out.year.min() == 2011 and out.year.max() == 2025
out.to_csv(ROOT / "data" / "japanese_stays_monthly.csv", index=False, float_format="%.0f")
print(len(out), "行", "全国と47都道府県の合計の差の最大", chk.abs().max())
