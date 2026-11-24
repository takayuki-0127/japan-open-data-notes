"""1222 まだ判定していない文書を「正しくない」と見なすと、新しい検索のやり方はどれだけ不利になるのか？（架空のデータ）

架空の社内の文書3,000件と、架空の検索語50語。語ごとの正しい文書を作成者が決め、正しい文書は
「検索語と同じ言葉を含む文書」と「言いかえた文書」の2種類に分ける。
前からある2つのやり方（旧1・旧2）は同じ言葉を含む文書に強く、言いかえた文書に弱い。新しいやり方はどちらにも同じ強さ。
正しいかどうかの判定は、旧1・旧2の上位20件を合わせた文書にだけ付ける（作成者はすべての文書の正しさを知っている）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1222
SRC = "架空の社内の文書と検索語（作成者が置いた正しさと点数からの乱数、seed 1222）"
DOCS, Q, K = 3000, 50, 10
BASE = dict(depth=20, para=0.4, rho=0.5, old_same=2.5, old_para=0.5, new=2.4, pool_new=False)
NAMES = {"O1": "旧1", "O2": "旧2", "N": "新"}


def topk(s, k):
    return np.argpartition(-s, k - 1, axis=1)[:, :k]


def one_set(rng, depth=20, para=0.4, rho=0.5, old_same=2.5, old_para=0.5, new=2.4, pool_new=False):
    n = np.round(np.exp(rng.uniform(np.log(5), np.log(60), Q))).astype(int)
    rel = np.arange(DOCS)[None, :] < n[:, None]
    is_para = rel & (rng.random((Q, DOCS)) < para)
    same = rel & ~is_para
    e0 = rng.standard_normal((Q, DOCS))  # 旧1・旧2・新に共通する点数の揺れ
    so = same * old_same + is_para * old_para
    s = {"O1": so + np.sqrt(.5) * e0 + np.sqrt(.5) * rng.standard_normal((Q, DOCS)),
         "O2": so + np.sqrt(.5) * e0 + np.sqrt(.5) * rng.standard_normal((Q, DOCS))}
    s["N"] = rel * new + rho * e0 + np.sqrt(1 - rho ** 2) * rng.standard_normal((Q, DOCS))
    judged = np.zeros((Q, DOCS), bool)
    for m in (["O1", "O2"] + (["N"] if pool_new else [])):
        np.put_along_axis(judged, topk(s[m], depth), True, 1)
    out, per_q = {}, {}
    for m in ["O1", "O2", "N"]:
        t = topk(s[m], K)
        r = np.take_along_axis(rel, t, 1)
        j = np.take_along_axis(judged, t, 1)
        pa = np.take_along_axis(is_para, t, 1)
        sj = np.where(judged, s[m], -np.inf)
        rj = np.take_along_axis(rel, topk(sj, K), 1)
        out[m] = {"true": r.mean(), "unjudged_as_wrong": (r & j).mean(), "judged_only": rj.mean(),
                  "unjudged_share": 1 - j.mean(), "rel_unjudged": (r & ~j).mean(), "wrong_unjudged": (~r & ~j).mean(),
                  "rel_judged": (r & j).mean(), "wrong_judged": (~r & j).mean(),
                  "para_share_of_rel_unjudged": (r & ~j & pa).sum() / max((r & ~j).sum(), 1)}
        per_q[m] = (r.sum(1), (r & j).sum(1), (~j).sum(1))
    return n, is_para.sum(1), out, per_q, int(judged.sum())


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分（data に置く）
    n, npara, o1, pq, nj = one_set(rng)
    df = pd.DataFrame({"query_id": np.arange(1, Q + 1), "n_correct": n, "n_correct_reworded": npara})
    for m in ["O1", "O2", "N"]:
        df[f"{m}_top10_correct"] = pq[m][0]
        df[f"{m}_top10_correct_judged"] = pq[m][1]
        df[f"{m}_top10_unjudged"] = pq[m][2]
    df.to_csv(DATA / "queries_one_set.csv", index=False)
    one = {"judged_docs_per_query": round(nj / Q, 2),
           "N_true": round(float(o1["N"]["true"]), 4), "N_unjudged_as_wrong": round(float(o1["N"]["unjudged_as_wrong"]), 4),
           "O1_true": round(float(o1["O1"]["true"]), 4)}

    # 2) 基本の置き方で200回、判定に新の上位20件も入れた場合で200回
    def many(reps, seed_off, **kw):
        rows = []
        for r in range(reps):
            _, _, o, _, _ = one_set(np.random.default_rng([SEED, seed_off, r]), **{**BASE, **kw})
            rows.append({"rep": r, **{f"{m}_{k}": v for m in o for k, v in o[m].items()}})
        return pd.DataFrame(rows)

    base = many(200, 1)
    base.to_csv(RES / "reps_base.csv", index=False, float_format="%.6f")
    withn = many(200, 2, pool_new=True)
    keys = ["true", "unjudged_as_wrong", "judged_only", "unjudged_share", "rel_unjudged", "wrong_unjudged",
            "rel_judged", "wrong_judged", "para_share_of_rel_unjudged"]
    mean = {m: {k: round(float(base[f"{m}_{k}"].mean()), 4) for k in keys} for m in ["O1", "O2", "N"]}
    head = {
        "mean_200": mean,
        "N_minus_O1_true_pt": round(float((base.N_true - base.O1_true).mean()) * 100, 2),
        "N_minus_O1_measured_pt": round(float((base.N_unjudged_as_wrong - base.O1_unjudged_as_wrong).mean()) * 100, 2),
        "N_minus_O1_judged_only_pt": round(float((base.N_judged_only - base.O1_judged_only).mean()) * 100, 2),
        "N_judged_only_minus_true_pt": round(float((base.N_judged_only - base.N_true).mean()) * 100, 2),
        "N_measured_over_true": round(float(base.N_unjudged_as_wrong.mean() / base.N_true.mean()), 4),
        "share_true_N_better": round(float((base.N_true > base.O1_true).mean()), 4),
        "share_measured_N_better": round(float((base.N_unjudged_as_wrong > base.O1_unjudged_as_wrong).mean()), 4),
        "share_order_reversed": round(float(((base.N_true > base.O1_true) &
                                             (base.N_unjudged_as_wrong < base.O1_unjudged_as_wrong)).mean()), 4),
        "O_measured_equals_true": bool((base.O1_true == base.O1_unjudged_as_wrong).all() and
                                       (base.O2_true == base.O2_unjudged_as_wrong).all()),
        "pool_with_new": {"N_true": round(float(withn.N_true.mean()), 4),
                          "N_unjudged_as_wrong": round(float(withn.N_unjudged_as_wrong.mean()), 4),
                          "N_equals_true_all": bool((withn.N_true == withn.N_unjudged_as_wrong).all())},
    }

    # 3) 確かめ：判定する深さ×言いかえた文書の割合×新と旧の点数の揺れの重なり×新の強さ（各10回）
    grid = []
    for depth in [10, 20, 50, 100]:
        for para in [0.2, 0.4, 0.6]:
            for rho in [0.0, 0.5, 0.75]:
                for nw in [2.0, 2.4, 2.8]:
                    g = many(10, 1000 + depth * 1000 + int(para * 10) * 100 + int(rho * 4) * 10 + int(nw * 10),
                             depth=depth, para=para, rho=rho, new=nw)
                    grid.append({"depth": depth, "para": para, "rho": rho, "new": nw,
                                 "N_true": g.N_true.mean(), "N_measured": g.N_unjudged_as_wrong.mean(),
                                 "N_judged_only": g.N_judged_only.mean(), "O1_true": g.O1_true.mean(),
                                 "N_unjudged_share": g.N_unjudged_share.mean(),
                                 "N_rel_unjudged": g.N_rel_unjudged.mean(), "N_rel_judged": g.N_rel_judged.mean(),
                                 "N_wrong_judged": g.N_wrong_judged.mean(), "N_wrong_unjudged": g.N_wrong_unjudged.mean(),
                                 "ratio": g.N_unjudged_as_wrong.mean() / g.N_true.mean(),
                                 "ratio_judged_only": g.N_judged_only.mean() / g.N_true.mean(),
                                 "reversed": float(((g.N_true > g.O1_true) & (g.N_unjudged_as_wrong < g.O1_unjudged_as_wrong)).mean()),
                                 "N_true_better_avg": bool(g.N_true.mean() > g.O1_true.mean()),
                                 "N_measured_better_avg": bool(g.N_unjudged_as_wrong.mean() > g.O1_unjudged_as_wrong.mean()),
                                 "judged_only_N_better_avg": bool(g.N_judged_only.mean() > g.O1_true.mean())})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False, float_format="%.4f")
    rv = gr[gr.N_true_better_avg & ~gr.N_measured_better_avg]
    robust = {"settings": int(len(gr)),
              "N_true_better_settings": int(gr.N_true_better_avg.sum()),
              "avg_order_reversed_settings": int(len(rv)),
              "avg_order_reversed_by_depth": {str(d): int((rv.depth == d).sum()) for d in [10, 20, 50, 100]},
              "ratio_range": [round(float(gr.ratio.min()), 4), round(float(gr.ratio.max()), 4)],
              "ratio_by_depth": {str(d): [round(float(gr[gr.depth == d].ratio.min()), 4), round(float(gr[gr.depth == d].ratio.max()), 4)]
                                 for d in [10, 20, 50, 100]},
              "ratio_by_rho": {str(r): [round(float(gr[gr.rho == r].ratio.min()), 4), round(float(gr[gr.rho == r].ratio.max()), 4)]
                               for r in [0.0, 0.5, 0.75]},
              "ratio_by_para": {str(r): [round(float(gr[gr.para == r].ratio.min()), 4), round(float(gr[gr.para == r].ratio.max()), 4)]
                                for r in [0.2, 0.4, 0.6]},
              "N_true_minus_O1_pt_range": [round(float((gr.N_true - gr.O1_true).min()) * 100, 2), round(float((gr.N_true - gr.O1_true).max()) * 100, 2)],
              "avg_order_reversed_by_new": {str(w): [int(((rv.new == w)).sum()), int((gr.N_true_better_avg & (gr.new == w)).sum())] for w in [2.0, 2.4, 2.8]},
              "not_reversed_settings": {"count": int((gr.N_true_better_avg & gr.N_measured_better_avg).sum()),
                                        "depths": sorted(set(int(x) for x in gr[gr.N_true_better_avg & gr.N_measured_better_avg].depth)),
                                        "by_new": {str(w): int((gr.N_true_better_avg & gr.N_measured_better_avg & (gr.new == w)).sum()) for w in [2.0, 2.4, 2.8]}},
              "judged_only_wrong_order_settings": int((gr.N_true_better_avg != gr.judged_only_N_better_avg).sum()),
              "judged_only_wrong_order_N_truly_worse": int((~gr.N_true_better_avg & gr.judged_only_N_better_avg).sum()),
              "judged_only_wrong_order_new_values": sorted(set(float(x) for x in gr[gr.N_true_better_avg != gr.judged_only_N_better_avg].new)),
              "N_true_better_by_depth": {str(d): int((gr.N_true_better_avg & (gr.depth == d)).sum()) for d in [10, 20, 50, 100]},
              "N_true_better_by_new": {str(w): int((gr.N_true_better_avg & (gr.new == w)).sum()) for w in [2.0, 2.4, 2.8]},
              "ratio_judged_only_range": [round(float(gr.ratio_judged_only.min()), 4), round(float(gr.ratio_judged_only.max()), 4)],
              "ratio_judged_only_over1_settings": int((gr.ratio_judged_only > 1).sum())}
    base_cols = (gr.para == 0.4) & (gr.rho == 0.5) & (gr.new == 2.4)
    by_depth = gr[base_cols][["depth", "N_true", "N_measured", "N_judged_only", "N_rel_judged", "N_rel_unjudged",
                              "N_wrong_judged", "N_wrong_unjudged", "ratio"]].round(4)
    robust["by_depth_base"] = by_depth.to_dict("records")

    out = {"headline": head, "one_set": one, "robust": robust,
           "setup": {"docs": DOCS, "queries": Q, "top": K, **BASE, "reps": 200, "grid_reps": 10}}
    json.dump(out, open(RES / "a1222_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：本当の値と、未判定を正しくないと見なした値
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(3)
    tv = [mean[m]["true"] * 100 for m in ["O1", "O2", "N"]]
    mv = [mean[m]["unjudged_as_wrong"] * 100 for m in ["O1", "O2", "N"]]
    jv = [mean[m]["judged_only"] * 100 for m in ["O1", "O2", "N"]]
    for off, v, c, lab in [(-0.27, tv, INK, "本当の値（すべての文書の正しさで数える）"),
                           (0, mv, ORANGE, "まだ判定していない文書を正しくないと見なす"),
                           (0.27, jv, LIGHT, "判定済みの文書だけで並べ直す")]:
        ax.bar(x + off, v, 0.27, color=c, label=lab)
        for i, vv in enumerate(v):
            ax.text(i + off, vv + 1, f"{vv:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(["旧1", "旧2", "新"]); ax.set_ylim(0, 80)
    ax.set_ylabel("上位10件の正しい割合（%、200回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("判定を旧1・旧2の上位20件にだけ付けると、新は低く数えられる（置いた例）")
    save(fig, "a1222_true_vs_measured.png", SRC)

    # 図2：判定する深さごとの、新の上位10件の中身
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    bd = by_depth.reset_index(drop=True)
    parts = [("N_rel_judged", BLUE, "正しい・判定済み"), ("N_rel_unjudged", LIGHT, "正しい・未判定"),
             ("N_wrong_judged", GRAY, "正しくない・判定済み"), ("N_wrong_unjudged", "#dddcd6", "正しくない・未判定")]
    bottom = np.zeros(len(bd))
    for col, c, lab in parts:
        v = bd[col].values * 100
        ax.bar(np.arange(len(bd)), v, 0.6, bottom=bottom, color=c, label=lab)
        for i, vv in enumerate(v):
            if vv > 4:
                ax.text(i, bottom[i] + vv / 2, f"{vv:.2f}", ha="center", va="center", fontsize=8)
        bottom += v
    ax.set_xticks(np.arange(len(bd))); ax.set_xticklabels([f"上位{d}件" for d in bd.depth])
    ax.set_xlabel("旧1・旧2の上位何件に判定を付けるか"); ax.set_ylabel("新の上位10件の内訳（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="center left", bbox_to_anchor=(1.0, 0.5))
    ax.set_title("判定を深くしても、新の上位10件には未判定の正しい文書が残る（各10回）")
    save(fig, "a1222_by_depth.png", SRC)

    # 図3：確かめ。見かけ÷本当（判定する深さごと、108通り）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    cols = {0.2: LIGHT, 0.4: BLUE, 0.6: INK}
    jit = np.random.default_rng(SEED + 9).uniform(-0.18, 0.18, len(gr))
    xpos = gr.depth.map({10: 0, 20: 1, 50: 2, 100: 3}).values + jit
    for para in [0.2, 0.4, 0.6]:
        sel = (gr.para == para).values
        ax.scatter(xpos[sel], gr.ratio.values[sel] * 100, s=14, color=cols[para], lw=0, label=f"言いかえた文書{int(para*100)}%")
    ax.axhline(100, color=GRAY, lw=1, ls="--")
    ax.set_xticks(np.arange(4)); ax.set_xticklabels([f"上位{d}件" for d in [10, 20, 50, 100]])
    ax.set_xlabel("旧1・旧2の上位何件に判定を付けるか（点は横に少しずらした）")
    ax.set_ylabel("新の見かけ÷本当の値（%）"); ax.set_ylim(0, 110)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("108通りすべてで、新は本当の値より低く数えられた（各10回）")
    save(fig, "a1222_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
