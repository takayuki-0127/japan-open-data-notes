"""356 曜日の並びが違うだけで、前年同月比は何ポイント動くのか
架空の日次売上（曜日の型あり）と、内閣府の祝日の一覧で数える。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, GREEN, INK

SEED = 356
SRC = "架空の日次売上（作成者が乱数で作成、seed 356）。祝日は内閣府「国民の祝日」の一覧"

# ---------- カレンダー（2015〜2026年）と日の種類 ----------
hol = pd.read_csv(DATA / "syukujitsu_utf8.csv", header=0, names=["d", "name"])
hol["d"] = pd.to_datetime(hol["d"])
cal = pd.DataFrame({"d": pd.date_range("2015-01-01", "2026-12-31")})
cal["dow"] = cal["d"].dt.dayofweek                       # 0=月 … 6=日
cal["hol"] = cal["d"].isin(hol["d"])
cal["dtype"] = np.where(cal["hol"], 7, cal["dow"])       # 7=祝日・休日（曜日より優先）
cal["ym"] = cal["d"].dt.to_period("M")
NAMES = ["月", "火", "水", "木", "金", "土", "日", "祝"]

# ---------- 曜日の型（1日の売上の重み。月曜=1 を基準に置いた架空の値） ----------
PAT = {
    "小売（週末型）":   [1.00, 0.95, 0.95, 1.00, 1.15, 1.50, 1.40, 1.35],
    "法人向け（平日型）": [1.00, 1.00, 1.00, 1.00, 1.00, 0.15, 0.05, 0.05],
    "飲食（金土型）":   [0.80, 0.85, 0.90, 1.00, 1.40, 1.50, 1.00, 1.10],
}
W = {k: np.array(v) for k, v in PAT.items()}
cnt = cal.groupby(["ym", "dtype"]).size().unstack(fill_value=0).reindex(columns=range(8), fill_value=0)
days = cnt.sum(axis=1)
biz = cnt[[0, 1, 2, 3, 4]].sum(axis=1)                    # 平日（祝日を除く）の数


def yoy(s):
    """月の系列 → 前年同月比（%）。2016年1月〜"""
    return (s / s.shift(12) - 1).dropna() * 100


# ---------- ① 曜日の並びだけで動く幅（成長0・揺れ0） ----------
rows, series = [], {}
for k, w in W.items():
    m = cnt.values @ w                                    # 月の売上（重みの合計）
    m = pd.Series(m, index=cnt.index)
    variants = {
        "補正なし": m,
        "1日あたり": m / days,
        "平日1日あたり": m / biz,
        "曜日の型で割る": m / (cnt.values @ w),
    }
    for name, s in variants.items():
        y = yoy(s)
        series[(k, name)] = y
        feb = y[y.index.month == 2]
        rows.append({"型": k, "補正": name, "最小": y.min(), "最大": y.max(), "幅": y.max() - y.min(),
                     "標準偏差": y.std(ddof=0), "1ポイント以上動いた月の割合": (y.abs() >= 1).mean() * 100,
                     "2月（うるう年）": feb[feb.index.year.isin([2016, 2020, 2024])].mean(),
                     "2月（うるう年の翌年）": feb[feb.index.year.isin([2017, 2021, 2025])].mean(),
                     "うるう年がらみの2月を除く最大の絶対値": y[~((y.index.month == 2) & y.index.year.isin([2016, 2017, 2020, 2021, 2024, 2025]))].abs().max()})
cal_only = pd.DataFrame(rows)
cal_only.round(3).to_csv(RES / "calendar_only_yoy.csv", index=False)
pd.DataFrame({f"{k}": series[(k, "補正なし")] for k in W}).round(3).rename_axis("ym").to_csv(RES / "calendar_only_series.csv")

# いちばん動いた月と、そのときの土日祝の数
y0 = series[("小売（週末型）", "補正なし")]
top = y0.abs().sort_values(ascending=False).head(6).index
ex = []
for p in top:
    q = p - 12
    ex.append({"月": str(p), "前年同月比": y0[p], "土日祝の日数": int(cnt.loc[p, [5, 6, 7]].sum()), "前年の土日祝の日数": int(cnt.loc[q, [5, 6, 7]].sum()),
               "日数": int(days[p]), "前年の日数": int(days[q])})
pd.DataFrame(ex).round(2).to_csv(RES / "largest_swings_retail.csv", index=False)

# ---------- ② 揺れと本当の伸びがある日次売上で、補正を比べる ----------
def simulate(w, rng, sigma=0.06):
    n = len(cal)
    t = np.arange(len(cnt))
    true_yoy = 0.02 + 0.04 * np.sin(2 * np.pi * t / 40)                   # 本当の前年同月比：−2%〜+6% をゆっくり動く
    level = np.ones(len(cnt))
    for i in range(12, len(cnt)):
        level[i] = level[i - 12] * (1 + true_yoy[i])
    season = 1 + 0.08 * np.sin(2 * np.pi * (cnt.index.month - 3) / 12)   # 毎年同じ季節の形
    mi = cal["ym"].map({p: i for i, p in enumerate(cnt.index)}).values
    daily = 1000 * level[mi] * season[mi] * w[cal["dtype"].values] * rng.lognormal(-sigma ** 2 / 2, sigma, n)
    return daily, pd.Series(true_yoy * 100, index=cnt.index)


def est_weights(daily, upto, months=24):
    """その月より前の24か月の日次データから、日の種類ごとの重みを推定（対数の回帰：月の水準＋日の種類）"""
    idx = list(cnt.index)
    j = idx.index(upto)
    use = idx[max(0, j - months):j]
    sub = cal[cal["ym"].isin(use)]
    y = np.log(daily[sub.index])
    mcode = pd.Categorical(sub["ym"]).codes
    X = np.zeros((len(sub), mcode.max() + 1 + 7))
    X[np.arange(len(sub)), mcode] = 1
    dt = sub["dtype"].values
    for c in range(1, 8):
        X[dt == c, mcode.max() + c] = 1
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    return np.exp(np.r_[0, beta[mcode.max() + 1:]])


sim_rows, keep = [], {}
for k, w in W.items():
    for rep in range(200):
        rng = np.random.default_rng([SEED, list(W).index(k), rep])
        daily, truth = simulate(w, rng)
        m = pd.Series(daily).groupby(cal["ym"].values).sum()
        est = {}
        raw = yoy(m)
        est["補正なし"] = raw
        est["1日あたり"] = yoy(m / days)
        est["平日1日あたり"] = yoy(m / biz)
        adj = []
        for p in raw.index:                               # 2017年1月〜：重みを過去24か月から推定
            if p < pd.Period("2017-01"):
                adj.append(np.nan); continue
            wh = est_weights(daily, p)
            adj.append(((m[p] / (cnt.loc[p].values @ wh)) / (m[p - 12] / (cnt.loc[p - 12].values @ wh)) - 1) * 100)
        est["曜日の型で割る（重みは過去24か月から推定）"] = pd.Series(adj, index=raw.index)
        est["曜日の型で割る（本当の重み）"] = yoy(m / (cnt.values @ w))
        ok = raw.index >= pd.Period("2017-01")
        for name, s in est.items():
            tr = truth.reindex(raw.index)
            e = (s - tr)[ok]
            sim_rows.append({"型": k, "補正": name, "rep": rep, "rmse": np.sqrt((e ** 2).mean()), "max_abs": e.abs().max(),
                             "sign_wrong": (np.sign(s[ok]) != np.sign(tr[ok])).mean() * 100})
        if rep == 0:
            keep[k] = (truth, est, daily)
sim = pd.DataFrame(sim_rows)
sim_sum = sim.groupby(["型", "補正"], sort=False).agg(RMSE=("rmse", "mean"), 最大のずれ=("max_abs", "mean"), 向きが逆の月の割合=("sign_wrong", "mean")).reset_index()
sim_sum.round(3).to_csv(RES / "noisy_correction_errors.csv", index=False)

# ---------- ③ SQL で同じ補正（DuckDB で実行。T-SQL 版は sql/ に置いた・未検証） ----------
truth, est, daily = keep["小売（週末型）"]
con = duckdb.connect(); con.execute("SET threads=1")
sales = pd.DataFrame({"d": cal["d"], "amount": daily})
calendar = pd.DataFrame({"d": cal["d"], "dtype": cal["dtype"]})
weights = pd.DataFrame({"dtype": range(8), "w": W["小売（週末型）"]})
for name, df in [("sales", sales), ("calendar", calendar), ("weights", weights)]:
    con.register(name + "_df", df); con.execute(f"CREATE TABLE {name} AS SELECT * FROM {name}_df")
q = (SQL / "01_adjusted_yoy_duckdb.sql").read_text(encoding="utf-8")
out = con.execute(q).df()
out["ym"] = pd.PeriodIndex(out["ym"], freq="M")
chk = out.set_index("ym")["yoy_adj"].dropna()
ref = est["曜日の型で割る（本当の重み）"]
assert np.allclose(chk.values, ref.loc[chk.index].values, atol=1e-9), "SQL と pandas が合わない"
out.assign(ym=out["ym"].astype(str)).round(4).to_csv(RES / "sql_adjusted_yoy_retail.csv", index=False)

# ---------- 図 ----------
fig, ax = plt.subplots(figsize=(9, 4.2))
for (k, c) in zip(W, [BLUE, ORANGE, GREEN]):
    y = series[(k, "補正なし")]
    ax.plot(y.index.to_timestamp(), y.values, color=c, lw=1.4, label=k)
ax.axhline(0, color=INK, lw=0.8)
ax.set_ylabel("前年同月比（%）"); ax.set_title("売上の力が同じでも、曜日の並びだけで前年同月比は動く")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.08))
save(fig, "a356_calendar_only.png", "成長0・揺れ0の架空の売上。" + SRC, y=-0.08)

fig, ax = plt.subplots(figsize=(9, 4.2))
names = ["補正なし", "1日あたり", "平日1日あたり", "曜日の型で割る"]
x = np.arange(len(W)); bw = 0.2
for i, (n, c) in enumerate(zip(names, [GRAY, "#a9c9ef", ORANGE, BLUE])):
    v = [cal_only[(cal_only["型"] == k) & (cal_only["補正"] == n)]["幅"].iloc[0] for k in W]
    b = ax.bar(x + (i - 1.5) * bw, v, bw, color=c, label=n)
    for xi, vi in zip(x + (i - 1.5) * bw, v):
        ax.text(xi, vi + 0.15, f"{vi:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(list(W)); ax.set_ylabel("前年同月比の幅（最大−最小、ポイント）")
ax.set_title("割り方で、曜日の並びによる揺れはどこまで消えるか"); ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
save(fig, "a356_range_by_correction.png", "成長0・揺れ0の架空の売上（2016年1月〜2026年12月の132か月）。" + SRC, y=-0.1)

fig, ax = plt.subplots(figsize=(9, 4.4))
tr = truth[truth.index >= pd.Period("2017-01")]
ax.plot(tr.index.to_timestamp(), tr.values, color=INK, lw=2, label="本当の伸び")
r0 = est["補正なし"]; r0 = r0[r0.index >= pd.Period("2017-01")]
ax.plot(r0.index.to_timestamp(), r0.values, color=GRAY, lw=1.1, label="補正なし")
a = est["曜日の型で割る（重みは過去24か月から推定）"].dropna()
ax.plot(a.index.to_timestamp(), a.values, color=BLUE, lw=1.3, label="曜日の型で割る（重みは過去24か月から推定）")
ax.set_ylabel("前年同月比（%）"); ax.set_title("揺れのある売上でも、補正すると本当の伸びに近づく（小売・週末型の1回分）")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.08))
save(fig, "a356_noisy_example.png", "1日の売上に6%の揺れを入れた架空の売上。" + SRC, y=-0.08)

main = {"calendar_only": cal_only.round(3).to_dict("records"), "noisy": sim_sum.round(3).to_dict("records"),
        "largest_swings_retail": pd.DataFrame(ex).round(2).to_dict("records"),
        "months": int(len(y0)), "holidays_used": int(cal["hol"].sum())}
json.dump(main, open(RES / "a356_main.json", "w"), ensure_ascii=False, indent=1)
print(cal_only.round(2).to_string()); print(sim_sum.round(2).to_string()); print(pd.DataFrame(ex).round(2).to_string())
