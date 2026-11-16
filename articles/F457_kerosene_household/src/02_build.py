"""灯油の行を取り出す。data/kerosene_long_1963_2007.csv（長期時系列）、data/kerosene_national.csv（2007〜2025年、表4-1）、
data/kerosene_cities.csv（2018〜2025年、52市）。"""
import gzip, io, pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""


def xl(name):
    f = next(RAW.glob(name + ".*"))
    if f.name.endswith(".gz"):
        return pd.ExcelFile(io.BytesIO(gzip.open(f).read()), engine="xlrd")
    return pd.ExcelFile(f, engine="openpyxl")


def num(x):
    return float(x) if isinstance(x, (int, float)) and not pd.isna(x) else None


# 長期時系列（横に品目、縦に年）
x = xl("long_20_3_a")
rows = []
for s in x.sheet_names:
    v = pd.read_excel(x, header=None, sheet_name=s)
    cols = [j for j in range(v.shape[1]) if n(v.iloc[8, j]) == "灯油"]
    if not cols:
        continue
    j = cols[0]
    assert "金額" in n(v.iloc[10, j]) and "数量" in n(v.iloc[10, j + 1]), (v.iloc[10, j], v.iloc[10, j + 1])
    for i in range(12, len(v)):
        y = num(v.iloc[i, 1])
        if y and 1960 < y < 2010:
            rows.append(dict(year=int(y), spend=num(v.iloc[i, j]), qty=num(v.iloc[i, j + 1])))
    break
long = pd.DataFrame(rows)
long.to_csv(ROOT / "data" / "kerosene_long_1963_2007.csv", index=False)

# 表4-1
nat, city = [], []
for y in range(2007, 2026):
    x = xl(f"t4_1_{y}")
    for k, s in enumerate(x.sheet_names[:2]):
        v = pd.read_excel(x, header=None, sheet_name=s)
        r, lc = next((i, j) for i in range(len(v)) for j in range(13) if n(v.iloc[i, j]) == "灯油")
        recs = {}
        hdr = [n(c) for c in v.iloc[8]]
        if any("・支出金額" in h for h in hdr):  # 2020年からの形：列の見出しが「地域・項目」
            KEY = {"購入頻度": "freq", "支出金額": "spend", "購入数量": "qty", "平均価格": "price", "購入世帯数": "buyers"}
            for j, h in enumerate(hdr):
                if "・" in h:
                    reg, item = h.split("・", 1)
                    for kk, nm in KEY.items():
                        if item.startswith(kk):
                            recs.setdefault(reg, {})[nm] = num(v.iloc[r, j])
        else:  # 2019年までの形：地域名の下に 購入頻度・支出金額・購入数量・平均価格（全国だけ購入世帯数も）
            for j in range(lc + 1, v.shape[1]):
                t = n(v.iloc[7, j])
                if t and t != "国":
                    name = "全国" if t == "全" else t
                    b = j - 1
                    recs[name] = dict(freq=num(v.iloc[r, b]), spend=num(v.iloc[r, b + 1]), qty=num(v.iloc[r, b + 2]),
                                      price=num(v.iloc[r, b + 3]), buyers=num(v.iloc[r, b + 4]) if name == "全国" else None)
        for name, d in recs.items():
            name = re.sub(r"^\d+", "", name)
            d = dict(year=y, region=name, **{kk: d.get(kk) for kk in ["freq", "spend", "qty", "price", "buyers"]})
            if name == "全国" and k == 0:
                nat.append(d)
            elif k == 1 and (name.endswith("市") or name.endswith("区部")):
                city.append(d)
        if y < 2018:
            break
pd.DataFrame(nat).to_csv(ROOT / "data" / "kerosene_national.csv", index=False)
c = pd.DataFrame(city)
c.to_csv(ROOT / "data" / "kerosene_cities.csv", index=False)
print(long.tail(3)); print(pd.DataFrame(nat)); print(c.groupby("year").size()); print(c[c.year == 2025].head())
