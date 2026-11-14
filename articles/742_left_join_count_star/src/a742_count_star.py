"""742 LEFT JOIN のあと COUNT(*) で注文数を数えると、注文0件の顧客は何件と数えられるのか

架空の顧客6,000人（登録月は2025年1〜12月）と、その注文。登録が新しい人ほど注文0件が多い。
顧客表に注文表を LEFT JOIN し、顧客ごとに COUNT(*) と COUNT(order_id) で注文数を数える。
1人あたりの平均注文数、「1回だけ買った人」の割合、登録月ごとの平均を比べる。
DuckDB（1スレッド）の結果と pandas の結果の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の顧客と注文（作成者が乱数で作成、seed 742）"
rng = np.random.default_rng(742)
N = 6000
m = rng.integers(1, 13, N)
lam = 0.25 * (13 - m)                         # 登録が古いほど多く買う
k = rng.poisson(lam * rng.gamma(1.0, 1.0, N))
C = pd.DataFrame({"customer_id": np.arange(1, N + 1), "signup_month": [f"2025-{x:02d}" for x in m]})
O = pd.DataFrame({"customer_id": np.repeat(C.customer_id, k)})
O.insert(0, "order_id", np.arange(1, len(O) + 1))
O["amount"] = rng.integers(500, 20000, len(O))
DATA.mkdir(exist_ok=True)
C.to_csv(DATA / "customers.csv", index=False); O.to_csv(DATA / "orders.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("customers", C); con.register("orders", O)
q = "\n".join(l for l in (SQL / "02_count_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
truth = O.groupby("customer_id").size().reindex(C.customer_id, fill_value=0).to_numpy()
assert (Q.n_count_col.to_numpy() == truth).all() and (Q.n_count_star.to_numpy() == np.maximum(truth, 1)).all()

zero = int((truth == 0).sum())
star, col = Q.n_count_star, Q.n_count_col
by_m = Q.groupby("signup_month").agg(star=("n_count_star", "mean"), col=("n_count_col", "mean"), zero=("n_count_col", lambda s: (s == 0).mean())).reset_index()
by_m.to_csv(RES / "by_month.csv", index=False)
dist = pd.DataFrame({"orders": np.arange(0, 11)})
dist["count_col"] = [int((col == v).sum()) for v in dist.orders]
dist["count_star"] = [int((star == v).sum()) for v in dist.orders]
dist.to_csv(RES / "distribution.csv", index=False)
out = {"customers": N, "orders": int(len(O)), "zero_customers": zero, "zero_share": zero / N,
       "mean_col": float(col.mean()), "mean_star": float(star.mean()), "mean_ratio": float(star.mean() / col.mean()),
       "one_time_col": int((col == 1).sum()), "one_time_star": int((star == 1).sum()),
       "one_time_share_col": float((col == 1).mean()), "one_time_share_star": float((star == 1).mean()),
       "mean_buyers_only": float(col[col > 0].mean()),
       "dec_mean_col": float(by_m.col.iloc[-1]), "dec_mean_star": float(by_m.star.iloc[-1]), "dec_zero_share": float(by_m.zero.iloc[-1]),
       "jan_mean_col": float(by_m.col.iloc[0]), "jan_mean_star": float(by_m.star.iloc[0]),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a742_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：注文数の分布
fig, ax = plt.subplots(figsize=(9, 4.6)); x = dist.orders; w = .4
ax.bar(x - w / 2, dist.count_col, w, color=BLUE, label="COUNT(order_id)（正しい）")
ax.bar(x + w / 2, dist.count_star, w, color=ORANGE, label="COUNT(*)")
for xx, a, b in zip(x[:2], dist.count_col[:2], dist.count_star[:2]):
    ax.text(xx - w / 2, a + 40, f"{a:,}", ha="center", fontsize=9); ax.text(xx + w / 2, b + 40, f"{b:,}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xlabel("顧客1人の注文数"); ax.set_ylabel("顧客の数"); ax.legend(frameon=False)
ax.set_title(f"COUNT(*) では、注文0件の{zero:,}人が「1件」に移る")
save(fig, "a742_distribution.png", SRC)

# 図2：平均と「1回だけ」の割合
fig, axs = plt.subplots(1, 2, figsize=(9, 4.4))
axs[0].bar(["COUNT(order_id)", "COUNT(*)"], [col.mean(), star.mean()], color=[BLUE, ORANGE])
for i, v in enumerate([col.mean(), star.mean()]):
    axs[0].text(i, v + .03, f"{v:.2f}", ha="center")
axs[0].set_title("1人あたりの注文数"); axs[0].set_ylim(0, star.mean() * 1.25)
axs[1].bar(["COUNT(order_id)", "COUNT(*)"], [(col == 1).mean() * 100, (star == 1).mean() * 100], color=[BLUE, ORANGE])
for i, v in enumerate([(col == 1).mean() * 100, (star == 1).mean() * 100]):
    axs[1].text(i, v + 1, f"{v:.1f}%", ha="center")
axs[1].set_title("「1回だけ買った人」の割合"); axs[1].set_ylim(0, 80)
fig.suptitle("平均も「1回だけ」の割合も、COUNT(*) では大きく出る", y=1.02)
save(fig, "a742_mean_onetime.png", SRC)

# 図3：登録月ごと
fig, ax = plt.subplots(figsize=(9, 4.6))
xm = np.arange(12)
ax.plot(xm, by_m.col, "o-", color=BLUE, label="COUNT(order_id)")
ax.plot(xm, by_m.star, "o-", color=ORANGE, label="COUNT(*)")
ax.set_xticks(xm); ax.set_xticklabels([s[5:] + "月" for s in by_m.signup_month])
ax.set_xlabel("登録月（2025年）"); ax.set_ylabel("1人あたりの注文数"); ax.legend(frameon=False)
ax.set_title("登録が新しく、注文0件の多い月ほど、COUNT(*) のずれが大きい")
save(fig, "a742_by_month.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
