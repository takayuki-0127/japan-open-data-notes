"""F117 02 整形：国民生活基礎調査（令和7年）と国勢調査の表を、比べやすい形にそろえる。

入力：data/raw/*.csv（国民生活基礎調査）、data/raw/*.xlsx（国勢調査）
出力：data/ の下の CSV
"""
import csv, re
from pathlib import Path
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"


def read_csv_rows(name):
    with open(RAW / f"{name}.csv", encoding="utf-8") as f:
        return list(csv.reader(f))


def year_of(label):
    m = re.match(r"(\d{4})\(", label or "")
    return int(m.group(1)) if m else None


def num(x):
    x = (x or "").strip().replace(",", "")
    if x in ("-", ""):
        return 0.0
    try:
        return float(x)
    except ValueError:
        return None


# ---------- 国民生活基礎調査 世帯票 第1表（世帯人員）・第2表（世帯構造）：推計数（千世帯）----------
def first_block(rows):
    out, on = [], False
    for r in rows:
        if r and r[0].startswith("推計数"):
            on = True
            continue
        if r and r[0].startswith("構成割合"):
            break
        if on and year_of(r[0]):
            out.append(r)
    return out


s01 = []
for r in first_block(read_csv_rows("s01")):
    y = year_of(r[0])
    if y < 1986:
        continue
    v = [num(x) for x in r[1:8]]
    s01.append(dict(year=y, total=v[0], n1=v[1], n2=v[2], n3=v[3], n4=v[4], n5=v[5], n6p=v[6]))
s01 = pd.DataFrame(s01)
s01.to_csv(OUT / "survey_households_size.csv", index=False)

s02 = []
for r in first_block(read_csv_rows("s02")):
    y = year_of(r[0])
    if y < 1986:
        continue
    v = [num(x) for x in r[1:11]]
    s02.append(dict(year=y, total=v[0], single=v[1], single_dorm=v[2], single_other=v[3], nuclear=v[4],
                    couple=v[5], couple_child=v[6], lone_parent=v[7], three_gen=v[8], other=v[9]))
pd.DataFrame(s02).to_csv(OUT / "survey_households_structure.csv", index=False)

# ---------- 所得票 第22表（世帯人員×所得金額階級）・第26表（世帯主の年齢×所得金額階級）・第24表（世帯構造×所得）----------
BINS = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950,
        1000, 1100, 1200, 1500, 2000, None]


def income_table(name, cols):
    rows = read_csv_rows(name)
    data = []
    for r in rows:
        lab = (r[0] or "").strip().replace("　", "")
        if lab.startswith("総") or not lab:
            continue
        if ("万円" in lab) or ("～" in lab):
            data.append([num(x) for x in r[1:1 + len(cols)]])
    assert len(data) == 25, (name, len(data))
    df = pd.DataFrame(data, columns=cols)
    df.insert(0, "lo", BINS[:-1])
    df.insert(1, "hi", BINS[1:])
    return df


i22 = income_table("i22", ["total", "n1", "n2", "n3", "n4", "n5", "n6p"])
i22.to_csv(OUT / "income_by_size_2024.csv", index=False)
i26 = income_table("i26", ["total", "a29", "a30", "a40", "a50", "a60", "a70", "a80", "r65", "r75"])
i26.to_csv(OUT / "income_by_headage_2024.csv", index=False)
i24 = income_table("i24", ["total", "single", "single_m", "single_f", "nuclear", "couple", "couple_child",
                           "lone_parent", "three_gen", "other"])
i24.to_csv(OUT / "income_by_structure_2024.csv", index=False)

# 第36表（世帯人員別の平均所得）・第39表（世帯構造別の平均所得）
def mean_table(name, keys):
    rows = read_csv_rows(name)
    out = {}
    for r in rows:
        lab = (r[0] or "").strip().replace("　", "").replace(" ", "")
        for k, pat in keys.items():
            if lab == pat:
                out[k] = num(r[1])
    return out


m36 = mean_table("i36", {"total": "総数", "n1": "１人", "n2": "２人", "n3": "３人", "n4": "４人", "n5": "５人", "n6p": "６人以上"})
m39 = mean_table("i39", {"total": "総数", "single": "単独世帯", "couple": "夫婦のみの世帯", "couple_child": "夫婦と未婚の子のみの世帯",
                         "lone_parent": "ひとり親と未婚の子のみの世帯", "three_gen": "三世代世帯", "other": "その他の世帯"})
pd.DataFrame([dict(table="size", **m36)]).to_csv(OUT / "mean_income_by_size_2024.csv", index=False)
pd.DataFrame([dict(table="structure", **m39)]).to_csv(OUT / "mean_income_by_structure_2024.csv", index=False)

# 第1表（平均所得の年次推移）
i01 = []
for r in read_csv_rows("i01"):
    y = year_of(r[0])
    if y:
        i01.append(dict(income_year=y, mean_income=num(r[1])))
pd.DataFrame(i01).to_csv(OUT / "mean_income_years.csv", index=False)

# ---------- 国勢調査 ----------
def xl_rows(name):
    wb = openpyxl.load_workbook(RAW / f"{name}.xlsx", read_only=True, data_only=True)
    return list(wb.worksheets[0].iter_rows(values_only=True))


def v(x):
    return 0 if x in ("-", None, "…") else float(x)


# 時系列 第2表：世帯人員の人数別一般世帯数（1960〜2020）
rows = xl_rows("c_ts_size")
years = [int(str(x).replace("年", "")) for x in rows[7][3:15]]
d = {}
for r in rows:
    if r[0] == "世帯数" and r[1]:
        d[r[1]] = [v(x) for x in r[3:15]]
cs = pd.DataFrame(dict(year=years, total=d["総数"], n1=d["1人"], n2=d["2人"], n3=d["3人"], n4=d["4人"], n5=d["5人"]))
cs["n6p"] = [sum(d[k][i] for k in ["6人", "7人", "8人", "9人", "10人以上"]) for i in range(len(years))]

# 時系列 第3表：家族類型（1995〜2020、全国）
rows = xl_rows("c_ts_fam")
hdr = list(rows[8])
hdr[3], hdr[4] = "総数", "親族のみの世帯"
hdr[-2:] = hdr[-2:]
fam = []
for r in rows:
    if r[2] == "00000_全国":
        rec = dict(year=int(r[0].replace("年", "")))
        for i, h in enumerate(hdr):
            if h:
                rec[h] = v(r[i])
        # 単独世帯・非親族を含む世帯は 7 行目の見出し
        for i, h in enumerate(rows[7]):
            if h in ("非親族を含む世帯", "単独世帯"):
                rec[h] = v(r[i])
        fam.append(rec)
fam = pd.DataFrame(fam)

# 令和7年 第11-1表：世帯主の男女・年齢・家族類型・世帯人員の人数（全国）
rows = xl_rows("c25_11_1")
cols = [str(x) for x in rows[6]]
recs = []
for r in rows[10:]:
    if r[0] != "00000_全国" or r[1] != "0_総数":
        continue
    rec = dict(age=r[2], size=r[3])
    for i, c in enumerate(cols[4:], start=4):
        rec[c] = v(r[i])
    recs.append(rec)
c25 = pd.DataFrame(recs)
c25.to_csv(OUT / "census2025_age_size_family.csv", index=False)

tot25 = c25[(c25.age == "00_総数")].set_index("size")
cs25 = dict(year=2025, total=tot25.loc["0_総数", "0_総数"])
for k, s in zip(["n1", "n2", "n3", "n4", "n5", "n6p"],
                ["1_世帯人員が1人", "2_世帯人員が2人", "3_世帯人員が3人", "4_世帯人員が4人", "5_世帯人員が5人", None]):
    cs25[k] = tot25.loc[s, "0_総数"] if s else tot25.loc["6_世帯人員が6人", "0_総数"] + tot25.loc["7_世帯人員が7人以上", "0_総数"]
cs = pd.concat([cs, pd.DataFrame([cs25])], ignore_index=True)
cs.to_csv(OUT / "census_households_size.csv", index=False)

# 家族類型を国民生活基礎調査の世帯構造にそろえる（2025 を追加）
row25 = c25[(c25.age == "00_総数") & (c25["size"] == "0_総数")].iloc[0]
fam25 = {"year": 2025, "総数": row25["0_総数"], "単独世帯": row25["3_単独世帯"], "夫婦のみの世帯": row25["111_夫婦のみの世帯"],
         "夫婦と子供から成る世帯": row25["112_夫婦と子供から成る世帯"], "男親と子供から成る世帯": row25["113_男親と子供から成る世帯"],
         "女親と子供から成る世帯": row25["114_女親と子供から成る世帯"], "不詳": row25["4_世帯の家族類型「不詳」"],
         "独身寮の単身者": row25["R5_（再掲）会社などの独身寮の単身者"]}
famc = pd.DataFrame([dict(year=r["year"], total=r["総数"], single=r["単独世帯"], couple=r["夫婦のみの世帯"],
                          couple_child=r["夫婦と子供から成る世帯"],
                          lone_parent=r["男親と子供から成る世帯"] + r["女親と子供から成る世帯"]) for _, r in fam.iterrows()]
                    + [dict(year=2025, total=fam25["総数"], single=fam25["単独世帯"], couple=fam25["夫婦のみの世帯"],
                            couple_child=fam25["夫婦と子供から成る世帯"],
                            lone_parent=fam25["男親と子供から成る世帯"] + fam25["女親と子供から成る世帯"])])
famc["unknown"] = 0.0
famc.loc[famc.year == 2025, "unknown"] = fam25["不詳"]
famc["other"] = famc.total - famc.unknown - famc[["single", "couple", "couple_child", "lone_parent"]].sum(axis=1)
famc.to_csv(OUT / "census_households_structure.csv", index=False)
pd.DataFrame([dict(year=2025, dorm_single=fam25["独身寮の単身者"],
                   lodger_single=row25["R4_（再掲）間借り・下宿などの単身者"])]).to_csv(OUT / "census2025_dorm.csv", index=False)

# 世帯主の年齢（10歳階級）×世帯人員の人数：2025（全国、男女計）
AGEMAP = {"01_15歳未満": "a29", "02_15～19歳": "a29", "03_20～24歳": "a29", "04_25～29歳": "a29",
          "05_30～34歳": "a30", "06_35～39歳": "a30", "07_40～44歳": "a40", "08_45～49歳": "a40",
          "09_50～54歳": "a50", "10_55～59歳": "a50", "11_60～64歳": "a60", "12_65～69歳": "a60",
          "13_70～74歳": "a70", "14_75～79歳": "a70", "15_80～84歳": "a80", "16_85歳以上": "a80"}
SIZEMAP = {"1_世帯人員が1人": "n1", "2_世帯人員が2人": "n2", "3_世帯人員が3人": "n3", "4_世帯人員が4人": "n4",
           "5_世帯人員が5人": "n5", "6_世帯人員が6人": "n6p", "7_世帯人員が7人以上": "n6p"}
j = c25[c25.age.isin(AGEMAP) & c25["size"].isin(SIZEMAP)].copy()
j["a"] = j.age.map(AGEMAP)
j["s"] = j["size"].map(SIZEMAP)
joint = j.groupby(["a", "s"])["0_総数"].sum().unstack("s")[["n1", "n2", "n3", "n4", "n5", "n6p"]]
joint.to_csv(OUT / "census2025_headage_by_size.csv")

# 世帯主の年齢（10歳階級）：1995〜2020（時系列 第4表、男女計）
rows = xl_rows("c_ts_famage")
AG2 = {"15歳未満": "a29", "15～19歳": "a29", "20～24歳": "a29", "25～29歳": "a29", "30～34歳": "a30", "35～39歳": "a30",
       "40～44歳": "a40", "45～49歳": "a40", "50～54歳": "a50", "55～59歳": "a50", "60～64歳": "a60", "65～69歳": "a60",
       "70～74歳": "a70", "75～79歳": "a70", "80～84歳": "a80", "85歳以上": "a80"}
single_col = [i for i, h in enumerate(rows[7]) if h == "単独世帯"][0]
ag = []
for r in rows[9:]:
    if r[2] == "総数" and r[3] in AG2:
        ag.append(dict(year=int(r[0].replace("年", "")), a=AG2[r[3]], n=v(r[4]), single=v(r[single_col])))
ag = pd.DataFrame(ag).groupby(["year", "a"], as_index=False)[["n", "single"]].sum()
a25 = j.groupby("a")["0_総数"].sum()
s25 = j[j.s == "n1"].groupby("a")["0_総数"].sum()
ag = pd.concat([ag, pd.DataFrame(dict(year=2025, a=a25.index, n=a25.values, single=s25.reindex(a25.index).values))])
ag.to_csv(OUT / "census_headage.csv", index=False)

# ---------- 回収率（公表資料の数字を手で写したもの）----------
rr = [
    # year, 世帯票, 所得票, 出典
    (1996, 90.0, None, "新田（2004）本文"), (2003, 81.6, None, "新田（2004）本文"),
    (2008, 79.7, 71.9, "総務省資料"), (2009, 81.9, 72.7, "総務省資料"), (2010, 79.4, 75.7, "総務省資料"),
    (2011, 80.5, 80.8, "総務省資料"), (2012, 80.1, 80.4, "総務省資料"), (2013, 79.6, 74.4, "総務省資料"),
    (2014, 78.7, 80.1, "総務省資料"), (2015, 78.5, 76.1, "総務省資料"), (2016, 77.6, 73.7, "総務省資料"),
    (2017, 76.0, 77.5, "総務省資料"),
    (2019, round(218332 / 301334 * 100, 1), round(23014 / 32529 * 100, 1), "令和元年 概況（回収数÷客体数）"),
    (2022, 68.4, None, "厚労省 回収率（令和4年）"),
    (2024, round(40425 / 61229 * 100, 1), round(5023 / 7427 * 100, 1), "令和6年 概況（回収数÷客体数）"),
    (2025, round(188589 / 301221 * 100, 1), round(17500 / 27901 * 100, 1), "令和7年 概況（回収数÷客体数）"),
]
pd.DataFrame(rr, columns=["year", "rr_household", "rr_income", "source"]).to_csv(OUT / "response_rates.csv", index=False)

# 地域ブロック・市郡別の回収率（世帯票、令和4年・令和7年）
rr_area = [
    ("全国", 68.4, 62.6), ("北海道・東北", 76.1, 67.7), ("関東", 62.9, 58.8), ("東海・北陸", 72.8, 66.4),
    ("近畿", 64.4, 57.8), ("中国・四国", 72.0, 66.0), ("九州", 65.0, 60.6),
    ("大都市", 59.2, 54.7), ("人口15万人以上の市", 66.3, 60.8), ("人口15万人未満の市", 73.9, 67.2), ("郡部", 79.3, 71.6),
]
pd.DataFrame(rr_area, columns=["area", "rr_2022", "rr_2025"]).to_csv(OUT / "response_rates_area.csv", index=False)
print("ok")
