"""02 整形：年次の時系列・物価・世帯主の年齢別パネルを作る"""
import json
import numpy as np
import pandas as pd
from common import RAW, DATA, AGE6

# 1) 長期時系列（月）→ 年平均（2000〜2025年、二人以上の世帯）
m = pd.read_csv(RAW / "kakei_long_monthly_subset.csv")
m["year"] = m["date"].str[:4].astype(int)
m = m[m["year"] <= 2025]
ann = m.pivot_table(index="year", columns="item", values="amount", aggfunc="mean")
ann = ann.rename(columns={"世帯人員(人)": "世帯人員", "65歳以上人員(人)": "65歳以上人員"})
assert (m.groupby("year")["date"].nunique() == 12).all()
ann.to_csv(DATA / "annual_long.csv", float_format="%.3f")

# 2) 消費者物価指数（月）→ 年平均
c = pd.read_csv(RAW / "cpi_subset.csv", dtype=str)
c = c[c["類・品目"].str.fullmatch(r"\d{6}")].copy()
c["year"] = c["類・品目"].str[:4].astype(int)
for col in c.columns[1:-1]:
    c[col] = pd.to_numeric(c[col], errors="coerce")
cy = c[(c["year"] >= 2000) & (c["year"] <= 2025)].groupby("year").mean(numeric_only=True)
assert (c[(c["year"] >= 2000) & (c["year"] <= 2025)].groupby("year").size() == 12).all()
cy.to_csv(DATA / "cpi_annual.csv", float_format="%.3f")

# 3) 第3-2表 → 世帯主の年齢6区分 × 年 のパネル
J = json.load(open(RAW / "kakei_age_3-2.json", encoding="utf-8"))
KEYS = {"世帯数分布": "w", "世帯人員": "hh", "65歳以上人員": "n65", "有業人員": "workers",
        "世帯主の年齢": "age", "消費支出": "C", "食料": "F", "外食": "out", "一般外食": "out_gen",
        "調理食品": "ready", "酒類": "alcohol", "飲料": "drink", "菓子類": "sweets",
        "可処分所得": "DI", "実収入": "income"}
rows = []
for kind in ("two", "work"):
    for y, v in J[kind].items():
        hdr = [h.replace("(再掲)", "").replace("歳", "") for h in v["hdr"]]
        rr = {}
        for lab, vals in v["rows"].items():
            for k, short in KEYS.items():
                if lab == k:
                    rr[short] = vals
        def col(name):
            # 年齢区分の列を探す（表記ゆれ：「～29歳」「～29」など）
            key = name.replace("歳", "")
            idx = [i for i, h in enumerate(hdr) if h == key]
            return idx[-1] if idx else None
        groups = [("平均", 0)] + [(g, col(g)) for g in AGE6]
        for g, i in groups:
            if i is None:
                raise SystemExit(f"列が見つからない: {kind} {y} {g} {hdr}")
            rec = {"kind": kind, "year": int(y), "group": g}
            for short, vals in rr.items():
                x = vals[i] if i < len(vals) else ""
                try:
                    rec[short] = float(x)
                except ValueError:
                    rec[short] = np.nan
            rows.append(rec)
P = pd.DataFrame(rows)
P.to_csv(DATA / "age_panel.csv", index=False, float_format="%.4f")

# 確認：6区分を世帯数分布で重み付けした平均が「平均」列と合うか
chk = []
for (kind, y), d in P.groupby(["kind", "year"]):
    a = d[d["group"] == "平均"].iloc[0]
    g = d[d["group"] != "平均"]
    wsum = g["w"].sum()
    Cw = (g["w"] * g["C"]).sum() / wsum
    Fw = (g["w"] * g["F"]).sum() / wsum
    chk.append({"kind": kind, "year": y, "w_sum": wsum, "C_avg": a["C"], "C_w": Cw,
                "C_diff_pct": 100 * (Cw / a["C"] - 1), "F_diff_pct": 100 * (Fw / a["F"] - 1)})
chk = pd.DataFrame(chk)
chk.to_csv(DATA / "check_age_weights.csv", index=False, float_format="%.4f")
print(chk.describe().round(3))
print(ann.loc[[2000, 2005, 2013, 2025], ["消費支出", "食料", "外食", "調理食品"]].round(0))
