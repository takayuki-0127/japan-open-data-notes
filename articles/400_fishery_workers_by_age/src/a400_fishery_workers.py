"""400 漁業就業者の年齢（海面漁業、1973〜2023年）：2023年漁業センサス 総括編 累年統計
年齢5歳きざみがそろう1973年から。65歳以上の内訳は1993年から"""
import csv, json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save
SRC = "出典：農林水産省「2023年漁業センサス」総括編 累年統計（男女別・年齢階層別漁業就業者数）をもとに作成者が加工して作成"
r = list(csv.reader(open(DATA / "raw" / "gyogyo_census_2023_ruinen_age.csv", encoding="utf-8")))
YEARS = [1963, 1968, 1973, 1978, 1983, 1988, 1993, 1998, 2003, 2008, 2013, 2018, 2023]
AGE = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75+"]
num = lambda s: np.nan if s.strip() in ("…", "", "-") else float(s)
rec = []
for y, x in zip(YEARS, r[14:27]):
    v = [num(c) for c in x[2:31]]
    rec.append(dict(year=y, total=v[0], male=v[1], female=v[15], **{"m_" + a: v[2 + i] for i, a in enumerate(AGE)}, **{"f_" + a: v[16 + i] for i, a in enumerate(AGE)}))
d = pd.DataFrame(rec).set_index("year")
assert d.total[2023] == 121389 and d.total[1963] == 625935 and (d.male + d.female == d.total).all()
for a in AGE:
    d["t_" + a] = d["m_" + a] + d["f_" + a]
# 1973〜88年は「65〜69」の列に65歳以上が入っている
g = d.loc[1973:].copy()
g["t_65+"] = g[["t_65-69", "t_70-74", "t_75+"]].sum(axis=1, min_count=1); g["m_65+"] = g[["m_65-69", "m_70-74", "m_75+"]].sum(axis=1, min_count=1)
A12 = AGE[:10] + ["65+"]
assert ((g[["t_" + a for a in A12]].sum(axis=1) - g.total).abs() < 1).all()
g["p65"] = g["t_65+"] / g.total * 100; g["p_u40"] = g[["t_" + a for a in AGE[:5]]].sum(axis=1) / g.total * 100; g["p75"] = g["t_75+"] / g.total * 100
g["p_female"] = g.female / g.total * 100
mid = np.array([17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5])
g["mean_age_approx"] = [(np.dot(row[["t_" + a for a in AGE[:10]]].values.astype(float), mid) + (row["t_65+"] * 72.5 if np.isnan(row["t_75+"]) else row["t_65-69"] * 67.5 + row["t_70-74"] * 72.5 + row["t_75+"] * 80)) / row.total for _, row in g.iterrows()]
g.to_csv(DATA / "fishery_workers_by_age.csv")
# 同じ生まれ年を追う：ある回のa歳階級の人数に対して、5年後の(a+5)歳階級の人数が何倍か（やめた人と新しく入った人の差し引き）
rows = []
ys = list(g.index)
for y0, y1 in zip(ys[:-1], ys[1:]):
    for i in range(9):
        rows.append(dict(y0=y0, y1=y1, age0=AGE[i], age1=AGE[i + 1], n0=g.loc[y0, "t_" + AGE[i]], n1=g.loc[y1, "t_" + AGE[i + 1]]))
    # 60〜64 → 65〜69（1993年以降）、65〜69→70〜74、70〜74→75+は開いた階級なので除く
    if y1 >= 1993:
        rows.append(dict(y0=y0, y1=y1, age0="60-64", age1="65-69", n0=g.loc[y0, "t_60-64"], n1=g.loc[y1, "t_65-69"]))
    if y0 >= 1993:
        rows.append(dict(y0=y0, y1=y1, age0="65-69", age1="70-74", n0=g.loc[y0, "t_65-69"], n1=g.loc[y1, "t_70-74"]))
    # 60歳以上 → 65歳以上（全期間）
    rows.append(dict(y0=y0, y1=y1, age0="60+", age1="65+", n0=g.loc[y0, "t_60-64"] + g.loc[y0, "t_65+"], n1=g.loc[y1, "t_65+"]))
c = pd.DataFrame(rows); c["ratio"] = c.n1 / c.n0
c.to_csv(RES / "a400_cohort_ratio.csv", index=False)
pv = c.pivot(index="age0", columns="y1", values="ratio").reindex(AGE[:9] + ["60-64", "65-69", "60+"])
pv.round(3).to_csv(RES / "a400_cohort_ratio_wide.csv")
# 生まれ年ごとの人数の流れ（1953〜57年生まれなど）
coh = []
for b in range(1923, 2004, 5):  # 生まれ年の階級の始まり（その年の調査で 15-19歳になるのは b+15〜b+19 年生まれ…調査年−年齢で近似）
    for y in ys:
        a = y - b - 5  # 例：1973年に15〜19歳 → 1954〜58年生まれ → b=1953 とおく（調査年−20）
        i = (y - 20 - b) // 5
        if 0 <= i < 10 and (y - 20 - b) % 5 == 0:
            coh.append(dict(birth=f"{b+1}〜{b+5}年生まれ", year=y, age=AGE[i], n=g.loc[y, "t_" + AGE[i]]))
coh = pd.DataFrame(coh); coh.to_csv(RES / "a400_cohort_paths.csv", index=False)
res = {
    "total": {int(y): int(v) for y, v in d.total.items()}, "ratio_2023_1973": float(g.total[2023] / g.total[1973]), "ratio_2023_1963": float(d.total[2023] / d.total[1963]),
    "p65": g.p65.round(1).to_dict(), "p_u40": g.p_u40.round(1).to_dict(), "p75": g.p75.round(1).dropna().to_dict(), "p_female": g.p_female.round(1).to_dict(),
    "n65": g["t_65+"].astype(int).to_dict(), "n_u40": g[["t_" + a for a in AGE[:5]]].sum(axis=1).astype(int).to_dict(), "n75": g["t_75+"].dropna().astype(int).to_dict(),
    "n_15_24": g[["t_15-19", "t_20-24"]].sum(axis=1).astype(int).to_dict(),
    "mean_age_approx": g.mean_age_approx.round(1).to_dict(),
    "largest_age_group": {int(y): max(A12 if y < 1993 else AGE, key=lambda a: g.loc[y, "t_" + a]) for y in ys},
    "change_5y_pct": (g.total.pct_change() * 100).round(1).dropna().to_dict(),
    "cohort_ratio": {a: {int(k): round(float(v), 2) for k, v in pv.loc[a].dropna().items()} for a in pv.index},
    "cohort_ratio_mean_1998_2023": {a: round(float(pv.loc[a, [y for y in pv.columns if y >= 1998]].mean()), 2) for a in pv.index},
    "cohort_ratio_mean_1978_1993": {a: round(float(pv.loc[a, [y for y in pv.columns if y <= 1993]].mean()), 2) for a in pv.index if pv.loc[a, [y for y in pv.columns if y <= 1993]].notna().any()},
    "decline_2003_2023_by_age": {a: int(g.loc[2023, "t_" + a] - g.loc[2003, "t_" + a]) for a in AGE},
    "cohort_example": {b: {int(r_.year): int(r_.n) for r_ in coh[coh.birth == b].itertuples()} for b in ["1954〜1958年生まれ", "1974〜1978年生まれ", "1934〜1938年生まれ"] if (coh.birth == b).any()},
}
# もし2018→2023年の残る割合が続いたら（新しく15〜19歳で入る人は2023年と同じと置く。見通しではなく、足し算の確かめ）
last = pv[2023]
v = g.loc[2023, ["t_" + a for a in AGE]].values.astype(float); r75 = g.loc[2023, "t_75+"] / (g.loc[2018, "t_70-74"] + g.loc[2018, "t_75+"])
nxt = np.zeros(13); nxt[0] = v[0]
for i in range(9): nxt[i + 1] = v[i] * last[AGE[i]]
nxt[10] = v[9] * last["60-64"]; nxt[11] = v[10] * last["65-69"]; nxt[12] = (v[11] + v[12]) * r75
res["if_same_ratio_2028"] = {"total": int(nxt.sum()), "p65": round(float(nxt[10:].sum() / nxt.sum() * 100), 1), "ratio_75": round(float(r75), 2)}
json.dump(res, open(RES / "a400_main.json", "w"), ensure_ascii=False, indent=1)

fig, ax = plt.subplots(figsize=(9.5, 4.6))
u40 = g[["t_" + a for a in AGE[:5]]].sum(axis=1) / 1e4; m = g[["t_" + a for a in AGE[5:10]]].sum(axis=1) / 1e4; o = g["t_65+"] / 1e4
ax.bar(g.index, u40, 3.6, color=LIGHT, label="15〜39歳"); ax.bar(g.index, m, 3.6, bottom=u40, color=BLUE, label="40〜64歳"); ax.bar(g.index, o, 3.6, bottom=u40 + m, color=ORANGE, label="65歳以上")
for y in g.index:
    ax.text(y, g.total[y] / 1e4 + 0.6, f"{g.total[y]/1e4:.1f}", ha="center", fontsize=8.5)
ax2 = ax.twinx(); ax2.plot(g.index, g.p65, color=INK, marker="o", lw=1.3); ax2.set_ylabel("65歳以上の割合（%、黒い線）"); ax2.set_ylim(0, 50); ax2.spines["right"].set_visible(True)
ax.set_xticks(g.index); ax.set_ylabel("漁業就業者（万人）"); ax.set_title("海面漁業の就業者数と65歳以上の割合（1973〜2023年）"); ax.legend(frameon=False, loc="upper right")
save(fig, "a400_workers_and_65share.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.6))
xs = np.arange(13)
for y, cl in [(1993, GRAY), (2008, LIGHT), (2023, BLUE)]:
    ax.plot(xs, g.loc[y, ["t_" + a for a in AGE]].values / 1e3, color=cl, marker="o", label=f"{y}年")
ax.set_xticks(xs); ax.set_xticklabels([a.replace("-", "〜") + ("歳" if a != "75+" else "") for a in AGE], fontsize=8); ax.set_xticklabels([a.replace("-", "〜").replace("75+", "75歳以上") for a in AGE], fontsize=8)
ax.set_ylabel("漁業就業者（千人）"); ax.set_title("年齢ごとの就業者数：1993年・2008年・2023年"); ax.legend(frameon=False)
save(fig, "a400_age_profile.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.6))
show = ["15-19", "20-24", "30-34", "40-44", "50-54", "55-59", "60-64", "65-69"]; cm = plt.cm.viridis(np.linspace(0.05, 0.9, len(show)))
for a, cl in zip(show, cm):
    s = pv.loc[a].dropna(); nm = {"15-19": "15〜19→20〜24歳", "20-24": "20〜24→25〜29歳", "30-34": "30〜34→35〜39歳", "40-44": "40〜44→45〜49歳", "50-54": "50〜54→55〜59歳", "55-59": "55〜59→60〜64歳", "60-64": "60〜64→65〜69歳", "65-69": "65〜69→70〜74歳"}[a]
    ax.plot(s.index, s.values, marker="o", color=cl, label=nm)
ax.axhline(1, color=GRAY, lw=0.8, ls=":"); ax.set_yscale("log"); ax.set_yticks([0.5, 0.7, 1, 1.5, 2, 3, 4]); ax.set_yticklabels(["0.5", "0.7", "1", "1.5", "2", "3", "4"]); ax.yaxis.set_minor_formatter(plt.NullFormatter())
ax.set_xticks(pv.columns); ax.set_xlabel("5年後の調査の年"); ax.set_ylabel("5年後の人数÷もとの人数（倍、対数の目盛り）"); ax.set_title("同じ生まれ年の人数は、5年で何倍になったか"); ax.legend(frameon=False, fontsize=8, ncol=2)
save(fig, "a400_cohort_ratio.png", SRC)
print(json.dumps(res, ensure_ascii=False))
