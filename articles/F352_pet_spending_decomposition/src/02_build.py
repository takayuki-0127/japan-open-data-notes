"""02 整形（オフライン）：家計調査 第4-6表（2005〜2025年）・第4-3表（2015〜2025年）からペット関連の品目を取り出し、
消費者物価指数（品目別、年平均）とあわせて CSV にする。動物病院代は扱わない（読み出さない）。
2002〜2004年の「他の愛がん動物・同用品」には動物病院代が含まれていたので、2005年から使う。
出力：data/pet_items.csv、data/cpi_pet.csv"""
import glob, pathlib, re, sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import kakei_parse as K

RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
CODES = {"848": "food", "84Y": "goods", "841": "goods_services_or_services"}
recs = []
for f in sorted(glob.glob(str(RAW / "kakei_4-*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    if y < 2005:
        continue
    tab = "age" if "4-6" in f else "income"
    for r in (K.read_46 if tab == "age" else K.read_43)(f, y, set(CODES)):
        r["table"] = tab
        recs.append(r)
d = pd.DataFrame(recs)
# 品目の名前の確かめ：841 は 2014年まで用品＋サービス、2015年からサービスだけ。84Y は 2015年から
n841 = d[d.code == "841"].groupby("year").name.first()
assert all(("同用品" in n841[y]) for y in n841.index if y <= 2014) and all(("サービス" in n841[y]) for y in n841.index if y >= 2015), n841
assert set(d[d.code == "84Y"].year) == set(range(2015, 2026))
def item(row):
    if row.code == "848":
        return "ペットフード"
    if row.code == "84Y":
        return "ペット用品"
    if row.code == "841":
        return "ペット用品・サービス（2014年まで）" if row.year <= 2014 else "ペット関連サービス"
    return row.code
d["item"] = d.apply(item, axis=1)
a = d[d.group == "平均"].pivot_table(index=["year", "code"], columns="table", values="amount")
a = a.dropna()
assert (a["age"] - a["income"]).abs().max() < 1e-9
d = d[["table", "year", "group", "code", "item", "amount", "freq"]].sort_values(["table", "year", "group", "code"])
d.to_csv(DATA / "pet_items.csv", index=False)

t = pd.read_csv(RAW / "cpi_item_annual.csv", encoding="cp932", header=None, dtype=str)
head = [str(x).strip() for x in t.iloc[0]]; code_row = [str(x).strip() for x in t.iloc[2]]; wrow = t.iloc[4]
want = {"総合": "0001", "他の教養娯楽用品": "0133", "ペットフード（ドッグフード）": "9193", "ペットフード（キャットフード）": "9196",
        "ペットトイレ用品": "9185", "ペット美容院代": "9188"}
t[0] = t[0].str.strip()
b = t[t[0].str.fullmatch(r"\d{4}", na=False)]
out = pd.DataFrame({"year": b[0].astype(int).values})
wts = {}
for nm, cd in want.items():
    j = [k for k in range(len(head)) if head[k] == nm and code_row[k] == cd]
    assert len(j) == 1, (nm, j)
    out[nm] = pd.to_numeric(b[j[0]], errors="coerce").values
    wts[nm] = float(wrow[j[0]])
wd, wc = wts["ペットフード（ドッグフード）"], wts["ペットフード（キャットフード）"]
out["ペットフード（犬・猫の加重平均）"] = (out["ペットフード（ドッグフード）"] * wd + out["ペットフード（キャットフード）"] * wc) / (wd + wc)
out = out[(out.year >= 2005) & (out.year <= 2025)]
out.to_csv(DATA / "cpi_pet.csv", index=False)
print(d[(d.table == "age") & (d.group == "平均")].pivot_table(index="year", columns="item", values="amount"), out.tail(3).T, sep="\n")
