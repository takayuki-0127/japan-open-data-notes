"""1229 決まった検索語の一覧で調整を重ねると、新しい検索語での良さはどれだけ下がるのか？（架空のデータ）

作成者が置いた架空の社内の文書の集まりと検索語。
  検索語は2つの型：「名前で探す語」30%・「中身で探す語」70%（新しい検索語はこの割合で来る）。
  1語ごとに候補の文書40件。文書ごとに4つの手がかり（題名に合う度合い・本文に合う度合い・新しさ・よく読まれる度合い）を
  平均0・標準偏差1で置く。正しさの元＝型ごとの重み・手がかり＋ゆらぎ（基本は標準偏差1）で、元の大きい10件を本当に正しい文書とする。
    名前で探す語の重み (2, 0.5, 0, 0.5)、中身で探す語の重み (0.5, 2, 0.5, 0)
  検索の点＝設定の重み・手がかり。設定は、足して1になる4つの重みをでたらめに400通り作る（全員同じ400通り）。
  物差し：上位10件の正しい割合。
調整：決まった検索語の一覧（基本50語、型の割合は新しい検索語と同じ30%）で、400通りをでたらめな順に試し、
      K 通り目までで一覧の良さがいちばん高い設定を選ぶ（K＝1・5・20・50・100・200・400）。
  一覧の良さ（調整に使った一覧での値）と、新しい検索語での良さ（型ごとに2,000語ずつの別の検索語で数え、30%・70%で合わせた値）を比べる。
  別の確かめ用の一覧（調整に使っていない同じ語数）での良さも数える。
(1) 基本を300回
(2) 確かめ：一覧の語数20・50・200 × ゆらぎ0.5・1・2 × 一覧の型の割合（新しい検索語と同じ30%／名前で探す語に偏った70%）＝18通り（各100回）
語は、型ごとに2,000語ずつ作った「一覧用の語の集まり」から重ならないように引く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1229
SRC = "架空の社内の文書と検索語（作成者が置いた手がかり・型ごとの重み・ゆらぎからの乱数、seed 1229）"
ND, NREL, NF, NCONF = 40, 10, 4, 400
W = {"name": np.array([2.0, 0.5, 0.0, 0.5]), "content": np.array([0.5, 2.0, 0.5, 0.0])}
SHARE_NAME = 0.3
POOL_LIST, POOL_NEW = 2000, 2000
KS = [1, 5, 20, 50, 100, 200, 400]
BASE = dict(n=50, noise=1.0, skew=0.3)
R_MAIN, R_GRID = 300, 100
FEAT = ["題名に合う度合い", "本文に合う度合い", "新しさ", "よく読まれる度合い"]
T0 = time.time()


def r(x, d=2):
    return round(float(x), d)


def p10_matrix(rng, typ, nq, noise, conf):
    """nq 語の、設定ごとの上位10件の正しい割合（nq×NCONF）"""
    out = np.empty((nq, NCONF))
    for s in range(0, nq, 250):
        m = min(250, nq - s)
        f = rng.normal(size=(m, ND, NF))
        latent = f @ W[typ] + noise * rng.normal(size=(m, ND))
        thr = np.partition(latent, ND - NREL, axis=1)[:, ND - NREL][:, None]
        rel = latent >= thr
        sc = np.einsum("mdf,cf->mcd", f, conf)
        t10 = np.partition(sc, ND - 10, axis=2)[:, :, ND - 10][:, :, None]
        out[s:s + m] = ((sc >= t10) & rel[:, None, :]).sum(axis=2) / 10
    return out


def build(rng, conf, noise):
    lp = {t: p10_matrix(rng, t, POOL_LIST, noise, conf) for t in W}
    newv = SHARE_NAME * p10_matrix(rng, "name", POOL_NEW, noise, conf).mean(0) + \
        (1 - SHARE_NAME) * p10_matrix(rng, "content", POOL_NEW, noise, conf).mean(0)
    return lp, newv


def draw(rng, lp, n, skew):
    na = rng.binomial(2 * n, skew)
    ia = rng.choice(POOL_LIST, na, replace=False)
    ib = rng.choice(POOL_LIST, 2 * n - na, replace=False)
    rows = np.vstack([lp["name"][ia], lp["content"][ib]])
    rows = rows[rng.permutation(2 * n)]
    return rows[:n].mean(0), rows[n:].mean(0)   # 調整に使う一覧・確かめ用の一覧


def one_rep(rng, lp, newv, n, skew):
    lst, chk = draw(rng, lp, n, skew)
    order = rng.permutation(NCONF)
    res = {}
    for K in KS:
        cand = order[:K]
        b = cand[np.argmax(lst[cand])]
        res[K] = (lst[b], newv[b], chk[b])
    return res


def main():
    rng = np.random.default_rng(SEED)
    conf = rng.dirichlet(np.ones(NF), NCONF)
    pools = {}
    for noise in (0.5, 1.0, 2.0):
        pools[noise] = build(rng, conf, noise)
    lp, newv = pools[BASE["noise"]]
    best_new = newv.max()
    pd.DataFrame(np.round(conf, 6), columns=[f"w_{i+1}" for i in range(NF)]).assign(
        new_queries_top10_correct=np.round(newv, 6)).to_csv(DATA / "configs_400_base.csv", index_label="config_id")

    reps = [one_rep(rng, lp, newv, BASE["n"], BASE["skew"]) for _ in range(R_MAIN)]
    rows = []
    for K in KS:
        a = np.array([rp[K] for rp in reps])
        rows.append({"tries": K, "list_pct": r(100 * a[:, 0].mean()), "new_pct": r(100 * a[:, 1].mean()),
                     "check_list_pct": r(100 * a[:, 2].mean()),
                     "list_minus_new_pt": r(100 * (a[:, 0] - a[:, 1]).mean()),
                     "check_minus_new_pt": r(100 * (a[:, 2] - a[:, 1]).mean()),
                     "new_below_best_pt": r(100 * (best_new - a[:, 1]).mean()),
                     "reps_list_above_new_pct": r(100 * (a[:, 0] > a[:, 1]).mean()),
                     "list_minus_new_p10_pt": r(100 * np.quantile(a[:, 0] - a[:, 1], 0.1)),
                     "list_minus_new_p90_pt": r(100 * np.quantile(a[:, 0] - a[:, 1], 0.9))})
    bt = pd.DataFrame(rows)
    bt.to_csv(RES / "base_by_tries.csv", index=False)

    grid = []
    for n in (20, 50, 200):
        for noise in (0.5, 1.0, 2.0):
            for skew in (0.3, 0.7):
                lpg, nvg = pools[noise]
                rr = [one_rep(rng, lpg, nvg, n, skew) for _ in range(R_GRID)]
                row = {"list_queries": n, "noise": noise, "list_name_share": skew, "best_new_pct": r(100 * nvg.max()),
                       "median_config_new_pct": r(100 * np.median(nvg))}
                for K in (1, 20, 400):
                    a = np.array([x[K] for x in rr])
                    row[f"list_pct_K{K}"] = r(100 * a[:, 0].mean())
                    row[f"new_pct_K{K}"] = r(100 * a[:, 1].mean())
                    row[f"gap_pt_K{K}"] = r(100 * (a[:, 0] - a[:, 1]).mean())
                    row[f"check_gap_pt_K{K}"] = r(100 * (a[:, 2] - a[:, 1]).mean())
                    row[f"new_below_best_pt_K{K}"] = r(100 * (nvg.max() - a[:, 1]).mean())
                row["new_change_K20_to_K400_pt"] = r(row["new_pct_K400"] - row["new_pct_K20"])
                grid.append(row)
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    B = lambda K: bt[bt.tries == K].iloc[0]
    headline = {"best_config_new_pct": r(100 * best_new), "median_config_new_pct": r(100 * np.median(newv)),
                "best_config_weights": [r(x, 3) for x in conf[np.argmax(newv)]]}
    for K in KS:
        for c in ("list_pct", "new_pct", "check_list_pct", "list_minus_new_pt", "check_minus_new_pt", "new_below_best_pt", "reps_list_above_new_pct"):
            headline[f"K{K}_{c}"] = B(K)[c]
    headline["K400_gap_p10_pt"] = B(400).list_minus_new_p10_pt
    headline["K400_gap_p90_pt"] = B(400).list_minus_new_p90_pt
    rob = {"settings": len(g)}
    for K in (1, 20, 400):
        rob[f"gap_K{K}_range"] = [g[f"gap_pt_K{K}"].min(), g[f"gap_pt_K{K}"].max()]
        rob[f"check_gap_K{K}_range"] = [g[f"check_gap_pt_K{K}"].min(), g[f"check_gap_pt_K{K}"].max()]
    for n in (20, 50, 200):
        gg = g[g.list_queries == n]
        rob[f"gap_K400_n{n}"] = [gg.gap_pt_K400.min(), gg.gap_pt_K400.max()]
    for n in (20, 50, 200):
        for sk in (0.3, 0.7):
            gg = g[(g.list_queries == n) & (g.list_name_share == sk)]
            rob[f"gap_K400_n{n}_skew{sk}"] = [gg.gap_pt_K400.min(), gg.gap_pt_K400.max()]
    for sk in (0.3, 0.7):
        gg = g[g.list_name_share == sk]
        rob[f"gap_K400_skew{sk}"] = [gg.gap_pt_K400.min(), gg.gap_pt_K400.max()]
        rob[f"check_gap_K400_skew{sk}"] = [gg.check_gap_pt_K400.min(), gg.check_gap_pt_K400.max()]
        rob[f"new_below_best_K400_skew{sk}"] = [gg.new_below_best_pt_K400.min(), gg.new_below_best_pt_K400.max()]
        rob[f"new_change_K20_to_K400_skew{sk}"] = [gg.new_change_K20_to_K400_pt.min(), gg.new_change_K20_to_K400_pt.max()]
    pv = g.pivot_table(index=["list_queries", "noise"], columns="list_name_share", values="new_pct_K400")
    dd = (pv[0.7] - pv[0.3]).round(2)
    rob["new_K400_skew_minus_rep_range_pt"] = [float(dd.min()), float(dd.max())]
    rob["settings_new_dropped_K20_to_K400"] = int((g.new_change_K20_to_K400_pt < 0).sum())
    js = {"settings": {"docs_per_query": ND, "correct_per_query": NREL, "features": FEAT, "weights_name": W["name"].tolist(),
                       "weights_content": W["content"].tolist(), "new_name_share": SHARE_NAME, "configs": NCONF,
                       "list_pool_per_type": POOL_LIST, "new_queries_per_type": POOL_NEW, "tries": KS, **BASE,
                       "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
          "headline": headline, "robust": rob}
    (RES / "a1229_main.json").write_text(json.dumps(js, ensure_ascii=False, indent=1))

    # 図1：試した数ごとの一覧の良さと新しい検索語での良さ
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    x = np.arange(len(KS))
    ax.plot(x, bt.list_pct, "-o", color=ORANGE, label="調整に使った一覧（50語）での良さ")
    ax.plot(x, bt.check_list_pct, "--s", color=GRAY, label="調整に使っていない一覧（50語）での良さ")
    ax.plot(x, bt.new_pct, "-o", color=BLUE, label="新しい検索語（4,000語）での良さ")
    ax.axhline(100 * best_new, color=INK, lw=0.8, ls=":", label="400通りの中で新しい検索語にいちばん良い設定")
    for xi, a, b in zip(x, bt.list_pct, bt.new_pct):
        # 線と重ならないよう、上の値は点の左上、下の値は点の右下に置く
        hi_v, hi_c, lo_v, lo_c = (a, ORANGE, b, BLUE) if a >= b else (b, BLUE, a, ORANGE)
        ax.annotate(f"{hi_v:.2f}", (xi, hi_v), xytext=(-5, 5), textcoords="offset points", ha="right", va="bottom", fontsize=8.5, color=hi_c)
        ax.annotate(f"{lo_v:.2f}", (xi, lo_v), xytext=(5, -5), textcoords="offset points", ha="left", va="top", fontsize=8.5, color=lo_c)
    ax.set_xlim(-0.7, len(KS) - 0.5)
    ax.set_xticks(x, [str(k) for k in KS])
    ax.set_xlabel("試した設定の数（でたらめな順に試し、一覧でいちばん良いものを選ぶ）")
    ax.set_ylabel("上位10件の正しい割合（%）")
    lo = min(bt.new_pct.min(), bt.check_list_pct.min()) - 4
    ax.set_ylim(lo, bt.list_pct.max() + 4)
    ax.set_title("試すほど、一覧での良さは新しい検索語での良さより上に離れた（300回の平均、縦軸は途中から）", fontsize=10.5)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    save(fig, "a1229_by_tries.png", SRC)

    # 図2：400通り試したときの、一覧の良さ−新しい検索語での良さ（18通り）
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    lab = []
    for i, n in enumerate((20, 50, 200)):
        for j, sk in enumerate((0.3, 0.7)):
            gg = g[(g.list_queries == n) & (g.list_name_share == sk)]
            xx = i + (j - 0.5) * 0.32 + np.array([-0.06, 0, 0.06])
            ax.bar(xx, gg.gap_pt_K400.values, 0.055, color=[BLUE, ORANGE][j],
                   label=["一覧の名前で探す語30%（新しい語と同じ）", "一覧の名前で探す語70%（偏り）"][j] if i == 0 else None)
    ax.set_xticks(range(3), ["一覧20語", "一覧50語", "一覧200語"])
    ax.set_ylabel("一覧での良さ−新しい検索語での良さ（ポイント）")
    ax.set_ylim(0, g.gap_pt_K400.max() * 1.2)
    ax.set_title("400通り試したときの見かけの上ずれ（18通り、各100回。棒はゆらぎ0.5・1・2の順）", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1229_gap_grid.png", SRC)

    # 図3：新しい検索語での良さが、いちばん良い設定よりどれだけ下か（K=20 と K=400）
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    for i, n in enumerate((20, 50, 200)):
        for j, sk in enumerate((0.3, 0.7)):
            gg = g[(g.list_queries == n) & (g.list_name_share == sk)]
            for k, K in enumerate((20, 400)):
                xx = i + (j - 0.5) * 0.4 + (k - 0.5) * 0.16 + np.array([-0.04, 0, 0.04])
                ax.bar(xx, gg[f"new_below_best_pt_K{K}"].values, 0.035, color=[[LIGHT_BLUE, BLUE], [LIGHT_OR, ORANGE]][j][k],
                       label=(f"{['30%', '70%'][j]}の一覧・{K}通り試す") if i == 0 else None)
    ax.set_xticks(range(3), ["一覧20語", "一覧50語", "一覧200語"])
    ax.set_ylabel("いちばん良い設定との差（ポイント）")
    ax.set_ylim(0, g[["new_below_best_pt_K20", "new_below_best_pt_K400"]].values.max() * 1.3)
    ax.set_title("選んだ設定の新しい検索語での良さは、いちばん良い設定より何ポイント下か\n（18通り、各100回。棒はゆらぎ0.5・1・2の順）", fontsize=11)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=2)
    save(fig, "a1229_below_best.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(rob, ensure_ascii=False), round(time.time() - T0, 1), "s")


LIGHT_BLUE, LIGHT_OR = "#a9c9ef", "#f5b89c"

if __name__ == "__main__":
    main()
