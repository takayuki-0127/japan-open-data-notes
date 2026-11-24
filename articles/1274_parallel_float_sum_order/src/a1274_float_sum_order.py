"""1274 同時に動かして足し合わせた小数の合計は、足す順番が回ごとに変わると、どれだけ食い違うのか？（架空のデータ）

架空のアプリの記録の値（小数）を100万件、作成者が乱数で作る。
「正の値だけ」（例：1件ごとの処理の秒数）と「増えた・減ったの差で打ち消し合う値」の2種類。
同じ値を、足す順番の決まりを変えて何回も合計し、回ごとの合計の食い違いを数える。
小数は、32ビットの小数（有効数字およそ7けた）と64ビットの小数（およそ16けた）の2つ。
同時に動かす様子は実機ではなく、足す順番を乱数で並べかえて作る。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1274
SRC = "架空のアプリの記録の値（作成者が乱数で作成、seed 1274）"
N_VAL = 1_000_000
PARTS = 8
CHUNK = 1000
RUNS = 100
METHODS = {
    "fixed_one": "① 1つで先頭から順に",
    "fixed_parts": "② 8つに分け、部分の合計を番号順に足す",
    "finish_order": "③ 8つに分け、部分の合計を終わった順に足す",
    "dynamic": "④ 1,000件ずつ空いた所が取り、終わった順に足す",
    "shared": "⑤ 全部の値を1つの合計に、来た順に足す",
}


def make_values(rng, n, kind):
    v = 0.05 * np.exp(rng.normal(-0.5, 1.0, n))           # 正の値：平均0.05
    if kind == "cancel":
        v = v * np.where(rng.random(n) < 0.5, 1.0, -1.0)   # 増えた・減った：打ち消し合う
    return v


def seqsum(x, dt):
    return np.cumsum(x, dtype=dt)[-1] if len(x) else dt(0)


def run_once(x, dt, method, rng, parts=PARTS, chunk=CHUNK):
    n = len(x)
    if method == "fixed_one":
        return float(seqsum(x, dt))
    if method in ("fixed_parts", "finish_order"):
        b = np.linspace(0, n, parts + 1).astype(int)
        ps = np.array([seqsum(x[b[i]:b[i + 1]], dt) for i in range(parts)], dtype=dt)
        if method == "finish_order":
            ps = ps[rng.permutation(parts)]
        return float(seqsum(ps, dt))
    if method == "dynamic":
        nc = int(np.ceil(n / chunk))
        dur = rng.exponential(1.0, nc) * 0.3 + 1.0          # かたまりごとのかかり方（回ごとに違う）
        free = np.zeros(parts); who = np.empty(nc, int); fin = np.empty(parts)
        for c in range(nc):                                  # 空いた所が次を取る
            w = int(np.argmin(free)); who[c] = w; free[w] += dur[c]
        ps = []
        for w in range(parts):
            idx = np.where(who == w)[0]
            if len(idx) == 0:
                continue
            seg = np.concatenate([x[c * chunk:(c + 1) * chunk] for c in idx])
            ps.append((free[w], seqsum(seg, dt)))
        ps.sort(key=lambda t: t[0])
        return float(seqsum(np.array([p for _, p in ps], dtype=dt), dt))
    if method == "shared":
        return float(seqsum(x[rng.permutation(n)], dt))
    raise ValueError(method)


def stats(vals, exact, x_abs_sum, dt):
    vals = np.array(vals)
    ulp = float(np.spacing(dt(abs(exact)))) if exact != 0 else float(np.spacing(dt(1)))
    spread = float(vals.max() - vals.min())
    return {"distinct": int(len(np.unique(vals))),
            "spread": spread,
            "spread_rel_to_total": spread / abs(exact),
            "spread_ulp": spread / ulp,
            "max_err_rel_to_total": float(np.abs(vals - exact).max()) / abs(exact),
            "spread_rel_to_abs_sum": spread / x_abs_sum,
            "exact_total": exact, "min": float(vals.min()), "max": float(vals.max())}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows, examples = [], {}
    for kind in ["positive", "cancel"]:
        base = make_values(rng, N_VAL, kind)
        for bits, dt in [(32, np.float32), (64, np.float64)]:
            x = base.astype(dt)
            exact = math.fsum(x.astype(np.float64))
            absum = math.fsum(np.abs(x.astype(np.float64)))
            for m in METHODS:
                runs = 1 if m.startswith("fixed") else RUNS
                r2 = np.random.default_rng(SEED * 10 + bits + len(rows))
                vals = [run_once(x, dt, m, r2) for _ in range(runs)]
                if m.startswith("fixed"):
                    vals = vals * 2  # 決まった順は何回やっても同じ（確かめに2回目も同じ値を数える）
                    chk = run_once(x, dt, m, r2)
                    assert chk == vals[0]
                s = stats(vals, exact, absum, dt)
                s.update({"kind": kind, "bits": bits, "method": m, "label": METHODS[m], "runs": runs})
                rows.append(s)
                if bits == 32 and m in ("finish_order", "shared"):
                    examples[f"{kind}_{m}"] = vals[:20]
        if kind == "positive":
            pd.DataFrame({"value_id": np.arange(20000), "value": base[:20000].round(8)}).to_csv(DATA / "values_positive_head.csv", index=False)
        else:
            pd.DataFrame({"value_id": np.arange(20000), "value": base[:20000].round(8)}).to_csv(DATA / "values_cancel_head.csv", index=False)
    df = pd.DataFrame(rows)
    cols = ["kind", "bits", "method", "label", "runs", "distinct", "exact_total", "min", "max", "spread",
            "spread_rel_to_total", "spread_ulp", "max_err_rel_to_total", "spread_rel_to_abs_sum"]
    df[cols].to_csv(RES / "spread_by_method.csv", index=False, float_format="%.10g")
    # 確かめ：件数 × 分ける数 × 小数の長さ × 値の種類（③④、各50回）
    grid = []
    rg = np.random.default_rng(SEED + 1)
    for kind in ["positive", "cancel"]:
        for nv in [10_000, 100_000, 1_000_000]:
            base = make_values(rg, nv, kind)
            for bits, dt in [(32, np.float32), (64, np.float64)]:
                x = base.astype(dt)
                exact = math.fsum(x.astype(np.float64)); absum = math.fsum(np.abs(x.astype(np.float64)))
                for parts in [2, 8, 64]:
                    for m in ["finish_order", "dynamic"]:
                        ch = max(100, nv // 1000)
                        vals = [run_once(x, dt, m, rg, parts=parts, chunk=ch) for _ in range(50)]
                        s = stats(vals, exact, absum, dt)
                        grid.append({"kind": kind, "values": nv, "bits": bits, "parts": parts, "method": m,
                                     "distinct": s["distinct"], "spread_rel_to_total": s["spread_rel_to_total"],
                                     "spread_ulp": s["spread_ulp"], "max_err_rel_to_total": s["max_err_rel_to_total"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False, float_format="%.6g")

    def g(kind, bits, m, key):
        return df[(df.kind == kind) & (df.bits == bits) & (df.method == m)][key].iloc[0]

    def rr(v, k=4):
        return float(f"{v:.{k}g}")
    res = {"setting": {"values": N_VAL, "parts": PARTS, "chunk": CHUNK, "runs": RUNS},
           "table": {f"{k}_{b}_{m}": {"distinct": int(g(k, b, m, "distinct")),
                                      "spread_rel_to_total": rr(g(k, b, m, "spread_rel_to_total")),
                                      "spread_ulp": rr(g(k, b, m, "spread_ulp")),
                                      "spread": rr(g(k, b, m, "spread")),
                                      "spread_pct_of_total": rr(100 * g(k, b, m, "spread_rel_to_total")),
                                      "max_err_rel_to_total": rr(g(k, b, m, "max_err_rel_to_total")),
                                      "exact_total": rr(g(k, b, m, "exact_total"), 10),
                                      "min": rr(g(k, b, m, "min"), 10), "max": rr(g(k, b, m, "max"), 10)}
                     for k in ["positive", "cancel"] for b in [32, 64] for m in METHODS},
           "grid": {"configs": len(grid),
                    "distinct_min_nonfixed": int(grid.distinct.min()),
                    "configs_all_same": int((grid.distinct == 1).sum()),
                    "rel_spread_range": {f"{k}_{b}": [rr(grid[(grid.kind == k) & (grid.bits == b)].spread_rel_to_total.min()),
                                                      rr(grid[(grid.kind == k) & (grid.bits == b)].spread_rel_to_total.max())]
                                         for k in ["positive", "cancel"] for b in [32, 64]},
                    "rel_spread_pct_range_32bit": [rr(100 * grid[grid.bits == 32].spread_rel_to_total.min()),
                                                   rr(100 * grid[grid.bits == 32].spread_rel_to_total.max())],
                    "rel_spread_pct_range_64bit": [rr(100 * grid[grid.bits == 64].spread_rel_to_total.min()),
                                                   rr(100 * grid[grid.bits == 64].spread_rel_to_total.max())],
                    "all_same_configs_are_two_parts_finish_order": bool(
                        ((grid.distinct == 1) == ((grid.parts == 2) & (grid.method == "finish_order"))).all()),
                    "ratio_cancel_over_positive_rel_spread_median": rr(float(np.median(
                        (grid[grid.kind == "cancel"].spread_rel_to_total.to_numpy() /
                         grid[grid.kind == "positive"].spread_rel_to_total.to_numpy())[
                            grid[grid.kind == "positive"].spread_rel_to_total.to_numpy() > 0]))),
                    "cancel_1m_32_dynamic_rel_spread_by_parts": {int(p): rr(float(grid[(grid.kind == "cancel") & (grid["values"] == 1_000_000) & (grid.bits == 32) & (grid.method == "dynamic") & (grid.parts == p)].spread_rel_to_total.iloc[0])) for p in [2, 8, 64]}},
           "examples_32bit_first5": {k: [rr(v, 10) for v in vals[:5]] for k, vals in examples.items()}}
    with open(RES / "a1274_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    ex = pd.DataFrame({"run": np.arange(1, 21)})
    for k, v in examples.items():
        ex[k] = v[:20]
    ex.to_csv(RES / "runs_example_32bit.csv", index=False, float_format="%.10g")
    figs(df, examples)
    print(df[["kind", "bits", "method", "distinct", "spread_rel_to_total", "spread_ulp", "max_err_rel_to_total", "exact_total"]].to_string())
    print(json.dumps(res["grid"], ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


def figs(df, examples):
    order = list(METHODS)
    fig, axs = plt.subplots(1, 2, figsize=(9.8, 4.2), sharey=True)
    for ax, kind, ttl in zip(axs, ["positive", "cancel"], ["正の値だけ（合計は大きい）", "打ち消し合う値（合計は0に近い）"]):
        sub = df[(df.kind == kind) & (df.bits == 32)].set_index("method").loc[order]
        y = np.arange(len(order))[::-1]
        ax.barh(y, sub.distinct, color=[GRAY, GRAY, BLUE, BLUE, ORANGE])
        for yy, v in zip(y, sub.distinct):
            ax.text(v + 3, yy, str(v), va="center", fontsize=9)
        ax.set_yticks(y); ax.set_yticklabels([METHODS[m] for m in order], fontsize=8.5)
        ax.set_xlim(0, RUNS * 1.15); ax.set_title(ttl, fontsize=10.5)
        ax.set_xlabel(f"{RUNS}回のうち、違う合計が出た数")
    fig.suptitle("32ビットの小数：足す順番が回ごとに大きく変わる決まりほど、違う合計が多く出た", fontsize=11.5, y=1.02)
    save(fig, "a1274_distinct.png", SRC + "。100万件。①②は決まった順なので1通り（作りどおり）")

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    labs, vals, cols = [], [], []
    for kind, kl in [("positive", "正の値"), ("cancel", "打ち消し合う値")]:
        for bits in [32, 64]:
            for m in ["finish_order", "dynamic", "shared"]:
                v = df[(df.kind == kind) & (df.bits == bits) & (df.method == m)].spread_rel_to_total.iloc[0]
                labs.append(f"{kl}・{bits}ビット・{METHODS[m][0]}"); vals.append(v)
                cols.append(BLUE if bits == 32 else GREEN)
    y = np.arange(len(labs))[::-1]
    for yy, v, c in zip(y, vals, cols):
        ax.plot([v], [yy], "o", color=c, ms=7)
        ax.hlines(yy, 1e-17, v, color=c, lw=0.6, ls=":")
    ax.set_xscale("log")
    for yy, v in zip(y, vals):
        ax.text(v * 3, yy, f"{v:.4g}", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8.5)
    ax.set_xlim(1e-17, 1)
    ax.set_xlabel(f"{RUNS}回の合計の最大−最小 ÷ 本当の合計（対数の目盛り）")
    ax.set_title("合計に対する食い違いは、64ビットの小数では32ビットよりけたちがいに小さかった", fontsize=12)
    save(fig, "a1274_spread.png", SRC + f"。100万件、{RUNS}回。点の位置は対数の目盛り（値で読む）")

    fig, axs = plt.subplots(1, 2, figsize=(9.8, 4.0))
    for ax, kind, ttl in zip(axs, ["positive", "cancel"], ["正の値だけ", "打ち消し合う値"]):
        sub = df[(df.kind == kind) & (df.bits == 32)]
        exact = sub.exact_total.iloc[0]
        v = np.array(examples[f"{kind}_shared"])
        ax.plot(np.arange(1, len(v) + 1), v, color=ORANGE, marker="o", ms=4, label="⑤ 来た順に足す（32ビット）")
        ax.axhline(exact, color=INK, lw=1, ls="--", label=f"本当の合計 {exact:.10g}")
        ax.set_xlabel("回"); ax.set_title(ttl, fontsize=10.5)
        ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
        ax.ticklabel_format(axis="y", useOffset=False)
    axs[0].set_ylabel("合計", labelpad=8)
    fig.suptitle("同じ100万件を足しても、回ごとに合計が変わった（初めの20回）", fontsize=11.5, y=1.02)
    save(fig, "a1274_runs.png", SRC + "。縦軸は0から始めていない（回ごとの違いを見るための折れ線）", y=-0.12)


if __name__ == "__main__":
    main()
