"""A439 3人目より後に生まれる子は、いつから少数になったのか
人口動態統計 上巻 4-12 出生順位別にみた年次別出生数及び百分率（1950〜2025年）。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：厚生労働省「人口動態統計」（2025年確定数 上巻 第4.12表）をもとに作成"
L = open(DATA / "jinkou_r7_jokan_4-12_birth_order.csv", encoding="utf-8").read().split("\n")
def block(name):
    i = next(k for k, l in enumerate(L) if l.replace(" ", "").startswith(name)); rows = []
    for l in L[i + 1:]:
        c = l.split(",")
        if not c[0][:4].isdigit(): break
        rows.append([int(c[0])] + [pd.to_numeric(x.strip(), errors="coerce") for x in c[1:8]])
    return pd.DataFrame(rows, columns=["year", "total", "b1", "b2", "b3", "b4", "b5p", "unknown"])
n, pub = block("出生数"), block("百分率")
known = n[["b1", "b2", "b3", "b4", "b5p"]].sum(axis=1)
s = pd.DataFrame({"year": n.year, "births": n.total, "first": n.b1 / known * 100, "second": n.b2 / known * 100, "third": n.b3 / known * 100,
                  "fourth_plus": (n.b4 + n.b5p) / known * 100, "third_plus": (n.b3 + n.b4 + n.b5p) / known * 100, "n_third_plus": n.b3 + n.b4 + n.b5p, "n_first": n.b1, "n_second": n.b2})
s.to_csv(RES / "a439_shares_by_year.csv", index=False)
chk = float(np.nanmax(np.abs(np.c_[s["first"] - pub.b1, s.second - pub.b2, s.third - pub.b3, n.b4 / known * 100 - pub.b4, n.b5p / known * 100 - pub.b5p])))
t = s.set_index("year")
def first_below(col, x):
    b = t[t[col] < x]; return int(b.index[0]) if len(b) else None
ann = t.loc[2000:]            # 2000年からは毎年
def dec(y0, y1):
    return {"births": int(t.births[y1] - t.births[y0]), "first": int(t.n_first[y1] - t.n_first[y0]), "second": int(t.n_second[y1] - t.n_second[y0]), "third_plus": int(t.n_third_plus[y1] - t.n_third_plus[y0])}
main = {"years": n.year.tolist(),
        "share": {str(y): {c: round(float(t.loc[y, c]), 1) for c in ["first", "second", "third", "fourth_plus", "third_plus"]} for y in (1950, 1955, 1960, 1965, 1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025)},
        "n_third_plus": {str(y): int(t.n_third_plus[y]) for y in (1950, 1960, 1975, 2000, 2025)}, "n_fourth_plus": {str(y): int(n.set_index("year").loc[y, ["b4", "b5p"]].sum()) for y in (1950, 1960, 1975, 2000, 2025)},
        "third_plus_first_below": {"40": first_below("third_plus", 40), "30": first_below("third_plus", 30), "25": first_below("third_plus", 25), "20": first_below("third_plus", 20), "15": first_below("third_plus", 15)},
        "third_plus_min": [int(t.third_plus.idxmin()), round(float(t.third_plus.min()), 1)], "third_plus_max_after_1965": [int(t.loc[1965:].third_plus.idxmax()), round(float(t.loc[1965:].third_plus.max()), 1)],
        "third_plus_min_since_2000": [int(ann.third_plus.idxmin()), round(float(ann.third_plus.min()), 1)], "third_plus_max_since_2000": [int(ann.third_plus.idxmax()), round(float(ann.third_plus.max()), 1)],
        "first_max": [int(t["first"].idxmax()), round(float(t["first"].max()), 1)], "first_min": [int(t["first"].idxmin()), round(float(t["first"].min()), 1)],
        "first_over_second_year": int(t[t["first"] > t.second].index[0]), "second_max": [int(t.second.idxmax()), round(float(t.second.max()), 1)],
        "fourth_plus_first_below_5": first_below("fourth_plus", 5), "decline_1950_1960": dec(1950, 1960), "decline_1950_2025": dec(1950, 2025), "decline_2000_2025": dec(2000, 2025),
        "pct_change_2000_2025": {c: round(float((t.loc[2025, c] / t.loc[2000, c] - 1) * 100), 1) for c in ["n_first", "n_second", "n_third_plus", "births"]},
        "max_abs_diff_vs_published_pct": chk, "unknown_max": int(n.unknown.max())}
json.dump(main, open(RES / "a439_main.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(main, ensure_ascii=False))

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.stackplot(s.year, s["first"], s.second, s.third, s.fourth_plus, colors=[BLUE, LIGHT, ORANGE, INK], labels=["第1子", "第2子", "第3子", "第4子以上"])
ax.set_xlim(1950, 2025); ax.set_ylim(0, 100); ax.set_ylabel("出生に占める割合（%）"); ax.legend(frameon=False, ncol=4, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.08))
ax.set_title("生まれた子の出生順位の内訳（1950〜2025年。2000年までは5年おき）"); save(fig, "a439_share_stack.png", SRC, y=-0.08)

fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(s.year, s.third_plus, color=ORANGE, lw=2, marker="o", ms=3, label="第3子以上"); ax.plot(s.year, s.fourth_plus, color=INK, lw=2, marker="o", ms=3, label="第4子以上"); ax.plot(s.year, s["first"], color=BLUE, lw=2, marker="o", ms=3, label="第1子")
ax.set_xlim(1950, 2025); ax.set_ylim(0, 55); ax.set_ylabel("出生に占める割合（%）"); ax.legend(frameon=False, ncol=3, fontsize=9)
ax.set_title(f"第3子以上は1950年の{main['share']['1950']['third_plus']}%から1960年に{main['share']['1960']['third_plus']}%、その後は14〜19%のあいだ"); save(fig, "a439_third_plus.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.4))
ax.bar(s.year.astype(str), s.n_first / 1e4, color=BLUE, label="第1子"); ax.bar(s.year.astype(str), s.n_second / 1e4, bottom=s.n_first / 1e4, color=LIGHT, label="第2子")
ax.bar(s.year.astype(str), s.n_third_plus / 1e4, bottom=(s.n_first + s.n_second) / 1e4, color=ORANGE, label="第3子以上")
ax.set_ylabel("出生数（万人）"); ax.legend(frameon=False, ncol=3, fontsize=9); ax.set_xticks(range(0, len(s), 2)); ax.tick_params(axis="x", labelsize=8, rotation=45)
ax.set_title("出生順位別の出生数（2000年までは5年おき、2001年からは毎年）"); save(fig, "a439_counts.png", SRC, y=-0.05)
