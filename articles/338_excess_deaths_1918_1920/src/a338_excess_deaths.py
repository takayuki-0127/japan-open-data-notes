"""338：1918〜20年の流行（スペインかぜ）で、死亡はふだんよりどれだけ多かったのか。
年ごとの死亡数・死亡率（総数・男女・主な死因）に、前後の年から「ふだんの死亡率」を作って差を取る。
月別の死亡数は5年おき（1915・1920・1925年）しか公開の表にないので、1920年だけ月ごとに見る。
"""
import csv, json, re
import numpy as np, pandas as pd, xlrd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：厚生労働省「人口動態統計」（上巻 第5.12表、総務省統計局「日本の長期統計系列」2-26・2-28）をもとに作成者が加工して作成"
R = list(csv.reader(open(DATA / "raw" / "jinkou_h26_jokan_5-12_cause_by_year.csv", encoding="utf-8")))
names = ["死亡総数"] + [x for x in R[14][3::2]]
isblock = lambda r: bool(r) and r[0].strip() in ("総数", "男", "女") and not any(x.strip() for x in r[1:])
blocks = {r[0].strip(): i for i, r in enumerate(R) if isblock(r)}
num = lambda x: float(x) if re.fullmatch(r"-?\d+(\.\d+)?", x.strip()) else np.nan
rec = []
for sex, i in blocks.items():
    for r in R[i + 1:]:
        if isblock(r): break
        if r and r[0].strip().isdigit() and len(r) >= 2 * len(names) + 1:
            for j, nm in enumerate(names):
                rec.append((sex, int(r[0]), nm, num(r[1 + 2 * j]), num(r[2 + 2 * j])))
L = pd.DataFrame(rec, columns=["sex", "year", "cause", "deaths", "rate"])
L = L[(L.year >= 1899) & (L.year <= 1935)]; L.to_csv(DATA / "deaths_by_cause_1899_1935.csv", index=False)
T = L[L.cause == "死亡総数"].pivot(index="year", columns="sex", values=["deaths", "rate"])
pop = (T["deaths"]["総数"] / T["rate"]["総数"] * 1e5)            # 率の分母の人口（死亡数÷死亡率）

EPI = [1918, 1919, 1920]
def excess(sub, lo=1910, hi=1927, drop=(1923,)):
    """流行の3年（と関東大震災の1923年）を除いた前後の年の死亡率に直線を当て、差を人数に直す"""
    d = sub.set_index("year"); yrs = [y for y in range(lo, hi + 1) if y not in EPI and y not in drop and not np.isnan(d.rate.get(y, np.nan))]
    k = np.polyfit(yrs, d.rate.loc[yrs].values, 1); res = d.rate.loc[yrs].values - np.polyval(k, yrs)
    o = {}
    for y in EPI:
        p = d.deaths[y] / d.rate[y] * 1e5; e = np.polyval(k, y)
        o[y] = {"actual": int(d.deaths[y]), "expected": round(e * p / 1e5), "excess": round((d.rate[y] - e) * p / 1e5), "excess_pct": round((d.rate[y] / e - 1) * 100, 1)}
    o["total_excess"] = sum(o[y]["excess"] for y in EPI); o["resid_sd_pct"] = round(float(res.std(ddof=2) / d.rate.loc[yrs].mean() * 100), 1)
    return o
out = {"all": {sx: excess(L[(L.cause == "死亡総数") & (L.sex == sx)]) for sx in ("総数", "男", "女")}}
out["population_1918_man"] = round(float(pop[1918]) / 1e4)
out["excess_per_1000_pop"] = round(out["all"]["総数"]["total_excess"] / float(pop[1918]) * 1000, 1)
out["by_cause"] = {}
for c in ("肺炎", "結核", "心疾患（高血圧性を除く）", "脳血管疾患", "老衰", "悪性新生物"):
    sub = L[(L.cause == c) & (L.sex == "総数")]
    if sub.rate.notna().sum() > 10: out["by_cause"][c] = excess(sub)
oth = out["all"]["総数"]["total_excess"] - sum(v["total_excess"] for v in out["by_cause"].values())
out["other_causes_excess"] = oth
out["pneumonia_share_pct"] = round(out["by_cause"]["肺炎"]["total_excess"] / out["all"]["総数"]["total_excess"] * 100, 1)
# 窓を変える
out["robust"] = {f"{lo}-{hi}": excess(L[(L.cause == "死亡総数") & (L.sex == "総数")], lo, hi)["total_excess"] for lo, hi in ((1908, 1930), (1912, 1925), (1905, 1927))}
flat = L[(L.cause == "死亡総数") & (L.sex == "総数")].set_index("year")
base5 = flat.rate.loc[1913:1917].mean()
out["robust"]["mean_1913_17"] = round(sum((flat.rate[y] - base5) * flat.deaths[y] / flat.rate[y] for y in EPI))
# もう1つの「ふだん」：流行のすぐ前後の4年（1916・1917・1921・1922年）の死亡率の平均
base4 = flat.rate.loc[[1916, 1917, 1921, 1922]].mean()
out["near_years_baseline"] = {y: round((flat.rate[y] - base4) * flat.deaths[y] / flat.rate[y]) for y in EPI}
out["near_years_baseline"]["total_excess"] = sum(out["near_years_baseline"][y] for y in EPI)
pn = L[(L.cause == "肺炎") & (L.sex == "総数")].set_index("year"); b4p = pn.rate.loc[[1916, 1917, 1921, 1922]].mean()
out["near_years_baseline"]["pneumonia_excess"] = round(sum((pn.rate[y] - b4p) * pn.deaths[y] / pn.rate[y] for y in EPI))
# 乳児（1歳未満）とそれ以外
s = xlrd.open_workbook(DATA / "raw" / "chouki_02-26.xls").sheet_by_index(0)
inf = {}
for r in range(s.nrows):
    v = s.row_values(r); m = re.match(r"\s*(\d{4})", str(v[1]))
    if m and isinstance(v[3], float): inf[int(m.group(1))] = (v[2], v[3], v[6])
I = pd.DataFrame(inf, index=["births", "inf", "imr"]).T; I.loc[1905:1930].to_csv(DATA / "infant_deaths_1905_1930.csv")
yrs = [y for y in range(1910, 1928) if y not in EPI and y != 1923]
k = np.polyfit(yrs, I.imr.loc[yrs].values, 1)
out["infant"] = {y: {"imr": float(I.imr[y]), "expected_imr": round(float(np.polyval(k, y)), 1), "excess": round(float((I.imr[y] - np.polyval(k, y)) * I.births[y] / 1000))} for y in EPI}
out["infant"]["total_excess"] = sum(out["infant"][y]["excess"] for y in EPI)
out["infant_share_of_excess_pct"] = round(out["infant"]["total_excess"] / out["all"]["総数"]["total_excess"] * 100, 1)
b4i = I.imr.loc[[1916, 1917, 1921, 1922]].mean()
out["near_years_baseline"]["infant_excess"] = round(float(sum((I.imr[y] - b4i) * I.births[y] / 1000 for y in EPI)))
out["infant_share_of_usual_deaths_pct"] = round(float(I.inf.loc[1913:1917].sum() / flat.deaths.loc[1913:1917].sum() * 100), 1)
# 月別（1915・1920・1925年）
s = xlrd.open_workbook(DATA / "raw" / "chouki_02-28.xls").sheet_by_index(0)
mon, sec = {}, None
for r in range(s.nrows):
    v = s.row_values(r)
    if str(v[1]).startswith("Deaths"): sec = "d"
    elif str(v[1]).startswith("Live"): sec = "b"
    elif sec == "d" and isinstance(v[1], float) and int(v[1]) in (1910, 1915, 1920, 1925, 1930): mon[int(v[1])] = [float(x) for x in v[3:15]]
Mn = pd.DataFrame(mon, index=range(1, 13)); Mn.to_csv(DATA / "monthly_deaths_5yearly.csv")
days = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]); d20 = days.copy(); d20[1] = 29
per = {y: Mn[y].values / (d20 if y == 1920 else days) for y in Mn}
usual = (per[1915] + per[1925]) / 2
out["monthly_1920"] = {int(m): {"deaths": int(Mn[1920][m]), "ratio_to_1915_25": round(float(per[1920][m - 1] / usual[m - 1]), 2)} for m in range(1, 13)}
out["monthly_1920_excess_vs_1915_25"] = {int(m): round(float((per[1920][m - 1] - usual[m - 1]) * d20[m - 1])) for m in range(1, 13)}
out["jan_mar_1920_excess"] = sum(out["monthly_1920_excess_vs_1915_25"][m] for m in (1, 2, 3))
json.dump(out, open(RES / "a338_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame([{"sex": sx, "year": y, **out["all"][sx][y]} for sx in out["all"] for y in EPI]).to_csv(RES / "excess_by_year_sex.csv", index=False)

# 図1：死亡率と「ふだん」の線
fig, ax = plt.subplots(figsize=(8.6, 4.3))
d = flat.loc[1905:1930]; ax.plot(d.index, d.rate / 100, "-o", color=BLUE, ms=4)
yrs = [y for y in range(1910, 1928) if y not in EPI and y != 1923]; k = np.polyfit(yrs, flat.rate.loc[yrs].values, 1)
ax.plot([1910, 1927], np.polyval(k, [1910, 1927]) / 100, "--", color=GRAY, lw=1.2, label="前後の年に当てた「ふだん」の線")
a = out["all"]["総数"]
for y in EPI:
    ax.plot([y, y], [np.polyval(k, y) / 100, flat.rate[y] / 100], color=ORANGE, lw=5, alpha=0.6)
    ax.annotate(f"{y}年\n+{a[y]['excess'] / 1e4:.1f}万人", (y, flat.rate[y] / 100), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=9)
ax.set_ylabel("死亡率（人口1,000人あたり）"); ax.set_xlabel("年"); ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_ylim(17, 30)
ax.axhline(base4 / 100, xmin=0.42, xmax=0.7, color=GREEN, lw=1.2, ls=":", label="すぐ前後の4年（1916・17・21・22年）の平均")
ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title(f"1918〜20年の死亡は、ふだんより約{out['near_years_baseline']['total_excess'] / 1e4:.0f}万〜{a['total_excess'] / 1e4:.0f}万人多かった（ふだんの取り方による）")
save(fig, "a338_death_rate.png", SRC + "。線は1910〜27年（1918〜20年と1923年を除く）")

# 図2：死因ごとの多かった分
fig, ax = plt.subplots(figsize=(8.6, 4.2))
cs = [c for c in out["by_cause"]]; lab = {"心疾患（高血圧性を除く）": "心疾患", "悪性新生物": "がん"}
x = np.arange(len(cs) + 1); bot = np.zeros(len(cs) + 1)
for y, col in zip(EPI, (BLUE, LIGHT, GREEN)):
    v = np.array([out["by_cause"][c][y]["excess"] for c in cs] + [a[y]["excess"] - sum(out["by_cause"][c][y]["excess"] for c in cs)]) / 1e4
    ax.bar(x, v, bottom=np.where(v >= 0, bot, 0), color=col, label=f"{y}年"); bot += np.where(v >= 0, v, 0)
tot = [out["by_cause"][c]["total_excess"] / 1e4 for c in cs] + [oth / 1e4]
for i, t in enumerate(tot): ax.text(i, max(bot[i], 0) + 0.6, f"{t:+.1f}万人", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([lab.get(c, c) for c in cs] + ["そのほか\n（インフルエンザと\n書かれた死亡を含む）"]); ax.set_ylabel("ふだんより多かった死亡（万人、3年の合計）"); ax.legend(frameon=False, fontsize=9); ax.axhline(0, color=INK, lw=0.6)
ax.set_title(f"多かった分の{out['pneumonia_share_pct']:.0f}%は肺炎と書かれた死亡。結核や老衰でも増えていた")
save(fig, "a338_by_cause.png", SRC + "。死因ごとに同じやり方で「ふだん」を作った。「そのほか」は総数との差（インフルエンザと書かれた死亡を含む）")

# 図3：1920年の月ごとの死亡（1日あたり）
fig, ax = plt.subplots(figsize=(8.6, 4.2))
m = np.arange(1, 13)
ax.plot(m, per[1915], "-o", color=GRAY, ms=3, label="1915年"); ax.plot(m, per[1925], "-o", color=LIGHT, ms=3, label="1925年"); ax.plot(m, per[1920], "-o", color=ORANGE, ms=5, lw=2, label="1920年")
for mm in (1, 2, 3): ax.annotate(f"{out['monthly_1920'][mm]['ratio_to_1915_25']:.2f}倍", (mm, per[1920][mm - 1]), xytext=(8, 4), textcoords="offset points", fontsize=9)
ax.set_xticks(m); ax.set_xticklabels([f"{i}月" for i in m]); ax.set_ylabel("1日あたりの死亡数（人）"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0)
ax.set_title("1920年は1月の死亡がふだんの1.8倍。山は1〜3月で、5月には1.1倍まで下がった")
save(fig, "a338_monthly_1920.png", SRC + "。倍率は1915年と1925年の平均との比。月別の表は5年おきで、1918・1919年の月別は載っていない")
print(out["near_years_baseline"], out["robust"])
