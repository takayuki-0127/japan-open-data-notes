"""1090 カバレッジ80%のテストで、埋めこんだバグはどれだけ見つかるのか？（架空のデータ）

架空のアプリのコード（300の関数×30行＝9,000行）を置き、1つの関数は「ふだん通る行」24行と、
めったに通らない分かれ道（2行ずつ3つ、計6行）からなるとする。テストを1本ずつ足していき、
通った行の割合（カバレッジ）が50〜90%になったところで、
・作成者がわざと埋めこんだバグ（行に一様に置く）
・本当のバグ（分かれ道の行に多く入ると置く）
が、それぞれどれだけ見つかるかを数える。バグは、通った行にあっても、そのテストの入力で表に出て（表に出る確率）、
テストが結果を確かめる（確かめる確率）ときだけ見つかる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1090
SRC = "架空のアプリのコードとテストとバグ（作成者が置いた数と確率からの乱数、seed 1090）"
N_FUNC, MAIN, N_BR, BR_LEN = 300, 24, 3, 2
LINES_PER = MAIN + N_BR * BR_LEN
N_LINES = N_FUNC * LINES_PER
BASE = {"sigma_pop": 1.0, "p_branch": 0.1, "edge_weight": 4.0, "check": 0.6, "trig_beta": (1.0, 3.0),
        "n_real": 60, "n_seeded": 100}
TARGETS = [0.5, 0.6, 0.7, 0.8, 0.9]
REPS = 100
GRID_REPS = 40
T_MAX = 60000


def r(x, d=4):
    return round(float(x), d)


def make_tests(rng, p):
    """テストを T_MAX 本作り、行ごとに「何本目で初めて通ったか」を出す"""
    pop = np.exp(rng.normal(0, p["sigma_pop"], N_FUNC)); pop /= pop.sum()
    fn = rng.choice(N_FUNC, T_MAX, p=pop)
    br = rng.random((T_MAX, N_BR)) < p["p_branch"]
    return fn, br


def counts_at(fn, br, t):
    """t 本目までのテストで、行ごとに何本のテストが通ったか（9,000行）"""
    f = fn[:t]
    main_cnt = np.bincount(f, minlength=N_FUNC)
    br_cnt = np.stack([np.bincount(f[br[:t, b]], minlength=N_FUNC) for b in range(N_BR)], 1)
    n = np.zeros((N_FUNC, LINES_PER), int)
    n[:, :MAIN] = main_cnt[:, None]
    for b in range(N_BR):
        n[:, MAIN + b * BR_LEN: MAIN + (b + 1) * BR_LEN] = br_cnt[:, b][:, None]
    return n.ravel()


def tests_for_targets(fn, br, targets):
    """カバレッジが目標に届く最初のテスト本数（二分探索）"""
    out = {}
    for tg in targets:
        lo, hi = 1, T_MAX
        if (counts_at(fn, br, hi) > 0).mean() < tg:
            out[tg] = None; continue
        while lo < hi:
            mid = (lo + hi) // 2
            if (counts_at(fn, br, mid) > 0).mean() >= tg:
                hi = mid
            else:
                lo = mid + 1
        out[tg] = lo
    return out


def bugs(rng, p, n, edge_weight):
    w = np.ones((N_FUNC, LINES_PER)); w[:, MAIN:] = edge_weight
    w = w.ravel() / w.sum()
    line = rng.choice(N_LINES, n, p=w)
    trig = rng.beta(*p["trig_beta"], n)
    return line, trig


def detect(rng, n_cov, line, trig, check):
    k = n_cov[line]
    pr = 1 - (1 - trig * check) ** k
    return k > 0, rng.random(len(line)) < pr


def one_run(rng, p, targets, keep=False):
    fn, br = make_tests(rng, p)
    tt = tests_for_targets(fn, br, targets)
    real_l, real_t = bugs(rng, p, p["n_real"], p["edge_weight"])
    seed_l, seed_t = bugs(rng, p, p["n_seeded"], 1.0)
    is_edge = (np.arange(N_LINES) % LINES_PER) >= MAIN
    rows, keep_df = [], None
    for tg, t in tt.items():
        if t is None:
            continue
        n_cov = counts_at(fn, br, t)
        cov_r, fd_r = detect(rng, n_cov, real_l, real_t, p["check"])
        cov_s, fd_s = detect(rng, n_cov, seed_l, seed_t, p["check"])
        rows.append({"target": tg, "tests": t, "coverage": (n_cov > 0).mean(),
                     "main_cov": (n_cov[~is_edge] > 0).mean(), "edge_cov": (n_cov[is_edge] > 0).mean(),
                     "real_found": fd_r.mean(), "real_uncovered": (~cov_r).mean(), "real_cov_notfound": (cov_r & ~fd_r).mean(),
                     "seeded_found": fd_s.mean(), "seeded_uncovered": (~cov_s).mean(), "seeded_cov_notfound": (cov_s & ~fd_s).mean(),
                     "real_on_edge": is_edge[real_l].mean(), "seeded_on_edge": is_edge[seed_l].mean()})
        if keep and tg == 0.8:
            keep_df = pd.DataFrame({"bug": [f"R{i:02d}" for i in range(len(real_l))] + [f"S{i:03d}" for i in range(len(seed_l))],
                                    "kind": ["real"] * len(real_l) + ["seeded"] * len(seed_l),
                                    "func": np.r_[real_l, seed_l] // LINES_PER, "line_in_func": np.r_[real_l, seed_l] % LINES_PER,
                                    "on_branch": is_edge[np.r_[real_l, seed_l]].astype(int),
                                    "trigger_prob": np.round(np.r_[real_t, seed_t], 4),
                                    "tests_covering": n_cov[np.r_[real_l, seed_l]],
                                    "found": np.r_[fd_r, fd_s].astype(int)})
            keep_df.attrs["tests"] = t
    return rows, keep_df


def main():
    t0 = time.time()
    p = dict(BASE)
    allrows, one = [], None
    for rep in range(REPS):
        rr = np.random.default_rng(SEED * 1000 + rep)
        rows, kd = one_run(rr, p, TARGETS, keep=(rep == 0))
        if rep == 0:
            one = kd
        allrows += [{"rep": rep, **x} for x in rows]
    sim = pd.DataFrame(allrows)
    tab = sim.groupby("target").agg(**{c: (c, "mean") for c in sim.columns if c not in ("rep", "target")},
                                    real_found_p10=("real_found", lambda x: x.quantile(.1)), real_found_p90=("real_found", lambda x: x.quantile(.9)),
                                    seeded_found_p10=("seeded_found", lambda x: x.quantile(.1)), seeded_found_p90=("seeded_found", lambda x: x.quantile(.9))).reset_index().round(4)
    tab.to_csv(RES / "by_coverage.csv", index=False)
    b80 = tab.set_index("target").loc[0.8]

    # 確かめる確率（0.3・0.6・0.9）を変えた3つのテスト（同じ80%）
    checks = []
    for j, c in enumerate([0.3, 0.6, 0.9]):
        rs = []
        for rep in range(REPS):
            rr = np.random.default_rng(SEED * 2000 + rep)  # 同じテストとバグで、確かめる確率だけ変える
            rows, _ = one_run(rr, dict(BASE, check=c), [0.8])
            rs += rows
        d = pd.DataFrame(rs)
        checks.append({"check": c, "real_found": r(d.real_found.mean()), "seeded_found": r(d.seeded_found.mean()), "coverage": r(d.coverage.mean())})
    checks = pd.DataFrame(checks)
    checks.to_csv(RES / "by_check.csv", index=False)

    # 確かめ：分かれ道へのバグの入りやすさ×確かめる確率×表に出る確率（27通り、80%、各40回）
    grid, gi = [], 0
    for ew in [1.0, 4.0, 8.0]:
        for c in [0.3, 0.6, 0.9]:
            for tb, tname in [((1.0, 9.0), 0.1), ((1.0, 3.0), 0.25), ((1.0, 1.0), 0.5)]:
                pp = dict(BASE, edge_weight=ew, check=c, trig_beta=tb)
                rs = []
                for rep in range(GRID_REPS):
                    rows, _ = one_run(np.random.default_rng(SEED * 100000 + gi * 1000 + rep), pp, [0.8])
                    rs += rows
                d = pd.DataFrame(rs)
                grid.append({"edge_weight": ew, "check": c, "trigger_mean": tname, "real_found": r(d.real_found.mean()),
                             "seeded_found": r(d.seeded_found.mean()), "gap": r(d.seeded_found.mean() - d.real_found.mean()),
                             "real_uncovered": r(d.real_uncovered.mean()), "seeded_uncovered": r(d.seeded_uncovered.mean())})
                gi += 1
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid27.csv", index=False)

    # 確かめ：テストの偏り（関数の選ばれやすさ）と分かれ道に入る確率
    extra = []
    for k, (name, ch) in enumerate([("基本", {}), ("選ばれ方の偏り 0.5", {"sigma_pop": 0.5}), ("選ばれ方の偏り 1.5", {"sigma_pop": 1.5}),
                                    ("分かれ道に入る 0.05", {"p_branch": 0.05}), ("分かれ道に入る 0.2", {"p_branch": 0.2})]):
        rs = []
        for rep in range(GRID_REPS):
            rows, _ = one_run(np.random.default_rng(SEED * 7 + k * 1000 + rep), dict(BASE, **ch), [0.8])
            rs += rows
        d = pd.DataFrame(rs)
        extra.append({"setting": name, "tests": r(d.tests.mean(), 1), "main_cov": r(d.main_cov.mean()), "edge_cov": r(d.edge_cov.mean()),
                      "real_found": r(d.real_found.mean()), "seeded_found": r(d.seeded_found.mean()),
                      "gap": r(d.seeded_found.mean() - d.real_found.mean())})
    extra = pd.DataFrame(extra)
    extra.to_csv(RES / "extra.csv", index=False)

    one.to_csv(DATA / "bugs_one_run_cov80.csv", index=False)
    rep0 = sim[(sim.rep == 0) & (sim.target == 0.8)].iloc[0]
    tb_mean = BASE["trig_beta"][0] / sum(BASE["trig_beta"])
    out = {"settings": {**{k: (list(v) if isinstance(v, tuple) else v) for k, v in BASE.items()}, "functions": N_FUNC, "lines": N_LINES,
                        "main_lines_per_func": MAIN, "branch_lines_per_func": N_BR * BR_LEN, "targets": TARGETS, "reps": REPS,
                        "grid_reps": GRID_REPS, "seed": SEED},
           "formula": {"edge_share_lines": r(N_BR * BR_LEN / LINES_PER), "real_on_edge_expected": r(N_BR * BR_LEN * BASE["edge_weight"] / (MAIN + N_BR * BR_LEN * BASE["edge_weight"])),
                       "trigger_mean": r(tb_mean), "one_test_find_if_covered": r(tb_mean * BASE["check"]),
                       "naive_cov80_x_one_test": r(0.8 * tb_mean * BASE["check"])},
           "by_coverage": tab.to_dict("records"),
           "cov80": {**{k: float(v) for k, v in b80.items()}, "gap_seeded_minus_real": r(b80.seeded_found - b80.real_found),
                     "real_found_given_covered": r(b80.real_found / (1 - b80.real_uncovered)),
                     "seeded_found_given_covered": r(b80.seeded_found / (1 - b80.seeded_uncovered))},
           "by_check": checks.to_dict("records"),
           "grid27_ranges": {k: [r(grid[k].min()), r(grid[k].max())] for k in ["real_found", "seeded_found", "gap", "real_uncovered", "seeded_uncovered"]},
           "grid27_gap_positive": int((grid.gap > 0).sum()),
           "grid27_edge1_gap_range": [r(grid[grid.edge_weight == 1].gap.min()), r(grid[grid.edge_weight == 1].gap.max())],
           "grid27_edge4_8_gap_range": [r(grid[grid.edge_weight > 1].gap.min()), r(grid[grid.edge_weight > 1].gap.max())],
           "extra": extra.to_dict("records"),
           "data_check": {"tests_rep0_cov80": int(one.attrs["tests"]), "sim_rep0_tests": int(rep0.tests),
                          "data_real_found": r(one[one.kind == "real"].found.mean()), "sim_rep0_real_found": r(rep0.real_found),
                          "data_seeded_found": r(one[one.kind == "seeded"].found.mean()), "sim_rep0_seeded_found": r(rep0.seeded_found)}}
    json.dump(out, open(RES / "a1090_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：カバレッジと見つかった割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    xs = tab.target * 100
    ax.plot(xs, tab.coverage * 100, color=GRAY, ls="--", lw=1.2, label="カバレッジ（通った行の割合）")
    ax.plot(xs, tab.seeded_found * 100, color=BLUE, marker="o", lw=1.8, label="埋めこんだバグ（行に一様）")
    ax.plot(xs, tab.real_found * 100, color=ORANGE, marker="s", lw=1.8, label="本当のバグ（分かれ道に多い）")
    for xx, a, b in zip(xs, tab.seeded_found * 100, tab.real_found * 100):
        ax.text(xx, a + 2.5, f"{round(a, 2):g}", ha="center", fontsize=8, color=BLUE)
        ax.text(xx, b - 3.5, f"{round(b, 2):g}", ha="center", va="top", fontsize=8, color=ORANGE)
    ax.set_xlim(45, 95); ax.set_ylim(0, 100); ax.set_xlabel("テストのカバレッジ（%）")
    ax.set_ylabel("見つかったバグの割合（%、100回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"カバレッジ80%で見つかったのは、埋めこんだバグの{b80.seeded_found * 100:.2f}%、\n分かれ道に多い本当のバグの{b80.real_found * 100:.2f}%", fontsize=11.5)
    save(fig, "a1090_coverage.png", SRC, y=-0.03)

    # 図2：80%のときの内訳（通らなかった・通ったが見つからない・見つかった）
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    cats = [("seeded", "埋めこんだバグ"), ("real", "本当のバグ")]
    for i, (k, nm) in enumerate(cats):
        parts = [b80[f"{k}_found"], b80[f"{k}_cov_notfound"], b80[f"{k}_uncovered"]]
        left = 0
        for v, col, lab in zip(parts, [GREEN, LIGHT, GRAY], ["見つかった", "行は通ったが見つからない", "行を通らなかった"]):
            ax.barh(i, v * 100, left=left, color=col, label=lab if i == 0 else None, height=0.55)
            ax.text(left + v * 50, i, f"{round(v * 100, 2):g}%", ha="center", va="center", fontsize=9)
            left += v * 100
    ax.set_yticks([0, 1]); ax.set_yticklabels([c[1] for c in cats]); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xlabel("バグの割合（%、カバレッジ80%、100回の平均）")
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    ax.set_title("カバレッジ80%のときの内訳", fontsize=12, pad=26)
    save(fig, "a1090_breakdown.png", SRC, y=-0.05)

    # 図3：27通り（80%）の埋めこんだバグと本当のバグ
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    mk = {1.0: "o", 4.0: "s", 8.0: "^"}
    cl = {0.3: GRAY, 0.6: BLUE, 0.9: ORANGE}
    for _, g in grid.iterrows():
        ax.scatter(g.seeded_found * 100, g.real_found * 100, marker=mk[g.edge_weight], color=cl[g.check], s=40, zorder=3)
    ax.plot([0, 100], [0, 100], color=INK, lw=0.8, ls=":")
    ax.text(70, 74, "同じ割合の線", fontsize=8.5, rotation=40)
    for ew, m in mk.items():
        ax.scatter([], [], marker=m, color=INK, label=f"分かれ道のバグの入りやすさ ×{ew:g}")
    for c, col in cl.items():
        ax.scatter([], [], marker="o", color=col, label=f"確かめる確率 {c}")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel("埋めこんだバグの見つかった割合（%）"); ax.set_ylabel("本当のバグの見つかった割合（%）")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("カバレッジ80%・置き方27通り（各40回）：分かれ道にバグが多いと置くと、\n本当のバグの見つかる割合は埋めこんだバグより低い", fontsize=11)
    save(fig, "a1090_robust.png", SRC, y=-0.03)

    print(json.dumps({k: out[k] for k in ["formula", "cov80", "by_check", "grid27_ranges", "grid27_gap_positive", "grid27_edge1_gap_range", "grid27_edge4_8_gap_range", "data_check"]}, ensure_ascii=False, indent=1))
    print(tab.T.to_string()); print(grid.to_string()); print(extra.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
