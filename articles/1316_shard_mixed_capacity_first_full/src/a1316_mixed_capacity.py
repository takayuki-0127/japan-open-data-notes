"""1316 容量の大きい台と小さい台がまざるとき、件数で均等に振り分けると、全体の何割が埋まった時点で最初の1台がいっぱいになるのか？（架空のデータ）

作成者が置いた架空のアプリの保存データ。台は10台で、大きい台5台（容量200GB）と小さい台5台（容量100GB）。
データは1件ずつ増え、1件の大きさは平均10MB・右に長い乱数（対数で正規、対数のばらつき1.0）。1GB＝1,000MB。
1件ごとに置く台を決める。振り分け方は3つ：
  ①件数で均等（でたらめ）：どの台にも同じ確率で、乱数で決める
  ②件数で均等（順番）：台0・台1・…と順番に回す（件数はぴったりそろう）
  ③容量に比例：容量に比例した確率で、乱数で決める（比べるための参考）
ある台に次の1件が入らなくなった時点を「最初の1台がいっぱい」とし、そのときの全体の埋まり具合（使った量の合計÷容量の合計）を数える。
(1) 基本：300回
(2) 確かめ：大きい台÷小さい台の容量の比 1・1.5・2・4 × 大きい台の数 2・5・8（10台のうち）× 小さい台の容量 10GB・100GB・1,000GB（10GB・100GBは各40回、1,000GBは各10回）
件数で均等なら、小さい台が平均で満杯になるのは全体が「台の数×小さい台の容量÷容量の合計」のとき（式どおりの見込み。基本で66.67%）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1316
SRC = "架空のアプリの保存データの振り分け（作成者が置いた台の容量・1件の大きさからの乱数、seed 1316）"
N = 10
MEAN_MB, SIG = 10.0, 1.0
MU = np.log(MEAN_MB) - SIG ** 2 / 2
REPS, GRID_REPS = 300, {10: 40, 100: 40, 1000: 10}
METHODS = {"rand_equal": "①件数で均等（でたらめ）", "round": "②件数で均等（順番）", "rand_cap": "③容量に比例（参考）"}


def r(x, d=4):
    return round(float(x), d)


def caps_of(n_large, ratio, small_gb):
    return np.array([small_gb * ratio * 1000] * n_large + [small_gb * 1000] * (N - n_large), dtype=float)  # MB


def first_full(method, rng, caps):
    """最初の1台に次の1件が入らなくなった時点の、全体の埋まり具合と、その台の番号"""
    total = caps.sum()
    reach = total if method == "rand_cap" else N * caps.min()  # 満杯になるまでに要る量のおおよそ
    n_items = int(reach / MEAN_MB * 1.3) + 1000
    size = rng.lognormal(MU, SIG, n_items)
    if method == "rand_equal":
        a = rng.integers(0, N, n_items)
    elif method == "round":
        a = np.arange(n_items) % N
    else:
        a = rng.choice(N, n_items, p=caps / total)
    best_t, best_j = n_items, -1  # 見込みの1.3倍までに満杯にならなければ止まる（下で確かめる）
    for j in range(N):
        idx = np.flatnonzero(a == j)
        cs = np.cumsum(size[idx])
        k = np.searchsorted(cs, caps[j], side="right")  # 入らなくなる1件目
        if k < len(idx) and idx[k] < best_t:
            best_t, best_j = idx[k], j
    assert best_j >= 0, "満杯になる前に件が尽きた"
    used = size[:best_t].sum()
    return used / total, best_j, best_t


def run(method, caps, reps, seed_key):
    fills, js = [], []
    for rep in range(reps):
        f, j, _ = first_full(method, np.random.default_rng(seed_key + [rep]), caps)
        fills.append(f); js.append(j)
    return np.array(fills), np.array(js)


def stats(fills, js, caps):
    small = caps.min()
    return {"fill_mean_pct": r(fills.mean() * 100, 2), "fill_p5_pct": r(np.quantile(fills, .05) * 100, 2),
            "fill_p95_pct": r(np.quantile(fills, .95) * 100, 2), "fill_min_pct": r(fills.min() * 100, 2),
            "first_full_is_small_pct": r((caps[js] == small).mean() * 100, 1) if caps.max() > small else None}


def main():
    t0 = time.time()
    # (1) 基本
    caps = caps_of(5, 2.0, 100)
    formula = N * caps.min() / caps.sum()
    base, base_fills = {}, {}
    for i, m in enumerate(METHODS):
        f, j = run(m, caps, REPS, [SEED, 1, i])
        base[m] = {"method": METHODS[m], **stats(f, j, caps)}
        base_fills[m] = f
    base_df = pd.DataFrame(base.values())
    base_df.to_csv(RES / "base_methods.csv", index=False)
    pd.DataFrame({k: np.round(v * 100, 4) for k, v in base_fills.items()}).rename_axis("rep").to_csv(
        RES / "base_fills.csv")

    # 1回目（①）の台ごとの使った量（data）
    rng = np.random.default_rng([SEED, 1, 0, 0])
    total = caps.sum()
    n_items = int(N * caps.min() / MEAN_MB * 1.3) + 1000
    size = rng.lognormal(MU, SIG, n_items)
    a = rng.integers(0, N, n_items)
    f1, j1, used_items = first_full("rand_equal", np.random.default_rng([SEED, 1, 0, 0]), caps)  # 同じ乱数で、同じ時点まで
    used = np.bincount(a[:used_items], weights=size[:used_items], minlength=N)
    cnt = np.bincount(a[:used_items], minlength=N)
    ex = pd.DataFrame({"node": np.arange(N), "capacity_gb": caps / 1000, "items": cnt,
                       "used_gb": np.round(used / 1000, 3), "used_pct": np.round(used / caps * 100, 2)})
    ex.to_csv(DATA / "rep1_nodes_at_first_full.csv", index=False)
    example = {"fill_pct": r(f1 * 100, 2), "first_full_node": int(j1), "items": int(cnt.sum()),
               "large_used_pct_mean": r(ex.used_pct[:5].mean(), 2), "small_used_pct_mean": r(ex.used_pct[5:].mean(), 2)}

    # (2) 確かめ
    grid = []
    for ratio in [1.0, 1.5, 2.0, 4.0]:
        for nl in [2, 5, 8]:
            for sg in [10, 100, 1000]:
                c = caps_of(nl, ratio, sg)
                row = {"ratio_large_small": ratio, "n_large": nl, "small_gb": sg,
                       "formula_equal_pct": r(N * c.min() / c.sum() * 100, 2)}
                for i, m in enumerate(METHODS):
                    f, j = run(m, c, GRID_REPS[sg], [SEED, 2, int(ratio * 10), nl, sg, i])
                    s = stats(f, j, c)
                    row[f"{m}_fill_mean_pct"] = s["fill_mean_pct"]
                    row[f"{m}_fill_p5_pct"] = s["fill_p5_pct"]
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid["rand_equal_minus_formula_pt"] = (grid.rand_equal_fill_mean_pct - grid.formula_equal_pct).round(2)
    grid["round_minus_formula_pt"] = (grid.round_fill_mean_pct - grid.formula_equal_pct).round(2)
    grid.to_csv(RES / "grid.csv", index=False)

    def rg(s):
        return [r(s.min(), 2), r(s.max(), 2)]

    mixed = grid[grid.ratio_large_small > 1]
    out = {"base": {"caps_gb": (caps / 1000).tolist(), "formula_equal_pct": r(formula * 100, 2),
                    "rand_equal_minus_formula_pt": r(base["rand_equal"]["fill_mean_pct"] - r(formula * 100, 2), 2),
                    "round_minus_formula_pt": r(base["round"]["fill_mean_pct"] - r(formula * 100, 2), 2),
                    "methods": base_df.to_dict("records")},
           "example_rep1": example,
           "grid_summary": {
               "n_configs": int(len(grid)),
               "formula_equal_range_mixed": rg(mixed.formula_equal_pct),
               "rand_equal_mean_range_mixed": rg(mixed.rand_equal_fill_mean_pct),
               "round_mean_range_mixed": rg(mixed.round_fill_mean_pct),
               "rand_cap_mean_range_all": rg(grid.rand_cap_fill_mean_pct),
               "rand_equal_minus_formula_range": rg(grid.rand_equal_minus_formula_pt),
               "round_minus_formula_range": rg(grid.round_minus_formula_pt),
               "by_small_gb_rand_equal_minus_formula": {str(g): rg(grid[grid.small_gb == g].rand_equal_minus_formula_pt) for g in [10, 100, 1000]},
               "by_small_gb_rand_cap_mean": {str(g): rg(grid[grid.small_gb == g].rand_cap_fill_mean_pct) for g in [10, 100, 1000]},
               "same_caps_rand_equal_mean_range": rg(grid[grid.ratio_large_small == 1].rand_equal_fill_mean_pct)}}
    json.dump(out, open(RES / "a1316_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回目の台ごとの埋まり具合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    col = [BLUE] * 5 + [ORANGE] * 5
    ax.bar(ex.node, ex.used_pct, color=col)
    ax.bar(j1, ex.used_pct[j1], color=INK)
    ax.axhline(100, color=GRAY, lw=1, ls="--")
    ax.set_xticks(ex.node, [f"台{i}\n（{'大' if i < 5 else '小'}）" for i in ex.node], fontsize=9)
    for t in ax.get_xticklabels(): t.set_linespacing(1.5)
    ax.set_ylabel("台ごとの埋まり具合（%）"); ax.set_ylim(0, 110)
    ax.set_title(f"1回目：最初の1台（黒）が満杯の時点で、全体は{example['fill_pct']}%")
    ax.text(0, 103, "青＝200GBの台　橙＝100GBの台", fontsize=8, color=GRAY)
    save(fig, "a1316_rep1_nodes.png", SRC + "。①件数で均等（でたらめ）の1回目", y=-0.05)

    # 図2：振り分け方ごとの全体の埋まり具合（基本、300回）
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    labels = [METHODS[m] for m in METHODS]
    vals = [base[m]["fill_mean_pct"] for m in METHODS]
    ax.barh(labels[::-1], vals[::-1], color=[BLUE, LIGHT, GRAY][::-1])
    for i, (m, v) in enumerate(zip(list(METHODS)[::-1], vals[::-1])):
        ax.text(max(v, formula * 100) + 1.5, i, f"{v}%（5%点 {base[m]['fill_p5_pct']}%）", va="center", fontsize=9)
    ax.axvline(formula * 100, color=ORANGE, ls="--", lw=1)
    ax.text(formula * 100 + 0.5, 2.45, f"式どおりの見込み{r(formula * 100, 2)}%", color=ORANGE, fontsize=8)
    ax.set_xlim(0, 125); ax.set_xlabel("最初の1台が満杯になった時点の、全体の埋まり具合（%、300回の平均）")
    ax.set_title(f"件数で均等（でたらめ）に振り分けると、全体の{vals[0]}%で1台が満杯になった")
    save(fig, "a1316_methods.png", SRC + "。200GB×5台＋100GB×5台", y=-0.05)

    # 図3：容量の比と、件数で均等（でたらめ）の埋まり具合（小さい台100GB）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    sub = grid[grid.small_gb == 100]
    for nl, c, mk in zip([2, 5, 8], [GREEN, BLUE, ORANGE], ["o", "s", "^"]):
        s = sub[sub.n_large == nl]
        ax.plot(s.ratio_large_small, s.rand_equal_fill_mean_pct, marker=mk, color=c, label=f"大きい台{nl}台（でたらめ）")
        ax.plot(s.ratio_large_small, s.formula_equal_pct, ls=":", color=c, lw=1)
    ax.set_xticks([1, 1.5, 2, 4], ["1倍", "1.5倍", "2倍", "4倍"])
    ax.set_xlabel("大きい台の容量÷小さい台の容量"); ax.set_ylabel("全体の埋まり具合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("容量の差が大きいほど、大きい台が多いほど、早く1台が満杯になる")
    save(fig, "a1316_by_ratio.png", SRC + "。10台・小さい台100GB・各40回の平均。点線は式どおりの見込み", y=-0.05)
    print(round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
