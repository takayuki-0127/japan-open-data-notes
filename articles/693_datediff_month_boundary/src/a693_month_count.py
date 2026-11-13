"""693 月数を「月の境目をまたいだ回数」で数えると、契約の経過月数は何件ずれるのか

架空の契約3万件（始まりは2023〜2025年の毎日、長さは1日〜3年、月末に始まる契約を多めに）。
経過月数を3通りで数える：
  境目の回数：年×12＋月の差（日は見ない。T-SQL の DATEDIFF(month) と同じ考え方）
  満了した月数：日が足りなければ1を引く。月末どうしは満了とみなす（DuckDB の date_sub('month') と同じ）
  日数÷30 の切り捨て
「6か月以上」「12か月以上」の区分の食い違い、始まりの日ごとの違いを数える。DuckDB の SQL と一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の契約（作成者が乱数で作成、seed 693）"
rng = np.random.default_rng(693)
DATA.mkdir(exist_ok=True)
N = 30000
days = pd.date_range("2023-01-01", "2025-12-31", freq="D")
w = np.where(days.is_month_end, 6.0, 1.0); w /= w.sum()            # 月末に始まる契約を多めに
start = pd.DatetimeIndex(rng.choice(days, N, p=w))
length = np.where(rng.uniform(size=N) < 0.5, rng.integers(1, 400, N), rng.integers(1, 1100, N))
end = start + pd.to_timedelta(length, unit="D")
C = pd.DataFrame({"contract_id": np.arange(1, N + 1), "start_date": start.date, "end_date": end.date})
C.to_csv(DATA / "contracts.csv", index=False)

s, e = pd.DatetimeIndex(start), pd.DatetimeIndex(end)
boundary = (e.year - s.year) * 12 + (e.month - s.month)
full = boundary - ((e.day < s.day) & ~e.is_month_end).astype(int)
days30 = (e - s).days // 30
C["months_boundary"], C["months_full"], C["months_days30"] = np.asarray(boundary), np.asarray(full), np.asarray(days30)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("cdf", C[["contract_id", "start_date", "end_date"]]); con.execute("CREATE TABLE contracts AS SELECT * FROM cdf")
dq = con.execute((SQL / "02_month_count_duckdb.sql").read_text(encoding="utf-8")).df()
for col in ["months_boundary", "months_full", "months_days30"]:
    assert (dq[col].values == C[col].values).all(), col

C["d_boundary"] = C.months_boundary - C.months_full; C["d_days30"] = C.months_days30 - C.months_full
C["start_day"] = s.day
by_day = C.groupby("start_day").agg(n=("contract_id", "size"), boundary_diff_pct=("d_boundary", lambda v: (v != 0).mean() * 100),
                                    days30_diff_pct=("d_days30", lambda v: (v != 0).mean() * 100)).reset_index()
by_day.round(2).to_csv(RES / "by_start_day.csv", index=False)
cut = {}
for k in [1, 6, 12]:
    t = C.months_full >= k
    cut[str(k)] = {"true": int(t.sum()), "boundary_wrong": int(((C.months_boundary >= k) != t).sum()), "days30_wrong": int(((C.months_days30 >= k) != t).sum())}
out = {"contracts": N, "boundary_ne_full": int((C.d_boundary != 0).sum()), "boundary_ne_full_pct": round(float((C.d_boundary != 0).mean() * 100), 1),
       "days30_ne_full": int((C.d_days30 != 0).sum()), "days30_ne_full_pct": round(float((C.d_days30 != 0).mean() * 100), 1),
       "days30_diff_counts": {str(k): int(v) for k, v in C.d_days30.value_counts().sort_index().items()},
       "cutoffs": cut, "month_end_start_boundary_diff_pct": round(float((C[s.is_month_end].d_boundary != 0).mean() * 100), 1),
       "day1_start_boundary_diff_pct": round(float((C[s.day == 1].d_boundary != 0).mean() * 100), 1),
       "example": {f"{a}→{b}": [int(v) for v in con.execute(f"SELECT datediff('month', DATE '{a}', DATE '{b}'), date_sub('month', DATE '{a}', DATE '{b}'), datediff('day', DATE '{a}', DATE '{b}') // 30").fetchone()]
                   for a, b in [("2025-01-31", "2025-02-01"), ("2025-01-15", "2025-07-14"), ("2025-01-31", "2025-02-28"), ("2024-01-01", "2024-12-31")]},
       "sql_matches_python": True}
json.dump(out, open(RES / "a693_main.json", "w"), ensure_ascii=False, indent=1)
C.drop(columns=["start_day"]).to_csv(RES / "month_counts.csv", index=False)

# 図1：始まりの日ごとの食い違い
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.bar(by_day.start_day, by_day.boundary_diff_pct, color=ORANGE, label="境目の回数（DATEDIFF 型）")
ax.plot(by_day.start_day, by_day.days30_diff_pct, color=BLUE, marker="o", ms=3, lw=1.5, label="日数÷30")
ax.set_xlabel("契約が始まった日（月の何日か）"); ax.set_ylabel("満了した月数と違う割合（%）")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("月の後半に始まった契約ほど、境目の回数は1か月多く数える")
save(fig, "a693_by_start_day.png", SRC)

# 図2：区分の食い違い
fig, ax = plt.subplots(figsize=(8.5, 3.6))
x = np.arange(3); wd = 0.38
b = [cut[k]["boundary_wrong"] for k in ["1", "6", "12"]]; d = [cut[k]["days30_wrong"] for k in ["1", "6", "12"]]
ax.bar(x - wd / 2, b, wd, color=ORANGE, label="境目の回数"); ax.bar(x + wd / 2, d, wd, color=BLUE, label="日数÷30")
for i in range(3):
    ax.text(i - wd / 2, b[i], f"{b[i]:,}", ha="center", va="bottom", fontsize=9); ax.text(i + wd / 2, d[i], f"{d[i]:,}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(["1か月以上か", "6か月以上か", "12か月以上か"]); ax.set_ylabel("区分を取り違えた契約（件）")
ax.legend(frameon=False, fontsize=9); ax.set_title(f"3万件のうち、区分の判定が満了した月数と食い違った件数")
save(fig, "a693_cutoffs.png", SRC)

# 図3：日数÷30 のずれ方（契約の長さ別）
C["len_m"] = pd.cut(C.months_full, [-1, 5, 11, 23, 40], labels=["0〜5か月", "6〜11か月", "12〜23か月", "24か月〜"])
tab = C.groupby("len_m", observed=True)["d_days30"].value_counts(normalize=True).unstack(fill_value=0) * 100
fig, ax = plt.subplots(figsize=(8.5, 3.6))
bottom = np.zeros(len(tab))
for k, c in zip(sorted(tab.columns), [GRAY, BLUE, ORANGE, INK]):
    ax.bar(tab.index.astype(str), tab[k], bottom=bottom, color=c, label=f"差 {k:+d}か月"); bottom += tab[k].values
ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.38))
ax.set_title("日数÷30 は、長い契約ほど満了した月数より多く数える（1年＝365日÷30＝12.2）")
save(fig, "a693_days30.png", SRC, y=-0.2)
print(json.dumps(out, ensure_ascii=False, indent=1))
