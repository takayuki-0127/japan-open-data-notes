"""1221 上位10件の正しい割合で比べるか、正しい文書を拾えた割合で比べるかで、良い方の検索は入れかわるのか？（架空のデータ）

架空の社内の文書2,000件と、架空の検索語50語。語ごとに「正しい文書」を作成者が決める（1〜100件、対数で一様）。
検索のやり方A・Bは、正しい文書に点数を上乗せして並べる。上乗せの大きさは作成者が置く
（A は正しい文書の多い語ほど強く、B はどの語でも同じ）。正しくない文書の点数はどちらも同じ散らばり。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1221
SRC = "架空の社内の文書と検索語（作成者が置いた正しさと点数からの乱数、seed 1221）"
DOCS, Q = 2000, 50
BASE = dict(nmax=100, a0=1.0, slope=0.5, dB=1.6, k=10, deep=100)
GROUPS = [(1, 3), (4, 10), (11, 30), (31, 100)]


def one_set(rng, Q=Q, nmax=100, a0=1.0, slope=0.5, dB=1.6, k=10, deep=100):
    """検索語 Q 語を作り、A・B の上位 k 件・deep 件に入った正しい文書の数を返す"""
    n = np.round(np.exp(rng.uniform(0, np.log(nmax), Q))).astype(int)
    mask = np.arange(DOCS)[None, :] < n[:, None]
    hits = {}
    for name, d in [("A", a0 + slope * np.log10(n)), ("B", np.full(Q, dB))]:
        s = rng.standard_normal((Q, DOCS)) + d[:, None] * mask
        idx = np.argpartition(-s, [k - 1, deep - 1], axis=1)
        h = np.take_along_axis(mask, idx, 1)
        hits[name] = (h[:, :k].sum(1), h[:, :deep].sum(1))
    return n, hits


def scores(n, hits, k):
    """3つの物差しの平均（語ごとに同じ重み）と、合計で割った拾えた割合"""
    out = {}
    for m in "AB":
        hk, hd = hits[m]
        out[m] = {"top_share": hk.mean() / k, "found_k": (hk / n).mean(), "found_100": (hd / n).mean(),
                  "found_k_pooled": hk.sum() / n.sum()}
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分（data に置く）
    n, hits = one_set(rng)
    one = pd.DataFrame({"query_id": np.arange(1, Q + 1), "n_correct": n,
                        "A_top10_hits": hits["A"][0], "B_top10_hits": hits["B"][0],
                        "A_top100_hits": hits["A"][1], "B_top100_hits": hits["B"][1]})
    one.to_csv(DATA / "queries_one_set.csv", index=False)
    sc1 = scores(n, hits, 10)
    one_res = {"A": {k: round(float(v), 4) for k, v in sc1["A"].items()},
               "B": {k: round(float(v), 4) for k, v in sc1["B"].items()},
               "queries_A_more_top10": int((one.A_top10_hits > one.B_top10_hits).sum()),
               "queries_B_more_top10": int((one.A_top10_hits < one.B_top10_hits).sum()),
               "queries_tie_top10": int((one.A_top10_hits == one.B_top10_hits).sum()),
               "queries_n_le_3": int((one.n_correct <= 3).sum())}

    # 2) 基本の置き方で200回
    rows, grp = [], []
    for r in range(200):
        g = np.random.default_rng(SEED * 1000 + r)
        n, hits = one_set(g)
        sc = scores(n, hits, 10)
        rows.append({"rep": r, **{f"{m}_{k}": v for m in "AB" for k, v in sc[m].items()}})
        for lo, hi in GROUPS:
            sel = (n >= lo) & (n <= hi)
            if sel.sum() == 0:
                continue
            for m in "AB":
                hk = hits[m][0][sel]
                grp.append({"rep": r, "group": f"{lo}〜{hi}件", "method": m, "queries": int(sel.sum()),
                            "top_share": hk.sum() / (10 * sel.sum()), "found_k_sum": (hk / n[sel]).sum()})
    reps = pd.DataFrame(rows)
    reps.to_csv(RES / "reps_base.csv", index=False, float_format="%.6f")
    for key in ["top_share", "found_k", "found_100", "found_k_pooled"]:
        reps[f"A_wins_{key}"] = reps[f"A_{key}"] > reps[f"B_{key}"]
    mean = {c: round(float(reps[c].mean()), 4) for c in reps.columns if c[:2] in ("A_", "B_") and "wins" not in c}
    win = {key: round(float(reps[f"A_wins_{key}"].mean()), 4) for key in ["top_share", "found_k", "found_100", "found_k_pooled"]}
    flip_k = round(float((reps.A_wins_top_share != reps.A_wins_found_k).mean()), 4)
    flip_100 = round(float((reps.A_wins_top_share != reps.A_wins_found_100).mean()), 4)
    pooled_same = round(float((reps.A_wins_top_share == reps.A_wins_found_k_pooled).mean()), 4)

    G = pd.DataFrame(grp)
    gq = G.groupby(["group", "method"], sort=False).agg(queries=("queries", "sum"), top=("top_share", "mean"),
                                                         fsum=("found_k_sum", "sum")).reset_index()
    gq["found_k"] = gq.fsum / gq.queries
    # 語ごとの重み：上位10件の割合では1語あたり 1/(10×語数)、拾えた割合では 1/(正しい件数×語数)
    by_group = []
    for (lo, hi) in GROUPS:
        name = f"{lo}〜{hi}件"
        a = gq[(gq.group == name) & (gq.method == "A")].iloc[0]
        b = gq[(gq.group == name) & (gq.method == "B")].iloc[0]
        by_group.append({"group": name, "queries_per_set": round(a.queries / 200, 2),
                         "A_top_share": round(float(a.top), 4), "B_top_share": round(float(b.top), 4),
                         "A_found10": round(float(a.found_k), 4), "B_found10": round(float(b.found_k), 4),
                         "max_top_share": round(min(hi, 10) / 10, 1),
                         "A_minus_B_top_pt": round(float(a.top - b.top) * 100, 2),
                         "A_minus_B_found10_pt": round(float(a.found_k - b.found_k) * 100, 2)})
    bg = pd.DataFrame(by_group)
    bg.to_csv(RES / "by_group_base.csv", index=False)

    # 3) 確かめ：A の伸び方×B の強さ×正しい文書の多さの上限×上位何件で数えるか（各20回）
    grid = []
    for slope in [0.0, 0.25, 0.5, 1.0]:
        for dB in [1.4, 1.6, 1.8]:
            for nmax in [30, 100, 300]:
                for k in [5, 10, 20]:
                    w = []
                    for r in range(20):
                        g = np.random.default_rng([SEED, int(slope * 100), int(dB * 10), nmax, k, r])
                        n, hits = one_set(g, nmax=nmax, slope=slope, dB=dB, k=k)
                        sc = scores(n, hits, k)
                        w.append([sc["A"][x] > sc["B"][x] for x in ["top_share", "found_k", "found_100", "found_k_pooled"]]
                                 + [sc["A"]["top_share"] - sc["B"]["top_share"], sc["A"]["found_k"] - sc["B"]["found_k"]])
                    w = np.array(w, dtype=float)
                    grid.append({"slope": slope, "dB": dB, "nmax": nmax, "k": k,
                                 "A_wins_top": w[:, 0].mean(), "A_wins_found_k": w[:, 1].mean(), "A_wins_found_100": w[:, 2].mean(),
                                 "flip_k": float((w[:, 0] != w[:, 1]).mean()), "flip_100": float((w[:, 0] != w[:, 2]).mean()),
                                 "pooled_same_as_top": float((w[:, 0] == w[:, 3]).mean()),
                                 "diff_top": round(float(w[:, 4].mean()), 4), "diff_found_k": round(float(w[:, 5].mean()), 4)})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False, float_format="%.4f")
    # 平均の向きで入れかわる置き方（20回の平均の差の符号が違う）
    gr["avg_flip"] = np.sign(gr.diff_top) != np.sign(gr.diff_found_k)
    robust = {"settings": int(len(gr)),
              "avg_sign_flip_settings": int(gr.avg_flip.sum()),
              "avg_sign_flip_settings_slope0": int(gr[gr.slope == 0].avg_flip.sum()),
              "avg_sign_flip_by_slope": {str(s): int(gr[gr.slope == s].avg_flip.sum()) for s in [0.0, 0.25, 0.5, 1.0]},
              "avg_sign_flip_A_top_B_found": int((gr.avg_flip & (gr.diff_top > 0)).sum()),
              "base_setting_in_grid_flip_k": round(float(gr[(gr.slope == 0.5) & (gr.dB == 1.6) & (gr.nmax == 100) & (gr.k == 10)].flip_k.iloc[0]), 4),
              "flip_k_range": [round(float(gr.flip_k.min()), 4), round(float(gr.flip_k.max()), 4)],
              "flip_k_mean_by_slope": {str(s): round(float(gr[gr.slope == s].flip_k.mean()), 4) for s in [0.0, 0.25, 0.5, 1.0]},
              "flip_k_mean_by_k": {str(k): round(float(gr[gr.k == k].flip_k.mean()), 4) for k in [5, 10, 20]},
              "flip_k_mean_by_nmax": {str(x): round(float(gr[gr.nmax == x].flip_k.mean()), 4) for x in [30, 100, 300]},
              "flip_k_max_slope0": round(float(gr[gr.slope == 0].flip_k.max()), 4),
              "flip_k_min_slope0": round(float(gr[gr.slope == 0].flip_k.min()), 4),
              "pooled_same_as_top_min": round(float(gr.pooled_same_as_top.min()), 4),
              "flip_k_by_slope_k": {f"slope{s}_top{k}": round(float(gr[(gr.slope == s) & (gr.k == k)].flip_k.mean()), 4)
                                    for s in [0.0, 0.25, 0.5, 1.0] for k in [5, 10, 20]}}

    out = {"headline": {"mean_200": mean, "A_wins_share_200": win, "flip_top_vs_found10": flip_k,
                        "flip_top_vs_found100": flip_100, "pooled_found10_same_as_top": pooled_same},
           "by_group_base": bg.to_dict("records"), "one_set": one_res, "robust": robust,
           "setup": {"docs": DOCS, "queries": Q, **BASE, "reps": 200, "grid_reps": 20}}
    json.dump(out, open(RES / "a1221_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：正しい文書の数ごとの、2つの物差し
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), sharey=True)
    x = np.arange(len(bg))
    for ax, (ca, cb, ttl) in zip(axs, [("A_top_share", "B_top_share", "上位10件の正しい割合"),
                                         ("A_found10", "B_found10", "正しい文書を上位10件に拾えた割合")]):
        ax.bar(x - 0.2, bg[ca] * 100, 0.4, color=BLUE, label="やり方A")
        ax.bar(x + 0.2, bg[cb] * 100, 0.4, color=ORANGE, label="やり方B")
        for i in range(len(bg)):
            ax.text(i - 0.21, bg[ca][i] * 100 + 1.5, f"{bg[ca][i]*100:.2f}", ha="center", fontsize=6.5)
            ax.text(i + 0.21, bg[cb][i] * 100 + 1.5, f"{bg[cb][i]*100:.2f}", ha="center", fontsize=6.5)
        ax.set_xticks(x); ax.set_xticklabels(bg.group); ax.set_title(ttl, fontsize=11)
        ax.set_xlabel("語ごとの正しい文書の数"); ax.set_ylim(0, 100)
    axs[0].set_ylabel("%（200回の平均）"); axs[0].legend(frameon=False, fontsize=9)
    fig.suptitle("語ごとの正しい文書の数で分けた2つの物差し（置いた例、200回の平均）", fontsize=12, y=1.03)
    save(fig, "a1221_by_group.png", SRC)

    # 図2：1回分の語ごとの差（上位10件に入った正しい文書の数、A−B）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    dif = one.A_top10_hits - one.B_top10_hits
    jit = np.random.default_rng(SEED + 5).uniform(-0.12, 0.12, len(one))
    ax.scatter(one.n_correct, dif + jit, s=22, color=np.where(dif > 0, BLUE, np.where(dif < 0, ORANGE, GRAY)), lw=0)
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xscale("log"); ax.set_xlabel("語ごとの正しい文書の数（対数の目盛り）")
    ax.set_ylabel("上位10件の正しい文書の数の差（A−B）\n点は重ならないよう上下に少しずらした", fontsize=9.5)
    ax.set_title("語ごとの勝ち負けは、どちらの物差しでも同じ（作りどおり、1回分の50語）")
    save(fig, "a1221_per_query.png", SRC)

    # 図3：確かめ。A の伸び方ごとの、2つの物差しで勝つ方が入れかわった回の割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    sl = [0.0, 0.25, 0.5, 1.0]
    for j, k in enumerate([5, 10, 20]):
        v = [robust["flip_k_by_slope_k"][f"slope{s}_top{k}"] * 100 for s in sl]
        ax.bar(np.arange(4) + (j - 1) * 0.26, v, 0.26, color=[LIGHT, BLUE, INK][j], label=f"上位{k}件で数える")
        for i, vv in enumerate(v):
            ax.text(i + (j - 1) * 0.26, vv + 1, f"{vv:.2f}", ha="center", fontsize=6.5)
    ax.set_xticks(np.arange(4)); ax.set_xticklabels([f"Aの伸び {s}" for s in sl])
    ax.set_ylabel("勝つ方が入れかわった回の割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("入れかわりは、語によって強い方が違う置き方で多い（ほかの置き方9通りの平均、各20回）")
    save(fig, "a1221_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
