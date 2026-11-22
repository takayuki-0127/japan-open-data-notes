"""929 選択問題の「当てずっぽう」は、点をどれだけ押し上げるのか？（架空のデータ）

架空の社内資格試験（4択・50問・30問以上で合格）。受験者ごとに「知っている問の割合」を置き、
知っている問は必ず正解、知らない問は選択肢から当てずっぽうで選ぶ（いくつかの誤りの選択肢を外せる場合も置く）。
知っている問だけの点と、当てずっぽうを含めた点を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 929
SRC = "架空の社内資格試験の受験者（作成者が乱数で作成、seed 929）"
N = 20000
K_MEAN, K_SD = 0.50, 0.15
PASS_SHARE = 0.60
BASE = {"choices": 4, "items": 50, "elim": "なし"}
# 知らない問で外せる誤りの選択肢の数（0・1・2個）の割合
ELIM = {"なし": [1.0, 0.0, 0.0], "少し": [0.5, 0.3, 0.2], "多い": [0.2, 0.4, 0.4]}


def beta_ab(mean, sd):
    v = sd ** 2
    c = mean * (1 - mean) / v - 1
    return mean * c, (1 - mean) * c


def take(rng, k, choices, items, elim):
    """k：人ごとの知っている問の割合。返り値：知っている問の数、正解の数、誤りの数"""
    n = len(k)
    known = rng.random((n, items)) < k[:, None]
    e = rng.choice(3, size=(n, items), p=ELIM[elim])
    e = np.minimum(e, choices - 2)
    lucky = rng.random((n, items)) < 1.0 / (choices - e)
    right = known | lucky
    K = known.sum(1)
    R = right.sum(1)
    return K, R, items - R


def cell(rng, choices, items, elim, n=N, k_mean=K_MEAN):
    a, b = beta_ab(k_mean, K_SD)
    k = rng.beta(a, b, n)
    K, R, W = take(rng, k, choices, items, elim)
    line = int(np.ceil(PASS_SHARE * items))
    pass_g = R >= line
    pass_k = K >= line
    corr = R - W / (choices - 1)
    # 知っている割合がちょうど半分の人
    k5 = np.full(n, 0.5)
    K5, R5, _ = take(rng, k5, choices, items, elim)
    return {"choices": choices, "items": items, "elim": elim, "k_mean": k_mean, "pass_line": line,
            "boost_points": round(float((R - K).mean() / items * 100), 2),
            "pass_rate_guess": round(float(pass_g.mean() * 100), 2),
            "pass_rate_known_only": round(float(pass_k.mean() * 100), 2),
            "share_passers_below_line": round(float((K[pass_g] < line).mean() * 100), 2),
            "pass_prob_k50_guess": round(float((R5 >= line).mean() * 100), 2),
            "pass_prob_k50_known_only": round(float((K5 >= line).mean() * 100), 2),
            "corrected_minus_known_points": round(float((corr - K).mean() / items * 100), 2),
            "k_needed_formula": round((PASS_SHARE - 1 / choices) / (1 - 1 / choices), 4)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 基本の置き方：1回分の受験者（data に置く）
    a, b = beta_ab(K_MEAN, K_SD)
    k = rng.beta(a, b, N)
    K, R, W = take(rng, k, BASE["choices"], BASE["items"], BASE["elim"])
    line = int(np.ceil(PASS_SHARE * BASE["items"]))
    df = pd.DataFrame({"person_id": np.arange(1, N + 1), "k_true": k.round(4), "known": K, "right": R, "wrong": W,
                       "passed": (R >= line).astype(int)})
    df.head(3000).to_csv(DATA / "examinees.csv", index=False)
    passers = df[df.passed == 1]
    base_one = {"n": N, "pass_line": line, "pass_rate": round(float(df.passed.mean() * 100), 2),
                "pass_rate_known_only": round(float((df.known >= line).mean() * 100), 2),
                "boost_points": round(float((df.right - df.known).mean() / BASE["items"] * 100), 2),
                "share_passers_below_line": round(float((passers.known < line).mean() * 100), 2),
                "share_passers_known_le_25": round(float((passers.known <= 25).mean() * 100), 2),
                "min_known_among_passers": int(passers.known.min()),
                "corr_mean_minus_known_points": round(float(((df.right - df.wrong / 3) - df.known).mean()
                                                            / BASE["items"] * 100), 2),
                "sd_score_guess": round(float(df.right.std() / BASE["items"] * 100), 2),
                "sd_score_known": round(float(df.known.std() / BASE["items"] * 100), 2)}

    # 知っている割合ごとの合格の確率（基本の置き方、各割合1万人）
    curve = []
    for j, kk in enumerate(np.round(np.arange(0.30, 0.751, 0.025), 3)):
        g = np.random.default_rng([SEED, 1, j])
        Kc, Rc, _ = take(g, np.full(10000, kk), BASE["choices"], BASE["items"], BASE["elim"])
        curve.append({"k": float(kk), "pass_guess": round(float((Rc >= line).mean() * 100), 2),
                      "pass_known_only": round(float((Kc >= line).mean() * 100), 2),
                      "mean_score_guess": round(float(Rc.mean() / BASE["items"] * 100), 2)})
    curve = pd.DataFrame(curve)
    curve.to_csv(RES / "pass_by_knowledge.csv", index=False)

    # 確かめ：選択肢の数 × 問の数 × 外せる選択肢
    rows = []
    j = 0
    for c in [3, 4, 5]:
        for it in [20, 50, 100]:
            for el in ELIM:
                rows.append(cell(np.random.default_rng([SEED, 2, j]), c, it, el)); j += 1
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "robustness.csv", index=False)
    kdf = pd.DataFrame([cell(np.random.default_rng([SEED, 3, i]), 4, 50, "なし", k_mean=km)
                        for i, km in enumerate([0.4, 0.5, 0.6])])
    kdf.to_csv(RES / "by_k_mean.csv", index=False)
    basecell = grid[(grid.choices == 4) & (grid["items"] == 50) & (grid.elim == "なし")].iloc[0].to_dict()

    out = {"settings": {"n": N, "k_mean": K_MEAN, "k_sd": K_SD, "pass_share": PASS_SHARE, **BASE,
                        "elim_mix": ELIM},
           "base_one_draw": base_one, "base_cell": basecell,
           "pass_by_knowledge": curve.to_dict("records"), "grid": grid.to_dict("records"),
           "by_k_mean": kdf.to_dict("records"),
           "summary": {"n_cells": int(len(grid)), "boost_range": [float(grid.boost_points.min()), float(grid.boost_points.max())],
                       "share_below_range": [float(grid.share_passers_below_line.min()),
                                             float(grid.share_passers_below_line.max())],
                       "pass_k50_range": [float(grid.pass_prob_k50_guess.min()), float(grid.pass_prob_k50_guess.max())],
                       "corr_err_range": [float(grid.corrected_minus_known_points.min()),
                                          float(grid.corrected_minus_known_points.max())],
                       "corr_err_elim_range": [float(grid[grid.elim != "なし"].corrected_minus_known_points.min()),
                                               float(grid[grid.elim != "なし"].corrected_minus_known_points.max())],
                       "corr_err_none_range": [float(grid[grid.elim == "なし"].corrected_minus_known_points.min()),
                                               float(grid[grid.elim == "なし"].corrected_minus_known_points.max())]}}
    json.dump(out, open(RES / "a929_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：知っている割合ごとの合格の確率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(curve.k * 100, curve.pass_guess, color=ORANGE, marker="o", ms=4, label="当てずっぽうを含めた点で")
    ax.plot(curve.k * 100, curve.pass_known_only, color=BLUE, marker="o", ms=4, label="知っている問だけの点で")
    ax.axvline(PASS_SHARE * 100, color=GRAY, ls="--", lw=1)
    ax.text(PASS_SHARE * 100 + 0.5, 5, "合格点（60%）", color=GRAY, fontsize=9)
    ax.set_xlabel("知っている問の割合（%）"); ax.set_ylabel("合格する確率（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    r50 = curve[curve.k == 0.5].iloc[0]
    ax.set_title(f"半分しか知らない人も{r50.pass_guess:.0f}%の確率で受かる（4択50問・30問で合格）")
    save(fig, "a929_pass_curve.png", SRC)

    # 図2：合格した人の、知っている問の数
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    bins = np.arange(passers.known.min() - 0.5, passers.known.max() + 1.5)
    below = passers[passers.known < line].known
    above = passers[passers.known >= line].known
    ax.hist([below, above], bins=bins, stacked=True, color=[ORANGE, BLUE],
            label=[f"知っている問が{line}問未満", f"{line}問以上"])
    ax.axvline(line - 0.5, color=GRAY, ls="--", lw=1)
    ax.set_xlabel("合格した人が知っていた問の数（50問中）"); ax.set_ylabel("人数")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"合格した人の{base_one['share_passers_below_line']:.1f}%は、知っている問だけでは合格点に届かなかった")
    save(fig, "a929_passers_known.png", SRC)

    # 図3：選択肢の数と外せる選択肢で、合格者のうち届かない人の割合（50問）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    g50 = grid[grid["items"] == 50]
    x = np.arange(3)
    for i, (el, col) in enumerate(zip(ELIM, [BLUE, LIGHT, ORANGE])):
        v = g50[g50.elim == el].share_passers_below_line.values
        ax.bar(x + (i - 1) * 0.27, v, 0.27, color=col, label=f"外せる誤りの選択肢：{el}")
        for xi, vi in zip(x + (i - 1) * 0.27, v):
            ax.text(xi, vi + 1, f"{vi:.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(x, ["3択", "4択", "5択"])
    ax.set_ylabel("合格者のうち、知っている問では届かない人（%）", fontsize=10)
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("選択肢が少なく、誤りを外せるほど、当てずっぽうの分は大きい（50問）")
    save(fig, "a929_by_choices.png", SRC)
    print(json.dumps(base_one, ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
