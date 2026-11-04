"""03 分析：築年数ごとの価格（減価曲線）を、物件の特徴と市区町村×四半期の固定効果をそろえて推定し、条件を変えて確かめる"""
import numpy as np, pandas as pd
from common import load_clean, age_curve, summarize, RES, REG_ORDER

d = load_clean()
print("件数", len(d))
curves, rows = {}, []

def run(label, sub, **kw):
    r = age_curve(sub, **kw)
    curves[label] = r; rows.append(summarize(r, label))
    print(label, r.attrs["n"], {k: round(v, 1) for k, v in rows[-1].items() if isinstance(v, float)})

run("基本（全国）", d)
run("物件の特徴をそろえない", d, controls=False)
run("固定効果を都道府県×四半期に粗くする", d.assign(cell=d.pref + "_" + d.yq))
for g in REG_ORDER:
    run(f"地域：{g}", d[d.region == g])
run("地域：東京23区", d[d.muni.astype(int).between(13101, 13123)])
for a, b in [(2015, 2017), (2019, 2021), (2023, 2025)]:
    run(f"期間：{a}〜{b}年", d[d.year.between(a, b)])
run("構造：RC", d[d.struct == "RC"])
run("構造：SRC", d[d.struct == "SRC"])
run("1982年以降に建った物件だけ（新耐震）", d[d.built >= 1982], ages=range(0, 44))
run("基準を築2年にする", d, ref=2)

S = pd.DataFrame(rows); S.to_csv(RES / "summary_by_spec.csv", index=False)
pd.concat([c.assign(spec=k) for k, c in curves.items()]).to_csv(RES / "age_curves.csv", index=False)

# 何も補正しない中央値（比較用）
med = d.groupby("age").ppm2.agg(["median", "size"]).reset_index()
med["rel_median"] = med["median"] / med.loc[med.age == 1, "median"].values[0]
med.to_csv(RES / "raw_median_by_age.csv", index=False)

# 「新築に近い」差は、そのあとの何年分の値下がりにあたるか
m = curves["基本（全国）"].set_index("age")
rate_1_10 = -(m.b[10] - m.b[1]) / 9                         # 築1〜10年の1年あたりの下がり（log）
rate_2_10 = -(m.b[10] - m.b[2]) / 8
prem = pd.DataFrame([
    {"指標": "築0年と築1年の差（%）", "値": (np.exp(m.b[0] - m.b[1]) - 1) * 100},
    {"指標": "築0年と築2年の差（%）", "値": (np.exp(m.b[0] - m.b[2]) - 1) * 100},
    {"指標": "築1〜10年の1年あたりの下がり（%）", "値": (1 - np.exp(-rate_1_10)) * 100},
    {"指標": "築2〜10年の1年あたりの下がり（%）", "値": (1 - np.exp(-rate_2_10)) * 100},
    {"指標": "築0→1年の差は、築1〜10年の何年分か", "値": (m.b[0] - m.b[1]) / rate_1_10},
    {"指標": "築0→2年の差は、築2〜10年の何年分か", "値": (m.b[0] - m.b[2]) / rate_2_10},
])
prem.to_csv(RES / "new_premium_years.csv", index=False)
print(prem)

# 築年数ごとの件数
d.groupby("age").size().rename("件数").to_csv(RES / "count_by_age.csv")
# 1年ごとの下がり方（基本）
r = curves["基本（全国）"].sort_values("age")
r["前年からの変化（%）"] = (np.exp(r.b.diff()) - 1) * 100
r.to_csv(RES / "main_curve.csv", index=False)
