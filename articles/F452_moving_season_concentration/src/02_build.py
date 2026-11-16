"""長期時系列表と月報の年齢別の表から、月別の移動者数を縦長の表にする。
data/long_monthly.csv（日本人、1954〜2025年、都道府県間・都道府県内）、data/age_monthly.csv（移動者、2019・2023〜2025年）"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s)))

# 長期時系列表
v = pd.read_excel(RAW / "long_t1.xlsx", header=None, sheet_name="総数")
years = [int(y) if str(y).strip().isdigit() else None for y in v.iloc[6, 2:].tolist()]  # 年は数値と文字が混ざっている
recs = []
for start, kind in [(23, "intra"), (38, "inter")]:
    assert n(v.iloc[start, 0]).startswith("都道府県内" if kind == "intra" else "都道府県間")
    for k in range(12):
        row = v.iloc[start + 2 + k]
        assert n(row[0]) == f"{k + 1}月", row[0]
        for y, val in zip(years, row[2:].tolist()):
            if y is not None and isinstance(val, (int, float)) and not pd.isna(val):
                recs.append(dict(kind=kind, year=int(y), month=k + 1, movers=int(val)))
long = pd.DataFrame(recs).sort_values(["kind", "year", "month"])
long.to_csv(ROOT / "data" / "long_monthly.csv", index=False)

# 月報 表番号3-1：全国の行の 総数・年齢19階級
AGES = ["total", "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54",
        "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"]
recs = []
for f in sorted(RAW.glob("monthly_t3_1_*")):
    ym = re.search(r"(\d{4})-(\d{2})", f.name).groups()
    s = list(pd.read_excel(f, header=None, sheet_name=None).values())[0]
    for _, row in s.iterrows():
        cells = row.tolist()
        idx = [i for i, c in enumerate(cells) if isinstance(c, str) and n(c) == "全国"]
        if not idx:
            continue
        nums = [float(c) for c in cells[idx[0] + 1:] if isinstance(c, (int, float)) and not pd.isna(c)][:20]
        if len(nums) == 20:
            recs.append(dict(year=int(ym[0]), month=int(ym[1]), **dict(zip(AGES, nums))))
            break
age = pd.DataFrame(recs).sort_values(["year", "month"])
assert len(age) == 48, len(age)
assert (abs(age[AGES[1:]].sum(axis=1) - age.total) <= age.total * 0.002).all()  # 年齢不詳はほぼない
age.to_csv(ROOT / "data" / "age_monthly.csv", index=False)
print(long.groupby("kind").year.agg(["min", "max"]), age.groupby("year").total.sum())
