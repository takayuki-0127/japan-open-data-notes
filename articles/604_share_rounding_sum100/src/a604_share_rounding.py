"""604 構成比を四捨五入すると、合計が100%にならない表は何%あり、最大剰余法で直すと各項目はどれだけ動くのか

項目数 k=3〜12 の架空の構成（売上の内訳など）を、k ごとに2万表ずつ作る（ディリクレ分布、集中度をばらつかせる）。
  R0 ふつうの四捨五入（整数の%、小数1桁の%）
  R1 最大剰余法：切り捨てた値の合計の不足分を、小数部分の大きい項目から1ずつ足す
  R2 いちばん大きい項目に差をまとめて寄せる
合計が100にならない表の割合・合計のずれの幅・直したときに動く項目と、もとの値からのずれを数える。
最大剰余法は DuckDB（1スレッド）の SQL でも計算し、Python と一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空の構成（作成者が乱数で作成、seed 604）"
rng = np.random.default_rng(604)
N = 20000


def round_half_up(x, nd=0):
    f = 10 ** nd
    return np.floor(x * f + 0.5) / f


def largest_remainder(p):
    base = np.floor(p); short = (100 - base.sum(axis=1)).round().astype(int)
    rem = p - base
    order = np.argsort(-rem, axis=1, kind="stable")
    add = np.zeros_like(base)
    for i in range(p.shape[0]):
        add[i, order[i, :short[i]]] = 1
    return base + add


rows, sums_k10 = [], None
for k in range(3, 13):
    alpha = rng.choice([0.5, 1.0, 3.0], N)[:, None] * np.ones((1, k))
    v = rng.gamma(alpha, 1.0)
    p = 100 * v / v.sum(axis=1, keepdims=True)
    r0 = round_half_up(p); s0 = r0.sum(axis=1)
    r01 = round_half_up(p, 1); s01 = np.round(r01.sum(axis=1), 1)
    lr = largest_remainder(p)
    assert np.all(lr.sum(axis=1) == 100)
    big = np.argmax(p, axis=1)
    r2 = r0.copy(); r2[np.arange(N), big] += 100 - s0
    moved_lr = (lr != r0).sum(axis=1)
    err_lr = np.abs(lr - p).max(axis=1); err_r2 = np.abs(r2 - p).max(axis=1); err_r0 = np.abs(r0 - p).max(axis=1)
    off = s0 != 100
    rows.append({"k": k, "not100_int_pct": round(100 * off.mean(), 1), "not100_1dec_pct": round(100 * (s01 != 100).mean(), 1),
                 "sum_range": [int(s0.min()), int(s0.max())], "abs_off_ge2_pct": round(100 * (np.abs(s0 - 100) >= 2).mean(), 2),
                 "lr_items_moved_mean_when_off": round(float(moved_lr[off].mean()), 2),
                 "max_err_r0": round(float(err_r0.max()), 3), "max_err_lr": round(float(err_lr.max()), 3), "max_err_r2": round(float(err_r2.max()), 3),
                 "p99_err_r2_when_off": round(float(np.quantile(err_r2[off], 0.99)), 3),
                 "lr_vs_r2_differ_pct": round(100 * (np.abs(lr - r2).sum(axis=1) > 0).mean(), 1)})
    if k == 10:
        sums_k10 = pd.Series(s0).value_counts().sort_index()
        # SQL で最大剰余法を計算して一致を確かめる（先頭500表）
        sub = pd.DataFrame([(t, j + 1, float(v[t, j])) for t in range(500) for j in range(k)], columns=["table_id", "item", "value"])
        con = duckdb.connect(); con.execute("SET threads=1"); con.register("shares", sub)
        out_sql = con.execute((SQL / "02_largest_remainder_duckdb.sql").read_text(encoding="utf-8")).df()
        # 小数部分が同じになる（同点の）場合だけ順番の決め方で差が出うる。同点がないことを確かめてから比べる
        assert np.array_equal(out_sql.pct_lr.to_numpy().reshape(500, k), lr[:500]), "SQL と Python が不一致"
        assert np.array_equal(out_sql.pct_round.to_numpy().reshape(500, k), r0[:500])
        ex_i = int(np.where(np.abs(s0 - 100) == np.abs(s0 - 100).max())[0][0])
        example = pd.DataFrame({"pct": p[ex_i], "round": r0[ex_i], "largest_remainder": lr[ex_i], "to_largest": r2[ex_i]})
        example.round(3).to_csv(RES / "example_k10.csv", index_label="item")
res = pd.DataFrame(rows)
res.to_csv(RES / "summary.csv", index=False)
sums_k10.to_csv(RES / "sum_dist_k10.csv", header=["tables"])
out = {"tables_per_k": N, "by_k": rows, "k10_sum_dist": {int(a): int(b) for a, b in sums_k10.items()},
       "example_k10_sum": int(example["round"].sum())}
json.dump(out, open(RES / "a604_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：k ごとの、合計が100にならない割合
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(res.k, res.not100_int_pct, marker="o", color=BLUE, label="整数の%に四捨五入")
ax.plot(res.k, res.not100_1dec_pct, marker="s", color=ORANGE, label="小数1桁の%に四捨五入")
ax.set_xticks(res.k); ax.set_xlabel("項目の数"); ax.set_ylabel("合計が100にならない表の割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False); ax.set_title("項目が多いほど、四捨五入した構成比の合計は100からずれる")
save(fig, "a604_not100_by_k.png", SRC)
# 図2：k=10 の合計の分布
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.bar(sums_k10.index.astype(int), sums_k10.values / N * 100, color=[GREEN if i == 100 else BLUE for i in sums_k10.index], width=0.7)
for i, vv in zip(sums_k10.index, sums_k10.values):
    ax.text(i, vv / N * 100, f"{vv / N * 100:.1f}%", ha="center", va="bottom", fontsize=9)
ax.set_xlabel("四捨五入した10項目の構成比の合計（%）"); ax.set_ylabel("表の割合（%）"); ax.set_xticks(sums_k10.index.astype(int))
ax.set_title("10項目の表2万枚：四捨五入した合計の分布")
save(fig, "a604_sum_dist_k10.png", SRC)
# 図3：直し方ごとの、もとの値からの最大のずれ（k ごと）
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(res.k, res.max_err_lr, marker="o", color=GREEN, label="最大剰余法")
ax.plot(res.k, res.max_err_r2, marker="s", color=ORANGE, label="いちばん大きい項目に寄せる")
ax.plot(res.k, res.max_err_r0, marker="^", color=GRAY, label="四捨五入だけ（合計は合わない）")
ax.set_xticks(res.k); ax.set_xlabel("項目の数"); ax.set_ylabel("もとの値からの最大のずれ（ポイント）")
ax.legend(frameon=False, fontsize=9); ax.set_title("合計を100に合わせたときの、項目ごとの最大のずれ（2万表の中の最大）")
save(fig, "a604_max_error.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1)); print(example.round(2))
