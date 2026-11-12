"""A440 女性の進学先は、短大から4年制大学へ、いつ入れ替わったのか
学校基本調査 年次統計 総括表4 進学率（過年度高卒者等を含む、1954〜2025年）。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：文部科学省「学校基本調査」年次統計（総括表4 進学率）をもとに作成"
g = pd.read_excel(DATA / "raw" / "gakkou_soukatsu4_shingakuritsu.xlsx", header=None)
rows = g[pd.to_numeric(g[1], errors="coerce").between(1948, 2030)]
d = pd.DataFrame({"year": rows[1].astype(int).values})
for name, i in (("both_all", 16), ("both_m", 17), ("both_f", 18), ("univ_all", 19), ("univ_m", 20), ("univ_f", 21), ("jc_all", 22), ("jc_m", 23), ("jc_f", 24)):
    d[name] = pd.to_numeric(rows[i], errors="coerce").round(1).values
d = d[d.univ_f.notna()].reset_index(drop=True); d["gap_univ"] = (d.univ_m - d.univ_f).round(1); d["gap_both"] = (d.both_m - d.both_f).round(1)
d.to_csv(DATA / "shingakuritsu_univ_jc_by_sex_1954_2025.csv", index=False); d.to_csv(RES / "a440_rates_by_year.csv", index=False)
t = d.set_index("year")
def first(cond):
    x = t[cond]; return int(x.index[0]) if len(x) else None
def stays(cond):
    c = cond.values; ys = t.index.tolist()
    for i in range(len(ys)):
        if c[i:].all(): return int(ys[i])
    return None
main = {"years": [int(t.index.min()), int(t.index.max())],
        "rates": {str(y): {c: float(t.loc[y, c]) for c in ["univ_f", "jc_f", "univ_m", "jc_m", "both_f", "both_m"]} for y in (1954, 1960, 1965, 1970, 1975, 1980, 1985, 1990, 1994, 1995, 1996, 2000, 2005, 2010, 2015, 2020, 2025)},
        "jc_f_over_univ_f_first": first(t.jc_f > t.univ_f),
        "univ_f_over_jc_f_final": stays(t.univ_f > t.jc_f), "years_jc_f_higher": [int(y) for y in t[t.jc_f > t.univ_f].index],
        "jc_f_max": [int(t.jc_f.idxmax()), float(t.jc_f.max())], "jc_f_min_after_peak": [int(t.loc[t.jc_f.idxmax():].jc_f.idxmin()), float(t.loc[t.jc_f.idxmax():].jc_f.min())],
        "univ_f_first_over": {str(x): first(t.univ_f >= x) for x in (10, 20, 30, 40, 50)}, "univ_m_first_over": {str(x): first(t.univ_m >= x) for x in (20, 30, 40, 50)},
        "gap_univ": {str(y): float(t.gap_univ[y]) for y in (1954, 1965, 1975, 1985, 1990, 1995, 2000, 2010, 2020, 2025)}, "gap_univ_max": [int(t.gap_univ.idxmax()), float(t.gap_univ.max())], "gap_univ_min": [int(t.gap_univ.idxmin()), float(t.gap_univ.min())],
        "both_f_over_both_m_years": [int(y) for y in t[t.both_f > t.both_m].index], "gap_both": {str(y): float(t.gap_both[y]) for y in (1954, 1975, 1989, 1995, 2000, 2010, 2025)},
        "change_1994_2025": {c: round(float(t.loc[2025, c] - t.loc[1994, c]), 1) for c in ["univ_f", "jc_f", "both_f", "univ_m", "both_m"]},
        "male_univ_dip": {"max_before_1990": [int(t.loc[:1990].univ_m.idxmax()), float(t.loc[:1990].univ_m.max())], "min_1976_1995": [int(t.loc[1976:1995].univ_m.idxmin()), float(t.loc[1976:1995].univ_m.min())]}}
json.dump(main, open(RES / "a440_main.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(main, ensure_ascii=False))

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(t.index, t.univ_f, color=ORANGE, lw=2.2, label="女性：大学（学部）"); ax.plot(t.index, t.jc_f, color=ORANGE, lw=2.2, ls="--", label="女性：短期大学（本科）")
y = main["univ_f_over_jc_f_final"]; ax.axvline(y, color=GRAY, lw=0.8, ls=":"); ax.text(y + 0.5, 3, f"{y}年から大学が上", fontsize=8.5, color=GRAY)
ax.set_xlim(1954, 2025); ax.set_ylim(0, 65); ax.set_ylabel("進学率（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title(f"女性の進学率：短大は{main['jc_f_max'][0]}年の{main['jc_f_max'][1]}%が山、大学は{y}年に短大を上回った"); save(fig, "a440_women_univ_jc.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(t.index, t.univ_m, color=BLUE, lw=2, label="男性：大学"); ax.plot(t.index, t.univ_f, color=ORANGE, lw=2, label="女性：大学")
ax.plot(t.index, t.both_m, color=BLUE, lw=1.3, ls="--", label="男性：大学＋短大"); ax.plot(t.index, t.both_f, color=ORANGE, lw=1.3, ls="--", label="女性：大学＋短大")
ax.set_xlim(1954, 2025); ax.set_ylim(0, 70); ax.set_ylabel("進学率（%）"); ax.legend(frameon=False, ncol=2, fontsize=9, loc="upper left")
ax.set_title("大学と短大を合わせると、女性は1989〜99年に男性を上回っていた" if main["both_f_over_both_m_years"] else "男女の進学率"); save(fig, "a440_men_women.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.0))
ax.bar(t.index, t.gap_univ, color=LIGHT); ax.set_xlim(1953.3, 2025.7); ax.set_ylabel("男性−女性（ポイント）")
ax.set_title(f"大学進学率の男女差：{main['gap_univ_max'][0]}年の{main['gap_univ_max'][1]}ポイントが最大、2025年は{main['gap_univ']['2025']}ポイント"); save(fig, "a440_gap.png", SRC)
