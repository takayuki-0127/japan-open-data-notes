"""907 四捨五入した割合を足すと、なぜ100%にならないのか？（架空のデータ）

架空の会社の売上の構成比（項目の数 k）を乱数で作り、整数の%に四捨五入して足したときに
100%ちょうどになる割合、ずれの大きさ、丸め方・項目の偏り・件数から出した割合での違いを数える。
"""
import json
from math import comb, factorial, floor
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 907
SRC = "架空の会社の売上の構成比（作成者が乱数で作成、seed 907）"
N_TABLE = 20000
KS = list(range(2, 13))


def half_up(x):
    return np.floor(x + 0.5)


def irwin_hall_p(n):
    """一様な丸めのずれ n 個の和 S が |S|<0.5 になる確率（k=n+1 項目の表が100%ちょうどになる式の値）"""
    if n == 0:
        return 1.0
    def F(x):
        return sum((-1) ** j * comb(n, j) * (x - j) ** n for j in range(0, floor(x) + 1)) / factorial(n)
    return F(n / 2 + 0.5) - F(n / 2 - 0.5)


def shares(rng, k, alpha, n=N_TABLE, count=None):
    p = rng.dirichlet(np.full(k, alpha), size=n)
    if count is None:
        return p * 100
    x = np.array([rng.multinomial(count, pi) for pi in p])
    return x * 100 / count


def largest_remainder(s):
    """切り捨ててから、余りの大きい順に1ずつ足して合計を100にする"""
    fl = np.floor(s)
    short = (100 - fl.sum(1)).round().astype(int)
    rem = s - fl
    order = np.argsort(-rem, axis=1, kind="stable")
    add = np.zeros_like(fl)
    for i in range(s.shape[0]):
        add[i, order[i, :short[i]]] = 1
    return fl + add


def summarize(s, rounder):
    r = rounder(s)
    tot = r.sum(1).round().astype(int)
    return {"p_exact_100": float((tot == 100).mean()), "p_99": float((tot == 99).mean()),
            "p_101": float((tot == 101).mean()), "p_le_98": float((tot <= 98).mean()),
            "p_ge_102": float((tot >= 102).mean()), "mean_total": float(tot.mean()),
            "max_abs_dev": int(np.abs(tot - 100).max())}


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    # 1) 項目の数 k ごと（基本：偏りの置き方 alpha=1、四捨五入して整数の%）
    for k in KS:
        s = shares(np.random.default_rng(SEED * 100 + k), k, 1.0)
        res = summarize(s, half_up)
        one_dec = (np.floor(s * 10 + 0.5).sum(1).round().astype(int) == 1000).mean()
        rows.append({"k": k, "formula_p_exact_100": round(irwin_hall_p(k - 1), 4),
                     **{kk: round(v, 4) if isinstance(v, float) else v for kk, v in res.items()},
                     "p_exact_100_one_decimal": round(float(one_dec), 4)})
    byk = pd.DataFrame(rows)
    byk.to_csv(RES / "by_k_items.csv", index=False)

    # 2) 確かめ：項目の偏り（alpha）× k、丸め方、件数から出した割合
    rows = []
    for alpha, alab in [(0.2, "偏りが大きい（α=0.2）"), (1.0, "基本（α=1）"), (10.0, "そろっている（α=10）")]:
        for k in [3, 5, 8, 12]:
            for cnt, clab in [(None, "売上の額から（連続）"), (200, "200件から"), (1000, "1,000件から"), (1237, "1,237件から")]:
                s = shares(np.random.default_rng(SEED * 10000 + int(alpha * 10) * 100 + k * 10 + (cnt or 0) % 97),
                           k, alpha, n=5000, count=cnt)
                for rl, fn in [("四捨五入", half_up), ("偶数への丸め", np.round), ("切り捨て", np.floor)]:
                    res = summarize(s, fn)
                    rows.append({"alpha": alab, "k": k, "source": clab, "rounding": rl,
                                 **{kk: round(v, 4) if isinstance(v, float) else v for kk, v in res.items()},
                                 "share_exact_half": round(float((np.abs(s - np.floor(s) - 0.5) < 1e-9).mean()), 4),
                                 "share_nonzero_shown_0": round(float(((s > 0) & (fn(s) == 0)).mean()), 4)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)

    # 3) 最大剰余法（切り捨てて余りの大きい順に足す）で100にそろえると、何項目が変わるか（k=8、alpha=1）
    s = shares(np.random.default_rng(SEED * 3), 8, 1.0)
    lr = largest_remainder(s); hu = half_up(s)
    changed = (lr != hu).sum(1)
    lr_res = {"k": 8, "tables": N_TABLE, "share_tables_changed": round(float((changed > 0).mean()), 4),
              "mean_items_changed_when_changed": round(float(changed[changed > 0].mean()), 3),
              "max_items_changed": int(changed.max()),
              "max_abs_error_half_up": round(float(np.abs(hu - s).max()), 3),
              "max_abs_error_largest_remainder": round(float(np.abs(lr - s).max()), 3),
              "share_items_err_ge_0_5_largest_remainder": round(float((np.abs(lr - s) >= 0.5).mean()), 4),
              "order_reversed_pairs_largest_remainder": int(sum(((s[:, i] > s[:, j]) & (lr[:, i] < lr[:, j])).sum()
                                                               for i in range(8) for j in range(8)))}

    # 4) 表示の差から本当の差は読めるか（k=8、alpha=1、四捨五入）。並んだ2項目の表示の差ごとの本当の差
    i, j = np.triu_indices(8, 1)
    disp_d = np.abs(hu[:, i] - hu[:, j]).ravel(); true_d = np.abs(s[:, i] - s[:, j]).ravel()
    diff_tab = []
    for dd in [0, 1, 2]:
        m = disp_d == dd
        diff_tab.append({"shown_diff_pt": dd, "pairs": int(m.sum()),
                         "true_diff_p10": round(float(np.quantile(true_d[m], .1)), 3),
                         "true_diff_median": round(float(np.median(true_d[m])), 3),
                         "true_diff_p90": round(float(np.quantile(true_d[m], .9)), 3),
                         "true_diff_max": round(float(true_d[m].max()), 3)})
    # 表示が同じ（差0）なのに、本当は0.5ポイント以上違う組の割合
    same_but = float((true_d[disp_d == 0] >= 0.5).mean())
    pd.DataFrame(diff_tab).to_csv(RES / "shown_vs_true_diff.csv", index=False)

    # 例の表：k=7・alpha=1 で合計が100にならない最初の表、200件から出した表
    ex = shares(np.random.default_rng(SEED * 7), 7, 1.0, n=200)
    t = np.where(half_up(ex).sum(1) != 100)[0][0]
    ex2 = shares(np.random.default_rng(SEED * 8), 7, 1.0, n=200, count=200)
    t2 = np.where(half_up(ex2).sum(1) != 100)[0][0]
    names = [f"商品{c}" for c in "ABCDEFG"]
    exdf = pd.concat([
        pd.DataFrame({"table": "売上の額から", "item": names, "true_pct": ex[t].round(4),
                      "half_up": half_up(ex[t]).astype(int), "largest_remainder": largest_remainder(ex[t:t + 1])[0].astype(int)}),
        pd.DataFrame({"table": "200件から", "item": names, "true_pct": ex2[t2].round(4),
                      "half_up": half_up(ex2[t2]).astype(int), "largest_remainder": largest_remainder(ex2[t2:t2 + 1])[0].astype(int)})])
    exdf.to_csv(DATA / "example_tables.csv", index=False)
    example = {tb: {"half_up_total": int(d.half_up.sum()), "largest_remainder_total": int(d.largest_remainder.sum()),
                    "items_exact_half": int((np.abs(d.true_pct - np.floor(d.true_pct) - 0.5) < 1e-9).sum())}
               for tb, d in exdf.groupby("table", sort=False)}

    g = grid
    def pick(alpha, k, src, rl, col="p_exact_100"):
        return float(g[(g.alpha == alpha) & (g.k == k) & (g.source == src) & (g.rounding == rl)][col].iloc[0])
    key = {
        "k8_alpha_range_p_exact": [round(pick(a, 8, "売上の額から（連続）", "四捨五入"), 4) for a in g.alpha.unique()],
        "k12_alpha02_nonzero_shown0": pick("偏りが大きい（α=0.2）", 12, "売上の額から（連続）", "四捨五入", "share_nonzero_shown_0"),
        "k12_alpha02_mean_total": pick("偏りが大きい（α=0.2）", 12, "売上の額から（連続）", "四捨五入", "mean_total"),
        "k8_n200_halfup_mean_total": pick("基本（α=1）", 8, "200件から", "四捨五入", "mean_total"),
        "k8_n200_halfup_p_exact": pick("基本（α=1）", 8, "200件から", "四捨五入"),
        "k8_n200_halfup_p_ge101": round(pick("基本（α=1）", 8, "200件から", "四捨五入", "p_101") +
                                        pick("基本（α=1）", 8, "200件から", "四捨五入", "p_ge_102"), 4),
        "k8_n200_even_mean_total": pick("基本（α=1）", 8, "200件から", "偶数への丸め", "mean_total"),
        "k8_n200_even_p_exact": pick("基本（α=1）", 8, "200件から", "偶数への丸め"),
        "k8_n200_share_exact_half": pick("基本（α=1）", 8, "200件から", "四捨五入", "share_exact_half"),
        "k8_cont_halfup_mean_total": pick("基本（α=1）", 8, "売上の額から（連続）", "四捨五入", "mean_total"),
        "k8_cont_floor_mean_total": pick("基本（α=1）", 8, "売上の額から（連続）", "切り捨て", "mean_total"),
        "k8_cont_floor_p_exact": pick("基本（α=1）", 8, "売上の額から（連続）", "切り捨て"),
        "halfup_p_exact_min": float(g[g.rounding == "四捨五入"].p_exact_100.min()),
        "halfup_p_exact_max": float(g[g.rounding == "四捨五入"].p_exact_100.max()),
    }
    max_dev_k12 = int(byk[byk.k == 12].max_abs_dev.iloc[0])
    out = {"by_k": byk.to_dict("records"), "max_sim_minus_formula": round(float((byk.p_exact_100 - byk.formula_p_exact_100).abs().max()), 4),
           "key": key, "largest_remainder_k8": lr_res, "shown_vs_true_diff_k8": diff_tab,
           "shown_same_but_true_ge_0_5": round(same_but, 4), "max_abs_dev_k12": max_dev_k12, "example_tables": example,
           "rounding_examples": {f"{v}": {"half_up": int(half_up(np.array([v]))[0]), "shift": round(float(half_up(np.array([v]))[0] - v), 1)}
                                 for v in [12.4, 13.6, 12.5, 23.5]},
           "one_case_pct_when_200": 100 / 200}
    json.dump(out, open(RES / "a907_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：項目の数ごとの、100%ちょうどになる割合（シミュレーションと式）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(byk.k, byk.p_exact_100 * 100, "o-", color=BLUE, label="架空の表2万枚で数えた値（整数の%）")
    ax.plot(byk.k, byk.formula_p_exact_100 * 100, "x", color=INK, ms=8, label="式の値（丸めのずれが一様と置いた値）")
    ax.plot(byk.k, byk.p_exact_100_one_decimal * 100, "s--", color=GREEN, ms=5, label="小数1けたまで出した場合")
    for x, v in zip(byk.k, byk.p_exact_100 * 100):
        ax.text(x + 0.12, v - 7, f"{v:.0f}%", ha="center", fontsize=8, color=BLUE)
    ax.set_xticks(KS); ax.set_ylim(0, 105); ax.set_xlabel("構成比の項目の数")
    ax.set_ylabel("足すと100%ちょうどになる表の割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("項目が増えるほど、四捨五入した割合の合計は100%から外れやすい")
    save(fig, "a907_exact_by_k.png", SRC)

    # 図2：合計の分布（k=3,8,12）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    labs = ["98以下", "99", "100", "101", "102以上"]; x = np.arange(5); w = 0.26
    for jj, (k, col) in enumerate([(3, LIGHT), (8, BLUE), (12, INK)]):
        r = byk[byk.k == k].iloc[0]
        v = np.array([r.p_le_98, r.p_99, r.p_exact_100, r.p_101, r.p_ge_102]) * 100
        ax.bar(x + (jj - 1) * w, v, w, color=col, label=f"{k}項目")
        for xi, vi in zip(x, v):
            if vi >= 0.5:
                ax.text(xi + (jj - 1) * w, vi + 1, f"{vi:.0f}", ha="center", fontsize=7.5)
    ax.set_xticks(x, labs); ax.set_xlabel("四捨五入した割合の合計（%）"); ax.set_ylabel("表の割合（%）")
    ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, 85)
    ax.set_title("ずれは99%か101%がほとんど。項目が多いと98%以下・102%以上も出る")
    save(fig, "a907_total_dist.png", SRC)

    # 図3：件数から出した割合（k=8）での合計の平均：丸め方ごと
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    sub = g[(g.alpha == "基本（α=1）") & (g.k == 8)]
    srcs = ["売上の額から（連続）", "200件から", "1,000件から", "1,237件から"]
    x = np.arange(len(srcs)); w = 0.26
    for jj, (rl, col) in enumerate([("四捨五入", BLUE), ("偶数への丸め", GREEN), ("切り捨て", GRAY)]):
        v = [float(sub[(sub.source == sc) & (sub.rounding == rl)].mean_total.iloc[0]) for sc in srcs]
        ax.bar(x + (jj - 1) * w, np.array(v) - 100, w, color=col, label=rl)
        for xi, vi in zip(x, v):
            ax.text(xi + (jj - 1) * w, vi - 100 + (0.08 if vi >= 100 else -0.08), f"{vi:.1f}", ha="center",
                    va="bottom" if vi >= 100 else "top", fontsize=7.5)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(x, srcs); ax.set_ylabel("合計の平均と100%の差（ポイント）"); ax.text(0.01, 0.02, "棒の数字は合計の平均（%）", transform=ax.transAxes, fontsize=8.5, color=GRAY); ax.set_ylim(-4.8, 2.9)
    ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=3)
    ax.set_title("200件から出した割合は「.5ちょうど」が多く、四捨五入で合計が上にずれる（8項目）")
    save(fig, "a907_by_source.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
