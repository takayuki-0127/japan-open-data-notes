"""579 店ごとの比率を平均するか、合計どうしで比を取るか（seed 579）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(579)
SRC = "架空の店（作成者が乱数で作成、seed 579）"
N = 50


def indicators(vis, buy):
    r = buy / vis
    return {"simple_mean": float(r.mean()), "median": float(np.median(r)),
            "weighted_by_visitors": float(np.average(r, weights=vis)), "ratio_of_totals": float(buy.sum() / vis.sum())}


# 例の店：来店客数は大きく違い、小さい店ほど購入率が高い。翌年は大きい店が少し上がり、小さい店が下がる
vis1 = np.round(np.exp(rng.normal(np.log(5000), 1.0, N))).astype(int)
z = (np.log(vis1) - np.log(vis1).mean()) / np.log(vis1).std()
rate1 = np.clip(0.30 - 0.04 * z + rng.normal(0, 0.02, N), 0.05, 0.9)
vis2 = np.round(vis1 * np.exp(rng.normal(0, 0.05, N))).astype(int)              # 客数は前年並み（±5%ほど）
rate2 = np.clip(rate1 + 0.006 * z - 0.003 + rng.normal(0, 0.008, N), 0.05, 0.9)   # 大きい店ほど上がる
buy1 = np.round(vis1 * rate1).astype(int); buy2 = np.round(vis2 * rate2).astype(int)
stores = pd.DataFrame({"store": [f"S{i+1:02d}" for i in range(N)], "visitors_y1": vis1, "buyers_y1": buy1, "visitors_y2": vis2, "buyers_y2": buy2})
DATA.mkdir(exist_ok=True)
stores.to_csv(DATA / "stores.csv", index=False)
i1, i2 = indicators(vis1, buy1), indicators(vis2, buy2)
ex = pd.DataFrame([{"method": k, "year1": i1[k], "year2": i2[k], "change_pt": (i2[k] - i1[k]) * 100} for k in i1])
ex.to_csv(RES / "example_indicators.csv", index=False)
r1 = buy1 / vis1; r2 = buy2 / vis2
n_up = int((r2 > r1).sum())
top10_share = float(np.sort(vis1)[::-1][:10].sum() / vis1.sum())

con = duckdb.connect(); con.execute("SET threads=1"); con.register("stores", stores)
sq = con.execute(open(SQL / "a579_ratios.sql", encoding="utf-8").read()).df()
sq.to_csv(RES / "sql_indicators.csv", index=False)
ok = all(np.isclose(sq.loc[sq.year == y, k].iloc[0], d[k]) for y, d in [(1, i1), (2, i2)] for k in ["simple_mean", "weighted_by_visitors", "ratio_of_totals"])

# 試し1：店の大きさと購入率の結びつき（b）を変えたときの、単純平均と合計の比の差（1,000回ずつ）
gap = []
for b in [0.0, 0.01, 0.02, 0.04, 0.06]:
    for s in range(1000):
        v = np.exp(rng.normal(np.log(5000), 1.0, N)); zz = (np.log(v) - np.log(v).mean()) / np.log(v).std()
        r = np.clip(0.30 - b * zz + rng.normal(0, 0.02, N), 0.01, 0.99)
        gap.append({"b": b, "sim": s, "gap_pt": (r.mean() - (v * r).sum() / v.sum()) * 100})
gap = pd.DataFrame(gap)
gs = gap.groupby("b").gap_pt.agg(median="median", p05=lambda x: x.quantile(.05), p95=lambda x: x.quantile(.95)).reset_index()
gs.to_csv(RES / "gap_by_size_link.csv", index=False)

# 試し2：前年比の向きが食い違う割合。変化が店の大きさとどれだけ結びつくか（c）を変える（2,000回ずつ）
flip = []
for c in [0.0, 0.0025, 0.005, 0.01]:
    for s in range(2000):
        v = np.exp(rng.normal(np.log(5000), 1.0, N)); zz = (np.log(v) - np.log(v).mean()) / np.log(v).std()
        r = np.clip(0.30 - 0.04 * zz + rng.normal(0, 0.02, N), 0.01, 0.99)
        d = rng.normal(0, 0.005) + c * zz + rng.normal(0, 0.01, N)
        r2_ = np.clip(r + d, 0.01, 0.99)
        ds = r2_.mean() - r.mean(); dt = (v * r2_).sum() / v.sum() - (v * r).sum() / v.sum()
        flip.append({"c": c, "sim": s, "flip": bool(np.sign(ds) != np.sign(dt)), "abs_diff_pt": abs(ds - dt) * 100})
flip = pd.DataFrame(flip)
fs = flip.groupby("c").agg(flip_share=("flip", "mean"), diff_median_pt=("abs_diff_pt", "median")).reset_index()
fs.to_csv(RES / "direction_flip.csv", index=False)

# 図1：例の店（来店客数と購入率）
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.scatter(vis1, r1 * 100, s=np.sqrt(vis1) / 2, color=BLUE, alpha=0.6)
ax.set_xscale("log"); ax.set_xlabel("1年目の来店客数（人、対数目盛）"); ax.set_ylabel("1年目の購入率（%）")
for k, col, lab in [("simple_mean", ORANGE, "店の購入率の単純平均"), ("ratio_of_totals", INK, "合計の比（全体の購入率）")]:
    ax.axhline(i1[k] * 100, color=col, lw=1.2, ls="--"); ax.text(vis1.max() * 1.05, i1[k] * 100, f"{lab}\n{i1[k]*100:.1f}%", color=col, fontsize=8.5, va="center")
ax.set_title("小さい店ほど購入率が高いと、単純平均は高く出る")
save(fig, "a579_stores.png", SRC + "。50店、点の大きさは来店客数")

# 図2：例の前年比
fig, ax = plt.subplots(figsize=(8, 4))
lab = {"simple_mean": "単純平均", "median": "中央値", "weighted_by_visitors": "来店客数で重み付けた平均", "ratio_of_totals": "合計の比"}
y = np.arange(len(ex))
cols = [ORANGE if v < 0 else BLUE for v in ex.change_pt]
ax.barh(y, ex.change_pt, color=cols)
for yy, v, a_, b_ in zip(y, ex.change_pt, ex.year1, ex.year2):
    ax.text(v + (0.03 if v >= 0 else -0.03), yy, f"{v:+.2f}pt（{a_*100:.1f}%→{b_*100:.1f}%）", va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color=INK, lw=1); ax.set_yticks(y, [lab[m] for m in ex.method]); ax.invert_yaxis()
ax.set_xlim(-1.2, 1.2); ax.set_xlabel("購入率の前年からの変化（ポイント）")
ax.set_title("同じ50店でも、平均の取り方で前年比の向きが変わる")
save(fig, "a579_yoy.png", SRC + f"。購入率が上がった店は50店中{n_up}店")

# 図3：試しの結果
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
ax = axes[0]
ax.plot(gs.b * 100, gs["median"], "o-", color=ORANGE); ax.fill_between(gs.b * 100, gs.p05, gs.p95, color=ORANGE, alpha=0.15)
for x, v in zip(gs.b * 100, gs["median"]): ax.text(x, v + 0.3, f"{v:+.1f}", ha="center", fontsize=9)
ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("店の大きさ1標準偏差あたりの購入率の違い（ポイント）")
ax.set_ylabel("単純平均 − 合計の比（ポイント）"); ax.set_title("差の大きさ（1,000回、帯は5〜95%）")
ax = axes[1]
ax.bar(np.arange(len(fs)), fs.flip_share * 100, color=BLUE)
for x, v in enumerate(fs.flip_share * 100): ax.text(x, v + 0.8, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_xticks(np.arange(len(fs)), [f"{c*100:.2g}" for c in fs.c]); ax.set_xlabel("変化と店の大きさの結びつき（ポイント）")
ax.set_ylabel("前年比の向きが食い違った割合（%）"); ax.set_title("前年比の向きの食い違い（2,000回）")
save(fig, "a579_sim.png", SRC)

main = {"n_stores": N, "example": ex.round(5).to_dict(orient="records"), "n_stores_up": n_up, "top10_visitor_share": top10_share,
        "sql_matches_python": bool(ok), "gap": gs.round(4).to_dict(orient="records"), "flip": fs.round(4).to_dict(orient="records")}
json.dump(main, open(RES / "a579_main.json", "w"), ensure_ascii=False, indent=1)
print(ex.round(4).to_string()); print("up", n_up, "top10", round(top10_share, 3)); print(gs.round(3).to_string()); print(fs.round(4).to_string()); print("sql ok", ok)
