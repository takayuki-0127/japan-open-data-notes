"""1011 外れた値1つで、合計点はどれだけ動くのか？（架空のデータ）

架空の製品30個を6項目で測り、項目ごとにそろえて（標準化など）平均した「総合スコア」で並べる。
1個の製品の1項目（電池の持ち）だけを10倍に打ち間違えたとき、その製品とほかの製品の順位がどれだけ動くかを、
そろえ方5通りで数える。正しい答えは、打ち間違いのない値で同じそろえ方をしたときの順位。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1011
SRC = "架空の製品の測定値（作成者が乱数で作成、seed 1011）"
N, K, FACTOR = 30, 6, 10.0
ITEMS = ["電池の持ち", "画面の明るさ", "音の大きさ", "起動の速さ", "充電の速さ", "丈夫さ"]
MEANS = np.array([12, 500, 80, 50, 40, 60], float)    # 項目ごとの単位での平均（どれも大きいほど良い向きにしてある）
SDS = np.array([2, 80, 10, 8, 6, 9], float)
COMMON = 0.5                                           # 項目どうしの共通の分（相関0.25）
REPS, GRID_REPS = 1000, 200
METHODS = {"z": "平均と標準偏差でそろえる", "minmax": "最小0・最大1にそろえる", "rank": "順位にする",
           "zclip": "平均と標準偏差でそろえ±3で切る", "robust": "中央値とMADでそろえ±3で切る"}


def make_items(rng, n=N, k=K):
    means = np.resize(MEANS, k); sds = np.resize(SDS, k)
    c = rng.normal(0, 1, (n, 1))
    e = rng.normal(0, 1, (n, k))
    return means + sds * (COMMON * c + np.sqrt(1 - COMMON ** 2) * e)


def scale(x, how):
    """列ごとにそろえる（x は 製品×項目）"""
    if how in ("z", "zclip"):
        s = (x - x.mean(0)) / x.std(0)
        return np.clip(s, -3, 3) if how == "zclip" else s
    if how == "minmax":
        return (x - x.min(0)) / (x.max(0) - x.min(0))
    if how == "rank":
        return (np.argsort(np.argsort(x, 0), 0) + 1) / len(x)
    if how == "robust":
        med = np.median(x, 0)
        mad = np.median(np.abs(x - med), 0) * 1.4826
        return np.clip((x - med) / mad, -3, 3)
    raise ValueError(how)


def order_of(score, ids):
    """スコアの高い順の順位（1が最上位）。同点は番号の小さいほうを上に"""
    o = np.lexsort((ids, -score))
    r = np.empty(len(score), int); r[o] = np.arange(1, len(score) + 1)
    return r


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def one_rep(rng, n=N, k=K, factor=FACTOR, methods=METHODS):
    true = make_items(rng, n, k)
    j = int(rng.integers(n))
    obs = true.copy(); obs[j, 0] = true[j, 0] * factor
    ids = np.arange(n); oth = ids != j
    out = {}
    for m in methods:
        st, so = scale(true, m), scale(obs, m)
        ct, co = st.mean(1), so.mean(1)
        rt, ro = order_of(ct, ids), order_of(co, ids)
        rt_o, ro_o = order_of(ct[oth], ids[oth]), order_of(co[oth], ids[oth])    # ほかの製品どうしの順位
        top5_t, top5_o = set(ids[oth][rt_o <= 5]), set(ids[oth][ro_o <= 5])
        out[m] = {"target_true_rank": int(rt[j]), "target_obs_rank": int(ro[j]),
                  "target_rank_up": int(rt[j] - ro[j]), "target_first": int(ro[j] == 1),
                  "target_item_score": float(so[j, 0]),
                  "others_mean_abs_move": float(np.abs(rt_o - ro_o).mean()),
                  "others_share_moved": float((rt_o != ro_o).mean()),
                  "others_top5_overlap": len(top5_t & top5_o),
                  "others_spearman": spearman(ct[oth], co[oth]),
                  "item1_spread_ratio": float(so[oth, 0].std() / st[oth, 0].std())}
    return out, true, obs, j


def summarize(rows):
    df = pd.DataFrame(rows)
    return df.mean(numeric_only=True)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分（data/products.csv）
    _, true, obs, j = one_rep(rng)
    ids = np.arange(N)
    d = pd.DataFrame({"product": [f"P{i + 1:02d}" for i in ids]})
    for c, name in enumerate(ITEMS):
        d[f"true_{c + 1}"] = true[:, c].round(3)
    d["recorded_1"] = obs[:, 0].round(3)
    d["is_typo"] = (ids == j).astype(int)
    one = {"typo_product": d["product"][j], "typo_true": round(float(true[j, 0]), 2),
           "typo_recorded": round(float(obs[j, 0]), 2)}
    for m in METHODS:
        ct, co = scale(true, m).mean(1), scale(obs, m).mean(1)
        d[f"rank_true_{m}"] = order_of(ct, ids); d[f"rank_obs_{m}"] = order_of(co, ids)
    d.to_csv(DATA / "products.csv", index=False)
    oth = ids != j
    for m in METHODS:
        rt_o = order_of(scale(true, m).mean(1)[oth], ids[oth]); ro_o = order_of(scale(obs, m).mean(1)[oth], ids[oth])
        one[m] = {"target_true_rank": int(d[f"rank_true_{m}"][j]), "target_obs_rank": int(d[f"rank_obs_{m}"][j]),
                  "others_moved": int((rt_o != ro_o).sum()), "others_max_move": int(np.abs(rt_o - ro_o).max())}
    zt, zo = scale(true, "z"), scale(obs, "z")
    one["z_item1_target_true"] = round(float(zt[j, 0]), 3); one["z_item1_target_obs"] = round(float(zo[j, 0]), 3)
    one["z_item1_others_sd_obs"] = round(float(zo[oth, 0].std()), 3)

    # 基本の置き方（1,000回）
    rows = {m: [] for m in METHODS}
    for r in range(REPS):
        out, *_ = one_rep(np.random.default_rng(SEED * 1000 + r))
        for m in METHODS:
            rows[m].append(out[m])
    base = pd.DataFrame({m: summarize(rows[m]) for m in METHODS}).T
    base.insert(0, "method", [METHODS[m] for m in base.index])
    base = base.round(4)
    base.to_csv(RES / "methods_base.csv", index_label="key")

    # 下向きの打ち間違い（10分の1）
    rows_dn = {m: [] for m in METHODS}
    for r in range(REPS):
        out, *_ = one_rep(np.random.default_rng(SEED * 2000 + r), factor=0.1)
        for m in METHODS:
            rows_dn[m].append(out[m])
    down = pd.DataFrame({m: summarize(rows_dn[m]) for m in METHODS}).T
    down.insert(0, "method", [METHODS[m] for m in down.index])
    down = down.round(4)
    down.to_csv(RES / "methods_down.csv", index_label="key")

    # 確かめ：倍率×製品の数×項目の数（各200回）
    grid = []
    gi = 0
    for n in [10, 30, 100]:
        for k in [3, 6, 12]:
            for f in [1.5, 2, 3, 5, 10, 100]:
                rr = {m: [] for m in METHODS}
                for r in range(GRID_REPS):
                    out, *_ = one_rep(np.random.default_rng(SEED * 100000 + gi * 1000 + r), n, k, f)
                    for m in METHODS:
                        rr[m].append(out[m])
                gi += 1
                for m in METHODS:
                    s = summarize(rr[m])
                    grid.append({"n_products": n, "n_items": k, "factor": f, "method": METHODS[m],
                                 "target_rank_up": round(s.target_rank_up, 3), "target_first": round(s.target_first, 4),
                                 "target_item_score": round(s.target_item_score, 3),
                                 "others_mean_abs_move": round(s.others_mean_abs_move, 3),
                                 "others_share_moved": round(s.others_share_moved, 4),
                                 "others_top5_overlap": round(s.others_top5_overlap, 3),
                                 "item1_spread_ratio": round(s.item1_spread_ratio, 4),
                                 "z_bound_sqrt_n_minus_1": round(float(np.sqrt(n - 1)), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    zg = grid[grid.method == METHODS["z"]]
    rk = grid[grid.method == METHODS["rank"]]
    rb = grid[grid.method == METHODS["robust"]]
    summary = {
        "z_target_score_x100_vs_bound": zg[zg.factor == 100][["n_products", "n_items", "target_item_score",
                                                              "z_bound_sqrt_n_minus_1"]].drop_duplicates(
            ["n_products"]).to_dict("records"),
        "z_others_share_moved_range": [round(float(zg.others_share_moved.min()), 4), round(float(zg.others_share_moved.max()), 4)],
        "z_others_share_moved_range_factor_ge_5": [round(float(zg[zg.factor >= 5].others_share_moved.min()), 4),
                                                   round(float(zg[zg.factor >= 5].others_share_moved.max()), 4)],
        "z_others_mean_abs_move_range": [round(float(zg.others_mean_abs_move.min()), 3), round(float(zg.others_mean_abs_move.max()), 3)],
        "z_target_first_range_factor10": [round(float(zg[zg.factor == 10].target_first.min()), 4),
                                          round(float(zg[zg.factor == 10].target_first.max()), 4)],
        "rank_others_share_moved_range": [round(float(rk.others_share_moved.min()), 4), round(float(rk.others_share_moved.max()), 4)],
        "robust_others_share_moved_range": [round(float(rb.others_share_moved.min()), 4), round(float(rb.others_share_moved.max()), 4)],
        "z_item1_spread_ratio_factor10_range": [round(float(zg[zg.factor == 10].item1_spread_ratio.min()), 4),
                                                round(float(zg[zg.factor == 10].item1_spread_ratio.max()), 4)],
        "n_grid": int(len(zg)),
    }
    out = {"one_draw": one, "base_1000reps": base.reset_index().to_dict("records"),
           "down_0_1_1000reps": down.reset_index().to_dict("records"), "grid_summary": summary,
           "z_bound_n30": round(float(np.sqrt(N - 1)), 3)}

    # 図1：1回分、本当の順位と打ち間違いのあとの順位（平均と標準偏差でそろえる）
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    rt, ro = d["rank_true_z"].values, d["rank_obs_z"].values
    rto = order_of(scale(true, "z").mean(1)[oth], ids[oth]); roo = order_of(scale(obs, "z").mean(1)[oth], ids[oth])
    moved = set(ids[oth][rto != roo])
    for i in ids:
        col = ORANGE if i == j else (BLUE if i in moved else LIGHT)
        lw = 2.2 if i == j else 1.0
        ax.plot([0, 1], [rt[i], ro[i]], color=col, lw=lw, marker="o", ms=3.5)
    ax.text(-0.04, rt[j], f"{d['product'][j]}（{rt[j]}位）", ha="right", va="center", fontsize=9, color=ORANGE)
    ax.text(1.04, ro[j], f"{ro[j]}位：電池の持ちを10倍に打ち間違えた製品", ha="left", va="center", fontsize=9, color=ORANGE)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["正しい値で", "1つ打ち間違えると"])
    ax.set_xlim(-0.55, 1.9); ax.set_ylim(N + 1, 0); ax.set_yticks([1, 5, 10, 15, 20, 25, 30]); ax.set_ylabel("総合スコアの順位（30個）")
    ax.spines["bottom"].set_visible(False); ax.tick_params(axis="x", length=0)
    ax.set_title("外れた値1つで、その製品もほかの製品も順位が動く\n（平均と標準偏差でそろえて6項目を平均、1回分）")
    ax.text(1.04, N + 0.2, f"青：ほかの29個どうしの順位が動いたもの（{one['z']['others_moved']}個）", fontsize=8.5, color=BLUE, va="bottom")
    save(fig, "a1011_slope.png", SRC)

    # 図2：そろえ方ごとの動き（1,000回の平均）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)
    lab = [METHODS[m] for m in METHODS][::-1]
    v1 = base["target_rank_up"].values[::-1]
    v2 = (base["others_share_moved"].values * 100)[::-1]
    axes[0].barh(lab, v1, color=ORANGE)
    for i, v in enumerate(v1):
        axes[0].text(v + 0.3, i, f"{v:.1f}位", va="center", fontsize=9)
    axes[0].set_xlabel("打ち間違えた製品が上がった順位（平均）"); axes[0].set_xlim(0, max(v1) * 1.3)
    axes[1].barh(lab, v2, color=BLUE)
    for i, v in enumerate(v2):
        axes[1].text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9)
    axes[1].set_xlabel("ほかの29個のうち、互いの順位が動いた割合（%）"); axes[1].set_xlim(0, 100)
    fig.suptitle("そろえ方で、外れた値の効き方は変わる（製品30個・6項目・10倍の打ち間違い、1,000回の平均）", fontsize=12)
    save(fig, "a1011_methods.png", SRC)

    # 図3：倍率ごと、ほかの製品の動いた割合（6項目、製品の数ごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    fs = [1.5, 2, 3, 5, 10, 100]
    xs = np.arange(len(fs))
    for n, col, ls in [(10, LIGHT, "-"), (30, BLUE, "-"), (100, INK, "-")]:
        g = zg[(zg.n_products == n) & (zg.n_items == 6)].set_index("factor").loc[fs]
        ax.plot(xs, g.others_share_moved * 100, color=col, marker="o", ls=ls, label=f"平均と標準偏差：製品{n}個")
    for n, col in [(30, ORANGE)]:
        g = rk[(rk.n_products == n) & (rk.n_items == 6)].set_index("factor").loc[fs]
        ax.plot(xs, g.others_share_moved * 100, color=col, marker="s", ls="--", label=f"順位にする：製品{n}個")
        g = rb[(rb.n_products == n) & (rb.n_items == 6)].set_index("factor").loc[fs]
        ax.plot(xs, g.others_share_moved * 100, color=GREEN, marker="^", ls=":", label=f"中央値とMAD・±3：製品{n}個")
    ax.set_xticks(xs); ax.set_xticklabels([f"{f:g}倍" for f in fs])
    ax.set_xlabel("1つの値の打ち間違いの大きさ"); ax.set_ylabel("ほかの製品のうち順位が動いた割合（%）")
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("平均と標準偏差でそろえると、外れが大きいほどほかの製品も動く（6項目、各200回）")
    save(fig, "a1011_by_factor.png", SRC)

    json.dump(out, open(RES / "a1011_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
