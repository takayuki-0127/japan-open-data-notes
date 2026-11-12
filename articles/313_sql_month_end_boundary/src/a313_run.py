"""313 月の集計で、月末の最終日はどれだけ落ちているのか
架空の時刻つき取引（12か月）に、月を絞る9つの書き方を当て、落ちる行・余分に入る行を数える"""
import json, re, calendar
import numpy as np, pandas as pd, duckdb
from common import SQL, RES

SEED = 313
MONTHS = pd.period_range("2025-04", "2026-03", freq="M")
N = 300_000


def make(last_day_weight=2.0, seed=SEED):
    """last_day_weight＝月の最終日の取引が、ふつうの日の何倍あるか"""
    rng = np.random.default_rng(seed)
    days = pd.date_range(MONTHS[0].start_time, MONTHS[-1].end_time.normalize(), freq="D")
    w = np.ones(len(days)); w[days.is_month_end] = last_day_weight
    d = rng.choice(len(days), N, p=w / w.sum())
    # 時刻：昼と夜（21〜翌1時）に山。深夜の取引もある
    hour_w = np.array([3, 2, 1, .5, .5, .5, 1, 2, 3, 4, 5, 5, 6, 5, 4, 4, 4, 5, 6, 7, 8, 9, 8, 6], float)
    h = rng.choice(24, N, p=hour_w / hour_w.sum())
    sec = rng.integers(0, 3600, N); ms = rng.integers(0, 1000, N)
    ts = days[d] + pd.to_timedelta(h, unit="h") + pd.to_timedelta(sec, unit="s") + pd.to_timedelta(ms, unit="ms")
    amount = rng.lognormal(8.0, 0.8, N).round(-1).astype(int)
    df = pd.DataFrame({"ts_jst": ts, "amount": amount, "kind": "通常"})
    # 毎月1日 0:00:00 ちょうどに入る定期課金（1回 600件）
    sub = pd.DataFrame({"ts_jst": np.repeat([m.start_time for m in MONTHS], 600), "amount": 1980, "kind": "定期課金"})
    df = pd.concat([df, sub]).sort_values("ts_jst").reset_index(drop=True)
    df["tx_id"] = np.arange(1, len(df) + 1); df["ts_utc"] = df.ts_jst - pd.Timedelta(hours=9)
    return df[["tx_id", "ts_jst", "ts_utc", "amount", "kind"]]


def blocks():
    out = {}
    for b in re.split(r"-- name: ", (SQL / "month_filters.sql").read_text(encoding="utf-8"))[1:]:
        name, body = b.split("\n", 1); out[name.strip()] = body.strip()
    return out


def to_duck(q):
    q = q.replace("dbo.", "")
    q = re.sub(r"DATEADD\(hour,\s*(\d+),\s*(\w+)\)", r"(\2 + INTERVAL \1 HOUR)", q)   # T-SQL の DATEADD
    q = re.sub(r"EOMONTH\(('[^']+')\)", r"last_day(CAST(\1 AS DATE))", q)             # T-SQL の EOMONTH
    return q


def evaluate(df, con):
    q = blocks(); rows = []
    for m in MONTHS:
        m0 = m.start_time; m1 = (m + 1).start_time; ml = m.end_time.normalize()
        true = df[(df.ts_jst >= m0) & (df.ts_jst < m1)]
        for name, sql in q.items():
            cond = to_duck(sql).split("WHERE", 1)[1].rstrip(";")
            cond = cond.replace("{M0}", f"{m0:%Y-%m-%d}").replace("{ML}", f"{ml:%Y-%m-%d}").replace("{M1}", f"{m1:%Y-%m-%d}")
            n, total = con.execute(to_duck(sql).replace("{M0}", f"{m0:%Y-%m-%d}").replace("{ML}", f"{ml:%Y-%m-%d}").replace("{M1}", f"{m1:%Y-%m-%d}")).fetchone()
            got = con.execute(f"SELECT tx_id FROM tx WHERE {cond}").df().tx_id
            miss = (~true.tx_id.isin(got)).sum(); extra = (~got.isin(true.tx_id)).sum()
            rows.append({"月": str(m), "書き方": name, "正解の件数": len(true), "件数": int(n), "正解の合計": int(true.amount.sum()), "合計": int(total),
                         "落ちた行": int(miss), "余分な行": int(extra), "落ちた行(%)": round(miss / len(true) * 100, 3),
                         "余分な行(%)": round(extra / len(true) * 100, 3), "合計の差(%)": round((total / true.amount.sum() - 1) * 100, 3)})
    return pd.DataFrame(rows)


def main():
    df = make(); con = duckdb.connect(); con.register("tx_df", df); con.execute("CREATE TABLE tx AS SELECT * FROM tx_df")
    r = evaluate(df, con); r.to_csv(RES / "by_month.csv", index=False)
    g = r.groupby("書き方", sort=False)
    tot_true = int(df.amount.sum())
    summ = pd.DataFrame({"落ちた行(%)・12か月平均": g["落ちた行(%)"].mean().round(2), "余分な行(%)・12か月平均": g["余分な行(%)"].mean().round(2),
                         "合計の差(%)・最小": g["合計の差(%)"].min().round(2), "合計の差(%)・最大": g["合計の差(%)"].max().round(2),
                         "正しい月の数": g.apply(lambda x: int(((x["落ちた行"] == 0) & (x["余分な行"] == 0)).sum())),
                         "12か月の合計÷年の合計": (g["合計"].sum() / tot_true).round(4)}).reset_index()
    summ.to_csv(RES / "nine_writings.csv", index=False)
    # 月末に取引が集まる度合いを変える
    sw = []
    for wgt in [1, 2, 3, 5]:
        d2 = make(wgt); c2 = duckdb.connect(); c2.register("tx_df", d2); c2.execute("CREATE TABLE tx AS SELECT * FROM tx_df")
        r2 = evaluate(d2, c2)
        for name, x in r2.groupby("書き方", sort=False):
            sw.append({"最終日の重み": wgt, "書き方": name, "落ちた行(%)": round(x["落ちた行(%)"].mean(), 2), "合計の差(%)": round(x["合計の差(%)"].mean(), 2)})
    sw = pd.DataFrame(sw); sw.to_csv(RES / "last_day_weight_sweep.csv", index=False)
    mar = r[r["月"] == "2025-12"]
    night = df[(df.ts_jst >= "2025-12-01 00:00") & (df.ts_jst < "2025-12-01 09:00")]
    summary = {"seed": SEED, "取引": len(df), "うち定期課金（毎月1日0:00:00）": int((df.kind == "定期課金").sum()), "期間": "2025-04〜2026-03",
               "最終日の重み（基本）": 2.0, "正しかった書き方": [n for n in summ[summ["正しい月の数"] == 12]["書き方"]],
               "ずれた書き方の数(9本中)": int((summ["正しい月の数"] < 12).sum()),
               "W2で落ちた行（12か月の合計）": int(r[r["書き方"].str.startswith("W2")]["落ちた行"].sum()),
               "W8で月の合計の差が0.5%を超えた月の数": int((r[r["書き方"].str.startswith("W8")]["合計の差(%)"].abs() > 0.5).sum()),
               "2025年12月": {x["書き方"]: {"落ちた行": int(x["落ちた行"]), "余分な行": int(x["余分な行"]), "合計の差(%)": float(x["合計の差(%)"])} for _, x in mar.iterrows()},
               "12/1 0:00〜9:00（日本時間）の取引が12月に占める割合(%)": round(len(night) / int(mar["正解の件数"].iloc[0]) * 100, 2)}
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); print(summ.to_string()); print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(sw.pivot(index="書き方", columns="最終日の重み", values="落ちた行(%)").to_string())


if __name__ == "__main__":
    main()
