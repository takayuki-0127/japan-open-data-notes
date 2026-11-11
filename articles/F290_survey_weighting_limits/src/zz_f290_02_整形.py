"""就業構造基本調査 第52表（2017・2022）を、年×男女×年齢×雇用形態×本業の所得×本業の就業時間×副業の有無 の長い表にそろえる。
- 年齢は10歳刻み（2022年の5歳刻みを2017年に合わせる）
- 雇用形態は 正規／非正規／役員（雇用者−正規−非正規）／自営業主など（総数−雇用者）
- 本業の就業時間は 200日未満／200日以上で週35時間未満／35〜59時間／60時間以上（両年で共通の区切り）
入力: data/raw/000040077317.csv(.gz)（2022）, data/raw/000031729397.csv(.gz)（2017）
出力: data/side_job_long.csv（F139 と同じ整形。F147 はこの長い表を「本当の多重クロス表」として使う）
"""
import csv, re, gzip
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

def rd(name):
    """data/raw/<name>.csv があればそれを、なければ .csv.gz を読む"""
    p = RAW / (name + ".csv")
    f = open(p, encoding="utf-8") if p.exists() else gzip.open(RAW / (name + ".csv.gz"), "rt", encoding="utf-8")
    return list(csv.reader(f))

def num(v):
    v = v.strip().replace(",", "")
    return 0.0 if v in ("-", "", "…", "X") else float(v)

AGE10 = {"01": "15〜24歳", "02": "15〜24歳", "03": "25〜34歳", "04": "25〜34歳", "05": "35〜44歳", "06": "35〜44歳",
         "07": "45〜54歳", "08": "45〜54歳", "09": "55〜64歳", "10": "55〜64歳", "11": "65〜74歳", "12": "65〜74歳", "13": "75歳以上"}
AGE17 = {"1": "15〜24歳", "2": "25〜34歳", "3": "35〜44歳", "4": "45〜54歳", "5": "55〜64歳", "6": "65〜74歳", "7": "75歳以上"}

def hours_bin(code_label):
    """日数・時間の項目名を4区分に。総数は'総数'、集計区分（200日未満の内訳・日数の小計）は None"""
    code, lab = code_label.split("_", 1)
    if code == "0":
        return "総数"
    if code == "1":
        return "200日未満"
    if len(code) == 1 or code in ("11", "12", "13"):
        return None  # 日数の小計、200日未満の内訳
    m = re.match(r"(\d+)～(\d+)時間|(\d+)時間未満|(\d+)時間以上", lab)
    if "時間未満" in lab:
        return "200日以上・週35時間未満"
    lo = int(re.search(r"(\d+)", lab).group(1))
    return "200日以上・週60時間以上" if lo >= 60 else "200日以上・週35〜59時間"

def emp_split(tot, empl, reg, irr):
    return {"正規": reg, "非正規": irr, "役員": max(empl - reg - irr, 0.0), "自営業主など": max(tot - empl, 0.0)}

rows = []
# 2022
r = rd("000040077317")[9:]
for x in r:
    sex, age, side, days, inc = x[3], x[5], x[7], x[9], x[11]
    if sex.startswith("0") or age.startswith("00") or side.startswith("0") or inc.startswith("00"):
        continue
    hb = hours_bin(days)
    if hb is None:
        continue
    vals = [num(v) for v in x[12:16]]
    for emp, n in emp_split(*vals).items():
        rows.append(dict(year=2022, sex=sex.split("_")[1], age=AGE10[age.split("_")[0]], side=side.split("_")[1],
                         hours=hb, income=inc, emp=emp, n=n))
# 2017
r = [x for x in rd("000031729397") if len(x) > 3 and x[1] == "D"]
for x in r:
    sex, age, side, inc, days = x[4], x[5], x[6], x[7], x[8]
    if sex.startswith("0") or age.startswith("0_") or side.startswith("0") or inc.startswith("00"):
        continue
    hb = hours_bin(days)
    if hb is None:
        continue
    vals = [num(v) for v in x[15:19]]
    for emp, n in emp_split(*vals).items():
        rows.append(dict(year=2017, sex=sex.split("_")[1], age=AGE17[age.split("_")[0]], side=side.split("_")[1],
                         hours=hb, income=inc, emp=emp, n=n))

df = pd.DataFrame(rows)
df = df.groupby(["year", "sex", "age", "side", "hours", "income", "emp"], as_index=False)["n"].sum()
df.to_csv(ROOT / "data" / "side_job_long.csv", index=False, encoding="utf-8")

# 確認：総数（hours=総数）と公表の全国総数
for y in (2017, 2022):
    d = df[(df.year == y) & (df.hours == "総数")]
    print(y, "有業者（所得・年齢・男女の内訳の合計）", int(d.n.sum()), "副業あり", int(d[d.side == "副業あり"].n.sum()),
          "率 %.2f%%" % (100 * d[d.side == "副業あり"].n.sum() / d.n.sum()))
    h = df[(df.year == y) & (df.hours != "総数")]
    print("   就業時間4区分の合計", int(h.n.sum()))
print(len(df), "行")
