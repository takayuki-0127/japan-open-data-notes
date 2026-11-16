"""問い直し：流氷が来ない年は増えたのか（稚内・釧路）。年ごとのばらつきの大きさも並べる。
H2 で、減り方が氷の季節の終わりだけでなく始まり（12〜1月）でも大きかったため、
「沿岸に流氷が来るかどうか」という形で見直す（PLAN の問い直しの候補の2つ目。1つ目もあわせて計算）。"""
import json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RES = os.path.join(HERE, "..", "results")

st = pd.read_csv(os.path.join(DATA, "stations.csv"))
s = pd.read_csv(os.path.join(DATA, "season.csv"), index_col=0)

# 1) 流氷が来なかった年の数（10年ごと）。観測が続いた3地点
rows = []
for key in ("wakkanai", "abashiri", "kushiro"):
    d = st[st.station == key].set_index("season")
    for dec0 in range(1946, 2026, 10):
        dd = d.loc[dec0:dec0 + 9]
        rows.append({"station": key, "name": d["name"].iloc[0], "from": dec0, "to": min(dec0 + 9, 2025),
                     "years": int(len(dd)), "no_ice_years": int(dd["no_ice"].sum())})
noice = pd.DataFrame(rows)
noice.to_csv(os.path.join(RES, "requestion_no_ice.csv"), index=False)

# 2) 30年ずつ：流氷が来なかった年の割合、初日の平均
cmp_rows = []
for key in ("wakkanai", "abashiri", "kushiro"):
    d = st[st.station == key].set_index("season")
    for a, b in ((1946, 1975), (1996, 2025)):
        dd = d.loc[a:b]
        cmp_rows.append({"station": key, "name": d["name"].iloc[0], "from": a, "to": b,
                         "no_ice_years": int(dd["no_ice"].sum()), "years": int(len(dd)),
                         "first_mean_when_ice": round(float(dd.loc[dd["no_ice"] == 0, "first"].mean()), 1)})
cmpd = pd.DataFrame(cmp_rows)
cmpd.to_csv(os.path.join(RES, "requestion_no_ice_30y.csv"), index=False)
# 釧路で最後に流氷が来た年と、そのあと続いた来ない年
k = st[st.station == "kushiro"].set_index("season")
last_ice = int(k.index[k["no_ice"] == 0].max())
streak = int((k.loc[last_ice + 1:, "no_ice"] == 1).sum())

# 3) ばらつき：積算海氷域面積の、長期の傾きを除いた残りの標準偏差（期間ごと）
z = s["acc_dec_may"].dropna()
x = z.index.values.astype(float)
b = np.polyfit(x, z.values, 1)
resid = pd.Series(z.values - np.polyval(b, x), index=z.index)
fit = pd.Series(np.polyval(b, x), index=z.index)
var = []
for a, c in ((1972, 1990), (1991, 2008), (2009, 2026)):
    rr = resid.loc[a:c]
    var.append({"from": a, "to": c, "n": int(len(rr)), "sd_resid": round(float(rr.std(ddof=1)), 1),
                "mean_fit": round(float(fit.loc[a:c].mean()), 1),
                "cv_pct": round(float(rr.std(ddof=1) / fit.loc[a:c].mean() * 100), 1)})
vd = pd.DataFrame(var)
vd.to_csv(os.path.join(RES, "requestion_variability.csv"), index=False)

out = {"no_ice_30y": cmp_rows, "kushiro_last_ice_season": last_ice, "kushiro_no_ice_streak_after": streak,
       "variability": var}
with open(os.path.join(RES, "requestion.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
print(noice.pivot(index="from", columns="name", values="no_ice_years"))
