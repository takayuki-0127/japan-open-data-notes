"""315 1年分の保険料を、月ごとの売上にどう分けるか
架空の保険契約（1年契約・始期が月の途中）で、日割り・12分の1・24分の1 の3つの分け方を比べる"""
import json, re
import numpy as np, pandas as pd, duckdb
from common import SQL, RES

SEED = 315
FY = pd.date_range("2025-04-01", "2026-03-01", freq="MS")   # 比べる12か月（2025年度）
FY_END = pd.Timestamp("2026-04-01")


def make(day_pattern="ばらばら", march_boost=1.0, seed=SEED, n_month=2500):
    """day_pattern＝始期が月のどこに集まるか。march_boost＝3月の契約が何倍あるか"""
    rng = np.random.default_rng(seed)
    rows = []
    for ms in pd.date_range("2024-01-01", "2026-03-01", freq="MS"):
        nd = ms.days_in_month
        n = int(n_month * (1.6 if ms.month == 4 else 1.0) * (march_boost if (ms.month == 3 and ms.year == 2026) else 1.0) * 1.008 ** ((ms.year - 2024) * 12 + ms.month - 1))
        w = np.ones(nd)
        if day_pattern == "月初に集まる": w[0] = nd          # 1日始期が約半分
        if day_pattern == "月末に集まる": w[-3:] = nd / 3     # 最後の3日で約半分
        day = rng.choice(nd, n, p=w / w.sum())
        rows.append(pd.DataFrame({"start_date": ms + pd.to_timedelta(day, unit="D"), "premium": rng.lognormal(10.9, 0.5, n).round(-1).astype(int)}))
    p = pd.concat(rows, ignore_index=True)
    p["end_date"] = p.start_date + pd.DateOffset(years=1)
    p.insert(0, "policy_id", np.arange(1, len(p) + 1))
    months = pd.DataFrame({"month_start": pd.date_range("2024-01-01", "2027-04-01", freq="MS")})
    months["next_month_start"] = months.month_start + pd.DateOffset(months=1)
    return p[["policy_id", "start_date", "end_date", "premium"]], months


def blocks():
    out = {}
    for b in re.split(r"-- name: ", (SQL / "earned.sql").read_text(encoding="utf-8"))[1:]:
        name, body = b.split("\n", 1); out[name.strip()] = body.strip()
    return out


def to_duck(q):
    return q.replace("dbo.", "").replace("DATEDIFF(day,", "date_diff('day',").replace("DATEDIFF(month,", "date_diff('month',").replace("AS FLOAT", "AS DOUBLE")


def measure(p, months):
    con = duckdb.connect()
    for n, df in [("policies", p), ("months", months)]:
        df = df.copy()
        for c in df.columns:
            if "date" in c or "month" in c: df[c] = df[c].dt.date
        con.register(n + "_df", df); con.execute(f"CREATE TABLE {n} AS SELECT * FROM {n}_df")
    out = None
    for name, sql in blocks().items():
        d = con.execute(to_duck(sql)).df().rename(columns={"earned": name}); d["month_start"] = pd.to_datetime(d.month_start)
        out = d if out is None else out.merge(d, on="month_start", how="outer")
    out = out.sort_values("month_start").fillna(0).reset_index(drop=True)
    # 日割りを pandas で別に計算して照合する
    term = (p.end_date - p.start_date).dt.days
    chk = []
    for ms, ne in zip(FY, list(FY[1:]) + [FY_END]):
        ov = (p.end_date.clip(upper=ne) - p.start_date.clip(lower=ms)).dt.days.clip(lower=0)
        chk.append((p.premium * ov / term).sum())
    fy = out[out.month_start.isin(FY)].reset_index(drop=True)
    assert np.allclose(fy["日割り"].values, chk, rtol=1e-9), "日割りが合わない"
    written = float(p.premium.sum())
    totals = {c: float(out[c].sum()) for c in out.columns[1:]}       # 全期間で足すと、もらった保険料に合うか
    # 2026年3月末の未経過保険料＝もらった保険料 − 3月までに売上にした分
    upto = out[out.month_start < FY_END]
    unearned = {c: written - float(upto[c].sum()) for c in out.columns[1:]}
    return fy, written, totals, unearned


def main():
    p, months = make()
    fy, written, totals, unearned = measure(p, months)
    fy["12分の1の差(%)"] = ((fy.iloc[:, 2] / fy["日割り"] - 1) * 100).round(3); fy["24分の1の差(%)"] = ((fy.iloc[:, 3] / fy["日割り"] - 1) * 100).round(3)
    fy.round(1).to_csv(RES / "fy2025_by_month.csv", index=False)
    sc = []
    for label, kw in [("ばらばら（基本）", {}), ("月初に集まる", dict(day_pattern="月初に集まる")), ("月末に集まる", dict(day_pattern="月末に集まる")),
                      ("3月の契約が2倍", dict(march_boost=2.0)), ("月末に集まる＋3月が2倍", dict(day_pattern="月末に集まる", march_boost=2.0))]:
        f2, w2, t2, u2 = measure(*make(**kw))
        k12, k24 = f2.columns[2], f2.columns[3]
        d12 = (f2[k12] / f2["日割り"] - 1) * 100; d24 = (f2[k24] / f2["日割り"] - 1) * 100
        sc.append({"置き方": label, "月の売上の差・12分の1（最大%）": round(d12.abs().max(), 2), "月の売上の差・24分の1（最大%）": round(d24.abs().max(), 2),
                   "年度の売上の差・12分の1(%)": round((f2[k12].sum() / f2["日割り"].sum() - 1) * 100, 2), "年度の売上の差・24分の1(%)": round((f2[k24].sum() / f2["日割り"].sum() - 1) * 100, 2),
                   "未経過保険料の差・12分の1(%)": round((u2[k12] / u2["日割り"] - 1) * 100, 2), "未経過保険料の差・24分の1(%)": round((u2[k24] / u2["日割り"] - 1) * 100, 2),
                   "未経過保険料（日割り、億円）": round(u2["日割り"] / 1e8, 2),
                   "全期間の合計は合うか": all(abs(v - w2) < 1e-3 * 1 + 1e-9 * w2 for v in t2.values())})
    sc = pd.DataFrame(sc); sc.to_csv(RES / "scenarios.csv", index=False)
    # 1件の契約で見る（始期 5月20日、保険料 120,000円）
    one = pd.DataFrame({"policy_id": [1], "start_date": [pd.Timestamp("2025-05-20")], "end_date": [pd.Timestamp("2026-05-20")], "premium": [120000]})
    con = duckdb.connect(); o = one.copy(); o["start_date"] = o.start_date.dt.date; o["end_date"] = o.end_date.dt.date
    mm = months.copy(); mm["month_start"] = mm.month_start.dt.date; mm["next_month_start"] = mm.next_month_start.dt.date
    con.register("o", o); con.register("mm", mm); con.execute("CREATE TABLE policies AS SELECT * FROM o"); con.execute("CREATE TABLE months AS SELECT * FROM mm")
    ex = None
    for name, sql in blocks().items():
        d = con.execute(to_duck(sql)).df().rename(columns={"earned": name}); ex = d if ex is None else ex.merge(d, on="month_start", how="outer")
    ex = ex.sort_values("month_start").fillna(0).round(0); ex.to_csv(RES / "one_policy.csv", index=False)
    k12, k24 = fy.columns[2], fy.columns[3]
    summary = {"seed": SEED, "契約": len(p), "もらった保険料の合計（億円）": round(written / 1e8, 2),
               "2025年度の売上（億円）": {c: round(float(fy[c].sum()) / 1e8, 3) for c in ["日割り", k12, k24]},
               "月の売上の差(%)": {"12分の1": [float(fy["12分の1の差(%)"].min()), float(fy["12分の1の差(%)"].max())], "24分の1": [float(fy["24分の1の差(%)"].min()), float(fy["24分の1の差(%)"].max())]},
               "2026年3月末の未経過保険料（億円）": {c: round(v / 1e8, 3) for c, v in unearned.items()},
               "未経過保険料の差(%)": {c: round((unearned[c] / unearned["日割り"] - 1) * 100, 2) for c in [k12, k24]},
               "全期間で足した合計 − もらった保険料（円）": {c: round(v - written, 2) for c, v in totals.items()}}
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); print(fy.round(1).to_string()); print(sc.T.to_string()); print(ex.to_string()); print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
