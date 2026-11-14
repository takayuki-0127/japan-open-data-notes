"""663 ウィンドウ関数の PARTITION BY を書き忘れると、店ごとの累計や順位はどれだけ狂うのか

架空の20店の日別売上（2025年1〜3月、90日）。4つのウィンドウ関数を PARTITION BY あり・なしで出し、ずれた行とずれの大きさを数える。
  累計（SUM OVER ORDER BY 日付）、7日の移動平均（ROWS 6 PRECEDING、ORDER BY 店・日付）、
  前日の売上（LAG、ORDER BY 店・日付）、その日の順位（RANK）
GROUP BY（自己結合）で出した累計とも比べる。DuckDB（1スレッド）と pandas の一致を確かめる。seed 663。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空の20店の日別売上（作成者が乱数で作成、seed 663）"
rng = np.random.default_rng(663)
dates = pd.date_range("2025-01-01", "2025-03-31")
base = rng.lognormal(np.log(300), 0.5, 20)
dow = np.array([0.95, 0.9, 0.92, 0.97, 1.05, 1.2, 1.15])
rows = [(f"S{s + 1:02d}", d.strftime("%Y-%m-%d"), int(round(base[s] * dow[d.dayofweek] * rng.lognormal(0, 0.12)) * 1000))
        for s in range(20) for d in dates]
D0 = pd.DataFrame(rows, columns=["store_id", "sale_date", "sales"])
D0.to_csv(DATA / "daily.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("daily", D0)
qs = [x for x in (SQL / "02_window_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
Q = con.execute(qs[0]).df(); G = con.execute(qs[1]).df()
# pandas
P = D0.sort_values(["store_id", "sale_date"]).reset_index(drop=True)
P["cum_ok"] = P.groupby("store_id").sales.cumsum()
P["cum_ng"] = P.sale_date.map(P.groupby("sale_date").sales.sum().cumsum())
P["ma7_ok"] = P.groupby("store_id").sales.transform(lambda s: s.rolling(7, min_periods=1).mean())
P["ma7_ng"] = P.sales.rolling(7, min_periods=1).mean()
P["prev_ok"] = P.groupby("store_id").sales.shift(); P["prev_ng"] = P.sales.shift()
P["rank_ok"] = P.groupby("sale_date").sales.rank(method="min", ascending=False).astype(int)
P["rank_ng"] = P.sales.rank(method="min", ascending=False).astype(int)
for c in ["cum_ok", "cum_ng", "ma7_ok", "ma7_ng", "rank_ok", "rank_ng"]:
    assert np.allclose(P[c].astype(float), Q[c].astype(float)), c
assert P.prev_ok.isna().equals(Q.prev_ok.isna()) and np.allclose(P.prev_ok.fillna(-1), Q.prev_ok.fillna(-1).astype(float))
assert np.allclose(P.prev_ng.fillna(-1), Q.prev_ng.fillna(-1).astype(float))
assert np.allclose(G.cum_groupby.astype(float), P.cum_ok)
P.to_csv(RES / "window_compare.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
n = len(P)
P["day_idx"] = P.groupby("store_id").cumcount() + 1
prev_wrong = (P.prev_ok.isna() != P.prev_ng.isna()) | (P.prev_ok.fillna(-1) != P.prev_ng.fillna(-1))
dod_ng = P.sales / P.prev_ng - 1
summ = {
  "累計": {"wrong": int((P.cum_ok != P.cum_ng).sum()), "max_ratio": round(float((P.cum_ng / P.cum_ok).max()), 1), "median_ratio": round(float((P.cum_ng / P.cum_ok).median()), 1)},
  "7日の移動平均": {"wrong": int((~np.isclose(P.ma7_ok, P.ma7_ng)).sum()), "max_abs_pct": round(float((P.ma7_ng / P.ma7_ok - 1).abs().max() * 100), 1)},
  "前日の売上": {"wrong": int(prev_wrong.sum()), "dod_ng_range_pct_wrong_rows": [round(float(dod_ng[prev_wrong].min() * 100), 1), round(float(dod_ng[prev_wrong].max() * 100), 1)]},
  "その日の順位": {"wrong": int((P.rank_ok != P.rank_ng).sum()), "max_rank_ng": int(P.rank_ng.max())}}
for k in summ:
    summ[k]["wrong_pct"] = round(summ[k]["wrong"] / n * 100, 1)
ma_err = P[P.day_idx <= 7].assign(err=lambda d: (d.ma7_ng / d.ma7_ok - 1) * 100)
out = {"n_rows": n, "stores": 20, "days": 90, "summary": summ, "groupby_cum_matches": True,
       "ma7_err_by_day_idx": {int(i): round(float(g.err.abs().median()), 1) for i, g in ma_err.groupby("day_idx")},
       "store_size_range": [int(P.groupby("store_id").sales.mean().min()), int(P.groupby("store_id").sales.mean().max())]}
json.dump(out, open(RES / "a663_main.json", "w"), ensure_ascii=False, indent=1)

# 図1
fig, ax = plt.subplots(figsize=(8.5, 3.2))
lab = list(summ); v = [summ[k]["wrong_pct"] for k in lab]
ax.barh(lab[::-1], v[::-1], color=[ORANGE if x > 50 else BLUE for x in v[::-1]])
for i, x in enumerate(v[::-1]):
    ax.text(x, i, f" {x:.1f}%（{summ[lab[::-1][i]]['wrong']:,}行）", va="center", fontsize=9)
ax.set_xlim(0, 125); ax.set_xlabel(f"値がずれた行の割合（全{n:,}行）")
ax.set_title("全部ずれる関数と、店の境目だけずれる関数がある")
save(fig, "a663_wrong_rows.png", SRC, y=-0.05)
# 図2：1店の累計
s = P[P.store_id == "S05"]; x = pd.to_datetime(s.sale_date)
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.plot(x, s.cum_ok / 1e6, color=BLUE, label="PARTITION BY 店 あり（S05 の累計）")
ax.plot(x, s.cum_ng / 1e6, color=ORANGE, label="PARTITION BY なし（全店の累計になる）")
ax.set_ylabel("累計の売上（百万円）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"PARTITION BY がないと、1店の累計が全店の合計になる（S05 で{float((s.cum_ng / s.cum_ok).iloc[-1]):.0f}倍）")
save(fig, "a663_cumsum.png", SRC)
# 図3：移動平均のずれ
fig, ax = plt.subplots(figsize=(8.5, 3.6))
for i in range(1, 8):
    e = ma_err[ma_err.day_idx == i].err
    ax.scatter(np.full(len(e), i) + rng.uniform(-0.12, 0.12, len(e)), e, s=14, color=ORANGE if i < 7 else BLUE, alpha=0.8)
ax.axhline(0, color="black", lw=0.8); ax.set_xticks(range(1, 8)); ax.set_xticklabels([f"{i}日目" for i in range(1, 8)])
ax.set_ylabel("7日の移動平均のずれ（%）"); ax.set_title("移動平均は、各店の最初の6日だけ、前の店の売上が混ざる")
save(fig, "a663_ma7_edge.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
