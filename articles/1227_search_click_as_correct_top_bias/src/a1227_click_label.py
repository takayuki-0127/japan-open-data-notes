"""1227 クリックされた文書を正しいと見なすと、上に出ていた文書はどれだけ有利になるのか？（架空のデータ）

作成者が置いた架空の社内の文書の集まりと検索語。
  検索語300語。1語ごとに候補の文書40件、うち本当に正しい文書は6件（作成者が決める）。
  今の検索 A の点＝1.0×（正しければ1）＋ゆらぎ、新しい検索 B の点＝1.6×（正しければ1）＋ゆらぎ（ゆらぎは平均0・標準偏差1、A と B で別々）。
  利用の記録は A だけから取る：A の順に1〜20位を出し、p 位の文書が見られる見込み＝(1/p)^η（基本 η=1）。21位より下は出さない。
  見た文書をクリックする見込み：正しい文書0.6、正しくない文書0.15。1語あたり20回検索される。
クリックを正解と見なす2つの決め方：
  ① 1回でもクリックされた文書を正しいとする
  ② 見られやすさで割り戻す：クリック数÷（検索回数×その位置の見られる見込み）が0.375（0.6と0.15の真ん中）以上なら正しいとする（見られる見込みは分かっていると置く）
  どちらも、A が21位より下にした文書は記録がないので正しくないと扱う。
良さの物差し：上位10件の正しい割合（本当の正しさで数える／クリックの決め方で数える）。
(1) 基本を200回  (2) 位置ごとの「正しい」と決まる割合（式：1−(1−クリックの見込み×見られる見込み)^検索回数）
(3) 確かめ：η 3通り×正しくない文書のクリック0.05・0.15・0.3×1語あたりの検索回数5・20・100＝27通り（各20回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1227
SRC = "架空の社内の文書と検索語（作成者が置いた正しさ・見られる見込み・クリックの見込みからの乱数、seed 1227）"
Q, C, NREL = 300, 40, 6
SHOWN = 20
MU_A, MU_B = 1.0, 1.6
CLICK_REL = 0.6
BASE = dict(eta=1.0, c_not=0.15, sess=20)
R_MAIN, R_GRID = 200, 20
T0 = time.time()


def r(x, d=2):
    return round(float(x), d)


def one_run(rng, eta, c_not, sess, keep=False):
    rel = np.zeros((Q, C), bool)
    rel[:, :NREL] = True
    sa = MU_A * rel + rng.normal(size=(Q, C))
    sb = MU_B * rel + rng.normal(size=(Q, C))
    order_a = np.argsort(-sa, axis=1)
    pos = np.empty((Q, C), int)
    np.put_along_axis(pos, order_a, np.arange(1, C + 1)[None, :].repeat(Q, 0), axis=1)
    exam = np.where(pos <= SHOWN, (1.0 / pos) ** eta, 0.0)
    cprob = np.where(rel, CLICK_REL, c_not)
    clicks = rng.binomial(sess, exam * cprob)
    lab1 = clicks >= 1
    with np.errstate(divide="ignore", invalid="ignore"):
        est = np.where(exam > 0, clicks / (sess * exam), 0.0)
    lab2 = est >= (CLICK_REL + c_not) / 2
    order_b = np.argsort(-sb, axis=1)
    top_a, top_b = order_a[:, :10], order_b[:, :10]
    g = lambda m, t: np.take_along_axis(m, t, axis=1).mean()
    out = {"A_true": g(rel, top_a), "B_true": g(rel, top_b), "A_lab1": g(lab1, top_a), "B_lab1": g(lab1, top_b),
           "A_lab2": g(lab2, top_a), "B_lab2": g(lab2, top_b),
           "B_top10_from_A_below20": g(pos > SHOWN, top_b),
           "B_top10_rel_from_A_below20": (np.take_along_axis(rel & (pos > SHOWN), top_b, 1).sum()
                                          / np.take_along_axis(rel, top_b, 1).sum())}
    if keep:
        out["_pos"], out["_rel"], out["_lab1"], out["_lab2"], out["_clicks"] = pos, rel, lab1, lab2, clicks
        out["_sb"] = sb
    return out


def main():
    rng = np.random.default_rng(SEED)
    runs, pos_rows = [], []
    acc = {}
    for i in range(R_MAIN):
        o = one_run(rng, **BASE, keep=True)
        pos, rel, l1, l2 = o["_pos"], o["_rel"], o["_lab1"], o["_lab2"]
        bucket = np.minimum(pos, SHOWN + 1)
        for t in (True, False):
            m = rel == t
            for b in range(1, SHOWN + 2):
                mm = m & (bucket == b)
                a = acc.setdefault((t, b), [0, 0, 0])
                a[0] += mm.sum(); a[1] += l1[mm].sum(); a[2] += l2[mm].sum()
        if i == 0:
            ex = pd.DataFrame({"query_id": np.repeat(np.arange(Q), C), "doc_id": np.tile(np.arange(C), Q),
                               "correct": rel.ravel().astype(int), "rank_A": pos.ravel(),
                               "clicks": o["_clicks"].ravel(), "label_click_any": l1.ravel().astype(int),
                               "label_reweighted": l2.ravel().astype(int),
                               "rank_B": (np.argsort(np.argsort(-o["_sb"], axis=1), axis=1) + 1).ravel()})
            ex.to_csv(DATA / "click_log_example.csv", index=False)
        runs.append({k: v for k, v in o.items() if not k.startswith("_")})
    rdf = pd.DataFrame(runs)
    m = rdf.mean()
    # 位置ごと
    for (t, b), (n, s1, s2) in sorted(acc.items(), key=lambda x: (not x[0][0], x[0][1])):
        if b <= SHOWN:
            e = (1.0 / b) ** BASE["eta"]
            c = CLICK_REL if t else BASE["c_not"]
            f = 1 - (1 - c * e) ** BASE["sess"]
        else:
            f = 0.0
        pos_rows.append({"correct": int(t), "rank_A": b if b <= SHOWN else "21-40", "docs": int(n),
                         "label_click_any_pct": r(100 * s1 / n), "formula_pct": r(100 * f),
                         "label_reweighted_pct": r(100 * s2 / n)})
    pdf = pd.DataFrame(pos_rows)
    pdf.to_csv(RES / "by_rank_label_rate.csv", index=False)
    gap_formula = float((pdf.label_click_any_pct - pdf.formula_pct).abs().max())

    main_tbl = pd.DataFrame([
        {"measure": "本当の正しさ", "A_pct": r(100 * m.A_true), "B_pct": r(100 * m.B_true)},
        {"measure": "①1回でもクリック", "A_pct": r(100 * m.A_lab1), "B_pct": r(100 * m.B_lab1)},
        {"measure": "②見られやすさで割り戻す", "A_pct": r(100 * m.A_lab2), "B_pct": r(100 * m.B_lab2)}])
    main_tbl["B_minus_A_pt"] = (main_tbl.B_pct - main_tbl.A_pct).round(2)
    main_tbl["reps_B_below_A_pct"] = [r(100 * (rdf.B_true < rdf.A_true).mean()),
                                      r(100 * (rdf.B_lab1 < rdf.A_lab1).mean()),
                                      r(100 * (rdf.B_lab2 < rdf.A_lab2).mean())]
    main_tbl.to_csv(RES / "base_top10_A_vs_B.csv", index=False)

    # 確かめ 27通り
    grid = []
    for eta in (0.5, 1.0, 1.5):
        for c_not in (0.05, 0.15, 0.3):
            for sess in (5, 20, 100):
                rr = pd.DataFrame([one_run(rng, eta, c_not, sess) for _ in range(R_GRID)])
                mm = rr.mean()
                grid.append({"eta": eta, "click_not_correct": c_not, "searches_per_query": sess,
                             "A_true_pct": r(100 * mm.A_true), "B_true_pct": r(100 * mm.B_true),
                             "A_lab1_pct": r(100 * mm.A_lab1), "B_lab1_pct": r(100 * mm.B_lab1),
                             "A_lab2_pct": r(100 * mm.A_lab2), "B_lab2_pct": r(100 * mm.B_lab2),
                             "diff_true_pt": r(100 * (mm.B_true - mm.A_true)),
                             "diff_lab1_pt": r(100 * (mm.B_lab1 - mm.A_lab1)),
                             "diff_lab2_pt": r(100 * (mm.B_lab2 - mm.A_lab2)),
                             "flip_lab1_pct": r(100 * (rr.B_lab1 < rr.A_lab1).mean()),
                             "flip_lab2_pct": r(100 * (rr.B_lab2 < rr.A_lab2).mean())})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    P = lambda t, b: pdf[(pdf.correct == t) & (pdf.rank_A.astype(str) == str(b))].iloc[0]
    headline = {
        "A_true_pct": r(100 * m.A_true), "B_true_pct": r(100 * m.B_true),
        "A_lab1_pct": r(100 * m.A_lab1), "B_lab1_pct": r(100 * m.B_lab1),
        "A_lab2_pct": r(100 * m.A_lab2), "B_lab2_pct": r(100 * m.B_lab2),
        "diff_true_pt": main_tbl.B_minus_A_pt[0], "diff_lab1_pt": main_tbl.B_minus_A_pt[1],
        "diff_lab2_pt": main_tbl.B_minus_A_pt[2],
        "reps_B_below_A_lab1_pct": main_tbl.reps_B_below_A_pct[1],
        "reps_B_below_A_lab2_pct": main_tbl.reps_B_below_A_pct[2],
        "reps_B_below_A_true_pct": main_tbl.reps_B_below_A_pct[0],
        "B_top10_docs_A_below20_pct": r(100 * m.B_top10_from_A_below20),
        "B_top10_correct_docs_A_below20_pct": r(100 * m.B_top10_rel_from_A_below20),
        "correct_rank1_lab1_pct": P(1, 1).label_click_any_pct, "correct_rank10_lab1_pct": P(1, 10).label_click_any_pct,
        "correct_rank20_lab1_pct": P(1, 20).label_click_any_pct, "correct_below20_lab1_pct": P(1, "21-40").label_click_any_pct,
        "notcorrect_rank1_lab1_pct": P(0, 1).label_click_any_pct, "notcorrect_rank3_lab1_pct": P(0, 3).label_click_any_pct,
        "notcorrect_rank10_lab1_pct": P(0, 10).label_click_any_pct,
        "correct_rank10_lab2_pct": P(1, 10).label_reweighted_pct, "correct_rank20_lab2_pct": P(1, 20).label_reweighted_pct,
        "notcorrect_rank1_lab2_pct": P(0, 1).label_reweighted_pct, "correct_rank1_lab2_pct": P(1, 1).label_reweighted_pct,
        "formula_gap_max_pt": r(gap_formula), "formula_groups_compared": int(len(pdf)),
    }
    robust = {
        "settings": 27,
        "diff_true_pt_range": [g.diff_true_pt.min(), g.diff_true_pt.max()],
        "diff_lab1_pt_range": [g.diff_lab1_pt.min(), g.diff_lab1_pt.max()],
        "diff_lab2_pt_range": [g.diff_lab2_pt.min(), g.diff_lab2_pt.max()],
        "settings_lab1_B_below_A": int((g.diff_lab1_pt < 0).sum()),
        "settings_lab2_B_below_A": int((g.diff_lab2_pt < 0).sum()),
        "settings_true_B_below_A": int((g.diff_true_pt < 0).sum()),
        "lab1_diff_by_sess": {str(s): [g[g.searches_per_query == s].diff_lab1_pt.min(), g[g.searches_per_query == s].diff_lab1_pt.max()] for s in (5, 20, 100)},
        "lab2_diff_by_sess": {str(s): [g[g.searches_per_query == s].diff_lab2_pt.min(), g[g.searches_per_query == s].diff_lab2_pt.max()] for s in (5, 20, 100)},
        "A_lab1_minus_true_pt_range": [r((g.A_lab1_pct - g.A_true_pct).min()), r((g.A_lab1_pct - g.A_true_pct).max())],
    }
    js = {"settings": {"queries": Q, "candidates": C, "correct_per_query": NREL, "shown": SHOWN, "mu_A": MU_A, "mu_B": MU_B,
                       "click_correct": CLICK_REL, "reweighted_threshold_at_base": (CLICK_REL + BASE["c_not"]) / 2, **BASE, "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
          "headline": headline, "robust": robust}
    (RES / "a1227_main.json").write_text(json.dumps(js, ensure_ascii=False, indent=1))

    # 図1：位置ごとに「正しい」と決まった割合
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    for t, col, lab in [(1, BLUE, "本当に正しい文書"), (0, ORANGE, "正しくない文書")]:
        d = pdf[pdf.correct == t]
        x = np.r_[np.arange(1, SHOWN + 1), SHOWN + 2.5]
        ax.plot(x, d.label_click_any_pct, "-o", color=col, ms=3.5, label=f"{lab}：①1回でもクリック")
        ax.plot(x, d.label_reweighted_pct, "--s", color=col, ms=3, alpha=0.7, label=f"{lab}：②見られやすさで割り戻す")
    ax.set_xticks([1, 3, 5, 10, 15, 20, SHOWN + 2.5], ["1", "3", "5", "10", "15", "20", "21位より下\n（出さない）"])
    ax.set_xlabel("今の検索 A で出した順位")
    ax.set_ylabel("「正しい」と決まった割合（%）")
    ax.set_ylim(0, 105)
    ax.set_title("A で上に出た文書ほど、①では「正しい」と決まりやすかった（200回の平均）", fontsize=12)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1227_by_rank.png", SRC, y=-0.07)

    # 図2：上位10件の正しい割合 A と B
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = np.arange(3)
    w = 0.36
    ax.bar(x - w / 2, main_tbl.A_pct, w, color=GRAY, label="今の検索 A（記録を取った側）")
    ax.bar(x + w / 2, main_tbl.B_pct, w, color=BLUE, label="新しい検索 B")
    for xi, a, b in zip(x, main_tbl.A_pct, main_tbl.B_pct):
        ax.text(xi - w / 2, a + 1, f"{a:.2f}%", ha="center", fontsize=9)
        ax.text(xi + w / 2, b + 1, f"{b:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(x, ["本当の正しさで数える", "①1回でもクリック\nを正しいとする", "②見られやすさで\n割り戻す"])
    ax.set_ylabel("上位10件の正しい割合（%）")
    ax.set_ylim(0, max(main_tbl.A_pct.max(), main_tbl.B_pct.max()) * 1.25)
    ax.set_title("同じ2つの検索でも、数え方で上下が入れかわった（200回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1227_top10_A_vs_B.png", SRC)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    cols = {5: GRAY, 20: BLUE, 100: ORANGE}
    for j, key in enumerate(["diff_true_pt", "diff_lab1_pt", "diff_lab2_pt"]):
        for i, s in enumerate((5, 20, 100)):
            v = g[g.searches_per_query == s][key].values
            xx = j + (i - 1) * 0.22 + np.linspace(-0.06, 0.06, len(v))
            ax.scatter(xx, v, s=14, color=cols[s], alpha=0.8, label=f"1語あたり{s}回検索" if j == 0 else None)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(range(3), ["本当の正しさ", "①1回でもクリック", "②見られやすさで割り戻す"])
    ax.set_ylabel("B−A（上位10件の正しい割合、ポイント）")
    ax.set_title("27通りの置き方（見られやすさの落ち方・クリックの見込み・検索回数）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1227_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(robust, ensure_ascii=False), round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
