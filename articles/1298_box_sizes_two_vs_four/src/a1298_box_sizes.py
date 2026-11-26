"""1298 用意する箱の大きさを2種類から4種類に増やすと、箱の中のすきま（詰め物の量）はどれだけ減るのか？（架空のデータ）

架空の通販の1か月の注文3,000件。注文ごとの中身の大きさ（体積、リットル）を作成者が置いた分布から引く。
注文ごとに、入る箱のうちいちばん小さい箱を使う。すきま＝箱の容量−中身の大きさ（詰め物の量とみなす）。
形は考えず、大きさだけで「入る」を決める（形を考えると、すきまはこれより減ることはない）。
いちばん大きい箱は、中身の大きさの分布の99.9%点（中央値×exp(3.09×対数の標準偏差)、小数1けたに丸める）に決め、
中身はそれ以下に置く。残りの箱の大きさを3つの決め方で選ぶ：
  ① 倍ずつ：いちばん大きい箱の1/2・1/4・1/8…（1つ下は半分）
  ② 件数で等分：その月の注文を件数で等分する境目の大きさ
  ③ すきまがいちばん少なくなる大きさ：その月の注文に合わせて選ぶ（全部の組み合わせから最小を探す）
すべてシミュレーション。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1298
SRC = "架空の通販の注文と箱のシミュレーション（作成者が乱数で作成、seed 1298）"
N = 3000
V_MIN = 0.3
TOP_Z = 3.09                         # 99.9%点
TOP_CHECK = 1.5                      # 確かめ：いちばん大きい箱を1.5倍にする
KS = [1, 2, 3, 4, 6, 8]
BASE_MED, BASE_SIG = 6.0, 0.6
SIGS = [0.3, 0.6, 0.9]
SHAPES = ["one", "two"]              # 1つの山／2つの山（小さい注文7割と、中央値が4倍の大きい注文3割）
TOP_MULTS = [1.0, 1.5]
TWO_SHARE, TWO_RATIO = 0.3, 4.0
METHODS = {"double": "①倍ずつ", "quantile": "②件数で等分", "best": "③すきまが最少"}


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def top_of(med, sig, shape="one"):
    m = med * (TWO_RATIO if shape == "two" else 1.0)
    return round(m * float(np.exp(TOP_Z * sig)), 1)


def draw(rng, n, med, sig, shape):
    m = np.full(n, med)
    if shape == "two":
        m = np.where(rng.random(n) < TWO_SHARE, med * TWO_RATIO, med)
    return m * np.exp(rng.normal(0, sig, n))


def orders(rng, n, med, sig, top, shape="one"):
    v = draw(rng, n, med, sig, shape)
    bad = (v < V_MIN) | (v > top)
    while bad.any():
        v[bad] = draw(rng, int(bad.sum()), med, sig, shape)
        bad = (v < V_MIN) | (v > top)
    return np.round(v, 4)


def sizes_double(k, top):
    return sorted(top / 2 ** j for j in range(k))


def sizes_quantile(v, k, top):
    s = np.sort(v)
    q = [s[int(np.ceil(len(s) * j / k)) - 1] for j in range(1, k)]
    return sorted(set(float(x) for x in q) | {top})


def sizes_best(v, kmax, top):
    """いちばん大きい箱を top に決め、残り k−1 種類を注文の大きさの中から選んで箱の容量の合計を最小にする。
    k＝1〜kmax の最良の大きさをまとめて返す（区切りを順に決める計算）"""
    s = np.sort(v); n = len(s)
    INF = np.inf
    # f[l][j]：小さい順に j 件を l 種類の箱（いちばん大きい箱の大きさ＝s[j-1]）で覆うときの容量の合計の最小
    f = [np.full(n + 1, INF)]; f[0][0] = 0.0
    arg = [None]
    idx = np.arange(n + 1)
    for l in range(1, kmax):
        prev = f[-1]
        cur = np.full(n + 1, INF); a = np.zeros(n + 1, dtype=int)
        for j in range(1, n + 1):
            c = s[j - 1]
            cand = prev[:j] + (j - idx[:j]) * c
            i = int(np.argmin(cand))
            cur[j] = cand[i]; a[j] = i
        f.append(cur); arg.append(a)
    out = {1: [top]}
    for k in range(2, kmax + 1):
        prev = f[k - 1]
        cand = prev + (n - idx) * top
        cand[0] = INF
        j = int(np.argmin(cand))
        sizes = [top]
        l = k - 1
        while l >= 1 and j > 0:
            sizes.append(float(s[j - 1]))
            j = arg[l][j]; l -= 1
        out[k] = sorted(set(sizes))
    return out


def evaluate(v, sizes):
    b = np.array(sorted(sizes))
    i = np.searchsorted(b, v, side="left")
    box = b[i]
    gap = box - v
    return {"box_total": float(box.sum()), "content_total": float(v.sum()), "gap_total": float(gap.sum()),
            "gap_share": float(gap.sum() / box.sum()), "gap_per_order": float(gap.mean()),
            "types_used": int(len(np.unique(box)))}


def run_setting(rng, med, sig, keep=False, top_mult=1.0, shape="one"):
    top0 = top_of(med, sig, shape)
    v = orders(rng, N, med, sig, top0, shape)
    v_next = orders(rng, N, med, sig, top0, shape)    # 翌月の注文（同じ分布、別の乱数）
    top = round(top0 * top_mult, 1)
    best = sizes_best(v, max(KS), top)
    rows = []
    for k in KS:
        for m, sz in (("double", sizes_double(k, top)), ("quantile", sizes_quantile(v, k, top)), ("best", best[k])):
            r = evaluate(v, sz)
            rn = evaluate(v_next, sz)
            r.update({"method": m, "k": k, "largest_box": top, "sizes": " / ".join(fmt(x) for x in sz),
                      "gap_share_next_month": rn["gap_share"], "gap_total_next_month": rn["gap_total"]})
            rows.append(r)
    d = pd.DataFrame(rows)
    return (d, v) if keep else d


def cut(d, m, a, b):
    ga = d[(d.method == m) & (d.k == a)].gap_total.iloc[0]
    gb = d[(d.method == m) & (d.k == b)].gap_total.iloc[0]
    return 1 - gb / ga


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base, v = run_setting(rng, BASE_MED, BASE_SIG, keep=True)
    pd.DataFrame({"order_id": np.arange(1, N + 1), "content_liter": v}).to_csv(DATA / "orders_base.csv", index=False)
    base.to_csv(RES / "base_by_types.csv", index=False, float_format="%.4f")

    chk = run_setting(np.random.default_rng(SEED), BASE_MED, BASE_SIG, top_mult=TOP_CHECK)
    chk.to_csv(RES / "check_largest_box_x1_5.csv", index=False, float_format="%.4f")

    grid_rows = []
    for hi, shape in enumerate(SHAPES):
      for ti, tm in enumerate(TOP_MULTS):
        for si, sig in enumerate(SIGS):
            d = run_setting(np.random.default_rng(SEED * 100 + hi * 20 + ti * 10 + si), BASE_MED, sig, top_mult=tm, shape=shape)
            row = {"shape": shape, "largest_box_mult": tm, "content_sigma_log": sig, "largest_box": float(d.largest_box.iloc[0])}
            for m in METHODS:
                for k in (1, 2, 4, 8):
                    row[f"{m}_gap_share_k{k}"] = d[(d.method == m) & (d.k == k)].gap_share.iloc[0]
                row[f"{m}_cut_2to4"] = cut(d, m, 2, 4)
            row["best_cut_1to2"] = cut(d, "best", 1, 2)
            row["best_cut_4to8"] = cut(d, "best", 4, 8)
            row["best_next_month_k4"] = d[(d.method == "best") & (d.k == 4)].gap_share_next_month.iloc[0]
            grid_rows.append(row)
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False, float_format="%.4f")

    def pick(m, k):
        r = base[(base.method == m) & (base.k == k)].iloc[0]
        return {c: (r[c] if isinstance(r[c], str) else float(r[c])) for c in base.columns}

    main_res = {
        "setting": {"orders": N, "content_median_liter": BASE_MED, "content_sigma_log": BASE_SIG,
                    "content_range_liter": [V_MIN, top_of(BASE_MED, BASE_SIG)], "largest_box_liter": top_of(BASE_MED, BASE_SIG),
                    "types": KS},
        "content_max_sample": float(v.max()),
        "content_total": float(v.sum()), "content_median_sample": float(np.median(v)),
        "base": {m: {str(k): pick(m, k) for k in KS} for m in METHODS},
        "cut_2to4": {m: cut(base, m, 2, 4) for m in METHODS},
        "cut_1to2_best": cut(base, "best", 1, 2), "cut_4to8_best": cut(base, "best", 4, 8),
        "check_largest_box_x1_5": {"largest_box": float(chk.largest_box.iloc[0]),
                                   **{f"{m}_gap_share_k{k}": float(chk[(chk.method == m) & (chk.k == k)].gap_share.iloc[0])
                                      for m in METHODS for k in (2, 4)},
                                   **{f"{m}_cut_2to4": cut(chk, m, 2, 4) for m in METHODS}},
        "grid_range": {
            **{f"{m}_cut_2to4_min": float(grid[f"{m}_cut_2to4"].min()) for m in METHODS},
            **{f"{m}_cut_2to4_max": float(grid[f"{m}_cut_2to4"].max()) for m in METHODS},
            "best_gap_share_k2_min": float(grid.best_gap_share_k2.min()), "best_gap_share_k2_max": float(grid.best_gap_share_k2.max()),
            "best_gap_share_k4_min": float(grid.best_gap_share_k4.min()), "best_gap_share_k4_max": float(grid.best_gap_share_k4.max()),
            "best_cut_4to8_min": float(grid.best_cut_4to8.min()), "best_cut_4to8_max": float(grid.best_cut_4to8.max()),
            "best_next_month_k4_minus_this_max": float((grid.best_next_month_k4 - grid.best_gap_share_k4).max()),
            "best_next_month_k4_minus_this_min": float((grid.best_next_month_k4 - grid.best_gap_share_k4).min()),
            "double_gap_share_k2_min": float(grid.double_gap_share_k2.min()), "double_gap_share_k2_max": float(grid.double_gap_share_k2.max()),
        },
    }
    with open(RES / "a1298_main.json", "w", encoding="utf-8") as f:
        json.dump(main_res, f, ensure_ascii=False, indent=1)

    # 図1：箱の種類の数とすきまの割合
    OFFS = {("double", 2): -10, ("double", 4): 6, ("quantile", 2): 8, ("quantile", 4): 4, ("best", 2): -16, ("best", 4): -14}
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    for m, col in (("double", GRAY), ("quantile", ORANGE), ("best", BLUE)):
        d = base[base.method == m]
        ax.plot(d.k, d.gap_share * 100, color=col, lw=2.2, marker="o", ms=5, label=METHODS[m])
        for r in d.itertuples():
            if r.k in (2, 4):
                ax.annotate(f"{r.gap_share*100:.2f}%", (r.k, r.gap_share * 100), textcoords="offset points",
                            xytext=(10, OFFS[(m, r.k)]), ha="left", fontsize=8.5, color=col,
                            bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"))
    ax.set_xlabel(f"箱の大きさの種類の数（いちばん大きい箱は{fmt(top_of(BASE_MED, BASE_SIG))}リットル）")
    ax.set_ylabel("すきまの割合（すきまの合計÷箱の容量の合計、%）")
    ax.set_ylim(0, 105); ax.set_xticks(KS)
    ax.set_title("2種類から4種類にしたときの減り方は、大きさの決め方で違う")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1298_gap_share.png", SRC + "。注文3,000件、中身の大きさの中央値6リットル")

    # 図2：③の大きさ（2種類と4種類）と注文の分布
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    TOPB = top_of(BASE_MED, BASE_SIG)
    bins = np.logspace(np.log10(V_MIN), np.log10(TOPB), 50)
    ax.hist(v, bins=bins, color=LIGHT)
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 2, 5, 10, 20, 40]); ax.set_xticklabels(["0.5", "1", "2", "5", "10", "20", "40"])
    ax.minorticks_off()
    for k, col, ls in ((2, ORANGE, "--"), (4, BLUE, "-")):
        for x in pick("best", k)["sizes"].split(" / "):
            ax.axvline(float(x), color=col, ls=ls, lw=1.6)
    ax.plot([], [], color=ORANGE, ls="--", label="③で選んだ2種類の大きさ")
    ax.plot([], [], color=BLUE, ls="-", label="③で選んだ4種類の大きさ")
    ax.set_xlabel("中身の大きさ（リットル、対数の目盛り）")
    ax.set_ylabel("注文の件数")
    ax.set_title("注文の大きさの分布と、選んだ箱の大きさ")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1298_sizes.png", SRC + f"。いちばん大きい箱（{fmt(TOPB)}リットル）は2種類・4種類とも同じ")

    # 図3：9通りで、2種類→4種類のすきまの減り
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    xs = np.arange(len(grid)); w = 0.27
    for o, (m, col) in enumerate((("double", GRAY), ("quantile", ORANGE), ("best", BLUE))):
        ax.bar(xs + (o - 1) * w, grid[f"{m}_cut_2to4"] * 100, w, color=col, label=METHODS[m])
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{'山1' if r.shape == 'one' else '山2'}\n{fmt(r.largest_box_mult)}倍\n{r.content_sigma_log}" for r in grid.itertuples()], fontsize=8.5)
    ax.set_ylabel("すきまの合計の減り（2種類→4種類、%）")
    ax.set_ylim(0, 110)
    ax.set_title("2種類から4種類でのすきまの減り（12通り）")
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=3)
    save(fig, "a1298_grid_cut.png", SRC + "。目盛りは、分布の山の数・いちばん大きい箱の倍率（99.9%点に対して）／対数の標準偏差")
    print(json.dumps(main_res, ensure_ascii=False, indent=1)[:4000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
