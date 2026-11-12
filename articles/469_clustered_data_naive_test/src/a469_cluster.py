"""469 同じ店の中で似ているデータを、ばらばらの件数として検定すると、効果0でも何%で「差あり」が出るか（シミュレーション、seed 469）"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *

SEED = 469
REP = 4000
SRC = "シミュレーション（作成者が乱数で作成、seed 469）"


def sim(rng, K, m, rho, effect=0.0, rep=REP):
    """店 K（半分に施策）、1店 m 件。店ごとに割り当て。店の平均と店の中の平方和だけを作る（全件を作るのと同じ分布）"""
    kt = K // 2
    u = rng.normal(0, np.sqrt(rho), (rep, K)) if rho > 0 else np.zeros((rep, K))
    ybar = u + rng.normal(0, np.sqrt((1 - rho) / m), (rep, K))          # 店の平均
    ybar[:, :kt] += effect
    ssw = (1 - rho) * rng.chisquare(m - 1, (rep, K))                    # 店の中の平方和
    t_mean, c_mean = ybar[:, :kt].mean(1), ybar[:, kt:].mean(1)
    diff = t_mean - c_mean
    # ① 1件ずつを独立として t 検定（等分散）
    ss_t = ssw[:, :kt].sum(1) + m * ((ybar[:, :kt] - t_mean[:, None]) ** 2).sum(1)
    ss_c = ssw[:, kt:].sum(1) + m * ((ybar[:, kt:] - c_mean[:, None]) ** 2).sum(1)
    n_t, n_c = kt * m, (K - kt) * m
    s2 = (ss_t + ss_c) / (n_t + n_c - 2)
    p_naive = 2 * stats.t.sf(np.abs(diff / np.sqrt(s2 * (1 / n_t + 1 / n_c))), n_t + n_c - 2)
    # ② 店ごとに平均してから t 検定
    v_t, v_c = ybar[:, :kt].var(1, ddof=1), ybar[:, kt:].var(1, ddof=1)
    sp = ((kt - 1) * v_t + (K - kt - 1) * v_c) / (K - 2)
    t2 = diff / np.sqrt(sp * (1 / kt + 1 / (K - kt)))
    p_store = 2 * stats.t.sf(np.abs(t2), K - 2)
    # ③ 固まりを考えた標準誤差（店でまとめた頑健な標準誤差。補正なし・正規分布で判定／小標本の補正つき・t分布で判定）
    v_cr = ((ybar[:, :kt] - t_mean[:, None]) ** 2).sum(1) / kt ** 2 + ((ybar[:, kt:] - c_mean[:, None]) ** 2).sum(1) / (K - kt) ** 2
    p_cr0 = 2 * stats.norm.sf(np.abs(diff / np.sqrt(v_cr)))
    p_cr1 = 2 * stats.t.sf(np.abs(diff / np.sqrt(v_cr * K / (K - 1))), K - 1)
    return {k: float(np.mean(p < 0.05) * 100) for k, p in [("naive", p_naive), ("store", p_store), ("cr0", p_cr0), ("cr1", p_cr1)]}


def sim_within(rng, K, m, rho, rep=2000):
    """件ごとに割り当てる場合（同じ店の中に施策あり・なしが混ざる）。全件を作って1件ずつの t 検定"""
    out = 0
    for _ in range(rep):
        u = rng.normal(0, np.sqrt(rho), K) if rho > 0 else np.zeros(K)
        y = np.repeat(u, m) + rng.normal(0, np.sqrt(1 - rho), K * m)
        g = rng.random(K * m) < 0.5
        out += stats.ttest_ind(y[g], y[~g]).pvalue < 0.05
    return out / rep * 100


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    RHOS = [0, 0.01, 0.02, 0.05, 0.1, 0.3]; MS = [10, 30, 100, 300, 1000]; KS = [20, 50, 200]
    rows = []
    for K in KS:
        for m in MS:
            for rho in RHOS:
                r = sim(rng, K, m, rho)
                deff = 1 + (m - 1) * rho
                rows.append(dict(店の数=K, 一店の件数=m, 似かたの強さ=rho, 全部の件数=K * m, 実質の件数=round(K * m / deff), デザイン効果=round(deff, 2),
                                 空振り_1件ずつ=round(r["naive"], 1), 空振り_店の平均=round(r["store"], 1), 空振り_固まりの標準誤差_補正なし=round(r["cr0"], 1),
                                 空振り_固まりの標準誤差_補正つき=round(r["cr1"], 1),
                                 式の見込み_1件ずつ=round(2 * stats.norm.sf(1.96 / np.sqrt(deff)) * 100, 1)))
    fp = pd.DataFrame(rows); fp.to_csv(RES / "false_positive.csv", index=False)
    # 店の数が少ないとき
    rows = []
    for K in (6, 10, 20, 50, 200):
        r = sim(rng, K, 100, 0.05, rep=8000)
        rows.append(dict(店の数=K, 空振り_1件ずつ=round(r["naive"], 1), 空振り_店の平均=round(r["store"], 1), 空振り_固まりの標準誤差_補正なし=round(r["cr0"], 1), 空振り_固まりの標準誤差_補正つき=round(r["cr1"], 1)))
    few = pd.DataFrame(rows); few.to_csv(RES / "few_stores.csv", index=False)
    # 検出力（本当に差が0.1標準偏差あるとき）
    rows = []
    for K in (20, 50, 200):
        for rho in (0, 0.05):
            for m in MS:
                r = sim(rng, K, m, rho, effect=0.1)
                rows.append(dict(店の数=K, 似かたの強さ=rho, 一店の件数=m, 検出力_店の平均=round(r["store"], 1), 検出力_固まりの標準誤差_補正つき=round(r["cr1"], 1), 差ありの割合_1件ずつ=round(r["naive"], 1)))
    pw = pd.DataFrame(rows); pw.to_csv(RES / "power.csv", index=False)
    # 件ごとに割り当てる場合
    rows = [dict(割り当て="件ごと", 店の数=50, 一店の件数=100, 似かたの強さ=rho, 空振り_1件ずつ=round(sim_within(rng, 50, 100, rho), 1)) for rho in (0, 0.05, 0.1, 0.3)]
    wi = pd.DataFrame(rows); wi.to_csv(RES / "assigned_within_store.csv", index=False)
    # 例のデータ
    u = rng.normal(0, np.sqrt(0.05), 6)
    ex = pd.DataFrame({"店": np.repeat([f"店{i+1}" for i in range(6)], 5), "施策": np.repeat(["あり"] * 3 + ["なし"] * 3, 5),
                       "値": np.round(np.repeat(u, 5) + rng.normal(0, np.sqrt(0.95), 30), 3)})
    ex.to_csv(DATA / "example_rows.csv", index=False)

    # 図1：1件ずつの検定の空振り
    fig, ax = plt.subplots(figsize=(8.4, 4.4)); d = fp[fp.店の数 == 50]
    cols = {0: GRAY, 0.01: LIGHT, 0.02: "#7fb0e6", 0.05: BLUE, 0.1: ORANGE, 0.3: "#b23a0e"}
    for rho in RHOS:
        dd = d[d.似かたの強さ == rho]; ax.plot(dd.一店の件数, dd.空振り_1件ずつ, "o-", color=cols[rho], label=f"似かたの強さ {rho}")
        ax.text(1080, dd.空振り_1件ずつ.iloc[-1], f"{dd.空振り_1件ずつ.iloc[-1]:.0f}%", fontsize=8, va="center", color=cols[rho])
    ax.axhline(5, color=INK, lw=1, ls="--"); ax.text(8.3, -1.5, "点線＝ねらいの5%", fontsize=8.5); ax.set_ylim(-5, 97)
    ax.set_xscale("log"); ax.set_xticks(MS); ax.set_xticklabels([str(m) for m in MS]); ax.set_xlim(8, 1500)
    ax.set_xlabel("1店あたりの件数（対数の目盛り）"); ax.set_ylabel("効果0なのに「差あり」と出た割合（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
    ax.set_title("1件ずつを独立として検定したときの空振り（50店、店ごとに割り当て）")
    save(fig, "a469_naive_false_positive.png", SRC + "。各4,000回")
    # 図2：3つの方法
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]; d = fp[(fp.一店の件数 == 100) & (fp.似かたの強さ == 0.05)]; x = np.arange(3); w = 0.2
    for i, (c, lab, col) in enumerate([("空振り_1件ずつ", "1件ずつを独立として検定", ORANGE), ("空振り_店の平均", "店ごとに平均してから検定", BLUE),
                                       ("空振り_固まりの標準誤差_補正なし", "固まりを考えた標準誤差（補正なし）", GRAY), ("空振り_固まりの標準誤差_補正つき", "固まりを考えた標準誤差（補正つき）", GREEN)]):
        b = ax.bar(x + (i - 1.5) * w, d[c], w, color=col, label=lab)
        for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.6, f"{r.get_height():.1f}", ha="center", fontsize=8)
    ax.axhline(5, color=INK, lw=1, ls="--"); ax.set_xticks(x); ax.set_xticklabels(["20店", "50店", "200店"]); ax.set_ylabel("効果0なのに「差あり」と出た割合（%）")
    ax.set_ylim(0, 72); ax.legend(frameon=False, fontsize=8, loc="upper right"); ax.set_title("3つの方法（1店100件、似かたの強さ0.05）", fontsize=11)
    ax = axes[1]
    for c, lab, col in [("空振り_店の平均", "店ごとに平均してから検定", BLUE), ("空振り_固まりの標準誤差_補正なし", "固まりを考えた標準誤差（補正なし）", GRAY), ("空振り_固まりの標準誤差_補正つき", "固まりを考えた標準誤差（補正つき）", GREEN)]:
        ax.plot(range(len(few)), few[c], "o-", color=col, label=lab)
    ax.axhline(5, color=INK, lw=1, ls="--"); ax.set_xticks(range(len(few))); ax.set_xticklabels([f"{k}店" for k in few.店の数]); ax.set_ylabel("空振りの割合（%）"); ax.set_ylim(0, 16)
    ax.legend(frameon=False, fontsize=8); ax.set_title("店の数が少ないとき", fontsize=11)
    save(fig, "a469_three_methods.png", SRC)
    # 図3：検出力
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), sharey=True)
    for ax, rho in zip(axes, (0, 0.05)):
        for K, col in [(20, LIGHT), (50, BLUE), (200, ORANGE)]:
            d = pw[(pw.店の数 == K) & (pw.似かたの強さ == rho)]; ax.plot(d.一店の件数, d.検出力_店の平均, "o-", color=col, label=f"{K}店")
        ax.set_xscale("log"); ax.set_xticks(MS); ax.set_xticklabels([str(m) for m in MS]); ax.set_xlabel("1店あたりの件数（対数の目盛り）")
        ax.set_title(f"似かたの強さ {rho}", fontsize=11); ax.set_ylim(0, 105)
    axes[0].set_ylabel("本当の差（0.1標準偏差）を見つけた割合（%）"); axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("店ごとに平均してから検定したときの検出力", y=1.02)
    save(fig, "a469_power.png", SRC + "。各4,000回")

    g = lambda K, m, rho, c: float(fp[(fp.店の数 == K) & (fp.一店の件数 == m) & (fp.似かたの強さ == rho)][c].iloc[0])
    main = {"naive_K50": {f"m{m}_rho{rho}": g(50, m, rho, "空振り_1件ずつ") for m in MS for rho in RHOS},
            "deff": {f"m{m}_rho{rho}": round(1 + (m - 1) * rho, 2) for m in MS for rho in RHOS},
            "methods_m100_rho005": fp[(fp.一店の件数 == 100) & (fp.似かたの強さ == 0.05)].to_dict("records"), "few": few.to_dict("records"),
            "within": wi.to_dict("records"), "power": pw.to_dict("records"),
            "max_store_mean": float(fp.空振り_店の平均.max()), "min_store_mean": float(fp.空振り_店の平均.min())}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(fp[fp.店の数 == 50].pivot(index="似かたの強さ", columns="一店の件数", values="空振り_1件ずつ"))
    print(fp[fp.店の数 == 50].pivot(index="似かたの強さ", columns="一店の件数", values="式の見込み_1件ずつ"))
    print(fp[fp.店の数 == 50].pivot(index="似かたの強さ", columns="一店の件数", values="実質の件数"))
    print(fp[(fp.一店の件数 == 100) & (fp.似かたの強さ == 0.05)].to_string()); print(few.to_string()); print(wi.to_string())
    print(pw.pivot_table(index=["似かたの強さ", "店の数"], columns="一店の件数", values="検出力_店の平均"))
    print(pw.pivot_table(index=["似かたの強さ", "店の数"], columns="一店の件数", values="差ありの割合_1件ずつ"))
    print(main["max_store_mean"], main["min_store_mean"], fp.空振り_固まりの標準誤差_補正つき.min(), fp.空振り_固まりの標準誤差_補正つき.max())
