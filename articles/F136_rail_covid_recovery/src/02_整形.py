"""e-Stat 鉄道輸送統計調査 表2-2（月次）から、運輸局別・業態別の定期／定期外／計の旅客数（千人）を縦長の表にする。"""
import csv, io, json, re, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
j = json.load(open(ROOT / "data/raw/f136_rail_t22.json", encoding="utf-8"))

NAMES = {"北海道": "北海道", "東北": "東北", "関東": "関東", "北陸信越": "北陸信越", "中部": "中部",
         "近畿": "近畿", "中国": "中国", "四国": "四国", "九州": "九州", "沖縄": "沖縄",
         "ＪＲ旅客会社": "JR", "新幹線": "新幹線", "民鉄（JR以外）": "民鉄", "大手": "大手民鉄",
         "中小": "中小民鉄", "公営": "公営", "全国計": "全国"}

def num(s):
    s = (s or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None

rows = []
for key, text in j["csv"].items():
    ym = key[3:]
    for f in csv.reader(io.StringIO(text)):
        if len(f) < 10:
            continue
        lab = re.sub(r"\s|　", "", f[1]) or re.sub(r"\s|　", "", f[0])
        if lab not in NAMES:
            continue
        rows.append(dict(ym=ym, unit=NAMES[lab], km=num(f[2]), teiki=num(f[3]), teikigai=num(f[6]), total=num(f[9])))
df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["ym"] + "-01")
assert df.groupby("ym").size().eq(17).all(), df.groupby("ym").size().value_counts()
# 計 = 定期 + 定期外 の確認
chk = (df["teiki"] + df["teikigai"] - df["total"]).abs().max()
print("max |定期+定期外-計| =", chk)
df = df.sort_values(["unit", "date"])
df.to_csv(ROOT / "data/rail_monthly_t22.csv", index=False, encoding="utf-8")
print(df.shape, df["ym"].min(), df["ym"].max())
