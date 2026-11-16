"""物流センサスの表から、輸送機関別の重量・件数（2000〜2021年）、業種別のロット、ロット階層別の件数・重量を取り出す。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""
MODES = ["鉄道コンテナ", "車扱・その他", "自家用トラック", "宅配便等混載", "一車貸切", "トレーラー", "フェリー", "コンテナ船", "RORO船", "その他船舶", "航空", "その他", "合計"]

# 2021年調査の表1-5-15（横に 重量4年・件数4年・ロット4年）
v = pd.read_excel(RAW / "t1_5_15_2021.xlsx", header=None)
yrs = [int(re.search(r"\d{4}", str(x)).group()) for x in v.iloc[1, 3:7]]
rec = []
for i in range(4, len(v)):
    lab = n(v.iloc[i, 2])
    if lab in MODES:
        for k, y in enumerate(yrs):
            rec.append(dict(year=y, mode=lab, ton=float(v.iloc[i, 3 + k]), count=float(v.iloc[i, 7 + k])))
# 2015年調査の表1-5-15（縦に 重量・件数・ロットのブロック）から2000年
w = pd.read_excel(RAW / "t1_5_15_2015.xls", header=None)
blocks = [i for i in range(len(w)) if n(w.iloc[i, 1]).startswith("代表輸送機関")]
ycols = {j: int(re.search(r"\d{4}", str(w.iloc[blocks[0], j])).group()) for j in range(4, 8)}
def label(row):
    s = n(row[3]) or n(row[2]) or n(row[1])
    return s.replace("(計)", "").replace("一車貸切", "一車貸切")
old = {}
for b, kind in zip(blocks[:2], ["ton", "count"]):
    for i in range(b + 1, b + 18):
        lab = label(w.iloc[i])
        if lab in MODES:
            for j, y in ycols.items():
                old.setdefault((y, lab), {})[kind] = float(w.iloc[i, j])
for (y, lab), d in old.items():
    if y == 2000:
        rec.append(dict(year=y, mode=lab, **d))
modes = pd.DataFrame(rec).sort_values(["year", "mode"])
# 重なる年の一致の確かめ（2005・2010・2015年の合計）
chk = []
for y in [2005, 2010, 2015]:
    a = modes[(modes.year == y) & (modes["mode"] == "合計")].iloc[0]
    b = old[(y, "合計")]
    chk.append(dict(year=y, ton_2021table=a.ton, ton_2015table=b["ton"], count_2021table=a["count"], count_2015table=b["count"]))
pd.DataFrame(chk).to_csv(ROOT / "data" / "overlap_check.csv", index=False, float_format="%.4f")
modes.to_csv(ROOT / "data" / "modes.csv", index=False, float_format="%.4f")

# 業種別（表1-5-12、2021年調査）
u = pd.read_excel(RAW / "t1_5_12_2021.xlsx", header=None)
uy = [int(re.search(r"\d{4}", str(x)).group()) for x in u.iloc[1, 3:7]]
ind = []
TOP = {"鉱業(小計)", "製造業(小計)", "卸売業(小計)", "倉庫業(小計)", "合計"}
for i in range(4, len(u)):
    b = n(u.iloc[i, 2]) or n(u.iloc[i, 1]) or n(u.iloc[i, 0])
    if b in TOP:
        for k, y in enumerate(uy):
            ind.append(dict(year=y, industry=b.replace("(小計)", ""), ton=float(u.iloc[i, 3 + k]), count=float(u.iloc[i, 7 + k])))
pd.DataFrame(ind).to_csv(ROOT / "data" / "industry.csv", index=False, float_format="%.4f")

# ロット階層別（全業種の合計、代表輸送機関の合計）
CLS = ["<0.01", "0.01-0.05", "0.05-0.1", "0.1-0.5", "0.5-1", "1-3", "3-5", "5-7", "7-10", "10-15", "15-20", "20-30", "30-50", "50-100", "100-500", "500-1000", ">=1000"]
def lot2021(path):
    x = pd.read_excel(path, header=None)
    cols = [j for j in range(x.shape[1]) if n(x.iloc[1, j]) == "合計"]
    row = next(i for i in range(x.shape[0]) if n(x.iloc[i, 0]) == "合計" and n(x.iloc[i, 1]) == "合計")
    vals = [float(x.iloc[row, j]) for j in cols]
    return vals[:17], vals[17]
def lot2015(path):
    x = pd.read_excel(path, header=None)
    row = next(i for i in range(6, x.shape[0]) if n(x.iloc[i, 1]).startswith("合計"))
    vals = [float(x.iloc[row, j]) for j in range(3, 21)]
    return vals[:17], vals[17]
lots = []
for y, f1, f2, fn in [(2015, "t2_7_1_2015.xls", "t2_7_2_2015.xls", lot2015), (2021, "t2_7_1_2021.xlsx", "t2_7_2_2021.xlsx", lot2021)]:
    ton, tt = fn(RAW / f1); cnt, ct = fn(RAW / f2)
    assert abs(sum(ton) - tt) / tt < 0.001 and abs(sum(cnt) - ct) / ct < 0.001, (y, sum(ton), tt, sum(cnt), ct)
    for c, a, b in zip(CLS, ton, cnt):
        lots.append(dict(year=y, lot_class=c, ton=a, count=b))
pd.DataFrame(lots).to_csv(ROOT / "data" / "lot_classes.csv", index=False, float_format="%.4f")
print(modes[modes["mode"] == "合計"]); print(pd.DataFrame(chk)); print(pd.DataFrame(lots).groupby("year")[["ton", "count"]].sum())
