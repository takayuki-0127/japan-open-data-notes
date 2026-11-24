"""1160 試験の環境で測った当たり率は、本番の使われ方の偏りが違うとどれだけ外れるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ10万件。i番目に人気のデータが選ばれる確率は 1÷i^a に比例（a が偏りの大きさ）。
本番の偏りを a=0.8 と置き、試験の環境では偏りだけが違う問い合わせ（a=0〜1.2）を流して、同じ大きさの置き場所（キャッシュ）で当たり率を測る。
置き場所は件数で数え、いっぱいなら、いちばん長く使われていないものを捨てる。
(1) 乱数の問い合わせ列（はじめの10万件で埋め、続く30万件で数える）で、本番 a=0.8 と試験 a=0・0.6・1.0 の当たり率を置き場所1%・4%で数える
(2) 本番 a×試験 a（0.6〜1.2、0.1きざみの7×7）を、近い値を出す式で出す（置き場所の大きさに合う「置いておける時間」を1つ決め、
    データごとに その時間のうちにもう一度来る確率 を人気の重みで足し合わせる式）。式と乱数の差も(1)で照らす
(3) 確かめ（偏り以外の違い）：試験のデータの件数が少ない（1万・2万・5万件）、試験が短く空の置き場所から始まる（2万・5万件）
"""
import json
import time
from collections import OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1160
SRC = "架空のアプリへの問い合わせ（作成者が置いた人気の偏りからの乱数、seed 1160）"
N_ITEMS = 100_000
WARM, MEAS = 100_000, 300_000
PROD_A = 0.8
SIZES_PCT = [1, 4]
GRID_A = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
SIM_TEST_A = [0.0, 0.6, 1.0]
CURVE_A = np.round(np.arange(0.0, 1.2001, 0.05), 2)
TEST_ITEMS = [10_000, 20_000, 50_000]
SHORT = [20_000, 50_000]
SHORT_REPS = 10
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def probs(n, a):
    p = 1.0 / np.arange(1, n + 1) ** a
    return p / p.sum()


def stream(rng, p, n):
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    return np.searchsorted(cdf, rng.random(n), side="right") + 1


def recent_hit(seq, cap, warm):
    c = OrderedDict()
    hits = 0
    for i, x in enumerate(seq.tolist()):
        if x in c:
            c.move_to_end(x)
            if i >= warm:
                hits += 1
        else:
            c[x] = None
            if len(c) > cap:
                c.popitem(last=False)
    return hits / (len(seq) - warm)


def hit_formula(p, cap):
    """置いておける時間 T を、sum(1−exp(−p×T)) が置き場所の大きさになるように決め、sum(p×(1−exp(−p×T))) を当たり率とする"""
    lo, hi = 1e-3, 1e12
    for _ in range(200):
        mid = np.sqrt(lo * hi)
        if np.sum(-np.expm1(-p * mid)) < cap:
            lo = mid
        else:
            hi = mid
    T = np.sqrt(lo * hi)
    return float(np.sum(p * -np.expm1(-p * T)))


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"items": N_ITEMS, "prod_alpha": PROD_A, "sizes_pct": SIZES_PCT, "warm": WARM, "measure": MEAS,
                       "grid_alpha": GRID_A, "test_items": TEST_ITEMS, "short_requests": SHORT, "short_reps": SHORT_REPS}}

    # (1) 乱数で数える
    sim = []
    for a in [PROD_A] + SIM_TEST_A:
        p = probs(N_ITEMS, a)
        seq = stream(rng, p, WARM + MEAS)
        for sz in SIZES_PCT:
            cap = N_ITEMS * sz // 100
            sim.append({"role": "本番" if a == PROD_A else "試験", "alpha": a, "items": N_ITEMS, "size_pct": sz, "size_items": cap,
                        "hit_sim_pct": r(recent_hit(seq, cap, WARM) * 100, 2), "hit_formula_pct": r(hit_formula(p, cap) * 100, 2)})
        if a == PROD_A:
            prod_seq = seq
    sim = pd.DataFrame(sim)
    sim["formula_minus_sim_pt"] = (sim.hit_formula_pct - sim.hit_sim_pct).round(2)
    prod_sim = {sz: sim[(sim.role == "本番") & (sim.size_pct == sz)].hit_sim_pct.iloc[0] for sz in SIZES_PCT}
    t = sim[sim.role == "試験"].copy()
    t["prod_hit_sim_pct"] = t.size_pct.map(prod_sim)
    t["test_minus_prod_pt"] = (t.hit_sim_pct - t.prod_hit_sim_pct).round(2)
    t["test_miss_over_prod_miss"] = ((100 - t.hit_sim_pct) / (100 - t.prod_hit_sim_pct)).round(3)
    sim.to_csv(RES / "sim_hit.csv", index=False)
    t.to_csv(RES / "sim_test_vs_prod.csv", index=False)
    out["sim"] = sim.to_dict("records")
    out["sim_test_vs_prod"] = t.to_dict("records")
    out["formula_check_max_abs_pt"] = r(sim.formula_minus_sim_pt.abs().max(), 2)
    print("sim", round(time.time() - T0, 1), flush=True)

    # (2) 式の7×7
    hf = {}
    for a in sorted(set(GRID_A) | set(CURVE_A.tolist())):
        p = probs(N_ITEMS, a)
        for sz in SIZES_PCT:
            hf[(round(a, 2), sz)] = hit_formula(p, N_ITEMS * sz // 100) * 100
    rows = []
    for sz in SIZES_PCT:
        for ap in GRID_A:
            for at in GRID_A:
                hp, ht = hf[(ap, sz)], hf[(at, sz)]
                rows.append({"size_pct": sz, "prod_alpha": ap, "test_alpha": at, "alpha_gap": r(at - ap, 1),
                             "prod_hit_pct": r(hp, 2), "test_hit_pct": r(ht, 2), "test_minus_prod_pt": r(ht - hp, 2),
                             "test_miss_over_prod_miss": r((100 - ht) / (100 - hp), 3)})
    g = pd.DataFrame(rows)
    g.to_csv(RES / "grid_formula.csv", index=False)
    gs = []
    for sz in SIZES_PCT:
        for gap in [-0.2, -0.1, 0.1, 0.2]:
            s = g[(g.size_pct == sz) & (np.isclose(g.alpha_gap, gap))]
            gs.append({"size_pct": sz, "alpha_gap": gap, "n": len(s),
                       "min_pt": float(s.test_minus_prod_pt.min()), "max_pt": float(s.test_minus_prod_pt.max()),
                       "miss_ratio_min": float(s.test_miss_over_prod_miss.min()), "miss_ratio_max": float(s.test_miss_over_prod_miss.max())})
    gs = pd.DataFrame(gs)
    gs.to_csv(RES / "grid_by_gap.csv", index=False)
    out["grid_by_gap"] = gs.to_dict("records")
    both = []
    for gap in [0.1, 0.2]:
        s = g[np.isclose(g.alpha_gap.abs(), gap)]
        both.append({"abs_alpha_gap": gap, "n": len(s), "abs_pt_min": float(s.test_minus_prod_pt.abs().min()),
                     "abs_pt_max": float(s.test_minus_prod_pt.abs().max())})
    out["grid_by_abs_gap_both_sizes"] = both
    out["grid_abs_max_pt"] = float(g.test_minus_prod_pt.abs().max())
    cv = pd.DataFrame([{"test_alpha": a, "size_pct": sz, "test_hit_formula_pct": r(hf[(round(a, 2), sz)], 2)}
                       for a in CURVE_A for sz in SIZES_PCT])
    cv.to_csv(RES / "curve_formula.csv", index=False)

    # (3) 偏り以外の違い
    ex = []
    for n_it in TEST_ITEMS:
        p = probs(n_it, PROD_A)
        seq = stream(rng, p, WARM + MEAS)
        for sz in SIZES_PCT:
            cap = N_ITEMS * sz // 100
            h = r(recent_hit(seq, cap, WARM) * 100, 2)
            ex.append({"case": f"試験のデータ {n_it:,}件", "kind": "items", "value": n_it, "size_pct": sz, "size_items": cap,
                       "test_hit_pct": h, "prod_hit_pct": prod_sim[sz], "test_minus_prod_pt": r(h - prod_sim[sz], 2),
                       "p10_pct": None, "p90_pct": None})
    p = probs(N_ITEMS, PROD_A)
    for n_req in SHORT:
        for sz in SIZES_PCT:
            cap = N_ITEMS * sz // 100
            hs = [recent_hit(stream(rng, p, n_req), cap, 0) * 100 for _ in range(SHORT_REPS)]
            m = r(np.mean(hs), 2)
            ex.append({"case": f"空から{n_req // 10000}万件だけ", "kind": "short", "value": n_req, "size_pct": sz, "size_items": cap,
                       "test_hit_pct": m, "prod_hit_pct": prod_sim[sz], "test_minus_prod_pt": r(m - prod_sim[sz], 2),
                       "p10_pct": r(np.percentile(hs, 10), 2), "p90_pct": r(np.percentile(hs, 90), 2)})
    ex = pd.DataFrame(ex)
    ex.to_csv(RES / "check_other_gaps.csv", index=False)
    out["check_other_gaps"] = ex.to_dict("records")
    print("check", round(time.time() - T0, 1), flush=True)

    # データ
    pd.DataFrame({"request_id": np.arange(1, 20001), "item_rank": prod_seq[WARM:WARM + 20000]}).to_csv(DATA / "requests_prod_head.csv", index=False)
    pd.DataFrame({"item_rank": np.arange(1, 1001),
                  **{f"prob_pct_a{a:g}": np.round(probs(N_ITEMS, a)[:1000] * 100, 5) for a in [0.6, 0.8, 1.0]}}).to_csv(
        DATA / "popularity_top1000.csv", index=False)

    # 図1：試験の偏りと測れる当たり率
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    for sz, col in zip(SIZES_PCT, [BLUE, ORANGE]):
        c = cv[cv.size_pct == sz]
        ax.plot(c.test_alpha, c.test_hit_formula_pct, color=col, label=f"置き場所{sz}%（式）")
        s = t[t.size_pct == sz]
        ax.plot(s.alpha, s.hit_sim_pct, "o", color=col, ms=5)
        ax.axhline(prod_sim[sz], color=col, lw=0.9, ls="--")
        ax.text(0.02, prod_sim[sz] + 1.2, f"本番（a=0.8）{prod_sim[sz]:.2f}%", fontsize=8.5, color=col)
        for _, rr in s.iterrows():
            if rr.alpha == 0:
                ax.text(0.03, 13.5 if sz == 4 else 8.5, f"a=0：{rr.hit_sim_pct:.2f}%", fontsize=8, color=col)
            else:
                ax.text(rr.alpha + 0.03, rr.hit_sim_pct - 3.5, f"{rr.hit_sim_pct:.2f}%", fontsize=8, color=col)
    ax.set_ylim(0, 100)
    ax.set_xlim(-0.02, 1.25)
    ax.set_xlabel("試験の環境の偏り a（本番は0.8）")
    ax.set_ylabel("試験で測れる当たり率（%）")
    ax.set_title("試験の偏りだけを変えたときの当たり率（点は乱数30万件）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0.0, 0.88))
    save(fig, "a1160_curve.png", SRC)

    # 図2：7×7（置き場所1%）
    fig, axs = plt.subplots(1, 2, figsize=(10.6, 4.6))
    for ax, sz in zip(axs, SIZES_PCT):
        m = g[g.size_pct == sz].pivot(index="prod_alpha", columns="test_alpha", values="test_minus_prod_pt")
        lim = float(np.abs(g.test_minus_prod_pt).max())
        im = ax.imshow(m.values, cmap="RdBu_r", norm=TwoSlopeNorm(0, -lim, lim), origin="lower")
        for i in range(len(GRID_A)):
            for j in range(len(GRID_A)):
                v = m.values[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5, color="white" if abs(v) > lim * 0.55 else INK)
        ax.set_xticks(range(len(GRID_A)), [f"{a:g}" for a in GRID_A], fontsize=8)
        ax.set_yticks(range(len(GRID_A)), [f"{a:g}" for a in GRID_A], fontsize=8)
        ax.set_xlabel("試験の偏り a")
        ax.set_ylabel("本番の偏り a")
        ax.set_title(f"置き場所{sz}%：試験 − 本番（ポイント、式）", fontsize=10.5)
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.tight_layout()
    save(fig, "a1160_grid.png", SRC)

    # 図3：偏り以外の違い
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    cases = list(dict.fromkeys(ex.case))
    w = 0.38
    for j, (sz, col) in enumerate(zip(SIZES_PCT, [BLUE, ORANGE])):
        v = [ex[(ex.case == c) & (ex.size_pct == sz)].test_minus_prod_pt.iloc[0] for c in cases]
        ax.bar(np.arange(len(cases)) + (j - 0.5) * w, v, w, color=col, label=f"置き場所{sz}%")
        for i, vv in enumerate(v):
            ax.text(i + (j - 0.5) * w, vv + (0.8 if vv >= 0 else -0.8), f"{vv:.2f}", ha="center",
                    va="bottom" if vv >= 0 else "top", fontsize=7.5)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(np.arange(len(cases)), [c.replace("試験のデータ ", "データ\n").replace("空から", "空から\n") for c in cases], fontsize=9)
    ax.set_ylim(ex.test_minus_prod_pt.min() * 1.3 - 2, ex.test_minus_prod_pt.max() * 1.25 + 2)
    ax.set_ylabel("試験 − 本番（ポイント）")
    ax.set_title("偏りは同じ（a=0.8）で、データの件数・試験の長さだけが違うとき")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1160_other_gaps.png", SRC)

    (RES / "a1160_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.item()))
    print(sim.to_string()); print(t.to_string()); print(gs.to_string()); print(ex.to_string())
    print("abs max", out["grid_abs_max_pt"], "formula chk", out["formula_check_max_abs_pt"])
    print("sec", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
