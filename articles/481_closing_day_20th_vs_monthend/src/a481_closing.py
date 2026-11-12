"""481 「20日締め」と「月末締め」で、月の売上はどれだけ動くのか（架空の日次売上・3年分）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "架空の日次売上（作成者が乱数で作成、seed 481）、内閣府「国民の祝日」"
hol = pd.to_datetime(pd.read_csv(DATA / "syukujitsu_utf8.csv", encoding="utf-8").iloc[:, 0])
HOL = set(hol[(hol >= "2022-01-01") & (hol <= "2026-12-31")].dt.date)
days = pd.date_range("2022-12-21", "2025-12-31", freq="D")
dow = days.dayofweek.values
is_hol = np.array([d.date() in HOL for d in days])
SEASON = np.array([0.92, 0.90, 1.02, 1.00, 0.98, 0.97, 1.03, 1.00, 0.97, 1.00, 1.03, 1.18])
# 2つの型：小売型（週末が多い）、法人向け型（平日だけ、祝日は休み）
W = {"retail": np.array([0.9, 0.9, 0.9, 0.95, 1.1, 1.45, 1.35]),
     "b2b": np.array([1.05, 1.0, 1.0, 1.0, 1.15, 0.0, 0.0])}


def daily(kind, rng, step=None, noise=0.08):
    w = W[kind][dow].copy()
    if kind == "b2b":
        w[is_hol] = 0.0
    else:
        w[is_hol] = 1.35
    t = (days - days[0]).days.values / 365.25
    lvl = 1_000_000 * 1.03 ** t * SEASON[days.month.values - 1]
    if step is not None:
        lvl = lvl * np.where(days >= pd.Timestamp(step), 1.10, 1.0)
    x = lvl * w * np.exp(rng.normal(0, noise, len(days)) - noise ** 2 / 2)
    return pd.DataFrame({"d": days, "sales": np.round(x).astype(np.int64)})


def monthly(df):
    """月末締め（暦月）と20日締め（前月21日〜当月20日）を DuckDB で集計"""
    q = """
    WITH t AS (SELECT d, sales,
                      date_trunc('month', d) AS m_end,
                      date_trunc('month', d - INTERVAL 20 DAY) + INTERVAL 1 MONTH AS m_20
               FROM df)
    SELECT a.m, a.v AS month_end, b.v AS close20, a.n AS days_end, b.n AS days_20
    FROM (SELECT m_end AS m, SUM(sales) v, COUNT(*) n FROM t GROUP BY 1) a
    JOIN (SELECT m_20 AS m, SUM(sales) v, COUNT(*) n FROM t GROUP BY 1) b USING (m)
    ORDER BY a.m"""
    out = duckdb.sql(q).df()
    out["m"] = pd.to_datetime(out["m"])
    return out[(out.m >= "2023-01-01") & (out.m <= "2025-12-01")].reset_index(drop=True)


def check_numpy(df, out):
    d = df.d
    lab = (d - pd.Timedelta(days=20)).dt.to_period("M").dt.to_timestamp() + pd.offsets.MonthBegin(1)
    s = df.groupby(lab).sales.sum()
    assert all(s.loc[out.m].values == out.close20.values)
    s2 = df.groupby(d.dt.to_period("M").dt.to_timestamp()).sales.sum()
    assert all(s2.loc[out.m].values == out.month_end.values)


def yoy(out):
    o = out.set_index("m")
    r = (o[["month_end", "close20"]] / o[["month_end", "close20"]].shift(12) - 1) * 100
    return r.dropna()


def metrics(out):
    gap = (out.close20 / out.month_end - 1) * 100
    y = yoy(out)
    flip = int((np.sign(y.month_end) != np.sign(y.close20)).sum())
    return {"gap_mean_abs": float(gap.abs().mean()), "gap_max_abs": float(gap.abs().max()),
            "yoy_diff_mean_abs": float((y.month_end - y.close20).abs().mean()),
            "yoy_diff_max_abs": float((y.month_end - y.close20).abs().max()), "flip": flip, "n_yoy": len(y)}


res = {}
ex = {}
for kind in ["retail", "b2b"]:
    rng = np.random.default_rng(481)
    df = daily(kind, rng)
    out = monthly(df)
    check_numpy(df, out)
    out.to_csv(RES / f"monthly_{kind}.csv", index=False)
    if kind == "retail":
        df.to_csv(DATA / "fictional_daily_sales_retail.csv", index=False)
    ex[kind] = out
    res[kind] = metrics(out)
    # 営業日数（売上>0の日）
    bd_end = df.assign(m=df.d.dt.to_period("M").dt.to_timestamp()).groupby("m").sales.apply(lambda s: int((s > 0).sum()))
    lab = (df.d - pd.Timedelta(days=20)).dt.to_period("M").dt.to_timestamp() + pd.offsets.MonthBegin(1)
    bd_20 = df.groupby(lab).sales.apply(lambda s: int((s > 0).sum()))
    bd = pd.DataFrame({"days_end": out.set_index("m").days_end, "days_20": out.set_index("m").days_20,
                       "bdays_end": bd_end.loc[out.m].values, "bdays_20": bd_20.loc[out.m].values})
    bd.to_csv(RES / f"days_{kind}.csv")
    res[kind]["bdays_range_end"] = [int(bd.bdays_end.min()), int(bd.bdays_end.max())]
    res[kind]["bdays_range_20"] = [int(bd.bdays_20.min()), int(bd.bdays_20.max())]

# 揺れを変えて500回：前年同月比の向きが逆になる月の数
rep = []
for kind in ["retail", "b2b"]:
    for trend in [0.0, 0.03]:
        fl = []
        for s in range(500):
            rng = np.random.default_rng(10_000 + s)
            df = daily(kind, rng)
            if trend == 0.0:
                t = (df.d - df.d.iloc[0]).dt.days.values / 365.25
                df["sales"] = np.round(df.sales / 1.03 ** t).astype(np.int64)
            fl.append(metrics(monthly(df))["flip"])
        fl = np.array(fl)
        rep.append({"kind": kind, "trend": trend, "flip_mean": fl.mean(), "flip_p90": float(np.percentile(fl, 90)),
                    "share_any_flip": float((fl > 0).mean())})
rep = pd.DataFrame(rep); rep.to_csv(RES / "yoy_flip_500.csv", index=False)

# 値上げ（2024年10月1日から+10%）が数字に出る割合
rng = np.random.default_rng(481)
base = monthly(daily("retail", np.random.default_rng(481), noise=0.0))
stp = monthly(daily("retail", np.random.default_rng(481), step="2024-10-01", noise=0.0))
sh = pd.DataFrame({"m": base.m, "month_end": (stp.month_end / base.month_end - 1) / 0.10 * 100,
                   "close20": (stp.close20 / base.close20 - 1) / 0.10 * 100})
sh = sh[(sh.m >= "2024-08-01") & (sh.m <= "2025-01-01")]
sh.to_csv(RES / "step_share.csv", index=False)
res["step_share"] = sh.round(1).astype({"m": str}).to_dict("records")
# 年の合計（暦年 vs 前年12月21日〜当年12月20日）
yr = []
for kind in ["retail", "b2b"]:
    o = ex[kind]
    for y in [2023, 2024, 2025]:
        a = o[o.m.dt.year == y].month_end.sum(); b = o[o.m.dt.year == y].close20.sum()
        yr.append({"kind": kind, "year": y, "calendar": int(a), "close20": int(b), "diff_pct": (b / a - 1) * 100})
yr = pd.DataFrame(yr); yr.to_csv(RES / "annual.csv", index=False)
res["annual_diff_pct"] = yr.round(2).to_dict("records")
res["flip_500"] = rep.round(3).to_dict("records")
json.dump(res, open(RES / "a481_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：月の売上（小売型・法人向け型）
fig, axs = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True)
for ax, kind, ttl in zip(axs, ["retail", "b2b"], ["小売型（週末に多い・祝日も営業）", "法人向け型（平日だけ・祝日は休み）"]):
    o = ex[kind]
    ax.plot(o.m, o.month_end / 1e6, color=BLUE, lw=2, label="月末締め（暦月）")
    ax.plot(o.m, o.close20 / 1e6, color=ORANGE, lw=2, ls="--", label="20日締め（前月21日〜当月20日）")
    ax.set_title(ttl, loc="left", fontsize=11); ax.set_ylabel("月の売上（百万円）")
    ax.grid(axis="y", alpha=.3)
axs[0].legend(frameon=False, fontsize=9)
fig.suptitle("同じ日次売上を、2つの締め日で月に集計する", x=0.01, ha="left", fontsize=13)
save(fig, "a481_monthly.png", SRC)

# 図2：前年同月比（法人向け型、2024〜2025年）
fig, ax = plt.subplots(figsize=(10, 4.4))
y = yoy(ex["b2b"])
xs = np.arange(len(y)); w = 0.4
ax.bar(xs - w / 2, y.month_end, w, color=BLUE, label="月末締め")
ax.bar(xs + w / 2, y.close20, w, color=ORANGE, label="20日締め")
for i, (a, b) in enumerate(zip(y.month_end, y.close20)):
    if np.sign(a) != np.sign(b):
        ax.annotate("向きが逆", (i, max(a, b) + 0.6), ha="center", fontsize=8, color=INK)
ax.axhline(0, color=INK, lw=.8)
ax.set_xticks(xs); ax.set_xticklabels([f"{m.year % 100}/{m.month}" for m in y.index], fontsize=8, rotation=45)
ax.set_ylabel("前年同月比（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("法人向け型の前年同月比：締め日で向きまで変わる月がある", loc="left")
save(fig, "a481_yoy_b2b.png", SRC)

# 図3：営業日数と値上げの出方
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
bd = pd.read_csv(RES / "days_b2b.csv", parse_dates=["m"])
bd = bd[bd.m.dt.year == 2025]
xs = np.arange(len(bd))
axs[0].bar(xs - .2, bd.bdays_end, .4, color=BLUE, label="月末締め")
axs[0].bar(xs + .2, bd.bdays_20, .4, color=ORANGE, label="20日締め")
axs[0].set_xticks(xs); axs[0].set_xticklabels([f"{m}月" for m in bd.m.dt.month], fontsize=8)
axs[0].set_ylim(14, 24); axs[0].set_ylabel("営業日数（日）"); axs[0].legend(frameon=False, fontsize=8)
axs[0].set_title("法人向け型の営業日数（2025年）", loc="left", fontsize=11)
xs = np.arange(len(sh))
axs[1].bar(xs - .2, sh.month_end, .4, color=BLUE, label="月末締め")
axs[1].bar(xs + .2, sh.close20, .4, color=ORANGE, label="20日締め")
axs[1].set_xticks(xs); axs[1].set_xticklabels([f"{m.year % 100}/{m.month}" for m in sh.m], fontsize=8)
axs[1].set_ylabel("値上げ+10%のうち月の数字に出た割合（%）"); axs[1].set_ylim(0, 110)
axs[1].set_title("10月1日の値上げが数字に出る月", loc="left", fontsize=11)
save(fig, "a481_days_and_step.png", SRC)
print(json.dumps({k: res[k] for k in ["retail", "b2b"]}, ensure_ascii=False))
print(rep.round(2).to_string()); print(sh.round(1).to_string()); print(yr.round(2).to_string())
