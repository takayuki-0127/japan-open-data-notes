"""1312 値の種類が台数の数倍しかない項目（店の番号など）で振り分けると、いちばん多い1台は平均の何倍になるのか？（架空のデータ）

作成者が置いた架空のアプリの記録10万件。記録は S の店（基本30店）のどれかに属し、10台に振り分ける。
店ごとの記録の数は、対数でばらつき sigma（基本1.0）の右に長い乱数の重みで10万件を割り振る（sigma=0 なら同じ大きさ）。
振り分け方：
  ① 店の番号を混ぜた値の余り（店ごとに台が乱数で決まるのと同じ）
  ② 店の番号（1から順の番号）を台数で割った余り
  ③ 店の記録の数を見て、大きい店から順に、それまでの記録の数がいちばん少ない台へ（店は分けない）
  ④ 記録の番号の余り（値の種類が多い項目で振り分ける）
いちばん多い1台÷平均（＝10万÷台数）を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1312
SRC = "架空のアプリの記録（作成者が置いた店ごとの記録の数と振り分けの決まりからの乱数、seed 1312）"
N = 100_000
METHODS = ["m1_shop_mixed", "m2_shop_mod", "m3_shop_largest_first", "m4_record_id"]
LABELS = ["①店の番号を混ぜた値の余り", "②店の番号（1から順）の余り", "③大きい店から空いた台へ", "④記録の番号の余り"]
COLS = [ORANGE, "#c08a2a", GREEN, GRAY]


def loads_by(machine, counts, M):
    """machine: (R,S) の台、counts: (R,S) の記録の数 → (R,M) の台ごとの記録の数"""
    R = counts.shape[0]
    idx = (np.arange(R)[:, None] * M + machine).ravel()
    return np.bincount(idx, weights=counts.ravel(), minlength=R * M).reshape(R, M)


def simulate(rng, R, S, M, sigma):
    w = rng.lognormal(0, sigma, (R, S)) if sigma > 0 else np.ones((R, S))
    p = w / w.sum(1, keepdims=True)
    counts = rng.multinomial(N, p).astype(float)
    out = {}
    m1 = rng.integers(0, M, (R, S))
    out["m1_shop_mixed"] = loads_by(m1, counts, M)
    m2 = np.broadcast_to(np.arange(S) % M, (R, S))
    out["m2_shop_mod"] = loads_by(m2, counts, M)
    order = np.argsort(-counts, 1)
    sc = np.take_along_axis(counts, order, 1)
    ld = np.zeros((R, M))
    rr = np.arange(R)
    for j in range(S):
        k = np.argmin(ld, 1)
        ld[rr, k] += sc[:, j]
    out["m3_shop_largest_first"] = ld
    out["m4_record_id"] = rng.multinomial(N, np.full(M, 1 / M), R).astype(float)
    mean = N / M
    ratio = {m: out[m].max(1) / mean for m in METHODS}
    extra = {"largest_shop_vs_average": counts.max(1) / mean,
             "m1_machines_without_shop": (np.bincount((np.arange(R)[:, None] * M + m1).ravel(), minlength=R * M).reshape(R, M) == 0).sum(1)}
    return ratio, extra, counts, m1, out


def q(a, p):
    return round(float(np.quantile(a, p)), 3)


def main():
    t0 = time.time()
    R, S, M, SIG = 2000, 30, 10, 1.0

    # 基本の置き方
    rng = np.random.default_rng([SEED, 1])
    ratio, extra, counts, m1, out = simulate(rng, R, S, M, SIG)
    base = {}
    rows = []
    for i, m in enumerate(METHODS):
        base[m] = {"label": LABELS[i], "busiest_vs_average_mean": round(float(ratio[m].mean()), 3),
                   "p10": q(ratio[m], 0.1), "p90": q(ratio[m], 0.9),
                   "share_over_1_5x_pct": round(float((ratio[m] >= 1.5).mean()) * 100, 2),
                   "share_over_2x_pct": round(float((ratio[m] >= 2.0).mean()) * 100, 2)}
        rows.append({"method": LABELS[i], **{k: v for k, v in base[m].items() if k != "label"}})
    pd.DataFrame(rows).to_csv(RES / "base_by_method.csv", index=False)
    base["largest_shop_vs_average_mean"] = round(float(extra["largest_shop_vs_average"].mean()), 3)
    base["largest_shop_over_average_pct"] = round(float((extra["largest_shop_vs_average"] > 1).mean()) * 100, 2)
    base["m3_equals_largest_shop_pct"] = round(float(np.isclose(ratio["m3_shop_largest_first"], extra["largest_shop_vs_average"]).mean()) * 100, 2)
    base["m1_machines_without_shop_mean"] = round(float(extra["m1_machines_without_shop"].mean()), 3)
    base["m1_any_machine_without_shop_pct"] = round(float((extra["m1_machines_without_shop"] > 0).mean()) * 100, 2)
    base["m1_machines_without_shop_formula"] = round(float(M * (1 - 1 / M) ** S), 3)                  # 式どおりの期待値

    # 1回分（data に置く）
    pd.DataFrame({"shop": np.arange(1, S + 1), "records": counts[0].astype(int),
                  "machine_m1": m1[0], "machine_m2": np.arange(S) % M}).to_csv(DATA / "shops_one_set.csv", index=False)
    one = pd.DataFrame({"machine": np.arange(M), **{m: out[m][0].astype(int) for m in METHODS}})
    one.to_csv(RES / "one_set_machines.csv", index=False)

    # 店の大きさが同じとき（sigma=0）
    rng = np.random.default_rng([SEED, 2])
    r0, e0, _, _, _ = simulate(rng, R, S, M, 0.0)
    equal = {m: {"busiest_vs_average_mean": round(float(r0[m].mean()), 3), "p10": q(r0[m], 0.1), "p90": q(r0[m], 0.9)} for m in METHODS}
    equal["m1_machines_without_shop_mean"] = round(float(e0["m1_machines_without_shop"].mean()), 3)

    # 店の数を変える（台10、sigma 0 と 1.0、各2,000回）
    srows = []
    for sig in [0.0, 1.0]:
        for mult in [1, 2, 3, 5, 10, 30, 100]:
            rg = np.random.default_rng([SEED, 3, int(sig * 10), mult])
            rr, ee, _, _, _ = simulate(rg, R, mult * M, M, sig)
            srows.append({"sigma": sig, "shops": mult * M, "shops_per_machine": mult,
                          **{f"{m}_mean": round(float(rr[m].mean()), 3) for m in METHODS},
                          "largest_shop_vs_average_mean": round(float(ee["largest_shop_vs_average"].mean()), 3)})
    sr = pd.DataFrame(srows)
    sr.to_csv(RES / "by_shops.csv", index=False)

    # 確かめ：店の数（台の1〜100倍）×店の大きさのばらつき（0・0.5・1.0・1.5）×台数（10・50）の56通り（各400回）
    grid = []
    for mm in [10, 50]:
        for sig in [0.0, 0.5, 1.0, 1.5]:
            for mult in [1, 2, 3, 5, 10, 30, 100]:
                rg = np.random.default_rng([SEED, 4, mm, int(sig * 10), mult])
                rr, ee, _, _, _ = simulate(rg, 400, mult * mm, mm, sig)
                grid.append({"machines": mm, "sigma": sig, "shops_per_machine": mult,
                             **{f"{m}_mean": round(float(rr[m].mean()), 3) for m in METHODS},
                             "largest_shop_vs_average_mean": round(float(ee["largest_shop_vs_average"].mean()), 3)})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    g3 = gr[gr.shops_per_machine <= 5]
    robust = {"settings": int(len(gr)),
              "m1_range": [float(gr.m1_shop_mixed_mean.min()), float(gr.m1_shop_mixed_mean.max())],
              "m1_range_upto_5x": [float(g3.m1_shop_mixed_mean.min()), float(g3.m1_shop_mixed_mean.max())],
              "m2_range": [float(gr.m2_shop_mod_mean.min()), float(gr.m2_shop_mod_mean.max())],
              "m3_range": [float(gr.m3_shop_largest_first_mean.min()), float(gr.m3_shop_largest_first_mean.max())],
              "m4_range": [float(gr.m4_record_id_mean.min()), float(gr.m4_record_id_mean.max())],
              "m1_over_1_5x_count": int((gr.m1_shop_mixed_mean >= 1.5).sum()),
              "m1_over_1_5x_count_upto_5x": int((g3.m1_shop_mixed_mean >= 1.5).sum()), "settings_upto_5x": int(len(g3)),
              "m3_lt_m1_count": int((gr.m3_shop_largest_first_mean < gr.m1_shop_mixed_mean).sum()),
              "m1_at_100x_range": [float(gr[gr.shops_per_machine == 100].m1_shop_mixed_mean.min()), float(gr[gr.shops_per_machine == 100].m1_shop_mixed_mean.max())]}

    out_json = {"base": base, "equal_size_shops": equal, "robust": robust,
                "setup": {"records": N, "shops": S, "machines": M, "shop_size_sigma_log": SIG, "reps": R, "grid_reps": 400}}
    json.dump(out_json, open(RES / "a1312_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の台ごとの記録の数
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(M)
    for i, m in enumerate(METHODS):
        ax.bar(x + (i - 1.5) * 0.2, out[m][0] / 1000, 0.2, color=COLS[i], label=LABELS[i])
    ax.axhline(N / M / 1000, color=GRAY, lw=0.8, ls="--", label="平均（1万件）")
    ax.set_xticks(x); ax.set_xticklabels([f"{i+1}台目" for i in x], fontsize=9)
    ax.set_ylim(0, float(max(out[m][0].max() for m in METHODS)) / 1000 * 1.15)
    ax.set_ylabel("台ごとの記録の数（千件）")
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax.set_title("30店を10台に分けた1回分（店の大きさのばらつき1.0）", fontsize=12)
    save(fig, "a1312_one_set.png", SRC, y=-0.2)

    # 図2：店の数を変える
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.2), sharey=True)
    for a, sig, ttl in [(axs[0], 0.0, "店の大きさが同じ"), (axs[1], 1.0, "店の大きさがばらつく（1.0）")]:
        d = sr[sr.sigma == sig]
        xx = np.arange(len(d))
        for i, m in enumerate(METHODS):
            a.plot(xx, d[f"{m}_mean"], "o-", color=COLS[i], ms=4, lw=1, label=LABELS[i])
        a.axhline(1, color=GRAY, lw=0.8, ls="--")
        a.set_xticks(xx); a.set_xticklabels([f"{v}倍" for v in d.shops_per_machine], fontsize=9)
        a.set_xlabel("店の数（台数の何倍か）", fontsize=9.5)
        a.set_title(ttl, fontsize=11)
    axs[0].set_ylim(0, float(sr[[f"{m}_mean" for m in METHODS]].max().max()) * 1.1)
    axs[0].set_ylabel("いちばん多い1台÷平均（2,000回の平均）", fontsize=9.5)
    axs[0].legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(1.05, -0.15))
    fig.suptitle("店の数が台数の数倍しかないと、いちばん多い1台は平均を大きく超える（10台）", fontsize=12, y=1.03)
    save(fig, "a1312_by_shops.png", SRC, y=-0.17)

    # 図3：56通り（①と③）
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    gx = np.arange(len(gr))
    for i, m in enumerate(METHODS):
        for kk in range(8):  # 条件の組ごとに線を切る（組をまたいで線を結ばない）
            sl = slice(kk * 7, kk * 7 + 7)
            ax.plot(gx[sl], gr[f"{m}_mean"].values[sl], "o-", color=COLS[i], ms=3, lw=0.8,
                    label=LABELS[i] if kk == 0 else None)
    for kk in range(1, 8):
        ax.axvline(kk * 7 - 0.5, color=GRAY, lw=0.6, ls=":")
    ymax = float(gr[[f"{m}_mean" for m in METHODS]].max().max()) * 1.15
    ax.set_ylim(0, ymax)
    for kk in range(8):
        mm = 10 if kk < 4 else 50
        sg = [0.0, 0.5, 1.0, 1.5][kk % 4]
        ax.text(kk * 7 + 3, ymax * 0.95, f"{mm}台\nばらつき{sg}", ha="center", va="top", fontsize=7)
    ax.axhline(1, color=GRAY, lw=0.8, ls="--")
    ax.set_xticks(gx); ax.set_xticklabels([f"{v}" for v in gr.shops_per_machine], fontsize=5.5, rotation=90)
    ax.set_xlabel("56通り（下は「店の数が台数の何倍か」）", fontsize=8.5)
    ax.set_ylabel("いちばん多い1台÷平均（各400回の平均）", fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    ax.set_title("店の数を増やすほど1倍に近づくが、ばらつきが大きいと③でも下がりきらない", fontsize=11)
    save(fig, "a1312_grid.png", SRC, y=-0.27)

    print(json.dumps(out_json, ensure_ascii=False, indent=1))
    print(sr.to_string()); print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
