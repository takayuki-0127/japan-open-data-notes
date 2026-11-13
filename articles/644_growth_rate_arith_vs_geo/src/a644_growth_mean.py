"""644 毎年の伸び率を足して割った平均と、年率（幾何平均）では、5年後の値はどれだけ違うのか

架空の店の年間売上（2020〜2025年、毎年の伸び率は振れる）で、
  算術平均：毎年の伸び率を足して年数で割る
  年率（幾何平均）：(最後÷最初)^(1/年数) − 1
を比べる。(1) 店ごとの2つの平均の差と、算術平均で最初の年から延ばしたときの2025年の値のずれ（DuckDB の SQL でも計算して一致を確かめる）、
(2) 伸び率の振れ（標準偏差）を 5〜30% に変えたときの差、(3) 過去5年の平均で次の5年を延ばしたとき、実際の値の中央値と平均のどちらに近いか（各2万回）。
数字は置いた伸び率と振れで決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の店の年間売上（作成者が乱数で作成、seed 644）"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(644)

# (1) 架空の100店、2020〜2025年
NS = 100
rows = []
for s in range(1, NS + 1):
    sd = rng.choice([0.05, 0.1, 0.2, 0.3])
    g = np.exp(rng.normal(0.02, sd, 5)) - 1
    v = [round(rng.lognormal(np.log(5000), 0.5), 1)]
    for x in g:
        v.append(round(v[-1] * (1 + x), 1))
    for y, val in zip(range(2020, 2026), v):
        rows.append((f"S{s:03d}", y, val, sd))
A = pd.DataFrame(rows, columns=["store_id", "yr", "sales", "sd_set"])
A[["store_id", "yr", "sales"]].to_csv(DATA / "annual_sales.csv", index=False)
p = A.pivot(index="store_id", columns="yr", values="sales")
gr = p.pct_change(axis=1).iloc[:, 1:]
arith = gr.mean(1); geo = np.exp(np.log1p(gr).mean(1)) - 1
cagr = (p[2025] / p[2020]) ** (1 / 5) - 1
con = duckdb.connect(); con.execute("SET threads=1"); con.register("annual_sales", A[["store_id", "yr", "sales"]])
sq = con.execute((SQL / "02_growth_duckdb.sql").read_text(encoding="utf-8")).df().set_index("store_id")
assert np.allclose(sq.arith_mean, arith.loc[sq.index]) and np.allclose(sq.geo_mean, geo.loc[sq.index]) and np.allclose(sq.cagr, cagr.loc[sq.index])
assert np.allclose(geo, cagr)
end_by_arith = p[2020] * (1 + arith) ** 5
over = (end_by_arith / p[2025] - 1) * 100
st = pd.DataFrame({"sd_set": A.groupby("store_id").sd_set.first(), "arith": arith * 100, "geo": geo * 100, "gap_pt": (arith - geo) * 100, "end_over_pct": over})
st.round(3).to_csv(RES / "per_store.csv")
by_sd = st.groupby("sd_set").agg(stores=("gap_pt", "size"), gap_pt=("gap_pt", "mean"), end_over_pct=("end_over_pct", "median"),
                                 end_over_max=("end_over_pct", "max")).round(2)
by_sd.to_csv(RES / "by_sd_stores.csv")

# 例：+50% と −50%
ex = {"arith": 0.0, "geo": round(float((np.sqrt(1.5 * 0.5) - 1) * 100), 2), "end": 75.0}

# (2) 振れを変えた理論とシミュレーション
sims = []
for sd in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
    G = np.exp(rng.normal(0.02, sd, (20000, 5))) - 1
    ar = G.mean(1); ge = np.exp(np.log1p(G).mean(1)) - 1
    # (3) 次の5年
    F = np.exp(rng.normal(0.02, sd, (20000, 5))) - 1
    fut = np.prod(1 + F, 1)                      # 次の5年の倍率（実際）
    sims.append({"sd": sd, "gap_pt_mean": float((ar - ge).mean() * 100), "gap_theory_pt": float(sd ** 2 / 2 * 100),
                 "fut_median": float(np.median(fut)), "fut_mean": float(fut.mean()),
                 "proj_arith_median": float(np.median((1 + ar) ** 5)), "proj_geo_median": float(np.median((1 + ge) ** 5)),
                 "true_median": float(np.exp(0.02 * 5)), "true_mean": float(np.exp(0.02 * 5 + 5 * sd ** 2 / 2)),
                 "abs_err_arith": float(np.median(np.abs(np.log((1 + ar) ** 5 / fut)))),
                 "abs_err_geo": float(np.median(np.abs(np.log((1 + ge) ** 5 / fut))))})
SM = pd.DataFrame(sims).round(4); SM.to_csv(RES / "by_sd_sim.csv", index=False)
out = {"stores": NS, "example_plus50_minus50": ex, "stores_gap_pt_mean": round(float(st.gap_pt.mean()), 3),
       "by_sd_stores": by_sd.reset_index().to_dict(orient="records"), "sim": SM.to_dict(orient="records")}
json.dump(out, open(RES / "a644_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：店ごとの2つの平均（振れの大きさで色分け）
fig, ax = plt.subplots(figsize=(7.5, 4.5))
cmap = {0.05: LIGHT, 0.1: BLUE, 0.2: ORANGE, 0.3: INK}
for sd, c in cmap.items():
    s = st[st.sd_set == sd]
    ax.scatter(s.geo, s.arith, s=16, color=c, label=f"伸び率の振れ {int(sd*100)}%")
lim = [min(st.geo.min(), st.arith.min()) - 1, max(st.geo.max(), st.arith.max()) + 1]
ax.plot(lim, lim, color=GRAY, ls="--", lw=0.8)
ax.set_xlabel("年率（幾何平均、%）"); ax.set_ylabel("毎年の伸び率の算術平均（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("算術平均はいつも年率以上。振れの大きい店ほど上に離れる（架空の100店）")
save(fig, "a644_store_scatter.png", SRC)

# 図2：振れと差（シミュレーションと σ²/2）
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(SM.sd * 100, SM.gap_pt_mean, marker="o", color=ORANGE, label="算術平均−年率（2万回の平均）")
ax.plot(SM.sd * 100, SM.gap_theory_pt, color=GRAY, ls="--", label="近似 σ²/2")
for x, y in zip(SM.sd * 100, SM.gap_pt_mean):
    ax.text(x, y, f" {y:.2f}", fontsize=8, va="bottom")
ax.set_xlabel("毎年の伸び率の振れ（標準偏差、%）"); ax.set_ylabel("差（ポイント）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("2つの平均の差は、振れのほぼ2乗の半分")
save(fig, "a644_gap_by_sd.png", SRC)

# 図3：5年延ばした倍率の中央値と、実際の中央値・平均
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(SM.sd * 100, SM.proj_arith_median, marker="o", color=ORANGE, label="算術平均で延ばした倍率（中央値）")
ax.plot(SM.sd * 100, SM.proj_geo_median, marker="s", color=BLUE, label="年率で延ばした倍率（中央値）")
ax.plot(SM.sd * 100, SM.fut_median, color=INK, ls="--", label="実際の5年後の倍率の中央値")
ax.plot(SM.sd * 100, SM.fut_mean, color=GRAY, ls=":", label="実際の5年後の倍率の平均")
ax.set_xlabel("毎年の伸び率の振れ（標準偏差、%）"); ax.set_ylabel("5年後の値÷今の値"); ax.legend(frameon=False, fontsize=8.5)
ax.set_title("算術平均で延ばすと平均に、年率で延ばすと中央値に近い（各2万回）")
save(fig, "a644_projection.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
