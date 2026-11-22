"""939 項目ごとの点を足すときの重みで、順位は入れ替わるのか？（架空のデータ）

架空の会社の1チーム（基本30人）。評価の項目は4つ（成果・業務の質・協働・改善）で、それぞれ1〜5の5段階。
項目どうしの結びつき（相関）と、項目ごとの点の散らばりを作成者が置く。
「どの重みが正しいか」は扱わず、重みの選び方だけで順位がどれだけ動くかを数える。
"""
import json
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 939
SRC = "架空の会社のチームの評価（作成者が乱数で作成、seed 939）"
rng = np.random.default_rng(SEED)

ITEMS = ["成果", "業務の質", "協働", "改善"]
SPREAD = np.array([1.0, 0.8, 0.5, 0.6])  # 5段階に丸める前の散らばり（項目ごと）
BASE = {"n": 30, "rho": 0.5, "discrete": True}
N_TEAM = 1000
WEIGHTS = {"均等": [0.25, 0.25, 0.25, 0.25],
           "成果重視": [0.4, 0.2, 0.2, 0.2],
           "成果を強く": [0.55, 0.15, 0.15, 0.15],
           "協働重視": [0.2, 0.2, 0.4, 0.2],
           "改善重視": [0.2, 0.2, 0.2, 0.4]}
WN = list(WEIGHTS)
WM = np.array([WEIGHTS[k] for k in WN])  # 5×4
# 各項目0.1以上・0.05刻みで合計1になる重みの組（455通り）
GRID = np.array([[0.1 + 0.05 * a for a in c] for c in
                 itertools.product(range(13), repeat=4) if sum(c) == 12])


def make_team(rng, n=30, rho=0.5, discrete=True, **_):
    cov = np.full((4, 4), rho) + np.eye(4) * (1 - rho)
    z = rng.multivariate_normal(np.zeros(4), cov, n)
    x = 3.2 + z * SPREAD
    if discrete:
        x = np.clip(np.round(x), 1, 5)
    return x


def ranks(s):
    """大きい順の順位（同点は同じ順位、いちばん良い順位をとる）"""
    return (s[:, None] < s[None, :]).sum(1) + 1


def team_stats(x, top=3):
    n = len(x)
    tot = np.round(x @ WM.T, 9)  # n×5（小数の誤差で同点が崩れないように丸める）
    rk = np.stack([ranks(tot[:, k]) for k in range(5)], 1)
    first = [set(np.where(rk[:, k] == 1)[0]) for k in range(5)]
    first_unique_all = all(len(f) == 1 for f in first) and len(set.union(*first)) == 1
    topset = [set(np.where(rk[:, k] <= top)[0]) for k in range(5)]
    # 均等と協働重視の上位3人の重なり（同点で3人を超えるときは、重なった人数÷その組の人数×3）
    a, b = topset[0], topset[3]
    overlap = len(a & b) / max(len(a), len(b)) * top
    # 3位の境目の同点（均等で、3位の点と同じ点の人が3位以内の外にもいる）
    s0 = np.sort(tot[:, 0])[::-1]
    tie_at_3 = bool(s0[top - 1] == s0[top])
    move = np.abs(rk[:, 3] - rk[:, 0])
    maxmove = (rk.max(1) - rk.min(1))
    # 重みの組455通りで、1位になれる人・上位3人に入れる人
    g = np.round(x @ GRID.T, 9)  # n×455
    best = g.max(0)
    can1 = (g == best[None, :]).any(1)
    thr = np.sort(g, 0)[::-1][top - 1]
    can3 = (g >= thr[None, :]).any(1)
    # 均等の合計に対する項目ごとの実際の効き（合計の散らばりへの寄与）
    S = tot[:, 0]
    cov = np.array([np.cov(x[:, j], S)[0, 1] for j in range(4)])
    eff = 0.25 * cov / S.var(ddof=1)
    return {"first_same_all5": first_unique_all,
            "top3_overlap_equal_vs_collab": overlap,
            "tie_at_3rd_equal": tie_at_3,
            "share_move_ge5_equal_vs_collab": float((move >= 5).mean()) if n >= 10 else np.nan,
            "mean_max_rank_range": float(maxmove.mean()),
            "n_can_be_1st": int(can1.sum()), "n_can_be_top3": int(can3.sum()),
            "n_union_top3_5weights": len(set.union(*topset)),
            "spearman_equal_vs_collab": float(pd.Series(tot[:, 0]).rank().corr(pd.Series(tot[:, 3]).rank())),
            "eff": eff}


def summarize(stats):
    df = pd.DataFrame([{k: v for k, v in s.items() if k != "eff"} for s in stats])
    eff = np.array([s["eff"] for s in stats])
    out = {"P_first_same_all5": round(float(df.first_same_all5.mean()), 3),
           "top3_overlap_mean": round(float(df.top3_overlap_equal_vs_collab.mean()), 2),
           "P_tie_at_3rd": round(float(df.tie_at_3rd_equal.mean()), 3),
           "share_move_ge5": round(float(df.share_move_ge5_equal_vs_collab.mean()), 3),
           "mean_max_rank_range": round(float(df.mean_max_rank_range.mean()), 2),
           "n_can_be_1st_mean": round(float(df.n_can_be_1st.mean()), 2),
           "n_can_be_1st_p10": float(df.n_can_be_1st.quantile(.1)),
           "n_can_be_1st_p90": float(df.n_can_be_1st.quantile(.9)),
           "n_can_be_top3_mean": round(float(df.n_can_be_top3.mean()), 2),
           "n_union_top3_5weights_mean": round(float(df.n_union_top3_5weights.mean()), 2),
           "spearman_mean": round(float(df.spearman_equal_vs_collab.mean()), 3),
           "eff_share_equal": {ITEMS[j]: round(float(eff[:, j].mean()), 3) for j in range(4)}}
    return out, df


def formula_corr(rho, w, v, spread=SPREAD):
    """丸めないときの、2つの重みの合計どうしの相関（式）"""
    cov = (np.full((4, 4), rho) + np.eye(4) * (1 - rho)) * np.outer(spread, spread)
    w, v = np.array(w), np.array(v)
    return float(w @ cov @ v / np.sqrt(w @ cov @ w * (v @ cov @ v)))


def main():
    # 1) 例のチーム（data に置く）
    ex = make_team(rng, **BASE)
    dfx = pd.DataFrame(ex.astype(int), columns=ITEMS)
    dfx.insert(0, "person_id", np.arange(1, len(dfx) + 1))
    dfx.to_csv(DATA / "team_example.csv", index=False)
    x = dfx[ITEMS].values.astype(float)
    tot = np.round(x @ WM.T, 9)
    rk = np.stack([ranks(tot[:, k]) for k in range(5)], 1)
    ex_tab = pd.DataFrame(rk, columns=[f"順位_{k}" for k in WN])
    ex_tab.insert(0, "person_id", dfx.person_id)
    for k, name in enumerate(WN):
        ex_tab[f"合計_{name}"] = np.round(tot[:, k], 3)
    ex_tab.to_csv(RES / "example_team_ranks.csv", index=False)
    st = team_stats(x)
    top3 = {name: sorted((np.where(rk[:, k] <= 3)[0] + 1).tolist()) for k, name in enumerate(WN)}
    first = {name: sorted((np.where(rk[:, k] == 1)[0] + 1).tolist()) for k, name in enumerate(WN)}
    example = {"top3_person_ids": top3, "first_person_ids": first,
               "n_union_top3_5weights": st["n_union_top3_5weights"],
               "tie_at_3rd_equal": st["tie_at_3rd_equal"],
               "n_can_be_1st": st["n_can_be_1st"], "n_can_be_top3": st["n_can_be_top3"],
               "share_move_ge5_equal_vs_collab": round(st["share_move_ge5_equal_vs_collab"], 3),
               "max_rank_range": int((rk.max(1) - rk.min(1)).max()),
               "item_sd": {ITEMS[j]: round(float(x[:, j].std(ddof=1)), 2) for j in range(4)},
               "item_corr_mean": round(float(np.corrcoef(x.T)[np.triu_indices(4, 1)].mean()), 3)}

    # 2) 1,000チーム（基本の置き方）
    stats = [team_stats(make_team(np.random.default_rng(SEED * 1000 + r), **BASE)) for r in range(N_TEAM)]
    base, base_df = summarize(stats)
    base_df.to_csv(RES / "teams_1000.csv", index=False, float_format="%.4f")
    # 標準化してから均等に足したときの実際の効き（項目の散らばりをそろえる）
    effz = []
    for r in range(N_TEAM):
        xx = make_team(np.random.default_rng(SEED * 1000 + r), **BASE)
        sd = xx.std(0, ddof=1)
        sd[sd == 0] = 1
        zz = (xx - xx.mean(0)) / sd
        S = zz.sum(1)
        effz.append([np.cov(zz[:, j], S)[0, 1] / S.var(ddof=1) for j in range(4)])
    base["eff_share_standardized"] = {ITEMS[j]: round(float(np.mean(effz, 0)[j]), 3) for j in range(4)}

    # 3) 確かめ：置き方を1つずつ変える（各300チーム）
    rob = []
    settings = [("項目どうしの相関", "rho", v) for v in [0.0, 0.3, 0.5, 0.8]] + \
               [("チームの人数", "n", v) for v in [10, 30, 100]] + \
               [("点の付け方", "discrete", v) for v in [True, False]]
    for i, (label, key, v) in enumerate(settings):
        kw = dict(BASE); kw[key] = v
        ss = [team_stats(make_team(np.random.default_rng(SEED * 7 + 100000 * i + r), **kw)) for r in range(300)]
        o, _ = summarize(ss)
        row = {"変えたもの": label, "値": ("5段階" if v is True else "丸めない" if v is False else v),
               "1位が5つの重みで同じ": o["P_first_same_all5"],
               "上位3人の重なり（均等と協働重視）": o["top3_overlap_mean"],
               "3位の境目に同点": o["P_tie_at_3rd"],
               "順位が5つ以上動く人（均等と協働重視）": o["share_move_ge5"],
               "1位になれる人（455通り）": o["n_can_be_1st_mean"],
               "5つの重みのどれかで上位3人に入る人": o["n_union_top3_5weights_mean"],
               "順位相関（均等と協働重視）": o["spearman_mean"],
               "式の相関（丸めないとき）": round(formula_corr(kw["rho"], WEIGHTS["均等"], WEIGHTS["協働重視"]), 3),
               "成果の実際の効き（均等）": o["eff_share_equal"]["成果"]}
        rob.append(row)
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"settings": {"items": ITEMS, "spread_before_rounding": SPREAD.tolist(), **{k: v for k, v in BASE.items()},
                        "weights": WEIGHTS, "grid_count": int(len(GRID)), "n_team": N_TEAM},
           "example_team": example, "base_1000teams": base,
           "formula_corr_base": round(formula_corr(0.5, WEIGHTS["均等"], WEIGHTS["協働重視"]), 3),
           "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a939_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例のチームの順位の入れ替わり（均等→協働重視）
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    order = [0, 1, 2, 3, 4]
    for i in range(len(x)):
        ys = [rk[i, k] for k in order]
        hit = rk[i, :].min() <= 3
        ax.plot(range(5), ys, color=ORANGE if hit else LIGHT, lw=1.6 if hit else 0.9, alpha=.95 if hit else .7,
                marker="o", ms=3, zorder=3 if hit else 2)
    ax.set_xticks(range(5)); ax.set_xticklabels(WN)
    ax.invert_yaxis(); ax.set_ylabel("チームの中の順位（同点は同じ順位）")
    ax.plot([-0.2, 4.05], [3.5, 3.5], color=GRAY, lw=.8, ls="--")
    ax.text(4.12, 3.5, "3位と4位の境目", color=GRAY, fontsize=8.5, va="center")
    ax.set_xlim(-0.2, 4.9)
    ax.set_title(f"重みを変えると、上位3人に入る顔ぶれが入れ替わる（例のチーム30人）\n"
                 f"5つの重みのどれかで上位3人に入った人＝オレンジの線")
    save(fig, "a939_bump.png", SRC)

    # 図2：1位になれる人の数の分布（455通りの重み）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    vc = base_df.n_can_be_1st.value_counts().sort_index()
    ax.bar(vc.index, vc.values / N_TEAM * 100, color=BLUE)
    ax.set_xlabel("重みの組455通りのどれかで1位（同点を含む）になれる人の数")
    ax.set_ylabel("チームの割合（%）")
    ax.set_xticks(vc.index)
    ax.set_title(f"30人のチームで、重みしだいで1位になれる人は平均{base['n_can_be_1st_mean']:.1f}人（1,000チーム）")
    save(fig, "a939_can_be_first.png", SRC)

    # 図3：名目の重みと実際の効き（均等）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xs = np.arange(4)
    e1 = [base["eff_share_equal"][k] * 100 for k in ITEMS]
    e2 = [base["eff_share_standardized"][k] * 100 for k in ITEMS]
    ax.bar(xs - 0.2, e1, 0.38, color=ORANGE, label="5段階の点をそのまま均等に足す")
    ax.bar(xs + 0.2, e2, 0.38, color=BLUE, label="項目ごとに散らばりをそろえてから均等に足す")
    for xi, v in zip(xs - 0.2, e1):
        ax.text(xi, v + 0.8, f"{v:.0f}%", ha="center", fontsize=9)
    for xi, v in zip(xs + 0.2, e2):
        ax.text(xi, v + 0.8, f"{v:.0f}%", ha="center", fontsize=9)
    ax.axhline(25, color=GRAY, lw=.8, ls="--", label="名目の重み（25%）")
    ax.set_xticks(xs); ax.set_xticklabels(ITEMS); ax.set_ylim(0, 50)
    ax.set_ylabel("合計の散らばりのうち、その項目の分（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("「均等」に足しても、点の散らばりが大きい項目ほど合計を動かす")
    save(fig, "a939_effective_weight.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
