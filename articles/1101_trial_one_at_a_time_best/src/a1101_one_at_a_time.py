"""1101 条件を1つずつ変える試し方で、いちばん良い組み合わせは見つかるのか？（架空のデータ）

架空の塗りの工房で、3つの条件（乾かす温度・塗料の薄め方・刷毛を動かす速さ、どれも3段階）の27通りの組み合わせに
「本当の仕上がりの点数」（塗りのむらの少なさを機械で測った点数、高いほど良い）を作成者が置く。
工房ごとに、1つずつの効き目・曲がり・2つの条件の組み合わせの効き目を乱数で置き、
「いつもの条件から1つずつ変えて、良かった段階に決めて次へ」の試し方と、27通りを全部試す試し方で、
本当にいちばん良い組み合わせに着く割合と、着いた所の本当の点数の不足を数える。
"""
import json
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1101
SRC = "架空の塗りの工房の仕上がりの点数（作成者が置いた効き目からの乱数、seed 1101）"
FACT = ["乾かす温度", "塗料の薄め方", "刷毛の速さ"]
X = np.array(list(itertools.product([-1, 0, 1], repeat=3)))          # 27通り
IDX = {tuple(x): i for i, x in enumerate(X)}
BASE = {"main_sd": 2.0, "quad_mean": -0.5, "quad_sd": 1.0, "inter_sd": 2.0, "noise_sd": 1.5, "level": 70.0}
W_BASE = 4000
W_GRID = 1000
METHODS = {"ofat1": "①1つずつ1周（7条件×4回）", "ofat2": "②1つずつ2周（2回ずつ）",
           "full": "③27通りを1回ずつ、いちばん良かった所", "fit": "④27通りを1回ずつ、式を当てはめて選ぶ"}
PAIRS = [(0, 1), (0, 2), (1, 2)]


def r(x, d=4):
    return round(float(x), d)


def design(Xm):
    cols = [np.ones(len(Xm))] + [Xm[:, i] for i in range(3)] + [Xm[:, i] ** 2 for i in range(3)] + [Xm[:, i] * Xm[:, j] for i, j in PAIRS]
    return np.column_stack(cols)


D = design(X)
PINV = np.linalg.pinv(D)


def true_scores(rng, W, inter_sd, three_sd=0.0):
    m = BASE["main_sd"] * rng.standard_normal((W, 3))
    q = BASE["quad_mean"] + BASE["quad_sd"] * rng.standard_normal((W, 3))
    g = inter_sd * rng.standard_normal((W, 3))
    beta = np.column_stack([np.full(W, BASE["level"]), m, q, g])         # W×10
    F = beta @ D.T                                                         # W×27
    if three_sd > 0:                                                       # 3つの条件がそろったときだけの効き目（当てはめる式に入れていない）
        F = F + (three_sd * rng.standard_normal(W))[:, None] * (X[:, 0] * X[:, 1] * X[:, 2])[None, :]
    return F


def ofat(obs, start, order=(0, 1, 2), rounds=1):
    """obs: W×27 の測った平均（同じ条件は1度だけ測り、戻ったときは同じ値を使う）。返り値：着いた所・試した条件の数"""
    W = obs.shape[0]
    cur = np.tile(np.array(start), (W, 1))
    tried = np.zeros((W, 27), bool)
    tried[np.arange(W), [IDX[tuple(start)]] * W] = True
    for _ in range(rounds):
        for k in order:
            cand = []
            for lv in (-1, 0, 1):
                c = cur.copy(); c[:, k] = lv
                ci = c[:, 0] * 9 + c[:, 1] * 3 + c[:, 2] + 13                # (-1,-1,-1)→0
                cand.append(ci)
            cand = np.column_stack(cand)                                    # W×3
            tried[np.arange(W)[:, None], cand] = True
            best = obs[np.arange(W)[:, None], cand].argmax(1)
            cur[:, k] = np.array([-1, 0, 1])[best]
    end = cur[:, 0] * 9 + cur[:, 1] * 3 + cur[:, 2] + 13
    return end, tried.sum(1)


def run(rng, W, inter_sd, noise_sd, start, three_sd=0.0):
    F = true_scores(rng, W, inter_sd, three_sd)
    best = F.argmax(1); fbest = F.max(1)
    o4 = F + noise_sd / 2 * rng.standard_normal(F.shape)                   # 4回の平均
    o2 = F + noise_sd / np.sqrt(2) * rng.standard_normal(F.shape)          # 2回の平均
    o1 = F + noise_sd * rng.standard_normal(F.shape)                       # 1回
    e1, n1 = ofat(o4, start, rounds=1)
    e2, n2 = ofat(o2, start, rounds=2)
    e3 = o1.argmax(1)
    pred = (PINV @ o1.T).T @ D.T
    e4 = pred.argmax(1)
    e0, _ = ofat(F, start, rounds=1)                                       # 測り誤差なしの1周
    e0r, _ = ofat(F, start, order=(2, 1, 0), rounds=1)                     # 順番を逆にした1周（誤差なし）
    out = {}
    W_ = np.arange(W)
    for key, e, runs in [("ofat1", e1, n1 * 4), ("ofat2", e2, n2 * 2), ("full", e3, np.full(W, 27)), ("fit", e4, np.full(W, 27))]:
        short = fbest - F[W_, e]
        out[key] = {"p_best": r(100 * np.mean(e == best), 2), "short_mean": r(short.mean(), 3), "short_median": r(np.median(short), 3),
                    "short_p90": r(np.quantile(short, 0.9), 3), "p_within1": r(100 * np.mean(short <= 1), 2), "runs_mean": r(runs.mean(), 2),
                    "short_bins": [r(100 * np.mean(short == 0), 2), r(100 * np.mean((short > 0) & (short <= 1)), 2),
                                   r(100 * np.mean((short > 1) & (short <= 3)), 2), r(100 * np.mean((short > 3) & (short <= 6)), 2),
                                   r(100 * np.mean(short > 6), 2)]}
    short0 = fbest - F[W_, e0]
    out["ofat_noisefree"] = {"p_best": r(100 * np.mean(e0 == best), 2), "short_mean": r(short0.mean(), 3),
                             "p_best_rev": r(100 * np.mean(e0r == best), 2), "p_diff_end_by_order": r(100 * np.mean(e0 != e0r), 2)}
    # 本当にいちばん良い所が、いつもの条件から何個の条件を変えた所か
    nchg = (X[best] != np.array(start)).sum(1)
    out["best_n_changed"] = {}
    for k in range(4):
        sel = nchg == k
        out["best_n_changed"][str(k)] = {"share": r(100 * np.mean(sel), 2),
                                         "p_best_ofat_noisefree": r(100 * np.mean(e0[sel] == best[sel]), 2) if sel.any() else None}
    return out, F, o1, o4, e1, best


def main():
    rng = np.random.default_rng(SEED)
    base, F, o1, o4, e1, best = run(rng, W_BASE, BASE["inter_sd"], BASE["noise_sd"], (0, 0, 0))
    rows = [{"method": METHODS[k], **{kk: v for kk, v in base[k].items() if kk != "short_bins"}} for k in METHODS]
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "methods_base.csv", index=False)

    grid = []
    for inter_sd in [0.0, 1.0, 2.0, 4.0]:
        for noise_sd in [0.0, 1.5, 3.0]:
            for sname, start in [("center", (0, 0, 0)), ("corner", (-1, -1, -1))]:
                o, *_ = run(rng, W_GRID, inter_sd, noise_sd, start)
                row = {"inter_sd": inter_sd, "noise_sd": noise_sd, "start": sname}
                for k in METHODS:
                    row[f"{k}_p_best"] = o[k]["p_best"]; row[f"{k}_short_mean"] = o[k]["short_mean"]
                row["ofat_noisefree_p_best"] = o["ofat_noisefree"]["p_best"]
                row["order_diff_end"] = o["ofat_noisefree"]["p_diff_end_by_order"]
                grid.append(row)
    grid = pd.DataFrame(grid)
    # 当てはめる式に入れていない効き目（3つの条件がそろったときだけの効き目）を足した確かめ
    three = {}
    for t in [2.0, 4.0]:
        o, *_ = run(rng, W_BASE, BASE["inter_sd"], BASE["noise_sd"], (0, 0, 0), three_sd=t)
        three[str(t)] = {k: {"p_best": o[k]["p_best"], "short_mean": o[k]["short_mean"]} for k in METHODS}
    grid.to_csv(RES / "grid.csv", index=False)

    # 1つの工房の例（1軒目）
    one = pd.DataFrame({FACT[0]: X[:, 0], FACT[1]: X[:, 1], FACT[2]: X[:, 2], "true_score": np.round(F[0], 3),
                        "observed_1run": np.round(o1[0], 3), "observed_4run_mean": np.round(o4[0], 3)})
    one.columns = ["temp", "dilution", "brush_speed", "true_score", "observed_1run", "observed_4run_mean"]
    one.to_csv(DATA / "one_workshop_27.csv", index=False)

    g0 = grid[grid.inter_sd == 0]
    gi = grid[grid.inter_sd > 0]
    out = {"base": base, "setting": BASE, "three_way_check": three, "workshops_base": W_BASE, "workshops_grid": W_GRID,
           "one_workshop": {"true_best_index": int(best[0]), "ofat1_end_index": int(e1[0])},
           "grid_ofat1_p_best_range": [r(grid.ofat1_p_best.min(), 2), r(grid.ofat1_p_best.max(), 2)],
           "grid_full_p_best_range": [r(grid.full_p_best.min(), 2), r(grid.full_p_best.max(), 2)],
           "grid_fit_p_best_range": [r(grid.fit_p_best.min(), 2), r(grid.fit_p_best.max(), 2)],
           "grid_noisefree_p_best_inter0": [r(g0.ofat_noisefree_p_best.min(), 2), r(g0.ofat_noisefree_p_best.max(), 2)],
           "grid_noisefree_p_best_inter_pos": [r(gi.ofat_noisefree_p_best.min(), 2), r(gi.ofat_noisefree_p_best.max(), 2)],
           "grid_ofat1_short_mean_range": [r(grid.ofat1_short_mean.min(), 3), r(grid.ofat1_short_mean.max(), 3)],
           "grid_fit_short_mean_range": [r(grid.fit_short_mean.min(), 3), r(grid.fit_short_mean.max(), 3)],
           "grid_n_fit_beats_ofat1_p_best": int((grid.fit_p_best > grid.ofat1_p_best).sum()),
           "grid_n_ofat1_beats_fit_p_best": int((grid.ofat1_p_best > grid.fit_p_best).sum()),
           "grid_n_ofat1_beats_full_p_best": int((grid.ofat1_p_best > grid.full_p_best).sum()),
           "grid_n_noise_pos": int((grid.noise_sd > 0).sum()),
           "grid_inter0_ofat1_minus_fit_p_best": [r((g0.ofat1_p_best - g0.fit_p_best).min(), 2), r((g0.ofat1_p_best - g0.fit_p_best).max(), 2)],
           "grid_n_cases": int(len(grid))}
    for s in ["center", "corner"]:
        gs = grid[(grid.start == s) & (grid.noise_sd == 0)]
        out[f"grid_noisefree_{s}_by_inter"] = {str(a): r(b, 2) for a, b in zip(gs.inter_sd, gs.ofat_noisefree_p_best)}
    json.dump(out, open(RES / "a1101_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：方法ごとのいちばん良い所に着いた割合
    fig, ax = plt.subplots(figsize=(8, 4.2))
    keys = list(METHODS)
    vals = [base[k]["p_best"] for k in keys]
    cols = [ORANGE, ORANGE, BLUE, BLUE]
    ax.barh(range(4)[::-1], vals, color=cols)
    for i, (k, v) in enumerate(zip(keys, vals)):
        ax.text(v + 1, 3 - i, f"{v}%（平均{base[k]['runs_mean']}回）", va="center", fontsize=10)
    ax.set_yticks(range(4)[::-1]); ax.set_yticklabels([METHODS[k] for k in keys])
    ax.set_xlim(0, 100); ax.set_xlabel("本当にいちばん良い組み合わせに着いた工房の割合（%）")
    ax.set_title("基本の置き方（4,000軒）：1つずつ変える試し方は、いちばん良い所に着きにくかった", loc="left", fontsize=11.5)
    save(fig, "a1101_methods.png", SRC, y=-0.04)

    # 図2：組み合わせの効き目の強さで、着く割合がどう変わるか（いつもの条件から始める）
    fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True)
    for ax, ns in zip(axes, [0.0, 1.5, 3.0]):
        gg = grid[(grid.start == "center") & (grid.noise_sd == ns)]
        for k, c, mk in [("ofat1", ORANGE, "o"), ("ofat2", "#b8471b", "s"), ("full", LIGHT, "^"), ("fit", BLUE, "D")]:
            ax.plot(gg.inter_sd, gg[f"{k}_p_best"], color=c, marker=mk, label=METHODS[k])
        ax.set_title(f"1回の測りの誤差 {ns}点", fontsize=11)
        ax.set_xticks([0, 1, 2, 4]); ax.set_xlabel("組み合わせの効き目の大きさ（標準偏差）")
        ax.set_ylim(0, 102); ax.grid(axis="y", color="#eeeeee")
    axes[0].set_ylabel("いちばん良い所に着いた割合（%）")
    axes[0].legend(fontsize=8, loc="lower left")
    fig.suptitle("組み合わせの効き目が0なら、誤差のない1つずつの試し方は100%着く（作りどおり）", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "a1101_grid.png", SRC, y=-0.03)

    # 図3：着いた所の本当の点数の不足の分かれ方
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    labels = ["0点（いちばん良い所）", "0〜1点", "1〜3点", "3〜6点", "6点より多い"]
    left = np.zeros(4)
    colors = [BLUE, LIGHT, "#e6e4dc", "#f2b38f", ORANGE]
    for j, (lab, c) in enumerate(zip(labels, colors)):
        v = np.array([base[k]["short_bins"][j] for k in keys])
        ax.barh(range(4)[::-1], v, left=left, color=c, label=lab, edgecolor="white")
        for i in range(4):
            if v[i] >= 6:
                ax.text(left[i] + v[i] / 2, 3 - i, f"{v[i]:g}", ha="center", va="center", fontsize=8.5, color=INK)
        left += v
    ax.set_yticks(range(4)[::-1]); ax.set_yticklabels([METHODS[k] for k in keys])
    ax.set_xlim(0, 100); ax.set_xlabel("工房の割合（%）")
    ax.legend(ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.4, -0.15), frameon=False, title="着いた所の本当の点数が、いちばん良い所より何点低いか", title_fontsize=8.5)
    ax.set_title("基本の置き方：着いた所の本当の点数の不足", loc="left", fontsize=12)
    save(fig, "a1101_shortfall.png", SRC, y=-0.2)

    print(tab.to_string()); print(json.dumps({k: v for k, v in out.items() if k != "base"}, ensure_ascii=False, indent=1))
    print(json.dumps(base["ofat_noisefree"], ensure_ascii=False), json.dumps(base["best_n_changed"], ensure_ascii=False))
    print(grid.to_string())


if __name__ == "__main__":
    main()
