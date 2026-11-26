"""1297 上に重ねられない荷物が1割まざると、体積で見た積載率はどれだけ下がり、車は何台増えるのか？（架空のデータ）

架空の通販の1日の発送。荷台の床は16区画、高さは1（荷台の高さを1とした割合）。
荷物の底はどれも1区画分にそろえ、高さだけが違う（作成者が置いた単純な形）。
1つの区画には荷物を下から重ねる（高さの合計が1まで）。
上に重ねられない荷物の決まりを2つ置く：
  決まりA：上に何も載せない（ほかの荷物の上には置ける）→ 1つの区画に1つまで、いちばん上に置く
  決まりB：床に直に置き、上にも何も載せない → 1つで1区画を使う
詰め方：大きい（高い）順に並べ、入る区画のうち残りがいちばん小さい区画に置く。
台数＝区画の数÷16の切り上げ。体積で見た積載率＝荷物の高さの合計÷(台数×16)。
すべてシミュレーション。
"""
import json
import math
import time
from bisect import bisect_left, insort
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1297
SRC = "架空の通販の発送の積み込みのシミュレーション（作成者が乱数で作成、seed 1297）"
CAP = 1_000_000                    # 荷台の高さ（整数の単位）
CELLS = 16                         # 1台の床の区画の数
N_ITEMS = 600                      # 1日の荷物の数
DAYS = 300
GRID_DAYS = 100
P_LIST = [0.0, 0.05, 0.10, 0.20, 0.30]
BASE_MED, BASE_SIG = 0.25, 0.5
H_MIN, H_MAX = 0.05, 1.0
MEDS = [0.12, 0.25, 0.45]
SIGS = [0.3, 0.7]


def heights(rng, n, med, sig):
    h = med * np.exp(rng.normal(0, sig, n))
    bad = (h < H_MIN) | (h > H_MAX)
    while bad.any():
        h[bad] = med * np.exp(rng.normal(0, sig, bad.sum()))
        bad = (h < H_MIN) | (h > H_MAX)
    return np.maximum(1, np.round(h * CAP)).astype(np.int64)


def pack_plain(hs):
    """重ねてよい荷物だけを詰め、区画の数を返す"""
    res = []
    for s in sorted(hs, reverse=True):
        i = bisect_left(res, s)
        r = (res.pop(i) if i < len(res) else CAP) - s
        insort(res, r)
    return len(res)


def pack_rule_a(stack_h, ns_h):
    """決まりA：重ねられない荷物は1区画に1つまで（いちばん上）。区画の数を返す"""
    items = sorted([(s, 0) for s in stack_h] + [(s, 1) for s in ns_h], reverse=True)
    free, top = [], []               # 重ねられない荷物がまだない区画／もうある区画（残りの小さい順）
    for s, ns in items:
        i = bisect_left(free, s)
        if ns:
            if i < len(free):
                r = free.pop(i) - s
            else:
                r = CAP - s
            insort(top, r)
        else:
            j = bisect_left(top, s)
            cf = free[i] if i < len(free) else None
            ct = top[j] if j < len(top) else None
            if ct is not None and (cf is None or ct <= cf):
                r = top.pop(j) - s; insort(top, r)
            elif cf is not None:
                r = free.pop(i) - s; insort(free, r)
            else:
                insort(free, CAP - s)
    return len(free) + len(top)


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def trucks_of(cells):
    return math.ceil(cells / CELLS)


def run(rng, days, med, sig, keep_days=False):
    rows = []
    for d in range(days):
        h = heights(rng, N_ITEMS, med, sig)
        order = rng.permutation(N_ITEMS)     # 先頭から p の割合を「重ねられない」にする（p が大きいほど前の印を含む）
        vol = h.sum() / CAP
        for p in P_LIST:
            k = int(round(p * N_ITEMS))
            mask = np.zeros(N_ITEMS, bool); mask[order[:k]] = True
            st = h[~mask].tolist(); ns = h[mask].tolist()
            plain = pack_plain(st)
            cells_b = plain + len(ns)
            cells_a = pack_rule_a(st, ns) if k > 0 else plain
            gap_above = sum(CAP - x for x in ns) / CAP     # 重ねられない荷物の上の空き（区画の高さで数えた合計）
            for rule, cells in (("A", cells_a), ("B", cells_b)):
                tr = trucks_of(cells)
                rows.append({"day": d, "p_no_stack": p, "rule": rule, "no_stack_items": k, "volume": vol,
                             "cells": cells, "trucks": tr, "load": vol / (tr * CELLS),
                             "cell_fill": vol / cells, "gap_above_no_stack": gap_above})
    return pd.DataFrame(rows)


def summarize(df):
    base0 = df[df.p_no_stack == 0].groupby(["day", "rule"])[["cells", "trucks"]].first()
    m = df.merge(base0.rename(columns={"cells": "cells0", "trucks": "trucks0"}), left_on=["day", "rule"], right_index=True)
    m["extra_cells"] = m.cells - m.cells0
    m["extra_trucks"] = m.trucks - m.trucks0
    g = m.groupby(["rule", "p_no_stack"])
    out = pd.DataFrame({
        "no_stack_items": g.no_stack_items.mean(),
        "trucks_mean": g.trucks.mean(),
        "extra_trucks_mean": g.extra_trucks.mean(),
        "share_days_more_trucks": g.apply(lambda x: (x.extra_trucks > 0).mean()),
        "cells_mean": g.cells.mean(),
        "extra_cells_mean": g.extra_cells.mean(),
        "gap_above_mean": g.gap_above_no_stack.mean(),
        "load_total": g.apply(lambda x: x.volume.sum() / (x.trucks.sum() * CELLS)),
        "cell_fill_total": g.apply(lambda x: x.volume.sum() / x.cells.sum()),
    }).reset_index()
    out["load_change_pt"] = out.apply(lambda r: (r.load_total - out[(out.rule == r.rule) & (out.p_no_stack == 0)].load_total.iloc[0]) * 100, axis=1)
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base = run(rng, DAYS, BASE_MED, BASE_SIG)
    base.to_csv(DATA / "days_base.csv", index=False, float_format="%.6f")
    bs = summarize(base)
    bs.to_csv(RES / "base_by_share.csv", index=False, float_format="%.4f")

    grid_rows = []
    for mi, med in enumerate(MEDS):
        for si, sig in enumerate(SIGS):
            g = summarize(run(np.random.default_rng(SEED * 100 + mi * 10 + si), GRID_DAYS, med, sig))
            g.insert(0, "height_sigma_log", sig); g.insert(0, "height_median", med)
            grid_rows.append(g)
    grid = pd.concat(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False, float_format="%.4f")

    def pick(df, rule, p):
        r = df[(df.rule == rule) & (np.isclose(df.p_no_stack, p))].iloc[0]
        return {k: (v if isinstance(v, str) else float(v)) for k, v in r.items()}

    g10a = grid[(grid.rule == "A") & np.isclose(grid.p_no_stack, 0.1)]
    g10b = grid[(grid.rule == "B") & np.isclose(grid.p_no_stack, 0.1)]
    g0 = grid[(grid.rule == "B") & (grid.p_no_stack == 0)]
    b10 = base[(base.rule == "B") & np.isclose(base.p_no_stack, 0.1)]
    b0 = base[(base.rule == "B") & (base.p_no_stack == 0)].set_index("day")
    diff = b10.set_index("day").cells - b0.cells
    main_res = {
        "setting": {"cells_per_truck": CELLS, "items_per_day": N_ITEMS, "height_median": BASE_MED,
                    "height_sigma_log": BASE_SIG, "height_range": [H_MIN, H_MAX], "days": DAYS, "p_list": P_LIST},
        "p0": pick(bs, "B", 0.0),
        "A_p10": pick(bs, "A", 0.10), "B_p10": pick(bs, "B", 0.10),
        "A_p30": pick(bs, "A", 0.30), "B_p30": pick(bs, "B", 0.30),
        "B_p10_extra_cells_vs_gap_above": {
            "extra_cells_mean": float(diff.mean()),
            "gap_above_mean": float(b10.gap_above_no_stack.mean()),
            "ratio": float(diff.mean() / b10.gap_above_no_stack.mean()),
            "corr_days": float(np.corrcoef(diff.values, b10.set_index("day").gap_above_no_stack.values)[0, 1]),
        },
        "grid_range": {
            "trucks_p0_min": float(g0.trucks_mean.min()), "trucks_p0_max": float(g0.trucks_mean.max()),
            "A_p10_extra_trucks_min": float(g10a.extra_trucks_mean.min()), "A_p10_extra_trucks_max": float(g10a.extra_trucks_mean.max()),
            "A_p10_load_change_min": float(g10a.load_change_pt.min()), "A_p10_load_change_max": float(g10a.load_change_pt.max()),
            "B_p10_extra_trucks_min": float(g10b.extra_trucks_mean.min()), "B_p10_extra_trucks_max": float(g10b.extra_trucks_mean.max()),
            "B_p10_load_change_min": float(g10b.load_change_pt.min()), "B_p10_load_change_max": float(g10b.load_change_pt.max()),
            "B_p10_extra_cells_over_gap_min": float((g10b.extra_cells_mean / g10b.gap_above_mean).min()),
            "B_p10_extra_cells_over_gap_max": float((g10b.extra_cells_mean / g10b.gap_above_mean).max()),
        },
    }
    with open(RES / "a1297_main.json", "w", encoding="utf-8") as f:
        json.dump(main_res, f, ensure_ascii=False, indent=1)

    # 図1：台数
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for rule, col, lab in (("A", BLUE, "決まりA：上に載せない（ほかの荷物の上には置ける）"),
                           ("B", ORANGE, "決まりB：床に直に置き、上にも載せない")):
        d = bs[bs.rule == rule]
        ax.plot(d.p_no_stack * 100, d.trucks_mean, color=col, lw=2.2, marker="o", ms=5, label=lab)
        for r in d.itertuples():
            if r.p_no_stack in (0.1, 0.3):
                ax.annotate(f"{fmt(r.trucks_mean)}台", (r.p_no_stack * 100, r.trucks_mean), textcoords="offset points",
                            xytext=(0, 8 if rule == "B" else -16), ha="center", fontsize=9, color=col)
    ax.set_xlabel("上に重ねられない荷物の割合（%、1日600個のうち）")
    ax.set_ylabel("車の台数（300日の平均）")
    ax.set_ylim(0, max(bs.trucks_mean) * 1.15)
    ax.set_xticks([p * 100 for p in P_LIST])
    ax.set_title("決まりAは1割までほとんど増えず、決まりBは割合とともに増える")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1297_trucks.png", SRC + "。床16区画・荷物の高さの中央値は荷台の0.25")

    # 図2：積載率（10%のとき）
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    labs = ["重ねられない\n荷物なし", "1割・決まりA", "1割・決まりB"]
    vals = [main_res["p0"]["load_total"], main_res["A_p10"]["load_total"], main_res["B_p10"]["load_total"]]
    ax.bar(range(3), [v * 100 for v in vals], color=[GRAY, BLUE, ORANGE], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v * 100 + 1.2, f"{v*100:.2f}%", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(range(3)); ax.set_xticklabels(labs)
    ax.set_ylabel("体積で見た積載率（%）")
    ax.set_ylim(0, 110)
    ax.set_title("1割まざったときの体積で見た積載率")
    save(fig, "a1297_load.png", SRC)

    # 図3：6通りで、1割まざったときに増えた台数
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    xs = np.arange(len(g10b)); w = 0.38
    ax.bar(xs - w / 2, g10a.extra_trucks_mean, w, color=BLUE, label="決まりA")
    ax.bar(xs + w / 2, g10b.extra_trucks_mean, w, color=ORANGE, label="決まりB")
    for x, a, b in zip(xs, g10a.extra_trucks_mean, g10b.extra_trucks_mean):
        ax.text(x - w / 2, a + 0.05, fmt(a), ha="center", va="bottom", fontsize=8)
        ax.text(x + w / 2, b + 0.05, fmt(b), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"高さ{r.height_median}\n散らばり{r.height_sigma_log}" for r in g10b.itertuples()], fontsize=8.5)
    ax.set_ylabel("増えた台数（なしとの差、100日の平均）")
    ax.set_ylim(0, max(g10b.extra_trucks_mean) * 1.25)
    ax.set_title("1割まざったときに増えた台数（6通り）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1297_grid.png", SRC + "。高さは荷台に対する中央値と対数の標準偏差")
    print(json.dumps(main_res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
