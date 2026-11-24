"""1230 同じ内容の文書が何件もあると、上位10件の正しい割合は高く出ても、役に立つ文書はいくつなのか？（架空のデータ）

架空の社内の文書の集まり。検索語ごとに中身200件（うち正しい中身 R 件）を置き、
中身ごとに写し（同じ内容の文書）の件数を置く。検索の点は中身の点＋写しごとの小さな揺れ。
並べ方 A：文書をそのまま点の順に並べる。並べ方 B：同じ中身の写しは点のいちばん高い1件だけ残す。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1230
SRC = "架空の社内の文書と検索語（作成者が乱数で作成、seed 1230）"
N_CONTENT = 200   # 検索語ごとの候補の中身の数
K = 10
MU = 2.0          # 正しい中身の点の上げ幅
COPY_SD = 0.1     # 写しどうしの点の揺れ
MAX_COPY = 8
COPY_W = 0.6 ** np.arange(MAX_COPY - 1)   # 写しの件数 2..8 の重み（1件増えるごとに0.6倍）
COPY_P = COPY_W / COPY_W.sum()


def one_query(rng, R, d, f):
    rel = np.zeros(N_CONTENT, int)
    rel[:R] = 1
    pc = np.where(rel == 1, min(1.0, d * f), d)          # 写しがある確率
    has = rng.random(N_CONTENT) < pc
    n = np.ones(N_CONTENT, int)
    n[has] = rng.choice(np.arange(2, MAX_COPY + 1), size=has.sum(), p=COPY_P)
    s = MU * rel + rng.normal(0, 1, N_CONTENT)
    cid = np.repeat(np.arange(N_CONTENT), n)
    sc = s[cid] + rng.normal(0, COPY_SD, cid.size)
    return rel, n, cid, sc


def metrics(rel, n, cid, sc):
    order = np.argsort(-sc, kind="stable")
    topA = cid[order[:K]]
    # B：中身ごとに最初に出た1件だけ残す
    _, first = np.unique(cid[order], return_index=True)
    keep = order[np.sort(first)]
    topB = cid[keep[:K]]
    pA = rel[topA].mean()
    dA = len(set(topA[rel[topA] == 1]))
    pB = rel[topB].mean()
    dB = len(set(topB[rel[topB] == 1]))
    copiesA = K - len(set(topA))           # 上位10件のうち、前に出た中身の写しの件数
    relcopyA = int((rel[topA] == 1).sum()) - dA
    return pA, dA, pB, dB, copiesA, relcopyA


def run(rng, R, d, f, nq):
    out = np.array([metrics(*one_query(rng, R, d, f)) for _ in range(nq)], float)
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    R0, D0, F0, NQ, REP = 6, 0.25, 2.0, 200, 20

    # 例：1回分（200語）の文書を保存
    ex = []
    rng_ex = np.random.default_rng(SEED + 1)
    for q in range(NQ):
        rel, n, cid, sc = one_query(rng_ex, R0, D0, F0)
        order = np.argsort(-sc, kind="stable")
        rankA = np.empty(cid.size, int); rankA[order] = np.arange(1, cid.size + 1)
        _, first = np.unique(cid[order], return_index=True)
        keep = order[np.sort(first)]
        rankB = np.zeros(cid.size, int); rankB[keep] = np.arange(1, keep.size + 1)
        top = rankA <= 20
        ex.append(pd.DataFrame({"query": q + 1, "content": cid[top] + 1, "correct": rel[cid[top]],
                                "copies_of_content": n[cid[top]], "score": sc[top].round(4),
                                "rank_all": rankA[top], "rank_one_per_content": rankB[top]}))
    ex = pd.concat(ex).sort_values(["query", "rank_all"])
    ex.to_csv(DATA / "query_top20_example.csv", index=False)
    e1 = ex[ex.rank_all <= 10]
    ex_sum = {"queries": NQ,
              "p10_all": round(float(e1.correct.mean()) * 100, 2),
              "distinct_correct_all": round(float(e1[e1.correct == 1].groupby("query").content.nunique()
                                                  .reindex(range(1, NQ + 1), fill_value=0).mean()), 4)}

    # 基本：200語×20回
    base = np.concatenate([run(np.random.default_rng(SEED * 100 + r), R0, D0, F0, NQ) for r in range(REP)])
    pA, dA, pB, dB, cA, rcA = base.T
    # 写しなし（どの中身も1件）
    none = np.concatenate([run(np.random.default_rng(SEED * 100 + r), R0, 0.0, 1.0, NQ) for r in range(REP)])
    headline = {
        "p10_all": round(pA.mean() * 100, 2), "p10_one_per_content": round(pB.mean() * 100, 2),
        "distinct_all": round(dA.mean(), 3), "distinct_one_per_content": round(dB.mean(), 3),
        "correct_slots_all": round(pA.mean() * K, 3),
        "copy_slots_all": round(cA.mean(), 3), "correct_copy_slots_all": round(rcA.mean(), 3),
        "useful_per_correct_slot_all": round(dA.mean() / (pA.mean() * K), 4),
        "useful_share_of_correct_all_pct": round(dA.mean() / (pA.mean() * K) * 100, 2),
        "share_q_pA_gt_pB_and_dB_gt_dA": round(float(((pA > pB) & (dB > dA)).mean()) * 100, 2),
        "share_q_pA_gt_pB": round(float((pA > pB).mean()) * 100, 2),
        "share_q_dB_lt_dA": round(float((dB < dA).mean()) * 100, 2),
        "share_q_dB_gt_dA": round(float((dB > dA).mean()) * 100, 2),
        "share_q_distinct_le2_all": round(float((dA <= 2).mean()) * 100, 2),
        "share_q_distinct_le2_one_per_content": round(float((dB <= 2).mean()) * 100, 2),
        "no_copies_p10": round(none[:, 0].mean() * 100, 2), "no_copies_distinct": round(none[:, 1].mean(), 3),
        "queries": NQ, "reps": REP,
    }
    # 正しい中身の件数ごとの分布
    dist = pd.DataFrame({"distinct_correct": np.arange(0, K + 1)})
    dist["all_pct"] = [round(float((dA == k).mean()) * 100, 2) for k in dist.distinct_correct]
    dist["one_per_content_pct"] = [round(float((dB == k).mean()) * 100, 2) for k in dist.distinct_correct]
    dist.to_csv(RES / "distinct_dist.csv", index=False)

    # 確かめ：写しの確率 d × 正しい中身の写しやすさ f × 正しい中身の数 R（各200語×10回）
    rows = []
    for R in [3, 6, 10]:
        for d in [0.1, 0.25, 0.4]:
            for f in [1.0, 2.0, 3.0]:
                g = np.concatenate([run(np.random.default_rng(SEED * 1000 + int(R * 100 + d * 100 + f) * 10 + r),
                                        R, d, f, NQ) for r in range(10)])
                rows.append({"correct_contents": R, "copy_prob": d, "correct_copy_factor": f,
                             "p10_all": round(g[:, 0].mean() * 100, 2), "p10_one_per_content": round(g[:, 2].mean() * 100, 2),
                             "distinct_all": round(g[:, 1].mean(), 3), "distinct_one_per_content": round(g[:, 3].mean(), 3),
                             "p10_gap": round((g[:, 0].mean() - g[:, 2].mean()) * 100, 2),
                             "distinct_gap": round(g[:, 3].mean() - g[:, 1].mean(), 3),
                             "useful_per_correct_slot_all": round(g[:, 1].mean() / (g[:, 0].mean() * K), 4)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {
        "settings": len(grid),
        "p10_all_higher_count": int((grid.p10_gap > 0).sum()),
        "distinct_one_higher_count": int((grid.distinct_gap > 0).sum()),
        "both_flip_count": int(((grid.p10_gap > 0) & (grid.distinct_gap > 0)).sum()),
        "p10_gap_min": float(grid.p10_gap.min()), "p10_gap_max": float(grid.p10_gap.max()),
        "distinct_gap_min": float(grid.distinct_gap.min()), "distinct_gap_max": float(grid.distinct_gap.max()),
        "useful_per_slot_min": float(grid.useful_per_correct_slot_all.min()),
        "useful_per_slot_max": float(grid.useful_per_correct_slot_all.max()),
        "useful_share_pct_min": round(float(grid.useful_per_correct_slot_all.min()) * 100, 2),
        "useful_share_pct_max": round(float(grid.useful_per_correct_slot_all.max()) * 100, 2),
        "f1_p10_gap_min": float(grid[grid.correct_copy_factor == 1].p10_gap.min()),
        "f1_p10_gap_max": float(grid[grid.correct_copy_factor == 1].p10_gap.max()),
        "f1_p10_all_higher_count": int((grid[grid.correct_copy_factor == 1].p10_gap > 0).sum()),
        "f1_settings": int((grid.correct_copy_factor == 1).sum()),
    }
    json.dump({"headline": headline, "example_one_run": ex_sum, "robust": robust,
               "setup": {"contents_per_query": N_CONTENT, "correct_contents": R0, "copy_prob": D0,
                         "correct_copy_factor": F0, "score_gap": MU, "copy_score_sd": COPY_SD,
                         "copies_when_copied": "2-8, weight 0.6^(c-2)"}},
              open(RES / "a1230_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：上位10件の中身（10枠の内訳）
    fig, ax = plt.subplots(figsize=(7, 3.8))
    labels = ["A 文書をそのまま並べる", "B 同じ中身は1件だけ残す"]
    dd = [headline["distinct_all"], headline["distinct_one_per_content"]]
    cc = [headline["correct_copy_slots_all"], 0.0]
    wr = [round(K - headline["p10_all"] / 10, 3), round(K - headline["p10_one_per_content"] / 10, 3)]
    y = [1, 0]
    ax.barh(y, dd, color=BLUE, label="役に立つ文書（別々の正しい中身）")
    ax.barh(y, cc, left=dd, color=ORANGE, label="すでに出た正しい中身の写し")
    ax.barh(y, wr, left=np.add(dd, cc), color=GRAY, label="正しくない文書")
    for yi, a, b, c in zip(y, dd, cc, wr):
        ax.text(a / 2, yi, f"{a:.3f}", ha="center", va="center", color="white", fontsize=10)
        if b > 0.3:
            ax.text(a + b / 2, yi, f"{b:.3f}", ha="center", va="center", color="white", fontsize=10)
        ax.text(a + b + c / 2, yi, f"{c:.3f}", ha="center", va="center", color="white", fontsize=10)
    ax.set_yticks(y, labels); ax.set_xlim(0, 10); ax.set_xlabel("上位10件の枠の数（200語×20回の平均）")
    ax.set_title(f"上位10件の正しい割合 A {headline['p10_all']}%・B {headline['p10_one_per_content']}%")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2, fontsize=9, frameon=False)
    save(fig, "a1230_slots.png", SRC, y=-0.30)

    # 図2：別々の正しい中身の件数の分布
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = dist.distinct_correct.values
    ax.bar(x - 0.2, dist.all_pct, 0.4, color=ORANGE, label="A 文書をそのまま並べる")
    ax.bar(x + 0.2, dist.one_per_content_pct, 0.4, color=BLUE, label="B 同じ中身は1件だけ残す")
    ax.set_xticks(x); ax.set_ylim(0, None)
    ax.set_xlabel("上位10件に入った別々の正しい中身の数（正しい中身は1語あたり6件）")
    ax.set_ylabel("検索語の割合（%）")
    ax.set_title("同じ中身を1件にすると、別々の正しい中身が多い語が増えた")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1230_distinct.png", SRC)

    # 図3：置き方27通り
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for f, c in zip([1.0, 2.0, 3.0], [GRAY, BLUE, ORANGE]):
        gg = grid[grid.correct_copy_factor == f]
        for R, mk in zip([3, 6, 10], ["o", "s", "^"]):
            g2 = gg[gg.correct_contents == R]
            axs[0].plot(g2.copy_prob, g2.p10_gap, marker=mk, color=c, lw=1)
            axs[1].plot(g2.copy_prob, g2.distinct_gap, marker=mk, color=c, lw=1)
    for a in axs:
        a.axhline(0, color=INK, lw=0.8); a.set_xticks([0.1, 0.25, 0.4]); a.set_xlabel("中身に写しがある確率")
    axs[0].set_ylabel("A−B（ポイント）"); axs[0].set_title("上位10件の正しい割合の差 A−B")
    axs[1].set_ylabel("B−A（件）"); axs[1].set_title("別々の正しい中身の数の差 B−A")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=c, label=f"正しい中身の写しやすさ {f:g}倍") for f, c in zip([1, 2, 3], [GRAY, BLUE, ORANGE])]
    h += [Line2D([], [], color=INK, marker=m, ls="", label=f"正しい中身 {R}件") for R, m in zip([3, 6, 10], ["o", "s", "^"])]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9, frameon=False)
    save(fig, "a1230_grid.png", SRC, y=-0.18)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(robust), f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
