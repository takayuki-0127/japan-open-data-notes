"""754 欠品率を「欠品した SKU の数」で数えるか「売上の重み」で数えるかで、店の比べ方はどれだけ変わるのか

架空の20店×300SKU×90日の在庫（欠品なら0）。SKU の売れ方は大きく偏り（上位の売れ筋と多くの死に筋）、
店によって「売れ筋が欠けやすい店」と「死に筋が欠けやすい店」がある。欠品率を3通りに出す。
  A SKU×日の数で割る（欠品した SKU 日 ÷ 全 SKU 日）
  B 売上の重み（欠品の日に売れたはずの数 ÷ 売れたはずの数の合計）
  C 期間中に1日でも欠品した SKU の割合
店の順位の入れ替わりを数える。DuckDB（1スレッド）と pandas で一致を確かめる。seed 754。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店と SKU の日次在庫（作成者が乱数で作成、seed 754）"
rng = np.random.default_rng(754)
NS, NK, ND = 20, 300, 90
vel = np.sort(rng.lognormal(0, 1.2, NK))[::-1]           # 1日に売れる数の見込み（SKU ごと）
vel = vel / vel.mean() * 2.0
rel = np.log(vel / np.median(vel))                          # 売れ筋ほど大きい
gamma = np.linspace(-0.9, 0.9, NS); rng.shuffle(gamma)      # 店ごとの「どちらが欠けやすいか」
base = rng.uniform(0.012, 0.03, NS)
rows = []
out_flag = np.zeros((NS, NK, ND), dtype=np.int8)
for s in range(NS):
    p_out = np.clip(base[s] * np.exp(gamma[s] * rel), 0.001, 0.25)   # 在庫ありから欠品になる確率（1日）
    state = np.zeros(NK, dtype=bool)
    for t in range(ND):
        go = rng.random(NK) < p_out
        back = rng.random(NK) < 0.35
        state = np.where(state, ~back, go)
        out_flag[s, :, t] = state
store_ids = [f"店{s + 1:02d}" for s in range(NS)]
sku_ids = [f"K{k + 1:03d}" for k in range(NK)]
dates = pd.date_range("2025-07-01", periods=ND, freq="D")
S, K, T = np.meshgrid(np.arange(NS), np.arange(NK), np.arange(ND), indexing="ij")
inv = pd.DataFrame({"store_id": np.array(store_ids)[S.ravel()], "sku": np.array(sku_ids)[K.ravel()],
                    "d": dates[T.ravel()], "stockout": out_flag.ravel()})
skus = pd.DataFrame({"sku": sku_ids, "daily_rate": vel.round(4)})
skus.to_csv(DATA / "skus.csv", index=False)
summ = inv.groupby(["store_id", "sku"], sort=True).stockout.sum().rename("stockout_days").reset_index()
summ.to_csv(DATA / "stockout_days.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("inventory", inv); con.register("skus", skus)
q = [x for x in (SQL / "02_stockout_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
R = con.execute(q[0]).df().set_index("store_id").sort_index()
# pandas
m = inv.merge(skus, on="sku")
gA = m.groupby("store_id").stockout.mean() * 100
gB = m.assign(lost=m.stockout * m.daily_rate).groupby("store_id").apply(lambda g: g.lost.sum() / g.daily_rate.sum(), include_groups=False) * 100
gC = summ.assign(any_=summ.stockout_days > 0).groupby("store_id").any_.mean() * 100
assert np.allclose(R.rate_sku_days, gA) and np.allclose(R.rate_sales_weighted, gB) and np.allclose(R.rate_any_sku, gC)
rk = pd.DataFrame({"A": gA, "B": gB, "C": gC})
for c in "ABC":
    rk["rank_" + c] = rk[c].rank(ascending=False, method="first").astype(int)
rk["gamma"] = [dict(zip(store_ids, gamma))[s] for s in rk.index]
rho_AB = spearmanr(rk.A, rk.B).statistic
moved5 = int(((rk.rank_A - rk.rank_B).abs() >= 5).sum())
top5A = set(rk.nsmallest(5, "rank_A").index); top5B = set(rk.nsmallest(5, "rank_B").index)
best5A = set(rk.nlargest(5, "rank_A").index); best5B = set(rk.nlargest(5, "rank_B").index)
# 売れ筋の上位10%が全体の売上に占める割合
top10_share = vel[: NK // 10].sum() / vel.sum() * 100
out = {"stores": NS, "skus": NK, "days": ND, "top10pct_sku_share_of_sales": round(top10_share, 1),
       "chain_rate_A_pct": round(float(inv.stockout.mean() * 100), 2),
       "chain_rate_B_pct": round(float((m.stockout * m.daily_rate).sum() / m.daily_rate.sum() * 100), 2),
       "store_rate_A_range": [round(float(rk.A.min()), 2), round(float(rk.A.max()), 2)],
       "store_rate_B_range": [round(float(rk.B.min()), 2), round(float(rk.B.max()), 2)],
       "spearman_A_B": round(float(rho_AB), 2), "spearman_A_C": round(float(spearmanr(rk.A, rk.C).statistic), 2),
       "stores_moved_5plus_ranks_A_to_B": moved5,
       "max_rank_move_A_to_B": int((rk.rank_A - rk.rank_B).abs().max()),
       "worst5_overlap_A_B": len(top5A & top5B), "best5_overlap_A_B": len(best5A & best5B)}
# 例：A では良く B では悪い店
rk["diff"] = rk.rank_A - rk.rank_B
ex_up = rk["diff"].idxmax(); ex_dn = rk["diff"].idxmin()
out["example_A_good_B_bad"] = {"store": ex_up, "A_pct": round(float(rk.A[ex_up]), 2), "B_pct": round(float(rk.B[ex_up]), 2), "rank_A": int(rk.rank_A[ex_up]), "rank_B": int(rk.rank_B[ex_up])}
out["example_A_bad_B_good"] = {"store": ex_dn, "A_pct": round(float(rk.A[ex_dn]), 2), "B_pct": round(float(rk.B[ex_dn]), 2), "rank_A": int(rk.rank_A[ex_dn]), "rank_B": int(rk.rank_B[ex_dn])}
json.dump(out, open(RES / "a754_main.json", "w"), ensure_ascii=False, indent=1)
rk.drop(columns=["diff"]).round(3).reset_index().to_csv(RES / "store_rates.csv", index=False)

# 図1：A と B の散布図
fig, ax = plt.subplots(figsize=(6.8, 5))
sc = ax.scatter(rk.A, rk.B, c=rk.gamma, cmap="coolwarm", s=50, edgecolor="k", lw=0.4)
for s in [ex_up, ex_dn]:
    ax.annotate(s, (rk.A[s], rk.B[s]), xytext=(6, 4), textcoords="offset points", fontsize=9)
cb = fig.colorbar(sc, ax=ax); cb.set_label("売れ筋が欠けやすい ← → 死に筋が欠けやすい", fontsize=8.5)
cb.ax.invert_yaxis(); cb.set_ticks([])
ax.set_xlabel("A SKU×日の数で数えた欠品率（%）"); ax.set_ylabel("B 売上の重みで数えた欠品率（%）")
ax.set_title(f"同じ店でも、数え方で欠品率の大きさが変わる（順位の相関 {rho_AB:.2f}）")
save(fig, "a754_scatter.png", SRC)
# 図2：順位の入れ替わり
fig, ax = plt.subplots(figsize=(6.5, 6))
for s in rk.index:
    c = ORANGE if abs(rk["diff"][s]) >= 5 else GRAY
    ax.plot([0, 1], [rk.rank_A[s], rk.rank_B[s]], color=c, lw=1.6 if c == ORANGE else 0.8, marker="o", ms=4)
    ax.text(-0.04, rk.rank_A[s], s, ha="right", va="center", fontsize=8)
    ax.text(1.04, rk.rank_B[s], s, ha="left", va="center", fontsize=8)
ax.set_xlim(-0.3, 1.3); ax.invert_yaxis(); ax.set_xticks([0, 1]); ax.set_xticklabels(["A SKU×日の数", "B 売上の重み"])
ax.set_yticks([]); ax.spines["left"].set_visible(False)
ax.set_title(f"欠品率の高い順の順位：5位以上動いた店は{moved5}店（オレンジ）")
save(fig, "a754_ranks.png", SRC)
# 図3：例の2店の SKU 別欠品日数
fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
for ax, s in zip(axes, [ex_up, ex_dn]):
    d = summ[summ.store_id == s].merge(skus, on="sku")
    ax.scatter(d.daily_rate, d.stockout_days, s=8, color=BLUE, alpha=0.6)
    ax.set_xscale("log"); ax.set_xlabel("1日に売れる数の見込み（対数）")
    ax.set_title(f"{s}：A {rk.A[s]:.1f}%（{rk.rank_A[s]}位）／B {rk.B[s]:.1f}%（{rk.rank_B[s]}位）", fontsize=10.5)
axes[0].set_ylabel("90日のうち欠品した日数")
fig.suptitle("売れ筋（右）が欠けるか、死に筋（左）が欠けるかで、2つの数え方の答えが分かれる", fontsize=12, y=1.04)
save(fig, "a754_examples.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
