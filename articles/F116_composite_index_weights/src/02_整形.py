"""「暮らしやすさ」の合成指標に使う20指標（6分野）を取り出す。

向き（+1：大きいほど暮らしやすいとみなす、-1：小さいほど）は私が決めたもの。README に一覧を載せる。
本体は2026年版の各指標の最新年。頑健性用に、2015年版にもある指標はその最新年の値も作る。
"""
import pandas as pd
from common import RAW, DATA

IND = [  # code, 分野, 向き, 短い名前
    ("C01321", "所得・仕事", +1, "1人当たり県民所得"),
    ("F01301", "所得・仕事", -1, "完全失業率"),
    ("F03105", "所得・仕事", +1, "有効求人倍率"),
    ("F0610103", "所得・仕事", -1, "月間実労働時間（男）"),
    ("H01301", "住まい", +1, "持ち家比率"),
    ("H0220302", "住まい", +1, "借家の1人当たり畳数"),
    ("H04102", "住まい", -1, "民営賃貸の家賃"),
    ("H03102", "住まい", -1, "通勤1時間半以上の世帯比率"),
    ("I0920101", "医療", +1, "医師数（人口当たり）"),
    ("I11101", "医療", +1, "救急告示病院・診療所数"),
    ("G01104", "教育・文化", +1, "図書館数（人口当たり）"),
    ("E0510301", "教育・文化", -1, "小学校の教員1人当たり児童数"),
    ("E09402", "教育・文化", +1, "高校卒業者の進学率"),
    ("G042111", "教育・文化", +1, "スポーツの行動者率"),
    ("H05308", "生活環境", +1, "下水道処理人口普及率"),
    ("H08101", "生活環境", +1, "1人当たり都市公園面積"),
    ("H055031", "生活環境", +1, "ごみのリサイクル率"),
    ("K04102", "安全・物価", -1, "交通事故（道路延長当たり）"),
    ("K02101", "安全・物価", -1, "火災出火件数（人口当たり）"),
    ("L04414", "安全・物価", -1, "物価の地域差指数"),
]
P = [f"p{i:02d}" for i in range(1, 48)]
raw = pd.read_csv(RAW / "ssds_pref_indicators.csv")
names = pd.read_csv(RAW / "indicator_names_2026.tsv", sep="\t")
names["code"] = names["code"].str.lstrip("#")
names = names.set_index("code")

def latest(ed):
    x = raw[(raw.edition == ed)].dropna(subset=P)
    return x.sort_values("year").groupby("code").tail(1).set_index("code")

l26, l15 = latest(2026), latest(2015)
meta = pd.DataFrame(IND, columns=["code", "domain", "sign", "short"]).set_index("code")
meta["name"] = [names.loc[c, "name"] for c in meta.index]
meta["unit"] = [names.loc[c, "unit"] for c in meta.index]
meta["year"] = [int(l26.loc[c, "year"]) for c in meta.index]
meta["year_2015ed"] = [int(l15.loc[c, "year"]) if c in l15.index else None for c in meta.index]
x26 = l26.loc[meta.index, P].astype(float).T
x26.index = range(1, 48); x26.index.name = "pref_code"
c15 = [c for c in meta.index if c in l15.index]
x15 = l15.loc[c15, P].astype(float).T
x15.index = range(1, 48); x15.index.name = "pref_code"
x26.to_csv(DATA / "indicators_main.csv")
x15.to_csv(DATA / "indicators_2015ed.csv")
meta.to_csv(DATA / "indicator_meta.csv")
print(meta[["domain", "sign", "short", "year", "year_2015ed"]].to_string())
print("2015年版にもある指標:", len(c15))
