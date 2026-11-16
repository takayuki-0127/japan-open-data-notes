"""各年の集計表の国籍・地域別の表から、利用した宿泊施設（複数回答）と滞在日数の構成比を取り出す。"""
import gzip, io, pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""
LODG = {"ホテル(洋室中心)": "hotel", "旅館(和室中心)": "ryokan", "自己所有の別荘・コンドミニアム": "villa", "学校の寮・会社所有の宿泊施設": "dorm",
        "親族・知人宅": "relatives", "ユースホステル・ゲストハウス": "guesthouse", "カプセルホテル": "capsule", "その他": "other", "宿泊せず": "none"}
STAY = {"3日間以内": "d0_3", "4~6日間": "d4_6", "7~13日間": "d7_13", "14~20日間": "d14_20", "21~27日間": "d21_27", "28~90日間": "d28_90", "91日間以上1年未満": "d91p"}
recs = []
for y in [2018, 2019, 2023, 2024, 2025]:
    x = pd.ExcelFile(io.BytesIO(gzip.open(RAW / f"inbound_{y}.xls.gz").read()), engine="xlrd")
    v = pd.read_excel(x, header=None, sheet_name="表1-1")
    hr = next(i for i in range(12) if any(n(c) == "調査項目" for c in v.iloc[i]))
    nations = {j: ("全体" if n(c).startswith("全国籍") else n(c)) for j, c in enumerate(v.iloc[hr]) if n(c) and n(c) != "調査項目"}
    j0 = min(nations)
    sec = None
    for i in range(hr + 1, len(v)):
        labs = [n(c) for c in v.iloc[i, :j0] if n(c)]
        if any(l.startswith("日本滞在中に") or l == "宿泊施設" for l in labs) and any("ホテル" in l for l in labs):
            sec = "lodg"
        if any(l == "滞在日数" for l in labs):
            sec = "stay"
        if any(l.startswith("性別") or l.startswith("旅行手配") for l in labs):
            sec = None
        if not labs or sec is None:
            continue
        item = labs[-1]
        key = None
        if sec == "lodg":
            key = "minpaku" if item.startswith("有料での住宅宿泊") else LODG.get(item)
        elif sec == "stay":
            key = STAY.get(item)
        if key is None:
            continue
        for j, nat in nations.items():
            c, s_ = v.iloc[i, j], v.iloc[i, j + 1]
            if isinstance(s_, (int, float)) and not pd.isna(s_):
                recs.append(dict(year=y, nation=nat, item=key, count=float(c), share=float(s_)))
d = pd.DataFrame(recs)
d.to_csv(ROOT / "data" / "lodging_stay_long.csv", index=False, float_format="%.4f")
print(d.groupby(["year"]).item.unique().apply(sorted).to_string()); print(d[d.nation == "全体"].pivot(index="item", columns="year", values="share").round(1))
