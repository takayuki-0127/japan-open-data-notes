"""A421 乳児死亡率（出生1,000あたり）の長期推移。人口動態統計 上巻 6-1・6-2・6-4"""
import csv, json, math
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
SRC = "出典：厚生労働省「人口動態統計」（2025年確定数 上巻 6-1・6-2・6-4）をもとに作成者が加工して作成"

def rows(f):
    return [r for r in csv.reader(open(DATA / f, encoding="utf-8")) if r and r[0].strip().isdigit()]
num = lambda s: float(str(s).replace(",", "")) if str(s).strip() not in ("-", "…", "") else np.nan
a = pd.DataFrame([[int(r[0]), num(r[1]), num(r[2]), num(r[6])] for r in rows("jinkou_r7_jokan_6-1_infant_deaths.csv")],
                 columns=["year", "births", "infant_deaths", "rate_pub"])
b = pd.DataFrame([[int(r[0]), num(r[1]), num(r[5]), num(r[7])] for r in rows("jinkou_r7_jokan_6-2_neonatal_deaths.csv")],
                 columns=["year", "neonatal_deaths", "neo_rate_pub", "neo_share_pub"])
d = a.merge(b, on="year")
d["rate"] = d.infant_deaths / d.births * 1000          # 自分で計算した率（小数第2位まで使える）
d["neo_rate"] = d.neonatal_deaths / d.births * 1000
d["post_rate"] = d.rate - d.neo_rate
d["neo_share"] = d.neonatal_deaths / d.infant_deaths * 100
assert (d.rate.round(1) - d.rate_pub).abs().max() <= 0.11, (d.rate.round(1) - d.rate_pub).abs().max()
d.to_csv(RES / "a421_rate_by_year.csv", index=False)
R = d.set_index("year")
out = {"n_years": len(d), "missing_years": [y for y in range(1899, 2026) if y not in R.index],
       "max_check_diff_vs_published": float((d.rate.round(1) - d.rate_pub).abs().max())}
for y in [1899, 1900, 1918, 1920, 1925, 1940, 1943, 1947, 1950, 1955, 1960, 1965, 1970, 1975, 1980, 1990, 2000, 2010, 2020, 2025]:
    out[f"y{y}"] = {k: round(float(R.loc[y, k]), 2) for k in ["rate", "neo_rate", "post_rate", "neo_share"]} | {
        "deaths": int(R.loc[y, "infant_deaths"]), "births": int(R.loc[y, "births"])}
pk = d.loc[d.rate.idxmax()]; out["peak"] = {"year": int(pk.year), "rate": round(pk.rate, 1), "deaths": int(pk.infant_deaths)}
# はじめて下回った年（その後に上回った年があるかも記録）
th = {}
for t in [150, 100, 75, 50, 25, 20, 15, 10, 5, 3, 2]:
    below = d[d.rate < t]
    if len(below):
        y0 = int(below.year.iloc[0]); last_above = d[d.rate >= t].year.max()
        th[str(t)] = {"first_below": y0, "last_year_at_or_above": int(last_above)}
out["thresholds"] = th
# 半分になるまでの年数：1920年の率を起点に、半分・4分の1…になった最初の年
steps = []
base_y = 1920; base = R.loc[base_y, "rate"]; k = 1
while True:
    t = base / (2 ** k); bl = d[(d.year > base_y) & (d.rate <= t)]
    if not len(bl): break
    steps.append({"fraction": f"1/{2**k}", "target": round(t, 2), "year": int(bl.year.iloc[0])}); k += 1
for i, s in enumerate(steps): s["years_from_prev"] = s["year"] - (steps[i - 1]["year"] if i else base_y)
out["halvings_from_1920"] = steps
t10 = d[(d.year > 1920) & (d.rate <= base / 10)].year.iloc[0]; t100 = d[(d.year > 1920) & (d.rate <= base / 100)]
out["one_tenth_of_1920"] = {"year": int(t10), "years": int(t10 - 1920)}
out["one_hundredth_of_1920"] = {"year": int(t100.year.iloc[0])} if len(t100) else None
# 10分の1になるのにかかった年数を、起点を変えて
ten = []
for y0 in range(1900, 1990, 10):
    if y0 not in R.index: continue
    bl = d[(d.year > y0) & (d.rate <= R.loc[y0, "rate"] / 10)]
    ten.append({"start": y0, "start_rate": round(R.loc[y0, "rate"], 1), "year": int(bl.year.iloc[0]) if len(bl) else None,
                "years": int(bl.year.iloc[0] - y0) if len(bl) else None})
out["one_tenth_by_start"] = ten
# 期間ごとの年あたりの下がり方（対数の差÷年数）
per = []
edges = [1899, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025]
for y0, y1 in zip(edges[:-1], edges[1:]):
    r = (math.log(R.loc[y1, "rate"]) - math.log(R.loc[y0, "rate"])) / (y1 - y0)
    per.append({"from": y0, "to": y1, "rate_from": round(R.loc[y0, "rate"], 2), "rate_to": round(R.loc[y1, "rate"], 2),
                "annual_change_pct": round((math.exp(r) - 1) * 100, 2),
                "neo_annual_pct": round((math.exp((math.log(R.loc[y1, "neo_rate"]) - math.log(R.loc[y0, "neo_rate"])) / (y1 - y0)) - 1) * 100, 2),
                "post_annual_pct": round((math.exp((math.log(R.loc[y1, "post_rate"]) - math.log(R.loc[y0, "post_rate"])) / (y1 - y0)) - 1) * 100, 2)})
pd.DataFrame(per).to_csv(RES / "a421_change_by_period.csv", index=False); out["by_period"] = per
# 頑健性：3年移動平均で同じしきい値、沖縄を含まない期間の注記、1947年の前後
d["ma3"] = d.rate.rolling(3, center=True, min_periods=2).mean()
out["robust_ma3_first_below"] = {str(t): int(d[d.ma3 < t].year.iloc[0]) for t in [100, 50, 25, 10, 5]}
out["drop_1900_1950"] = {"abs": round(R.loc[1900, "rate"] - R.loc[1950, "rate"], 1), "neo": round(R.loc[1900, "neo_rate"] - R.loc[1950, "neo_rate"], 1),
                         "post": round(R.loc[1900, "post_rate"] - R.loc[1950, "post_rate"], 1)}
out["drop_1950_2000"] = {"abs": round(R.loc[1950, "rate"] - R.loc[2000, "rate"], 1), "neo": round(R.loc[1950, "neo_rate"] - R.loc[2000, "neo_rate"], 1),
                         "post": round(R.loc[1950, "post_rate"] - R.loc[2000, "post_rate"], 1)}
out["survive_per_1000"] = {str(y): round(1000 - R.loc[y, "rate"], 1) for y in [1900, 1950, 2000, 2025]}
out["one_in"] = {str(y): round(1000 / R.loc[y, "rate"], 1) for y in [1900, 1918, 1950, 1975, 2000, 2025]}
# 生存期間別（6-4、出生10万対、1950年〜）
raw = [r for r in csv.reader(open(DATA / "jinkou_r7_jokan_6-4_by_survival_period.csv", encoding="utf-8"))]
hdr = next(r for r in raw if len(r) > 3 and r[2].strip() == "1950"); yrs = [int(x) for x in hdr[2:]]
i0 = raw.index(hdr); tot = {}
for r in raw[i0 + 1:i0 + 12]:
    key = r[1].replace("　", "").strip()
    if key: tot[key] = [num(x) for x in r[2:2 + len(yrs)]]
sp = pd.DataFrame(tot, index=yrs); sp.to_csv(RES / "a421_by_survival_period_total.csv")
out["survival_period"] = {str(y): {k: sp.loc[y, k] for k in sp.columns[:3]} for y in [1950, 1975, 2000, 2025]}
json.dump(out, open(RES / "a421_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：率（対数の目盛り）
fig, ax = plt.subplots(figsize=(9, 4.8))
for seg in [d[d.year <= 1943], d[d.year >= 1947]]:
    ax.plot(seg.year, seg.rate, color=BLUE, lw=2)
ax.set_yscale("log"); ax.set_yticks([1, 2, 5, 10, 20, 50, 100, 200]); ax.set_yticklabels(["1", "2", "5", "10", "20", "50", "100", "200"])
for y, dy in [(1899, -30), (1918, 8), (1950, 8), (1975, 8), (2000, 8), (2025, 8)]:
    ax.annotate(f"{y}年\n{R.loc[y,'rate']:.1f}", (y, R.loc[y, "rate"]), textcoords="offset points", xytext=(0, dy), ha="center", fontsize=8.5, color=INK)
ax.set_ylim(1, 330)
ax.axvspan(1943.5, 1946.5, color=LIGHT, alpha=.5); ax.text(1945, 1.3, "1944〜46年\nは数字なし", ha="center", fontsize=8, color=GRAY)
ax.set_ylabel("出生1,000あたりの乳児死亡（対数の目盛り）"); ax.set_title("乳児死亡率は、1899年の153.8から2025年の1.9になった", pad=12)
ax.grid(axis="y", color="#e6e6e6", lw=.6); save(fig, "a421_rate_log.png", SRC)
# 図2：期間ごとの年あたりの変化率
P = pd.DataFrame(per); fig, ax = plt.subplots(figsize=(9, 4.6))
lab = [f"{a}〜\n{str(b)[2:]}年" for a, b in zip(P["from"], P["to"])]
c = [ORANGE if v < -6 else BLUE for v in P.annual_change_pct]
ax.bar(range(len(P)), P.annual_change_pct, color=c)
for i, v in enumerate(P.annual_change_pct): ax.text(i, v - 0.25 if v < 0 else v + 0.1, f"{v:+.1f}%", ha="center", va="top" if v < 0 else "bottom", fontsize=8.5)
ax.set_xticks(range(len(P))); ax.set_xticklabels(lab, fontsize=8.5); ax.axhline(0, color=INK, lw=.8)
ax.set_ylabel("乳児死亡率の年あたりの変化率（%）"); ax.set_ylim(-9.6, 1.6); ax.set_title("下がり方がいちばん速かったのは、1950年代と1960年代（年に6.5%と8.1%）")
save(fig, "a421_change_by_period.png", SRC)
# 図3：新生児とそれ以後
fig, ax = plt.subplots(figsize=(9, 4.8))
for seg in [d[d.year <= 1943], d[d.year >= 1947]]:
    ax.plot(seg.year, seg.neo_rate, color=ORANGE, lw=2, label="生後4週（1943年までは1か月）未満" if seg.year.iloc[0] < 1900 else None)
    ax.plot(seg.year, seg.post_rate, color=BLUE, lw=2, label="それ以後、1歳になるまで" if seg.year.iloc[0] < 1900 else None)
ax.set_yscale("log"); ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100]); ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100"])
ax.legend(frameon=False); ax.grid(axis="y", color="#e6e6e6", lw=.6)
ax.set_ylabel("出生1,000あたりの死亡（対数の目盛り）"); ax.set_title("1950〜60年代は「4週以後」が速く減り、1980年代は「4週未満」が速く減った")
save(fig, "a421_neonatal_vs_post.png", SRC)
print(json.dumps(out, ensure_ascii=False)[:3000])
