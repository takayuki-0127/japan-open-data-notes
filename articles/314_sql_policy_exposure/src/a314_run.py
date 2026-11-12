"""314 契約の「在籍件数」を、SQL でどう数えるか
架空の保険契約（始期・終期・中途解約）で、日数で数えた経過契約年と、件数で代える7つの数え方を比べる"""
import json, re
import numpy as np, pandas as pd, duckdb
from common import SQL, RES

SEED = 314
LAMBDA = 0.060   # 1契約・1年あたりの事故の件数（正解。架空の置き方）
YEAR_FROM, YEAR_TO = "2025-01-01", "2026-01-01"


def make(growth=0.15, april=0.25, cancel=0.08, seed=SEED, n2023=30_000):
    """growth＝新しい契約が毎年どれだけ増えるか、april＝4月始期に集まる割合、cancel＝期間の途中で解約する割合"""
    rng = np.random.default_rng(seed)
    rows = []
    for k, y in enumerate([2023, 2024, 2025, 2026]):
        n = int(n2023 * (1 + growth) ** k)
        days = pd.date_range(f"{y}-01-01", f"{y}-12-31", freq="D")
        w = np.ones(len(days)); apr = days.month == 4
        w[apr] = 0; w = w / w.sum() * (1 - april)
        w[apr] = april / apr.sum()
        w[(days.month == 4) & (days.day == 1)] *= 8          # 4月1日始期が特に多い
        w = w / w.sum()
        rows.append(pd.DataFrame({"start_date": rng.choice(days, n, p=w)}))
    p = pd.concat(rows, ignore_index=True)
    p["start_date"] = pd.to_datetime(p.start_date)
    p["full_end"] = p.start_date + pd.DateOffset(years=1)
    term = (p.full_end - p.start_date).dt.days
    c = rng.random(len(p)) < cancel
    p["end_date"] = p.full_end
    p.loc[c, "end_date"] = p.start_date[c] + pd.to_timedelta((rng.uniform(0.02, 0.98, c.sum()) * term[c]).astype(int).clip(lower=1), unit="D")
    p["cancelled"] = c.astype(int)
    p.insert(0, "policy_id", np.arange(1, len(p) + 1))
    # 事故：在籍した日数に比例して起きる（1年あたり LAMBDA 件）
    days_in = (p.end_date - p.start_date).dt.days.values
    k = rng.poisson(LAMBDA * days_in / 365.0)
    pid = np.repeat(p.policy_id.values, k)
    off = (rng.random(len(pid)) * np.repeat(days_in, k)).astype(int)
    claims = pd.DataFrame({"policy_id": pid, "claim_date": np.repeat(p.start_date.values, k) + pd.to_timedelta(off, unit="D")})
    months = pd.DataFrame({"month_start": pd.date_range("2023-01-01", "2026-12-01", freq="MS")})
    months["next_month_start"] = months.month_start + pd.DateOffset(months=1)
    return p[["policy_id", "start_date", "end_date", "cancelled"]], claims, months


def blocks():
    out = {}
    for b in re.split(r"-- name: ", (SQL / "exposure.sql").read_text(encoding="utf-8"))[1:]:
        name, body = b.split("\n", 1); out[name.strip()] = body.strip()
    return out


def to_duck(q):
    return q.replace("dbo.", "").replace("DATEDIFF(day,", "date_diff('day',").replace("AS FLOAT", "AS DOUBLE").replace("{FROM}", YEAR_FROM).replace("{TO}", YEAR_TO)


def measure(p, claims, months):
    con = duckdb.connect()
    for n, df in [("policies", p), ("claims", claims), ("months", months)]:
        df = df.copy()
        for c in df.columns:
            if "date" in c or "month" in c: df[c] = df[c].dt.date
        con.register(n + "_df", df); con.execute(f"CREATE TABLE {n} AS SELECT * FROM {n}_df")
    f, t = pd.Timestamp(YEAR_FROM), pd.Timestamp(YEAR_TO)
    ov = (p.end_date.clip(upper=t) - p.start_date.clip(lower=f)).dt.days.clip(lower=0)
    exact = ov.sum() / 365.0                       # pandas で別に計算した経過契約年
    n_claims = int(((claims.claim_date >= f) & (claims.claim_date < t)).sum())
    rows = []
    for name, sql in blocks().items():
        v = float(con.execute(to_duck(sql)).fetchone()[0])
        rows.append({"数え方": name, "在籍の量": round(v, 2), "正解との差(%)": round((v / exact - 1) * 100, 2),
                     "事故率(%)": round(n_claims / v * 100, 3), "事故率の差(%)": round((n_claims / v / (n_claims / exact) - 1) * 100, 2)})
    assert abs(rows[0]["在籍の量"] - round(exact, 2)) < 0.01, (rows[0], exact)
    return pd.DataFrame(rows), exact, n_claims, con


def main():
    p, claims, months = make()
    res, exact, n_claims, con = measure(p, claims, months)
    res.to_csv(RES / "eight_ways.csv", index=False)
    # 月ごと：日数で数えた在籍（契約月）と、月初の件数・月末の件数
    q = """SELECT m.month_start,
      SUM(date_diff('day', GREATEST(p.start_date, m.month_start), LEAST(p.end_date, m.next_month_start)))
        / CAST(date_diff('day', m.month_start, m.next_month_start) AS DOUBLE) AS exact_months,
      SUM(CASE WHEN p.start_date <= m.month_start AND p.end_date > m.month_start THEN 1 ELSE 0 END) AS at_start,
      SUM(CASE WHEN p.start_date < m.next_month_start AND p.end_date >= m.next_month_start THEN 1 ELSE 0 END) AS at_end
    FROM months m JOIN policies p ON p.start_date < m.next_month_start AND p.end_date > m.month_start
    WHERE m.month_start >= DATE '2025-01-01' AND m.month_start < DATE '2026-01-01' GROUP BY m.month_start, m.next_month_start ORDER BY 1"""
    mon = con.execute(q).df()
    mon["月初の差(%)"] = ((mon.at_start / mon.exact_months - 1) * 100).round(2); mon["月末の差(%)"] = ((mon.at_end / mon.exact_months - 1) * 100).round(2)
    mon["平均の差(%)"] = (((mon.at_start + mon.at_end) / 2 / mon.exact_months - 1) * 100).round(2)
    mon["exact_months"] = mon.exact_months.round(1); mon.to_csv(RES / "by_month_2025.csv", index=False)
    # 契約の増え方を変える
    sw = []
    for g in [-0.2, -0.1, 0.0, 0.15, 0.3, 0.5]:
        r, ex, nc, _ = measure(*make(growth=g))
        for _, x in r.iterrows(): sw.append({"新しい契約の増え方": g, "数え方": x["数え方"], "正解との差(%)": x["正解との差(%)"]})
    sw = pd.DataFrame(sw); sw.to_csv(RES / "growth_sweep.csv", index=False)
    # 4月への集中をなくした場合・解約をなくした場合
    alt = {}
    for label, kw in [("4月への集中なし", dict(april=1 / 12)), ("解約なし", dict(cancel=0.0)), ("解約が2倍", dict(cancel=0.16))]:
        r, ex, nc, _ = measure(*make(**kw)); alt[label] = {x["数え方"][:1]: x["正解との差(%)"] for _, x in r.iterrows()}
    summary = {"seed": SEED, "契約": len(p), "うち途中で解約": int(p.cancelled.sum()), "事故の正解（1契約年あたり）": LAMBDA,
               "2025年の経過契約年（日数で数えた正解）": round(exact, 1), "2025年の事故": n_claims, "日数で数えた事故率(%)": round(n_claims / exact * 100, 3),
               "置き方": {"新しい契約の増え方": 0.15, "4月始期の割合": 0.25, "途中解約の割合": 0.08}, "置き方を変えたとき（正解との差%）": alt}
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); print(res.to_string()); print(mon.to_string()); print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(sw.pivot(index="数え方", columns="新しい契約の増え方", values="正解との差(%)").to_string())


if __name__ == "__main__":
    main()
