"""1015 足し算か掛け算かで、苦手な項目の効き方はどう変わるのか？（架空のデータ）

架空のハンディ掃除機120製品。4項目（吸う力・使いやすさ・静かさ・電池の持ち）を1〜10点（0.1点きざみ）で付け、
足し算（4項目の平均）と掛け算（4項目の積の4乗根＝幾何平均。どちらも1〜10点の物差しにそろう）で総合点を出す。
苦手な項目（いちばん低い項目）が総合点と順位にどう効くかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1015
SRC = "架空のハンディ掃除機120製品の項目の点（作成者が乱数で作成、seed 1015）"
ITEMS = ["吸う力", "使いやすさ", "静かさ", "電池の持ち"]
N_PROD, MEAN, SD, RHO = 120, 6.5, 1.8, 0.0


def make_items(rng, n=N_PROD, sd=SD, rho=RHO):
    cov = sd ** 2 * (rho * np.ones((4, 4)) + (1 - rho) * np.eye(4))
    x = rng.multivariate_normal(np.full(4, MEAN), cov, n)
    return np.round(np.clip(x, 1, 10), 1)


def add_score(x):
    return x.mean(1)


def mul_score(x):
    with np.errstate(divide="ignore"):
        return np.exp(np.log(x).mean(1))


def rank_desc(x):
    r = np.empty(len(x), int)
    r[np.argsort(-x, kind="stable")] = np.arange(1, len(x) + 1)
    return r


def top_overlap(a, b, k=10):
    return len(set(np.argsort(-a, kind="stable")[:k]) & set(np.argsort(-b, kind="stable")[:k]))


def compare(x, k=10):
    a, m = add_score(x), mul_score(x)
    ra, rm = rank_desc(a), rank_desc(m)
    return dict(top10_overlap=top_overlap(a, m, k), move10_pct=100 * float((np.abs(ra - rm) >= 10).mean()),
                spearman=float(np.corrcoef(ra, rm)[0, 1]), max_move=int(np.abs(ra - rm).max()))


def raise_gain(x, score_fn, which):
    """1製品ずつ、いちばん低い（高い）項目を1点上げ、ほかの製品はそのままで順位がいくつ上がるか"""
    base = score_fn(x)
    gains, dscore = [], []
    for i in range(len(x)):
        y = x[i].copy()
        j = int(np.argmin(y)) if which == "weak" else int(np.argmax(y))
        y[j] += 1.0
        s_new = score_fn(y[None, :])[0]
        others = np.delete(base, i)
        r_old = 1 + (others > base[i] + 1e-9).sum()
        r_new = 1 + (others > s_new + 1e-9).sum()
        gains.append(r_old - r_new); dscore.append(s_new - base[i])
    return np.array(gains), np.array(dscore)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    x = make_items(rng)
    a, m = add_score(x), mul_score(x)
    ra, rm = rank_desc(a), rank_desc(m)
    df = pd.DataFrame(x, columns=[f"item{j + 1}_{n}" for j, n in enumerate(ITEMS)])
    df.insert(0, "product_id", np.arange(1, N_PROD + 1))
    df["add_score"] = a.round(3); df["mul_score"] = m.round(3)
    df["add_rank"] = ra; df["mul_rank"] = rm
    df.to_csv(DATA / "products.csv", index=False)

    lo, hi = x.min(1), x.max(1)
    move = rm - ra   # ＋：掛け算で順位が下がる
    res = compare(x)
    top20_add, top20_mul = ra <= 20, rm <= 20
    # 例：同じ平均8点
    ex = np.array([[8, 8, 8, 8], [10, 10, 10, 2], [9, 9, 9, 5]], float)
    example = [{"items": e.tolist(), "add": round(float(add_score(e[None])[0]), 2),
                "mul": round(float(mul_score(e[None])[0]), 2)} for e in ex]

    # 苦手・得意を1点上げたとき（ほかの製品はそのまま）
    ok = hi <= 9.0   # 得意な項目も1点上げられる製品だけ
    gain = {}
    rows = []
    for name, fn in [("足し算", add_score), ("掛け算", mul_score)]:
        for which, lab in [("weak", "いちばん低い項目を1点上げる"), ("strong", "いちばん高い項目を1点上げる")]:
            g, d = raise_gain(x, fn, which)
            gain[(name, which)] = (g, d)
            rows.append({"score": name, "change": lab, "products": int(ok.sum()),
                         "score_gain_mean": round(float(d[ok].mean()), 3),
                         "rank_gain_median": float(np.median(g[ok])), "rank_gain_mean": round(float(g[ok].mean()), 2)})
    raise_tab = pd.DataFrame(rows)
    raise_tab.to_csv(RES / "raise_one_item.csv", index=False)
    # 掛け算で、苦手1点と得意1点の効きの比（式では ≒ 高い項目÷低い項目）
    dw, ds = gain[("掛け算", "weak")][1][ok], gain[("掛け算", "strong")][1][ok]
    ratio_sim = dw / ds
    ratio_formula = (hi / lo)[ok]

    # 確かめ1：項目どうしの似かた × 項目の散らばり（12通り、各300回）
    grid = []
    for rho in [-0.3, 0.0, 0.3, 0.6, 0.9]:
        for sd in [1.0, 1.8, 2.6]:
            rr = np.random.default_rng(SEED * 100 + int(round((rho + 0.5) * 10)) * 100 + int(round(sd * 10)))
            cs = [compare(make_items(rr, sd=sd, rho=rho)) for _ in range(300)]
            grid.append({"rho": rho, "item_sd": sd,
                         "top10_overlap_mean": round(np.mean([c["top10_overlap"] for c in cs]), 2),
                         "move10_pct": round(np.mean([c["move10_pct"] for c in cs]), 2),
                         "spearman": round(np.mean([c["spearman"] for c in cs]), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_rho_sd.csv", index=False)

    # 確かめ2：物差しの下の端（同じ点に一定の数を足して掛け算する）
    offs = []
    rr = np.random.default_rng(SEED * 1000)
    sets = [make_items(rr) for _ in range(300)]
    for off, lab in [(-1.0, "0〜9点（1を引く）"), (0.0, "1〜10点（基本）"), (5.0, "6〜15点（5を足す）"), (10.0, "11〜20点（10を足す）")]:
        ov, mv, zero = [], [], []
        for s in sets:
            y = s + off
            zero.append(100 * float((y.min(1) <= 0).mean()))
            ov.append(top_overlap(add_score(y), mul_score(np.maximum(y, 0.0))))
            mv.append(100 * float((np.abs(rank_desc(add_score(y)) - rank_desc(mul_score(np.maximum(y, 0.0)))) >= 10).mean()))
        offs.append({"scale": lab, "offset": off, "top10_overlap_mean": round(float(np.mean(ov)), 2),
                     "move10_pct": round(float(np.mean(mv)), 2), "products_with_zero_pct": round(float(np.mean(zero)), 2)})
    offs = pd.DataFrame(offs)
    offs.to_csv(RES / "scale_offset.csv", index=False)
    # 確かめ3：4項目がすべて同じ点なら、足し算と掛け算は同じ順位
    same = np.repeat(np.round(rng.uniform(1, 10, (N_PROD, 1)), 1), 4, 1)
    same_check = bool((rank_desc(add_score(same)) == rank_desc(mul_score(same))).all())

    main_json = {
        "seed": SEED, "products": N_PROD,
        "examples_same_mean": example,
        "one_set": {
            "top10_overlap": res["top10_overlap"], "spearman": round(res["spearman"], 3),
            "move10_pct": round(res["move10_pct"], 2), "move10_products": int((np.abs(move) >= 10).sum()),
            "max_move": res["max_move"],
            "corr_min_item_vs_move": round(float(np.corrcoef(lo, -move)[0, 1]), 3),
            "down_min_item_median": float(np.median(lo[move > 0])),
            "up_min_item_median": float(np.median(lo[move < 0])),
            "all_min_item_median": float(np.median(lo)),
            "top20_overlap": int((top20_add & top20_mul).sum()),
            "top20_out_by_mul_min_items": sorted(lo[top20_add & ~top20_mul].tolist()),
            "top20_in_by_mul_min_items": sorted(lo[top20_mul & ~top20_add].tolist()),
            "top20_add_min_item_median": float(np.median(lo[top20_add])),
            "products_min_le4": int((lo <= 4).sum()),
            "move10_add_rank_range": [int(ra[np.abs(move) >= 10].min()), int(ra[np.abs(move) >= 10].max())],
            "max_move_product": {"product_id": int(np.argmax(np.abs(move)) + 1),
                                 "items": x[np.argmax(np.abs(move))].tolist(),
                                 "add_rank": int(ra[np.argmax(np.abs(move))]), "mul_rank": int(rm[np.argmax(np.abs(move))]),
                                 "add": round(float(a[np.argmax(np.abs(move))]), 2), "mul": round(float(m[np.argmax(np.abs(move))]), 2)},
        },
        "raise_one_item": {
            "products_used": int(ok.sum()),
            "mul_weak_over_strong_median": round(float(np.median(ratio_sim)), 2),
            "mul_weak_over_strong_range": [round(float(ratio_sim.min()), 2), round(float(ratio_sim.max()), 2)],
            "formula_hi_over_lo_median": round(float(np.median(ratio_formula)), 2),
        },
        "grid_ranges": {"top10_overlap_mean": [float(grid.top10_overlap_mean.min()), float(grid.top10_overlap_mean.max())],
                        "move10_pct": [float(grid.move10_pct.min()), float(grid.move10_pct.max())]},
        "all_items_equal_same_rank": same_check,
    }

    # 図1：足し算の点と掛け算の点
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    weak = lo <= 4
    ax.plot([2, 9.5], [2, 9.5], color=GRAY, lw=0.8, ls="--")
    ax.text(3.0, 2.4, "点線：足し算＝掛け算", color=GRAY, fontsize=8, ha="left")
    ax.scatter(a[~weak], m[~weak], s=20, color=BLUE, label="いちばん低い項目が4点より上")
    ax.scatter(a[weak], m[weak], s=22, color=ORANGE, label="いちばん低い項目が4点以下")
    ax.set_xlabel("足し算（4項目の平均、点）")
    ax.set_ylabel("掛け算（4項目の幾何平均、点）")
    ax.set_title("苦手な項目のある製品ほど、掛け算で下がる", loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1015_scatter.png", SRC + "。1〜10点、0.1点きざみ")

    # 図2：1点上げたときの順位の上がり方
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    xs = np.arange(2)
    for k, (which, c, lab) in enumerate([("weak", ORANGE, "いちばん低い項目を1点上げる"), ("strong", BLUE, "いちばん高い項目を1点上げる")]):
        v = [raise_tab[(raise_tab.score == s) & (raise_tab.change == lab)].rank_gain_mean.iloc[0] for s in ["足し算", "掛け算"]]
        ax.bar(xs + (k - 0.5) * 0.36, v, width=0.34, color=c, label=lab)
        for xx, vv in zip(xs + (k - 0.5) * 0.36, v):
            ax.text(xx, vv + 0.3, f"{vv:.1f}位", ha="center", fontsize=9, color=INK)
    ax.set_xticks(xs); ax.set_xticklabels(["足し算", "掛け算"])
    ax.set_ylabel("順位が上がった数（平均）")
    ax.set_ylim(0, max(raise_tab.rank_gain_mean) * 1.3)
    ax.set_title("掛け算では、苦手な項目を上げるほうが順位が上がる", loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1015_raise.png", SRC + "。いちばん高い項目が9点以下の%d製品。ほかの製品はそのまま" % ok.sum())

    # 図3：確かめ（項目の似かた・物差しの下の端）
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.0))
    ax = axs[0]
    for sd, c, lab in [(1.0, GRAY, "項目の散らばり 1.0"), (1.8, BLUE, "1.8（基本）"), (2.6, ORANGE, "2.6")]:
        g = grid[grid.item_sd == sd]
        ax.plot(g.rho, g.move10_pct, marker="o", color=c, lw=2, label=lab)
    ax.set_xlabel("項目どうしの相関（似かた）")
    ax.set_ylabel("順位が10位以上動いた製品の割合（%）")
    ax.set_ylim(0, 70); ax.set_xticks([-0.3, 0, 0.3, 0.6, 0.9])
    ax.set_title("項目が似ているほど、順位は動かない", loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax = axs[1]
    ax.bar(np.arange(len(offs)), offs.move10_pct, color=[ORANGE, BLUE, LIGHT, LIGHT], width=0.6)
    for i, v in enumerate(offs.move10_pct):
        ax.text(i, v + 1.0, f"{v:.1f}%", ha="center", fontsize=9, color=INK)
    ax.set_xticks(np.arange(len(offs)))
    ax.set_xticklabels([s.replace("（", "\n（") for s in offs.scale], fontsize=8.5)
    ax.set_ylim(0, 70)
    ax.set_ylabel("順位が10位以上動いた製品の割合（%）")
    ax.set_title("同じ点でも、物差しの下の端で効き方が変わる", loc="left", fontsize=11)
    fig.tight_layout()
    save(fig, "a1015_robust.png", SRC + "。左は15通り、右は4通り、各300回。足し算の順位と掛け算の順位の差が10以上の製品の割合")

    with open(RES / "a1015_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(raise_tab.to_string()); print(grid.to_string()); print(offs.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
