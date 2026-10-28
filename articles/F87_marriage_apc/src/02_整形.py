"""JSON から、年齢×年×男女の長い表を作る（初婚率・未婚割合・50歳時未婚割合）。"""
import json, re
import pandas as pd
from common import RAW, DATA

d = json.load(open(RAW / "ipss_T06-09_T06-23_T06-24.json", encoding="utf-8"))

def age_key(s):
    s = str(s).replace(" ", "").replace("　", "")
    m = re.match(r"(\d+)～(\d+)", s)
    return f"{m.group(1)}-{m.group(2)}" if m else None

def year_of(h):
    m = re.match(r"(\d{4})", str(h))
    return int(m.group(1)) if m else None

def long_table(rows, header_row, sex_labels, value):
    years = [year_of(h) for h in rows[header_row]]
    out, sex = [], None
    for r in rows[header_row + 1:]:
        if r[0] is None and r[1] in sex_labels:
            sex = sex_labels[r[1]]; continue
        a = age_key(r[0]) if r[0] is not None else None
        if sex and a:
            for j, y in enumerate(years):
                if y and isinstance(r[j], (int, float)):
                    out.append({"sex": sex, "age": a, "year": y, value: float(r[j])})
    return pd.DataFrame(out)

# 表6-9 初婚率（‰、未婚者1,000人あたり）
fm = long_table(d["T06-09"]["T06-09"], 2, {"夫": "男", "妻": "女"}, "first_marriage_rate")
# 表6-24(1) 未婚割合（%）
um = long_table(d["T06-24"]["T06-24(1)"], 2, {"男": "男", "女": "女"}, "unmarried_pct")
# 表6-23 50歳時の未婚割合（%）
r50 = []
for r in d["T06-23"]["T06-23"][4:]:
    if isinstance(r[0], (int, float)) and r[0] > 1900:
        r50.append({"year": int(r[0]), "男": r[2], "女": r[6]})
r50 = pd.DataFrame(r50).melt(id_vars="year", var_name="sex", value_name="unmarried50_pct")

if __name__ == "__main__":
    fm.to_csv(DATA / "first_marriage_rate.csv", index=False, encoding="utf-8-sig")
    um.to_csv(DATA / "unmarried_pct.csv", index=False, encoding="utf-8-sig")
    r50.to_csv(DATA / "unmarried_at50.csv", index=False, encoding="utf-8-sig")
    print(fm.shape, um.shape, r50.shape)
    print(fm.pivot_table(index=["sex", "age"], columns="year", values="first_marriage_rate").head(8))
