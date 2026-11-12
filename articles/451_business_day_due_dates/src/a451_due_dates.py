"""451 「5営業日後」の期日は、祝日の持ち方で何件ずれるのか
架空の取引（受付日を乱数で作成、seed 451）と、内閣府の祝日の一覧で、休みの日の持ち方を変えて期日を比べる。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, LIGHT, save

SEED, N, K = 451, 60000, 5
START, END = "2019-01-01", "2025-12-31"
rng = np.random.default_rng(SEED)

# ---------- 祝日の一覧 ----------
hol = pd.read_csv(DATA / "syukujitsu_utf8.csv", header=0, names=["d", "name"])
hol["d"] = pd.to_datetime(hol["d"])
hol = hol[(hol.d >= "2018-01-01") & (hol.d <= "2026-12-31")].reset_index(drop=True)
hol["furikae"] = hol.name.str.startswith("休日")            # 振替休日・国民の休日・祝日扱いの休日
full = set(hol.d)                                            # ① 祝日と休日すべて
named = set(hol.d[~hol.furikae])                             # 名前のある祝日だけ（「休日」の行を落とす）


def nth_monday(y, m, n):
    d = pd.Timestamp(y, m, 1)
    return d + pd.Timedelta(days=(7 - d.dayofweek) % 7 + 7 * (n - 1))


def with_furikae(days):
    """祝日が日曜なら、その後の最初の「祝日でない日」を休みにする。祝日に挟まれた平日も休みにする。"""
    s = set(days)
    for d in sorted(days):
        if d.dayofweek == 6:
            x = d + pd.Timedelta(days=1)
            while x in s:
                x += pd.Timedelta(days=1)
            s.add(x)
    for d in sorted(days):
        x = d + pd.Timedelta(days=2)
        mid = d + pd.Timedelta(days=1)
        if x in days and mid not in s and mid.dayofweek != 6:
            s.add(mid)
    return s


# ② 法律が変わる前の決まりのままの一覧（2019年の即位に伴う休日なし、2020・2021年の祝日の移動なし）
old_named = set()
for d, nm in zip(hol.d, hol.name):
    if d.year == 2019 and nm.startswith("休日（祝日扱い）"):
        continue
    if d.year in (2020, 2021) and nm in ("海の日", "スポーツの日", "山の日"):
        continue
    if not nm.startswith("休日"):
        old_named.add(d)
for y in (2020, 2021):
    old_named |= {nth_monday(y, 7, 3), pd.Timestamp(y, 8, 11), nth_monday(y, 10, 2)}
old_rule = with_furikae(old_named)
# 2022年以降は実際の一覧と同じ
old_rule = {d for d in old_rule if d.year <= 2021} | {d for d in full if d.year >= 2022}

# ③ 一覧を1年更新し忘れる（2025年分がない）
stale = {d for d in full if d.year <= 2024}
# ④ 前の年の月日をそのまま写す（2025年分を2024年の月日で作る）
copied = {d for d in full if d.year <= 2024} | {pd.Timestamp(2025, d.month, d.day) for d in full if d.year == 2024 and not (d.month == 2 and d.day == 29)}

cal = pd.DataFrame({"d": pd.date_range("2018-12-01", "2026-03-31")})
cal["dow"] = cal.d.dt.dayofweek
cal["weekend"] = cal.dow >= 5
cal["nenmatsu"] = ((cal.d.dt.month == 12) & (cal.d.dt.day >= 29)) | ((cal.d.dt.month == 1) & (cal.d.dt.day <= 3))


def offdays(hset, nenmatsu=True, weekend=True):
    off = cal.d.isin(hset)
    if weekend:
        off |= cal.weekend
    if nenmatsu:
        off |= cal.nenmatsu
    return off.values


METHODS = {
    "truth":   ("正しい決まり（土日・祝日と休日・年末年始）", offdays(full)),
    "weekend": ("土日だけ除く", offdays(set(), nenmatsu=False)),
    "no_ny":   ("土日と祝日（年末年始を入れない）", offdays(full, nenmatsu=False)),
    "named":   ("振替休日・国民の休日を入れ忘れる", offdays(named)),
    "oldrule": ("法律が変わる前の一覧のまま", offdays(old_rule)),
    "stale":   ("一覧を1年更新し忘れる（2025年分なし）", offdays(stale)),
    "copied":  ("前の年の月日を写す（2025年分）", offdays(copied)),
}

# ---------- 架空の取引 ----------
days = pd.date_range(START, END)
w = np.where(days.dayofweek >= 5, 0.25, 1.0)                 # 土日の受付は平日の4分の1
recv = pd.Series(rng.choice(days, size=N, p=w / w.sum())).sort_values().reset_index(drop=True)
tx = pd.DataFrame({"tx_id": np.arange(1, N + 1), "received": recv})
tx.to_csv(DATA / "transactions.csv", index=False, date_format="%Y-%m-%d")

dates = cal.d.values


def due_dates(off):
    """受付日の次の営業日を1日目として、K営業日目の日付。"""
    biz = (~off).cumsum()                                    # その日までの営業日の数
    pos = np.searchsorted(dates, tx.received.values)
    target = biz[pos] + K
    idx = np.searchsorted(biz, target, side="left")
    return pd.Series(dates[idx])


due = pd.DataFrame({k: due_dates(off) for k, (_, off) in METHODS.items()})
due.insert(0, "received", tx.received)
due.insert(0, "tx_id", tx.tx_id)

# ---------- DuckDB で同じ計算（正しい決まり） ----------
con = duckdb.connect()
calsql = pd.DataFrame({"d": cal.d, "is_off": METHODS["truth"][1]})
con.register("cal0", calsql); con.register("tx", tx)
sql = """
WITH cal AS (
  SELECT d, is_off,
         SUM(CASE WHEN is_off THEN 0 ELSE 1 END) OVER (ORDER BY d ROWS UNBOUNDED PRECEDING) AS biz_no
  FROM cal0
),
biz AS (SELECT d, biz_no FROM cal WHERE NOT is_off)
SELECT t.tx_id, b.d AS due
FROM tx t
JOIN cal c ON c.d = t.received
JOIN biz b ON b.biz_no = c.biz_no + 5
ORDER BY t.tx_id
"""
sqldue = con.execute(sql).df()
assert (pd.to_datetime(sqldue.due).values == due.truth.values).all(), "SQL と Python が一致しない"
pd.DataFrame({"check": ["DuckDB と Python の期日が一致した件数", "件数"], "value": [int((pd.to_datetime(sqldue.due).values == due.truth.values).sum()), N]}).to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---------- 集計 ----------
rows = []
for k, (label, _) in METHODS.items():
    if k == "truth":
        continue
    gap = (due.truth - due[k]).dt.days                       # 正しい期日 − その数え方の期日（＋なら早すぎる）
    scope = due.received.dt.year == 2025 if k in ("stale", "copied") else (due.received.dt.year <= 2021 if k == "oldrule" else pd.Series(True, index=due.index))
    g = gap[scope]
    rows.append({"key": k, "method": label, "scope": "2025年の受付" if k in ("stale", "copied") else ("2019〜2021年の受付" if k == "oldrule" else "全期間"),
                 "n": int(scope.sum()), "diff": int((g != 0).sum()), "diff_pct": round(100 * (g != 0).mean(), 2),
                 "early": int((g > 0).sum()), "late": int((g < 0).sum()),
                 "gap1": int((g.abs() == 1).sum()), "gap2": int((g.abs() == 2).sum()), "gap3": int((g.abs() == 3).sum()),
                 "gap4plus": int((g.abs() >= 4).sum()), "max_gap": int(g.abs().max())})
summ = pd.DataFrame(rows)
summ.to_csv(RES / "summary_by_method.csv", index=False)

# 月ごと（受付の月）
bym = []
for k in ("weekend", "no_ny", "named"):
    gap = (due.truth - due[k]).dt.days
    t = pd.DataFrame({"m": due.received.dt.month, "diff": gap != 0}).groupby("m")["diff"].agg(["mean", "size"])
    for m, r in t.iterrows():
        bym.append({"key": k, "month": int(m), "n": int(r["size"]), "diff_pct": round(100 * r["mean"], 2)})
bym = pd.DataFrame(bym)
bym.to_csv(RES / "by_month.csv", index=False)

# 年ごと（振替休日の入れ忘れ、法律が変わる前の一覧）
byy = []
for k in ("named", "oldrule"):
    gap = (due.truth - due[k]).dt.days
    t = pd.DataFrame({"y": due.received.dt.year, "diff": gap != 0}).groupby("y")["diff"].agg(["mean", "size"])
    for y, r in t.iterrows():
        byy.append({"key": k, "year": int(y), "n": int(r["size"]), "diff_pct": round(100 * r["mean"], 2)})
byy = pd.DataFrame(byy); byy.to_csv(RES / "by_year.csv", index=False)

# 2025年の受付を月ごとに（更新し忘れ・月日を写す）
m25 = []
sel = due.received.dt.year == 2025
for k in ("stale", "copied"):
    gap = (due.truth - due[k]).dt.days[sel]
    t = pd.DataFrame({"m": due.received[sel].dt.month, "diff": gap != 0}).groupby("m")["diff"].agg(["mean", "size"])
    for m, r in t.iterrows():
        m25.append({"key": k, "month": int(m), "n": int(r["size"]), "diff_pct": round(100 * r["mean"], 2)})
m25 = pd.DataFrame(m25); m25.to_csv(RES / "year2025_by_month.csv", index=False)

# 休みの日の数（数え方ごと、2019〜2025年の平日のうち）
wk = (~cal.weekend.values) & (cal.d.dt.year.between(2019, 2025)).values
offcount = {k: int((off & wk).sum()) for k, (_, off) in METHODS.items()}
truth_off = METHODS["truth"][1]
missing = {k: int((truth_off & ~off & wk).sum()) for k, (_, off) in METHODS.items()}
extra = {k: int((~truth_off & off & wk).sum()) for k, (_, off) in METHODS.items()}

main = {"seed": SEED, "n": N, "k": K, "period": [START, END],
        "weekday_offdays_truth_2019_2025": offcount["truth"],
        "missing_offdays": missing, "extra_offdays": extra,
        "summary": summ.to_dict(orient="records"),
        "weekend_receipts_pct": round(100 * (tx.received.dt.dayofweek >= 5).mean(), 1),
        "sql_matches": True}
json.dump(main, open(RES / "a451_main.json", "w"), ensure_ascii=False, indent=1)

# ---------- 図 ----------
SRC = "祝日は内閣府「国民の祝日について」の一覧。取引は架空のデータ（乱数で作成、seed 451）"
fig, ax = plt.subplots(figsize=(8.6, 4.4))
s = summ.iloc[::-1]
col = [ORANGE if k in ("weekend", "no_ny") else BLUE for k in s.key]
ax.barh([f"{m}\n（{sc}）" for m, sc in zip(s.method, s.scope)], s.diff_pct, color=col)
for i, v in enumerate(s.diff_pct):
    ax.text(v + 0.3, i, f"{v:.1f}%", va="center", fontsize=10)
ax.set_xlabel("期日が正しい決まりと違った取引の割合（%）"); ax.set_xlim(0, max(s.diff_pct) * 1.18)
ax.set_title("休みの日の持ち方ごとの、期日がずれた取引の割合")
ax.tick_params(axis="y", labelsize=9)
save(fig, "a451_diff_by_method.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 4.2))
for k, c, lab in (("weekend", ORANGE, "土日だけ除く"), ("no_ny", GRAY, "土日と祝日（年末年始を入れない）"), ("named", BLUE, "振替休日・国民の休日を入れ忘れる")):
    t = bym[bym.key == k]
    ax.plot(t.month, t.diff_pct, marker="o", color=c, label=lab)
ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
ax.set_ylabel("期日がずれた取引の割合（%）"); ax.set_xlabel("受付の月（2019〜2025年）"); ax.set_ylim(0, None)
ax.legend(frameon=False, fontsize=9); ax.set_title("受付の月ごとの、期日がずれた割合")
save(fig, "a451_by_month.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 4.2))
x = np.arange(1, 13); wd = 0.38
for i, (k, c, lab) in enumerate((("stale", ORANGE, "一覧を1年更新し忘れる"), ("copied", BLUE, "前の年の月日を写す"))):
    t = m25[m25.key == k].set_index("month").reindex(x)
    ax.bar(x + (i - 0.5) * wd, t.diff_pct, wd, color=c, label=lab)
ax.set_xticks(x); ax.set_xticklabels([f"{m}月" for m in x])
ax.set_ylabel("期日がずれた取引の割合（%）"); ax.set_xlabel("受付の月（2025年）")
ax.legend(frameon=False, fontsize=9); ax.set_title("2025年分の祝日がないとき・前の年を写したときのずれ")
save(fig, "a451_year2025.png", SRC)
print(summ.to_string()); print(main["missing_offdays"], main["extra_offdays"], offcount)
print(bym.pivot(index="month", columns="key", values="diff_pct")); print(byy.pivot(index="year", columns="key", values="diff_pct")); print(m25.pivot(index="month", columns="key", values="diff_pct"))
