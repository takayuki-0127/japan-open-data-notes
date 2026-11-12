"""A422 中学校を出てすぐ働く人の割合と人数。学校基本調査 年次統計 総括表5・13"""
import csv, json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
SRC = "出典：文部科学省「学校基本調査」年次統計（総括表5 卒業者に占める就職者の割合、総括表13 卒業者数）をもとに作成者が加工して作成"
num = lambda s: float(str(s).replace(",", "")) if str(s).strip() not in ("-", "…", "－", "") else np.nan
r5 = [r for r in csv.reader(open(DATA / "gakkou_nenji_soukatsu5_shushoku_rate.csv", encoding="utf-8")) if len(r) > 4 and r[1].strip().isdigit()]
r13 = [r for r in csv.reader(open(DATA / "gakkou_nenji_soukatsu13_graduates.csv", encoding="utf-8")) if len(r) > 4 and r[1].strip().isdigit()]
# 総括表5：列2〜4＝中学校卒業者（計・男・女）、列5〜7＝中学校・義務教育学校等を含む（計・男・女）、列8〜10＝高等学校卒業者
a = pd.DataFrame([[int(r[1])] + [num(x) for x in r[2:11]] for r in r5],
                 columns=["year", "rate", "rate_m", "rate_f", "rate_all", "rate_all_m", "rate_all_f", "hs_rate", "hs_rate_m", "hs_rate_f"])
b = pd.DataFrame([[int(r[1]), num(r[4]), num(r[6])] for r in r13], columns=["year", "grads", "hs_grads"])
d = a.merge(b, on="year", how="left")
d["workers_est"] = d.rate / 100 * d.grads          # 割合×卒業者数（割合が小数第1位までなので概算）
d["hs_workers_est"] = d.hs_rate / 100 * d.hs_grads
d.to_csv(RES / "a422_rate_and_number.csv", index=False)
R = d.set_index("year"); out = {"years": [int(d.year.min()), int(d.year.max())]}
for y in [1950, 1952, 1955, 1960, 1963, 1965, 1970, 1975, 1980, 1990, 2000, 2010, 2020, 2025]:
    out[f"y{y}"] = {k: (None if pd.isna(R.loc[y, k]) else round(float(R.loc[y, k]), 1)) for k in ["rate", "rate_m", "rate_f", "grads", "workers_est", "hs_rate"]}
pk = d.loc[d.rate.idxmax()]; out["rate_peak"] = {"year": int(pk.year), "rate": float(pk.rate)}
pn = d.loc[d.workers_est.idxmax()]; out["number_peak"] = {"year": int(pn.year), "workers_est": int(round(pn.workers_est, -3)), "grads": int(pn.grads), "rate": float(pn.rate)}
gp = d.loc[d.grads.idxmax()]; out["grads_peak"] = {"year": int(gp.year), "grads": int(gp.grads)}
th = {}
for t in [40, 30, 20, 10, 5, 3, 2, 1, 0.5]:
    for c in ["rate", "rate_m", "rate_f"]:
        bl = d[d[c] < t]
        th.setdefault(str(t), {})[c] = {"first_below": int(bl.year.iloc[0]), "last_at_or_above": int(d[d[c] >= t].year.max())} if len(bl) else None
out["thresholds"] = th
# 10年ごとの下がり方（ポイント）と人数
dec = []
for y0, y1 in [(1950, 1960), (1960, 1970), (1970, 1980), (1980, 1990), (1990, 2000), (2000, 2010), (2010, 2020), (2020, 2025)]:
    dec.append({"from": y0, "to": y1, "rate_from": R.loc[y0, "rate"], "rate_to": R.loc[y1, "rate"], "pt": round(R.loc[y1, "rate"] - R.loc[y0, "rate"], 1),
                "workers_from": int(round(R.loc[y0, "workers_est"], -3)), "workers_to": int(round(R.loc[y1, "workers_est"], -2))})
pd.DataFrame(dec).to_csv(RES / "a422_by_decade.csv", index=False); out["by_decade"] = dec
# 1年でいちばん大きく下がった年
d["diff"] = d.rate.diff(); mn = d.loc[d["diff"].idxmin()]; out["largest_1y_drop"] = {"year": int(mn.year), "pt": round(float(mn["diff"]), 1)}
out["drop_1960_1970_per_year"] = round((R.loc[1970, "rate"] - R.loc[1960, "rate"]) / 10, 2)
# 人数の変化を「卒業者の数」と「割合」に分ける（1963年→1975年）
y0, y1 = 1963, 1975
dn = R.loc[y1, "workers_est"] - R.loc[y0, "workers_est"]
eff_g = (R.loc[y1, "grads"] - R.loc[y0, "grads"]) * (R.loc[y0, "rate"] + R.loc[y1, "rate"]) / 200
eff_r = (R.loc[y1, "rate"] - R.loc[y0, "rate"]) / 100 * (R.loc[y0, "grads"] + R.loc[y1, "grads"]) / 2
out["decomp_1963_1975"] = {"change": int(round(dn, -3)), "from_grads": int(round(eff_g, -3)), "from_rate": int(round(eff_r, -3))}
# 男女の差、義務教育学校などを含めた率との差、高校卒業者
out["sex_gap_max"] = {"year": int(d.loc[(d.rate_m - d.rate_f).idxmax(), "year"]), "pt": round(float((d.rate_m - d.rate_f).max()), 1)}
out["female_higher_years"] = [int(y) for y in d[d.rate_f > d.rate_m].year]
out["max_diff_incl_gimu"] = round(float((d.rate - d.rate_all).abs().max()), 1)
out["hs_workers_exceed_jhs_year"] = int(d[d.hs_workers_est > d.workers_est].year.iloc[0])
out["hs_peak"] = {"year": int(d.loc[d.hs_workers_est.idxmax(), "year"]), "n": int(round(d.hs_workers_est.max(), -3))}
out["cum_workers_1950_1975_est"] = int(round(d[(d.year >= 1950) & (d.year <= 1975)].workers_est.sum(), -4))
json.dump(out, open(RES / "a422_main.json", "w"), ensure_ascii=False, indent=1)

fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(d.year, d.rate_m, color=BLUE, lw=1.6, label="男"); ax.plot(d.year, d.rate_f, color=ORANGE, lw=1.6, label="女"); ax.plot(d.year, d.rate, color=INK, lw=2.2, label="計")
for t in [40, 10, 1]: ax.axhline(t, color="#dddddd", lw=.8)
for y in [1952, 1960, 1970, 1980, 2025]:
    ax.annotate(f"{y}年 {R.loc[y,'rate']:.1f}%", (y, R.loc[y, "rate"]), textcoords="offset points", xytext=(8, 6), fontsize=8.5)
ax.legend(frameon=False); ax.set_ylabel("中学校卒業者のうち就職した人の割合（%）"); ax.set_ylim(0, 52)
ax.set_title("中学校を出て就職した人の割合は、1952年の47.5%から1970年代に1割を切った"); save(fig, "a422_rate.png", SRC)
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.bar(d.year, d.grads / 1e4, color=LIGHT, label="中学校の卒業者"); ax.bar(d.year, d.workers_est / 1e4, color=ORANGE, label="うち就職した人（割合×卒業者数の概算）")
ax.annotate(f"{int(pn.year)}年 約{pn.workers_est/1e4:.0f}万人", (pn.year, pn.workers_est / 1e4), textcoords="offset points", xytext=(18, 10), fontsize=9, arrowprops=dict(arrowstyle="-", color=GRAY))
ax.legend(frameon=False); ax.set_ylabel("万人"); ax.set_title("就職した人の数は1950年代から60年代前半に年68万〜86万人、いまは2千人ほど"); save(fig, "a422_number.png", SRC)
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(d.year, d.workers_est / 1e4, color=ORANGE, lw=2, label="中学校を出て就職"); ax.plot(d.year, d.hs_workers_est / 1e4, color=BLUE, lw=2, label="高等学校を出て就職")
ax.legend(frameon=False); ax.set_ylabel("万人（割合×卒業者数の概算）"); ax.set_title("就職する人の中心は、1960年代に中学校卒から高校卒へ入れ替わった"); save(fig, "a422_jhs_vs_hs.png", SRC)
print(json.dumps(out, ensure_ascii=False))
