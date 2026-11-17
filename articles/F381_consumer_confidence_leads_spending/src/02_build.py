"""data/raw から分析用の表を作る（ネットにはつながない）。
- data/cci_monthly.csv：消費者態度指数と4つの意識指標・資産価値（季節調整値）。2004年3月までは四半期ごと（3・6・9・12月）
- data/qe_quarterly.csv：GDP 速報の実質季節調整系列（10億円、2020年連鎖価格）。家計最終消費支出と形態別
- data/kakei_monthly.csv：家計調査（二人以上の世帯）の消費支出と耐久財に近い費目の実質増減率（前年同月比、%）"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return np.nan


# 1) 消費者態度指数（2表、季節調整値）
x = pd.read_excel(RAW / "cci_t2_sa.xlsx", header=None, dtype=str)
r = x[x[0].astype(str).str.match(r"^\d{10}$")]
cci = pd.DataFrame({
    "year": r[0].str[:4].astype(int).values,
    "month": r[0].str[-2:].astype(int).values,
    "cci": [num(v) for v in r[4]], "kurashi": [num(v) for v in r[6]], "shunyu": [num(v) for v in r[8]],
    "koyo": [num(v) for v in r[10]], "kaidoki": [num(v) for v in r[12]], "shisan": [num(v) for v in r[14]],
})
assert not cci.duplicated(["year", "month"]).any()
cci = cci.sort_values(["year", "month"]).reset_index(drop=True)
cci.to_csv(ROOT / "data" / "cci_monthly.csv", index=False)

# 2) GDP 速報（実質季節調整系列の実額）


def read_qe(path, cols):
    rows, year = [], None
    for line in open(path, encoding="cp932").read().splitlines():
        f = next(iter([list(pd.read_csv(pd.io.common.StringIO(line), header=None, dtype=str).iloc[0])])) if line.strip() else []
        if not f:
            continue
        lab = str(f[0]).strip()
        m = re.match(r"^(\d{4})/\s*(\d+)-\s*(\d+)\.$", lab)
        m2 = re.match(r"^(\d+)-\s*(\d+)\.$", lab)
        if m:
            year, q1 = int(m.group(1)), int(m.group(2))
        elif m2 and year is not None:
            q1 = int(m2.group(1))
        else:
            continue
        q = (q1 + 2) // 3
        if m2 and q == 1:
            year += 1
        rows.append({"year": year, "q": q, **{k: num(f[i]) for k, i in cols.items()}})
    return pd.DataFrame(rows)


a = read_qe(RAW / "qe_gaku-jk2631.csv", {"gdp": 1, "pc": 2, "hc": 3, "hc_xrent": 4})
b = read_qe(RAW / "qe_kgaku-jk2631.csv", {"durable": 5, "semidur": 6, "nondur": 7, "services": 8})
qe = a.merge(b, on=["year", "q"], how="inner").sort_values(["year", "q"]).reset_index(drop=True)
assert not qe.duplicated(["year", "q"]).any()
qe.to_csv(ROOT / "data" / "qe_quarterly.csv", index=False)

# 3) 家計調査 長期時系列 表2（二人以上の世帯）の実質増減率（月）


def norm(s):
    s = re.sub(r"\s+", "", str(s))
    return re.sub(r"^[0-9.]+", "", s)


v = pd.read_excel(RAW / "kakei_ts2_youto_monthly.xlsx", header=None, dtype=str, sheet_name="実質増減率（月）").fillna("")
cols, cur = [], None
for k in range(15, v.shape[1]):
    yy = re.match(r"^(\d{4})年", str(v.iat[9, k]).strip())
    if yy:
        cur = int(yy.group(1))
    mm = re.match(r"^(\d{1,2})\s*月", str(v.iat[11, k]).strip().replace("　", " "))
    if cur and mm:
        cols.append((k, cur, int(mm.group(1))))
labels = [norm("".join(str(c) for c in v.iloc[i, 7:15])) for i in range(len(v))]
items = {"消費支出": "cons", "家具・家事用品": "furn", "教養娯楽": "recr", "交通・通信": "trans"}
out = []
for lab, key in items.items():
    i = next(i for i, l in enumerate(labels) if l == lab)
    for k, yy, mm in cols:
        out.append({"year": yy, "month": mm, "item": key, "real_yoy": num(v.iat[i, k])})
kk = pd.DataFrame(out).pivot_table(index=["year", "month"], columns="item", values="real_yoy").reset_index()
kk.columns.name = None
kk = kk.sort_values(["year", "month"]).reset_index(drop=True)
kk.to_csv(ROOT / "data" / "kakei_monthly.csv", index=False)
print("cci", len(cci), cci.iloc[0, :2].tolist(), cci.iloc[-1, :2].tolist(),
      "| qe", len(qe), qe.iloc[0, :2].tolist(), qe.iloc[-1, :2].tolist(),
      "| kakei", len(kk), kk.iloc[0, :2].tolist(), kk.iloc[-1, :2].tolist(), int(kk.isna().sum().sum()))
