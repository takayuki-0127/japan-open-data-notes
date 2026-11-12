"""A424 人口の「真ん中の年齢」（中央値）を国勢調査の5歳階級から計算する。1920〜2020年"""
import csv, json, re
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
SRC = "出典：総務省統計局「国勢調査」時系列データ 第2表（年齢5歳階級、男女別人口 1920〜2020年）をもとに作成者が加工して作成"
rows = [r for r in csv.reader(open(DATA / "kokusei_ts_t2_age5_sex_1920_2020.csv", encoding="utf-8")) if r and re.match(r"\d{4}年", r[0])]
num = lambda s: float(s) if str(s).strip() not in ("", "-", "…") else np.nan
rec = []
for r in rows:
    m = re.match(r"(\d+)～(\d+)歳", r[2]); m2 = re.match(r"(\d+)歳以上", r[2])
    if r[2].startswith("（再掲）") or r[2].strip() == "総数": continue
    lo = int(m.group(1)) if m else (int(m2.group(1)) if m2 else None)
    if lo is None: continue
    rec.append([int(r[0][:4]), lo, r[2], num(r[4]), num(r[5]), num(r[6]), r[3].strip()])
allr = pd.DataFrame(rec, columns=["year", "lo", "label", "T", "M", "F", "mark"]).dropna(subset=["T"])
a = allr[allr.mark == ""].copy()          # 2015・2020年は「年齢不詳をあん分した値（※）」も載っている。本文は、ほかの年とそろえて元の値を使う
alt = allr[allr.mark == "※"].copy()
tot = {int(r[0][:4]): num(r[4]) for r in rows if r[2].strip() == "総数"}

def classes(g, col):
    """5歳階級にそろえる。85歳以上と85〜89歳などが両方ある年は、細かいほうを使う"""
    g = g.sort_values("lo"); has_fine = (g.label == "85～89歳").any()
    if has_fine: g = g[g.label != "85歳以上"]
    return g[["lo", "label", col]].rename(columns={col: "n"})

def median_age(g, col):
    c = classes(g, col); n = c.n.values; lo = c.lo.values; cum = np.cumsum(n); half = cum[-1] / 2
    i = int(np.searchsorted(cum, half)); prev = cum[i - 1] if i else 0
    return lo[i] + 5 * (half - prev) / n[i]          # 階級の中は年齢が均等に並ぶと置く

def mean_age(g, col):
    c = classes(g, col); mid = np.where(c.label.str.contains("以上"), c.lo + 5.0, c.lo + 2.5)   # 上が開いた階級は下限+5歳と置く（粗い）
    return float((mid * c.n).sum() / c.n.sum())

res = []
for y, g in a.groupby("year"):
    c = classes(g, "T"); known = c.n.sum()
    res.append({"year": y, "median": median_age(g, "T"), "median_m": median_age(g, "M"), "median_f": median_age(g, "F"), "mean": mean_age(g, "T"),
                "under15": c[c.lo < 15].n.sum() / known * 100, "over65": c[c.lo >= 65].n.sum() / known * 100,
                "pop": tot[y], "age_unknown_pct": (tot[y] - known) / tot[y] * 100})
d = pd.DataFrame(res); d.round(3).to_csv(RES / "a424_median_age.csv", index=False)
R = d.set_index("year"); out = {f"y{y}": {k: round(float(R.loc[y, k]), 1) for k in ["median", "median_m", "median_f", "mean", "under15", "over65"]} for y in d.year}
out["age_unknown_pct_max"] = {"year": int(d.loc[d.age_unknown_pct.idxmax(), "year"]), "pct": round(float(d.age_unknown_pct.max()), 2)}
# しきい値を超えた最初の調査年と、直線で内挿した年
th = {}
for t in [25, 30, 35, 40, 45]:
    ab = d[d["median"] >= t]
    if len(ab):
        y1 = int(ab.year.iloc[0]); y0 = y1 - 5; v0, v1 = R.loc[y0, "median"], R.loc[y1, "median"]
        th[str(t)] = {"first_census": y1, "interp_year": round(y0 + 5 * (t - v0) / (v1 - v0), 1)}
out["thresholds"] = th
v20 = R.loc[1920, "median"]; steps = []
for k in [10, 20]:
    ab = d[d["median"] >= v20 + k]; y1 = int(ab.year.iloc[0]); y0 = y1 - 5
    steps.append({"plus": k, "target": round(v20 + k, 1), "interp_year": round(y0 + 5 * (v20 + k - R.loc[y0, "median"]) / (R.loc[y1, "median"] - R.loc[y0, "median"]), 1)})
out["plus10_steps"] = steps
out["rise"] = {f"{a_}_{b_}": round(float(R.loc[b_, "median"] - R.loc[a_, "median"]), 1) for a_, b_ in [(1920, 1950), (1950, 1970), (1970, 1990), (1990, 2010), (2010, 2020), (1920, 2020), (1950, 2020)]}
d["d5"] = d["median"].diff(); out["fastest_5y"] = {"to": int(d.loc[d.d5.idxmax(), "year"]), "years": round(float(d.d5.max()), 2)}
out["per_decade"] = {f"{y-10}_{y}": round(float(R.loc[y, "median"] - R.loc[y - 10, "median"]), 1) for y in range(1930, 2021, 10)}
out["sex_gap"] = {str(y): round(float(R.loc[y, "median_f"] - R.loc[y, "median_m"]), 1) for y in [1920, 1950, 1980, 2000, 2020]}
out["median_minus_mean"] = {str(y): round(float(R.loc[y, "median"] - R.loc[y, "mean"]), 1) for y in [1920, 1950, 1980, 2000, 2020]}
# 頑健性：階級の中を「直線で内挿」ではなく、前後の階級の人数で傾きをつけた場合（台形）
def median_trap(g, col):
    c = classes(g, col); n = c.n.values; lo = c.lo.values; cum = np.cumsum(n); half = cum[-1] / 2
    i = int(np.searchsorted(cum, half)); prev = cum[i - 1] if i else 0
    dl = (n[i - 1] + n[i]) / 2 / 5; dr = (n[i] + n[i + 1]) / 2 / 5      # 階級の両端での密度（人/歳）
    scale = n[i] / ((dl + dr) / 2 * 5); dl, dr = dl * scale, dr * scale; need = half - prev
    aa = (dr - dl) / 10; bb = dl; cc = -need
    x = (-bb + np.sqrt(bb * bb - 4 * aa * cc)) / (2 * aa) if abs(aa) > 1e-9 else need / bb
    return lo[i] + x
out["robust_trapezoid"] = {str(y): round(float(median_trap(g, "T")), 2) for y, g in a.groupby("year") if y in (1920, 1950, 1980, 2000, 2020)}
out["robust_trapezoid_maxdiff"] = round(float(max(abs(median_trap(g, "T") - median_age(g, "T")) for y, g in a.groupby("year"))), 2)
out["robust_imputed_unknown"] = {str(y): {"median": round(float(median_age(g, "T")), 2), "diff_vs_main": round(float(median_age(g, "T") - R.loc[y, "median"]), 2)} for y, g in alt.groupby("year")}
json.dump(out, open(RES / "a424_main.json", "w"), ensure_ascii=False, indent=1)

fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(d.year, d.median_f, color=ORANGE, lw=1.6, marker="o", ms=3.5, label="女"); ax.plot(d.year, d.median_m, color=BLUE, lw=1.6, marker="o", ms=3.5, label="男")
ax.plot(d.year, d["median"], color=INK, lw=2.4, marker="o", ms=4, label="男女計")
for y in [1920, 1950, 1980, 2000, 2020]: ax.annotate(f"{y}年\n{R.loc[y,'median']:.1f}歳", (y, R.loc[y, "median"]), textcoords="offset points", xytext=(4, -26) if y == 1920 else (-4, 10), ha="left" if y == 1920 else "right", fontsize=8.5)
ax.set_ylim(18, 54); ax.legend(frameon=False, loc="upper left"); ax.set_ylabel("年齢の中央値（歳）")
ax.set_title("人口の真ん中の年齢は、1920年の22歳から2020年の48歳になった"); save(fig, "a424_median.png", SRC)
fig, ax = plt.subplots(figsize=(9, 4.6)); c = d.dropna(subset=["d5"])
ax.bar(c.year, c.d5, width=3.6, color=[ORANGE if v >= 2 else BLUE for v in c.d5]); ax.axhline(0, color=INK, lw=.8)
for y, v in zip(c.year, c.d5): ax.text(y, v + (0.06 if v >= 0 else -0.06), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.set_xticks(c.year); ax.set_xticklabels([f"{int(y)-5}→\n{str(int(y))[2:]}" for y in c.year], fontsize=7.5)
ax.set_ylabel("5年間に上がった年齢（歳）"); ax.set_title("上がり方が速かったのは1975〜95年（5年で2.2〜2.5歳）"); save(fig, "a424_rise_5y.png", SRC)
fig, ax = plt.subplots(figsize=(9, 4.8))
for y, col in [(1920, GRAY), (1950, GREEN), (1980, BLUE), (2020, ORANGE)]:
    c = classes(a[a.year == y], "T"); cum = np.concatenate([[0], np.cumsum(c.n.values) / c.n.sum() * 100]); x = np.concatenate([c.lo.values, [c.lo.values[-1] + 5]])
    ax.plot(x, cum, color=col, lw=2, label=f"{y}年（中央値{R.loc[y,'median']:.1f}歳）")
ax.axhline(50, color="#cccccc", lw=.8); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_xlabel("年齢（歳）"); ax.set_ylabel("その年齢より若い人の割合（%）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("線が50%を横切る年齢が、真ん中の年齢"); save(fig, "a424_cumulative.png", SRC)
print(json.dumps(out, ensure_ascii=False))
