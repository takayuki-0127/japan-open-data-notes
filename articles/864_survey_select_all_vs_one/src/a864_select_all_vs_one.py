"""864 「当てはまるものをすべて」と「1つだけ」で、割合はどう変わるのか？（架空のデータ）

架空の料理レシピのサービスの利用者1,000人。8つの機能について、利用者ごとに
「使っているか」（作成者が置いた正解）と「その機能をどれだけ大事に思っているか」（強さ）を置く。
同じ人に次の聞き方をしたときの割合を比べる。
  ・機能ごとに「はい・いいえ」で聞く（各機能 はい・いいえ）
  ・当てはまるものをすべて選ぶ（すべて）：使っている機能でも、強さの弱いものは選び忘れることがある
  ・いちばん大事なものを1つだけ選ぶ（1つだけ）：使っている機能のうち、強さ＋迷いがいちばん大きいもの
「すべて」は、回答者数で割る数え方と、選ばれた数の合計で割る数え方の2つで数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy_free import norm_ppf
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 864
SRC = "架空の料理レシピのサービスの利用者アンケート（作成者が乱数で作成、seed 864）"
N, REPS, REPS_R = 1000, 2000, 300
ITEMS = ["検索", "お気に入り保存", "人気順の一覧", "タイマー", "手順の動画", "買い物リスト", "献立の提案", "コメント欄"]
P_USE = np.array([0.80, 0.55, 0.50, 0.45, 0.40, 0.30, 0.25, 0.20])   # 使っている人の割合（正解）
MU = np.array([-0.6, 0.0, -0.3, -0.8, 0.8, 0.6, 0.9, -0.5])          # 使っている人の、その機能の強さの平均
LAM, SIG, C_ALL, C_YN, C1 = 0.5, 0.5, 1.9, 3.5, 1.0
THR = norm_ppf(P_USE)


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def survey(rng, n, lam=LAM, sig=SIG, c_all=C_ALL, mu=MU):
    """1回分の調査。返り値：使っているか・強さ・各機能はい/いいえ・すべて・1つだけ（-1は特になし）"""
    m = len(P_USE)
    a = rng.standard_normal((n, 1))
    z = lam * a + np.sqrt(1 - lam ** 2) * rng.standard_normal((n, m))
    use = z < THR
    s = mu + rng.standard_normal((n, m))
    yn = use & (rng.random((n, m)) < sigmoid(C_YN + C1 * s))
    alls = use & (rng.random((n, m)) < sigmoid(c_all + C1 * s))
    sc = np.where(use, s + sig * rng.standard_normal((n, m)), -np.inf)
    one = np.where(use.any(1), sc.argmax(1), -1)
    return use, s, yn, alls, one


def shares(use, yn, alls, one):
    m = use.shape[1]
    one_sh = np.array([(one == i).mean() for i in range(m)])
    return {"truth": use.mean(0), "yn": yn.mean(0), "all": alls.mean(0),
            "all_mention": alls.sum(0) / alls.sum(), "one": one_sh,
            "none_one": float((one == -1).mean()), "n_checked_all": float(alls.sum(1).mean()),
            "n_used": float(use.sum(1).mean())}


def ranks(x):
    """大きい順の順位（1が最上位）。同点は平均"""
    return pd.Series(x).rank(ascending=False, method="average").values


def spearman(a, b):
    return float(np.corrcoef(ranks(a), ranks(b))[0, 1])


def many(rng, reps, **kw):
    out = {k: [] for k in ["truth", "yn", "all", "all_mention", "one"]}
    extra = {"none_one": [], "n_checked_all": [], "n_used": [], "sp_one": [], "sp_all": [], "sp_yn": [],
             "top_one": [], "top_all": [], "rank_search_one": []}
    for _ in range(reps):
        use, s, yn, alls, one = survey(rng, N, **kw)
        sh = shares(use, yn, alls, one)
        for k in out:
            out[k].append(sh[k])
        for k in ["none_one", "n_checked_all", "n_used"]:
            extra[k].append(sh[k])
        extra["sp_one"].append(spearman(sh["truth"], sh["one"]))
        extra["sp_all"].append(spearman(sh["truth"], sh["all"]))
        extra["sp_yn"].append(spearman(sh["truth"], sh["yn"]))
        extra["top_one"].append(int(np.argmax(sh["one"]) == np.argmax(sh["truth"])))
        extra["top_all"].append(int(np.argmax(sh["all"]) == np.argmax(sh["truth"])))
        extra["rank_search_one"].append(ranks(sh["one"])[0])
    return {k: np.array(v) for k, v in out.items()}, {k: np.array(v) for k, v in extra.items()}


def r3(x):
    return round(float(x), 3)


def main():
    rng = np.random.default_rng(SEED)

    # 1回分の調査（data）
    use, s, yn, alls, one = survey(rng, N)
    d = {"id": np.arange(1, N + 1)}
    for i, it in enumerate(ITEMS):
        d[f"use_{i+1}"] = use[:, i].astype(int)
    for i, it in enumerate(ITEMS):
        d[f"all_{i+1}"] = alls[:, i].astype(int)
    for i, it in enumerate(ITEMS):
        d[f"yn_{i+1}"] = yn[:, i].astype(int)
    d["one"] = np.where(one >= 0, one + 1, 0)
    pd.DataFrame(d).to_csv(DATA / "respondents.csv", index=False)
    pd.DataFrame({"item_no": np.arange(1, 9), "item": ITEMS}).to_csv(DATA / "items.csv", index=False)
    one_sh = shares(use, yn, alls, one)

    # 2,000回
    sh, ex = many(rng, REPS)
    tab = pd.DataFrame({"item": ITEMS, "truth": P_USE, "mu_strength": MU,
                        "truth_sim": sh["truth"].mean(0), "yn": sh["yn"].mean(0), "all": sh["all"].mean(0),
                        "all_mention": sh["all_mention"].mean(0), "one": sh["one"].mean(0)})
    tab["one_over_truth"] = tab["one"] / tab["truth_sim"]
    tab["all_over_truth"] = tab["all"] / tab["truth_sim"]
    for k in ["truth_sim", "yn", "all", "all_mention", "one"]:
        tab[f"rank_{k}"] = ranks(tab[k].values)
    tab.round(4).to_csv(RES / "shares_by_format.csv", index=False)

    main_ = {"n_respondents": N, "reps": REPS,
             "sum_truth": r3(sh["truth"].mean(0).sum()), "sum_yn": r3(sh["yn"].mean(0).sum()),
             "sum_all": r3(sh["all"].mean(0).sum()), "sum_all_mention": r3(sh["all_mention"].mean(0).sum()),
             "sum_one": r3(sh["one"].mean(0).sum()), "none_one": r3(ex["none_one"].mean()),
             "n_used_mean": r3(ex["n_used"].mean()), "n_checked_all_mean": r3(ex["n_checked_all"].mean()),
             "recall_all": r3(sh["all"].mean(0).sum() / sh["truth"].mean(0).sum()),
             "recall_yn": r3(sh["yn"].mean(0).sum() / sh["truth"].mean(0).sum()),
             "spearman_one_mean": r3(ex["sp_one"].mean()), "spearman_all_mean": r3(ex["sp_all"].mean()),
             "spearman_yn_mean": r3(ex["sp_yn"].mean()),
             "top_correct_one": r3(ex["top_one"].mean()), "top_correct_all": r3(ex["top_all"].mean()),
             "search_rank_one_mean": r3(ex["rank_search_one"].mean()),
             "search_one_p05_p95": [r3(np.quantile(sh["one"][:, 0], .05)), r3(np.quantile(sh["one"][:, 0], .95))],
             "one_top_item_counts": {ITEMS[i]: int((sh["one"].argmax(1) == i).sum()) for i in range(8)}}
    # 「1つだけ」で選ばれた機能を、使っている人のうち何%がいちばんに選んだか
    main_["one_among_users"] = {ITEMS[i]: r3(sh["one"].mean(0)[i] / sh["truth"].mean(0)[i]) for i in range(8)}

    # 確かめ：使い方の重なり λ × 迷い σ × 選び忘れ c_all、強さの差なし
    rows = []
    for lam in [0.0, 0.5, 0.8]:
        for sig in [0.25, 0.5, 1.5]:
            for c_all in [1.0, 1.9, 3.0]:
                g = np.random.default_rng(SEED * 100 + int(lam * 10) * 9 + int(sig * 4) * 3 + int(c_all))
                a, e = many(g, REPS_R, lam=lam, sig=sig, c_all=c_all)
                rows.append({"variant": "基本の強さ", "lam": lam, "sig": sig, "c_all": c_all,
                             "search_one": r3(a["one"].mean(0)[0]), "search_rank_one": r3(e["rank_search_one"].mean()),
                             "spearman_one": r3(e["sp_one"].mean()), "spearman_all": r3(e["sp_all"].mean()),
                             "recall_all": r3(a["all"].mean(0).sum() / a["truth"].mean(0).sum()),
                             "comment_all_over_truth": r3(a["all"].mean(0)[7] / a["truth"].mean(0)[7]),
                             "video_all_over_truth": r3(a["all"].mean(0)[4] / a["truth"].mean(0)[4]),
                             "top_correct_one": r3(e["top_one"].mean())})
    for sig in [0.25, 0.5, 1.5]:
        g = np.random.default_rng(SEED * 1000 + int(sig * 4))
        a, e = many(g, REPS_R, sig=sig, mu=np.zeros(8))
        rows.append({"variant": "強さの差なし", "lam": LAM, "sig": sig, "c_all": C_ALL,
                     "search_one": r3(a["one"].mean(0)[0]), "search_rank_one": r3(e["rank_search_one"].mean()),
                     "spearman_one": r3(e["sp_one"].mean()), "spearman_all": r3(e["sp_all"].mean()),
                     "recall_all": r3(a["all"].mean(0).sum() / a["truth"].mean(0).sum()),
                     "comment_all_over_truth": r3(a["all"].mean(0)[7] / a["truth"].mean(0)[7]),
                     "video_all_over_truth": r3(a["all"].mean(0)[4] / a["truth"].mean(0)[4]),
                     "top_correct_one": r3(e["top_one"].mean())})
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness.csv", index=False)
    base = rob[rob.variant == "基本の強さ"]
    nomu = rob[rob.variant == "強さの差なし"]
    main_["robust"] = {"combos": int(len(base)),
                       "search_one_min": float(base.search_one.min()), "search_one_max": float(base.search_one.max()),
                       "search_rank_one_min": float(base.search_rank_one.min()),
                       "search_rank_one_max": float(base.search_rank_one.max()),
                       "spearman_one_min": float(base.spearman_one.min()), "spearman_one_max": float(base.spearman_one.max()),
                       "recall_all_min": float(base.recall_all.min()), "recall_all_max": float(base.recall_all.max()),
                       "comment_all_over_truth_min": float(base.comment_all_over_truth.min()),
                       "comment_all_over_truth_max": float(base.comment_all_over_truth.max()),
                       "video_all_over_truth_min": float(base.video_all_over_truth.min()),
                       "video_all_over_truth_max": float(base.video_all_over_truth.max()),
                       "no_strength_search_one": nomu.search_one.tolist(),
                       "no_strength_spearman_one": nomu.spearman_one.tolist(),
                       "no_strength_search_rank_one": nomu.search_rank_one.tolist()}
    main_["one_survey"] = {"truth": [r3(x) for x in one_sh["truth"]], "all": [r3(x) for x in one_sh["all"]],
                           "one": [r3(x) for x in one_sh["one"]], "yn": [r3(x) for x in one_sh["yn"]],
                           "none_one": r3(one_sh["none_one"])}
    json.dump(main_, open(RES / "a864_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：聞き方ごとの割合
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    x = np.arange(8); w = 0.2
    ax.bar(x - 1.5 * w, tab.truth_sim * 100, w, color=INK, label="正解（使っている人）")
    ax.bar(x - 0.5 * w, tab["all"] * 100, w, color=BLUE, label="すべて（回答者数で割る）")
    ax.bar(x + 0.5 * w, tab.all_mention * 100, w, color=LIGHT, label="すべて（選ばれた数で割る）")
    ax.bar(x + 1.5 * w, tab.one * 100, w, color=ORANGE, label="1つだけ")
    ax.set_xticks(x); ax.set_xticklabels(ITEMS, fontsize=9, rotation=25)
    ax.set_ylabel("割合（%、2,000回の平均）"); ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("同じ利用者でも、聞き方と割り方で機能ごとの割合が変わる")
    save(fig, "a864_formats.png", SRC)

    # 図2：使っている割合と「1つだけ」の割合
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.scatter(tab.truth_sim * 100, tab.one * 100, s=40, color=ORANGE, zorder=3)
    for i, it in enumerate(ITEMS):
        off = {"買い物リスト": (5, -12), "献立の提案": (-8, 6)}.get(it, (5, 3))
        ax.annotate(it, (tab.truth_sim[i] * 100, tab.one[i] * 100), xytext=off, textcoords="offset points",
                    fontsize=9, ha="right" if off[0] < 0 else "left")
    ax.set_xlabel("使っている人の割合（正解、%）"); ax.set_ylabel("「1つだけ」で選ばれた割合（%）")
    ax.set_xlim(10, 90); ax.set_ylim(0, 30)
    ax.set_title(f"いちばん多く使われる検索は、「1つだけ」では{ranks(tab.one.values)[0]:.0f}位")
    save(fig, "a864_use_vs_one.png", SRC)

    # 図3：確かめ（重なり×迷い、選び忘れは基本）での検索の「1つだけ」の割合と、1位が合った割合
    bb = base[base.c_all == C_ALL].sort_values(["lam", "sig"])
    labs = [f"重なり{a}・迷い{b}" for a, b in zip(bb.lam, bb.sig)]
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 4.0))
    yy = np.arange(len(bb))
    axs[0].barh(yy, bb.search_one * 100, color=ORANGE)
    axs[0].axvline(80, color=INK, lw=1, ls="--"); axs[0].text(79, -0.7, "使っている人 80%", ha="right", fontsize=8)
    for i, v in enumerate(bb.search_one * 100):
        axs[0].text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8)
    axs[0].set_yticks(yy); axs[0].set_yticklabels(labs, fontsize=8); axs[0].invert_yaxis(); axs[0].set_xlim(0, 90)
    axs[0].set_xlabel("検索の「1つだけ」の割合（%）", fontsize=9)
    axs[1].barh(yy, bb.top_correct_one * 100, color=BLUE)
    for i, v in enumerate(bb.top_correct_one * 100):
        axs[1].text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8)
    axs[1].set_yticks(yy); axs[1].set_yticklabels([]); axs[1].invert_yaxis(); axs[1].set_xlim(0, 115)
    axs[1].set_xlabel("「1つだけ」の1位が検索だった調査（%）", fontsize=9)
    fig.suptitle("「1つだけ」の割合は使っている割合と別もの。1位が合うかは置き方しだい", fontsize=12)
    save(fig, "a864_robustness.png", SRC)
    print(json.dumps(main_, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
