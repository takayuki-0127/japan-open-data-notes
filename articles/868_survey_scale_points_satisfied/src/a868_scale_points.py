"""868 「満足」の段階の数（3・5・7段階）で、満足の割合はどう変わるのか？（架空のデータ）

架空の2つの店（A店・B店）の客。客ごとに気持ちの中の満足度（連続の値）を置き、
それを3・5・7段階の選択肢に区切って答えると置く。区切りの位置は作成者が置き、置き方を4通り試す。
「満足の割合」を3通りの数え方で数え、段階の数・区切りの置き方でどれだけ動くかと、
A店とB店の差（本当は B が 0.2 上）を200人ずつの調査で見つけられる割合を数える。
"""
import json, math, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 868
SRC = "架空の店の客アンケート（作成者が乱数で作成、seed 868）"
MU_A, MU_B = 0.2, 0.4  # 気持ちの中の満足度の平均（ばらつきは1）
N_SHOP = 200
LABELS = {3: ["不満", "どちらでもない", "満足"],
          5: ["不満", "やや不満", "どちらでもない", "やや満足", "満足"],
          7: ["とても不満", "不満", "やや不満", "どちらでもない", "やや満足", "満足", "とても満足"]}
WORD_TOP = {3: 1, 5: 1, 7: 2}  # 「満足」と書いた箱から上の箱の数


def cuts(k, placement):
    if placement == "equal":      # 基本：幅3.0を等分
        L = 3.0; return np.array([(j - k / 2) * L / k for j in range(1, k)])
    if placement == "wide":       # 端の箱が狭い（端を選びにくい）：幅4.0を等分
        L = 4.0; return np.array([(j - k / 2) * L / k for j in range(1, k)])
    if placement == "narrow":     # 端の箱が広い（端を選びやすい）：幅2.0を等分
        L = 2.0; return np.array([(j - k / 2) * L / k for j in range(1, k)])
    if placement == "fixed_mid":  # 「どちらでもない」の幅を段階によらず ±0.5 にそろえる
        if k == 3: return np.array([-0.5, 0.5])
        out = np.linspace(0.5, 1.5, (k - 1) // 2)
        return np.concatenate([-out[::-1], out])
    raise ValueError(placement)


PLACE_JA = {"equal": "等間隔（基本）", "fixed_mid": "「どちらでもない」の幅をそろえる",
            "wide": "端の箱が狭い", "narrow": "端の箱が広い"}


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def box_probs(mu, c):
    edges = [-np.inf] + list(c) + [np.inf]
    return np.array([phi(edges[i + 1] - mu) - phi(edges[i] - mu) for i in range(len(edges) - 1)])


def measures(p, k):
    mid = k // 2
    sc = np.arange(1, k + 1)
    return {"sat_side": float(p[mid + 1:].sum()),             # 満足側すべて
            "word_satisfied_up": float(p[-WORD_TOP[k]:].sum()),  # 「満足」と書いた箱から上
            "top_box": float(p[-1]),                          # いちばん上の箱だけ
            "score100": float(((p * sc).sum() - 1) / (k - 1) * 100)}


def main():
    t0 = time.time()
    # 1) 本当の割合（区切りから計算で出す）
    rows = []
    for placement in ["equal", "fixed_mid", "wide", "narrow"]:
        for mu_name, mu in [("A", MU_A), ("B", MU_B), ("低い店", -0.5), ("高い店", 1.0)]:
            for k in [3, 5, 7]:
                p = box_probs(mu, cuts(k, placement))
                m = measures(p, k)
                rows.append({"placement": placement, "shop": mu_name, "mu": mu, "k": k,
                             **{kk: round(v * (100 if kk != "score100" else 1), 2) for kk, v in m.items()},
                             "boxes_pct": ";".join(f"{v*100:.1f}" for v in p)})
    pop = pd.DataFrame(rows)
    pop.to_csv(RES / "share_by_scale.csv", index=False)
    ref_A = round(100 * (1 - phi(-MU_A)), 2)  # 気持ちの中で0より上（作成者の置いた目安）
    ref_B = round(100 * (1 - phi(-MU_B)), 2)

    # 2) A店とB店の差を200人ずつの調査で見つけられる割合（2,000回、基本の区切り）
    rng = np.random.default_rng(SEED)
    R = 2000
    zA = rng.normal(MU_A, 1, (R, N_SHOP)); zB = rng.normal(MU_B, 1, (R, N_SHOP))
    pw = []
    for placement in ["equal", "fixed_mid", "wide", "narrow"]:
        for k in [3, 5, 7]:
            c = cuts(k, placement)
            aA = np.searchsorted(c, zA) + 1; aB = np.searchsorted(c, zB) + 1
            res = {"placement": placement, "k": k}
            mid = k // 2 + 1
            for name, thr in [("sat_side", mid + 1), ("top_box", k), ("word_satisfied_up", k - WORD_TOP[k] + 1)]:
                pa = (aA >= thr).mean(1); pb = (aB >= thr).mean(1)
                pp = (pa + pb) / 2
                se = np.sqrt(pp * (1 - pp) * 2 / N_SHOP)
                z = np.where(se > 0, (pb - pa) / np.where(se > 0, se, 1), 0)
                res[f"power_{name}"] = round(float((z > 1.96).mean()), 4)
            ma, mb = aA.mean(1), aB.mean(1)
            se = np.sqrt(aA.var(1, ddof=1) / N_SHOP + aB.var(1, ddof=1) / N_SHOP)
            res["power_mean"] = round(float(((mb - ma) / se > 1.96).mean()), 4)
            pw.append(res)
    # 気持ちの中の値そのもの（連続）で比べた場合：段階に区切らない上限
    se = np.sqrt(zA.var(1, ddof=1) / N_SHOP + zB.var(1, ddof=1) / N_SHOP)
    power_latent = round(float(((zB.mean(1) - zA.mean(1)) / se > 1.96).mean()), 4)
    pw = pd.DataFrame(pw)
    pw.to_csv(RES / "power_A_vs_B.csv", index=False)

    # 1回分のデータ：A店・B店200人ずつ、同じ人が3通りの段階で答えたとしたら
    g = np.random.default_rng(SEED + 1)
    lat = np.concatenate([g.normal(MU_A, 1, N_SHOP), g.normal(MU_B, 1, N_SHOP)])
    df = pd.DataFrame({"shop": ["A"] * N_SHOP + ["B"] * N_SHOP, "resp_id": np.arange(1, 2 * N_SHOP + 1),
                       "latent": lat.round(4)})
    for k in [3, 5, 7]:
        df[f"ans{k}"] = np.searchsorted(cuts(k, "equal"), lat) + 1
    df.to_csv(DATA / "responses_A_B.csv", index=False)
    one = {}
    for k in [3, 5, 7]:
        mid = k // 2 + 1
        for s in ["A", "B"]:
            a = df.loc[df.shop == s, f"ans{k}"]
            one[f"{s}_k{k}_sat_side"] = round(float((a > mid).mean() * 100), 1)
            one[f"{s}_k{k}_top_box"] = round(float((a == k).mean() * 100), 1)

    eq = pop[(pop.placement == "equal")]
    def get(shop, k, col, placement="equal"):
        return float(pop[(pop.placement == placement) & (pop.shop == shop) & (pop.k == k)][col].iloc[0])
    out = {"mu_A": MU_A, "mu_B": MU_B, "n_per_shop": N_SHOP,
           "cuts": {pl: {str(k): [round(float(v), 3) for v in cuts(k, pl)] for k in [3, 5, 7]}
                    for pl in ["equal", "fixed_mid", "wide", "narrow"]},
           "reference_latent_gt0_A": ref_A, "reference_latent_gt0_B": ref_B,
           "share_by_scale": pop.to_dict("records"),
           "diff_B_minus_A_pt": {f"{col}_k{k}": round(get("B", k, col) - get("A", k, col), 2)
                                 for col in ["sat_side", "word_satisfied_up", "top_box", "score100"] for k in [3, 5, 7]},
           "range_sat_side_A_over_placements": {str(k): [float(pop[(pop.shop == "A") & (pop.k == k)].sat_side.min()),
                                                         float(pop[(pop.shop == "A") & (pop.k == k)].sat_side.max())]
                                                for k in [3, 5, 7]},
           "range_all_A_all_defs": [float(pop[pop.shop == "A"][["sat_side", "word_satisfied_up", "top_box"]].min().min()),
                                    float(pop[pop.shop == "A"][["sat_side", "word_satisfied_up", "top_box"]].max().max())],
           "range_A_equal_all_defs": [float(eq[eq.shop == "A"][["sat_side", "word_satisfied_up", "top_box"]].min().min()),
                                      float(eq[eq.shop == "A"][["sat_side", "word_satisfied_up", "top_box"]].max().max())],
           "range_score100_A_all_placements": [float(pop[pop.shop == "A"].score100.min()), float(pop[pop.shop == "A"].score100.max())],
           "range_score100_by_shop": {sh: [float(pop[pop.shop == sh].score100.min()), float(pop[pop.shop == sh].score100.max())]
                                      for sh in ["A", "B", "低い店", "高い店"]},
           "range_sat_side_by_shop": {sh: [float(pop[pop.shop == sh].sat_side.min()), float(pop[pop.shop == sh].sat_side.max())]
                                      for sh in ["A", "B", "低い店", "高い店"]},
           "power": pw.to_dict("records"), "power_latent_continuous": power_latent, "one_draw": one}
    json.dump(out, open(RES / "a868_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じA店の客が、3・5・7段階でどの箱に入るか（基本の区切り）
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    cmap = {3: [BLUE, GRAY, ORANGE],
            5: [BLUE, LIGHT, GRAY, "#f5b393", ORANGE],
            7: ["#174f94", BLUE, LIGHT, GRAY, "#f5b393", ORANGE, "#b5461b"]}
    for yi, k in enumerate([7, 5, 3]):
        p = box_probs(MU_A, cuts(k, "equal")) * 100
        left = 0
        for j, v in enumerate(p):
            ax.barh(yi, v, left=left, color=cmap[k][j], edgecolor="white", lw=.8)
            if v >= 6:
                ax.text(left + v / 2, yi, f"{LABELS[k][j]}\n{v:.0f}%", ha="center", va="center", fontsize=7.5,
                        color="white" if cmap[k][j] in (BLUE, ORANGE, "#174f94", "#b5461b") else INK)
            left += v
    ax.set_yticks(range(3)); ax.set_yticklabels(["7段階", "5段階", "3段階"])
    ax.set_xlim(0, 100); ax.set_xlabel("A店の客の割合（%、基本の区切り）")
    ax.set_title("同じ客でも、段階の数で「満足」の箱に入る割合が変わる（A店）")
    save(fig, "a868_boxes.png", SRC)

    # 図2：数え方×段階の数（A店、基本の区切り）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    defs = [("sat_side", "満足側すべて", ORANGE), ("word_satisfied_up", "「満足」と書いた箱から上", BLUE),
            ("top_box", "いちばん上の箱だけ", GRAY)]
    xs = np.arange(3); w = 0.26
    for i, (col, lab, cc) in enumerate(defs):
        v = [get("A", k, col) for k in [3, 5, 7]]
        ax.bar(xs + (i - 1) * w, v, w, color=cc, label=lab)
        for x, vv in zip(xs + (i - 1) * w, v):
            ax.text(x, vv + 1, f"{vv:.0f}", ha="center", fontsize=8.5)
    ax.axhline(ref_A, color=INK, lw=.8, ls="--")
    ax.text(2.45, ref_A + 1.2, f"気持ちの中で0より上 {ref_A:.0f}%", ha="right", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels(["3段階", "5段階", "7段階"]); ax.set_ylabel("満足の割合（%）")
    ax.set_ylim(0, 82); ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3)
    lo, hi = out["range_A_equal_all_defs"]
    ax.set_title(f"同じA店の客で、満足の割合は数え方と段階の数で{lo:.0f}〜{hi:.0f}%に動く（基本の区切り）", fontsize=12)
    save(fig, "a868_definitions.png", SRC)

    # 図3：区切りの置き方で「満足側すべて」がどう動くか（A店）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    pls = ["equal", "fixed_mid", "wide", "narrow"]
    colp = [ORANGE, INK, BLUE, GREEN]
    for pl, cc in zip(pls, colp):
        v = [get("A", k, "sat_side", pl) for k in [3, 5, 7]]
        ax.plot([3, 5, 7], v, marker="o", color=cc, label=PLACE_JA[pl])
    ax.axhline(ref_A, color=GRAY, lw=.8, ls="--")
    ax.text(7, ref_A + 0.8, f"気持ちの中で0より上 {ref_A:.0f}%", ha="right", fontsize=8.5, color=GRAY)
    ax.set_xticks([3, 5, 7]); ax.set_xticklabels(["3段階", "5段階", "7段階"])
    ax.set_ylabel("満足側すべての割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("段階を増やすと満足が増えるかは、区切りの置き方しだい（A店）")
    save(fig, "a868_placement.png", SRC)

    print(eq.to_string()); print(pw.to_string()); print("latent", power_latent, ref_A, ref_B)
    print(out["diff_B_minus_A_pt"]); print(out["range_sat_side_A_over_placements"], out["range_all_A_all_defs"])
    print(pop[pop.shop == "A"][["placement", "k", "sat_side", "word_satisfied_up", "top_box", "score100"]].to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
