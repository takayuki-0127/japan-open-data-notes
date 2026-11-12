"""426 外貨の売上を円に直すとき、どの日のレートを使うかで、月の売上はどれだけ変わるのか
ドル円は日本銀行の日次（東京市場 17時時点）。取引は架空（乱数の種は426）。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(426)
SRC = "出所：日本銀行「時系列統計データ検索サイト」外国為替市況（FXERD04、東京市場 ドル・円 スポット 17時時点）を加工。取引は架空（seed 426）"

r = pd.read_csv(DATA / "boj_usdjpy_daily.csv", dtype={"date": str})
r["rate_date"] = pd.to_datetime(r["date"], format="%Y%m%d")
r = r.rename(columns={"usdjpy_1700": "usdjpy"})[["rate_date", "usdjpy"]].dropna()
r = r[(r.rate_date >= "1998-01-01") & (r.rate_date <= "2025-12-31")].reset_index(drop=True)
r["ym"] = r.rate_date.dt.to_period("M").dt.to_timestamp()
r["k"] = r.groupby("ym").cumcount()                 # 月の中で何番目の営業日か
r["n"] = r.groupby("ym").rate_date.transform("size")
months = sorted(r.ym.unique())


def make_txn(pattern, per_month=60):
    """架空のドル建ての売上。pattern：even＝営業日に散らばる／end＝月の終わりの5営業日に半分／start＝月の初めの5営業日に半分"""
    out = []
    for ym, g in r.groupby("ym"):
        n = len(g)
        w = np.ones(n)
        if pattern == "end":
            w[-5:] = (n - 5) / 5        # 終わりの5営業日の合計が、残りの日の合計と同じになる重み
        elif pattern == "start":
            w[:5] = (n - 5) / 5
        idx = rng.choice(n, size=per_month, p=w / w.sum())
        usd = np.round(rng.lognormal(np.log(20000), 0.8, per_month), 2)
        out.append(pd.DataFrame({"txn_date": g.rate_date.values[idx], "usd": usd}))
    t = pd.concat(out, ignore_index=True).sort_values("txn_date").reset_index(drop=True)
    t.insert(0, "txn_id", np.arange(1, len(t) + 1))
    return t


def monthly(t):
    m = r.groupby("ym").agg(avg_rate=("usdjpy", "mean"), end_rate=("usdjpy", "last"), first_rate=("usdjpy", "first"),
                            hi=("usdjpy", "max"), lo=("usdjpy", "min"))
    m["prev_end_rate"] = m.end_rate.shift(1)
    m["prev_avg_rate"] = m.avg_rate.shift(1)
    x = t.merge(r[["rate_date", "usdjpy", "ym"]], left_on="txn_date", right_on="rate_date")
    x["jpy"] = x.usd * x.usdjpy
    g = x.groupby("ym").agg(usd=("usd", "sum"), jpy_txn_date=("jpy", "sum"))
    g = g.join(m)
    g["jpy_month_avg"] = g.usd * g.avg_rate
    g["jpy_month_end"] = g.usd * g.end_rate
    g["jpy_prev_end"] = g.usd * g.prev_end_rate
    g["jpy_prev_avg"] = g.usd * g.prev_avg_rate
    g["range_pct"] = (g.hi / g.lo - 1) * 100          # 月の中のレートの幅
    g["move_pct"] = (g.end_rate / g.first_rate - 1) * 100
    return g


METH = [("jpy_month_avg", "②月中平均"), ("jpy_month_end", "③月末レート"), ("jpy_prev_end", "④前の月の月末"), ("jpy_prev_avg", "⑤前の月の平均")]
res = {}
allm = {}
for pat in ["even", "end", "start"]:
    t = make_txn(pat)
    g = monthly(t)
    allm[pat] = g
    if pat == "even":
        t.assign(txn_date=t.txn_date.dt.strftime("%Y-%m-%d")).to_csv(DATA / "fx_transactions_even.csv", index=False)
        t_even = t
    d = {}
    for c, lab in METH:
        diff = (g[c] / g.jpy_txn_date - 1) * 100
        diff = diff.dropna()
        yr = g.dropna(subset=[c]).groupby(g.dropna(subset=[c]).index.year)[[c, "jpy_txn_date"]].sum()
        yd = (yr[c] / yr.jpy_txn_date - 1) * 100
        d[lab] = {"months": int(len(diff)), "median_abs": round(float(diff.abs().median()), 3), "mean_abs": round(float(diff.abs().mean()), 3),
                  "p90_abs": round(float(diff.abs().quantile(0.9)), 3), "max_abs": round(float(diff.abs().max()), 3),
                  "max_month": str(diff.abs().idxmax().date())[:7], "max_signed": round(float(diff[diff.abs().idxmax()]), 3),
                  "share_over_1pct": round(float((diff.abs() > 1).mean() * 100), 1), "share_over_2pct": round(float((diff.abs() > 2).mean() * 100), 1),
                  "mean_signed": round(float(diff.mean()), 3),
                  "year_median_abs": round(float(yd.abs().median()), 3), "year_max_abs": round(float(yd.abs().max()), 3), "year_max": int(yd.abs().idxmax()),
                  "year_max_signed": round(float(yd[yd.abs().idxmax()]), 3),
                  "total_diff_pct": round(float((g[c].sum() / g.loc[g[c].notna(), "jpy_txn_date"].sum() - 1) * 100), 4)}
    res[pat] = d

g = allm["even"]
out = g.reset_index()[["ym", "usd", "jpy_txn_date", "jpy_month_avg", "jpy_month_end", "jpy_prev_end", "jpy_prev_avg", "avg_rate", "end_rate", "range_pct", "move_pct"]].copy()
for c, _ in METH:
    out[c.replace("jpy_", "diff_") + "_pct"] = ((out[c] / out.jpy_txn_date - 1) * 100).round(4)
out["ym"] = out.ym.dt.strftime("%Y-%m")
out.round(4).to_csv(RES / "monthly_even.csv", index=False)
for pat in ["end", "start"]:
    o = allm[pat].reset_index()[["ym", "usd", "jpy_txn_date", "jpy_month_avg", "jpy_month_end"]].copy()
    o["diff_month_avg_pct"] = ((o.jpy_month_avg / o.jpy_txn_date - 1) * 100).round(4)
    o["diff_month_end_pct"] = ((o.jpy_month_end / o.jpy_txn_date - 1) * 100).round(4)
    o["ym"] = o.ym.dt.strftime("%Y-%m")
    o.round(2).to_csv(RES / f"monthly_{pat}.csv", index=False)

# 月の中のレートの幅と、差の大きさ
x = g.copy()
x["d_avg"] = ((x.jpy_month_avg / x.jpy_txn_date - 1) * 100).abs()
x["d_end"] = ((x.jpy_month_end / x.jpy_txn_date - 1) * 100).abs()
bins = [0, 2, 3, 4, 6, 100]
x["幅の区分"] = pd.cut(x.range_pct, bins, labels=["2%未満", "2〜3%", "3〜4%", "4〜6%", "6%以上"], right=False)
byr = x.groupby("幅の区分", observed=True).agg(月数=("d_avg", "size"), 月中平均の差の中央値=("d_avg", "median"), 月末レートの差の中央値=("d_end", "median"),
                                              月末レートの差の最大=("d_end", "max")).round(3)
byr.to_csv(RES / "diff_by_month_range.csv")
corr = {"range_vs_month_end": round(float(np.corrcoef(x.range_pct, x.d_end)[0, 1]), 3), "range_vs_month_avg": round(float(np.corrcoef(x.range_pct, x.d_avg)[0, 1]), 3),
        "move_vs_month_end_signed": round(float(np.corrcoef(x.move_pct, (x.jpy_month_end / x.jpy_txn_date - 1) * 100)[0, 1]), 3)}
top = x.assign(s_end=(x.jpy_month_end / x.jpy_txn_date - 1) * 100, s_avg=(x.jpy_month_avg / x.jpy_txn_date - 1) * 100).sort_values("d_end", ascending=False).head(10)
top10 = [{"ym": str(i.date())[:7], "range_pct": round(float(v.range_pct), 2), "move_pct": round(float(v.move_pct), 2), "diff_month_end": round(float(v.s_end), 2),
          "diff_month_avg": round(float(v.s_avg), 2)} for i, v in top.iterrows()]
pd.DataFrame(top10).to_csv(RES / "top10_months_month_end.csv", index=False)

# 取引の件数を変える（月の件数が少ないと、月中平均との差は大きくなるか）
cnt = {}
for pm in [5, 20, 60, 300]:
    gg = monthly(make_txn("even", pm))
    cnt[pm] = {"月中平均": round(float(((gg.jpy_month_avg / gg.jpy_txn_date - 1) * 100).abs().median()), 3),
               "月末レート": round(float(((gg.jpy_month_end / gg.jpy_txn_date - 1) * 100).abs().median()), 3)}
pd.DataFrame(cnt).T.rename_axis("月の取引件数").to_csv(RES / "diff_by_txn_count.csv")

# SQL（DuckDB）で同じ数字が出るか
con = duckdb.connect()
con.register("rates", r[["rate_date", "usdjpy"]]); con.register("txn", t_even)
q = """
WITH m AS (SELECT date_trunc('month', rate_date) AS ym, AVG(usdjpy) AS avg_rate, MAX(rate_date) AS last_day FROM rates GROUP BY 1),
m2 AS (SELECT m.ym, m.avg_rate, r.usdjpy AS end_rate, LAG(r.usdjpy) OVER (ORDER BY m.ym) AS prev_end_rate FROM m JOIN rates r ON r.rate_date = m.last_day)
SELECT m2.ym, SUM(t.usd * r.usdjpy) AS jpy_txn_date, SUM(t.usd) * MAX(m2.avg_rate) AS jpy_month_avg, SUM(t.usd) * MAX(m2.end_rate) AS jpy_month_end,
       SUM(t.usd) * MAX(m2.prev_end_rate) AS jpy_prev_end
FROM txn t JOIN rates r ON r.rate_date = t.txn_date JOIN m2 ON m2.ym = date_trunc('month', t.txn_date) GROUP BY m2.ym ORDER BY m2.ym"""
s = con.execute(q).df().set_index("ym")
chk = {}
for c in ["jpy_txn_date", "jpy_month_avg", "jpy_month_end", "jpy_prev_end"]:
    a = s[c].values.astype(float); b = g[c].values.astype(float)
    ok = np.allclose(a[~np.isnan(b)], b[~np.isnan(b)], rtol=1e-9)
    assert ok, c
    chk[c] = bool(ok)
pd.DataFrame([{"列": k, "Python と一致": v, "月数": len(s)} for k, v in chk.items()]).to_csv(RES / "sql_check_duckdb.csv", index=False)

main = {"period": "1998-01〜2025-12", "months": len(g), "txn_per_month": 60, "txn_total": int(len(t_even)), "usd_total": round(float(t_even.usd.sum()), 2),
        "patterns": res, "corr": corr, "top10_month_end": top10, "by_range": json.loads(byr.reset_index().to_json(orient="records", force_ascii=False)),
        "by_txn_count": cnt, "range_median": round(float(g.range_pct.median()), 2), "range_max": round(float(g.range_pct.max()), 2),
        "range_max_month": str(g.range_pct.idxmax().date())[:7]}
json.dump(main, open(RES / "a426_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1：月ごとの差の分布（取引が散らばる場合）
fig, ax = plt.subplots(figsize=(8.6, 4.4))
labs = [l for _, l in METH]; cols = [BLUE, ORANGE, GRAY, LIGHT]
data = [((g[c] / g.jpy_txn_date - 1) * 100).dropna().values for c, _ in METH]
bp = ax.boxplot(data, vert=False, whis=(5, 95), showfliers=True, patch_artist=True, flierprops=dict(marker=".", markersize=4, color=GRAY))
ax.set_yticks(range(1, len(labs) + 1)); ax.set_yticklabels(labs)
for p, c in zip(bp["boxes"], cols):
    p.set_facecolor(c); p.set_alpha(0.8)
for md_ in bp["medians"]:
    md_.set_color(INK)
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("取引日のレートで直した額との差（%）。箱は真ん中の半分、ひげは5〜95%")
ax.set_title("月の売上の円換算額は、使うレートでどれだけ違うか（336か月）")
ax.invert_yaxis()
for i, c in enumerate([c for c, _ in METH]):
    d = res["even"][METH[i][1]]
    ax.text(ax.get_xlim()[1], i + 1, f" 中央値 {d['median_abs']:.2f}%・最大 {d['max_abs']:.1f}%", va="center", fontsize=9, color=INK)
save(fig, "a426_diff_distribution.png", SRC)

# ---- 図2：月末レートとの差の推移
fig, ax = plt.subplots(figsize=(9, 4.2))
de = (g.jpy_month_end / g.jpy_txn_date - 1) * 100
da = (g.jpy_month_avg / g.jpy_txn_date - 1) * 100
ax.bar(de.index, de.values, width=25, color=ORANGE, alpha=0.85, label="③月末レート")
ax.plot(da.index, da.values, color=BLUE, lw=1.2, label="②月中平均")
ax.axhline(0, color=INK, lw=0.8)
ax.set_ylim(-7.2, 7.2)
for v in top10[:4]:
    xi = pd.Timestamp(v["ym"] + "-01"); up_ = v["diff_month_end"] > 0
    ax.annotate(v["ym"].replace("-", "年") + "月 " + f"{v['diff_month_end']:+.1f}%", (xi, v["diff_month_end"]), textcoords="offset points",
                xytext=(0, 5 if up_ else -12), ha="center", fontsize=8.5)
ax.set_ylabel("取引日のレートで直した額との差（%）")
ax.set_title("月末レートで直すと、円が大きく動いた月に差が開く")
ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=9)
save(fig, "a426_month_end_diff_series.png", SRC)

# ---- 図3：左＝月の中のレートの幅と差、右＝年の合計の差
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2))
ax = axs[0]
ax.scatter(x.range_pct, x.d_end, s=12, color=ORANGE, alpha=0.7, label="③月末レート")
ax.scatter(x.range_pct, x.d_avg, s=12, color=BLUE, alpha=0.7, label="②月中平均")
ax.set_xlabel("月の中のレートの幅（最高÷最低−1、%）"); ax.set_ylabel("差の大きさ（%）")
ax.set_title("レートの幅が大きい月ほど差が大きい"); ax.legend(frameon=False)
ax = axs[1]
yrs = sorted(set(g.index.year))
ys = g.groupby(g.index.year)[["jpy_txn_date", "jpy_month_avg", "jpy_month_end"]].sum()
w = 0.4
ax.bar(np.array(yrs) - w / 2, (ys.jpy_month_avg / ys.jpy_txn_date - 1) * 100, w, color=BLUE, label="②月中平均")
ax.bar(np.array(yrs) + w / 2, (ys.jpy_month_end / ys.jpy_txn_date - 1) * 100, w, color=ORANGE, label="③月末レート")
ax.axhline(0, color=INK, lw=0.8)
ax.set_title("年の合計にすると、差は小さくなる"); ax.set_ylabel("年の合計の差（%）"); ax.legend(frameon=False, fontsize=9)
fig.tight_layout()
save(fig, "a426_range_and_year.png", SRC)
print(json.dumps({k: v for k, v in main.items() if k not in ("top10_month_end",)}, ensure_ascii=False)[:3500])
print(top10[:5])
