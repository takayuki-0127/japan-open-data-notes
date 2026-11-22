"""918 不良の原因の上位を、件数で並べるか損失で並べるかで変わるのか？（架空のデータ）

架空の工場の1つの部品。不良の原因は12種類。原因ごとに「本当の月の件数」と「1件の平均の損失」を置く。
1件の損失はその平均のまわりで散らばる（対数正規）。損失は円ではなく指数（全体の1件の平均を1）。
本当の上位（件数の期待値の順・損失の期待値の順）が分かっているので、数えた順位がどれだけ当たるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 918
SRC = "架空の工場の不良の記録（作成者が乱数で作成、seed 918）"
K = 12
TOTAL = 300          # 1か月の不良の件数（期待値）
SIG_F = 1.0          # 原因ごとの件数の差（対数の標準偏差）
NAMES = [chr(ord("A") + i) for i in range(K)]
N_REP = 300


def make_causes(rng, sig_c=1.0, rho=0.0, total=TOTAL):
    zf = rng.normal(0, 1, K)
    zf = (zf - zf.mean()) / zf.std()
    lam = np.exp(SIG_F * zf)
    lam = lam / lam.sum() * total
    zc = rho * zf + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, K)
    c = np.exp(sig_c * zc)
    c = c / (c * lam).sum() * lam.sum()   # 全体の1件の平均の損失を1にそろえる
    return lam, c


def observe(rng, lam, c, months, sig_case=1.0):
    n = rng.poisson(lam * months)
    loss = np.array([(ci * rng.lognormal(-sig_case ** 2 / 2, sig_case, k)).sum() if k > 0 else 0.0
                     for ci, k in zip(c, n)])
    return n, loss


def top(x, k=3):
    return set(np.argsort(-np.asarray(x), kind="stable")[:k])


def true_metrics(lam, c):
    el = lam * c
    tc, tl = top(lam), top(el)
    return {"overlap3": len(tc & tl) / 3, "top1_same": float(np.argmax(lam) == np.argmax(el)),
            "loss_share_by_count_top3": el[list(tc)].sum() / el.sum(),
            "loss_share_by_loss_top3": el[list(tl)].sum() / el.sum(),
            "count_share_by_count_top3": lam[list(tc)].sum() / lam.sum()}


def main():
    rng = np.random.default_rng(SEED)

    # 1) 1つの工場の12か月（data に1件ずつ置く）
    lam, c = make_causes(rng)
    rows = []
    for m in range(1, 13):
        n = rng.poisson(lam)
        for k in range(K):
            for v in c[k] * rng.lognormal(-0.5, 1.0, n[k]):
                rows.append({"month": m, "cause": NAMES[k], "loss": round(float(v), 4)})
    cases = pd.DataFrame(rows)
    cases.to_csv(DATA / "defects_one_factory_12months.csv", index=False)
    g = cases.groupby("cause").agg(count=("loss", "size"), loss=("loss", "sum")).reindex(NAMES, fill_value=0)
    g["true_count_per_month"] = lam.round(3)
    g["true_mean_loss_per_case"] = c.round(3)
    g["true_loss_per_month"] = (lam * c).round(3)
    g["loss"] = g["loss"].round(3)
    g["rank_count"] = g["count"].rank(ascending=False, method="first").astype(int)
    g["rank_loss"] = g["loss"].rank(ascending=False, method="first").astype(int)
    g.to_csv(RES / "causes_one_factory.csv")
    one = {"total_count": int(g["count"].sum()), "total_loss": round(float(g["loss"].sum()), 2),
           "count_top3": sorted(g.nsmallest(3, "rank_count").index.tolist()),
           "loss_top3": sorted(g.nsmallest(3, "rank_loss").index.tolist()),
           "count_top1": g["rank_count"].idxmin(), "loss_top1": g["rank_loss"].idxmin(),
           "count_top1_rank_in_loss": int(g.loc[g["rank_count"].idxmin(), "rank_loss"]),
           "loss_top1_rank_in_count": int(g.loc[g["rank_loss"].idxmin(), "rank_count"]),
           "count_top3_share_of_count": round(float(g.nsmallest(3, "rank_count")["count"].sum() / g["count"].sum()), 3),
           "count_top3_share_of_loss": round(float(g.nsmallest(3, "rank_count")["loss"].sum() / g["loss"].sum()), 3),
           "loss_top3_share_of_loss": round(float(g.nsmallest(3, "rank_loss")["loss"].sum() / g["loss"].sum()), 3)}

    # 2) 本当の値どうしで：件数の上位3と損失の上位3はどれだけ重なるか（原因の差・相関を変える）
    grid = []
    for sig_c in [0.0, 0.5, 1.0, 1.5]:
        for rho in [-0.5, 0.0, 0.5]:
            r2 = np.random.default_rng(SEED * 100 + int(sig_c * 10) * 10 + int((rho + 1) * 2))
            ms = pd.DataFrame([true_metrics(*make_causes(r2, sig_c, rho)) for _ in range(N_REP)]).mean()
            grid.append({"sig_cost": sig_c, "rho": rho, **ms.round(3).to_dict()})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_true_overlap.csv", index=False)

    # 3) 数えた期間で：数えた件数の順・数えた損失の順は、本当の損失の上位3をどれだけ当てるか
    hits = []
    for total in [300, 30]:
      for sig_case in [0.5, 1.0, 1.5]:
        for months in [1, 3, 6, 12]:
            r3 = np.random.default_rng(SEED * 1000 + total * 10000 + int(sig_case * 10) * 100 + months)
            acc = []
            for _ in range(N_REP):
                lam_, c_ = make_causes(r3, total=total)
                n, loss = observe(r3, lam_, c_, months, sig_case)
                tl, tc = top(lam_ * c_), top(lam_)
                acc.append({"count_rank_hit_loss_top3": len(top(n) & tl) / 3,
                            "loss_rank_hit_loss_top3": len(top(loss) & tl) / 3,
                            "count_rank_hit_count_top3": len(top(n) & tc) / 3,
                            "loss_rank_top1_right": float(np.argmax(loss) == np.argmax(lam_ * c_)),
                            "count_rank_top1_right_for_loss": float(np.argmax(n) == np.argmax(lam_ * c_))})
            hits.append({"defects_per_month": total, "sig_case": sig_case, "months": months, **pd.DataFrame(acc).mean().round(3).to_dict()})
    hits = pd.DataFrame(hits)
    hits.to_csv(RES / "hits_by_months.csv", index=False)

    base_true = grid[(grid.sig_cost == 1.0) & (grid.rho == 0.0)].iloc[0].to_dict()
    nz = grid[grid.sig_cost > 0]
    out = {"settings": {"causes": K, "defects_per_month": TOTAL, "sig_freq": SIG_F, "sig_cost_base": 1.0,
                        "rho_base": 0.0, "sig_case_base": 1.0, "reps": N_REP},
           "one_factory_12months": one,
           "true_base": base_true,
           "true_grid_range_sig_cost_gt0": {"overlap3_min": float(nz.overlap3.min()), "overlap3_max": float(nz.overlap3.max()),
                                            "top1_same_min": float(nz.top1_same.min()), "top1_same_max": float(nz.top1_same.max()),
                                            "loss_share_by_count_top3_min": float(nz.loss_share_by_count_top3.min()),
                                            "loss_share_by_count_top3_max": float(nz.loss_share_by_count_top3.max())},
           "true_sig_cost0": grid[grid.sig_cost == 0].iloc[0].to_dict(),
           "hits_summary": {"cells": int(len(hits)),
                            "loss_minus_count_min": round(float((hits.loss_rank_hit_loss_top3 - hits.count_rank_hit_loss_top3).min()), 3),
                            "loss_minus_count_max": round(float((hits.loss_rank_hit_loss_top3 - hits.count_rank_hit_loss_top3).max()), 3),
                            "count_rank_hit_loss_top3_min": float(hits.count_rank_hit_loss_top3.min()),
                            "count_rank_hit_loss_top3_max": float(hits.count_rank_hit_loss_top3.max()),
                            "loss_rank_hit_loss_top3_min": float(hits.loss_rank_hit_loss_top3.min()),
                            "loss_rank_hit_loss_top3_max": float(hits.loss_rank_hit_loss_top3.max())},
           "hits_by_months": hits.to_dict("records")}
    json.dump(out, open(RES / "a918_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1つの工場の12か月を、件数の順と損失の順で
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.4))
    loss_top = set(g.nsmallest(3, "rank_loss").index)
    count_top = set(g.nsmallest(3, "rank_count").index)
    gc = g.sort_values("count")
    axs[0].barh(gc.index, gc["count"], color=[ORANGE if i in loss_top else LIGHT for i in gc.index])
    axs[0].set_title("件数の順（12か月の合計）", fontsize=11); axs[0].set_xlabel("件数")
    gl = g.sort_values("loss")
    axs[1].barh(gl.index, gl["loss"], color=[ORANGE if i in loss_top else LIGHT for i in gl.index])
    axs[1].set_title("損失の順（12か月の合計、指数）", fontsize=11); axs[1].set_xlabel("損失（1件の平均を1とする指数）")
    for ax in axs:
        ax.set_ylabel("不良の原因")
    fig.suptitle(f"同じ12か月の記録でも、件数の上位3（{'・'.join(sorted(count_top))}）と損失の上位3（{'・'.join(sorted(loss_top))}）は違う\n"
                 "（オレンジ＝損失の上位3）", fontsize=12)
    fig.tight_layout()
    save(fig, "a918_pareto_one.png", SRC)

    # 図2：本当の値どうしの重なり（原因ごとの1件の損失の差と、件数との相関で）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for rho, col, lab in [(-0.5, ORANGE, "よく起きる原因ほど1件が安い（相関−0.5）"), (0.0, BLUE, "関係なし（相関0、基本）"),
                          (0.5, GREEN, "よく起きる原因ほど1件が高い（相関+0.5）")]:
        s = grid[grid.rho == rho]
        ax.plot(s.sig_cost, s.overlap3 * 100, "o-", color=col, label=lab)
    ax.set_xticks([0, 0.5, 1.0, 1.5]); ax.set_xticklabels(["0（どれも同じ）", "0.5", "1.0（基本）", "1.5"])
    ax.set_xlabel("原因ごとの1件の平均の損失の差（対数の標準偏差）"); ax.set_ylabel("上位3の重なり（%、300工場の平均）")
    ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("1件の損失が原因ごとに違うほど、件数の上位3と損失の上位3はずれる")
    save(fig, "a918_overlap_grid.png", SRC)

    # 図3：数えた期間と当たり（1か月の不良300件・30件）
    fig, axs = plt.subplots(1, 2, figsize=(8.8, 4.0), sharey=True)
    for ax, total in zip(axs, [300, 30]):
        for sc, ls in [(0.5, ":"), (1.0, "-"), (1.5, "--")]:
            s = hits[(hits.defects_per_month == total) & (hits.sig_case == sc)]
            ax.plot(s.months, s.loss_rank_hit_loss_top3 * 100, ls, marker="o", color=ORANGE,
                    label=f"損失の順（1件の散らばり{sc}）")
        s = hits[(hits.defects_per_month == total) & (hits.sig_case == 1.0)]
        ax.plot(s.months, s.count_rank_hit_loss_top3 * 100, "-", marker="s", color=BLUE, label="件数の順（1件の散らばり1.0）")
        ax.set_xticks([1, 3, 6, 12]); ax.set_xlabel("数えた期間（か月）"); ax.set_ylim(0, 105)
        ax.set_title(f"不良が1か月に{total}件の工場", fontsize=11)
    axs[0].set_ylabel("本当の損失の上位3を当てた割合（%）")
    axs[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("件数の順は長く数えても損失の上位3を6割ほどしか当てない。損失の順は件数が少ないと1か月では振れる", fontsize=11)
    fig.tight_layout()
    save(fig, "a918_hits_months.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
