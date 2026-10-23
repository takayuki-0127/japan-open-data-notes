"""どこで、どれくらいの強さの竜巻が多いか（2007〜2025年、陸上などの竜巻）"""
from common import *

d = load()
t = tornado(d)
tp = t[(t.year >= 2007) & (t.year <= 2025)]
pref = tp.groupby("pref").size().sort_values(ascending=False)
pref.to_csv(RES / "a135_pref.csv", header=["件数"])
sc = tp.f_max.value_counts(dropna=False)
sc.to_csv(RES / "a135_scale.csv", header=["件数"])
rated = tp.f_max.dropna()
lines = ["都道府県・地方（上位10）: " + ", ".join(f"{k}{v}" for k, v in pref.head(10).items())]
lines.append(f"最大スケールの評定あり {len(rated)}件: " + ", ".join(f"{int(k)}:{v}({v/len(rated):.0%})" for k, v in rated.value_counts().sort_index().items()))
dead = tornado(d)[tornado(d).deaths > 0]
lines.append("死者のあった竜巻（1961〜）: " + ", ".join(f"{int(r.year)}年{int(r.month)}月 {r.pref} {int(r.deaths)}人" for r in dead.itertuples()))
(RES / "a135_place_summary.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
