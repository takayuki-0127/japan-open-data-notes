"""412 月末に始まった契約の「1か月後」は、いつになるのか。応当日の決め方で、何件の日付がずれるか
架空の契約5万件（始期が散る場合と、月末に集まる場合）。乱数の種は412。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(412)
N = 50_000
K = 12                                             # 12回分の月ごとの応当日（1か月後〜12か月後）
D0 = pd.Timestamp("2025-01-01")


def starts(kind):
    d = D0 + pd.to_timedelta(rng.integers(0, 365, N), unit="D")
    if kind == "月末に集まる":
        u = rng.random(N)
        eom = d + pd.offsets.MonthEnd(0)
        som = d.to_period("M").to_timestamp()
        d = pd.DatetimeIndex(np.where(u < 0.40, eom, np.where(u < 0.60, som, d)))
    return pd.DatetimeIndex(d)


def m1(s, k):
    """始期に k か月を足す（DATEADD(month, k, 始期)）。その日がない月は月末に切り詰める"""
    return pd.DatetimeIndex([x + pd.DateOffset(months=k) for x in s])


def m2(s, k):
    """前の応当日に1か月ずつ足す（くり返し）。一度切り詰められた日は戻らない"""
    d = s
    for _ in range(k):
        d = pd.DatetimeIndex([x + pd.DateOffset(months=1) for x in d])
    return d


def m3(s, k):
    """月末合わせ：始期が月の最終日なら、いつも月の最終日（EOMONTH）。それ以外は m1 と同じ"""
    a = m1(s, k)
    last = s.is_month_end
    return pd.DatetimeIndex(np.where(last, a + pd.offsets.MonthEnd(0), a))


def m4(s, k):
    """日数で決める：30日ごと"""
    return s + pd.to_timedelta(30 * k, unit="D")


METH = {"①始期に k か月を足す": m1, "②前の応当日に1か月ずつ足す": m2, "③月末合わせ": m3, "④30日ごと": m4}

# 速くするため、始期の日付（365通り）ごとに応当日を出しておく
days = pd.date_range("2025-01-01", "2025-12-31")
TAB = {name: np.stack([f(days, k).values for k in range(1, K + 1)], axis=1) for name, f in METH.items()}   # [365, 12]
base = TAB["①始期に k か月を足す"]
rows, counts = [], {}
data = {}
for kind in ("散らばる", "月末に集まる"):
    s = starts(kind); idx = (s - D0).days.values
    data[kind] = s
    for name in METH:
        diff = (TAB[name][idx] - base[idx]).astype("timedelta64[D]").astype(int)        # [N, 12]
        rows.append({"始期": kind, "決め方": name,
                     "1回でも①と違う契約の割合%": round(100 * float((diff != 0).any(1).mean()), 2),
                     "12か月後が①と違う契約の割合%": round(100 * float((diff[:, -1] != 0).mean()), 2),
                     "12回の応当日のうち①と違う回の割合%": round(100 * float((diff != 0).mean()), 2),
                     "ずれの最大（日）": int(np.abs(diff).max()), "12か月後のずれの平均（日）": round(float(diff[:, -1].mean()), 2)})
        d_all = pd.DatetimeIndex(TAB[name][idx].ravel())
        counts[(kind, name)] = d_all
T = pd.DataFrame(rows); T.to_csv(RES / "shifted_share.csv", index=False)
pd.DataFrame({"契約ID": np.arange(1, N + 1), "始期_散らばる": data["散らばる"].date, "始期_月末に集まる": data["月末に集まる"].date}).to_csv(DATA / "contracts.csv", index=False)

# 始期 1/29・1/30・1/31（2025年、うるう年でない）と 2024年（うるう年）の、応当日の道のり
ex = []
for y in (2025, 2024):
    for d in (28, 29, 30, 31):
        s = pd.DatetimeIndex([pd.Timestamp(y, 1, d)])
        for name, f in METH.items():
            path = [f(s, k)[0] for k in range(1, K + 1)]
            ex.append({"始期": f"{y}-01-{d}", "決め方": name, **{f"{k}か月後": str(p.date())[5:] for k, p in zip(range(1, K + 1), path)},
                       "12か月後": str(path[-1].date())})
EX = pd.DataFrame(ex); EX.to_csv(RES / "january_start_paths.csv", index=False)

# 月の何日に請求が立つか（月末に集まる始期、12回分）
dom = {}
for name in METH:
    d_all = counts[("月末に集まる", name)]
    dom[name] = pd.Series(d_all.day).value_counts().reindex(range(1, 32), fill_value=0)
DOM = pd.DataFrame(dom); DOM.index.name = "日"; DOM.to_csv(RES / "billing_day_of_month.csv")
# 月の最終日に立つ請求の件数、暦の月ごとの請求件数（2025-02〜2026-12）
eom_n = {name: int(counts[("月末に集まる", name)].is_month_end.sum()) for name in METH}
permonth = pd.DataFrame({name: pd.Series(counts[("月末に集まる", name)].to_period("M")).value_counts().sort_index() for name in METH}).fillna(0).astype(int)
permonth.index = permonth.index.astype(str); permonth.index.name = "月"; permonth.to_csv(RES / "billings_per_calendar_month.csv")
# ---------------- SQL（DuckDB）で①②③を出して、Python と比べる ----------------
db = duckdb.connect(); db.execute("SET threads=1")
db.register("c", pd.DataFrame({"id": np.arange(N), "s": data["月末に集まる"]}))
q = db.execute("""
WITH RECURSIVE ks AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM ks WHERE n < 12),
chain AS (                                          -- ②：前の応当日に1か月ずつ足す
  SELECT id, 1 AS n, s + INTERVAL 1 MONTH AS d FROM c
  UNION ALL
  SELECT id, n + 1, d + INTERVAL 1 MONTH FROM chain WHERE n < 12)
SELECT c.id, ks.n,
       c.s + to_months(CAST(ks.n AS INTEGER))                                      AS m1,   -- ①
       ch.d                                                                        AS m2,   -- ②
       CASE WHEN CAST(c.s AS DATE) = last_day(c.s)
            THEN CAST(last_day(c.s + to_months(CAST(ks.n AS INTEGER))) AS TIMESTAMP)
            ELSE c.s + to_months(CAST(ks.n AS INTEGER)) END                        AS m3    -- ③
FROM c CROSS JOIN ks JOIN chain ch ON ch.id = c.id AND ch.n = ks.n
ORDER BY c.id, ks.n""").df()
sql_ok = {}
for col, name in (("m1", "①始期に k か月を足す"), ("m2", "②前の応当日に1か月ずつ足す"), ("m3", "③月末合わせ")):
    sql_ok[name] = bool((pd.to_datetime(q[col]).values.reshape(N, K) == TAB[name][idx]).all())
assert all(sql_ok.values()), sql_ok
pd.DataFrame([sql_ok]).to_csv(RES / "sql_check_duckdb.csv", index=False)

main = {"契約の数": N, "始期の年": 2025, "月の最終日が始期の割合%": {k: round(100 * float(v.is_month_end.mean()), 1) for k, v in data.items()},
        "29〜31日が始期の割合%": {k: round(100 * float((v.day >= 29).mean()), 1) for k, v in data.items()},
        "決め方ごとのずれ": T.to_dict("records"), "月の最終日に立つ請求の件数（月末に集まる始期、60万件のうち）": eom_n,
        "1/31始期の12か月後": {r["決め方"]: r["12か月後"] for r in ex if r["始期"] == "2025-01-31"},
        "SQLとPythonの一致": sql_ok}
json.dump(main, open(RES / "a412_main.json", "w"), ensure_ascii=False, indent=1)

# ---------------- 図 ----------------
SRC = "架空の契約5万件（作成者が乱数で作成、seed 412）"
fig, ax = plt.subplots(figsize=(9.5, 4.2))
names = [n for n in METH if n != "①始期に k か月を足す"]; x = np.arange(len(names)); w = 0.38
for i, (kind, c) in enumerate((("散らばる", GRAY), ("月末に集まる", BLUE))):
    v = [T[(T["始期"] == kind) & (T["決め方"] == n)]["1回でも①と違う契約の割合%"].iloc[0] for n in names]
    b = ax.bar(x + (i - 0.5) * w, v, w, color=c, label=f"始期が{kind}")
    for r, y in zip(b, v): ax.text(r.get_x() + r.get_width() / 2, y, f"{y:.1f}%", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(names); ax.set_ylabel("%"); ax.legend(frameon=False)
ax.set_title("12回の応当日のうち、1回でも①と日付が違う契約の割合")
save(fig, "a412_shifted_share.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.2))
s = pd.DatetimeIndex([pd.Timestamp(2025, 1, 31)])
for (name, f), c, ls in zip(METH.items(), (BLUE, ORANGE, GREEN, GRAY), ("-", "--", ":", "-.")):
    ax.plot(range(1, K + 1), [f(s, k)[0].day for k in range(1, K + 1)], ls, color=c, marker="o", ms=4, label=name)
ax.set_xticks(range(1, K + 1)); ax.set_xlabel("何か月後（④は何回目）"); ax.set_ylabel("応当日の「日」"); ax.set_ylim(0, 33)
ax.set_title("2025年1月31日に始まった契約の、応当日の「日」"); ax.legend(frameon=False, ncol=1, loc="center right", bbox_to_anchor=(1.0, 0.42))
save(fig, "a412_jan31_path.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.2))
xs = np.arange(1, 32); w = 0.4
ax.bar(xs - w / 2, DOM["①始期に k か月を足す"], w, color=BLUE, label="①始期に k か月を足す")
ax.bar(xs + w / 2, DOM["②前の応当日に1か月ずつ足す"], w, color=ORANGE, label="②前の応当日に1か月ずつ足す")
ax.set_xticks(xs); ax.set_xlabel("月の何日か"); ax.set_ylabel("12回分の請求の件数"); ax.legend(frameon=False, loc="upper center")
ax.set_title("始期が月末に集まる5万件：請求が立つ日（①と②）")
save(fig, "a412_billing_day.png", SRC)
print(json.dumps(main, ensure_ascii=False)); print(EX[EX["始期"].isin(["2025-01-31", "2025-01-29"])].to_string())
