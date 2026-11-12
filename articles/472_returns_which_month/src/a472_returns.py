"""472 返品を「売れた月」に戻すか「返ってきた月」で引くかで、月の売上はどれだけ変わるのか（seed 472）"""
import json, numpy as np, pandas as pd, duckdb, matplotlib.pyplot as plt
from common import *
SEED = 472; SRC = "架空の売上と返品（seed 472）"
D0, D1 = pd.Timestamp("2023-10-01"), pd.Timestamp("2025-12-31")      # 売上は2023年10月〜2025年12月。見るのは2024年1月〜2025年12月
DAYS = pd.date_range(D0, D1); ND = len(DAYS)

def make(rng, rate=0.08, med=10.0, sale_boost=1.6, sale_rate_mult=1.8, per_day=450):
    """日ごとの注文を作る。7月と12月の後半はセール（件数が増え、返品もされやすい）"""
    mon, day, dow = DAYS.month.values, DAYS.day.values, DAYS.dayofweek.values
    is_sale = (np.isin(mon, [7, 12]) & (day >= 16))
    lam = per_day * np.where(dow >= 5, 1.25, 1.0) * np.where(is_sale, sale_boost, 1.0) * (1 + 0.04 * (np.arange(ND) / 365))
    n = rng.poisson(lam); d = np.repeat(np.arange(ND), n); N = len(d)
    amt = np.round(np.exp(rng.normal(8.6, 0.7, N)), -1)                  # 1件 5千円前後
    p = rate * np.where(is_sale[d], sale_rate_mult, 1.0)
    ret = rng.random(N) < p
    delay = np.ceil(rng.gamma(2.0, med / 1.678, N)).astype(int)          # 売れてから返るまでの日数（中央値が med 日くらい）
    s = pd.DataFrame({"order_id": np.arange(N), "sale_date": DAYS[d], "amount": amt})
    r = pd.DataFrame({"order_id": np.arange(N)[ret], "return_date": DAYS[d[ret]] + pd.to_timedelta(delay[ret], "D"), "amount": amt[ret]})
    return s, r, is_sale

def monthly(s, r, as_of=None):
    """月ごとの 売上（返品を見ない）／①売れた月に戻す／②返ってきた月で引く"""
    if as_of is not None: r = r[r.return_date <= as_of]
    sm = s.sale_date.dt.to_period("M"); gross = s.amount.groupby(sm).sum()
    rs = r.merge(s[["order_id", "sale_date"]], on="order_id")
    by_sale = rs.amount.groupby(rs.sale_date.dt.to_period("M")).sum().reindex(gross.index, fill_value=0)
    by_ret = r.amount.groupby(r.return_date.dt.to_period("M")).sum().reindex(gross.index, fill_value=0)
    return pd.DataFrame({"gross": gross, "net_sale_month": gross - by_sale, "net_return_month": gross - by_ret})

rng = np.random.default_rng(SEED); s, r, is_sale = make(rng); res = {}
M = monthly(s, r); W = M.loc["2024-01":"2025-12"].copy()
res["n_orders"] = int(len(s)); res["n_returns"] = int(len(r)); res["return_rate_count"] = float(len(r) / len(s))
res["return_rate_amount"] = float(r.amount.sum() / s.amount.sum()); res["delay_median_days"] = float((r.return_date - r.merge(s, on="order_id").sale_date.values).dt.days.median())
dl = (r.return_date.values - r.merge(s, on="order_id").sale_date.values).astype("timedelta64[D]").astype(int)
res["delay_p90_days"] = float(np.percentile(dl, 90)); res["share_return_next_month_or_later"] = float((r.return_date.dt.to_period("M").values != r.merge(s, on="order_id").sale_date.dt.to_period("M").values).mean())

# ---- SQL（DuckDB）と一致するか ----
con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", s); con.register("returns", r)
q = [x.strip() for x in open(SQL / "01_returns_tsql.sql", encoding="utf-8").read().split(";") if "SELECT" in x]
a = con.execute(q[0]).df().set_index("ym").net_by_sale_month; b = con.execute(q[1]).df().set_index("ym").net_by_return_month
ix = [p.year * 100 + p.month for p in M.index]
assert np.allclose(a.loc[ix].values, M.net_sale_month.values) and np.allclose(b.loc[ix].values, M.net_return_month.values)
res["sql_check"] = "DuckDB の結果が pandas と一致（27か月）"

# ---- 1. 月ごとの差 ----
W["diff_pct"] = (W.net_return_month / W.net_sale_month - 1) * 100          # ②が①より何%大きいか
W["gross_over_pct"] = (W.gross / W.net_sale_month - 1) * 100
for c in ["gross", "net_sale_month", "net_return_month"]: W["yoy_" + c] = (W[c] / W[c].shift(12) - 1) * 100
W["yoy_gap_pt"] = W.yoy_net_return_month - W.yoy_net_sale_month
W.reset_index().rename(columns={"sale_date": "ym"}).to_csv(RES / "monthly_three_ways.csv", index=False)
res["diff_pct"] = {"mean_abs": float(W.diff_pct.abs().mean()), "max": float(W.diff_pct.max()), "min": float(W.diff_pct.min()),
                   "max_month": str(W.diff_pct.idxmax()), "min_month": str(W.diff_pct.idxmin()),
                   "by_month_2025": {str(k): round(float(v), 2) for k, v in W.loc["2025-01":"2025-12"].diff_pct.items()}}
res["gross_over_pct_mean"] = float(W.gross_over_pct.mean())
y = W.loc["2025-01":"2025-12"]
res["yoy_gap_pt"] = {"mean_abs": float(y.yoy_gap_pt.abs().mean()), "max_abs": float(y.yoy_gap_pt.abs().max())}
res["year_total_diff_pct_2025"] = float((y.net_return_month.sum() / y.net_sale_month.sum() - 1) * 100)
# セールの月と翌月の前月比（見かけの落ち込み）
mom = lambda c, a, b: float((W.loc[b, c] / W.loc[a, c] - 1) * 100)
res["mom_after_sale"] = {f"{a}->{b}": {"sale_month": mom("net_sale_month", a, b), "return_month": mom("net_return_month", a, b), "gross": mom("gross", a, b)}
                         for a, b in [("2024-07", "2024-08"), ("2024-12", "2025-01"), ("2025-07", "2025-08")]}
res["sale_month_diff_pct"] = {m: float(W.loc[m, "diff_pct"]) for m in ["2024-07", "2024-08", "2024-12", "2025-01", "2025-07", "2025-08", "2025-12"]}

# ---- 2. 締めたあとに、①の過去の月が動く ----
rows = []
for m in pd.period_range("2024-01", "2025-09", freq="M"):
    end = m.to_timestamp("M"); fin = M.loc[m, "net_sale_month"]
    for k in [0, 5, 10, 20, 31, 45, 62, 92]:
        v = monthly(s[s.sale_date.dt.to_period("M") == m], r, as_of=end + pd.Timedelta(days=k)).net_sale_month.iloc[0]
        rows.append({"ym": str(m), "days_after_month_end": k, "over_final_pct": (v / fin - 1) * 100, "amount_still_to_come": v - fin})
cl = pd.DataFrame(rows); cl.to_csv(RES / "restated_after_close.csv", index=False)
g = cl.groupby("days_after_month_end").over_final_pct
res["close"] = {int(k): {"mean": float(v.mean()), "max": float(v.max())} for k, v in g}
res["close_amount_day5_mean"] = float(cl[cl.days_after_month_end == 5].amount_still_to_come.mean())
# ある締め日（月末の5日後）に見ると、過去の何か月が、前回の締めから動いているか
moved = []
for m in pd.period_range("2024-06", "2025-09", freq="M"):
    t1 = m.to_timestamp("M") + pd.Timedelta(days=5); t0 = (m - 1).to_timestamp("M") + pd.Timedelta(days=5)
    a1 = monthly(s[s.sale_date <= t1], r, as_of=t1).net_sale_month; a0 = monthly(s[s.sale_date <= t0], r, as_of=t0).net_sale_month
    dd = (a1.reindex(a0.index) - a0)
    dd = dd[dd.index < m]                       # 前回の締めのときに、もう締まっていた月（前月まで）
    moved.append({"close": str(m), "months_changed": int((dd != 0).sum()), "months_changed_over_0.1pct": int(((dd / a0.reindex(dd.index)).abs() > 0.001).sum()),
                  "amount_changed": float(-dd.sum()), "amount_changed_pct_of_month": float(-dd.sum() / a1.loc[m] * 100)})
mv = pd.DataFrame(moved); mv.to_csv(RES / "months_moved_per_close.csv", index=False)
res["moved"] = {"months_changed_mean": float(mv.months_changed.mean()), "months_changed_over_0.1pct_mean": float(mv["months_changed_over_0.1pct"].mean()),
                "amount_changed_mean": float(mv.amount_changed.mean()), "amount_pct_of_month_mean": float(mv.amount_changed_pct_of_month.mean())}

# ---- 3. 返品率と、返るまでの日数を変える（各5回の平均） ----
rows = []
for rate in [0.02, 0.08, 0.20]:
    for med in [5, 10, 20, 40]:
        o = []
        for rep in range(5):
            rg = np.random.default_rng(SEED * 1000 + int(rate * 100) * 100 + med * 10 + rep); s2, r2, _ = make(rg, rate=rate, med=med, per_day=150)
            w = monthly(s2, r2).loc["2024-01":"2025-12"]; dp = (w.net_return_month / w.net_sale_month - 1) * 100
            yy = ((w.net_return_month / w.net_return_month.shift(12)) - (w.net_sale_month / w.net_sale_month.shift(12))).dropna() * 100
            o.append([dp.abs().mean(), dp.abs().max(), yy.abs().mean()])
        o = np.mean(o, axis=0); rows.append({"return_rate": rate, "median_delay_days": med, "mean_abs_diff_pct": o[0], "max_abs_diff_pct": o[1], "yoy_gap_mean_abs_pt": o[2]})
sw = pd.DataFrame(rows); sw.to_csv(RES / "sweep_rate_delay.csv", index=False)
res["sweep"] = {f"rate{int(a.return_rate*100)}_med{int(a.median_delay_days)}": [round(a.mean_abs_diff_pct, 2), round(a.max_abs_diff_pct, 2)] for a in sw.itertuples()}
# セールがない場合
rg = np.random.default_rng(SEED + 1); s3, r3, _ = make(rg, sale_boost=1.0, sale_rate_mult=1.0); w3 = monthly(s3, r3).loc["2024-01":"2025-12"]
d3 = (w3.net_return_month / w3.net_sale_month - 1) * 100; res["no_sale"] = {"mean_abs": float(d3.abs().mean()), "max_abs": float(d3.abs().max())}
json.dump(res, open(RES / "a472_main.json", "w"), ensure_ascii=False, indent=1)
s.head(2000).to_csv(DATA / "sales_sample.csv", index=False); r.head(500).to_csv(DATA / "returns_sample.csv", index=False)

# ---- 図 ----
fig, ax = plt.subplots(1, 2, figsize=(12, 4.3)); y = W.loc["2024-07":"2025-12"]; xs = np.arange(len(y)); lab = [f"{p.year}\n{p.month}月" if p.month in (1, 7) else f"{p.month}月" for p in y.index]
ax[0].plot(xs, y.gross / 1e6, color=GRAY, lw=1.5, label="返品を見ない"); ax[0].plot(xs, y.net_sale_month / 1e6, color=BLUE, lw=2, label="① 売れた月に戻す"); ax[0].plot(xs, y.net_return_month / 1e6, color=ORANGE, lw=2, label="② 返ってきた月で引く")
ax[0].set_xticks(xs); ax[0].set_xticklabels(lab, fontsize=8); ax[0].set_ylabel("月の売上（百万円）"); ax[0].set_title("月の売上（3つの置き方）"); ax[0].legend(fontsize=9, frameon=False)
ax[1].bar(xs, y.diff_pct, color=[ORANGE if v < 0 else BLUE for v in y.diff_pct]); ax[1].axhline(0, color=INK, lw=.8)
ax[1].set_xticks(xs); ax[1].set_xticklabels(lab, fontsize=8); ax[1].set_ylabel("②が①より何%大きいか"); ax[1].set_title("②と①の差（セールは7月と12月の後半）")
for i, v in enumerate(y.diff_pct):
    if abs(v) > 0.9: ax[1].text(i, v + (0.08 if v > 0 else -0.25), f"{v:+.1f}", ha="center", fontsize=8)
save(fig, "a472_monthly.png", f"出典：{SRC}。返品率8%（セール中は約14%）、返るまでの日数の中央値は約10日")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.3)); gg = cl.groupby("days_after_month_end").over_final_pct
ax[0].plot(gg.mean().index, gg.mean().values, marker="o", color=BLUE, label="平均（21か月）"); ax[0].plot(gg.max().index, gg.max().values, marker="o", color=ORANGE, label="いちばん大きい月")
ax[0].set_xlabel("月末から何日たったか"); ax[0].set_ylabel("その時点の①の数字が、最後の数字より何%大きいか"); ax[0].set_title("①「売れた月に戻す」の数字は、あとから下がる"); ax[0].legend(fontsize=9, frameon=False)
for k_ in [5, 31]: ax[0].text(k_ + 2, gg.mean()[k_] + .15, f"{gg.mean()[k_]:.2f}%", fontsize=8.5, color=BLUE)
xs2 = np.arange(len(mv)); ax[1].bar(xs2, mv.amount_changed / 1e6, color=BLUE)
ax[1].set_xticks(xs2[::2]); ax[1].set_xticklabels([c[2:] for c in mv.close[::2]], fontsize=8); ax[1].set_xlabel("締めた月（年-月）"); ax[1].set_ylabel("前回の締めから、過去の月の売上が減った額（百万円）")
ax[1].set_title("締めるたびに、過去の月から消える売上（①）")
save(fig, "a472_restated.png", f"出典：{SRC}。締めは、月末の5日後と置いた。②「返ってきた月で引く」は、過去の月が動かない。右は毎回、過去2か月の数字が動いた")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.3)); pv = sw.pivot(index="return_rate", columns="median_delay_days", values="mean_abs_diff_pct"); pm = sw.pivot(index="return_rate", columns="median_delay_days", values="max_abs_diff_pct")
for a, p_, tt in zip(ax, [pv, pm], ["月の差の平均（絶対値、%）", "月の差のいちばん大きい月（絶対値、%）"]):
    im = a.imshow(p_.values, cmap="Blues", aspect="auto", vmin=0); a.set_xticks(range(4)); a.set_xticklabels([f"{c}日" for c in p_.columns]); a.set_yticks(range(3)); a.set_yticklabels([f"{int(i*100)}%" for i in p_.index])
    a.set_xlabel("売れてから返るまでの日数（中央値）"); a.set_ylabel("返品率"); a.set_title(tt)
    for i in range(3):
        for j in range(4): a.text(j, i, f"{p_.values[i, j]:.2f}", ha="center", va="center", color="white" if p_.values[i, j] > p_.values.max() * .55 else INK, fontsize=10)
    a.spines[:].set_visible(False)
save(fig, "a472_sweep.png", f"出典：{SRC}。②と①の差。各5回の平均。セールは7月と12月の後半")
print(json.dumps(res, ensure_ascii=False)[:4000])
