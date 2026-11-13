"""562 「直近30日」に今日を含めるか、時刻で切るか日付で切るかで、数字はどれだけ変わるのか

架空の店の時刻つき取引（2025年1〜12月）。毎朝9時に「直近30日」の件数と売上を出すとして、4つの定義を比べる：
  A 今日を含む30日（日付で切る。今日の分は9時までの途中）
  B 今日を含まない30日（昨日までの30日分）
  C 時刻で切る（今から720時間前まで）
  D 両端を含めて31日分になってしまう書き方（today - 30 から今日まで）
B を基準に、日ごとの差と、前日からの動き（振れ）を比べる。実行する時刻（0〜23時）を変えたときの差も見る。
Python と SQL（DuckDB、1スレッド）で値が一致することを確かめる。数字は置いた仮定で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の店の取引（作成者が乱数で作成、seed 562）"
rng = np.random.default_rng(562)
days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
# 曜日と季節で件数が変わる。時間帯は10〜21時が中心
dow = np.array([0.9, 0.85, 0.9, 0.95, 1.1, 1.35, 1.3])
hour_w = np.array([0.2, 0.1, 0.05, 0.05, 0.05, 0.1, 0.3, 0.6, 1.0, 1.5, 2.5, 3.5, 4.5, 4.0, 3.5, 3.5, 3.8, 4.2, 4.8, 5.0, 4.2, 3.0, 1.5, 0.6])
hour_w = hour_w / hour_w.sum()
rows = []
for d in days:
    lam = 300 * dow[d.dayofweek] * (1 + 0.15 * np.sin(2 * np.pi * (d.dayofyear - 80) / 365))
    if d.month == 12 and d.day >= 20:
        lam *= 1.4
    n = rng.poisson(lam)
    h = rng.choice(24, n, p=hour_w)
    sec = rng.integers(0, 3600, n)
    amt = np.round(np.exp(rng.normal(7.6, 0.7, n)) / 10) * 10
    for hh, ss, a in zip(h, sec, amt):
        rows.append((d + pd.Timedelta(hours=int(hh), seconds=int(ss)), int(a)))
tx = pd.DataFrame(rows, columns=["ts", "amount"]).sort_values("ts").reset_index(drop=True)
tx.insert(0, "tx_id", np.arange(1, len(tx) + 1))
tx.to_csv(DATA / "transactions.csv", index=False)

ts = tx.ts.values
dt = tx.ts.dt.normalize().values
amt = tx.amount.values
csum = np.r_[0, np.cumsum(amt)]


def window(now):
    """4つの定義の (件数, 金額)"""
    now = np.datetime64(now)
    today = now.astype("datetime64[D]")
    out = {}
    def rng_ts(lo, hi_incl):   # lo < ts <= hi
        i = np.searchsorted(ts, lo, side="right"); j = np.searchsorted(ts, hi_incl, side="right")
        return j - i, csum[j] - csum[i]
    def rng_date(d0, d1, cap):  # d0 <= date <= d1 かつ ts <= cap
        i = np.searchsorted(ts, d0.astype("datetime64[ns]"), side="left")
        j = np.searchsorted(ts, min((d1 + 1).astype("datetime64[ns]") - np.timedelta64(1, "ns"), cap), side="right")
        return j - i, csum[j] - csum[i]
    nowns = now.astype("datetime64[ns]")
    out["A"] = rng_date(today - 29, today, nowns)
    out["B"] = rng_date(today - 30, today - 1, nowns)
    out["C"] = rng_ts(nowns - np.timedelta64(30, "D"), nowns)
    out["D"] = rng_date(today - 30, today, nowns)
    return out


# 毎朝9時に出す（2月1日〜12月31日）
run_days = pd.date_range("2025-02-01", "2025-12-31", freq="D")
recs = []
for d in run_days:
    w = window(d + pd.Timedelta(hours=9))
    recs.append({"date": d.date(), **{f"{k}_n": v[0] for k, v in w.items()}, **{f"{k}_amt": int(v[1]) for k, v in w.items()}})
S = pd.DataFrame(recs)
for k in "ACD":
    S[f"{k}_diff_pct"] = 100 * (S[f"{k}_amt"] / S["B_amt"] - 1)
S.to_csv(RES / "daily_9am.csv", index=False)

summ = {}
for k in "ABCD":
    a = S[f"{k}_amt"]
    chg = 100 * a.pct_change().dropna()
    summ[k] = {"mean_amt": round(float(a.mean())), "mean_n": round(float(S[f"{k}_n"].mean()), 1),
               "mean_diff_vs_B_pct": None if k == "B" else round(float(S[f"{k}_diff_pct"].mean()), 2),
               "min_diff_vs_B_pct": None if k == "B" else round(float(S[f"{k}_diff_pct"].min()), 2),
               "max_diff_vs_B_pct": None if k == "B" else round(float(S[f"{k}_diff_pct"].max()), 2),
               "sd_daily_change_pct": round(float(chg.std()), 3), "max_abs_daily_change_pct": round(float(chg.abs().max()), 2)}

# 実行する時刻を0〜23時で変える（2025年3〜11月の毎日、B との差の平均）
hours = []
for hr in range(24):
    dd = {k: [] for k in "ACD"}
    for d in pd.date_range("2025-03-01", "2025-11-30", freq="D"):
        w = window(d + pd.Timedelta(hours=hr))
        for k in "ACD":
            dd[k].append(100 * (w[k][1] / w["B"][1] - 1))
    hours.append({"hour": hr, **{k: round(float(np.mean(v)), 3) for k, v in dd.items()}})
Hh = pd.DataFrame(hours)
Hh.to_csv(RES / "by_run_hour.csv", index=False)

# SQL（DuckDB）で同じ値を出して突き合わせ（12日分）
con = duckdb.connect()
con.execute("SET threads=1")
con.execute(f"CREATE TABLE transactions AS SELECT * FROM read_csv_auto('{DATA / 'transactions.csv'}')")
sql = (SQL / "02_last30_duckdb.sql").read_text()
checks = 0
for d in pd.date_range("2025-02-01", "2025-12-31", freq="28D"):
    for hr in (0, 9, 23):
        now = d + pd.Timedelta(hours=hr)
        v = con.execute(sql.replace(":now", now.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()
        w = window(now)
        py = (w["A"][0], w["A"][1], w["B"][0], w["B"][1], w["C"][0], w["C"][1], w["D"][0], w["D"][1])
        assert tuple(int(x) for x in v) == tuple(int(x) for x in py), (now, v, py)
        checks += 1

summary = {"transactions": len(tx), "days": len(days), "run_days_9am": len(S), "by_definition_9am": summ,
           "by_run_hour_A": {int(r.hour): r.A for r in Hh.itertuples()}, "by_run_hour_C": {int(r.hour): r.C for r in Hh.itertuples()},
           "sql_python_checks": checks}
json.dump(summary, open(RES / "a562_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

LAB = {"A": "A 今日を含む（日付）", "B": "B 昨日まで（日付）", "C": "C 720時間（時刻）", "D": "D 31日分になる書き方"}
COL = {"A": ORANGE, "B": INK, "C": BLUE, "D": GREEN}

# 図1：毎朝9時の値（9〜10月の一部）
fig, ax = plt.subplots(figsize=(8.5, 4.2))
q = S[(pd.to_datetime(S.date) >= "2025-09-01") & (pd.to_datetime(S.date) <= "2025-10-31")]
for k in "ABCD":
    ax.plot(pd.to_datetime(q.date), q[f"{k}_amt"] / 1e6, color=COL[k], lw=1.6 if k == "B" else 1.3, label=LAB[k])
ax.set_ylabel("直近30日の売上（百万円）")
ax.set_title("毎朝9時に出した「直近30日の売上」（2025年9〜10月）", loc="left")
ax.legend(frameon=False, fontsize=9, ncol=2)
fig.autofmt_xdate()
save(fig, "a562_series.png", SRC)

# 図2：B との差の分布と、前日からの動きの振れ
fig, axs = plt.subplots(1, 2, figsize=(9.5, 4))
data = [S[f"{k}_diff_pct"] for k in "ACD"]
bp = axs[0].boxplot(data, vert=True, patch_artist=True, widths=0.5)
for patch, k in zip(bp["boxes"], "ACD"):
    patch.set_facecolor(COL[k]); patch.set_alpha(0.6)
axs[0].set_xticks([1, 2, 3], ["A 今日を含む", "C 720時間", "D 31日分"])
axs[0].axhline(0, color=INK, lw=0.8)
axs[0].set_ylabel("B（昨日まで）との売上の差（%）")
axs[0].set_title("B との差（毎朝9時、2〜12月）", loc="left", fontsize=11)
sd = [summ[k]["sd_daily_change_pct"] for k in "ABCD"]
axs[1].bar(range(4), sd, color=[COL[k] for k in "ABCD"], alpha=0.8)
for i, v in enumerate(sd):
    axs[1].text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
axs[1].set_xticks(range(4), ["A", "B", "C", "D"])
axs[1].set_ylabel("前日からの変化率の標準偏差（%）")
axs[1].set_title("日ごとの振れ", loc="left", fontsize=11)
save(fig, "a562_diff.png", SRC)

# 図3：実行する時刻で差が変わる
fig, ax = plt.subplots(figsize=(8, 4))
for k in "ACD":
    ax.plot(Hh.hour, Hh[k], marker="o", ms=3.5, color=COL[k], label=LAB[k])
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(range(0, 24, 2))
ax.set_xlabel("「直近30日」を出す時刻（時）")
ax.set_ylabel("B（昨日まで）との売上の差の平均（%）")
ax.set_title("同じ定義でも、出す時刻で差が変わる（3〜11月の平均）", loc="left")
ax.legend(frameon=False, fontsize=9)
save(fig, "a562_hour.png", SRC)
