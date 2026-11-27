"""1308 輪の上に並べる振り分けで1台足すと、動く量は少なくても、台ごとの受け持ちはどれだけばらつくのか？（架空のデータ）

作成者が置いた架空のアプリのデータ（基本10万件）を、台（基本10台）に振り分ける。
輪の上に並べる振り分け：データも台も、番号から決まる「輪の上の位置」（0〜1の一様な乱数で置く）を持ち、
データは輪を時計回りに進んで最初に出会う台に置く。1台は輪の上に1か所だけ置く（何か所にも分けて置く形は 1309）。
台の位置を作り直して2,000回くり返す（データの位置は1回だけ作る）。
1台足す：11台目の位置を乱数で1か所置く。11台目より反時計回りのとなりの台までのデータが、11台目へ動く。
目安（式）：n 台の受け持ち（輪の長さ）のうち最大は、平均で平均の H_n 倍（H_n＝1＋1/2＋…＋1/n）。
確かめ：台数（5・10・20・50・100）×データの件数（1万・10万・100万）の15通り（各1,000回）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1308
SRC = "架空のアプリのデータ（作成者が置いた件数・台数と、輪の上の位置の乱数、seed 1308）"
N_BASE = 100_000
K_BASE = 10
TRIALS = 2000
TRIALS_GRID = 1000


def counts_on_ring(keys_sorted, pts):
    """台の位置 pts（1台1か所）に対する台ごとの件数。データは時計回りで次の台へ。"""
    order = np.argsort(pts)
    p = pts[order]
    c = np.searchsorted(keys_sorted, p, side="right")
    cnt = np.empty(len(p), np.int64)
    cnt[1:] = c[1:] - c[:-1]
    cnt[0] = c[0] + (len(keys_sorted) - c[-1])   # 最後の台の先から輪をまわって最初の台まで
    out = np.empty(len(p), np.int64)
    out[order] = cnt
    return out


def harmonic(n):
    return float(np.sum(1.0 / np.arange(1, n + 1)))


def one_setting(rng, n_keys, k, trials):
    keys = np.sort(rng.random(n_keys))
    rows = []
    for t in range(trials):
        pts = rng.random(k)
        before = counts_on_ring(keys, pts)
        new = rng.random()
        after = counts_on_ring(keys, np.append(pts, new))
        moved = int(after[-1])
        giver = np.flatnonzero(after[:-1] < before)          # データを渡した台
        busiest = int(np.argmax(before))
        mean_b = n_keys / k
        mean_a = n_keys / (k + 1)
        rows.append(dict(
            trial=t,
            max_ratio_before=before.max() / mean_b,
            min_ratio_before=before.min() / mean_b,
            cv_before=before.std() / mean_b,
            moved_share=moved / n_keys,
            new_vs_even=moved / mean_a,
            n_givers=len(giver),
            busiest_gave=bool(busiest in giver),
            max_ratio_after=after.max() / mean_a,
            max_count_before=int(before.max()),
            max_count_after=int(after.max()),
            max_count_drop_pct=(before.max() - after.max()) / before.max() * 100,
        ))
    return pd.DataFrame(rows), keys


def q(x, p):
    return float(np.quantile(x, p))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # ---- 基本：10万件・10台 ----
    df, keys = one_setting(rng, N_BASE, K_BASE, TRIALS)
    df_out = df.copy()
    for c in ["max_ratio_before", "min_ratio_before", "cv_before", "moved_share", "new_vs_even",
              "max_ratio_after", "max_count_drop_pct"]:
        df_out[c] = df_out[c].round(4)
    df_out.to_csv(RES / "base_trials.csv", index=False)

    even_moved = 1 / (K_BASE + 1)
    base = dict(
        n_keys=N_BASE, servers=K_BASE, trials=TRIALS,
        even_moved_share_pct=round(even_moved * 100, 2),
        even_per_server_before=N_BASE // K_BASE,
        moved_share_mean_pct=round(df.moved_share.mean() * 100, 2),
        moved_share_median_pct=round(q(df.moved_share, 0.5) * 100, 2),
        moved_share_p10_pct=round(q(df.moved_share, 0.1) * 100, 2),
        moved_share_p90_pct=round(q(df.moved_share, 0.9) * 100, 2),
        moved_share_max_pct=round(df.moved_share.max() * 100, 2),
        moved_under_half_even_pct=round((df.moved_share < even_moved / 2).mean() * 100, 2),
        moved_over_double_even_pct=round((df.moved_share > even_moved * 2).mean() * 100, 2),
        n_givers_one_pct=round((df.n_givers == 1).mean() * 100, 2),
        max_ratio_before_mean=round(df.max_ratio_before.mean(), 3),
        max_ratio_before_p10=round(q(df.max_ratio_before, 0.1), 3),
        max_ratio_before_p90=round(q(df.max_ratio_before, 0.9), 3),
        formula_max_ratio_Hn=round(harmonic(K_BASE), 3),
        min_ratio_before_mean=round(df.min_ratio_before.mean(), 3),
        min_ratio_before_median=round(q(df.min_ratio_before, 0.5), 3),
        cv_before_mean=round(df.cv_before.mean(), 3),
        max_ratio_after_mean=round(df.max_ratio_after.mean(), 3),
        max_ratio_after_p10=round(q(df.max_ratio_after, 0.1), 3),
        max_ratio_after_p90=round(q(df.max_ratio_after, 0.9), 3),
        formula_max_ratio_H11=round(harmonic(K_BASE + 1), 3),
        busiest_gave_pct=round(df.busiest_gave.mean() * 100, 2),
        busiest_share_mean_pct=round(df.max_ratio_before.mean() / K_BASE * 100, 2),
        max_count_unchanged_pct=round((df.max_count_after == df.max_count_before).mean() * 100, 2),
        max_count_drop_mean_pct=round(df.max_count_drop_pct.mean(), 2),
        max_count_before_mean=round(df.max_count_before.mean(), 1),
        max_count_after_mean=round(df.max_count_after.mean(), 1),
    )

    # 1回目の例
    rng_ex = np.random.default_rng(SEED + 1)
    pts = rng_ex.random(K_BASE)
    new = rng_ex.random()
    b = counts_on_ring(keys, pts)
    a = counts_on_ring(keys, np.append(pts, new))
    ex = pd.DataFrame(dict(server=[f"台{i+1}" for i in range(K_BASE)] + ["台11（足した台）"],
                           position=np.round(np.append(pts, new), 4),
                           count_before=np.append(b, 0), count_after=a))
    ex.to_csv(DATA / "example_one_trial.csv", index=False)
    base["example_moved"] = int(a[-1])
    base["example_max_before"] = int(b.max())
    base["example_min_before"] = int(b.min())
    base["example_max_after"] = int(a.max())

    # ---- 確かめ：15通り ----
    grid = []
    for k in [5, 10, 20, 50, 100]:
        for n_keys in [10_000, 100_000, 1_000_000]:
            g, _ = one_setting(rng, n_keys, k, TRIALS_GRID)
            grid.append(dict(
                servers=k, n_keys=n_keys,
                even_moved_share_pct=round(100 / (k + 1), 3),
                moved_share_mean_pct=round(g.moved_share.mean() * 100, 3),
                moved_share_p10_pct=round(q(g.moved_share, 0.1) * 100, 3),
                moved_share_p90_pct=round(q(g.moved_share, 0.9) * 100, 3),
                max_ratio_before_mean=round(g.max_ratio_before.mean(), 3),
                formula_Hn=round(harmonic(k), 3),
                min_ratio_before_mean=round(g.min_ratio_before.mean(), 3),
                busiest_gave_pct=round(g.busiest_gave.mean() * 100, 2),
                max_count_unchanged_pct=round((g.max_count_after == g.max_count_before).mean() * 100, 2),
            ))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    robust = dict(
        moved_mean_minus_even_pt_min=round(float((grid.moved_share_mean_pct - grid.even_moved_share_pct).min()), 3),
        moved_mean_minus_even_pt_max=round(float((grid.moved_share_mean_pct - grid.even_moved_share_pct).max()), 3),
        max_ratio_min=float(grid.max_ratio_before_mean.min()),
        max_ratio_max=float(grid.max_ratio_before_mean.max()),
        max_ratio_minus_Hn_min=round(float((grid.max_ratio_before_mean - grid.formula_Hn).min()), 3),
        max_ratio_minus_Hn_max=round(float((grid.max_ratio_before_mean - grid.formula_Hn).max()), 3),
        busiest_gave_pct_min=float(grid.busiest_gave_pct.min()),
        busiest_gave_pct_max=float(grid.busiest_gave_pct.max()),
        max_unchanged_pct_min=float(grid.max_count_unchanged_pct.min()),
        max_unchanged_pct_max=float(grid.max_count_unchanged_pct.max()),
    )
    for k in [5, 10, 20, 50, 100]:
        s = grid[grid.servers == k]
        robust[f"max_ratio_k{k}_range"] = [float(s.max_ratio_before_mean.min()), float(s.max_ratio_before_mean.max())]

    # ---- 図 ----
    # 1 例：1回分の台ごとの件数（足す前・足した後）
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = np.arange(K_BASE + 1)
    ax.bar(x - 0.2, ex.count_before, 0.4, color=LIGHT, label="10台のとき")
    ax.bar(x + 0.2, ex.count_after, 0.4, color=BLUE, label="1台足して11台のとき")
    ax.axhline(N_BASE / K_BASE, color=GRAY, ls="--", lw=1)
    ax.text(K_BASE + 0.5, N_BASE / K_BASE, "平均（10台）", color=GRAY, fontsize=8, va="bottom", ha="right")
    ax.set_xticks(x, [f"{i+1}" for i in range(K_BASE)] + ["11\n(足した台)"])
    ax.set_xlabel("台")
    ax.set_ylabel("受け持つデータの件数")
    ax.set_ylim(0, None)
    ax.set_title("1回分の例：足した台は1台からだけ受け取り、ほかの台は変わらない")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1308_example.png", SRC, y=-0.07)

    # 2 動いた割合の分布
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.hist(df.moved_share * 100, bins=np.arange(0, 66, 1), color=BLUE, alpha=0.85)
    ax.axvline(even_moved * 100, color=ORANGE, lw=1.5)
    ax.text(even_moved * 100 + 0.5, ax.get_ylim()[1] * 0.92, f"受け持ちがそろうときの{even_moved*100:.2f}%",
            color=ORANGE, fontsize=9)
    ax.set_xlabel("1台足したときに動いたデータの割合（%）")
    ax.set_ylabel("回数（2,000回のうち）")
    ax.set_title("動いた割合は平均で約1/11だが、回ごとに大きく散らばる")
    save(fig, "a1308_moved_hist.png", SRC, y=-0.03)

    # 3 台数といちばん多い1台の比
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    for n_keys, col in [(10_000, LIGHT), (100_000, BLUE), (1_000_000, INK)]:
        s = grid[grid.n_keys == n_keys]
        ax.plot(s.servers, s.max_ratio_before_mean, "o-", color=col, label=f"データ{n_keys:,}件", ms=4)
    ks = np.array([5, 10, 20, 50, 100])
    ax.plot(ks, [harmonic(k) for k in ks], ":", color=ORANGE, label="目安の式（1＋1/2＋…＋1/台数）")
    ax.set_xscale("log")
    ax.set_xticks(ks, [str(k) for k in ks])
    ax.set_ylim(0, None)
    ax.set_xlabel("台数（1台1か所）")
    ax.set_ylabel("いちばん多い1台÷平均（1,000回の平均）")
    ax.set_title("台数が多いほど、いちばん多い1台は平均から離れる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1308_by_servers.png", SRC)

    main_json = dict(base=base, robust=robust)
    (RES / "a1308_main.json").write_text(json.dumps(main_json, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
