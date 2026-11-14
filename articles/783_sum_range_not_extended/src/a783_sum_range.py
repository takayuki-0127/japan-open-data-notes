"""783 合計の範囲を固定したまま行を足していくと、月の合計はどれだけ少なく出るのか

架空の入力表。月ごとに1枚のシートを作り、1件1行で日付順に入力していく（1日に数件、月に89〜164件で、後の月ほど多い）。
合計の式はひな形のまま「2行目から101行目まで（100件分）」に固定されている、とする。101件目からは合計に入らない。
この動きを Python で再現し（Excel では未検証）、「列全体の合計」「表（テーブル）の範囲の合計」（どちらも行が増えても入る）と比べる。
2025年の12か月で、月の合計がどれだけ少なく出るか、何日目から合計がずれ始めるかを数える。SQL（DuckDB、1スレッド）で出した月の合計と一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の入力表（作成者が乱数で作成、seed 783）"
rng = np.random.default_rng(783)
FIXED = 100
rows = []
for m in range(1, 13):
    days = pd.Period(f"2025-{m:02d}").days_in_month
    for d in range(1, days + 1):
        k = rng.poisson(3.9 + .25 * (m - 6) / 6 * 3)
        for _ in range(k):
            rows.append(dict(entry_date=pd.Timestamp(2025, m, d), amount=int(np.round(rng.lognormal(8.5, .6), -1))))
E_ = pd.DataFrame(rows)
DATA.mkdir(exist_ok=True); E_.assign(entry_date=E_.entry_date.dt.strftime("%Y-%m-%d")).to_csv(DATA / "entries.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("entries", E_)
q = "\n".join(l for l in (SQL / "02_check_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
M = []
for mo, g in E_.groupby(E_.entry_date.dt.strftime("%Y-%m")):
    g = g.reset_index(drop=True)
    fixed = int(g.amount.iloc[:FIXED].sum()); full = int(g.amount.sum())
    over_day = int(g.entry_date.iloc[FIXED].day) if len(g) > FIXED else None
    M.append(dict(month=mo, rows=len(g), sum_full=full, sum_fixed=fixed, missing=full - fixed, missing_share=1 - fixed / full,
                  first_wrong_day=over_day, days=g.entry_date.iloc[0].days_in_month))
M = pd.DataFrame(M)
assert (Q.amount.to_numpy() == M.sum_full.to_numpy()).all() and (Q.n_rows.to_numpy() == M.rows.to_numpy()).all()
M.to_csv(RES / "by_month.csv", index=False)
# 月の中の日ごとの見え方（例：最も行が多い月）
ex_m = M.month[M.rows.idxmax()]
g = E_[E_.entry_date.dt.strftime("%Y-%m") == ex_m].reset_index(drop=True)
g["cum_full"] = g.amount.cumsum(); g["cum_fixed"] = np.where(np.arange(len(g)) < FIXED, g.cum_full, g.cum_full.iloc[FIXED - 1])
daily = g.groupby(g.entry_date.dt.day)[["cum_full", "cum_fixed"]].last()
wrong = M[M.missing > 0]
out = {"fixed_rows": FIXED, "months": 12, "rows_total": len(E_),
       "months_over": int((M.rows > FIXED).sum()), "rows_min": int(M.rows.min()), "rows_max": int(M.rows.max()),
       "missing_total": int(M.missing.sum()), "missing_share_total": float(M.missing.sum() / M.sum_full.sum()),
       "missing_share_max": float(M.missing_share.max()), "missing_share_max_month": str(M.month[M.missing_share.idxmax()]),
       "missing_share_mean_over": float(wrong.missing_share.mean()) if len(wrong) else 0.0,
       "first_wrong_day_min": int(wrong.first_wrong_day.min()) if len(wrong) else None,
       "first_wrong_day_median": float(wrong.first_wrong_day.median()) if len(wrong) else None,
       "example_month": ex_m, "example_rows": len(g), "example_first_wrong_day": int(M[M.month == ex_m].first_wrong_day.iloc[0]),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a783_main.json", "w"), ensure_ascii=False, indent=1)

x = np.arange(12); lab = [m[5:] + "月" for m in M.month]
# 図1：月の合計
fig, ax = plt.subplots(figsize=(10, 4.6)); w = .38
ax.bar(x - w / 2, M.sum_full / 1e4, w, color=BLUE, label="列全体・表の範囲の合計（正しい）")
ax.bar(x + w / 2, M.sum_fixed / 1e4, w, color=ORANGE, label=f"範囲を{FIXED}行に固定した合計")
for xx, s, r in zip(x, M.missing_share * 100, M.rows):
    if s > 0: ax.text(xx + w / 2, M.sum_fixed[xx] / 1e4 + 2, f"−{s:.0f}%", ha="center", fontsize=8, color=ORANGE)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("月の合計（万円）"); ax.legend(frameon=False, loc="lower left")
ax.set_title(f"行が{FIXED}件を超えた月は、超えた分がそのまま消える")
save(fig, "a783_monthly.png", SRC)
# 図2：月の行数
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.bar(x, M.rows, color=[ORANGE if r > FIXED else GRAY for r in M.rows])
ax.axhline(FIXED, color="black", ls="--", lw=1); ax.text(11.4, FIXED + 1.5, f"式の範囲（{FIXED}行）", ha="right", fontsize=9)
for xx, r, d in zip(x, M.rows, M.first_wrong_day):
    ax.text(xx, r + 1.5, f"{r}" + (f"\n{int(d)}日〜" if pd.notna(d) else ""), ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("月の行数（件）"); ax.set_ylim(0, M.rows.max() * 1.2)
ax.set_title("行数が範囲を超えた日から、合計がずれ始める（数字の下は、ずれ始めた日）")
save(fig, "a783_rows.png", SRC)
# 図3：例の月の累計
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(daily.index, daily.cum_full / 1e4, "o-", color=BLUE, ms=3, label="正しい累計")
ax.plot(daily.index, daily.cum_fixed / 1e4, "s-", color=ORANGE, ms=3, label="範囲を固定した合計")
ax.axvline(out["example_first_wrong_day"], color=GRAY, ls="--")
ax.set_xlabel(f"{ex_m[5:]}月の日"); ax.set_ylabel("その日までの合計（万円）"); ax.legend(frameon=False)
ax.set_title(f"{int(ex_m[5:])}月：{out['example_first_wrong_day']}日から合計が止まり、あとは入力しても増えない")
save(fig, "a783_example.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
