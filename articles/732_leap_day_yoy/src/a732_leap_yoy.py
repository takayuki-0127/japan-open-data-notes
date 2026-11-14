"""732 うるう年の2月29日を含む月の前年同月比は、日数をそろえないとどれだけ高く見えるのか

架空の店の日次売上（2023-01-01〜2025-12-31）。
  本当の伸び：毎日、前年の同じ時期より +2.0%（なめらかに伸びる）
  曜日の波：月 −10%・火 −12%・水 −8%・木 −6%・金 +6%・土 +18%・日 +12%
  日ごとのノイズ：標準偏差3%
月ごとの前年同月比を4通りで出す：
  そのまま（月の合計どうし）／日あたり（月の合計÷日数）／2月29日を除く／曜日をそろえる（曜日ごとの1日平均を出し、7曜日の平均で比べる）
2024年2月（29日）と2025年2月（28日）、年の合計（2024年は366日）も比べる。DuckDB の SQL と Python が一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の店の日次売上（作成者が乱数で作成、seed 732）"
rng = np.random.default_rng(732)
DATA.mkdir(exist_ok=True)
dates = pd.date_range("2023-01-01", "2025-12-31", freq="D")
WEEK = np.array([-0.10, -0.12, -0.08, -0.06, 0.06, 0.18, 0.12])
yrs = (dates - pd.Timestamp("2023-01-01")).days / 365.25
level = 80 * 1.02 ** yrs
sales = np.round(level * (1 + WEEK[dates.dayofweek]) * (1 + rng.normal(0, 0.03, len(dates))), 1)
D = pd.DataFrame({"sales_date": dates.date, "sales": sales})
D.to_csv(DATA / "daily_sales.csv", index=False)
D["y"] = dates.year; D["mo"] = dates.month; D["dow"] = dates.dayofweek; D["is29"] = (dates.month == 2) & (dates.day == 29)

g = D.groupby(["y", "mo"])
Mn = pd.DataFrame({"total": g.sales.sum(), "days": g.size(), "total_ex29": D.assign(s=np.where(D.is29, 0, D.sales)).groupby(["y", "mo"]).s.sum(),
                   "dow_mean": D.groupby(["y", "mo", "dow"]).sales.mean().groupby(level=[0, 1]).mean()}).reset_index()
P = Mn.merge(Mn.assign(y=Mn.y + 1), on=["y", "mo"], suffixes=("", "_p"))
P["yoy_plain"] = P.total / P.total_p - 1
P["yoy_per_day"] = (P.total / P.days) / (P.total_p / P.days_p) - 1
P["yoy_ex29"] = P.total_ex29 / P.total_ex29_p - 1
P["yoy_weekday"] = P.dow_mean / P.dow_mean_p - 1

con = duckdb.connect(); con.execute("SET threads=1")
con.register("d0", D[["sales_date", "sales"]].assign(sales_date=pd.to_datetime(D.sales_date)))
con.execute("CREATE TABLE daily_sales AS SELECT * FROM d0")
dq = con.execute((SQL / "02_leap_yoy_duckdb.sql").read_text(encoding="utf-8")).df()
mm = P.merge(dq, on=["y", "mo"], suffixes=("", "_sql"))
assert len(mm) == 24
for c in ["yoy_plain", "yoy_per_day", "yoy_ex29"]: assert np.allclose(mm[c], mm[c + "_sql"]), c
P.round(5).to_csv(RES / "monthly_yoy.csv", index=False)

feb = P[P.mo == 2].set_index("y")
Y = D.groupby("y").agg(total=("sales", "sum"), days=("sales", "size"))
yy = {str(y): {"days": int(Y.loc[y, "days"]), "yoy_plain_pct": round(float((Y.loc[y, "total"] / Y.loc[y - 1, "total"] - 1) * 100), 2),
               "yoy_per_day_pct": round(float(((Y.loc[y, "total"] / Y.loc[y, "days"]) / (Y.loc[y - 1, "total"] / Y.loc[y - 1, "days"]) - 1) * 100), 2)} for y in [2024, 2025]}
others = P[P.mo != 2]
out = {"true_growth_pct": 2.0, "noise_sd_pct": 3,
       "feb": {str(y): {m: round(float(feb.loc[y, "yoy_" + m] * 100), 2) for m in ["plain", "per_day", "ex29", "weekday"]} for y in [2024, 2025]},
       "feb2024_extra_day": "Thu", "annual": yy,
       "other_months_plain_mean_pct": round(float(others.yoy_plain.mean() * 100), 2),
       "other_months_plain_range_pct": [round(float(others.yoy_plain.min() * 100), 2), round(float(others.yoy_plain.max() * 100), 2)],
       "sql_matches_python": True}
json.dump(out, open(RES / "a732_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：月ごとの前年同月比（そのまま・日あたり）
fig, ax = plt.subplots(figsize=(10, 3.8)); lab = [f"{y % 100}/{m}" for y, m in zip(P.y, P.mo)]; x = np.arange(len(P))
ax.plot(x, P.yoy_plain * 100, marker="o", color=ORANGE, label="そのまま（月の合計どうし）")
ax.plot(x, P.yoy_per_day * 100, marker="o", color=BLUE, label="日あたり")
ax.axhline(2.0, color=INK, ls="--", lw=0.8, label="本当の伸び +2%")
for y in [2024, 2025]:
    i = int(np.where((P.y == y) & (P.mo == 2))[0][0]); ax.text(i, P.yoy_plain.iloc[i] * 100 + (0.6 if y == 2024 else -1.2), f"{P.yoy_plain.iloc[i] * 100:+.1f}%", color=ORANGE, ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8, rotation=90); ax.set_ylabel("前年同月比（%）"); ax.legend(frameon=False, fontsize=9, ncol=3, loc="lower left")
ax.set_ylim(-4, 8)
ax.set_title("2024年2月は高く、2025年2月は低く出る（横軸は 年/月）")
save(fig, "a732_monthly.png", SRC)

# 図2：2月の4通り
fig, ax = plt.subplots(figsize=(8.5, 3.8)); ms = ["plain", "per_day", "ex29", "weekday"]
nm = ["そのまま", "日あたり", "2月29日を除く", "曜日をそろえる"]; wd = 0.38; xx = np.arange(4)
for dx, y, col in [(-wd / 2, 2024, ORANGE), (wd / 2, 2025, BLUE)]:
    v = [out["feb"][str(y)][m] for m in ms]; ax.bar(xx + dx, v, wd, color=col, label=f"{y}年2月")
    for i, vv in enumerate(v): ax.text(xx[i] + dx, vv + (0.15 if vv >= 0 else -0.45), f"{vv:+.1f}", ha="center", fontsize=8.5)
ax.axhline(2.0, color=INK, ls="--", lw=0.8); ax.axhline(0, color=GRAY, lw=0.6)
ax.set_xticks(xx); ax.set_xticklabels(nm); ax.set_ylabel("2月の前年同月比（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("日数をそろえると、2月も本当の伸び +2% 近くに戻る")
save(fig, "a732_feb.png", SRC)

# 図3：年の合計
fig, ax = plt.subplots(figsize=(7, 3.6)); xx = np.arange(2)
a = [yy[str(y)]["yoy_plain_pct"] for y in [2024, 2025]]; b = [yy[str(y)]["yoy_per_day_pct"] for y in [2024, 2025]]
ax.bar(xx - 0.2, a, 0.4, color=ORANGE, label="そのまま（年の合計）"); ax.bar(xx + 0.2, b, 0.4, color=BLUE, label="日あたり")
for i in range(2):
    ax.text(xx[i] - 0.2, a[i] + 0.05, f"{a[i]:+.2f}", ha="center", fontsize=9); ax.text(xx[i] + 0.2, b[i] + 0.05, f"{b[i]:+.2f}", ha="center", fontsize=9)
ax.axhline(2.0, color=INK, ls="--", lw=0.8); ax.set_xticks(xx); ax.set_xticklabels(["2024年（366日）", "2025年（365日）"])
ax.set_ylabel("前年比（%）"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, 3.2)
ax.set_title("年の合計でも、1日分（約0.3ポイント）ずれる")
save(fig, "a732_annual.png", SRC)
print(json.dumps(out, ensure_ascii=False))
