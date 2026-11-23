"""1008 項目が互いに似ていると、合計点は何を測っているのか？（架空のデータ）

架空の飲食店200店の「総合おすすめ指数」。作成者は、味・接客・居心地の3つの面を同じだけ見る
つもりで10項目を作ったが、そのうち6項目は味に似た項目（料理の味・素材・盛り付けなど）だった、という置き方。
店ごとに3つの面の本当の良さ（因子）を置き、項目の点はそこから作る。
10項目をそのまま平均した合計点が、どの面をどれだけ測っているかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1008
SRC = "架空の飲食店の指数（作成者が乱数で作成、seed 1008）"
rng = np.random.default_rng(SEED)

ASPECTS = ["味", "接客", "居心地"]
ITEM_NAMES = {"味": ["料理の味", "素材", "盛り付け", "料理の温度", "料理の量", "看板メニュー", "飲み物", "デザート"],
              "接客": ["接客の丁寧さ", "提供の速さ", "説明の分かりやすさ"],
              "居心地": ["席の居心地", "店内の清潔さ", "店内の静かさ"]}
BASE = {"n_taste": 6, "r_w": 0.6, "rho_a": 0.2}
N_STORE, N_ITEM, TOP = 200, 10, 20
INDEX_NAMES = ["①10項目をそのまま平均", "②面ごとに平均してから3面を平均", "③面ごとに1項目だけ（3項目の平均）"]


def layout(n_taste):
    other = (N_ITEM - n_taste) // 2
    return [n_taste, other, other]


def make_stores(rng, n=N_STORE, n_taste=6, r_w=0.6, rho_a=0.2):
    counts = layout(n_taste)
    R = np.full((3, 3), rho_a) + np.eye(3) * (1 - rho_a)
    F = rng.multivariate_normal(np.zeros(3), R, n)
    lam = np.sqrt(r_w)
    asp = np.repeat(np.arange(3), counts)
    x = lam * F[:, asp] + np.sqrt(1 - r_w) * rng.standard_normal((n, len(asp)))
    score = np.clip(np.round(3.5 + 0.5 * x, 1), 1, 5)  # 1〜5点、0.1刻み（項目ごとの客の評価の平均のつもり）
    return F, score, asp, counts


def index_coef(counts, lam):
    """3つの指数が、3つの面と項目だけのぶれをどれだけの係数で含むか（丸め前の式）"""
    out = []
    n = sum(counts)
    # ① そのまま平均
    c1 = 0.5 * lam * np.array(counts) / n
    d1 = np.concatenate([[0.5 * np.sqrt(1 - lam ** 2) / n] * k for k in counts])
    # ② 面ごとに平均してから3面を平均
    c2 = 0.5 * lam * np.ones(3) / 3
    d2 = np.concatenate([[0.5 * np.sqrt(1 - lam ** 2) / (3 * k)] * k for k in counts])
    # ③ 面ごとに1項目
    c3 = 0.5 * lam * np.ones(3) / 3
    d3 = np.array([0.5 * np.sqrt(1 - lam ** 2) / 3] * 3)
    return [(c1, d1), (c2, d2), (c3, d3)]


def formula(n_taste, r_w, rho_a, truth_w=None):
    counts = layout(n_taste)
    R = np.full((3, 3), rho_a) + np.eye(3) * (1 - rho_a)
    tw = np.ones(3) / 3 if truth_w is None else np.asarray(truth_w)
    res = []
    for c, d in index_coef(counts, np.sqrt(r_w)):
        v = c @ R @ c + (d ** 2).sum()
        share = c * (R @ c) / v
        corr_truth = (c @ R @ tw) / np.sqrt(v * (tw @ R @ tw))
        res.append({"share": share, "share_noise": float((d ** 2).sum() / v), "corr_truth": float(corr_truth)})
    return res


def cronbach(x):
    k = x.shape[1]
    return float(k / (k - 1) * (1 - x.var(0, ddof=1).sum() / x.sum(1).var(ddof=1)))


def build_indices(score, asp, counts):
    i1 = score.mean(1)
    i2 = np.mean([score[:, asp == k].mean(1) for k in range(3)], 0)
    first = [np.where(asp == k)[0][0] for k in range(3)]
    i3 = score[:, first].mean(1)
    return [i1, i2, i3], first


def topset(v, k=TOP):
    return set(np.argsort(-v, kind="stable")[:k])


def spearman(a, b):
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def one_rep(rng, truth_w=None, **kw):
    F, score, asp, counts = make_stores(rng, **kw)
    lam = np.sqrt(kw.get("r_w", 0.6))
    idx, first = build_indices(score, asp, counts)
    tw = np.ones(3) / 3 if truth_w is None else np.asarray(truth_w)
    truth = F @ tw
    coefs = index_coef(counts, lam)
    out = {}
    for name, v, (c, d) in zip(INDEX_NAMES, idx, coefs):
        var = v.var(ddof=1)
        sh = [float(c[k] * np.cov(F[:, k], v)[0, 1] / var) for k in range(3)]
        out[name] = {"share_味": sh[0], "share_接客": sh[1], "share_居心地": sh[2],
                     "corr_味": float(np.corrcoef(v, F[:, 0])[0, 1]),
                     "corr_接客": float(np.corrcoef(v, F[:, 1])[0, 1]),
                     "corr_居心地": float(np.corrcoef(v, F[:, 2])[0, 1]),
                     "corr_truth": float(np.corrcoef(v, truth)[0, 1]),
                     "spearman_truth": spearman(v, truth),
                     "precision20": len(topset(v) & topset(truth)) / TOP}
    out["alpha_10items"] = cronbach(score)
    out["alpha_3items"] = cronbach(score[:, first])
    return out, F, score, asp, counts, idx


def flatten(d):
    row = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                row[f"{k}|{kk}"] = vv
        else:
            row[k] = v
    return row


def main():
    # 例の1回分
    ex, F, score, asp, counts, idx = one_rep(rng, **BASE)
    names = sum([ITEM_NAMES[a][:c] for a, c in zip(ASPECTS, counts)], [])
    df = pd.DataFrame(score, columns=names)
    df.insert(0, "store_id", np.arange(1, N_STORE + 1))
    for k, a in enumerate(ASPECTS):
        df[f"true_{a}"] = np.round(F[:, k], 4)
    df.to_csv(DATA / "stores_example.csv", index=False, float_format="%.4f")
    corrmat = np.corrcoef(score.T)
    pd.DataFrame(np.round(corrmat, 3), index=names, columns=names).to_csv(RES / "item_corr_example.csv")
    # 例：本当の接客がいちばん良い店の順位
    best_s = int(np.argmax(F[:, 1]))
    rk = [int((v > v[best_s]).sum() + 1) for v in idx]
    truth = F.mean(1)
    within = [float(corrmat[np.ix_(asp == k, asp == k)][~np.eye((asp == k).sum(), dtype=bool)].mean()) for k in range(3)]
    between = float(corrmat[np.not_equal.outer(asp, asp)].mean())
    example = {"best_service_store_id": best_s + 1,
               "best_service_rank_by_index": dict(zip(INDEX_NAMES, rk)),
               "best_service_rank_by_truth": int((truth > truth[best_s]).sum() + 1),
               "mean_item_corr_within_味": round(within[0], 3), "mean_item_corr_within_接客": round(within[1], 3),
               "mean_item_corr_within_居心地": round(within[2], 3), "mean_item_corr_between_aspects": round(between, 3),
               "alpha_10items": round(ex["alpha_10items"], 3),
               "precision20": {k: ex[k]["precision20"] for k in INDEX_NAMES}}

    # 1) 基本の置き方で500回
    rows = []
    for r in range(500):
        o = one_rep(np.random.default_rng(SEED * 1000 + r), **BASE)[0]
        rows.append(flatten(o))
    sim = pd.DataFrame(rows)
    sim.round(5).to_csv(RES / "reps_500.csv", index=False)
    f = formula(**BASE)
    summ = []
    for i, name in enumerate(INDEX_NAMES):
        s = {"index": name}
        for a in ASPECTS:
            s[f"share_{a}"] = round(sim[f"{name}|share_{a}"].mean(), 4)
            s[f"formula_share_{a}"] = round(float(f[i]["share"][ASPECTS.index(a)]), 4)
        s["share_noise_formula"] = round(f[i]["share_noise"], 4)
        for a in ASPECTS:
            s[f"corr_{a}"] = round(sim[f"{name}|corr_{a}"].mean(), 4)
        s["corr_truth"] = round(sim[f"{name}|corr_truth"].mean(), 4)
        s["formula_corr_truth"] = round(f[i]["corr_truth"], 4)
        s["spearman_truth"] = round(sim[f"{name}|spearman_truth"].mean(), 4)
        s["precision20"] = round(sim[f"{name}|precision20"].mean(), 4)
        s["precision20_p10"] = round(sim[f"{name}|precision20"].quantile(.1), 4)
        s["precision20_p90"] = round(sim[f"{name}|precision20"].quantile(.9), 4)
        summ.append(s)
    summ = pd.DataFrame(summ)
    summ.to_csv(RES / "indices_base.csv", index=False)
    alpha = {"alpha_10items_mean": round(sim["alpha_10items"].mean(), 4),
             "alpha_3items_mean": round(sim["alpha_3items"].mean(), 4)}
    p1, p2 = sim[f"{INDEX_NAMES[0]}|precision20"], sim[f"{INDEX_NAMES[1]}|precision20"]
    alpha["share_reps_index2_better_precision"] = round(float((p2 > p1).mean()), 4)
    diffs = [abs(summ.loc[i, f"share_{a}"] - summ.loc[i, f"formula_share_{a}"]) for i in range(3) for a in ASPECTS]
    cdiffs = [abs(summ.loc[i, "corr_truth"] - summ.loc[i, "formula_corr_truth"]) for i in range(3)]
    check = {"max_abs_diff_share_vs_formula_base": round(float(max(diffs)), 4),
             "max_abs_diff_corr_truth_vs_formula_base": round(float(max(cdiffs)), 4)}
    alpha["share_reps_index2_equal_precision"] = round(float((p2 == p1).mean()), 4)

    # 2) 確かめ：本当の良さを「味6割・接客2割・居心地2割」と置いた場合（作成者が味を重く見たいとき）
    tw = [0.6, 0.2, 0.2]
    rows = []
    for r in range(300):
        o = one_rep(np.random.default_rng(SEED * 3000 + r), truth_w=tw, **BASE)[0]
        rows.append(flatten(o))
    sim2 = pd.DataFrame(rows)
    f2 = formula(truth_w=tw, **BASE)
    taste_truth = {name: {"precision20": round(sim2[f"{name}|precision20"].mean(), 4),
                          "corr_truth": round(sim2[f"{name}|corr_truth"].mean(), 4),
                          "formula_corr_truth": round(f2[i]["corr_truth"], 4)} for i, name in enumerate(INDEX_NAMES)}

    # 3) 確かめ：味の項目の数 × 似た項目どうしの相関 × 面どうしの相関（27通り、各100回）
    grid = []
    for nt in [4, 6, 8]:
        for rw in [0.3, 0.6, 0.9]:
            for ra in [0.0, 0.2, 0.5]:
                kw = {"n_taste": nt, "r_w": rw, "rho_a": ra}
                rr = [one_rep(np.random.default_rng(SEED * 7 + nt * 100000 + int(rw * 1000) * 10 + int(ra * 10) * 1000 + r), **kw)[0]
                      for r in range(100)]
                ff = formula(**kw)
                g = {"n_taste": nt, "n_service": layout(nt)[1], "n_comfort": layout(nt)[2], "r_w": rw, "rho_a": ra,
                     "share_味_index1": round(np.mean([o[INDEX_NAMES[0]]["share_味"] for o in rr]), 4),
                     "formula_share_味_index1": round(float(ff[0]["share"][0]), 4),
                     "share_味_index2": round(np.mean([o[INDEX_NAMES[1]]["share_味"] for o in rr]), 4),
                     "alpha_10items": round(np.mean([o["alpha_10items"] for o in rr]), 4),
                     "corr_truth_index1": round(np.mean([o[INDEX_NAMES[0]]["corr_truth"] for o in rr]), 4),
                     "corr_truth_index2": round(np.mean([o[INDEX_NAMES[1]]["corr_truth"] for o in rr]), 4),
                     "precision20_index1": round(np.mean([o[INDEX_NAMES[0]]["precision20"] for o in rr]), 4),
                     "precision20_index2": round(np.mean([o[INDEX_NAMES[1]]["precision20"] for o in rr]), 4),
                     "precision20_index3": round(np.mean([o[INDEX_NAMES[2]]["precision20"] for o in rr]), 4)}
                g["precision20_gain_2_minus_1"] = round(g["precision20_index2"] - g["precision20_index1"], 4)
                grid.append(g)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness.csv", index=False)
    g6 = grid[grid.n_taste == 6]
    rob = {"share_味_index1_range": [float(grid.share_味_index1.min()), float(grid.share_味_index1.max())],
           "share_味_index1_range_n6": [float(g6.share_味_index1.min()), float(g6.share_味_index1.max())],
           "share_味_index2_range": [float(grid.share_味_index2.min()), float(grid.share_味_index2.max())],
           "alpha_range": [float(grid.alpha_10items.min()), float(grid.alpha_10items.max())],
           "precision_gain_range": [float(grid.precision20_gain_2_minus_1.min()), float(grid.precision20_gain_2_minus_1.max())],
           "precision_gain_range_n6": [float(g6.precision20_gain_2_minus_1.min()), float(g6.precision20_gain_2_minus_1.max())],
           "n_combos_gain_positive": int((grid.precision20_gain_2_minus_1 > 0).sum()),
           "n_combos": int(len(grid)),
           "n_combos_gain_nonpositive": int((grid.precision20_gain_2_minus_1 <= 0).sum()),
           "n_combos_gain_nonpositive_rw03": int(((grid.precision20_gain_2_minus_1 <= 0) & (grid.r_w == 0.3)).sum()),
           "precision_gain_range_rw06_09": [float(grid[grid.r_w > 0.5].precision20_gain_2_minus_1.min()),
                                            float(grid[grid.r_w > 0.5].precision20_gain_2_minus_1.max())],
           "max_abs_diff_share_vs_formula": round(float((grid.share_味_index1 - grid.formula_share_味_index1).abs().max()), 4),
           "by_n_taste_rw06_ra02": grid[(grid.r_w == 0.6) & (grid.rho_a == 0.2)][
               ["n_taste", "share_味_index1", "alpha_10items", "precision20_index1", "precision20_index2"]].to_dict("records")}
    # αと味の分の結びつき：同じ r_w・rho_a で味の項目を増やすと
    out = {"base": BASE, "example": example, "indices_base_500reps": summ.to_dict("records"), "alpha": alpha, "check_formula": check,
           "truth_taste60": taste_truth, "robustness": rob}
    json.dump(out, open(RES / "a1008_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の店200店での項目どうしの相関
    fig, ax = plt.subplots(figsize=(7.4, 6.0))
    im = ax.imshow(corrmat, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(N_ITEM)); ax.set_yticks(range(N_ITEM))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=9); ax.set_yticklabels(names, fontsize=9)
    for i in range(N_ITEM):
        for j in range(N_ITEM):
            ax.text(j, i, f"{corrmat[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if corrmat[i, j] > 0.6 else INK)
    for b in np.cumsum(counts)[:-1]:
        ax.axhline(b - .5, color=ORANGE, lw=1.2); ax.axvline(b - .5, color=ORANGE, lw=1.2)
    cb = fig.colorbar(im, ax=ax, fraction=0.04); cb.set_label("項目どうしの相関")
    ax.set_title("10項目のうち6項目が味どうしで似ている（例の店200店）")
    save(fig, "a1008_item_corr.png", SRC)

    # 図2：合計点の散らばりのうち、各面から来る分
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    cols = [ORANGE, BLUE, GREEN]
    labels = ["①そのまま平均", "②面ごとに平均→3面を平均", "③面ごとに1項目"]
    for i in range(3):
        left = 0
        vals = [summ.loc[i, f"share_{a}"] * 100 for a in ASPECTS] + [100 - sum(summ.loc[i, f"share_{a}"] * 100 for a in ASPECTS)]
        for k, v in enumerate(vals):
            c = cols[k] if k < 3 else "#e3e2dd"
            ax.barh(2 - i, v, left=left, color=c, label=(ASPECTS + ["項目だけのぶれ"])[k] if i == 0 else None)
            if v >= 6:
                ax.text(left + v / 2, 2 - i, f"{v:.0f}%", ha="center", va="center", fontsize=9,
                        color="white" if k < 3 else INK)
            left += v
    ax.set_yticks([2, 1, 0]); ax.set_yticklabels(labels)
    ax.set_xlim(0, 100); ax.set_xlabel("合計点の散らばり（分散）のうち、各面から来る分（%、500回の平均）")
    ax.legend(ncol=4, frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    ax.set_title("そのまま平均すると、合計点の散らばりの多くは味から来る")
    save(fig, "a1008_share.png", SRC, y=-0.2)

    # 図3：味の項目の数と、味の分・α（相関0.2、似た項目どうしの相関3通り）
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8))
    for rw, c in zip([0.3, 0.6, 0.9], [LIGHT, BLUE, INK]):
        g = grid[(grid.r_w == rw) & (grid.rho_a == 0.2)]
        axes[0].plot(g.n_taste, g.share_味_index1 * 100, "o-", color=c, label=f"同じ面の項目どうしの相関 {rw}")
        axes[1].plot(g.n_taste, g.alpha_10items, "o-", color=c, label=f"同じ面の項目どうしの相関 {rw}")
    axes[0].axhline(100 / 3, color=GRAY, ls="--", lw=1); axes[0].text(6.3, 100 / 3 - 6, "3面を同じだけ（33%）", color=GRAY, fontsize=8)
    axes[0].set_ylabel("①の散らばりのうち味から来る分（%）"); axes[0].set_ylim(0, 100)
    axes[1].set_ylabel("10項目のα（信頼性の目安）"); axes[1].set_ylim(0, 1)
    for a in axes:
        a.set_xticks([4, 6, 8]); a.set_xlabel("10項目のうち味の項目の数")
    axes[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("味の項目を増やすほど、味の分もαも上がる（面どうしの相関0.2）", fontsize=12)
    fig.tight_layout()
    save(fig, "a1008_robustness.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
