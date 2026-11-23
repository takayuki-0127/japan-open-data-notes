"""988 珍しい組み合わせを後から探すと、何が見つかるのか？（架空のデータ）

架空の店の1か月の客。曜日・時間帯・天気・入口・支払い方法・会員かどうかの6つの項目を乱数で付け、
「デザートも買った」かどうかは、基本では項目と関係なく全員10%と置く（どの組み合わせにも本当の差はない）。
1つの項目の値（例：土曜）と2つの項目の組み合わせ（例：土曜×雨）を全部調べ、
いちばん珍しく見える組み合わせ（全体の割合より高いことが偶然では起きにくい順）を後から探す。
見つけた組み合わせを、次の月の新しい客で数え直す。
"""
import json
import time
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binom
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 988
SRC = "架空の店の客と買い物（作成者が乱数で作成、seed 988）"
ATTR = {
    "曜日": (["月", "火", "水", "木", "金", "土", "日"], [1 / 7] * 7),
    "時間帯": (["朝", "昼", "夕方", "夜"], [0.2, 0.35, 0.25, 0.2]),
    "天気": (["晴れ", "くもり", "雨"], [0.5, 0.3, 0.2]),
    "入口": (["北口", "南口"], [0.5, 0.5]),
    "支払い": (["現金", "カード", "電子マネー"], [0.4, 0.35, 0.25]),
    "会員": (["会員", "会員でない"], [0.4, 0.6]),
}
NAMES = list(ATTR)
BASE = 0.10
N0 = 2000
MIN_CELL = 30
TRUE_CELL = ((0, 5), (2, 2))          # 土曜×雨（本当の差を置く確かめで使う）


def make(rng, n, effect=1.0):
    x = np.column_stack([rng.choice(len(v[0]), n, p=v[1]) for v in ATTR.values()])
    p = np.full(n, BASE)
    if effect != 1.0:
        m = (x[:, TRUE_CELL[0][0]] == TRUE_CELL[0][1]) & (x[:, TRUE_CELL[1][0]] == TRUE_CELL[1][1])
        p[m] = BASE * effect
    y = rng.random(n) < p
    return x, y


def subsets(depth):
    out = []
    for k in range(1, depth + 1):
        out += list(combinations(range(len(NAMES)), k))
    return out


def cell_table(x, y, depth):
    """組み合わせごとの人数・買った人数。キーは ((項目, 値), ...)"""
    rows = []
    for s in subsets(depth):
        sizes = [len(ATTR[NAMES[i]][0]) for i in s]
        idx = np.ravel_multi_index(tuple(x[:, i] for i in s), sizes)
        nn = np.bincount(idx, minlength=int(np.prod(sizes)))
        kk = np.bincount(idx, weights=y, minlength=int(np.prod(sizes)))
        for flat in range(len(nn)):
            vals = np.unravel_index(flat, sizes)
            rows.append((tuple(zip(s, (int(v) for v in vals))), int(nn[flat]), int(kk[flat])))
    return rows


def label(key):
    return "×".join(ATTR[NAMES[i]][0][v] + ("曜" if NAMES[i] == "曜日" else "") for i, v in key)


def count_cell(x, y, key):
    m = np.ones(len(y), dtype=bool)
    for i, v in key:
        m &= x[:, i] == v
    return int(m.sum()), int(y[m].sum())


def search(x, y, depth, min_cell=MIN_CELL):
    rows = cell_table(x, y, depth)
    p_all = float(y.mean())
    keys = [r[0] for r in rows if r[1] >= min_cell]
    n = np.array([r[1] for r in rows if r[1] >= min_cell])
    k = np.array([r[2] for r in rows if r[1] >= min_cell])
    pv = binom.sf(k - 1, n, p_all)                   # 全体の割合より高いことが偶然で起きる確率（片側）
    return keys, n, k, pv, p_all


def one_rep(rng, n, depth, effect=1.0):
    x, y = make(rng, n, effect)
    keys, nn, kk, pv, p_all = search(x, y, depth)
    m = len(keys)
    b = int(np.argmin(pv))
    x2, y2 = make(rng, n, effect)
    n2, k2 = count_cell(x2, y2, keys[b])
    # 前もって決めておいた1つ（土曜×雨）
    tn, tk = count_cell(x, y, TRUE_CELL)
    tp = float(binom.sf(tk - 1, tn, p_all)) if tn > 0 else 1.0
    true_rank = None
    if TRUE_CELL in keys:
        true_rank = int((pv < pv[keys.index(TRUE_CELL)]).sum()) + 1
    return {"cells": m, "p_all": p_all, "any_p05": bool((pv < 0.05).any()), "n_p05": int((pv < 0.05).sum()),
            "any_bonf": bool((pv < 0.05 / m).any()), "best_p": float(pv[b]), "best_n": int(nn[b]),
            "best_rate": float(kk[b] / nn[b]), "best_label": label(keys[b]), "best_is_true": keys[b] == TRUE_CELL,
            "next_n": n2, "next_rate": (k2 / n2) if n2 else np.nan, "next_p_all": float(y2.mean()),
            "next_p05": bool(n2 > 0 and binom.sf(k2 - 1, n2, float(y2.mean())) < 0.05),
            "pre_p05": tp < 0.05, "pre_bonf": tp < 0.05 / m, "pre_rate": tk / tn if tn else np.nan, "true_rank": true_rank}


def summarize(df):
    return {"reps": len(df), "cells_mean": round(float(df.cells.mean()), 1),
            "any_p05_pct": round(float(df.any_p05.mean()) * 100, 1),
            "n_p05_mean": round(float(df.n_p05.mean()), 2),
            "any_bonf_pct": round(float(df.any_bonf.mean()) * 100, 1),
            "best_p_median": float(np.median(df.best_p)),
            "best_rate_mean_pct": round(float(df.best_rate.mean()) * 100, 2),
            "best_n_median": float(df.best_n.median()),
            "next_rate_mean_pct": round(float(df.next_rate.mean()) * 100, 2),
            "next_p05_pct": round(float(df.next_p05.mean()) * 100, 1),
            "pre_p05_pct": round(float(df.pre_p05.mean()) * 100, 1),
            "pre_bonf_pct": round(float(df.pre_bonf.mean()) * 100, 1),
            "best_is_true_pct": round(float(df.best_is_true.mean()) * 100, 1),
            "pre_rate_mean_pct": round(float(df.pre_rate.mean()) * 100, 2)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分のデータ（調べた月と次の月）
    x1, y1 = make(rng, N0)
    x2, y2 = make(rng, N0)
    frames = []
    for mon, (x, y) in [("調べた月", (x1, y1)), ("次の月", (x2, y2))]:
        d = pd.DataFrame({n: np.array(ATTR[n][0])[x[:, i]] for i, n in enumerate(NAMES)})
        d.insert(0, "customer_id", np.arange(1, len(y) + 1)); d.insert(0, "month", mon)
        d["dessert"] = y.astype(int)
        frames.append(d)
    pd.concat(frames).to_csv(DATA / "customers.csv", index=False)
    keys, nn, kk, pv, p_all = search(x1, y1, 2)
    order = np.argsort(pv, kind="stable")
    tops = []
    for j in order[:15]:
        n2, k2 = count_cell(x2, y2, keys[j])
        tops.append({"組み合わせ": label(keys[j]), "人数": int(nn[j]), "買った人": int(kk[j]),
                     "割合_pct": round(kk[j] / nn[j] * 100, 2), "偶然で起きる確率": float(f"{pv[j]:.3g}"),
                     "次の月の人数": n2, "次の月の割合_pct": round(k2 / n2 * 100, 2) if n2 else None})
    pd.DataFrame(tops).to_csv(RES / "one_draw_top15.csv", index=False)
    one = {"cells": len(keys), "p_all_pct": round(p_all * 100, 2), "next_p_all_pct": round(float(y2.mean()) * 100, 2),
           "n_p05": int((pv < 0.05).sum()), "n_p01": int((pv < 0.01).sum()), "any_bonf": bool((pv < 0.05 / len(keys)).any()),
           "best": tops[0], "top5_next_rate_pct": [t["次の月の割合_pct"] for t in tops[:5]]}

    # 2) 基本：2,000人・1つと2つの組み合わせ・本当の差なし、1,000回
    base = pd.DataFrame([one_rep(np.random.default_rng(SEED * 1000 + r), N0, 2) for r in range(1000)])
    sb = summarize(base)
    q = base.best_p.quantile([0.1, 0.5, 0.9]).tolist()
    sb["best_p_q10_50_90"] = [float(f"{v:.3g}") for v in q]
    sb["best_one_in_median"] = int(round(1 / sb["best_p_median"]))
    sb["best_rate_q10_90_pct"] = [round(float(v) * 100, 2) for v in base.best_rate.quantile([0.1, 0.9])]
    sb["next_rate_q10_90_pct"] = [round(float(v) * 100, 2) for v in base.next_rate.quantile([0.1, 0.9])]
    sb["best_depth2_pct"] = round(float(base.best_label.str.contains("×").mean()) * 100, 1)
    base.drop(columns=["true_rank"]).to_csv(RES / "reps_base.csv", index=False, float_format="%.6g")

    # 3) 確かめ：客の数 × 調べる深さ（本当の差なし、各200回）
    rows = []
    for n in [500, 2000, 10000]:
        for depth, name in [(1, "1つの項目だけ"), (2, "2つの組み合わせまで"), (3, "3つの組み合わせまで")]:
            d = pd.DataFrame([one_rep(np.random.default_rng(SEED * 10 + 7 * n + depth * 100 + r), n, depth) for r in range(200)])
            s = summarize(d); s.update({"customers": n, "depth": name})
            rows.append(s)
    grid = pd.DataFrame(rows)[["customers", "depth", "cells_mean", "any_p05_pct", "n_p05_mean", "any_bonf_pct",
                               "best_rate_mean_pct", "best_n_median", "next_rate_mean_pct", "next_p05_pct", "pre_p05_pct"]]
    grid.to_csv(RES / "grid_customers_depth.csv", index=False)

    # 4) 確かめ：土曜×雨だけに本当の差を置く（2,000人・2つまで、各300回）
    rows = []
    for eff in [1.0, 1.5, 2.0, 3.0]:
        d = pd.DataFrame([one_rep(np.random.default_rng(SEED * 100 + int(eff * 10) * 1000 + r), N0, 2, eff) for r in range(300)])
        s = summarize(d)
        rows.append({"effect_x": eff, "true_rate_pct": round(BASE * eff * 100, 1), "best_is_true_pct": s["best_is_true_pct"],
                     "true_rank_median": float(d.true_rank.median()), "pre_p05_pct": s["pre_p05_pct"],
                     "pre_bonf_pct": s["pre_bonf_pct"], "any_bonf_pct": s["any_bonf_pct"],
                     "best_rate_mean_pct": s["best_rate_mean_pct"], "next_rate_mean_pct": s["next_rate_mean_pct"],
                     "pre_rate_mean_pct": s["pre_rate_mean_pct"]})
    eff = pd.DataFrame(rows)
    eff.to_csv(RES / "true_effect_saturday_rain.csv", index=False)

    out = {"setup": {"attributes": {k: v[0] for k, v in ATTR.items()}, "probs": {k: v[1] for k, v in ATTR.items()},
                     "base_rate_pct": BASE * 100, "customers": N0, "min_cell": MIN_CELL,
                     "test": "片側の二項検定（その月の全体の割合より高いか）", "true_cell": "土曜×雨"},
           "one_draw": one, "base_1000reps": sb, "grid": grid.to_dict("records"),
           "grid_any_p05_range_pct": [float(grid.any_p05_pct.min()), float(grid.any_p05_pct.max())],
           "grid_any_bonf_range_pct": [float(grid.any_bonf_pct.min()), float(grid.any_bonf_pct.max())],
           "grid_next_rate_range_pct": [float(grid.next_rate_mean_pct.min()), float(grid.next_rate_mean_pct.max())],
           "true_effect": eff.to_dict("records")}
    json.dump(out, open(RES / "a988_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の組み合わせ（人数と割合）
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    rate = kk / nn * 100
    ax.scatter(nn, rate, s=12, color=LIGHT, label=f"調べた{len(keys)}の値と組み合わせ")
    sig = pv < 0.05
    ax.scatter(nn[sig], rate[sig], s=16, color=BLUE, label=f"「偶然では5%未満」に見えた{int(sig.sum())}個")
    xs = np.linspace(MIN_CELL, nn.max(), 200)
    ax.plot(xs, binom.ppf(0.95, xs.astype(int), p_all) / xs.astype(int) * 100, color=GRAY, lw=0.8, ls="--",
            label="ここより上は「偶然では5%未満」")
    ax.axhline(p_all * 100, color=INK, lw=0.8)
    b = order[0]
    bt = tops[0]
    ax.scatter([nn[b]], [rate[b]], s=50, color=ORANGE, zorder=4)
    ax.annotate(f"いちばん珍しい：{bt['組み合わせ']}\n{bt['人数']}人中{bt['割合_pct']}% → 次の月 {bt['次の月の割合_pct']}%",
                (nn[b], rate[b]), (nn[b] * 2.2, rate[b] + 1.5), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.6))
    ax.set_xscale("log"); ax.set_xlabel("その値・組み合わせの客の人数（対数の目盛り）")
    ax.set_ylabel("デザートも買った割合（%）"); ax.set_ylim(0, max(rate.max() + 14, 36))
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title(f"本当の差はどこにもない（全員10%と置いた）1か月、客{N0:,}人")
    save(fig, "a988_one_month.png", SRC)

    # 図2：1,000回の「いちばん珍しい組み合わせ」の割合と、次の月
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    bins = np.arange(0, 52, 2)
    ax.hist(base.best_rate * 100, bins=bins, color=ORANGE, alpha=0.85, label=f"調べた月（平均{sb['best_rate_mean_pct']}%）")
    ax.hist(base.next_rate * 100, bins=bins, color=BLUE, alpha=0.6, label=f"同じ組み合わせの次の月（平均{sb['next_rate_mean_pct']}%）")
    ax.axvline(BASE * 100, color=INK, lw=0.8)
    ax.set_xlabel("いちばん珍しく見えた組み合わせで、デザートも買った割合（%）"); ax.set_ylabel("回数（1,000回のうち）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("後から探した組み合わせは、次の月には全体の10%に戻る")
    save(fig, "a988_best_vs_next.png", SRC)

    # 図3：探す広さと客の数
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    deps = ["1つの項目だけ", "2つの組み合わせまで", "3つの組み合わせまで"]
    w = 0.26
    for j, (n, c) in enumerate(zip([500, 2000, 10000], [LIGHT, BLUE, INK])):
        g = grid[grid.customers == n].set_index("depth").loc[deps]
        xx = np.arange(3) + (j - 1) * w
        ax.bar(xx, g.any_p05_pct, width=w, color=c, label=f"客{n:,}人：1つでも「5%未満」が出た回")
        ax.scatter(xx, g.any_bonf_pct, marker="_", s=180, color=ORANGE, zorder=3)
        for xi, v in zip(xx, g.any_p05_pct):
            ax.text(xi, v + 1.5, f"{v:g}", ha="center", fontsize=7.5)
    ax.scatter([], [], marker="_", s=180, color=ORANGE, label="横線：基準を調べた数で割ったとき")
    ax.set_xticks(range(3)); ax.set_xticklabels([f"{d}\n（{grid[grid.depth == d].cells_mean.max():g}個まで）" for d in deps], fontsize=9)
    ax.set_ylabel("%（各200回）"); ax.set_ylim(0, 140); ax.set_yticks(range(0, 101, 20))
    ax.legend(frameon=False, fontsize=7.8, loc="upper center", ncol=2)
    ax.set_title("広く探すほど、本当の差がなくても「珍しい組み合わせ」が見つかる")
    save(fig, "a988_search_breadth.png", SRC)

    print(json.dumps({k: out[k] for k in ["one_draw", "base_1000reps", "grid_any_p05_range_pct", "grid_any_bonf_range_pct",
                                         "grid_next_rate_range_pct"]}, ensure_ascii=False, indent=1))
    print(pd.DataFrame(tops).to_string()); print(grid.to_string()); print(eff.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
