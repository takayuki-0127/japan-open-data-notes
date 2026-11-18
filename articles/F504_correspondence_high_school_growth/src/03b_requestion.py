"""問い直し（結果を見てから足した）：私立の生徒が増えたのは、学校の数が増えたからか、1校あたりの生徒が増えたからか。
私立の生徒数 ＝ 学校数 × 1校あたりの生徒数 と書き、対数で変化を分ける。2025年度は通信教育連携協力施設の数も見る（見出しの文字で列を選ぶ）。"""
import json, math, re
import pandas as pd
from common import ROOT, sheet_rows, isnum

D, R = ROOT / "data", ROOT / "results"
sch = pd.read_csv(D / "schools.csv").set_index("year")
age = pd.read_csv(D / "age.csv")
tot = age[age.age == "計"].set_index("year")
out = pd.DataFrame({"private_students": tot.private, "private_schools": sch.private_independent + sch.private_attached,
                    "public_students": tot.public, "public_schools": sch.public_independent + sch.public_attached})
out["private_per_school"] = (out.private_students / out.private_schools).round(1)
out["public_per_school"] = (out.public_students / out.public_schools).round(1)
out.to_csv(R / "requestion_per_school.csv")


def split(y0, y1):
    ls = math.log(out.loc[y1, "private_students"] / out.loc[y0, "private_students"])
    ln = math.log(out.loc[y1, "private_schools"] / out.loc[y0, "private_schools"])
    return {"students_ratio": round(out.loc[y1, "private_students"] / out.loc[y0, "private_students"], 2),
            "schools_ratio": round(out.loc[y1, "private_schools"] / out.loc[y0, "private_schools"], 2),
            "per_school_ratio": round(out.loc[y1, "private_per_school"] / out.loc[y0, "private_per_school"], 2),
            "schools_share_of_log_growth_pct": round(100 * ln / ls, 1)}


# 2025年度：通信教育連携協力施設（見出しの文字で列を選ぶ）
rows = sheet_rows("tsushin_2025_schools.xlsx")
hs = [r for r in rows if str(r[0]).strip() == "区分"]
names = ["|".join(re.sub(r"\s+", "", str(h[j])) for h in hs) for j in range(len(hs[0]))]
fac = {}
for r in rows:
    if r[0] and str(r[0]).startswith("令和7") and str(r[1]) in ("公立", "私立"):
        for j, n in enumerate(names):
            if n.startswith("通信教育連携協力施設数") and isnum(r[j]):
                fac[f"{r[1]}|{n.split('|')[-1]}"] = int(r[j])
res = {"per_school": {int(y): {c: float(out.loc[y, c]) for c in out.columns} for y in out.index},
       "split_1990_2025": split(1990, 2025), "split_2010_2025": split(2010, 2025), "split_2015_2025": split(2015, 2025),
       "facilities_2025": fac,
       "private_facilities_per_school_2025": round(fac["私立|計"] / out.loc[2025, "private_schools"], 1)}
json.dump(res, open(R / "requestion.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
