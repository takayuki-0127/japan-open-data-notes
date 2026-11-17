"""data/raw から、洗濯代の月別（2015〜2025年）・年（1963〜2007年）・年齢別（2015〜2025年）と、物価の表を作る。ネットにはつながない。"""
import pathlib, re, io
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return np.nan


# ---- 月別（品目分類） ---------------------------------------------------------------------------
mon = []
for p in sorted(RAW.glob("kakei_monthly_items_*.csv")):
    t = pd.read_csv(io.StringIO(p.read_bytes().decode("cp932")), header=None, dtype=str).fillna("")
    yrow, mrow = [s.strip() for s in t.iloc[1].tolist()], [s.strip() for s in t.iloc[3].tolist()]
    namecol = mrow.index("品目分類")
    cur = None
    cols = []
    for k in range(namecol + 1, t.shape[1]):
        if re.match(r"^\d{4}年$", yrow[k]):
            cur = int(yrow[k][:4])
        m = re.match(r"^(\d{1,2})月$", mrow[k])
        if cur and m:
            cols.append((k, cur, int(m.group(1))))
    for item in ["洗濯代", "消費支出"]:
        r = t[t.iloc[:, namecol].str.strip() == item].iloc[0]
        for k, y, mo in cols:
            v = num(r.iloc[k])
            if not np.isnan(v):
                mon.append({"item": item, "year": y, "month": mo, "yen": v})
mon = pd.DataFrame(mon).drop_duplicates(["item", "year", "month"]).sort_values(["item", "year", "month"])
mon = mon[mon.year <= 2025]  # 年がそろう2025年まで
mon.to_csv(ROOT / "data" / "laundry_monthly.csv", index=False)

# ---- 1963〜2007年（年） --------------------------------------------------------------------------
x = pd.read_excel(RAW / "kakei_nonfarm_items_1963_2007.xls", header=None, dtype=str, sheet_name=None)
old = None
for name, v in x.items():
    v = v.fillna("")
    hit = [(i, j) for i in range(12) for j in range(v.shape[1]) if str(v.iat[i, j]).strip() == "洗濯代"]
    if hit:
        i, j = hit[0]
        yrs = []
        for r in range(v.shape[0]):
            yv = str(v.iat[r, 1]).strip()
            if re.match(r"^\d{4}$", yv):
                yrs.append({"year": int(yv), "yen": num(v.iat[r, j])})
        old = pd.DataFrame(yrs)
        break
old.to_csv(ROOT / "data" / "laundry_1963_2007.csv", index=False)

# ---- 年齢別（第4-6表、支出金額の列を見出しで探す） --------------------------------------------------
AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
rows = []
for p in sorted(RAW.glob("kakei_4-6_*.xls*")):
    y = int(re.search(r"_(\d{4})\.", p.name).group(1))
    z = pd.read_excel(p, header=None, dtype=str).fillna("")
    amt = None
    for i in range(20):
        cells = [str(c).strip() for c in z.iloc[i].tolist()]
        h = [k for k, c in enumerate(cells) if c == "支出金額" or c.endswith("・支出金額")]
        if len(h) >= len(AGES):
            amt = h[:len(AGES)]
            break
    for item in ["洗濯代", "消費支出"]:
        for i in range(len(z)):
            cells = [str(c).strip() for c in z.iloc[i].tolist()]
            if item in cells:
                for a, age in enumerate(AGES):
                    rows.append({"year": y, "item": item, "age": age, "yen": num(cells[amt[a]])})
                break
pd.DataFrame(rows).to_csv(ROOT / "data" / "laundry_age.csv", index=False)

# ---- 物価 ---------------------------------------------------------------------------------------
c = pd.read_csv(io.StringIO((RAW / "cpi_item_annual.csv").read_bytes().decode("cp932")), header=None, dtype=str)
want = {"総合": "cpi_all", "クリーニング代Ａ": "cpi_clean_a", "クリーニング代Ｂ": "cpi_clean_b"}
idx = {v: [k for k, s in enumerate(c.iloc[0]) if str(s).strip() == n][0] for n, v in want.items()}
cp = c.iloc[6:, [0] + list(idx.values())].copy()
cp.columns = ["year"] + list(idx.keys())
cp["year"] = cp.year.str.strip().str[:4].astype(int)
for k in idx:
    cp[k] = pd.to_numeric(cp[k], errors="coerce")
cp = cp[cp.year >= 1963].reset_index(drop=True)
cp.to_csv(ROOT / "data" / "cpi.csv", index=False)
print("rows", len(mon), len(old), len(rows), len(cp), "missing", int(mon.yen.isna().sum()), int(old.yen.isna().sum()))
