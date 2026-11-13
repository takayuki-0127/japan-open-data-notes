"""581 締め日が20日の会社で、月の売上を暦月で数えるか締め期間（前月21日〜当月20日）で数えるかで、
月ごとの数字と前年同月比はどれだけずれるのか。架空の取引（seed 581）"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT

SRC = "出典：架空の取引（作成者が乱数で作成、seed 581）"
rng = np.random.default_rng(581)

# ---- 1. 架空の取引を作る（2022-12-21〜2025-12-31） ----
days = pd.date_range("2022-12-21", "2025-12-31", freq="D")
dow = days.dayofweek.to_numpy()
base = np.where(dow < 5, 1.0, np.where(dow == 5, 0.25, 0.10))        # 平日中心（土日は少ない）
season = {1: 0.90, 2: 0.95, 3: 1.25, 4: 1.00, 5: 0.92, 6: 1.00, 7: 1.00, 8: 0.80, 9: 1.10, 10: 1.00, 11: 1.00, 12: 1.15}
seas = np.array([season[m] for m in days.month])
trend = 1.04 ** ((days - pd.Timestamp("2023-01-01")).days / 365.25)
# 暦月の月末3営業日に注文が集まる（月末の駆け込み）
dfd = pd.DataFrame({"d": days, "bd": dow < 5})
dfd["ym"] = dfd["d"].dt.to_period("M")
dfd["rank_from_end"] = dfd[dfd["bd"]].groupby("ym")["d"].rank(ascending=False)
monthend = np.where(dfd["rank_from_end"].fillna(99).to_numpy() <= 3, 1.6, 1.0)
# 年末年始・お盆は少ない
md = days.month * 100 + days.day
holiday = np.where((md >= 1229) | (md <= 103) | ((md >= 813) & (md <= 816)), 0.15, 1.0)
lam = 200 * base * seas * trend * monthend * holiday
n = rng.poisson(lam)
rows = []
tid = 0
for d, k in zip(days, n):
    amt = np.round(rng.lognormal(np.log(38000), 0.6, k), -1).astype(int)
    for a in amt:
        tid += 1
        rows.append((tid, d.date(), a))
tx = pd.DataFrame(rows, columns=["tx_id", "sold_on", "amount"])
tx["sold_on"] = pd.to_datetime(tx["sold_on"])
tx.to_csv(DATA / "transactions.csv", index=False, date_format="%Y-%m-%d")

# ---- 2. 暦月と締め期間で集計 ----
def closing_label(s):
    # 21日以降は翌月の締め期間に入る
    p = s.dt.to_period("M")
    return p.where(s.dt.day <= 20, p + 1)

tx["cal_m"] = tx["sold_on"].dt.to_period("M")
tx["close_m"] = closing_label(tx["sold_on"])
cal = tx.groupby("cal_m")["amount"].sum()
clo = tx.groupby("close_m")["amount"].sum()
months = pd.period_range("2023-01", "2025-12", freq="M")
m = pd.DataFrame({"cal": cal.reindex(months), "close": clo.reindex(months)})
m["diff_pct"] = (m["close"] / m["cal"] - 1) * 100
m["yoy_cal"] = (m["cal"] / m["cal"].shift(12) - 1) * 100
m["yoy_close"] = (m["close"] / m["close"].shift(12) - 1) * 100
m["yoy_gap"] = m["yoy_close"] - m["yoy_cal"]

# 期間の中の営業日数（平日）
def bdays(start, end):
    r = pd.date_range(start, end, freq="D")
    return int((r.dayofweek < 5).sum())
m["bd_cal"] = [bdays(p.start_time, p.end_time) for p in months]
m["bd_close"] = [bdays((p - 1).start_time + pd.Timedelta(days=20), p.start_time + pd.Timedelta(days=19)) for p in months]
m["days_close"] = [((p.start_time + pd.Timedelta(days=19)) - ((p - 1).start_time + pd.Timedelta(days=20))).days + 1 for p in months]
m["bd_yoy_close"] = m["bd_close"] - m["bd_close"].shift(12)
m["bd_yoy_cal"] = m["bd_cal"] - m["bd_cal"].shift(12)
m.index = m.index.astype(str)
m.to_csv(RES / "monthly_compare.csv", float_format="%.3f")

y = m.dropna(subset=["yoy_cal"])
flip = y[np.sign(y["yoy_cal"]) != np.sign(y["yoy_close"])]
# 営業日数の前年差で、締め期間の前年比のずれがどれだけ説明できるか
corr_close = float(np.corrcoef(y["bd_yoy_close"], y["yoy_close"])[0, 1])
corr_cal = float(np.corrcoef(y["bd_yoy_cal"], y["yoy_cal"])[0, 1])
# 年の合計：暦年と締め年（前年12/21〜当年12/20）
tx["cal_y"] = tx["sold_on"].dt.year
tx["close_y"] = tx["close_m"].dt.year
ann = pd.DataFrame({"cal": tx.groupby("cal_y")["amount"].sum(), "close": tx.groupby("close_y")["amount"].sum()}).loc[[2023, 2024, 2025]]
ann["diff_pct"] = (ann["close"] / ann["cal"] - 1) * 100
# 21日〜月末の売上の割合
tx["late"] = tx["sold_on"].dt.day >= 21
late_share = float(tx.loc[tx["cal_m"].isin(months)].groupby("late")["amount"].sum()[True] / tx.loc[tx["cal_m"].isin(months), "amount"].sum() * 100)

# ---- 3. SQL（DuckDB、1スレッド）で締め期間の集計を突き合わせ ----
con = duckdb.connect()
con.execute("SET threads=1")
con.execute(f"CREATE TABLE transactions AS SELECT * FROM read_csv_auto('{DATA / 'transactions.csv'}')")
q = (SQL / "02_closing_duckdb.sql").read_text()
sq = con.execute(q).df()
sq["close_m"] = sq["close_m"].astype(str).str[:7]
sq = sq.set_index("close_m")
chk = m[["close"]].join(sq, how="left")
sql_match = bool((chk["close"].astype("int64") == chk["sales"].astype("int64")).all())
sq.to_csv(RES / "sql_closing.csv")

res = {
    "n_tx": int(len(tx)), "n_tx_2023_2025": int(tx["cal_m"].isin(months).sum()),
    "late_share_pct": round(late_share, 2),
    "monthly_diff_pct": {"min": round(float(m["diff_pct"].min()), 2), "max": round(float(m["diff_pct"].max()), 2),
                          "abs_median": round(float(m["diff_pct"].abs().median()), 2),
                          "n_abs_over_5": int((m["diff_pct"].abs() > 5).sum()), "n_abs_over_10": int((m["diff_pct"].abs() > 10).sum()),
                          "argmin": m["diff_pct"].idxmin(), "argmax": m["diff_pct"].idxmax()},
    "yoy_gap_pt": {"abs_median": round(float(y["yoy_gap"].abs().median()), 2), "max_abs": round(float(y["yoy_gap"].abs().max()), 2),
                    "argmax": y["yoy_gap"].abs().idxmax(), "n_abs_over_5": int((y["yoy_gap"].abs() > 5).sum()), "n_months": int(len(y))},
    "yoy_sign_flips": {"n": int(len(flip)), "months": {k: [round(float(a), 2), round(float(b), 2)] for k, a, b in zip(flip.index, flip["yoy_cal"], flip["yoy_close"])}},
    "corr_bdays_vs_yoy": {"close": round(corr_close, 3), "cal": round(corr_cal, 3)},
    "annual": {str(k): {"cal": int(r.cal), "close": int(r.close), "diff_pct": round(float(r.diff_pct), 2)} for k, r in ann.iterrows()},
    "sql_match_python": sql_match,
}
json.dump(res, open(RES / "a581_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 4. 図 ----
x = np.arange(len(m))
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(x, m["diff_pct"], color=[ORANGE if v < 0 else BLUE for v in m["diff_pct"]])
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(x[::3]); ax.set_xticklabels(m.index[::3], rotation=45, ha="right")
ax.set_ylabel("締め期間 ÷ 暦月 − 1（%）")
ax.set_title("締め期間で数えた月の売上は、暦月より何%違うか（2023〜2025年）")
save(fig, "a581_monthly_diff.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
xx = np.arange(len(y))
ax.plot(xx, y["yoy_cal"], "o-", color=BLUE, label="暦月の前年同月比")
ax.plot(xx, y["yoy_close"], "s-", color=ORANGE, label="締め期間の前年同月比")
for i, k in enumerate(y.index):
    if k in flip.index:
        ax.axvspan(i - 0.4, i + 0.4, color=LIGHT, alpha=0.6, lw=0)
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(xx[::2]); ax.set_xticklabels(y.index[::2], rotation=45, ha="right")
ax.set_ylabel("前年同月比（%）"); ax.legend(frameon=False, loc="upper left")
ax.set_title("前年同月比は数え方で何ポイント違うか（網かけは増減の向きが逆の月）")
save(fig, "a581_yoy.png", SRC)

fig, axs = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
for a, col, bd, ttl, c in [(axs[0], "yoy_cal", "bd_yoy_cal", "暦月", BLUE), (axs[1], "yoy_close", "bd_yoy_close", "締め期間", ORANGE)]:
    jit = rng.uniform(-0.12, 0.12, len(y))
    a.scatter(y[bd] + jit, y[col], color=c, s=28)
    a.axhline(0, color=GRAY, lw=0.6); a.axvline(0, color=GRAY, lw=0.6)
    a.set_xlabel("営業日数の前年差（日）"); a.set_title(f"{ttl}（相関 {np.corrcoef(y[bd], y[col])[0, 1]:.2f}）")
axs[0].set_ylabel("前年同月比（%）")
fig.suptitle("前年同月比のぶれは、期間に入る営業日数の差でどこまで説明できるか", y=1.02)
save(fig, "a581_bdays.png", SRC)
