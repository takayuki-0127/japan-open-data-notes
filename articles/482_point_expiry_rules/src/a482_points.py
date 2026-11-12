"""482 ポイントの失効を「月末に一括」と「付与日から1年」にすると、失効額はどれだけ違うのか（架空の会員3,000人・4年分）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from collections import deque
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "架空の会員・購入・ポイント（作成者が乱数で作成、seed 482）"
D0, D1 = pd.Timestamp("2023-01-01"), pd.Timestamp("2026-12-31")
NDAY = (D1 - D0).days + 1
rng = np.random.default_rng(482)
N = 3000
rate = rng.gamma(0.8, 1 / 0.8, N) * 18 / 365          # 1日あたりの購入回数（平均 年18回、ばらつき大）
use_p = rng.beta(2, 3, N)                              # 購入のときにポイントを使う確率
# 購入イベント（会員, 日, ポイント, 使いたい量の割合）
ev = []
for i in range(N):
    k = rng.poisson(rate[i] * NDAY)
    dd = np.sort(rng.integers(0, NDAY, k))
    pts = np.maximum(1, np.round(rng.lognormal(np.log(40), 0.8, k))).astype(int)   # 1回の付与ポイント
    u = rng.random(k) < use_p[i]
    want = rng.uniform(0.3, 1.0, k)
    for a, b, c, e in zip(dd, pts, u, want):
        ev.append((i, int(a), int(b), bool(c), float(e)))
ev = pd.DataFrame(ev, columns=["member", "day", "grant", "use_flag", "use_share"]).sort_values(["member", "day"], kind="stable").reset_index(drop=True)
ev.insert(0, "event_id", np.arange(len(ev)))
ev.to_csv(DATA / "fictional_purchases.csv", index=False)
dates = D0 + pd.to_timedelta(np.arange(NDAY + 800), "D")


def exp_day(day, rule):
    """失効日（この日から使えない）。A：付与日から365日後。B：付与月の12か月後の月末の翌日"""
    if rule == "A":
        return day + 365
    t = dates[day]
    nxt = (t + pd.offsets.MonthBegin(13)) if t.day != 1 else (t + pd.DateOffset(months=13))
    nxt = pd.Timestamp(nxt.year, nxt.month, 1)
    return (nxt - D0).days


def simulate(rule):
    """会員ごとに日付順に、失効 → 利用（古い付与から）→ 付与。C は最後の付与・利用から365日で全額失効"""
    grants, uses, expired = [], [], []
    for m, g in ev.groupby("member", sort=False):
        q = deque()     # [grant_id, exp, remaining]
        last = None; bal = 0
        for r in g.itertuples(index=False):
            day = r.day
            if rule == "C":
                if last is not None and day >= last + 365 and bal > 0:
                    for gg in q:
                        if gg[2] > 0: expired.append((gg[0], m, last + 365, gg[2]))
                    q.clear(); bal = 0
            else:
                while q and q[0][1] <= day:
                    gg = q.popleft()
                    if gg[2] > 0: expired.append((gg[0], m, gg[1], gg[2]))
                    bal -= gg[2]
            if r.use_flag and bal > 0:
                amt = int(round(bal * r.use_share)); amt = max(1, min(amt, bal))
                uses.append((m, day, amt)); bal -= amt; left = amt
                while left > 0:
                    take = min(left, q[0][2]); q[0][2] -= take; left -= take
                    if q[0][2] == 0: q.popleft()
                last = day
            e = exp_day(day, rule) if rule != "C" else None
            q.append([r.event_id, e, r.grant]); bal += r.grant
            grants.append((r.event_id, m, day, e if e is not None else -1, r.grant))
            last = day
        if rule == "C" and last is not None and bal > 0:
            for gg in q:
                if gg[2] > 0: expired.append((gg[0], m, last + 365, gg[2]))
        elif rule != "C":
            for gg in q:
                if gg[2] > 0: expired.append((gg[0], m, gg[1], gg[2]))
    G = pd.DataFrame(grants, columns=["grant_id", "member", "day", "exp_day", "pts"])
    U = pd.DataFrame(uses, columns=["member", "day", "pts"])
    E = pd.DataFrame(expired, columns=["grant_id", "member", "exp_day", "pts"])
    return G, U, E


SQL = """
-- 付与ごとの失効額：累計付与 − 失効日までの累計利用 の「それまでの最大値」が累計失効額になる
WITH g AS (
  SELECT grant_id, member, day, exp_day, pts,
         SUM(pts) OVER (PARTITION BY member ORDER BY day, grant_id ROWS UNBOUNDED PRECEDING) AS cum_g
  FROM G),
gu AS (
  SELECT g.*, COALESCE((SELECT SUM(u.pts) FROM U u WHERE u.member = g.member AND u.day < g.exp_day), 0) AS cum_u
  FROM g),
x AS (
  SELECT *, GREATEST(0, MAX(cum_g - cum_u) OVER (PARTITION BY member ORDER BY day, grant_id ROWS UNBOUNDED PRECEDING)) AS cum_e
  FROM gu)
SELECT grant_id, member, exp_day,
       cum_e - COALESCE(LAG(cum_e) OVER (PARTITION BY member ORDER BY day, grant_id), 0) AS expired
FROM x"""

res = {}; S = {}
for rule in ["A", "B", "C"]:
    G, U, E = simulate(rule)
    S[rule] = (G, U, E)
    if rule in "AB":   # SQL（DuckDB）で失効額を計算し直して、シミュレーションと突き合わせる
        q = duckdb.sql(SQL).df()
        q = q[q.expired > 0].sort_values("grant_id").reset_index(drop=True)
        e2 = E.sort_values("grant_id").reset_index(drop=True)
        assert len(q) == len(e2) and (q.grant_id.values == e2.grant_id.values).all() and (q.expired.values == e2.pts.values).all(), rule
        res[f"sql_check_{rule}"] = f"{len(q)} grants match"

# 月ごと・年ごとに集計（2024〜2026年。2023年は助走）
def month(day): return (D0 + pd.to_timedelta(day, "D")).to_period("M").to_timestamp()
rows = []
for rule in "ABC":
    G, U, E = S[rule]
    E = E[E.exp_day < NDAY]
    for name, df, col in [("granted", G, "day"), ("used", U, "day"), ("expired", E, "exp_day")]:
        s = df.groupby(df[col].map(month)).pts.sum()
        for m, v in s.items(): rows.append({"rule": rule, "kind": name, "m": m, "pts": int(v)})
mon = pd.DataFrame(rows).pivot_table(index=["m"], columns=["rule", "kind"], values="pts", fill_value=0)
mon = mon[mon.index >= "2024-01-01"]
mon.columns = [f"{a}_{b}" for a, b in mon.columns]
mon.to_csv(RES / "monthly_points.csv")
yr = mon.groupby(mon.index.year).sum()
summ = []
for y, r in yr.iterrows():
    for rule in "ABC":
        summ.append({"year": int(y), "rule": rule, "granted": int(r[f"{rule}_granted"]), "used": int(r[f"{rule}_used"]),
                     "expired": int(r[f"{rule}_expired"]), "expire_rate": r[f"{rule}_expired"] / r[f"{rule}_granted"] * 100})
summ = pd.DataFrame(summ); summ.to_csv(RES / "annual_points.csv", index=False)
# 月末の残高
bal = []
for rule in "ABC":
    G, U, E = S[rule]
    for me in pd.date_range("2024-01-31", "2026-12-31", freq="ME"):
        dd = (me - D0).days
        b = G[G.day <= dd].pts.sum() - U[U.day <= dd].pts.sum() - E[E.exp_day <= dd].pts.sum()
        bal.append({"rule": rule, "month_end": me, "balance": int(b)})
bal = pd.DataFrame(bal).pivot(index="month_end", columns="rule", values="balance"); bal.to_csv(RES / "balance_month_end.csv")
# 月ごとの失効額の差（B − A）、1日の失効の集中
mdiff = (mon["B_expired"] - mon["A_expired"])
EA = S["A"][2]; EB = S["B"][2]
EA = EA[(EA.exp_day < NDAY) & (EA.exp_day >= (pd.Timestamp("2024-01-01") - D0).days)]
EB = EB[(EB.exp_day < NDAY) & (EB.exp_day >= (pd.Timestamp("2024-01-01") - D0).days)]
dA = EA.groupby("exp_day").pts.sum(); dB = EB.groupby("exp_day").pts.sum()
res.update({
    "members": N, "purchases": int(len(ev)),
    "annual": summ.round(2).to_dict("records"),
    "expired_total_2024_2026": {r: int(summ[summ.rule == r].expired.sum()) for r in "ABC"},
    "monthly_diff_B_minus_A": {"mean_abs": float(mdiff.abs().mean()), "max_abs": int(mdiff.abs().max()),
                               "mean_abs_pct_of_A": float((mdiff.abs() / mon["A_expired"]).mean() * 100)},
    "days_with_expiry": {"A": int((dA > 0).sum()), "B": int((dB > 0).sum())},
    "max_one_day_share_of_month": {"A": float((dA.groupby(dA.index.map(month)).max() / dA.groupby(dA.index.map(month)).sum()).mean() * 100),
                                   "B": 100.0},
    "balance_2026_12": {r: int(bal[r].iloc[-1]) for r in "ABC"},
})
m2 = mon[mon.index >= "2025-01-01"]; d2 = m2["B_expired"] - m2["A_expired"]
res["steady_2025_2026"] = {"expired": {r: int(m2[f"{r}_expired"].sum()) for r in "ABC"},
                           "granted": int(m2["A_granted"].sum()),
                           "monthly_diff_mean_abs": float(d2.abs().mean()), "monthly_diff_mean_abs_pct_of_A": float((d2.abs() / m2["A_expired"]).mean() * 100),
                           "monthly_diff_max_abs": int(d2.abs().max()), "months_B_higher": int((d2 > 0).sum()), "months_A_higher": int((d2 < 0).sum())}
json.dump(res, open(RES / "a482_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：月ごとの失効額
fig, ax = plt.subplots(figsize=(10, 4.4))
mon = mon[mon.index >= "2025-01-01"]
ax.plot(mon.index, mon["A_expired"] / 1e3, color=BLUE, lw=2, label="付与日から1年")
ax.plot(mon.index, mon["B_expired"] / 1e3, color=ORANGE, lw=2, label="付与月の1年後の月末に一括")
ax.plot(mon.index, mon["C_expired"] / 1e3, color=GRAY, lw=1.6, ls="--", label="最後の付与・利用から1年（参考）")
ax.set_ylabel("月の失効ポイント（千pt）"); ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=.3)
ax.set_title("月ごとの失効額：決まりで月の数字がずれる（2025〜2026年）", loc="left"); ax.set_ylim(0, None)
save(fig, "a482_monthly_expiry.png", SRC)

# 図2：年ごとの失効率と月末残高
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
summ = summ[summ.year >= 2025]; xs = np.arange(2)
for j, (rule, c, lab) in enumerate([("A", BLUE, "付与日から1年"), ("B", ORANGE, "月末に一括"), ("C", GRAY, "最後の付与・利用から1年")]):
    v = summ[summ.rule == rule].expire_rate.values
    axs[0].bar(xs + (j - 1) * 0.27, v, 0.27, color=c, label=lab)
    for x, vv in zip(xs + (j - 1) * 0.27, v): axs[0].text(x, vv + 0.3, f"{vv:.1f}", ha="center", fontsize=8)
axs[0].set_xticks(xs); axs[0].set_xticklabels(["2025年", "2026年"]); axs[0].set_ylabel("失効率（失効÷付与、%）")
axs[0].legend(frameon=False, fontsize=8); axs[0].set_title("年の失効率", loc="left", fontsize=11)
for rule, c in [("A", BLUE), ("B", ORANGE), ("C", GRAY)]:
    axs[1].plot(bal.index, bal[rule] / 1e3, color=c, lw=2)
import matplotlib.dates as mdates
axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); axs[1].set_ylabel("月末のポイント残高（千pt）"); axs[1].set_title("月末の残高", loc="left", fontsize=11); axs[1].grid(axis="y", alpha=.3)
save(fig, "a482_rate_and_balance.png", SRC)

# 図3：ある3か月の日ごとの失効
fig, ax = plt.subplots(figsize=(10, 4))
lo, hi = (pd.Timestamp("2025-04-01") - D0).days, (pd.Timestamp("2025-06-30") - D0).days
x = np.arange(lo, hi + 1); da = dA.reindex(x, fill_value=0); db = dB.reindex(x, fill_value=0)
xd = D0 + pd.to_timedelta(x, "D")
ax.bar(xd, da / 1e3, width=0.8, color=BLUE, label="付与日から1年")
ax.bar(xd, db / 1e3, width=0.8, color=ORANGE, alpha=.8, label="月末に一括（翌月1日に失効）")
ax.set_ylabel("その日の失効ポイント（千pt）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("日ごとの失効：月末に一括だと、1日に集まる（2025年4〜6月）", loc="left")
save(fig, "a482_daily_expiry.png", SRC)
print(json.dumps(res, ensure_ascii=False, default=float)[:3000])
print(summ.round(2).to_string())
