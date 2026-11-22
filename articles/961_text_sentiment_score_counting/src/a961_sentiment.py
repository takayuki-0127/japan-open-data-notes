"""961 前向き・後ろ向きの点数は、言葉の数え方でどれだけ変わるのか？（架空のデータ）

作成者が乱数で語を組み合わせて作った架空の店20軒への感想2,000件。感想ごとの「本当の気持ち」と
店ごとの「本当の満足」を作成者が置き、作成者が決めた前向きの語12・後ろ向きの語12の一覧で点数を数える。
数え方5つで、感想の点・店の順位がどれだけ変わるか、本当の満足とどれだけ合うかを数える。
語の区切りは作成者が置いた空白。「ない」は直前の語の向きを逆にする語と作成者が決めた。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 961
SRC = "架空の店への感想（作成者が乱数で語を組み合わせて作成、seed 961）"
N_SHOP, N_PER = 20, 100
SHOPS = [f"店{c}" for c in "ABCDEFGHIJKLMNOPQRST"]
POS = ["おいしい", "丁寧", "早い", "満足", "清潔", "親切", "落ち着く", "新鮮", "便利", "明るい", "静か", "好き"]
NEG = ["まずい", "遅い", "不満", "汚い", "冷たい", "雑", "狭い", "うるさい", "残念", "不便", "暗い", "嫌い"]
NEU = ["料理", "店", "席", "今日", "注文", "です", "ます", "とても", "少し", "量", "値段", "店員",
       "また", "友人", "昼", "夜", "思う", "感じ", "雰囲気", "メニュー"]
BASE = dict(shop_sd=0.5, len_median=15, shop_len_sd=0.5, len_noise=0.4, gamma=0.3, q_sent=0.25, slope=1.5, neg_rate=0.15)
METHODS = ["diff", "per_word", "per_sent", "sign", "negation"]
MLABEL = {"diff": "①語の数の差", "per_word": "②差÷語数", "per_sent": "③差÷前向き・後ろ向きの語数",
          "sign": "④向きだけ（+1・0・−1）", "negation": "⑤「ない」で向きを逆にして③"}


def simulate(rng, shop_sd=0.5, len_median=15, shop_len_sd=0.5, len_noise=0.4, gamma=0.3, q_sent=0.25,
             slope=1.5, neg_rate=0.15):
    """感想ごとの語の数を作る。戻り値：店の本当の満足・店の長さ、感想ごとの数"""
    m = rng.normal(0, shop_sd, N_SHOP)                      # 店の本当の満足
    shop_len = len_median * np.exp(shop_len_sd * rng.standard_normal(N_SHOP))
    shop = np.repeat(np.arange(N_SHOP), N_PER)
    y = m[shop] + rng.standard_normal(len(shop))            # 感想ごとの本当の気持ち
    L = np.clip(np.round(shop_len[shop] * np.exp(-gamma * y + len_noise * rng.standard_normal(len(shop)))), 3, 80).astype(int)
    K = rng.binomial(L, q_sent)                             # 前向き・後ろ向きの語の数
    p_pos = 1 / (1 + np.exp(-slope * y))
    ip = rng.binomial(K, p_pos)                             # 前向きのつもりの語
    ineg = K - ip                                           # 後ろ向きのつもりの語
    np_ = rng.binomial(ip, neg_rate)                        # 前向きを「後ろ向きの語＋ない」で書いた数
    nn_ = rng.binomial(ineg, neg_rate)                      # 後ろ向きを「前向きの語＋ない」で書いた数
    sp = ip - np_ + nn_                                     # 見た目の前向きの語
    sn = ineg - nn_ + np_                                   # 見た目の後ろ向きの語
    return dict(m=m, shop_len=shop_len, shop=shop, y=y, L=L, K=K, ip=ip, ineg=ineg, np_=np_, nn_=nn_, sp=sp, sn=sn)


def scores(d):
    sp, sn, L, K = d["sp"], d["sn"], d["L"], d["K"]
    diff = (sp - sn).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        per_sent = np.where(K > 0, diff / np.maximum(K, 1), 0.0)
        neg = np.where(K > 0, (d["ip"] - d["ineg"]) / np.maximum(K, 1), 0.0)
    return {"diff": diff, "per_word": diff / L, "per_sent": per_sent, "sign": np.sign(diff), "negation": neg}


def rank_desc(v):
    """大きい順の順位（1が最上位、同点は平均順位）"""
    return pd.Series(v).rank(ascending=False, method="average").values


def evaluate(d):
    sc = scores(d)
    m, shop = d["m"], d["shop"]
    true_rank = rank_desc(m)
    true_top5 = set(np.argsort(-m)[:5])
    res = {}
    shop_scores = {}
    for k in METHODS:
        s = np.bincount(shop, sc[k], N_SHOP) / N_PER
        shop_scores[k] = s
        rk = rank_desc(s)
        res[k] = {"review_spearman_true": float(spearmanr(sc[k], d["y"])[0]),
                  "shop_spearman_true": float(spearmanr(s, m)[0]),
                  "shop_spearman_len": float(spearmanr(s, d["shop_len"])[0]),
                  "top5_hit": int(len(set(np.argsort(-s)[:5]) & true_top5)),
                  "top1_true": int(np.argmax(s) == np.argmax(m)),
                  "mean_abs_rank_err": float(np.abs(rk - true_rank).mean())}
    # 数え方どうしで順位がどれだけ動くか
    ranks = np.array([rank_desc(shop_scores[k]) for k in METHODS])
    spread = ranks.max(0) - ranks.min(0)
    res["max_rank_spread"] = float(spread.max())
    res["shops_move_5plus"] = int((spread >= 5).sum())
    res["top1_all_same"] = int(len(set(int(np.argmax(shop_scores[k])) for k in METHODS)) == 1)
    res["diff_vs_negation_spearman"] = float(spearmanr(shop_scores["diff"], shop_scores["negation"])[0])
    # 感想ごとの向き（+・0・−）が、①と⑤で食い違う割合
    res["review_sign_differs_diff_vs_negation"] = float((np.sign(sc["diff"]) != np.sign(sc["negation"])).mean())
    res["review_sign_opposite_diff_vs_negation"] = float((np.sign(sc["diff"]) * np.sign(sc["negation"]) < 0).mean())
    return res, sc, shop_scores, ranks


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"settings": {**BASE, "n_shop": N_SHOP, "reviews_per_shop": N_PER, "pos_words": POS, "neg_words": NEG,
                        "neutral_words": NEU, "reps": 100}}

    # 1) 1回分（基本の置き方）
    d = simulate(rng, **BASE)
    res, sc, ss, ranks = evaluate(d)
    out["base_run"] = res
    out["base_run"]["review_len_median"] = float(np.median(d["L"]))
    out["base_run"]["shop_len_min_max"] = [round(float(d["shop_len"].min()), 1), round(float(d["shop_len"].max()), 1)]
    out["base_run"]["share_no_sent_word"] = float((d["K"] == 0).mean())
    out["base_run"]["share_negated_words"] = float((d["np_"] + d["nn_"]).sum() / d["K"].sum())
    # 長さと点の関係（感想ごと）
    out["base_run"]["review_len_vs_abs_diff_spearman"] = float(spearmanr(d["L"], np.abs(sc["diff"]))[0])
    out["base_run"]["review_len_vs_true_spearman"] = float(spearmanr(d["L"], d["y"])[0])
    shop_tab = pd.DataFrame({"shop": SHOPS, "true_satisfaction": np.round(d["m"], 3), "median_len": [
        float(np.median(d["L"][d["shop"] == s])) for s in range(N_SHOP)]})
    shop_tab["true_rank"] = rank_desc(d["m"]).astype(int)
    for i, k in enumerate(METHODS):
        shop_tab[f"{k}_score"] = np.round(ss[k], 4)
        shop_tab[f"{k}_rank"] = ranks[i]
    shop_tab["rank_spread"] = ranks.max(0) - ranks.min(0)
    shop_tab = shop_tab.sort_values("true_rank")
    shop_tab.to_csv(RES / "shop_ranks_base.csv", index=False)
    # 例：順位がいちばん動いた店
    big = shop_tab.sort_values(["rank_spread", "true_rank"], ascending=[False, True]).iloc[0]
    out["base_run"]["most_moved_shop"] = {"shop": big["shop"], "true_rank": int(big["true_rank"]),
                                          "median_len": float(big["median_len"]),
                                          "ranks": {k: float(big[f"{k}_rank"]) for k in METHODS}}

    # 感想の文章（1回分）
    rows = []
    for i in range(len(d["L"])):
        L, sp, sn = int(d["L"][i]), int(d["sp"][i]), int(d["sn"][i])
        npos_neg, nneg_neg = int(d["nn_"][i]), int(d["np_"][i])   # 前向きの語＋ない、後ろ向きの語＋ない
        toks = []
        for j in range(sp):
            toks.append([rng.choice(POS)] + (["ない"] if j < npos_neg else []))
        for j in range(sn):
            toks.append([rng.choice(NEG)] + (["ない"] if j < nneg_neg else []))
        for _ in range(L - sp - sn):
            toks.append([rng.choice(NEU)])
        order = rng.permutation(len(toks))
        words = [w for o in order for w in toks[o]]
        rows.append({"review_id": i + 1, "shop": SHOPS[d["shop"][i]], "true_feeling": round(float(d["y"][i]), 3),
                     "n_words": L, "pos_words": sp, "neg_words": sn, "negated": npos_neg + nneg_neg,
                     "text": " ".join(words)})
    pd.DataFrame(rows).to_csv(DATA / "reviews.csv", index=False)

    # 2) 基本の置き方で100回
    R = 100
    acc = [evaluate(simulate(np.random.default_rng([SEED, 0, r]), **BASE))[0] for r in range(R)]
    rep = {}
    for k in METHODS:
        rep[k] = {f: round(float(np.mean([a[k][f] for a in acc])), 4) for f in acc[0][k]}
    for f in ["max_rank_spread", "shops_move_5plus", "top1_all_same", "diff_vs_negation_spearman",
              "review_sign_differs_diff_vs_negation", "review_sign_opposite_diff_vs_negation"]:
        rep[f] = round(float(np.mean([a[f] for a in acc])), 4)
    rep["max_rank_spread_median"] = float(np.median([a["max_rank_spread"] for a in acc]))
    out["base_reps"] = rep

    # 3) 置き方を変えた確かめ（各100回）
    grid = []
    gi = 0
    for gamma in [-0.3, 0.0, 0.3]:
        for neg_rate in [0.0, 0.15, 0.3]:
            for sls in [0.0, 0.5]:
                gi += 1
                kw = {**BASE, "gamma": gamma, "neg_rate": neg_rate, "shop_len_sd": sls}
                acc = [evaluate(simulate(np.random.default_rng([SEED, gi, r]), **kw))[0] for r in range(R)]
                row = {"gamma_len_by_feeling": gamma, "neg_rate": neg_rate, "shop_len_sd": sls}
                for k in METHODS:
                    row[f"{k}_shop_rho"] = round(float(np.mean([a[k]["shop_spearman_true"] for a in acc])), 4)
                    row[f"{k}_top5"] = round(float(np.mean([a[k]["top5_hit"] for a in acc])), 3)
                    row[f"{k}_review_rho"] = round(float(np.mean([a[k]["review_spearman_true"] for a in acc])), 4)
                row["max_rank_spread"] = round(float(np.mean([a["max_rank_spread"] for a in acc])), 3)
                row["shops_move_5plus"] = round(float(np.mean([a["shops_move_5plus"] for a in acc])), 3)
                row["top1_all_same"] = round(float(np.mean([a["top1_all_same"] for a in acc])), 4)
                row["review_sign_opposite"] = round(float(np.mean([a["review_sign_opposite_diff_vs_negation"] for a in acc])), 4)
                grid.append(row)
    gdf = pd.DataFrame(grid)
    gdf.to_csv(RES / "robustness_grid.csv", index=False)
    out["robustness"] = grid
    out["robustness_range"] = {c: [float(gdf[c].min()), float(gdf[c].max())] for c in gdf.columns if c not in
                               ["gamma_len_by_feeling", "neg_rate", "shop_len_sd"]}
    # 「不満な人ほど長く書く」の強さを変えたときの、順位相関の動き（同じ「ない」の割合・長さの違いの中での最大と最小の差）
    gm = 0.0
    for (nr, sls), h in gdf.groupby(["neg_rate", "shop_len_sd"]):
        for k in METHODS:
            gm = max(gm, float(h[f"{k}_shop_rho"].max() - h[f"{k}_shop_rho"].min()))
    out["gamma_effect_max_rho_range"] = round(gm, 4)
    out["run_note"] = "乱数（numpy）"
    json.dump(out, open(RES / "a961_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：店ごとの順位（数え方5つ、1回分）
    fig, ax = plt.subplots(figsize=(8.6, 5.8))
    st = shop_tab.reset_index(drop=True)
    xs = np.arange(len(METHODS) + 1)
    lens = st["median_len"].values
    q75, q25 = np.percentile(lens, 75), np.percentile(lens, 25)
    for _, r in st.iterrows():
        yv = [r["true_rank"]] + [r[f"{k}_rank"] for k in METHODS]
        c = ORANGE if r["median_len"] >= q75 else (BLUE if r["median_len"] <= q25 else LIGHT)
        ax.plot(xs, yv, "-o", color=c, lw=1.4, ms=4, alpha=0.9, zorder=3 if c != LIGHT else 2)
        ax.text(-0.12, r["true_rank"], r["shop"], ha="right", va="center", fontsize=8)
    ax.set_ylim(20.8, 0.2)
    ax.set_yticks([1, 5, 10, 15, 20])
    ax.set_xticks(xs)
    ax.set_xticklabels(["本当の満足"] + ["①差", "②差÷語数", "③差÷向きの語数", "④向きだけ", "⑤否定も見る"], fontsize=9.5)
    ax.set_ylabel("順位（1が上）"); ax.set_xlim(-0.6, len(METHODS) + 0.2)
    ax.plot([], [], color=ORANGE, label=f"感想が長い店（語数の中央値 {q75:.1f}語以上）")
    ax.plot([], [], color=BLUE, label=f"感想が短い店（{q25:.1f}語以下）")
    ax.plot([], [], color=LIGHT, label="そのほか")
    fig.legend(fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=3, frameon=False)
    ax.set_title("架空の20店の順位：本当の満足と5つの数え方（1回分）", fontsize=12)
    save(fig, "a961_shop_ranks.png", SRC, y=-0.07)

    # 図2：本当の満足との順位相関（店）と、上位5店の当たり（100回の平均）
    fig, axs = plt.subplots(1, 2, figsize=(10.2, 3.9))
    cols = [GRAY, LIGHT, BLUE, GREEN, ORANGE]
    yy = np.arange(len(METHODS))[::-1]
    v = [rep[k]["shop_spearman_true"] for k in METHODS]
    axs[0].barh(yy, v, color=cols)
    for a, b in zip(yy, v):
        axs[0].text(b + 0.01, a, f"{b:.3f}", va="center", fontsize=9.5)
    axs[0].set_yticks(yy); axs[0].set_yticklabels([MLABEL[k] for k in METHODS], fontsize=9)
    axs[0].set_xlim(0, 1.12); axs[0].set_xlabel("店の点と本当の満足の順位相関")
    v = [rep[k]["top5_hit"] for k in METHODS]
    axs[1].barh(yy, v, color=cols)
    for a, b in zip(yy, v):
        axs[1].text(b + 0.05, a, f"{b:.2f}店", va="center", fontsize=9.5)
    axs[1].set_yticks(yy); axs[1].set_yticklabels([])
    axs[1].set_xlim(0, 5.6); axs[1].set_xlabel("上位5店のうち本当の上位5店に入っていた数")
    fig.suptitle("数え方ごとの当たり（基本の置き方、100回の平均）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a961_accuracy.png", SRC)

    # 図3：置き方を変えた確かめ（「ない」の割合と店の点の当たり）
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 4.1), sharey=True)
    for ax, sls in zip(axs, [0.0, 0.5]):
        g = gdf[(gdf.shop_len_sd == sls) & (gdf.gamma_len_by_feeling == 0.3)]
        for k, c in zip(METHODS, cols):
            ax.plot(g.neg_rate * 100, g[f"{k}_shop_rho"], "o-", color=c, lw=1.8, label=MLABEL[k])
        ax.set_xticks([0, 15, 30]); ax.set_xlabel("「語＋ない」で書く割合（%）")
        ax.set_title("店ごとの感想の長さ：" + ("どの店も同じ" if sls == 0 else "店ごとに違う（基本）"), fontsize=11)
        ax.set_ylim(0.75, 0.97)
    axs[0].set_ylabel("店の点と本当の満足の順位相関")
    axs[0].legend(fontsize=8, loc="lower left")
    fig.suptitle("置き方を変えた確かめ（不満な人ほど長く書くと置いたとき、各100回の平均）", fontsize=12)
    fig.tight_layout()
    save(fig, "a961_robustness.png", SRC)
    print(f"done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
