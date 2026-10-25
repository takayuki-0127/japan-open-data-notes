"""SSDSE-A の125項目から、人口・世帯・産業・就業・財政・教育・医療・生活の比率指標を作る。"""
import numpy as np
import pandas as pd
from common import RAW, DATA

raw = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", header=None, dtype=str)
codes = raw.iloc[0].tolist()
df = raw.iloc[3:].copy()
df.columns = ["code", "pref", "name"] + codes[3:]
for c in codes[3:]:
    df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="coerce")
# 2020年国勢調査で人口0の町（福島県双葉町）は指標が作れないので除く
df = df[df["A1101"] > 0].reset_index(drop=True)
c = lambda k: df[k]

pop = c("A1101")
emp = c("F1102"); unemp = c("F1107"); nlf = c("F1108")
lab = emp + unemp
wk = c("C2208")  # 民営の従業者数
rev = c("D3201"); exp = c("D3203")

X = pd.DataFrame(index=df.index)
# 人口・世帯
X["人口（対数）"] = np.log(pop)
X["可住地の人口密度（対数）"] = np.log(pop / c("B1103"))
X["可住地の割合"] = c("B1103") / c("B1101")
X["15歳未満の割合"] = c("A1301") / pop
X["65歳以上の割合"] = c("A1303") / pop
X["75歳以上の割合"] = c("A1419") / pop
X["外国人の割合（対数）"] = np.log1p(1000 * c("A1700") / pop)
X["出生率（千人あたり）"] = 1000 * c("A4101") / pop
X["死亡率（千人あたり）"] = 1000 * c("A4200") / pop
X["転入率"] = 1000 * c("A5101") / pop
X["純移動率"] = 1000 * (c("A5101") - c("A5102")) / pop
X["婚姻率"] = 1000 * c("A9101") / pop
X["離婚率"] = 1000 * c("A9201") / pop
X["性比（男/女）"] = c("A110101") / c("A110102")
X["1世帯あたり人員"] = c("A710201") / c("A710101")
X["単独世帯の割合"] = c("A810105") / c("A710101")
X["高齢夫婦のみ世帯の割合"] = c("A8201") / c("A710101")
X["高齢単身世帯の割合"] = c("A8301") / c("A710101")
# 就業
X["就業率"] = emp / (lab + nlf)
X["女性の就業率"] = c("F110202") / (c("F110202") + c("F110702") + c("F110802"))
X["失業率"] = unemp / lab
X["第1次産業就業者の割合"] = c("F2201") / emp
X["第2次産業就業者の割合"] = c("F2211") / emp
X["第3次産業就業者の割合"] = c("F2221") / emp
X["従業者数/人口（対数）"] = np.log(wk / pop)
X["事業所数/人口（対数）"] = np.log(c("C2108") / pop)
X["農家数/世帯数（対数）"] = np.log1p(100 * (c("C310201") + c("C310202")) / c("A7101"))
ind = {"C220836": "建設業", "C220837": "製造業", "C220839": "情報通信業", "C220840": "運輸業",
       "C220841": "卸売・小売業", "C220844": "金融・保険業", "C220845": "不動産業",
       "C220846": "専門・技術サービス業", "C220847": "宿泊・飲食業", "C220848": "生活関連・娯楽業",
       "C220849": "教育", "C220850": "医療・福祉", "C220832": "農林業（民営）", "C220833": "漁業（民営）"}
for k, v in ind.items():
    X[f"従業者の割合：{v}"] = c(k) / wk
# 財政
X["経常収支比率"] = c("D2203")
X["実質公債費比率"] = c("D2211")
X["1人あたり歳出（対数）"] = np.log(exp / pop)
X["地方税/歳入"] = c("D320101") / rev
X["民生費/歳出"] = c("D320303") / exp
X["土木費/歳出"] = c("D320308") / exp
X["教育費/歳出"] = c("D320310") / exp
X["職員数/人口（対数）"] = np.log(c("D1202") / pop)
# 教育・医療・生活
X["小学校1校あたり児童数（対数）"] = np.log1p((c("E2501") + c("E3905").fillna(0)) / (c("E2101") + c("E3901").fillna(0)))
X["小学校の教員1人あたり児童数"] = c("E2501") / c("E2401")
X["高校生徒数/人口"] = 1000 * c("E4501") / pop
X["一般病院/人口（対数）"] = np.log1p(1e5 * c("I510120") / pop)
X["一般診療所/人口（対数）"] = np.log1p(1e5 * c("I5102") / pop)
X["医師数/人口（対数）"] = np.log1p(1e5 * c("I6100") / pop)
X["薬剤師数/人口（対数）"] = np.log1p(1e5 * c("I6300") / pop)
X["保育所等/15歳未満（対数）"] = np.log1p(1000 * c("J250302") / c("A1301"))
X["図書館+公民館/人口（対数）"] = np.log1p(1e5 * (c("G1401") + c("G1201")) / pop)
X["小売店/人口（対数）"] = np.log1p(1e4 * c("H6130") / pop)
X["飲食店/人口（対数）"] = np.log1p(1e4 * c("H6131") / pop)
X["大型小売店/人口（対数）"] = np.log1p(1e5 * c("H6132") / pop)
X["非水洗化人口の割合"] = c("H550701") / c("H5507")

X = X.replace([np.inf, -np.inf], np.nan)
na = X.isna().mean()
print("欠損の割合が高い指標:\n", na[na > 0].sort_values(ascending=False).head(10))
keep = na[na <= 0.05].index
X = X[keep]
X = X.fillna(X.median())
meta = df[["code", "pref", "name"]].copy()
meta["pop"] = pop
out = pd.concat([meta, X], axis=1)
out.to_csv(DATA / "indicators.csv", index=False, encoding="utf-8-sig")
print(out.shape, "指標数", X.shape[1])
