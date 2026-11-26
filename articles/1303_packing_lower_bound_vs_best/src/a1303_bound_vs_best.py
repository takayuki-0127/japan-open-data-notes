"""1303 詰め方の良さを、「体積の合計÷容量」の切り上げと比べるか、いちばん良い詰め方と比べるかで、どれだけ見え方が違うのか？（架空のデータ）

作成者が置いた架空の通販の発送。箱の容量を100とし、商品12種類の大きさ（体積）を置く。1日に40個の荷物を詰める。
大きさ（体積）の合計だけで入るかを決め、縦・横・高さの形は考えない（形の話は別の場面）。
詰め方は3つ：①来た順に今の箱へ、入らなければ箱を閉じて次の箱 ②来た順に、入る最初の箱へ ③大きい順に並べてから、入る最初の箱へ。
物差しは2つ：(a) 体積の合計÷容量の切り上げ（下限） (b) その日の荷物でいちばん少ない箱の数（整数計画で厳密に解く）。
(1) 基本（大きさ10〜60）で200日、それぞれの詰め方の「下限より多い箱」と「いちばん良い詰め方より多い箱」を数える
(2) 大きさの範囲4通り（5〜35・10〜60・20〜70・30〜80）で同じことを数える（各200日）
(3) 確かめ：1日の荷物を20個・40個にした場合（大きさ4通り、各200日）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import coo_matrix
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1303
SRC = "架空の通販の発送（作成者が置いた箱の容量・商品の大きさからの乱数、seed 1303）"
C = 100
N = 40
DAYS = 200
TYPES = 12
RANGES = {"小さめ（5〜35）": (5, 35), "基本（10〜60）": (10, 60), "大きめ（20〜70）": (20, 70), "半分超えが多い（30〜80）": (30, 80)}
BASE = "基本（10〜60）"
METHODS = {"close": "①来た順・1箱ずつ閉じる", "arrival": "②来た順・入る最初の箱", "sorted": "③大きい順に並べてから"}


def r(x, d=4):
    return round(float(x), d)


def pack_close(items):
    n, room = 0, 0
    for p in items:
        if p > room:
            n += 1
            room = C
        room -= p
    return n


def pack_first_box(items):
    rest = []
    for p in items:
        for i, rr in enumerate(rest):
            if p <= rr:
                rest[i] = rr - p
                break
        else:
            rest.append(C - p)
    return len(rest)


def bound2(items):
    """大きい荷物は同じ箱に入れないことも使った下限（体積の下限以上）"""
    best = -(-sum(items) // C)
    its = sorted(items)
    for k in range(0, C // 2 + 1):
        n1 = sum(1 for x in its if x > C - k)
        big = [x for x in its if C - k >= x > C / 2]
        mid = sum(x for x in its if C / 2 >= x >= k)
        free = sum(C - x for x in big)
        v = n1 + len(big) + max(0, -(-(mid - free) // C))
        best = max(best, v)
    return best


def solve_best(items, ub):
    """その日の荷物でいちばん少ない箱の数（箱の中の埋まり具合を点とする流れの式の整数計画）"""
    sizes, q = np.unique(items, return_counts=True)
    sizes, q = sizes[::-1], q[::-1]
    reach, arcs = {0}, set()
    for k, s in enumerate(sizes):
        new = set()
        for u in sorted(reach):
            v = u
            for _m in range(q[k]):
                if v + s <= C:
                    arcs.add((v, v + s, k))
                    new.add(v + s)
                    v += s
        reach |= new
    nodes = sorted(reach | {C})
    for a, b in zip(nodes[:-1], nodes[1:]):
        arcs.add((a, b, -1))
    arcs = sorted(arcs)
    nv = len(arcs) + 1
    idx = {u: i for i, u in enumerate(nodes)}
    rows, cols, vals = [], [], []
    for j, (u, v, k) in enumerate(arcs):
        rows += [idx[u], idx[v]]
        cols += [j, j]
        vals += [1, -1]
    rows += [idx[0], idx[C]]
    cols += [nv - 1, nv - 1]
    vals += [-1, 1]
    A = coo_matrix((vals, (rows, cols)), shape=(len(nodes), nv))
    rr, cc = [], []
    for j, (u, v, k) in enumerate(arcs):
        if k >= 0:
            rr.append(k)
            cc.append(j)
    B = coo_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(sizes), nv))
    cons = [LinearConstraint(A, 0, 0), LinearConstraint(B, q, np.inf)]
    c = np.zeros(nv)
    c[-1] = 1
    lp = milp(c, constraints=cons, integrality=np.zeros(nv), bounds=Bounds(0, np.inf))
    if int(np.ceil(lp.fun - 1e-6)) >= ub:
        return ub
    res = milp(c, constraints=cons, integrality=np.ones(nv), bounds=Bounds(0, np.inf))
    return int(round(res.fun))


def exhaustive(items):
    """確かめ用：すべての入れ方をたどって、いちばん少ない箱の数を数える（同じ埋まり具合の箱の並びは1回だけたどる）"""
    its = sorted(items, reverse=True)
    best = [pack_first_box(its)]
    if best[0] == -(-sum(its) // C):
        return best[0]
    seen = set()

    def dfs(i, bins):
        if len(bins) >= best[0]:
            return
        if i == len(its):
            best[0] = len(bins)
            return
        free = sum(C - b for b in bins)
        if len(bins) + max(0, -(-(sum(its[i:]) - free) // C)) >= best[0]:
            return
        key = (i, tuple(sorted(bins)))
        if key in seen:
            return
        seen.add(key)
        tried = set()
        for j, b in enumerate(bins):
            if b + its[i] <= C and b not in tried:
                tried.add(b)
                bins[j] += its[i]
                dfs(i + 1, bins)
                bins[j] -= its[i]
        bins.append(its[i])
        dfs(i + 1, bins)
        bins.pop()
    dfs(0, [])
    return best[0]


def one_day(items):
    lb = -(-sum(items) // C)
    h = {"close": pack_close(items), "arrival": pack_first_box(items), "sorted": pack_first_box(sorted(items, reverse=True))}
    ub = min(h.values())
    b2 = bound2(items)
    best = ub if ub == b2 else solve_best(items, ub)
    return {"volume": int(sum(items)), "lower": lb, "best": best, **{f"boxes_{k}": v for k, v in h.items()}}


def run(rng, lo, hi, n, days):
    sizes = np.linspace(lo, hi, TYPES).round().astype(int)
    rows, lists = [], []
    for d in range(days):
        it = [int(x) for x in rng.choice(sizes, n)]
        o = one_day(it)
        o["day"] = d + 1
        rows.append(o)
        lists.append(it)
    return pd.DataFrame(rows), sizes, lists


def summarize(df):
    out = {"days": len(df), "volume_mean": r(df.volume.mean(), 2), "lower_mean": r(df.lower.mean(), 3),
           "best_mean": r(df.best.mean(), 3),
           "best_over_lower_mean": r((df.best - df.lower).mean(), 3),
           "best_over_lower_pct": r((df.best.sum() / df.lower.sum() - 1) * 100, 2),
           "days_best_gt_lower_pct": r((df.best > df.lower).mean() * 100, 2),
           "fill_at_best_pct": r(df.volume.sum() / (df.best.sum() * C) * 100, 2)}
    for k in METHODS:
        b = df[f"boxes_{k}"]
        out[k] = {"boxes_mean": r(b.mean(), 3),
                  "over_lower_mean": r((b - df.lower).mean(), 3),
                  "over_best_mean": r((b - df.best).mean(), 3),
                  "over_lower_pct": r((b.sum() / df.lower.sum() - 1) * 100, 2),
                  "over_best_pct": r((b.sum() / df.best.sum() - 1) * 100, 2),
                  "days_eq_lower_pct": r((b == df.lower).mean() * 100, 2),
                  "days_eq_best_pct": r((b == df.best).mean() * 100, 2),
                  "days_best_but_over_lower_pct": r(((b == df.best) & (b > df.lower)).mean() * 100, 2),
                  "fill_pct": r(df.volume.sum() / (b.sum() * C) * 100, 2)}
    return out


def main():
    t0 = time.time()
    out = {"setting": {"capacity": C, "items_per_day": N, "days": DAYS, "types": TYPES,
                       "ranges": {k: list(v) for k, v in RANGES.items()}, "methods": METHODS, "seed": SEED}}
    rows = []
    chk_days, chk_match = 0, 0
    for i, (name, (lo, hi)) in enumerate(RANGES.items()):
        for n in (20, N):
            rng = np.random.default_rng([SEED, i, n])
            df, sizes, lists = run(rng, lo, hi, n, DAYS)
            sm = summarize(df)
            if n == 20:   # 確かめ：1日20個の日は、すべての入れ方をたどる数え方でも同じ数になるか
                for it, bst in zip(lists, df.best):
                    chk_days += 1
                    chk_match += int(exhaustive(it) == bst)
            if n == N:
                out.setdefault("by_range", {})[name] = sm
                out.setdefault("sizes", {})[name] = sizes.tolist()
                if name == BASE:
                    df[["day", "volume", "lower", "best", "boxes_close", "boxes_arrival", "boxes_sorted"]].to_csv(
                        DATA / "days_base.csv", index=False)
            row = {"range": name, "items": n, "lower_mean": sm["lower_mean"], "best_mean": sm["best_mean"], "best_over_lower_pct": sm["best_over_lower_pct"],
                   "days_best_gt_lower_pct": sm["days_best_gt_lower_pct"]}
            for k in METHODS:
                for f in ("boxes_mean", "over_lower_pct", "over_best_pct", "days_eq_best_pct", "days_best_but_over_lower_pct", "fill_pct"):
                    row[f"{k}_{f}"] = sm[k][f]
            rows.append(row)
    out["check_exhaustive_20"] = {"days": chk_days, "days_same_best": chk_match}
    gr = pd.DataFrame(rows)
    gr.to_csv(RES / "grid.csv", index=False)
    out["grid_summary"] = {
        "sorted_over_lower_pct_min": r(gr.sorted_over_lower_pct.min(), 2), "sorted_over_lower_pct_max": r(gr.sorted_over_lower_pct.max(), 2),
        "sorted_over_best_pct_min": r(gr.sorted_over_best_pct.min(), 2), "sorted_over_best_pct_max": r(gr.sorted_over_best_pct.max(), 2),
        "arrival_over_lower_pct_min": r(gr.arrival_over_lower_pct.min(), 2), "arrival_over_lower_pct_max": r(gr.arrival_over_lower_pct.max(), 2),
        "arrival_over_best_pct_min": r(gr.arrival_over_best_pct.min(), 2), "arrival_over_best_pct_max": r(gr.arrival_over_best_pct.max(), 2),
        "days_best_gt_lower_pct_min": r(gr.days_best_gt_lower_pct.min(), 2), "days_best_gt_lower_pct_max": r(gr.days_best_gt_lower_pct.max(), 2)}

    names = list(RANGES)
    g40 = gr[gr["items"] == N].set_index("range").loc[names]
    # 図1：基本の置き方で、3つの詰め方の「多い箱」を2つの物差しで
    b = out["by_range"][BASE]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(3)
    lo_v = [b[k]["over_lower_pct"] for k in METHODS]
    be_v = [b[k]["over_best_pct"] for k in METHODS]
    ax.bar(x - 0.18, lo_v, 0.36, color=GRAY, label="下限（体積の合計÷容量の切り上げ）と比べる")
    ax.bar(x + 0.18, be_v, 0.36, color=BLUE, label="いちばん良い詰め方と比べる")
    for xi, v in zip(x - 0.18, lo_v):
        ax.text(xi, v, f"{v:.2f}%", ha="center", va="bottom", fontsize=9)
    for xi, v in zip(x + 0.18, be_v):
        ax.text(xi, v, f"{v:.2f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, list(METHODS.values()))
    ax.set_ylim(0, max(lo_v + be_v) * 1.2)
    ax.set_ylabel("比べる相手より多く使った箱（%）")
    ax.set_title("基本（大きさ10〜60、1日40個、200日）：同じ詰め方の見え方")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1303_base.png", SRC)

    # 図2：大きさの範囲で、③の見え方
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(names))
    ax.bar(x - 0.18, g40.sorted_over_lower_pct, 0.36, color=GRAY, label="下限と比べる")
    ax.bar(x + 0.18, g40.sorted_over_best_pct, 0.36, color=BLUE, label="いちばん良い詰め方と比べる")
    for xi, v in zip(x - 0.18, g40.sorted_over_lower_pct):
        ax.text(xi, v, f"{v:.2f}%", ha="center", va="bottom", fontsize=9)
    for xi, v in zip(x + 0.18, g40.sorted_over_best_pct):
        ax.text(xi, v, f"{v:.2f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, names, fontsize=9)
    ax.set_ylim(0, g40.sorted_over_lower_pct.max() * 1.2)
    ax.set_ylabel("③が多く使った箱（%）")
    ax.set_title("③大きい順に並べてから詰める：荷物の大きさの範囲ごと（1日40個）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1303_ranges.png", SRC)

    # 図3：いちばん良い詰め方でも下限より多い日の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    w = 0.36
    for j, (n, c) in enumerate([(20, ORANGE), (N, BLUE)]):
        sub = gr[gr["items"] == n].set_index("range").loc[names]
        ax.bar(x + (j - 0.5) * w, sub.days_best_gt_lower_pct, w, color=c, label=f"1日{n}個")
    ax.set_xticks(x, names, fontsize=9)
    ax.set_ylim(0, 108)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("いちばん良い詰め方でも下限より多い日（%）")
    ax.set_title("下限には、どう詰めても届かない日がある（各200日）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1303_unreachable.png", SRC)

    (RES / "a1303_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
