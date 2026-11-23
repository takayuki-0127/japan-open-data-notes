"""1055 平均・中央値・最小値のどれで比べるかで、速い方は入れかわるのか？（架空のデータ）

架空のアプリの処理 A・B。処理時間（ミリ秒）は作成者が置いた分布からの乱数で、実機では測っていない。
A：ふだんの時間（中央値100、ばらつき σ_A＝0.08 の対数正規）＋まれな大きな遅れ（確率 p＝8%、平均200の指数分布）
B：ふだんの時間（中央値110、ばらつき σ_B＝0.15 の対数正規）、まれな遅れなし
平均・中央値・最小値の3つで、本当の値（大きな乱数で数える）と、n 回ずつ測ったときに選ばれる方を数える。
比べるための対照：B を「A をそのまま5%遅くしたもの」（形が同じ）にした場合。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1055
SRC = "架空のアプリの処理時間（作成者が置いた分布からの乱数、seed 1055）"
BASE = {"p": 0.08, "stall": 200.0, "sigma_b": 0.15}
MED_A, SIG_A, MED_B = 100.0, 0.08, 110.0
NS = [3, 5, 10, 30, 100]
REPS = 20000
STATS = ["mean", "median", "min"]
JP = {"mean": "平均", "median": "中央値", "min": "最小値"}
r = lambda x, k=4: round(float(x), k)


def gen_a(rng, shape, p, stall):
    base = MED_A * np.exp(SIG_A * rng.standard_normal(shape))
    return base + np.where(rng.random(shape) < p, rng.exponential(stall, shape), 0.0)


def gen_b(rng, shape, sigma_b):
    return MED_B * np.exp(sigma_b * rng.standard_normal(shape))


def stat(x, s):
    return {"mean": x.mean(-1), "median": np.median(x, -1), "min": x.min(-1)}[s]


def truths(rng, p, stall, sigma_b, ns=NS):
    a = gen_a(rng, 2_000_000, p, stall)
    b = gen_b(rng, 2_000_000, sigma_b)
    t = {"mean_A": a.mean(), "mean_B": b.mean(), "median_A": np.median(a), "median_B": np.median(b)}
    for n in ns:  # 最小値は n 回の最小の期待値（n で変わる）
        t[f"min{n}_A"] = gen_a(rng, (100000, n), p, stall).min(1).mean()
        t[f"min{n}_B"] = gen_b(rng, (100000, n), sigma_b).min(1).mean()
    return t


def measured(rng, n, p, stall, sigma_b, control=False):
    a = gen_a(rng, (REPS, n), p, stall)
    b = gen_a(rng, (REPS, n), p, stall) * 1.05 if control else gen_b(rng, (REPS, n), sigma_b)
    picks = {s: stat(a, s) < stat(b, s) for s in STATS}  # True: A を速いと選ぶ
    allsame = (picks["mean"] == picks["median"]) & (picks["median"] == picks["min"])
    return {"pick_A_" + s: picks[s].mean() * 100 for s in STATS} | {
        "disagree_pct": (~allsame).mean() * 100,
        "mean_vs_median_differ_pct": (picks["mean"] != picks["median"]).mean() * 100}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    p, stall, sb = BASE["p"], BASE["stall"], BASE["sigma_b"]

    # データ：基本の置き方で A・B を300回ずつ
    a300, b300 = gen_a(rng, 300, p, stall), gen_b(rng, 300, sb)
    pd.DataFrame({"run": np.arange(1, 301), "A_ms": a300.round(3), "B_ms": b300.round(3)}).to_csv(
        DATA / "runs_a_b_300.csv", index=False)

    # 1) 本当の値
    t = truths(np.random.default_rng(SEED * 3), p, stall, sb)
    true_rows = [{"stat": "平均", "A_ms": r(t["mean_A"], 2), "B_ms": r(t["mean_B"], 2)},
                 {"stat": "中央値", "A_ms": r(t["median_A"], 2), "B_ms": r(t["median_B"], 2)}]
    for n in NS:
        true_rows.append({"stat": f"{n}回の最小値の期待値", "A_ms": r(t[f"min{n}_A"], 2), "B_ms": r(t[f"min{n}_B"], 2)})
    tt = pd.DataFrame(true_rows)
    tt["faster"] = np.where(tt.A_ms < tt.B_ms, "A", "B")
    tt["B_vs_A_pct"] = ((tt.B_ms / tt.A_ms - 1) * 100).round(2)
    tt.to_csv(RES / "true_values.csv", index=False)
    true_mean_formula_a = MED_A * np.exp(SIG_A ** 2 / 2) + p * stall
    true_mean_formula_b = MED_B * np.exp(sb ** 2 / 2)

    # 2) n 回ずつ測ったとき（基本と対照）
    rows = []
    for n in NS:
        m = measured(np.random.default_rng(SEED * 10 + n), n, p, stall, sb)
        c = measured(np.random.default_rng(SEED * 20 + n), n, p, stall, sb, control=True)
        rows.append({"n_each": n, **{k: r(v, 2) for k, v in m.items()},
                     **{"control_" + k: r(v, 2) for k, v in c.items()}})
    bm = pd.DataFrame(rows)
    bm.to_csv(RES / "measured_by_n.csv", index=False)

    # 3) 確かめ：p × 遅れの大きさ × σ_B の36通り（測るのは30回ずつ）
    grid = []
    gi = 0
    for pg in [0.02, 0.04, 0.08, 0.16]:
        for st in [100.0, 200.0, 400.0]:
            for sg in [0.10, 0.15, 0.25]:
                gi += 1
                tg = truths(np.random.default_rng(SEED * 100 + gi), pg, st, sg, ns=[30])
                mg = measured(np.random.default_rng(SEED * 1000 + gi), 30, pg, st, sg)
                fm = "A" if tg["mean_A"] < tg["mean_B"] else "B"
                fd = "A" if tg["median_A"] < tg["median_B"] else "B"
                fn = "A" if tg["min30_A"] < tg["min30_B"] else "B"
                grid.append({"p": pg, "stall_ms": st, "sigma_b": sg, "true_mean_faster": fm,
                             "true_median_faster": fd, "true_min30_faster": fn,
                             "true_all_same": fm == fd == fn, **{k: r(v, 2) for k, v in mg.items()}})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    b30 = bm.set_index("n_each").loc[30]
    out = {
        "settings": {"A": {"median_ms": MED_A, "sigma": SIG_A, "p_stall": p, "stall_mean_ms": stall},
                     "B": {"median_ms": MED_B, "sigma": sb}, "reps": REPS, "control": "B=A×1.05"},
        "headline": {
            "true_mean_A_ms": r(t["mean_A"], 2), "true_mean_B_ms": r(t["mean_B"], 2),
            "formula_mean_A_ms": r(true_mean_formula_a, 2), "formula_mean_B_ms": r(true_mean_formula_b, 2),
            "true_median_A_ms": r(t["median_A"], 2), "true_median_B_ms": r(t["median_B"], 2),
            "true_min_faster_by_n": {str(n): ("A" if t[f"min{n}_A"] < t[f"min{n}_B"] else "B") for n in NS},
            "n30_pick_A_pct": {s: float(b30["pick_A_" + s]) for s in STATS},
            "n30_disagree_pct": float(b30["disagree_pct"]),
            "n30_pick_B_by_mean_pct": r(100 - float(b30["pick_A_mean"]), 2),
            "n30_control_disagree_pct": float(b30["control_disagree_pct"]),
            "data_A_over_600ms_count": int((a300 >= 600).sum()), "data_A_max_ms": r(a300.max(), 2),
            "n100_disagree_pct": float(bm.set_index("n_each").loc[100, "disagree_pct"]),
            "n100_pick_A_pct": {s: float(bm.set_index("n_each").loc[100, "pick_A_" + s]) for s in STATS},
        },
        "true_values": tt.to_dict("records"),
        "measured_by_n": bm.to_dict("records"),
        "grid_summary": {
            "n": int(len(g)),
            "true_all_same_count": int(g.true_all_same.sum()),
            "true_median_A_count": int((g.true_median_faster == "A").sum()),
            "true_mean_A_count": int((g.true_mean_faster == "A").sum()),
            "true_mean_median_differ_count": int((g.true_mean_faster != g.true_median_faster).sum()),
            "true_min30_differs_from_median_count": int((g.true_min30_faster != g.true_median_faster).sum()),
            "disagree_n30_min_pct": r(g.disagree_pct.min(), 2), "disagree_n30_max_pct": r(g.disagree_pct.max(), 2),
            "disagree_n30_when_true_same": [r(g[g.true_all_same].disagree_pct.min(), 2),
                                            r(g[g.true_all_same].disagree_pct.max(), 2)] if g.true_all_same.any() else None,
            "disagree_n30_when_true_differ": [r(g[~g.true_all_same].disagree_pct.min(), 2),
                                              r(g[~g.true_all_same].disagree_pct.max(), 2)],
            "median_pick_A_min_pct": r(g.pick_A_median.min(), 2),
            "mean_pick_A_range_pct": [r(g.pick_A_mean.min(), 2), r(g.pick_A_mean.max(), 2)],
        },
    }
    json.dump(out, open(RES / "a1055_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：A・B の分布（300回ずつ）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.linspace(50, 605, 112)
    ax.hist(np.minimum(a300, 600), bins=bins, color=ORANGE, alpha=.55, label="A（ふだん速い・まれに大きく遅れる）")
    ax.hist(b300, bins=bins, color=BLUE, alpha=.55, label="B（まれな遅れなし・ばらつき大きめ）")
    ax.set_xlabel("1回の処理時間（ミリ秒）"); ax.set_ylabel("回数（300回ずつ）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_xticks([100, 200, 300, 400, 500, 600]); ax.set_xticklabels(["100", "200", "300", "400", "500", "600以上"])
    ax.set_title(f"A は山が左にあるが、右に長いすそがある（A の{int((a300 >= 600).sum())}回は600ミリ秒以上）", fontsize=12)
    save(fig, "a1055_distribution.png", SRC)

    # 図2：本当の値（平均・中央値・最小値の期待値）
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    y = np.arange(len(tt))
    ax.barh(y - .2, tt.A_ms, .4, color=ORANGE, label="A")
    ax.barh(y + .2, tt.B_ms, .4, color=BLUE, label="B")
    for i, row in tt.iterrows():
        ax.text(max(row.A_ms, row.B_ms) + 2, i, f"速いのは{row.faster}", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(tt.stat, fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, 150); ax.set_xlabel("本当の値（ミリ秒）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("平均ではB、中央値ではA。最小値は何回測るかで入れかわる", fontsize=12)
    save(fig, "a1055_true_values.png", SRC)

    # 図3：n 回ずつ測ったとき、それぞれの物差しで A を選んだ割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for s, col, mk in [("mean", BLUE, "o"), ("median", ORANGE, "s"), ("min", GREEN, "D")]:
        ax.plot(bm.n_each, bm["pick_A_" + s], mk + "-", color=col, lw=2, label=f"{JP[s]}で比べる")
    ax.plot(bm.n_each, bm.disagree_pct, "--", color=GRAY, lw=1.5, label="3つの答えがそろわない組")
    ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([str(n) for n in NS])
    ax.set_ylim(0, 100); ax.set_xlabel("A・B を何回ずつ測ったか（対数の目盛り）"); ax.set_ylabel("A を速いと選んだ割合（実線、%）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("測る回数を増やすと、物差しごとの答えが割れたまま固まる（2万組）", fontsize=12)
    save(fig, "a1055_by_n.png", SRC)

    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1))
    print(tt.to_string()); print(bm.to_string()); print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
