"""1225 結果が0件の検索を数から外すと、検索の良さはどう見えるのか？（架空のデータ）

架空の社内の文書の集まりで、1か月に出た検索語2,000語（1語1回）を比べる。
語ごとに「正しい文書が集まりの中にあるか」と「むずかしさ」を作成者が置く。
検索A：語をすべて含む文書だけを出す。むずかしい語ほど0件になりやすい。
検索B：語の一部が合えば出す。A が結果を出した語では A と同じ結果、A が0件だった語でも多くは何かを出す。
良さは「上位10件に正しい文書が1件以上あった語の割合」（見つかった割合）。
数え方：①0件の語を外す　②0件の語を0点として入れる　③正しい文書がある語だけを数え、0件は0点
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1225
SRC = "架空の社内の文書と検索語（作成者が置いたむずかしさ・0件の確率・見つかる確率からの乱数、seed 1225）"
NQ = 2000
REPS = 500
BASE = dict(cut=1.1, rescue=1.0, loss=0.04, noans=0.08)


def sig(x):
    return 1 / (1 + np.exp(-x))


def simulate(rng, nq, cut, rescue, loss, noans):
    z = rng.standard_normal(nq)                      # むずかしさ
    ans = rng.random(nq) >= noans                    # 正しい文書が集まりの中にあるか
    u0, u1, u2, u3, u4 = (rng.random(nq) for _ in range(5))
    # A：語をすべて含む文書だけ
    pz_a = np.where(ans, sig(2.2 * (z - cut)), 0.6)
    zero_a = u0 < pz_a
    ok_a = ans & ~zero_a & (u1 < sig(1.6 - 1.0 * z))
    # B：語の一部が合えば出す。A が出した語は、一部だけ合う文書が割りこみ、A で見つかった語のうち loss の割合で正しい文書が10件の外に落ちる
    pz_b = np.where(ans, sig(2.2 * (z - 3.0)), 0.05)
    zero_b = np.where(zero_a, u2 < pz_b / np.maximum(pz_a, 1e-12), False)   # A が出した語は B も出す
    zero_b = zero_b & zero_a
    rescued = zero_a & ~zero_b
    ok_b = np.where(zero_a, ans & rescued & (u3 < rescue * sig(0.2 - 1.0 * z)), ok_a & (u4 >= loss))
    return dict(z=z, ans=ans, zero_a=zero_a, zero_b=zero_b, ok_a=ok_a, ok_b=ok_b, rescued=rescued)


def scores(d):
    out = {}
    for m in ["a", "b"]:
        zero, ok, ans = d[f"zero_{m}"], d[f"ok_{m}"], d["ans"]
        out[m] = {"excl": ok[~zero].mean() * 100, "zero0": ok.mean() * 100, "ans_only": ok[ans].mean() * 100,
                  "zero_share": zero.mean() * 100}
    return out


def r2(x):
    return float(round(float(x), 2))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res = {"setting": {"n_queries": NQ, "reps": REPS, **BASE}}

    d = simulate(rng, NQ, **BASE)
    s = scores(d)
    main_tab = {m: {k: r2(v) for k, v in s[m].items()} for m in ["a", "b"]}
    main_tab["diff_b_minus_a"] = {k: r2(s["b"][k] - s["a"][k]) for k in ["excl", "zero0", "ans_only"]}
    res["one_month"] = main_tab
    # 0件の中身
    za = d["zero_a"]
    res["zero_a_detail"] = {"n_zero_a": int(za.sum()), "no_answer_share_of_zero_a_pct": r2((~d["ans"][za]).mean() * 100),
                            "no_answer_share_all_pct": r2((~d["ans"]).mean() * 100),
                            "no_answer_shown_a_pct": r2((~d["zero_a"][~d["ans"]]).mean() * 100),
                            "no_answer_shown_b_pct": r2((~d["zero_b"][~d["ans"]]).mean() * 100)}
    # B の語の内訳
    grp = {
        "A_also_results": ~za,
        "rescued": d["rescued"],
        "still_zero": d["zero_b"],
    }
    gdet = {}
    for k, m in grp.items():
        gdet[k] = {"share_pct": r2(m.mean() * 100), "found_b_pct": r2(d["ok_b"][m].mean() * 100) if m.sum() else None,
                   "mean_difficulty": r2(d["z"][m].mean()) if m.sum() else None}
    res["b_groups"] = gdet
    pd.DataFrame({"query": np.arange(1, NQ + 1), "difficulty": np.round(d["z"], 3), "has_answer": d["ans"].astype(int),
                  "zero_A": d["zero_a"].astype(int), "found_A": d["ok_a"].astype(int),
                  "zero_B": d["zero_b"].astype(int), "found_B": d["ok_b"].astype(int)}).to_csv(DATA / "queries_one_month.csv", index=False)

    # 引き直し
    rows = []
    for r in range(REPS):
        dd = simulate(rng, NQ, **BASE)
        ss = scores(dd)
        rows.append({"rep": r + 1, **{f"{k}_{m}": r2(ss[m][k]) for m in ["a", "b"] for k in ["excl", "zero0", "ans_only", "zero_share"]},
                     **{f"diff_{k}": r2(ss["b"][k] - ss["a"][k]) for k in ["excl", "zero0", "ans_only"]}})
    rdf = pd.DataFrame(rows)
    rdf.to_csv(RES / "reps.csv", index=False)
    res["reps"] = {f"diff_{k}_p5_p95": [r2(np.percentile(rdf[f"diff_{k}"], 5)), r2(np.percentile(rdf[f"diff_{k}"], 95))] for k in ["excl", "zero0", "ans_only"]}
    res["reps"]["excl_says_A_pct"] = r2((rdf.diff_excl < 0).mean() * 100)
    res["reps"]["zero0_says_B_pct"] = r2((rdf.diff_zero0 > 0).mean() * 100)
    res["reps"]["zero_share_a_p5_p95"] = [r2(np.percentile(rdf.zero_share_a, 5)), r2(np.percentile(rdf.zero_share_a, 95))]

    # 確かめ：81通り（各2万語）
    grows = []
    i = 0
    for cut in [1.6, 1.1, 0.55]:
        for rescue in [0.5, 1.0, 2.0]:
            for loss in [0.0, 0.04, 0.08]:
                for noans in [0.0, 0.08, 0.2]:
                    i += 1
                    rg = np.random.default_rng(SEED * 10 + i)
                    dd = simulate(rg, 20000, cut, rescue, loss, noans)
                    ss = scores(dd)
                    row = {"cut": cut, "rescue": rescue, "loss_pct": int(round(loss * 100)), "no_answer_pct": int(round(noans * 100)),
                           "zero_share_a": r2(ss["a"]["zero_share"]), "zero_share_b": r2(ss["b"]["zero_share"])}
                    for k in ["excl", "zero0", "ans_only"]:
                        row[f"a_{k}"] = r2(ss["a"][k]); row[f"b_{k}"] = r2(ss["b"][k]); row[f"diff_{k}"] = r2(ss["b"][k] - ss["a"][k])
                    row["rescued_found_pct"] = r2(dd["ok_b"][dd["rescued"]].mean() * 100)
                    row["a_results_found_pct"] = r2(dd["ok_a"][~dd["zero_a"]].mean() * 100)
                    za2 = dd["zero_a"]
                    row["no_answer_share_of_zero_a_pct"] = r2((~dd["ans"][za2]).mean() * 100) if za2.sum() else None
                    grows.append(row)
    gdf = pd.DataFrame(grows)
    gdf.to_csv(RES / "grid.csv", index=False)
    res["grid"] = {"n": len(gdf),
                   "excl_A_better_n": int((gdf.diff_excl < 0).sum()),
                   "zero0_B_better_n": int((gdf.diff_zero0 > 0).sum()),
                   "ans_only_B_better_n": int((gdf.diff_ans_only > 0).sum()),
                   "disagree_excl_vs_zero0_n": int((np.sign(gdf.diff_excl) != np.sign(gdf.diff_zero0)).sum()),
                   "diff_excl_range": [float(gdf.diff_excl.min()), float(gdf.diff_excl.max())],
                   "diff_zero0_range": [float(gdf.diff_zero0.min()), float(gdf.diff_zero0.max())],
                   "zero_share_a_range": [float(gdf.zero_share_a.min()), float(gdf.zero_share_a.max())],
                   "rescued_found_range": [float(gdf.rescued_found_pct.min()), float(gdf.rescued_found_pct.max())],
                   "excl_B_better_rows": gdf.loc[gdf.diff_excl > 0, ["cut", "rescue", "loss_pct", "no_answer_pct", "diff_excl", "rescued_found_pct", "a_results_found_pct"]].to_dict("records"),
                   "zero0_A_better_rows": gdf.loc[gdf.diff_zero0 < 0, ["cut", "rescue", "loss_pct", "no_answer_pct", "diff_zero0", "diff_excl"]].to_dict("records"),
                   "excl_wrong_dir_when_zero0_B_n": int(((gdf.diff_zero0 > 0) & (gdf.diff_excl < 0)).sum())}
    res["grid"]["zero0_B_better_n_by_loss_pct"] = {str(k): int((g.diff_zero0 > 0).sum()) for k, g in gdf.groupby("loss_pct")}
    res["grid"]["rescued_found_range_by_rescue"] = {str(k): [float(g.rescued_found_pct.min()), float(g.rescued_found_pct.max())] for k, g in gdf.groupby("rescue")}
    res["grid"]["zero0_A_better_n_by_cut"] = {str(k): int((g.diff_zero0 < 0).sum()) for k, g in gdf.groupby("cut")}
    res["grid"]["zero_share_a_range_by_cut"] = {str(k): [float(g.zero_share_a.min()), float(g.zero_share_a.max())] for k, g in gdf.groupby("cut")}
    res["grid"]["a_results_found_range"] = [float(gdf.a_results_found_pct.min()), float(gdf.a_results_found_pct.max())]
    sub = gdf[gdf.no_answer_pct > 0]
    res["grid"]["no_answer_share_of_zero_a_range_pct"] = [float(sub.no_answer_share_of_zero_a_pct.min()), float(sub.no_answer_share_of_zero_a_pct.max())]

    # 図1：3つの数え方
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    keys = ["excl", "zero0", "ans_only"]
    labs = ["①0件の語を外す", "②0件の語を0点", "③正しい文書がある語だけ\n（0件は0点）"]
    x = np.arange(3)
    va = [main_tab["a"][k] for k in keys]; vb = [main_tab["b"][k] for k in keys]
    b1 = ax.bar(x - 0.18, va, 0.36, color=ORANGE, label=f"A：語をすべて含む文書だけ（0件 {main_tab['a']['zero_share']}%）")
    b2 = ax.bar(x + 0.18, vb, 0.36, color=BLUE, label=f"B：語の一部が合えば出す（0件 {main_tab['b']['zero_share']}%）")
    for bars in (b1, b2):
        for bb in bars:
            ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 1, f"{bb.get_height():.2f}%", ha="center", fontsize=9)
    ax.set_xticks(x, labs)
    ax.set_ylim(0, 100)
    ax.set_ylabel("見つかった割合（%）")
    ax.set_title(f"同じ{NQ:,}語の結果でも、0件の語を外すと A が上に見える")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1)
    save(fig, "a1225_three_ways.png", SRC, y=-0.3)

    # 図2：B の語の内訳
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    order = [("A_also_results", "A も結果を出した語"), ("rescued", "A は0件、B は出した語"), ("still_zero", "B でも0件の語")]
    vals = [gdet[k]["found_b_pct"] or 0 for k, _ in order]
    bars = ax.bar(range(3), vals, color=[GRAY, BLUE, LIGHT])
    for j, (k, _) in enumerate(order):
        ax.text(j, vals[j] + 1.5, f"{vals[j]:.2f}%\n（語の{gdet[k]['share_pct']}%）", ha="center", fontsize=9)
    ax.set_xticks(range(3), [lab for _, lab in order])
    ax.set_ylim(0, 100)
    ax.set_ylabel("B で見つかった割合（%）")
    ax.set_title("0件だった語を拾うと、拾った語は見つかりにくい語なので①の平均は下がる")
    save(fig, "a1225_rescued.png", SRC)

    # 図3：81通り
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    ax.axhline(0, color=GRAY, lw=1); ax.axvline(0, color=GRAY, lw=1)
    cols = {0: GREEN, 8: BLUE, 20: ORANGE}
    for na, g in gdf.groupby("no_answer_pct"):
        ax.scatter(g.diff_excl, g.diff_zero0, color=cols[na], s=36, label=f"正しい文書がない語 {na}%")
    ax.set_xlabel("①0件の語を外したときの差（B−A、ポイント）")
    ax.set_ylabel("②0件の語を0点にしたときの差（B−A、ポイント）")
    ax.set_title(f"置き方の81通り：①で A が上は{res['grid']['excl_A_better_n']}通り、②で B が上は{res['grid']['zero0_B_better_n']}通り")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1225_grid.png", SRC)

    with open(RES / "a1225_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ["one_month", "zero_a_detail", "b_groups", "reps"]}, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res["grid"].items()}, ensure_ascii=False))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
