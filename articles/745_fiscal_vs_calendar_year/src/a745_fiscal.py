"""745 4月始まりの年度と暦年で前年比を出すと、伸びの年はどれだけずれて見えるのか

架空の会員向けサービスの月次の売上。2019年1月〜2025年12月。
前年同月比の伸びは、2022年9月までは年3%、2022年10月から年12%に変わる（変わり目を置く）。季節の波（12月が多い）と小さなばらつきを入れる。
前年比を3通りで出す：暦年（1〜12月）、4月始まりの年度（4月〜翌3月）、12か月の移動合計（毎月）。
「前年比が8%を超えた」と最初に分かる時期と、変わり目の年の前年比を比べる。
DuckDB（1スレッド）の結果と pandas の結果の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の月次の売上（作成者が乱数で作成、seed 745）"
rng = np.random.default_rng(745)
ym = pd.date_range("2019-01-01", "2025-12-01", freq="MS")
CHANGE = pd.Timestamp("2022-10-01")
g_month = np.where(ym < CHANGE, 1.03 ** (1 / 12), 1.12 ** (1 / 12))
level = 1000 * np.cumprod(g_month) / g_month[0]
season = 1 + 0.15 * np.cos(2 * np.pi * (ym.month - 12) / 12)
sales = np.round(level * season * np.exp(rng.normal(0, .01, len(ym)))).astype(int)
D = pd.DataFrame({"ym": ym, "sales": sales})
DATA.mkdir(exist_ok=True); D.to_csv(DATA / "sales_monthly.csv", index=False, date_format="%Y-%m-%d")

cal = D.groupby(D.ym.dt.year).sales.sum(); cal_yoy = cal.pct_change()
fyk = np.where(D.ym.dt.month >= 4, D.ym.dt.year, D.ym.dt.year - 1)
fy_n = D.groupby(fyk).sales.size(); fy = D.groupby(fyk).sales.sum()[fy_n == 12]; fy_yoy = fy.pct_change()
roll = D.set_index("ym").sales.rolling(12).sum(); roll_yoy = roll.pct_change(12)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales_monthly", D)
for s in [x for x in ("\n".join(l for l in (SQL / "02_fy_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))).split(";") if x.strip()]:
    con.execute(s)
bc = con.execute("SELECT y, sales FROM by_cal ORDER BY y").df().set_index("y").sales
bf = con.execute("SELECT fy, sales FROM by_fy WHERE months = 12 ORDER BY fy").df().set_index("fy").sales
br = con.execute("SELECT ym, sales_12m FROM rolling WHERE months = 12 ORDER BY ym").df()
assert (bc.to_numpy() == cal.to_numpy()).all() and (bf.to_numpy() == fy.to_numpy()).all()
assert (br.sales_12m.to_numpy() == roll.dropna().to_numpy()).all()

TH = .08
# 期間が終わってから分かる → 暦年は12月の数字が出たとき、年度は3月、移動合計は毎月
cal_first = int(cal_yoy[cal_yoy > TH].index.min()); fy_first = int(fy_yoy[fy_yoy > TH].index.min())
roll_first = roll_yoy[roll_yoy > TH].index.min()
known = {"calendar": pd.Timestamp(f"{cal_first}-12-01"), "fiscal": pd.Timestamp(f"{fy_first + 1}-03-01"), "rolling12": roll_first}
lag = {k: (v.year - CHANGE.year) * 12 + v.month - CHANGE.month for k, v in known.items()}
T = pd.DataFrame({"calendar_yoy": cal_yoy}).join(pd.DataFrame({"fiscal_yoy": fy_yoy}), how="outer")
T.to_csv(RES / "yearly_yoy.csv")
pd.DataFrame({"rolling12_yoy": roll_yoy.dropna()}).to_csv(RES / "rolling_yoy.csv")
out = {"change_month": "2022-10", "growth_before": 0.03, "growth_after": 0.12, "threshold": TH,
       "calendar_yoy": {int(k): round(float(v), 4) for k, v in cal_yoy.dropna().items()},
       "fiscal_yoy": {f"{int(k)}年度": round(float(v), 4) for k, v in fy_yoy.dropna().items()},
       "first_over_threshold": {"calendar": f"{cal_first}年", "fiscal": f"{fy_first}年度", "rolling12": roll_first.strftime("%Y-%m")},
       "known_month": {k: v.strftime("%Y-%m") for k, v in known.items()},
       "months_after_change": lag}
json.dump(out, open(RES / "a745_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：月次の売上と区切り
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(D.ym, D.sales, color=BLUE)
ax.axvline(CHANGE, color=ORANGE, ls="--"); ax.text(CHANGE, D.sales.max() * .98, " 伸びが年3%→12%", color=ORANGE, fontsize=9, va="top")
for y in range(2019, 2026):
    ax.axvline(pd.Timestamp(f"{y}-04-01"), color=LIGHT, lw=.8)
ax.set_ylabel("月の売上（架空の単位）"); ax.set_title("月次の売上（薄い線は年度の始まりの4月）")
save(fig, "a745_monthly.png", SRC)

# 図2：暦年と年度の前年比
fig, ax = plt.subplots(figsize=(9, 4.6))
cy = cal_yoy.dropna(); fyy = fy_yoy.dropna()
ax.plot(pd.to_datetime([f"{y}-07-01" for y in cy.index]), cy * 100, "o-", color=BLUE, label="暦年（1〜12月）")
ax.plot(pd.to_datetime([f"{y + 1}-01-01" for y in fyy.index]), fyy * 100, "s-", color=ORANGE, label="年度（4月〜翌3月）")
for x, v in zip(pd.to_datetime([f"{y}-07-01" for y in cy.index]), cy):
    ax.text(x, v * 100 + .5, f"{v * 100:.1f}", ha="center", fontsize=8, color=BLUE)
for x, v in zip(pd.to_datetime([f"{y + 1}-01-01" for y in fyy.index]), fyy):
    ax.text(x, v * 100 - 1.1, f"{v * 100:.1f}", ha="center", fontsize=8, color=ORANGE)
ax.axvline(CHANGE, color=GRAY, ls="--", lw=1)
ax.set_ylabel("前年比（%）"); ax.legend(frameon=False, loc="upper left")
ax.set_title("同じ月次の数字でも、区切りが違うと変わり目の年の伸びが違う（点は期間の真ん中）")
save(fig, "a745_yearly.png", SRC)

# 図3：分かる時期
fig, ax = plt.subplots(figsize=(9, 4.4))
ry = roll_yoy.dropna()
ax.plot(ry.index, ry * 100, color=GREEN, label="12か月の移動合計（毎月）")
ax.axhline(TH * 100, color=GRAY, ls=":", lw=1); ax.axvline(CHANGE, color=GRAY, ls="--", lw=1)
for (k, l, c), yy in zip([("rolling12", "移動合計", GREEN), ("calendar", "暦年", BLUE), ("fiscal", "年度", ORANGE)], [5.6, 4.6, 3.6]):
    ax.axvline(known[k], color=c, lw=2, alpha=.7)
    ax.text(known[k] + pd.Timedelta(days=12), yy, f"{l}：{known[k].strftime('%Y年%-m月')}（{lag[k]}か月後）", color=c, fontsize=9, va="center")
ax.set_ylabel("前年比（%）"); ax.legend(frameon=False, loc="upper left")
ax.set_title(f"前年比が{TH * 100:.0f}%を超えたと数字で分かる時期（変わり目から）")
save(fig, "a745_known.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
