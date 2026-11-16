"""各年の集計表の「国籍・地域別 回答者属性および旅行内容」（第1表／表1-1）から、日本への来訪回数の構成比を取り出す。
data/visits_long.csv（年 × 国籍・地域 × 来訪回数の区分、構成比%・回答数）"""
import gzip, io, pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""
recs = []
for y in [2014, 2015, 2016, 2017, 2018, 2019, 2023, 2024, 2025]:
    x = pd.ExcelFile(io.BytesIO(gzip.open(RAW / f"inbound_{y}.xls.gz").read()), engine="xlrd")
    sheet = next(s for s in x.sheet_names if n(s) in ("第1表", "表1-1"))
    v = pd.read_excel(x, header=None, sheet_name=sheet)
    hr = next(i for i in range(12) if any(n(c) == "調査項目" for c in v.iloc[i]))
    nations = {j: ("全体" if n(c).startswith("全国籍") else n(c)) for j, c in enumerate(v.iloc[hr]) if n(c) and n(c) != "調査項目"}
    # 来訪回数のブロック
    start = next(i for i in range(len(v)) if any(n(c) == "日本への" for c in v.iloc[i, :4]))
    for i in range(start, start + 12):
        lab = next((n(c) for c in v.iloc[i, :8] if re.search(r"回目?$|回以上$", n(c))), None)
        if lab is None:
            if i > start:
                break
            continue
        for j, nat in nations.items():
            cnt, sh = v.iloc[i, j], v.iloc[i, j + 1]
            if isinstance(sh, (int, float)) and not pd.isna(sh):
                recs.append(dict(year=y, nation=nat.replace("･", "・"), visit=lab, count=float(cnt) if isinstance(cnt, (int, float)) else None, share=float(sh)))
d = pd.DataFrame(recs)
d.to_csv(ROOT / "data" / "visits_long.csv", index=False, float_format="%.4f")
print(d.groupby("year").visit.unique().to_string()); print(d.groupby("year").nation.unique().apply(len))
print(sorted(d.nation.unique()))
