"""571 UTCで保存した時刻を日本時間に直さずに日付で集計すると、何件が前日に入るのか（架空の注文、seed 571）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT

rng = np.random.default_rng(571)
SRC = "架空の注文（作成者が乱数で作成、seed 571）"
# --- 架空の注文：2025年の1年分。日本時間の時刻の分布（夜に山、深夜も少しある）
days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
w_hour = np.array([3.0, 2.0, 1.2, .7, .5, .5, .8, 1.5, 2.5, 3.2, 3.8, 4.2, 5.0, 4.6, 4.0, 3.8, 4.0, 4.5, 5.2, 6.2, 7.0, 7.4, 6.6, 4.8])
w_hour = w_hour / w_hour.sum()
wd_mult = np.array([0.95, 0.92, 0.93, 0.95, 1.05, 1.12, 1.10])  # 月〜日
SALE = pd.Timestamp("2025-11-01")  # 0時開始のセール（11/1 0:00〜2:59 に注文が集中）
rows = []
for d in days:
    n = rng.poisson(160 * wd_mult[d.dayofweek])
    h = rng.choice(24, n, p=w_hour)
    if d == SALE:
        extra = rng.poisson(900); h = np.concatenate([h, rng.choice(3, extra, p=[.6, .3, .1])])
    sec = rng.integers(0, 3600, len(h))
    ts_jst = d + pd.to_timedelta(h, "h") + pd.to_timedelta(sec, "s")
    rows.append(pd.DataFrame({"ts_jst": ts_jst}))
o = pd.concat(rows, ignore_index=True).sort_values("ts_jst").reset_index(drop=True)
o["amount"] = np.round(rng.lognormal(np.log(4200), 0.6, len(o)), -1).astype(int)
o["ordered_at_utc"] = o["ts_jst"] - pd.Timedelta(hours=9)
o.insert(0, "order_id", np.arange(1, len(o) + 1))
o[["order_id", "ordered_at_utc", "amount"]].to_csv(DATA / "orders_utc.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

# --- 3通りの日付：正（UTC→JSTに直す）／UTCのまま／2回直す（すでにJSTの値にさらに+9時間）
o["d_ok"] = (o["ordered_at_utc"] + pd.Timedelta(hours=9)).dt.normalize()
o["d_utc"] = o["ordered_at_utc"].dt.normalize()
o["d_twice"] = (o["ordered_at_utc"] + pd.Timedelta(hours=18)).dt.normalize()
N = len(o); S = int(o.amount.sum())
prev = int((o.d_utc < o.d_ok).sum()); nxt = int((o.d_twice > o.d_ok).sum())
# 年の境目：2026年1月1日に入るはずの注文（データは2025年中のJSTのみ）／2024年12月31日に落ちる注文
to_2024 = int((o.d_utc < "2025-01-01").sum()); to_2026 = int((o.d_twice >= "2026-01-01").sum())

def daily(col):
    return o.groupby(col).agg(n=("order_id", "size"), amt=("amount", "sum"))
D = daily("d_ok").join(daily("d_utc"), rsuffix="_utc", how="outer").join(daily("d_twice"), rsuffix="_twice", how="outer").fillna(0)
D = D.loc["2025-01-01":"2025-12-31"]
D["pct_utc"] = (D.amt_utc / D.amt - 1) * 100; D["pct_twice"] = (D.amt_twice / D.amt - 1) * 100
D.to_csv(RES / "daily_compare.csv", float_format="%.3f")
absd = D.pct_utc.abs()
# 曜日別の合計（構成比）
def wd_share(col):
    s = o[o[col].between("2025-01-01", "2025-12-31")].groupby(o[col].dt.dayofweek)["amount"].sum()
    return s / s.sum() * 100
W = pd.DataFrame({"ok": wd_share("d_ok"), "utc": wd_share("d_utc"), "twice": wd_share("d_twice")})
W.index = list("月火水木金土日"); W.to_csv(RES / "weekday_share.csv", float_format="%.3f")
# 月別合計
def mon(col):
    return o[o[col].between("2025-01-01", "2025-12-31")].groupby(o[col].dt.month)["amount"].sum()
M = pd.DataFrame({"ok": mon("d_ok"), "utc": mon("d_utc"), "twice": mon("d_twice")})
M["pct_utc"] = (M.utc / M.ok - 1) * 100; M["pct_twice"] = (M.twice / M.ok - 1) * 100
M.to_csv(RES / "monthly_compare.csv", float_format="%.3f")
# 時間帯別：前日に入る注文の割合
hour = o.ts_jst.dt.hour
by_hour = o.groupby(hour).size()

# --- SQL（DuckDB、1スレッド）で正とUTCのままの日別件数を出し、Python と突き合わせる
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE orders AS SELECT * FROM read_csv_auto('{DATA/'orders_utc.csv'}', timestampformat='%Y-%m-%d %H:%M:%S')")
q = (SQL / "02_date_duckdb.sql").read_text()
sq = con.execute(q).df()
sq["d"] = pd.to_datetime(sq["d"])
ok = sq.set_index("d")
chk1 = bool((ok.loc["2025-01-01":"2025-12-31", "n_jst"].values == D["n"].values).all())
chk2 = bool((ok["n_utc"].reindex(D.index).fillna(0).values == D["n_utc"].values).all())
sq.to_csv(RES / "sql_daily.csv", index=False)

res = {"orders": N, "amount": S, "moved_to_prev_day": prev, "moved_share_pct": round(prev / N * 100, 2),
       "moved_amount_share_pct": round(o.loc[o.d_utc < o.d_ok, "amount"].sum() / S * 100, 2),
       "twice_moved_to_next_day": nxt, "twice_share_pct": round(nxt / N * 100, 2),
       "to_2024": to_2024, "to_2026": to_2026,
       "daily_abs_pct_median": round(float(absd.median()), 2), "daily_abs_pct_p90": round(float(absd.quantile(.9)), 2),
       "daily_abs_pct_max": round(float(absd.max()), 2), "daily_max_date": str(absd.idxmax().date()),
       "days_over_5pct": int((absd > 5).sum()), "days_over_10pct": int((absd > 10).sum()),
       "sale_day_ok": int(D.loc["2025-11-01", "amt"]), "sale_day_utc": int(D.loc["2025-11-01", "amt_utc"]),
       "oct31_ok": int(D.loc["2025-10-31", "amt"]), "oct31_utc": int(D.loc["2025-10-31", "amt_utc"]),
       "monthly_pct_utc_min": round(float(M.pct_utc.min()), 2), "monthly_pct_utc_max": round(float(M.pct_utc.max()), 2),
       "oct_pct_utc": round(float(M.loc[10, "pct_utc"]), 2), "nov_pct_utc": round(float(M.loc[11, "pct_utc"]), 2),
       "jan_pct_utc": round(float(M.loc[1, "pct_utc"]), 2),
       "weekday_share": W.round(2).to_dict(), "sql_match_jst": chk1, "sql_match_utc": chk2}
json.dump(res, open(RES / "a571_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))

# --- 図1：日本時間の時刻ごとの注文数（0〜8時台が前日に入る）
fig, ax = plt.subplots(figsize=(8, 4))
c = [ORANGE if h < 9 else LIGHT for h in range(24)]
ax.bar(range(24), by_hour.values / 1000, color=c)
ax.set_xticks(range(0, 24, 3)); ax.set_xlabel("注文した時刻（日本時間）"); ax.set_ylabel("注文数（千件、1年分）")
ax.set_title(f"0〜8時台の注文（全体の{prev/N*100:.1f}%）は、UTCのままだと前日の日付になる")
save(fig, "a571_by_hour.png", "出典：" + SRC + "。橙：UTCの日付が日本時間より1日前になる時間帯")
# --- 図2：10/25〜11/7 の日別売上（正 vs UTCのまま）
p = D.loc["2025-10-25":"2025-11-07"]
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(p)); ax.bar(x - .2, p.amt / 1e6, .4, color=INK, label="正しい日付（日本時間）"); ax.bar(x + .2, p.amt_utc / 1e6, .4, color=ORANGE, label="UTCのまま")
ax.set_xticks(x); ax.set_xticklabels([f"{d.month}/{d.day}" for d in p.index], fontsize=9); ax.set_ylabel("売上（百万円）"); ax.legend(frameon=False)
ax.set_title("11/1 0時開始のセールの売上が、ほぼまるごと10/31に入る")
save(fig, "a571_sale_days.png", "出典：" + SRC)
# --- 図3：日別の売上のずれ（UTCのまま）の分布
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(D.pct_utc.clip(-40, 60), bins=50, color=BLUE)
ax.axvline(0, color=INK, lw=.8)
ax.set_xlabel("日別の売上のずれ（UTCのまま ÷ 正しい日付 − 1、%）"); ax.set_ylabel("日数")
ax.set_title(f"日別売上のずれ：中央値 {absd.median():.1f}%、10%を超える日が{int((absd>10).sum())}日")
save(fig, "a571_daily_dist.png", "出典：" + SRC + "。±40%を超える日は端にまとめた")
