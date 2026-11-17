"""data/raw の月別の表（第3-12表、141か月）と長期時系列（表2）から、世帯の区分 × 月 × 項目の長い表を作る。ネットにはつながない。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# 列の位置（「60歳以上の者がいる世帯」の列からのずれ）。旧様式・新様式とも同じ並び
GROUPS = {"m65_nowork": 10,       # 世帯主が65歳以上・無職世帯（年金の世帯）
          "m65_worker": 8,        # 世帯主が65歳以上・勤労者世帯
          "u65_worker": 12,       # 世帯主が65歳未満・勤労者世帯（対照）
          "couple_nowork": 30,    # 夫65歳以上・妻60歳以上の夫婦のみ・無職世帯
          "eld_nowork": 25,       # 男65歳以上・女60歳以上の者のみの世帯・無職世帯
          "eld_nowork_inc1": 26,  # 同・年間収入250万円未満
          "eld_nowork_inc2": 27,  # 同・250〜349万円
          "eld_nowork_inc3": 28}  # 同・350万円以上
ITEMS = ["集計世帯数", "世帯主の年齢", "実収入", "公的年金給付", "消費支出", "食料", "外食", "住居", "光熱・水道",
         "家具・家事用品", "被服及び履物", "交通・通信", "教育", "教養娯楽", "その他の消費支出", "交際費",
         "預貯金", "預貯金引出"]


def norm(s):
    s = re.sub(r"\s+", "", str(s))
    s = re.sub(r"^[0-9.]+", "", s)
    return re.sub(r"\(歳\)$", "", s)


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return np.nan


rows = []
for p in sorted((RAW / "t3_12").glob("kakei_3-12_*")):
    y, m = map(int, re.search(r"(\d{4})-(\d{2})", p.name).groups())
    x = pd.read_excel(p, header=None, dtype=str).fillna("")
    new = str(x.iat[8, 11]).strip() == "用途分類"
    if new:
        base, labels = 13, [norm(c) for c in x.iloc[:, 11]]
    else:
        base = 15 if x.shape[1] == 50 else 16
        labels = [norm("".join(str(c) for c in x.iloc[i, 7:15])) for i in range(len(x))]
    start = next(i for i, l in enumerate(labels) if l.startswith("世帯数分布"))
    for item in ITEMS:
        i = next(i for i in range(start, len(labels)) if labels[i] == item)   # 最初に出てくる行（交際費の中の「食料」などより前）
        for g, off in GROUPS.items():
            rows.append({"year": y, "month": m, "group": g, "item": item, "value": num(x.iat[i, base + off])})
d = pd.DataFrame(rows).sort_values(["group", "item", "year", "month"]).reset_index(drop=True)

# 長期時系列 表2（二人以上の世帯全体）の消費支出と10費目ほか
v = pd.read_excel(RAW / "kakei_ts2_youto_monthly.xlsx", header=None, dtype=str, sheet_name="支出金額（月）").fillna("")
cols, cur = [], None
for k in range(15, v.shape[1]):
    yy = re.match(r"^(\d{4})年", str(v.iat[9, k]).strip())
    if yy:
        cur = int(yy.group(1))
    mm = re.match(r"^(\d{1,2})\s*月", str(v.iat[11, k]).strip().replace("　", " "))
    if cur and mm:
        cols.append((k, cur, int(mm.group(1))))
labels = [norm("".join(str(c) for c in v.iloc[i, 7:15])) for i in range(len(v))]
add = []
for item in ["消費支出", "食料", "外食", "住居", "光熱・水道", "家具・家事用品", "被服及び履物", "交通・通信", "教育",
             "教養娯楽", "その他の消費支出", "交際費"]:
    i = next(i for i, l in enumerate(labels) if l == item)
    for k, yy, mm in cols:
        if 2015 <= yy and (yy, mm) <= (2026, 9):
            add.append({"year": yy, "month": mm, "group": "all_2plus", "item": item, "value": num(v.iat[i, k])})
d = pd.concat([d, pd.DataFrame(add)], ignore_index=True).sort_values(["group", "item", "year", "month"]).reset_index(drop=True)
d.to_csv(ROOT / "data" / "monthly_groups.csv", index=False)
print("rows", len(d), "months", d[["year", "month"]].drop_duplicates().shape[0], "missing", int(d.value.isna().sum()))
print(d[d.value.isna()].groupby(["group", "item"]).size())
