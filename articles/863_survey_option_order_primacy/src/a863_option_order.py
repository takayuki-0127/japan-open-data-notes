"""863 選択肢の並び順で、先頭の選択肢は何%選ばれやすいのか？（架空のデータ）

架空のオンライン講座の利用者400人に「次に増やしてほしい講座」を8つの案から1つ選んでもらう。
案ごとに「本当に選ばれる割合」s（並び順の影響がないときの割合。作成者が置いた正解）を置く。
回答者のうち 1−u は好みだけで選ぶ（案 i を s_i の確率で選ぶ）。
残り u（迷う人、基本0.3）は、好みと並び順の両方で選ぶ：案 i を s_i × w(位置) に比例する確率で選ぶ。
  w(位置) = exp(−k×(位置−1))、k は上に置かれた案の選ばれやすさの強さ（基本0.5）。
並べ方は2つ：案の番号順で全員同じ（固定）／回答者ごとにでたらめに並べかえる（並べかえ）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 863
SRC = "架空のオンライン講座の利用者アンケート（作成者が乱数で作成、seed 863）"
N, REPS, U, K = 400, 2000, 0.3, 0.5
# 案1〜案8 の本当に選ばれる割合（案1は4番目に人気、本当の1番人気は案3）
S = np.array([0.13, 0.09, 0.20, 0.07, 0.17, 0.11, 0.15, 0.08])
LABELS = [f"案{i}" for i in range(1, 9)]


def weights(n, k):
    return np.exp(-k * np.arange(n))


def p_fixed(s, u, k):
    """全員同じ並び（案の番号順）のときの、案ごとの選ばれる確率"""
    q = s * weights(len(s), k)
    return (1 - u) * s + u * q / q.sum()


def p_at_position(s, u, k, rng, n_perm=20000):
    """案 i を位置 j に置き、ほかをでたらめに並べたときの、案 i の選ばれる確率（並べ方の平均）。返り値は [案, 位置]"""
    n = len(s); w = weights(n, k)
    out = np.zeros((n, n)); cnt = np.zeros((n, n))
    perms = np.argsort(rng.random((n_perm, n)), 1)        # perms[r, 位置] = 案
    pos_of = np.argsort(perms, 1)                          # pos_of[r, 案] = 位置
    ws = s[None, :] * w[pos_of]
    pr = (1 - u) * s[None, :] + u * ws / ws.sum(1, keepdims=True)
    for i in range(n):
        np.add.at(out[i], pos_of[:, i], pr[:, i]); np.add.at(cnt[i], pos_of[:, i], 1)
    return out / cnt, pr.mean(0)


def simulate(rng, reps, s, u, k, n=N):
    """固定と並べかえの調査を reps 回。返り値：観測の割合 [reps, 案]"""
    m = len(s)
    fixed = rng.multinomial(n, p_fixed(s, u, k), size=reps) / n
    perms = np.argsort(rng.random((reps, n, m)), 2)
    pos_of = np.argsort(perms, 2)
    ws = s * weights(m, k)[pos_of]
    pr = (1 - u) * s + u * ws / ws.sum(2, keepdims=True)
    c = (rng.random((reps, n, 1)) > np.cumsum(pr, 2)).sum(2)
    c = np.minimum(c, m - 1)
    rand = np.stack([(c == i).mean(1) for i in range(m)], 1)
    return fixed, rand


def main():
    rng = np.random.default_rng(SEED)

    # 1回分の調査（data）：固定400人＋並べかえ400人
    rows = []
    pf = p_fixed(S, U, K)
    for d in ["固定（案の番号順）", "並べかえ"]:
        for r in range(N):
            order = np.arange(8) if d.startswith("固定") else rng.permutation(8)
            pos_of = np.argsort(order)
            decided = rng.random() >= U
            if decided:
                p = S
            else:
                q = S * weights(8, K)[pos_of]; p = q / q.sum()
            ch = rng.choice(8, p=p)
            rows.append({"id": len(rows) + 1, "design": d, "order": "-".join(str(o + 1) for o in order),
                         "chosen": LABELS[ch], "chosen_position": int(pos_of[ch]) + 1, "decided_by_preference": int(decided)})
    one = pd.DataFrame(rows)
    one.to_csv(DATA / "respondents.csv", index=False)
    one_share = one.groupby(["design", "chosen"]).size().unstack(fill_value=0)
    one_share = (one_share.T / one_share.sum(1)).T.reindex(columns=LABELS).round(4)
    one_share.to_csv(RES / "one_survey_shares.csv")

    # 2) 理屈の値：案 i を各位置に置いたとき（ほかはでたらめ）
    pos_tab, rand_expect = p_at_position(S, U, K, rng)
    pt = pd.DataFrame(pos_tab, index=LABELS, columns=[f"位置{j}" for j in range(1, 9)]).round(4)
    pt.insert(0, "正解", S)
    pt["並べかえの平均"] = rand_expect.round(4)
    pt["先頭の上乗せ_ポイント"] = ((pos_tab[:, 0] - S) * 100).round(2)
    pt["先頭の倍率"] = (pos_tab[:, 0] / S).round(3)
    pt.to_csv(RES / "share_by_position.csv")

    # 3) 2,000回の調査（固定と並べかえ）
    fixed, rand = simulate(rng, REPS, S, U, K)
    true_rank = np.argsort(-S)
    res = {}
    for name, obs in [("fixed", fixed), ("random", rand)]:
        top1 = (obs + rng.random(obs.shape) * 1e-9).argmax(1)   # 同数はくじで決める
        res[name] = {"mean_share": dict(zip(LABELS, obs.mean(0).round(4).tolist())),
                     "p10": dict(zip(LABELS, np.quantile(obs, .1, 0).round(4).tolist())),
                     "p90": dict(zip(LABELS, np.quantile(obs, .9, 0).round(4).tolist())),
                     "top1_is_true_top(案3)": round(float((top1 == 2).mean()), 4),
                     "top1_is_案1": round(float((top1 == 0).mean()), 4),
                     "案1_rank_mean": round(float((obs > obs[:, [0]]).sum(1).mean() + 1), 3),
                     "max_abs_err_points_mean": round(float(np.abs(obs - S).max(1).mean() * 100), 2),
                     "rank_corr_mean": round(float(np.mean([np.corrcoef(np.argsort(np.argsort(-o)), np.argsort(np.argsort(-S)))[0, 1]
                                                             for o in obs])), 3)}
    res["fixed_expected"] = dict(zip(LABELS, pf.round(4).tolist()))
    res["random_expected_max_abs_err_points"] = round(float(np.abs(rand_expect - S).max() * 100), 2)

    # 4) 確かめ：迷う人の割合 u・位置の効き k・案の数（全部同じ人気のとき、先頭の倍率）
    rob = []
    for m in [4, 6, 8]:
        for u in [0.1, 0.2, 0.3, 0.5]:
            for k in [0.25, 0.5, 1.0]:
                w = weights(m, k)
                top = (1 - u) / m + u * w[0] / w.sum()
                last = (1 - u) / m + u * w[-1] / w.sum()
                rob.append({"n_options": m, "u": u, "k": k, "equal_share": round(1 / m, 4), "top_share": round(top, 4),
                            "top_ratio": round(top * m, 3), "top_plus_points": round((top - 1 / m) * 100, 2),
                            "last_ratio": round(last * m, 3)})
    rob = pd.DataFrame(rob)
    # 4b) 確かめ：8案（置いた人気）の固定の並びで、案1（4番人気）が1位に見える割合（各500回）
    flip = []
    for u in [0.1, 0.2, 0.3, 0.5]:
        for k in [0.25, 0.5, 1.0]:
            g = np.random.default_rng(SEED * 100 + int(u * 100) * 10 + int(k * 4))
            obs = g.multinomial(N, p_fixed(S, u, k), size=500) / N
            t1 = (obs + g.random(obs.shape) * 1e-9).argmax(1)   # 同数はくじで決める
            flip.append({"u": u, "k": k, "案1_expected": round(float(p_fixed(S, u, k)[0]), 4),
                         "案3_expected": round(float(p_fixed(S, u, k)[2]), 4),
                         "top1_is_案1": round(float((t1 == 0).mean()), 3),
                         "top1_is_案3": round(float((t1 == 2).mean()), 3)})
    flip = pd.DataFrame(flip)
    rob.to_csv(RES / "robustness_equal_share.csv", index=False)
    flip.to_csv(RES / "robustness_fixed_rank.csv", index=False)
    r8 = rob[rob.n_options == 8]
    robs = {"top_ratio_min": float(rob.top_ratio.min()), "top_ratio_max": float(rob.top_ratio.max()),
            "n8_u03_k05": rob[(rob.n_options == 8) & (rob.u == .3) & (rob.k == .5)].iloc[0].to_dict(),
            "n8_top_ratio_min": float(r8.top_ratio.min()), "n8_top_ratio_max": float(r8.top_ratio.max()),
            "k05_by_n_u03": rob[(rob.u == .3) & (rob.k == .5)].set_index("n_options").top_ratio.to_dict(),
            "u_by_k05_n8": r8[r8.k == .5].set_index("u").top_ratio.to_dict(),
            "flip_案1_min": float(flip.top1_is_案1.min()), "flip_案1_max": float(flip.top1_is_案1.max()),
            "flip_by_u_k05": flip[flip.k == .5].set_index("u")[["案1_expected", "top1_is_案1", "top1_is_案3"]].to_dict("index")}

    out = {"setting": {"N": N, "reps": REPS, "u": U, "k": K, "true_share": dict(zip(LABELS, S.tolist())),
                       "position_weight": weights(8, K).round(4).tolist()},
           "share_at_top": {"plus_points": dict(zip(LABELS, pt["先頭の上乗せ_ポイント"].tolist())),
                            "ratio": dict(zip(LABELS, pt["先頭の倍率"].tolist())),
                            "ratio_min": float(pt["先頭の倍率"].min()), "ratio_max": float(pt["先頭の倍率"].max()),
                            "last_ratio_min": float((pos_tab[:, -1] / S).min().round(3)),
                            "last_ratio_max": float((pos_tab[:, -1] / S).max().round(3))},
           "surveys": res, "one_survey": one_share.to_dict("index"), "robustness": robs}
    json.dump(out, open(RES / "a863_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：正解・固定・並べかえ
    x = np.arange(8); wdt = .27
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    fm, rm = fixed.mean(0) * 100, rand.mean(0) * 100
    ax.bar(x - wdt, S * 100, wdt, color=GRAY, label="正解（並び順の影響がないとき）")
    ax.bar(x, fm, wdt, color=ORANGE, label="全員同じ並び（案の番号順）")
    ax.bar(x + wdt, rm, wdt, color=BLUE, label="回答者ごとに並べかえ")
    ax.set_xticks(x); ax.set_xticklabels([f"{l}\n（{i+1}番目）" for i, l in enumerate(LABELS)], fontsize=8.5)
    ax.set_ylabel("選ばれた割合（%、2,000回の平均）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title(f"番号順に並べると、先頭の案1（本当は4番人気）が平均{fm[0]:.1f}%で1番人気の案3（{fm[2]:.1f}%）を上回った",
                 fontsize=10)
    save(fig, "a863_shares.png", SRC)

    # 図2：案ごとに、置いた位置と選ばれる割合（正解を1とした倍率）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cols = [ORANGE, GRAY, BLUE, LIGHT, GREEN, "#c0502a", INK, "#8a6fbf"]
    for i in range(8):
        ax.plot(np.arange(1, 9), pos_tab[i] / S[i], marker="o", ms=3.5, color=cols[i], lw=1.2,
                label=f"{LABELS[i]}（正解{S[i]*100:.0f}%）")
    ax.axhline(1, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("その案を置いた位置（上から何番目か）"); ax.set_ylabel("選ばれる割合 ÷ 正解")
    ax.legend(frameon=False, fontsize=7.5, ncol=2)
    ax.set_title(f"先頭に置くと{pt['先頭の倍率'].min():.2f}〜{pt['先頭の倍率'].max():.2f}倍。人気の低い案ほど上乗せの倍率が大きい",
                 fontsize=11)
    save(fig, "a863_by_position.png", SRC)

    # 図3：確かめ（全部同じ人気、先頭の倍率）
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 3.5), sharey=True)
    for ax, m in zip(axs, [4, 6, 8]):
        g = rob[rob.n_options == m]
        for k, c in [(0.25, LIGHT), (0.5, BLUE), (1.0, INK)]:
            gg = g[g.k == k]
            ax.plot(gg.u * 100, gg.top_ratio, marker="o", color=c, label=f"位置の効き k={k}")
        ax.axhline(1, color=GRAY, lw=.8, ls=":"); ax.set_title(f"案が{m}つ", fontsize=10)
        ax.set_xlabel("迷う人の割合（%）")
    axs[0].set_ylabel("先頭の案の選ばれる割合 ÷ 正解"); axs[0].legend(frameon=False, fontsize=7.5)
    fig.suptitle("先頭の上乗せは、迷う人の割合と位置の効きの置き方でほぼ決まる（全部同じ人気のとき）", fontsize=11, y=1.03)
    save(fig, "a863_robustness.png", SRC, y=-0.06)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
