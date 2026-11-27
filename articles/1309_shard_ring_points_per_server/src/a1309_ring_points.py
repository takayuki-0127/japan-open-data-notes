"""1309 輪の上に1台を何か所に分けて置くかで、いちばん多い1台の受け持ちはどれだけ平均に近づくのか？（架空のデータ）

作成者が置いた架空のアプリのデータ（基本10万件）を、台（基本10台）に「輪の上に並べる振り分け」で置く。
データも台の置き場所も、輪の上の位置を0〜1の一様な乱数で置き、データは時計回りで最初に出会う置き場所の台へ。
1台を輪の上に v か所（1・2・5・10・20・50・100・200・500・1000）に分けて置く。台の受け持ちは v か所の合計。
台の位置を作り直して1,000回（データの位置は1回だけ作る）。
いちばん多い1台÷平均を、件数で数えたもの（件数）と、輪の長さで数えたもの（データが限りなく多いとき）で出す。
参考の下限：データ1件ずつ、どの台にも同じ確率で乱数で置いたとき（輪を使わない）のいちばん多い1台÷平均。
1台足す：11台目を同じ v か所に置き、動いた割合・データを渡した台の数・渡した量のいちばん多い台の割合を数える。
確かめ：台数（10・50・100）×データの件数（1万・10万・100万）の9通り、各 v で300回。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1309
SRC = "架空のアプリのデータ（作成者が置いた件数・台数・置き場所の数と、輪の上の位置の乱数、seed 1309）"
N_BASE = 100_000
K_BASE = 10
VS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
TRIALS = 1000
TRIALS_GRID = 300


def ring_counts(keys_sorted, pts, owner, k):
    """置き場所 pts（台 owner）に対する台ごとの件数と輪の長さ。"""
    order = np.argsort(pts)
    p = pts[order]
    o = owner[order]
    c = np.searchsorted(keys_sorted, p, side="right")
    cnt = np.empty(len(p), np.int64)
    cnt[1:] = c[1:] - c[:-1]
    cnt[0] = c[0] + (len(keys_sorted) - c[-1])
    arc = np.empty(len(p))
    arc[1:] = p[1:] - p[:-1]
    arc[0] = p[0] + 1 - p[-1]
    return np.bincount(o, weights=cnt, minlength=k), np.bincount(o, weights=arc, minlength=k)


def run(rng, keys, k, v, trials, add=True):
    n = len(keys)
    owner = np.repeat(np.arange(k), v)
    owner_a = np.repeat(np.arange(k + 1), v)
    out = []
    for _ in range(trials):
        pts = rng.random(k * v)
        cb, ab = ring_counts(keys, pts, owner, k)
        r = dict(max_ratio=cb.max() / (n / k), min_ratio=cb.min() / (n / k),
                 cv=cb.std() / (n / k), max_ratio_arc=ab.max() * k)
        if add:
            new = rng.random(v)
            ca, _ = ring_counts(keys, np.append(pts, new), owner_a, k + 1)
            give = cb - ca[:k]
            moved = ca[k]
            r.update(moved_share=moved / n, n_givers=int((give > 0).sum()),
                     top_giver_share=(give.max() / moved) if moved > 0 else np.nan,
                     max_ratio_after=ca.max() / (n / (k + 1)))
        out.append(r)
    return pd.DataFrame(out)


def per_key_floor(rng, n, k, trials):
    m = rng.multinomial(n, np.full(k, 1 / k), size=trials)
    r = m.max(axis=1) / (n / k)
    return float(r.mean()), float(np.quantile(r, 0.1)), float(np.quantile(r, 0.9))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    keys = np.sort(rng.random(N_BASE))

    rows = []
    for v in VS:
        d = run(rng, keys, K_BASE, v, TRIALS)
        rows.append(dict(
            points_per_server=v, points_total=K_BASE * v,
            max_ratio_mean=round(d.max_ratio.mean(), 4),
            max_ratio_p10=round(float(d.max_ratio.quantile(0.1)), 4),
            max_ratio_p90=round(float(d.max_ratio.quantile(0.9)), 4),
            max_ratio_arc_mean=round(d.max_ratio_arc.mean(), 4),
            min_ratio_mean=round(d.min_ratio.mean(), 4),
            cv_mean=round(d.cv.mean(), 4),
            moved_share_mean_pct=round(d.moved_share.mean() * 100, 3),
            moved_share_p10_pct=round(float(d.moved_share.quantile(0.1)) * 100, 3),
            moved_share_p90_pct=round(float(d.moved_share.quantile(0.9)) * 100, 3),
            n_givers_mean=round(d.n_givers.mean(), 2),
            top_giver_share_mean_pct=round(d.top_giver_share.mean() * 100, 2),
            max_ratio_after_mean=round(d.max_ratio_after.mean(), 4),
        ))
    by_v = pd.DataFrame(rows)
    by_v.to_csv(RES / "by_points.csv", index=False)

    fl_mean, fl_p10, fl_p90 = per_key_floor(rng, N_BASE, K_BASE, TRIALS)

    def first_v(df, col, thr):
        s = df[df[col] <= thr]
        return int(s.points_per_server.iloc[0]) if len(s) else None

    base = dict(
        n_keys=N_BASE, servers=K_BASE, trials=TRIALS,
        per_key_floor_mean=round(fl_mean, 4), per_key_floor_p10=round(fl_p10, 4), per_key_floor_p90=round(fl_p90, 4),
        first_v_max_ratio_le_1_5=first_v(by_v, "max_ratio_mean", 1.5),
        first_v_max_ratio_le_1_2=first_v(by_v, "max_ratio_mean", 1.2),
        first_v_max_ratio_le_1_1=first_v(by_v, "max_ratio_mean", 1.1),
        first_v_max_ratio_le_1_05=first_v(by_v, "max_ratio_mean", 1.05),
        first_v_max_ratio_le_1_02=first_v(by_v, "max_ratio_mean", 1.02),
        even_moved_share_pct=round(100 / (K_BASE + 1), 3),
    )
    # v を10倍にしたときの縮み方（平均からのはみ出し）
    ex = by_v.set_index("points_per_server")
    base["excess_v10_over_v1000"] = None
    base["excess"] = {str(v): round(float(ex.loc[v, "max_ratio_mean"] - 1), 4) for v in VS}
    base["excess_arc"] = {str(v): round(float(ex.loc[v, "max_ratio_arc_mean"] - 1), 4) for v in VS}
    base.pop("excess_v10_over_v1000")
    base["count_minus_arc"] = {str(v): round(float(ex.loc[v, "max_ratio_mean"] - ex.loc[v, "max_ratio_arc_mean"]), 4) for v in VS}
    for a_, b_ in [(1, 10), (10, 100), (100, 1000)]:
        base[f"excess_ratio_v{a_}_to_v{b_}"] = round(float((ex.loc[a_, "max_ratio_mean"] - 1) / (ex.loc[b_, "max_ratio_mean"] - 1)), 2)

    # 例：v=1・10・100 の1回分の台ごとの件数
    rng_ex = np.random.default_rng(SEED + 1)
    exrows = []
    for v in [1, 10, 100]:
        owner = np.repeat(np.arange(K_BASE), v)
        cb, _ = ring_counts(keys, rng_ex.random(K_BASE * v), owner, K_BASE)
        for i in range(K_BASE):
            exrows.append(dict(points_per_server=v, server=i + 1, count=int(cb[i])))
    exdf = pd.DataFrame(exrows)
    exdf.to_csv(DATA / "example_counts.csv", index=False)
    base["example_max_min"] = {str(v): [int(exdf[exdf.points_per_server == v]["count"].max()),
                                        int(exdf[exdf.points_per_server == v]["count"].min())] for v in [1, 10, 100]}

    # ---- 確かめ：9通り ----
    grid = []
    floors = []
    for k in [10, 50, 100]:
        for n in [10_000, 100_000, 1_000_000]:
            kk = np.sort(rng.random(n))
            fm, _, _ = per_key_floor(rng, n, k, TRIALS_GRID)
            floors.append(dict(servers=k, n_keys=n, per_key_floor_mean=round(fm, 4)))
            for v in VS:
                d = run(rng, kk, k, v, TRIALS_GRID, add=False)
                grid.append(dict(servers=k, n_keys=n, points_per_server=v,
                                 max_ratio_mean=round(d.max_ratio.mean(), 4),
                                 max_ratio_arc_mean=round(d.max_ratio_arc.mean(), 4),
                                 per_key_floor_mean=round(fm, 4)))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    summ = []
    for (k, n), s in grid.groupby(["servers", "n_keys"]):
        s = s.sort_values("points_per_server")
        fm = float(s.per_key_floor_mean.iloc[0])
        r1000 = float(s.max_ratio_mean.iloc[-1])
        summ.append(dict(servers=k, n_keys=n,
                         max_ratio_v1=float(s.max_ratio_mean.iloc[0]),
                         max_ratio_v100=float(s[s.points_per_server == 100].max_ratio_mean.iloc[0]),
                         max_ratio_v1000=r1000,
                         per_key_floor_mean=fm,
                         first_v_le_1_1=first_v(s, "max_ratio_mean", 1.1),
                         v1000_minus_floor=round(r1000 - fm, 4)))
    summ = pd.DataFrame(summ)
    summ.to_csv(RES / "grid_summary.csv", index=False)
    robust = dict(
        max_ratio_v1_range=[float(summ.max_ratio_v1.min()), float(summ.max_ratio_v1.max())],
        max_ratio_v100_range=[float(summ.max_ratio_v100.min()), float(summ.max_ratio_v100.max())],
        max_ratio_v1000_range=[float(summ.max_ratio_v1000.min()), float(summ.max_ratio_v1000.max())],
        floor_range=[float(summ.per_key_floor_mean.min()), float(summ.per_key_floor_mean.max())],
        v1000_minus_floor_range=[float(summ.v1000_minus_floor.min()), float(summ.v1000_minus_floor.max())],
        n_never_le_1_1=int(summ.first_v_le_1_1.isna().sum()),
    )

    # ---- 図 ----
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    ax.fill_between(by_v.points_per_server, by_v.max_ratio_p10, by_v.max_ratio_p90, color=LIGHT, alpha=0.6,
                    label="10〜90%の範囲（件数）")
    ax.plot(by_v.points_per_server, by_v.max_ratio_mean, "o-", color=BLUE, ms=4, label="件数で数えた平均")
    ax.plot(by_v.points_per_server, by_v.max_ratio_arc_mean, ":", color=INK, label="輪の長さで数えた平均")
    ax.axhline(fl_mean, color=ORANGE, lw=1.2, ls="--")
    ax.text(1, fl_mean, f"1件ずつ乱数で置いたとき {fl_mean:.3f}", color=ORANGE, fontsize=8, va="bottom")
    ax.set_xscale("log")
    ax.set_xticks(VS, [str(v) for v in VS])
    ax.set_ylim(0, None)
    ax.set_xlabel("1台を輪の上に置く場所の数")
    ax.set_ylabel("いちばん多い1台÷平均")
    ax.set_title("置く場所を10倍にしても、平均からのはみ出しは約3分の1（10台・10万件）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1309_by_points.png", SRC)

    fig, axs = plt.subplots(1, 3, figsize=(10, 3.6), sharey=True)
    for ax, v in zip(axs, [1, 10, 100]):
        s = exdf[exdf.points_per_server == v]
        ax.bar(s.server, s["count"], color=BLUE)
        ax.axhline(N_BASE / K_BASE, color=GRAY, ls="--", lw=1)
        ax.set_title(f"1台{v}か所", fontsize=11)
        ax.set_xticks(range(1, K_BASE + 1))
        ax.set_xlabel("台")
        ax.set_ylim(0, None)
    axs[0].set_ylabel("受け持つデータの件数")
    fig.suptitle("1回分の例：台ごとの件数（点線は平均の1万件）", fontsize=12, y=1.05)
    save(fig, "a1309_example.png", SRC, y=-0.06)

    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    cols = {10_000: LIGHT, 100_000: BLUE, 1_000_000: INK}
    for n in [10_000, 100_000, 1_000_000]:
        s = grid[(grid.servers == 50) & (grid.n_keys == n)]
        ax.plot(s.points_per_server, s.max_ratio_mean, "o-", color=cols[n], ms=4, label=f"データ{n:,}件")
        ax.axhline(float(s.per_key_floor_mean.iloc[0]), color=cols[n], ls="--", lw=0.9)
    ax.set_xscale("log")
    ax.set_xticks(VS, [str(v) for v in VS])
    ax.set_ylim(0, None)
    ax.set_xlabel("1台を輪の上に置く場所の数")
    ax.set_ylabel("いちばん多い1台÷平均（300回の平均）")
    ax.set_title("50台のとき：データが少ないと、点線（1件ずつ乱数）より下がらない")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1309_by_keys.png", SRC)

    main_json = dict(base=base, robust=robust)
    (RES / "a1309_main.json").write_text(json.dumps(main_json, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(by_v.to_string())
    print(summ.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
