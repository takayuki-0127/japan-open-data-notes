"""e-Stat の家計調査 第4-3表（年間収入五分位階級別、品目分類、二人以上の世帯）の年次 Excel（2007〜2025年）から、
data/items_avg.csv（平均＝二人以上の世帯全体の支出金額・購入数量・平均価格）と
data/items_quintile.csv（五分位別の支出金額）を作る。元の Excel は data/raw/kakei43_<年>.xls(x) に置く。"""
import re, unicodedata
import pandas as pd
from common import ROOT, RAW

def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).strip().replace(" ", "").replace("　", "")
    return s

def read_sheet(path, sheet, new):
    d = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    cc, nc, v0 = (10, 11, 13) if new else (7, 8, 10)
    out = []
    started = False
    for _, r in d.iterrows():
        name = r[nc]
        if pd.isna(name):
            continue
        name = norm(name)
        if name == "消費支出":
            started = True
        if not started:
            continue
        code = r[cc]
        code = "" if pd.isna(code) else norm(code)
        vals = []
        for j in range(6):
            x = r[v0 + j]
            try:
                vals.append(float(x))
            except (TypeError, ValueError):
                vals.append(float("nan"))
        out.append([code, name] + vals)
    return pd.DataFrame(out, columns=["code", "name", "q0", "q1", "q2", "q3", "q4", "q5"])

def main():
    rows = []
    for y in range(2007, 2026):
        f = next(RAW.glob(f"kakei43_{y}.xls*"))
        new = y >= 2020
        sheets = pd.ExcelFile(f).sheet_names[:3]  # 支出金額・購入数量・平均価格（二人以上の世帯）
        parts = {}
        for s, key in zip(sheets, ["E", "Q", "P"]):
            assert key == "E" and "支出金額" in s or key == "Q" and "購入数量" in s or key == "P" and "平均価格" in s, (y, s)
            t = read_sheet(f, s, new)
            t["seq"] = range(len(t))
            parts[key] = t
        e = parts["E"]
        for key in ["Q", "P"]:
            t = parts[key]
            assert len(t) == len(e) and (t["name"].values == e["name"].values).all(), (y, key)
        for j in range(6):
            df = pd.DataFrame({"year": y, "seq": e["seq"], "code": e["code"], "name": e["name"], "quintile": j,
                               "E": e[f"q{j}"], "Q": parts["Q"][f"q{j}"], "P": parts["P"][f"q{j}"]})
            rows.append(df)
    a = pd.concat(rows, ignore_index=True)
    a["name"] = a["name"].str.replace(r"[（(]\d+[)）]$", "", regex=True)
    avg = a[a.quintile == 0].drop(columns="quintile")
    avg.to_csv(ROOT / "data" / "items_avg.csv", index=False)
    qu = a[a.quintile > 0].pivot_table(index=["year", "seq", "code", "name"], columns="quintile", values="E").reset_index()
    qu.columns = ["year", "seq", "code", "name"] + [f"E{j}" for j in range(1, 6)]
    qu.to_csv(ROOT / "data" / "items_quintile.csv", index=False)
    # 購入数量がある品目だけ、五分位別の購入数量も残す（分けた標本での推定に使う）
    qq = a[(a.quintile > 0) & a.Q.notna()].pivot_table(index=["year", "seq", "code", "name"], columns="quintile", values="Q").reset_index()
    qq.columns = ["year", "seq", "code", "name"] + [f"Q{j}" for j in range(1, 6)]
    qq.to_csv(ROOT / "data" / "items_quintile_qty.csv", index=False)
    print(avg.groupby("year").size().to_dict())

if __name__ == "__main__":
    main()
