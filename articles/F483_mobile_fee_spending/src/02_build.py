"""data/raw から、二人以上の世帯の携帯電話通信料（年齢階級別、2015〜2025年）、消費支出、通信（中分類、単身・二人以上）、
消費者物価指数（通信料（携帯電話）・総合）の表を作る。ネットにはつながない。"""
import pathlib, re, io
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
ITEMS = {"mobile": ["移動電話通信料", "携帯電話通信料"], "fixed": ["固定電話通信料"], "consumption": ["消費支出"], "dist": ["世帯数分布(抽出率調整)", "世帯数分布（抽出率調整）"]}


def num(v):
    try:
        return float(v)
    except ValueError:
        return np.nan


rows = []
for p in sorted(RAW.glob("kakei_4-6_*.xls*")):
    y = int(re.search(r"_(\d{4})\.", p.name).group(1))
    x = pd.read_excel(p, header=None, dtype=str).fillna("")
    # 「支出金額」の列：見出しの行（2019年まで）または「平均・支出金額」のような見出し（2020年から）で探す。最初の7つが年齢階級
    amt = None
    for i in range(20):
        cells = [str(v).strip() for v in x.iloc[i].tolist()]
        hit = [k for k, v in enumerate(cells) if v == "支出金額" or v.endswith("・支出金額")]
        if len(hit) >= len(AGES):
            amt = hit[:len(AGES)]
            break
    for key, names in ITEMS.items():
        r = None
        for i in range(len(x)):
            cells = [str(v).strip() for v in x.iloc[i].tolist()]
            if any(v in names for v in cells):
                r = cells
                break  # 最初に出てくる行（品目分類の本表）
        for a, age in enumerate(AGES):
            rows.append({"year": y, "item": key, "age": age, "value": num(r[amt[a]].replace(",", ""))})
age = pd.DataFrame(rows)
age.to_csv(ROOT / "data" / "kakei_age.csv", index=False)

# 長期時系列：通信（中分類）と消費支出（二人以上・単身）
def long_table(fn, label):
    t = pd.read_csv(io.StringIO((RAW / fn).read_bytes().decode("cp932")), header=None, dtype=str)
    yrow = [k for k in range(5) if any(str(v).endswith("年") and str(v)[:4].isdigit() for v in t.iloc[k])][0]
    years = {k: int(str(v)[:4]) for k, v in enumerate(t.iloc[yrow]) if str(v).endswith("年") and str(v)[:4].isdigit()}
    out = []
    for name in ["通信", "消費支出"]:
        r = t[t.iloc[:, 5].astype(str).str.strip() == name].iloc[0]
        for k, y in years.items():
            out.append({"household": label, "item": name, "year": y, "yen": num(str(r.iloc[k]).replace(",", ""))})
    return out


lt = pd.DataFrame(long_table("kakei_two_plus_items_nominal_2000_2025.csv", "二人以上の世帯") + long_table("kakei_single_items_2000_2025.csv", "単身世帯"))
lt.to_csv(ROOT / "data" / "kakei_long_comm.csv", index=False)

# 消費者物価指数（2025年＝100）
c = pd.read_csv(io.StringIO((RAW / "cpi_item_annual.csv").read_bytes().decode("cp932")), header=None, dtype=str)
cols = {"総合": "cpi_all", "通信料（携帯電話）": "cpi_mobile", "通信": "cpi_comm"}
idx = {v: [k for k, s in enumerate(c.iloc[0]) if str(s).strip() == n][0] for n, v in cols.items()}
cp = c.iloc[6:, [0] + list(idx.values())].copy()
cp.columns = ["year"] + list(idx.keys())
cp["year"] = cp.year.str.strip().str[:4].astype(int)
for k in idx:
    cp[k] = pd.to_numeric(cp[k], errors="coerce")
cp = cp[cp.year >= 2000].reset_index(drop=True)
cp.to_csv(ROOT / "data" / "cpi.csv", index=False)
print(age[age.item == "dist"].pivot_table(index="age", columns="year", values="value").notna().all().all())
print(cp.tail(12).to_string())
