"""1295 荷物を来た順に詰めるか、大きい順に並べ替えてから詰めるかで、使う車の台数と積載率はどれだけ違うのか？（架空のデータ）

架空の通販の配送。その日の荷物を、荷台の大きさが同じ車に積む。荷物の体積は荷台を1とした比で置く。
形は気にせず、体積の合計だけで入るかを決める（縦・横・高さの並べ方は入れていない）。
詰め方（どれも、入る車のうちいちばん先に使い始めた車に積む。車は閉じない）：
  A 来た順に詰める
  B その日の荷物を全部そろえてから、大きい順に並べて詰める
  参考 C 来た順に詰め、入らなければその車を出して次の車（開いている車は1台）
積載率＝その日の体積の合計÷(台数×1)。すべてシミュレーション。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1295
SRC = "架空の通販の配送の積み込みのシミュレーション（作成者が乱数で作成、seed 1295）"
TARGET = 20                 # 体積の合計が平均で荷台20台分になるように荷物の数を決める
BASE = ("lognormal", 0.2, 0.6)
LN_MEANS = [0.05, 0.1, 0.2, 0.3]
LN_SIGS = [0.3, 0.6, 1.0]
UNIFORMS = [(0.1, 0.4), (0.2, 0.45), (0.25, 0.5), (0.3, 0.5)]
DAYS_BASE, DAYS_GRID = 1000, 300


def draw(rng, n, shape, a, b):
    if shape == "uniform":
        return rng.uniform(a, b, n)
    mu = np.log(a) - b ** 2 / 2
    x = rng.lognormal(mu, b, n)
    bad = x > 1.0
    while bad.any():
        x[bad] = rng.lognormal(mu, b, bad.sum()); bad = x > 1.0
    return x


def pack_first(x):
    rem = np.ones(len(x)); nb = 0
    for v in x:
        if nb:
            ok = np.nonzero(rem[:nb] >= v - 1e-12)[0]
            if len(ok):
                rem[ok[0]] -= v; continue
        rem[nb] -= v; nb += 1
    return nb, 1.0 - rem[:nb]


def pack_close(x):
    nb, cur = 1, 0.0
    for v in x:
        if cur + v > 1.0 + 1e-12:
            nb += 1; cur = 0.0
        cur += v
    return nb


def n_items(shape, a, b):
    m = (a + b) / 2 if shape == "uniform" else a
    return int(round(TARGET / m))


def run(rng, shape, a, b, days, keep=False):
    n = n_items(shape, a, b)
    rows = []
    kept = []
    for d in range(days):
        x = draw(rng, n, shape, a, b)
        tot = float(x.sum())
        na, _ = pack_first(x)
        nsort, _ = pack_first(np.sort(x)[::-1])
        nc = pack_close(x)
        rows.append({"day": d, "items": n, "volume_sum": tot, "lower_bound": int(np.ceil(tot - 1e-9)),
                     "trucks_arrival": na, "trucks_sorted": nsort, "trucks_close": nc})
        if keep:
            kept.append(x)
    return (pd.DataFrame(rows), kept) if keep else pd.DataFrame(rows)


def summ(df):
    v = df.volume_sum
    diff = df.trucks_arrival - df.trucks_sorted
    return {"items": int(df["items"].iloc[0]), "item_mean_actual": (v / df["items"]).mean(),
            "trucks_arrival_mean": df.trucks_arrival.mean(), "trucks_sorted_mean": df.trucks_sorted.mean(),
            "trucks_close_mean": df.trucks_close.mean(), "lower_bound_mean": df.lower_bound.mean(),
            "fewer_by_sorting_mean": diff.mean(),
            "share_days_sorted_fewer": (diff > 0).mean() * 100,
            "share_days_sorted_more": (diff < 0).mean() * 100,
            "fill_arrival_pct": (v / df.trucks_arrival).mean() * 100,
            "fill_sorted_pct": (v / df.trucks_sorted).mean() * 100,
            "fill_close_pct": (v / df.trucks_close).mean() * 100,
            "fill_gain_sorted_vs_arrival_pt": ((v / df.trucks_sorted).mean() - (v / df.trucks_arrival).mean()) * 100,
            "fill_gain_arrival_vs_close_pt": ((v / df.trucks_arrival).mean() - (v / df.trucks_close).mean()) * 100,
            "more_trucks_close_vs_arrival_mean": (df.trucks_close - df.trucks_arrival).mean(),
            "share_days_sorted_at_bound": (df.trucks_sorted == df.lower_bound).mean() * 100,
            "share_days_arrival_at_bound": (df.trucks_arrival == df.lower_bound).mean() * 100}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base, xs_base = run(rng, *BASE, DAYS_BASE, keep=True)
    b2 = base.copy(); b2["volume_sum"] = b2.volume_sum.round(4)
    b2.to_csv(DATA / "days_base.csv", index=False)
    bs = {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in summ(base).items()}
    diff = (base.trucks_arrival - base.trucks_sorted).value_counts(normalize=True).sort_index() * 100
    dd = pd.DataFrame({"fewer_trucks_by_sorting": diff.index, "share_days_pct": diff.values.round(2)})
    dd.to_csv(RES / "base_diff_dist.csv", index=False)

    # 1日分の例：基本の置き方で、並べ替えで台数が減った最初の日の車ごとの埋まり
    ex_day = int(base[base.trucks_arrival > base.trucks_sorted].day.iloc[0])
    x = xs_base[ex_day]
    na, la = pack_first(x); ns, ls = pack_first(np.sort(x)[::-1])
    ex = pd.DataFrame({"truck": np.arange(1, max(na, ns) + 1)})
    ex["fill_arrival_pct"] = pd.Series((la * 100).round(2)).reindex(range(len(ex))).values
    ex["fill_sorted_pct"] = pd.Series((ls * 100).round(2)).reindex(range(len(ex))).values
    ex.to_csv(RES / "example_day.csv", index=False)

    grid = []
    for m in LN_MEANS:
        for s in LN_SIGS:
            r = summ(run(rng, "lognormal", m, s, DAYS_GRID)); r.update({"shape": "lognormal", "p1": m, "p2": s}); grid.append(r)
    for a, b in UNIFORMS:
        r = summ(run(rng, "uniform", a, b, DAYS_GRID)); r.update({"shape": "uniform", "p1": a, "p2": b}); grid.append(r)
    grid = pd.DataFrame(grid)
    cols = ["shape", "p1", "p2", "items", "item_mean_actual", "lower_bound_mean", "trucks_arrival_mean",
            "trucks_sorted_mean", "trucks_close_mean", "fewer_by_sorting_mean", "share_days_sorted_fewer",
            "share_days_sorted_more", "fill_arrival_pct", "fill_sorted_pct", "fill_close_pct",
            "fill_gain_sorted_vs_arrival_pt", "fill_gain_arrival_vs_close_pt", "more_trucks_close_vs_arrival_mean",
            "share_days_arrival_at_bound", "share_days_sorted_at_bound"]
    grid = grid[cols].round(4)
    for c in [c for c in cols if c.endswith("_pct") or c.endswith("_pt") or c.startswith("share_")]:
        grid[c] = grid[c].round(2)
    grid.to_csv(RES / "grid.csv", index=False)
    ln = grid[grid["shape"] == "lognormal"]; un = grid[grid["shape"] == "uniform"]
    main_j = {"base_settings": {"shape": "lognormal", "item_mean": BASE[1], "item_sigma": BASE[2], "days": DAYS_BASE,
                                "target_trucks": TARGET},
              "base": bs,
              "example_day": {"day": ex_day, "trucks_arrival": int(na), "trucks_sorted": int(ns), "volume_sum": round(float(x.sum()), 4)},
              "grid_range": {
                  "fewer_by_sorting_lognormal": [float(ln.fewer_by_sorting_mean.min()), float(ln.fewer_by_sorting_mean.max())],
                  "fewer_by_sorting_uniform": [float(un.fewer_by_sorting_mean.min()), float(un.fewer_by_sorting_mean.max())],
                  "fill_gain_sorted_vs_arrival_pt": [float(grid.fill_gain_sorted_vs_arrival_pt.min()), float(grid.fill_gain_sorted_vs_arrival_pt.max())],
                  "fill_gain_arrival_vs_close_pt": [float(grid.fill_gain_arrival_vs_close_pt.min()), float(grid.fill_gain_arrival_vs_close_pt.max())],
                  "more_trucks_close_vs_arrival": [float(grid.more_trucks_close_vs_arrival_mean.min()), float(grid.more_trucks_close_vs_arrival_mean.max())],
                  "share_days_sorted_fewer": [float(grid.share_days_sorted_fewer.min()), float(grid.share_days_sorted_fewer.max())],
                  "share_days_sorted_more_max": float(grid.share_days_sorted_more.max())}}
    with open(RES / "a1295_main.json", "w", encoding="utf-8") as f:
        json.dump(main_j, f, ensure_ascii=False, indent=1)

    # 図1：例の日の車ごとの埋まり
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    for ax, col, c, lab, k in [(axes[0], "fill_arrival_pct", BLUE, "A 来た順に詰める", na),
                               (axes[1], "fill_sorted_pct", ORANGE, "B 大きい順に並べてから詰める", ns)]:
        y = ex[col].fillna(0)
        ax.bar(ex.truck, y, color=c)
        ax.set_title(f"{lab}：{k}台", fontsize=11)
        ax.set_xlabel("車（使い始めた順）")
        ax.set_ylim(0, 105)
    axes[0].set_ylabel("荷台の埋まり（%）")
    fig.suptitle(f"同じ1日の荷物{len(x)}個（基本の置き方で、並べ替えで台数が減った最初の日）", y=1.02)
    save(fig, "a1295_example_day.png", SRC)

    # 図2：基本の置き方の台数の差の分布
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(dd.fewer_trucks_by_sorting, dd.share_days_pct, color=BLUE, width=0.6)
    for xx, yy in zip(dd.fewer_trucks_by_sorting, dd.share_days_pct):
        ax.text(xx, yy, str(yy), ha="center", va="bottom", fontsize=9)
    ax.set_xticks(dd.fewer_trucks_by_sorting)
    ax.set_xlabel("大きい順に並べて減った台数（A − B）")
    ax.set_ylabel("日の割合（%）")
    ax.set_ylim(0, None)
    ax.set_title(f"基本の置き方の{DAYS_BASE:,}日")
    save(fig, "a1295_diff_dist.png", SRC)

    # 図3：置き方ごとの積載率（横棒）
    fig, ax = plt.subplots(figsize=(8, 8.5))
    labs = [f"大きさの平均{r.p1:.0%}・散らばり{r.p2}" if r["shape"] == "lognormal" else f"一様に{r.p1:.0%}〜{r.p2:.0%}"
            for _, r in grid.iterrows()]
    ys = np.arange(len(grid))[::-1]; h = 0.27
    ax.barh(ys + h, grid.fill_close_pct, h, color=GRAY, label="参考 C 来た順・入らなければ次の車")
    ax.barh(ys, grid.fill_arrival_pct, h, color=BLUE, label="A 来た順に詰める")
    ax.barh(ys - h, grid.fill_sorted_pct, h, color=ORANGE, label="B 大きい順に並べてから詰める")
    ax.set_yticks(ys, labs, fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("積載率（%、各300日の平均）")
    ax.set_title("荷物の大きさの置き方16通りの積載率（荷台に対する割合）")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.07), ncol=1, fontsize=9)
    save(fig, "a1295_grid_fill.png", SRC, y=-0.1)

    print(json.dumps(main_j, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
