"""505 定期便の次回のお届け日を「30日後」と「毎月同じ日」で決めると、1年の出荷回数と月の出荷数はどれだけ違うのか（実務の型）

架空の定期便の会員（2025年に申込、月末の申込やスキップを含む）について、次回のお届け日の決め方4通りで
2026年の1年分のお届け日を作り、1人あたりの回数・月ごとの出荷数・日付のずれを数える。
"""
import json, calendar
from datetime import date, timedelta
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 505
SRC = "架空の定期便の会員データ（作成者が乱数で作成、seed 505）"
RULES = {"d30": "30日後", "same_anchor": "毎月同じ日（申込日の日にち、ない月は月末）",
         "same_drift": "前回のお届け日に1か月足す", "w4": "4週ごと（28日後）"}
Y0, Y1 = date(2026, 1, 1), date(2026, 12, 31)


def add_month(d, anchor_day):
    y, m = (d.year + (d.month // 12), d.month % 12 + 1)
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(anchor_day, last))


def schedule(start, rule, end=Y1):
    out = [start]; d = start; anchor = start.day
    while True:
        if rule == "d30":
            d = d + timedelta(days=30)
        elif rule == "w4":
            d = d + timedelta(days=28)
        elif rule == "same_anchor":
            d = add_month(d, anchor)
        else:
            d = add_month(d, d.day)            # 前回の日にちのまま1か月足す（31日→2月28日→3月28日…と戻らない）
        if d > end:
            return out
        out.append(d)


def make(n=5000, seed=SEED):
    rng = np.random.default_rng(seed)
    days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    w = np.ones(len(days)); w[days.day >= 29] *= 3.0          # 月末の申込（給料日のあと）を多めに
    st = rng.choice(days, n, p=w / w.sum())
    return pd.DataFrame({"member": range(n), "signup": pd.to_datetime(st).date})


def main():
    mem = make(); mem.to_csv(DATA / "fictional_subscribers.csv", index=False)
    rng = np.random.default_rng(SEED + 1)
    rows = []
    for r in mem.itertuples():
        skips = None
        for rule in RULES:
            s = schedule(r.signup, rule)
            if skips is None:
                skips = rng.random(40) < 0.10                     # 予定の10%はスキップ（同じ回をどの決め方でもスキップ）
            for k, d in enumerate(s):
                if Y0 <= d <= Y1:
                    rows.append((r.member, rule, d, bool(skips[k % 40])))
    sh = pd.DataFrame(rows, columns=["member", "rule", "date", "skipped"])
    sh.to_csv(RES / "deliveries_2026.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    ship = sh[~sh["skipped"]]
    out = {"members": len(mem), "month_end_signups": int(sum(d.day >= 29 for d in mem["signup"]))}
    per = ship.groupby(["rule", "member"]).size().unstack(0).fillna(0)
    sched = sh.groupby(["rule", "member"]).size().unstack(0).fillna(0)
    out["scheduled_per_person"] = {r: {"mean": round(float(sched[r].mean()), 3), "dist": sched[r].value_counts().sort_index().astype(int).to_dict()} for r in RULES}
    out["shipped_per_person_mean"] = {r: round(float(per[r].mean()), 3) for r in RULES}
    out["total_shipments"] = {r: int(per[r].sum()) for r in RULES}
    mon = ship.assign(m=pd.to_datetime(ship["date"]).dt.month).groupby(["m", "rule"]).size().unstack()
    mon.to_csv(RES / "monthly_shipments_2026.csv")
    out["monthly"] = {r: {"min": int(mon[r].min()), "max": int(mon[r].max()), "cv_pct": round(float(mon[r].std() / mon[r].mean() * 100), 2)} for r in RULES}
    two = sh.assign(m=pd.to_datetime(sh["date"]).dt.month).groupby(["rule", "member", "m"]).size()
    out["member_months_with_2"] = {r: int((two.loc[r] >= 2).sum()) for r in RULES}
    out["members_with_a_2_month"] = {r: int((two.loc[r] >= 2).groupby(level=0).any().sum()) for r in RULES}
    # 日にちのずれ：申込日の日にちと、2026年12月のお届け日の日にち
    dec = sh[pd.to_datetime(sh["date"]).dt.month == 12].groupby(["rule", "member"])["date"].first().unstack(0)
    sday = mem.set_index("member")["signup"].map(lambda d: d.day)
    out["dec_day_differs_from_signup_day"] = {r: int((dec[r].map(lambda d: d.day if isinstance(d, date) else np.nan) != sday.loc[dec.index]).sum()) for r in ["same_anchor", "same_drift"]}
    me = mem["signup"].map(lambda d: d.day >= 29)
    md = dec["same_drift"].map(lambda d: d.day if isinstance(d, date) else np.nan)
    out["month_end_signups_drifted_to_28_or_less"] = int(((md <= 28) & me.values[dec.index]).sum())
    wk = ship.assign(dow=pd.to_datetime(ship["date"]).dt.dayofweek).groupby(["rule", "dow"]).size().unstack(0)
    out["weekend_share_pct"] = {r: round(float(wk.loc[[5, 6], r].sum() / wk[r].sum() * 100), 2) for r in RULES}
    # 月末（29日以降）に出る数
    lastdays = ship.assign(d=pd.to_datetime(ship["date"]).dt.day).query("d >= 29").groupby("rule").size()
    out["shipments_on_29_31"] = {r: int(lastdays.get(r, 0)) for r in RULES}
    on28 = ship.assign(d=pd.to_datetime(ship["date"]).dt.day).query("d == 28").groupby("rule").size()
    out["shipments_on_28"] = {r: int(on28.get(r, 0)) for r in RULES}
    daily = ship.groupby(["rule", "date"]).size()
    out["daily_max"] = {r: int(daily.loc[r].max()) for r in RULES}
    out["daily_max_date"] = {r: str(daily.loc[r].idxmax()) for r in RULES}
    out["monthly_max_month"] = {r: int(mon[r].idxmax()) for r in RULES}
    out["monthly_min_month"] = {r: int(mon[r].idxmin()) for r in RULES}
    # DuckDB：日付に INTERVAL 1 MONTH を足していくと、月末で日にちが縮んだまま戻らないことを確かめる
    con = duckdb.connect()
    q = open(SQL / "02_add_month_duckdb.sql", encoding="utf-8").read()
    out["duckdb_add_month_from_jan31"] = [str(x[0]) for x in con.sql(q).fetchall()]
    py = [str(d) for d in schedule(date(2025, 1, 31), "same_drift", end=date(2025, 12, 31))]
    assert py == out["duckdb_add_month_from_jan31"], (py, out["duckdb_add_month_from_jan31"])
    json.dump(out, open(RES / "a505_main.json", "w"), ensure_ascii=False, indent=1, default=str)
    figs(mon, sched, dec, mem)
    print(json.dumps(out, ensure_ascii=False, default=str))


def figs(mon, sched, dec, mem):
    cols = {"d30": ORANGE, "same_anchor": BLUE, "same_drift": GRAY, "w4": GREEN}
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for r in RULES:
        ax.plot(mon.index, mon[r], marker="o", color=cols[r], label=RULES[r], ls="--" if r == "same_drift" else "-")
    ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)]); ax.set_ylabel("出荷の数（スキップを除く）")
    ax.legend(frameon=False, fontsize=9); ax.set_title("2026年の月ごとの出荷の数")
    save(fig, "a505_monthly.png", SRC)
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ks = list(RULES); w = 0.2
    vals = sorted(set().union(*[set(sched[r].astype(int)) for r in ks]))
    for i, r in enumerate(ks):
        v = sched[r].astype(int).value_counts().reindex(vals, fill_value=0) / len(sched) * 100
        ax.bar(np.arange(len(vals)) + (i - 1.5) * w, v.values, w, color=cols[r], label=RULES[r])
    ax.set_xticks(range(len(vals)), [f"{v}回" for v in vals]); ax.set_ylabel("会員の割合（%）")
    ax.set_ylim(0, 128); ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2); ax.set_title("2026年の1年間に予定されるお届けの回数（1人あたり）")
    save(fig, "a505_per_person.png", SRC)
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    sday = mem.set_index("member")["signup"].map(lambda d: d.day)
    for r, mk in [("same_anchor", "o"), ("same_drift", "x")]:
        dd = dec[r].map(lambda d: d.day if isinstance(d, date) else np.nan)
        t = pd.DataFrame({"s": sday.loc[dec.index], "d": dd}).groupby("s")["d"].mean()
        ax.plot(t.index, t.values, marker=mk, color=cols[r], label=RULES[r])
    ax.plot([1, 31], [1, 31], color=INK, lw=0.6, ls=":")
    ax.set_xlabel("申込日の日にち"); ax.set_ylabel("2026年12月のお届け日の日にち（平均）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("「1か月足す」をくり返すと、月末の申込は28日に縮んだまま戻らない")
    save(fig, "a505_day_drift.png", SRC)


if __name__ == "__main__":
    main()
