"""1224 1件目に正しい文書があるかだけを数える点と、10件全体を順位で重み付けする点では、2つの検索の差がどう違って見えるのか？（架空のデータ）

架空の社内の文書の集まりと架空の検索語。検索語ごとに、候補の文書215件の「正しさ」（0・1・2の3段階）を作成者が決める。
検索語は2種類：「1つを探す語」（正しさ2の文書が1件だけ）と「広く集める語」（正しさ2が3件・正しさ1が12件）。
検索A・Bは、文書ごとの点（正しさに応じた上乗せ＋乱数）の高い順に10件を出す。
A は正しさ2の文書を強く押し上げ、B は正しさ1の文書もよく拾う。
2つの点で A と B の差を比べる：
  ①1件目の点：1件目の文書が正しい（正しさ1以上）なら1、そうでなければ0
  ②10件の点：上位10件の正しさの段階を、順位 r の位置で 1/log2(r+1) 倍して足し、理想の並びの値で割る（0〜1）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1224
SRC = "架空の社内の文書と検索語（作成者が置いた正しさと検索の点からの乱数、seed 1224）"
M = 215                 # 候補の文書の数（検索語ごと）
RHO = 0.7               # A と B の乱数の重なり（同じ文書を見ているので似る）
A = (3.2, 1.6)          # A：正しさ2・正しさ1の上乗せ
B = (2.6, 2.4)          # B
MIX = 0.4               # 1つを探す語の割合
NPOP = 20000            # 本当の差を数える検索語の数
NSET = 200              # 一覧の検索語の数
REPS = 1000
NGRID = 20000          # 割合を変える・27通りのときの検索語の数
DISC = 1 / np.log2(np.arange(2, 12))


def simulate(rng, nq, mix, meths, rho=RHO):
    one = rng.random(nq) < mix
    g = np.zeros((nq, M), dtype=np.int64)
    g[:, 0] = 2
    g[~one, 1:3] = 2
    g[~one, 3:15] = 1
    h = rng.uniform(0.6, 1.4, (nq, 1))            # 検索語ごとの手がかりの強さ
    common = rng.standard_normal((nq, M))
    ideal = -np.sort(-g, axis=1)[:, :10]
    idcg = (ideal * DISC).sum(1)
    out = {}
    for name, (a2, a1) in meths.items():
        e = np.sqrt(rho) * common + np.sqrt(1 - rho) * rng.standard_normal((nq, M))
        s = h * (a2 * (g == 2) + a1 * (g == 1)) + e
        part = np.argpartition(-s, 10, axis=1)[:, :10]
        order = np.argsort(-np.take_along_axis(s, part, 1), axis=1, kind="stable")
        idx = np.take_along_axis(part, order, 1)
        gt = np.take_along_axis(g, idx, 1)
        out[name] = {"top1": (gt[:, 0] >= 1).astype(float), "w10": (gt * DISC).sum(1) / idcg}
    return one, out


def r4(x):
    return float(round(float(x), 4))


def pt(x):
    return float(round(float(x) * 100, 2))


def outcome_shares(d):
    return {"A_better": pt((d > 1e-12).mean()), "tie": pt((np.abs(d) <= 1e-12).mean()), "B_better": pt((d < -1e-12).mean())}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res = {"setting": {"candidates": M, "rho": RHO, "A": A, "B": B, "mix_one": MIX, "n_pop": NPOP, "n_set": NSET, "reps": REPS}}

    # 1. 本当の差（検索語2万語）
    one, o = simulate(rng, NPOP, MIX, {"A": A, "B": B})
    pop = {}
    for k in ["top1", "w10"]:
        d = o["A"][k] - o["B"][k]
        pop[k] = {"A": pt(o["A"][k].mean()), "B": pt(o["B"][k].mean()), "diff_pt": pt(d.mean()),
                  "sd_diff_pt": pt(d.std()), "std_effect": r4(d.mean() / d.std()),
                  "outcomes": outcome_shares(d),
                  "diff_one_pt": pt(d[one].mean()), "diff_broad_pt": pt(d[~one].mean())}
    res["population"] = pop
    res["population_kind_share_one_pct"] = pt(one.mean())

    # 2. 200語の一覧を1,000回引く
    dpop = {k: o["A"][k] - o["B"][k] for k in ["top1", "w10"]}
    sets = {}
    rows = []
    for n in [NSET]:
        sets[n] = {}
        for k in ["top1", "w10"]:
            cnt = {"A_sig": 0, "none": 0, "B_sig": 0}
            means = []
            for r in range(REPS):
                pick = rng.choice(NPOP, n, replace=False)
                d = dpop[k][pick]
                m, se = d.mean(), d.std(ddof=1) / np.sqrt(n)
                means.append(m)
                if se == 0:
                    cnt["none"] += 1
                elif m > 1.96 * se:
                    cnt["A_sig"] += 1
                elif m < -1.96 * se:
                    cnt["B_sig"] += 1
                else:
                    cnt["none"] += 1
            means = np.array(means)
            sets[n][k] = {"A_sig_pct": pt(cnt["A_sig"] / REPS), "none_pct": pt(cnt["none"] / REPS), "B_sig_pct": pt(cnt["B_sig"] / REPS),
                          "mean_diff_p5_p95_pt": [pt(np.percentile(means, 5)), pt(np.percentile(means, 95))],
                          "sign_A_pct": pt((means > 0).mean())}
            rows.append({"n_queries": n, "point": k, **sets[n][k], "mean_diff_p5_pt": sets[n][k]["mean_diff_p5_p95_pt"][0],
                         "mean_diff_p95_pt": sets[n][k]["mean_diff_p5_p95_pt"][1]})
    for r in rows:
        r.pop("mean_diff_p5_p95_pt")
    pd.DataFrame(rows).to_csv(RES / "query_sets.csv", index=False)
    res["query_sets"] = {str(k): v for k, v in sets.items()}

    # 一覧の1回分（200語）をデータに
    pick = np.arange(NSET)
    pd.DataFrame({"query": np.arange(1, NSET + 1), "kind": np.where(one[pick], "one", "broad"),
                  "top1_A": o["A"]["top1"][pick].astype(int), "top1_B": o["B"]["top1"][pick].astype(int),
                  "w10_A": np.round(o["A"]["w10"][pick], 4), "w10_B": np.round(o["B"]["w10"][pick], 4)}).to_csv(DATA / "queries_200.csv", index=False)
    first = {}
    for k in ["top1", "w10"]:
        d = dpop[k][pick]
        first[k] = {"A": pt(o["A"][k][pick].mean()), "B": pt(o["B"][k][pick].mean()), "diff_pt": pt(d.mean()), "outcomes": outcome_shares(d)}
    res["first_set_200"] = first

    # 3. 1つを探す語の割合を変える
    mrows = []
    for mix in np.round(np.arange(0, 1.01, 0.1), 1):
        r2 = np.random.default_rng(SEED + int(mix * 100) + 1)
        _, oo = simulate(r2, NGRID, mix, {"A": A, "B": B})
        row = {"mix_one_pct": int(round(mix * 100))}
        for k in ["top1", "w10"]:
            d = oo["A"][k] - oo["B"][k]
            row[f"{k}_diff_pt"] = pt(d.mean())
            row[f"{k}_std_effect"] = r4(d.mean() / d.std())
            row[f"{k}_tie_pct"] = pt((np.abs(d) <= 1e-12).mean())
            row[f"{k}_se_pt"] = pt(d.std() / np.sqrt(len(d)))
        row["disagree"] = bool(np.sign(row["top1_diff_pt"]) != np.sign(row["w10_diff_pt"]))
        mrows.append(row)
    mdf = pd.DataFrame(mrows)
    mdf.to_csv(RES / "by_mix.csv", index=False)
    res["by_mix_disagree_mix_pct"] = [int(x) for x in mdf.loc[mdf.disagree, "mix_one_pct"]]

    # 4. 確かめ：27通り
    grows = []
    i = 0
    for a2 in [2.9, 3.2, 3.5]:
        for b1 in [2.0, 2.4, 2.8]:
            for mix in [0.1, 0.4, 0.7]:
                i += 1
                r3 = np.random.default_rng(SEED * 10 + i)
                _, oo = simulate(r3, NGRID, mix, {"A": (a2, A[1]), "B": (B[0], b1)})
                row = {"A_up2": a2, "B_up1": b1, "mix_one_pct": int(round(mix * 100))}
                for k in ["top1", "w10"]:
                    d = oo["A"][k] - oo["B"][k]
                    row[f"{k}_diff_pt"] = pt(d.mean())
                    row[f"{k}_std_effect"] = r4(d.mean() / d.std())
                    row[f"{k}_tie_pct"] = pt((np.abs(d) <= 1e-12).mean())
                    row[f"{k}_se_pt"] = pt(d.std() / np.sqrt(len(d)))
                row["disagree"] = bool(np.sign(row["top1_diff_pt"]) != np.sign(row["w10_diff_pt"]))
                row["ratio_abs_std_effect_w10_over_top1"] = r4(abs(row["w10_std_effect"]) / abs(row["top1_std_effect"])) if row["top1_std_effect"] != 0 else None
                grows.append(row)
    gdf = pd.DataFrame(grows)
    gdf.to_csv(RES / "grid.csv", index=False)
    same = gdf[~gdf.disagree]
    res["grid"] = {"n": len(gdf), "disagree_n": int(gdf.disagree.sum()),
                   "disagree_rows": gdf.loc[gdf.disagree, ["A_up2", "B_up1", "mix_one_pct", "top1_diff_pt", "top1_se_pt", "w10_diff_pt", "w10_se_pt"]].to_dict("records"),
                   "disagree_clear_n": int((gdf.disagree & (gdf.top1_diff_pt.abs() > 2 * gdf.top1_se_pt) & (gdf.w10_diff_pt.abs() > 2 * gdf.w10_se_pt)).sum()),
                   "top1_tie_pct_range": [float(gdf.top1_tie_pct.min()), float(gdf.top1_tie_pct.max())],
                   "w10_tie_pct_range": [float(gdf.w10_tie_pct.min()), float(gdf.w10_tie_pct.max())],
                   "ratio_range_same_sign": [float(same.ratio_abs_std_effect_w10_over_top1.min()), float(same.ratio_abs_std_effect_w10_over_top1.max())],
                   "w10_larger_std_effect_n_same_sign": int((same.ratio_abs_std_effect_w10_over_top1 > 1).sum()), "same_sign_n": int(len(same))}

    # 図1：1つを探す語の割合と差
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.axhline(0, color=GRAY, lw=1)
    ax.plot(mdf.mix_one_pct, mdf.top1_diff_pt, "o-", color=ORANGE, label="①1件目の点の差（A−B）")
    ax.plot(mdf.mix_one_pct, mdf.w10_diff_pt, "s-", color=BLUE, label="②10件の点の差（A−B）")
    dis = mdf[mdf.disagree]
    for x in dis.mix_one_pct:
        ax.axvspan(x - 5, x + 5, color=LIGHT, alpha=0.35, lw=0)
    ax.set_xlabel("検索語のうち「1つを探す語」の割合（%）")
    ax.set_ylabel("A−B（ポイント）")
    ax.set_title("2つの点の差は、検索語の顔ぶれで大きさも向きも変わる\n（薄い帯：2つの点で良い方が入れかわる割合）")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1224_mix.png", SRC)

    # 図2：検索語ごとの勝ち負け（帯グラフ）
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    labels = ["①1件目の点", "②10件の点"]
    for j, k in enumerate(["top1", "w10"]):
        oc = pop[k]["outcomes"]
        left = 0
        for key, col, lab in [("A_better", ORANGE, "A が上"), ("tie", GRAY, "同じ"), ("B_better", BLUE, "B が上")]:
            ax.barh(j, oc[key], left=left, color=col, label=lab if j == 0 else None)
            if oc[key] >= 6:
                ax.text(left + oc[key] / 2, j, f"{oc[key]}%", ha="center", va="center", color="white", fontsize=9)
            left += oc[key]
    ax.set_yticks([0, 1], labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("検索語に占める割合（%）")
    ax.set_title("検索語ごとに A と B を比べると、①は大半が「同じ」")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    save(fig, "a1224_ties.png", SRC, y=-0.34)

    # 図3：200語の一覧を引き直したときの見分け
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for j, k in enumerate(["top1", "w10"]):
        sv = sets[NSET][k]
        left = 0
        for key, col, lab in [("A_sig_pct", ORANGE, "A が上と見分けた"), ("none_pct", GRAY, "偶然の幅の中"), ("B_sig_pct", BLUE, "B が上と見分けた")]:
            ax.barh(j, sv[key], left=left, color=col, label=lab if j == 0 else None)
            if sv[key] >= 6:
                ax.text(left + sv[key] / 2, j, f"{sv[key]}%", ha="center", va="center", color="white", fontsize=9)
            left += sv[key]
    ax.set_yticks([0, 1], labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel(f"{NSET}語の一覧を{REPS:,}回引き直したうちの割合（%）")
    ax.set_title(f"同じ A・B・同じ{NSET}語でも、①では半分ほどの回で差が偶然の幅の中")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    save(fig, "a1224_sets.png", SRC, y=-0.34)

    res["run_sec_note"] = "run_sec は results に入れない（流すたびに変わるため）"
    with open(RES / "a1224_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({"population": pop, "first": first, "sets": res["query_sets"], "mix_dis": res["by_mix_disagree_mix_pct"], "grid": res["grid"]}, ensure_ascii=False, indent=1))
    print(mdf.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
