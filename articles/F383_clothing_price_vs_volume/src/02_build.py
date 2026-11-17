"""02 整形（オフライン）：家計調査（長期時系列表 1-2・20-3-a、第4-6表）と消費者物価指数（中分類、暦年）から、
被服及び履物の支出と物価指数を CSV にする。
出力：data/nominal_items_2000_2025.csv、data/nominal_items_1963_2007.csv、data/official_real_growth.csv、
      data/cpi_clothing.csv、data/age_items.csv"""
import glob
import pathlib
import re
import sys

import pandas as pd
import xlrd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import kakei_parse as K  # noqa: E402

RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
Z = lambda x: re.sub(r"[\s　]", "", str(x))
ITEMS = {"5": "被服及び履物", "5.1": "和服", "5.2": "洋服", "5.3": "シャツ・セーター類", "5.4": "下着類", "5.5": "生地・糸類",
         "5.6": "他の被服", "5.7": "履物類", "5.8": "被服関連サービス"}
SUB = {"5.2.1": "男性用洋服", "5.2.2": "女性用洋服", "5.2.3": "子供用洋服", "5.3.1": "男性用シャツ・セーター類",
       "5.3.2": "女性用シャツ・セーター類", "5.3.3": "子供用シャツ・セーター類", "5.4.1": "男性用下着類", "5.4.2": "女性用下着類",
       "5.4.3": "子供用下着類"}


def read_longtime(fname):
    t = pd.read_csv(RAW / fname, encoding="cp932", header=None, dtype=str)
    years = [int(re.match(r"(\d{4})年", str(x)).group(1)) for x in t.iloc[1, 6:]]
    body = t.iloc[3:].reset_index(drop=True)
    out = {}
    for _, r in body.iterrows():
        lv, big, mid, small, name = [Z(r[k]) for k in (1, 2, 3, 4, 5)]
        if name in ("消費支出", "世帯人員(人)") and lv in ("1", "-") and name not in out:
            key = {"消費支出": "消費支出", "世帯人員(人)": "世帯人員"}[name]
            out[key] = r[6:].values
        if big == "5" and lv in ("2", "3", "4"):
            code = "5" if lv == "2" else (f"5.{mid}" if lv == "3" else f"5.{mid}.{small}")
            nm = ITEMS.get(code) or SUB.get(code)
            if nm:
                assert nm.replace("男性", "男性").replace("・", "") == name.replace("・", ""), (code, nm, name)
                out[nm] = r[6:].values
    df = pd.DataFrame({k: pd.to_numeric(pd.Series(v).replace("-", None), errors="coerce").values for k, v in out.items()})
    df.insert(0, "year", years)
    return df


nom = read_longtime("kakei_longtime_1-2_items_2000_2025.csv")
assert list(nom.year) == list(range(2000, 2026)) and len(nom.columns) == 1 + 2 + len(ITEMS) + len(SUB)
mid = [ITEMS[c] for c in ITEMS if c != "5"]
assert (nom[mid].sum(axis=1) - nom["被服及び履物"]).abs().max() <= 2   # 中分類の合計＝被服及び履物（四捨五入の範囲）
nom.to_csv(DATA / "nominal_items_2000_2025.csv", index=False)
rg = read_longtime("kakei_longtime_1-2_real_growth_2000_2025.csv")[["year", "消費支出", "被服及び履物"]]
rg.columns = ["year", "消費支出_実質増減率", "被服及び履物_実質増減率"]
rg.to_csv(DATA / "official_real_growth.csv", index=False)

# 20-3-a（1963〜2007年、二人以上の非農林漁家世帯）
b = xlrd.open_workbook(RAW / "kakei_longtime_20-3-a_1963_2007.xls")
s0 = b.sheet_by_index(0)
assert Z(s0.cell_value(8, 4)).startswith("世帯人員") and Z(s0.cell_value(8, 7)) == "消費支出"
rows = list(range(12, 57))
old = pd.DataFrame({"year": [int(s0.cell_value(r, 1)) for r in rows], "世帯人員": [s0.cell_value(r, 4) for r in rows],
                    "消費支出": [s0.cell_value(r, 7) for r in rows]})
assert list(old.year) == list(range(1963, 2008))
want = {"5.0": "被服及び履物", "5.1": "和服", "5.2": "洋服", "5.3": "シャツ・セーター類", "5.4": "下着類", "5.5": "生地・糸類",
        "5.6": "他の被服", "5.7": "履物類", "5.8": "被服関連サービス"}
for si in (4, 5):
    sh = b.sheet_by_index(si)
    for c in range(sh.ncols):
        code = Z(sh.cell_value(7, c))
        if code in want and want[code] not in old.columns:
            nm = Z(sh.cell_value(8, c)).replace("･", "・")
            assert nm == want[code], (code, nm)
            assert [int(sh.cell_value(r, 1)) for r in rows] == list(range(1963, 2008))
            old[want[code]] = [float(sh.cell_value(r, c)) for r in rows]
assert all(v in old.columns for v in want.values())
dd = (old[list(want.values())[1:]].sum(axis=1) - old["被服及び履物"]).abs()
assert dd.max() <= 5 and set(old.year[dd > 2]) <= {1968}  # 1968年だけ中分類の合計が5円少ない（元の表のまま）
old.to_csv(DATA / "nominal_items_1963_2007.csv", index=False)

# 消費者物価指数（2025年基準、中分類、暦年）
t = pd.read_csv(RAW / "cpi_annual_middle_class.csv", encoding="cp932", header=None, dtype=str)
head = [Z(x) for x in t.iloc[0]]
CPI = ["総合", "被服及び履物", "衣料", "和服", "洋服", "シャツ・セーター・下着類", "シャツ・セーター類", "下着類", "履物類", "他の被服", "被服関連サービス"]
t[0] = t[0].str.strip()
body = t[t[0].str.fullmatch(r"\d{4}", na=False)]
cpi = pd.DataFrame({"year": body[0].astype(int).values})
for nm in CPI:
    j = [k for k, h in enumerate(head) if h == nm]
    assert len(j) == 1, (nm, j)
    cpi[nm] = pd.to_numeric(body[j[0]]).values
assert cpi.year.min() == 1970 and cpi.year.max() == 2025 and abs(cpi.loc[cpi.year == 2025, "総合"].iloc[0] - 100) < 1e-9
cpi.to_csv(DATA / "cpi_clothing.csv", index=False)

# 第4-6表 世帯主の年齢階級別（2002〜2025年）
codes = set(ITEMS) | {"5.2.1", "5.2.2", "5.2.3"}
recs = []
for f in sorted(glob.glob(str(RAW / "kakei_4-6_*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    recs += K.read_46(f, y, codes)
age = pd.DataFrame(recs)
age["item"] = age.code.map(lambda c: {**ITEMS, "5.2.1": "男性用洋服", "5.2.2": "女性用洋服", "5.2.3": "子供用洋服"}.get(c, c))
age = age[["year", "group", "code", "item", "amount"]].sort_values(["year", "group", "code"], kind="mergesort")
assert set(age.year) == set(range(2002, 2026)) and age.groupby("year").size().nunique() == 1
# 平均の行が長期時系列表と一致することの確かめ
chk = age[(age.group == "平均") & (age.code == "5")].set_index("year").amount
ref = nom.set_index("year").loc[chk.index, "被服及び履物"]
assert (chk - ref).abs().max() < 1, (chk - ref)
age.to_csv(DATA / "age_items.csv", index=False)
print("ok", nom.shape, old.shape, cpi.shape, age.shape)
