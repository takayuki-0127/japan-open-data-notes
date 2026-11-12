"""396 自然災害による死者・行方不明者数（1945〜2025年）
令和8年版 防災白書 附属資料1・2 の文字（pdftotext -layout）から数字を取り出して数える"""
import re, json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, save
SRC = "出典：内閣府「令和8年版 防災白書」附属資料1・2 をもとに作成者が加工して作成"
T = (DATA / "raw" / "bousai_r8_appendix_p1_2.txt").read_text(encoding="utf-8").split("\n")

# ---- 附属資料2：年ごとの数（5つの列のかたまり） ----
i0 = next(k for k, l in enumerate(T) if re.search(r"昭和\s*20\s+6,062", l))
blocks = [[] for _ in range(5)]
for l in T[i0:i0 + 18]:
    l = re.sub(r"(（注）|出典|よる速報値|科年表|報，|降は|点速報).*$", "", l)
    l = l.replace("昭和", " ").replace("平成元", " 1 ").replace("令和元", " 1 ")
    nums = re.findall(r"[\d,]+", l)
    for b in range(len(nums) // 2):
        blocks[b].append(int(nums[2 * b + 1].replace(",", "")))
vals = [v for b in blocks for v in b]
assert len(vals) == 81, len(vals)
ann = pd.DataFrame({"year": range(1945, 2026), "deaths": vals})
assert ann.set_index("year").deaths[[1945, 1959, 1995, 2011, 2024, 2025]].tolist() == [6062, 5868, 6482, 22599, 783, 78]

# ---- 附属資料1：主な災害の一覧 ----
j0 = next(k for k, l in enumerate(T) if "三河地震" in l)
j1 = next(k for k, l in enumerate(T) if l.startswith("注１"))
era, yr, ev = 1925, None, []
for l in T[j0:j1]:
    if not l.strip():
        continue
    if l.startswith("平成"):
        era = 1988
    if l.startswith("令和"):
        era = 2018
    m = re.match(r"^(?:昭和|平成|令和)?\s{0,3}(\d+)\.", l)
    if m and (len(l) - len(l.lstrip()) <= 4 or l[0] in "昭平令"):
        yr = era + int(m.group(1))
    d = re.search(r"([\d,]+)\s*人\s*$", l)
    name = re.sub(r"^.*?(\d+\s*)(?=[^\d\s.～及び]{2})", "", l)
    name = re.split(r"\s{3,}", l.strip())
    nm = next((x for x in name if re.search(r"[台風雨震山雪害噴火津波]", x) and not re.match(r"^[\d.\s～及び昭和平成令]+$", x)), "")
    nm = re.sub(r"^[\d.\s～及び昭和平成令和]+", "", nm).strip()
    if not nm:
        continue
    kind = "地震・津波・噴火" if re.search(r"地震|震災|津波|噴火", nm) else ("雪害" if "雪" in nm else "風水害")
    ev.append({"year": yr, "name": nm, "kind": kind, "deaths": int(d.group(1).replace(",", "")) if d else 0})
ev = pd.DataFrame(ev)
assert ev.loc[ev.name.str.contains("伊勢湾"), ["year", "deaths"]].values.tolist() == [[1959, 5098]]
assert ev.loc[ev.name.str.contains("東日本大震災"), ["year", "deaths"]].values.tolist() == [[2011, 22336]]
assert ev.loc[ev.name.str.contains("能登"), "year"].iloc[0] == 2024 and ev.loc[ev.name.str.contains("阪神"), "year"].iloc[0] == 1995
ev.to_csv(DATA / "major_disasters.csv", index=False)

# 年ごとに、一覧にある地震・津波・噴火の分を引いた数（引きすぎないよう0で止める）
q = ev[ev.kind == "地震・津波・噴火"].groupby("year").deaths.sum()
ann["quake_listed"] = ann.year.map(q).fillna(0).astype(int)
ann["other"] = (ann.deaths - ann.quake_listed).clip(lower=0)
ann["wind_listed"] = ann.year.map(ev[ev.kind == "風水害"].groupby("year").deaths.sum()).fillna(0).astype(int)
ann.to_csv(DATA / "annual_deaths.csv", index=False)

per = [(1945, 1959), (1960, 1969), (1970, 1979), (1980, 1989), (1990, 1999), (2000, 2009), (2010, 2019), (2020, 2025)]
rows = []
for a, b in per:
    s = ann[(ann.year >= a) & (ann.year <= b)]
    rows.append({"period": f"{a}〜{b}", "years": len(s), "mean_all": s.deaths.mean(), "median_all": s.deaths.median(),
                 "mean_other": s.other.mean(), "median_other": s.other.median(), "max_other": s.other.max(),
                 "years_1000plus_other": int((s.other >= 1000).sum())})
dec = pd.DataFrame(rows)
dec.to_csv(RES / "a396_by_period.csv", index=False)

o = ann.set_index("year").other
last1000 = int(ann[ann.other >= 1000].year.max()); last500 = int(ann[ann.other >= 500].year.max())
big = ann.sort_values("deaths", ascending=False).head(5)
res = {
    "total_1945_2025": int(ann.deaths.sum()), "top5_years": big[["year", "deaths"]].values.tolist(),
    "top5_share": float(big.deaths.sum() / ann.deaths.sum()),
    "top3_quake_events_share": float(ev[ev.name.str.contains("東日本大震災|阪神|福井地震")].deaths.sum() / ann.deaths.sum()),
    "other_mean_1945_59": float(o.loc[1945:1959].mean()), "other_mean_1960_69": float(o.loc[1960:1969].mean()),
    "other_mean_1960_89": float(o.loc[1960:1989].mean()), "other_mean_1990_2025": float(o.loc[1990:2025].mean()),
    "ratio_60s_to_45_59": float(o.loc[1960:1969].mean() / o.loc[1945:1959].mean()),
    "other_median_1945_59": float(o.loc[1945:1959].median()), "other_median_1960_69": float(o.loc[1960:1969].median()),
    "last_year_other_1000plus": last1000, "last_year_other_500plus": last500,
    "years_other_1000plus_1945_59": int((o.loc[1945:1959] >= 1000).sum()), "years_other_1000plus_1960_2025": int((o.loc[1960:2025] >= 1000).sum()),
    "years_other_under100_by_period": {p: int((o.loc[a:b] < 100).sum()) for (a, b), p in zip(per, dec.period)},
    "other_excl_ise_mean_1945_59": float(o.loc[1945:1958].mean()),
    "wind_listed_share_1945_59": float(ann[(ann.year <= 1959)].wind_listed.sum() / o.loc[1945:1959].sum()),
    "five_year_mean_other": {int(y): float(o.loc[y:y + 4].mean()) for y in range(1945, 2025, 5)},
    "max_other_1960_2025": [int(o.loc[1960:2025].idxmax()), int(o.loc[1960:2025].max())],
    "deaths_2018": int(ann.set_index("year").deaths[2018]), "other_2018": int(o.loc[2018]),
    "n_events": len(ev), "n_quake_events": int((ev.kind == "地震・津波・噴火").sum()),
}
# 頑健性：1945年を除く（1945年は主な災害だけの数）、阪神・東日本・能登の年を丸ごと除く
res["other_mean_1946_59"] = float(o.loc[1946:1959].mean())
res["all_mean_excl_quake_years"] = {p: float(ann[(ann.year >= a) & (ann.year <= b) & (ann.quake_listed < 100)].deaths.mean()) for (a, b), p in zip(per, dec.period)}
json.dump(res, open(RES / "a396_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図 ----
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.bar(ann.year, ann.other, color=BLUE, width=0.85, label="それ以外（風水害・雪害など）")
ax.bar(ann.year, ann.deaths - ann.other, bottom=ann.other, color=ORANGE, width=0.85, label="一覧にある地震・津波・噴火の分")
ax.set_yscale("symlog", linthresh=1000); ax.set_yticks([0, 250, 500, 1000, 5000, 10000, 20000]); ax.set_yticklabels(["0", "250", "500", "1,000", "5,000", "10,000", "20,000"])
ax.set_ylabel("死者・行方不明者（人、1,000人より上は対数の目盛り）"); ax.set_title("自然災害による死者・行方不明者数（1945〜2025年）"); ax.legend(frameon=False, loc="upper right")
save(fig, "a396_annual.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.4))
x = np.arange(len(dec)); ax.bar(x - 0.2, dec.mean_other, 0.4, color=BLUE, label="平均"); ax.bar(x + 0.2, dec.median_other, 0.4, color=LIGHT, label="中央値")
for i, r in dec.iterrows():
    ax.text(i - 0.2, r.mean_other + 30, f"{r.mean_other:,.0f}", ha="center", fontsize=9); ax.text(i + 0.2, r.median_other + 30, f"{r.median_other:,.0f}", ha="center", fontsize=9, color=GRAY)
ax.set_xticks(x); ax.set_xticklabels(dec.period, fontsize=9); ax.set_ylabel("1年あたりの死者・行方不明者（人）")
ax.set_title("主な地震・津波・噴火を除いた数の、時期ごとの平均と中央値"); ax.legend(frameon=False)
save(fig, "a396_by_period.png", SRC)

fig, ax = plt.subplots(figsize=(10, 4.4))
ax.plot(ann.year, ann.other, color=BLUE, lw=1.2, marker="o", ms=3)
ax.set_yscale("log"); ax.set_yticks([20, 50, 100, 200, 500, 1000, 2000, 5000]); ax.set_yticklabels(["20", "50", "100", "200", "500", "1,000", "2,000", "5,000"])
for y in (1959, 1961):
    ax.axvline(y, color=GRAY, lw=0.8, ls=":")
ax.text(1959.3, 30, "1959年 伊勢湾台風\n1961年 災害対策基本法", fontsize=8.5, color=INK)
for nm, yy in [("洞爺丸台風", 1954), ("伊勢湾台風", 1959), ("昭和57年7・8月豪雨", 1982), ("平成30年7月豪雨", 2018)]:
    ax.annotate(nm, (yy, o.loc[yy]), textcoords="offset points", xytext=(4, 6), fontsize=8, color=GRAY)
ax.set_ylabel("人（対数の目盛り）"); ax.set_title("主な地震・津波・噴火を除いた死者・行方不明者数")
save(fig, "a396_other_log.png", SRC)
print(json.dumps(res, ensure_ascii=False)[:3000]); print(dec.round(0).to_string()); print(ev.kind.value_counts().to_dict()); print(ev.head(12).to_string())
