"""340：高校に進む人が9割を超えるまで、何年かかったのか。
学校基本調査 年次統計「進学率」（通信制課程への進学者を除く系列は1950年〜、含む系列は1984年〜）。
"""
import json
import numpy as np, pandas as pd, openpyxl
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：文部科学省「学校基本調査」年次統計 総括表4 進学率（昭和23年〜）をもとに作成者が加工して作成"
ws = openpyxl.load_workbook(DATA / "raw" / "gakkou_kihon_shingakuritsu.xlsx", data_only=True).worksheets[0]
rec = []
for r in ws.iter_rows(values_only=True):
    if str(r[1]).strip().isdigit():
        f = lambda v: float(v) if isinstance(v, (int, float)) else np.nan
        rec.append((int(r[1]), f(r[4]), f(r[5]), f(r[6]), f(r[7]), f(r[8]), f(r[9])))
D = pd.DataFrame(rec, columns=["year", "all_t", "all_m", "all_f", "ex_t", "ex_m", "ex_f"]).set_index("year").round(1)
D.to_csv(DATA / "high_school_rate_1948_2025.csv")
E_ = D[D.ex_t.notna()]

def first_at(col, level):
    s = E_[col]; return int(s[s >= level].index[0])
out = {"first_year": {c: {str(l): first_at(c, l) for l in (50, 60, 70, 80, 90, 95)} for c in ("ex_t", "ex_m", "ex_f")}}
out["years_50_to_90"] = {c: out["first_year"][c]["90"] - out["first_year"][c]["50"] for c in ("ex_t", "ex_m", "ex_f")}
out["rate"] = {int(y): {c: float(E_.loc[y, c]) for c in ("ex_t", "ex_m", "ex_f")} for y in (1950, 1955, 1960, 1965, 1970, 1974, 1975, 1980, 1990, 2000, 2010, 2020, 2025)}
gap = (E_.ex_m - E_.ex_f).round(1)
out["gap_m_minus_f"] = {int(y): float(gap[y]) for y in (1950, 1955, 1960, 1965, 1968, 1969, 1970, 1975, 1980, 1990, 2000, 2010, 2020, 2025)}
out["female_first_higher"] = int(gap[gap < 0].index[0]); out["female_max_lead"] = [int(gap.idxmin()), float(-gap.min())]
out["male_higher_again"] = int(gap[(gap.index > 1990) & (gap > 0)].index[0]) if ((gap.index > 1990) & (gap > 0)).any() else None
dy = E_.ex_t.diff().round(1)
out["biggest_yearly_gain"] = [[int(y), float(v)] for y, v in dy.sort_values(ascending=False).head(5).items()]
# 10年ごとの上がり方
out["gain_by_decade"] = {f"{a}-{a + 10}": round(float(E_.ex_t[a + 10] - E_.ex_t[a]), 1) for a in (1950, 1960, 1970, 1980, 1990, 2000, 2010)}
out["gain_1960_1974"] = round(float(E_.ex_t[1974] - E_.ex_t[1960]), 1)
out["not_going_pct"] = {int(y): round(100 - float(E_.ex_t[y]), 1) for y in (1950, 1960, 1970, 1974, 1980, 2000)}
# 通信制を含む系列との差（1984年〜）
both = D[D.all_t.notna()]; diff = (both.all_t - both.ex_t).round(1)
out["correspondence_gap"] = {int(y): float(diff[y]) for y in (1984, 1990, 2000, 2010, 2015, 2020, 2025)}
out["ex_peak"] = [int(E_.ex_t.idxmax()), float(E_.ex_t.max())]; out["all_peak"] = [int(both.all_t.idxmax()), float(both.all_t.max())]
json.dump(out, open(RES / "a340_main.json", "w"), ensure_ascii=False, indent=1)

fig, ax = plt.subplots(figsize=(8.8, 4.4))
ax.plot(E_.index, E_.ex_t, color=BLUE, lw=2.2, label="通信制への進学を除く（1950年〜）"); ax.plot(both.index, both.all_t, color=GRAY, lw=1.5, ls="--", label="通信制への進学を含む（1984年〜）")
fy = out["first_year"]["ex_t"]
for l in (50, 90):
    y = fy[str(l)]; ax.plot([y], [E_.ex_t[y]], "o", color=ORANGE, ms=7); ax.annotate(f"{y}年 {E_.ex_t[y]:.1f}%", (y, E_.ex_t[y]), xytext=(8, -12), textcoords="offset points", fontsize=10)
ax.annotate(f"2025年 {E_.ex_t[2025]:.1f}%", (2025, E_.ex_t[2025]), xytext=(-4, -14), textcoords="offset points", ha="right", fontsize=9, color=BLUE)
ax.annotate(f"{both.all_t[2025]:.1f}%", (2025, both.all_t[2025]), xytext=(-4, 5), textcoords="offset points", ha="right", fontsize=9, color=GRAY)
ax.set_ylim(35, 102); ax.set_ylabel("高校などへの進学率（%）"); ax.set_xlabel("中学校を卒業した年"); ax.legend(frameon=False, fontsize=9, loc="lower right"); ax.grid(axis="y", color="#e6e6e3", lw=0.6)
ax.set_title(f"高校への進学率は{fy['50']}年に5割、{fy['90']}年に9割を超えた。かかったのは{fy['90'] - fy['50']}年")
save(fig, "a340_rate.png", SRC)

fig, ax = plt.subplots(figsize=(8.8, 4.2))
ax.plot(E_.index, E_.ex_m, color=BLUE, lw=2, label="男"); ax.plot(E_.index, E_.ex_f, color=ORANGE, lw=2, label="女")
y0 = out["female_first_higher"]; ax.axvline(y0, color=GRAY, lw=0.8, ls="--"); ax.annotate(f"{y0}年に女が上回る\n（男{E_.ex_m[y0]:.1f}%・女{E_.ex_f[y0]:.1f}%）", (y0, E_.ex_f[y0]), xytext=(10, -42), textcoords="offset points", fontsize=9)
ax.annotate(f"1950年\n男{E_.ex_m[1950]:.1f}%・女{E_.ex_f[1950]:.1f}%", (1950, E_.ex_f[1950]), xytext=(30, -14), textcoords="offset points", fontsize=9)
ax.set_xlim(1949, 1990); ax.set_ylim(30, 100); ax.set_ylabel("高校などへの進学率（%、通信制を除く）"); ax.legend(frameon=False); ax.grid(axis="y", color="#e6e6e3", lw=0.6)
ax.set_title("1950年に11ポイントあった男女の差は、1969年に入れ替わった")
save(fig, "a340_by_sex.png", SRC)

fig, ax = plt.subplots(figsize=(8.8, 4.2))
d = dy.loc[1951:1985]; ax.bar(d.index, d, color=[ORANGE if v >= 2.5 else LIGHT for v in d])
for y, v in out["biggest_yearly_gain"][:3]: ax.text(y, v + 0.1, f"{y}年\n+{v:.1f}", ha="center", fontsize=8.5)
ax.axhline(0, color=INK, lw=0.6); ax.set_ylim(-0.8, 5.5); ax.set_ylabel("前の年からの上がり方（ポイント）"); ax.set_xlabel("中学校を卒業した年")
ax.set_title(f"上がり方がいちばん大きかったのは1961年。1960〜74年の14年で{out['gain_1960_1974']:.0f}ポイント上がった")
save(fig, "a340_yearly_gain.png", SRC + "。橙は2.5ポイント以上の年")
