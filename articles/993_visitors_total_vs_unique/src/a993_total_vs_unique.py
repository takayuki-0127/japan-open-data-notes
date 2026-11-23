"""993 延べの来場者と実際の人数は、どれだけ違うのか？（架空のデータ）

架空の科学館の1年（1か月を30日、1年を360日と置いた）。来る可能性のある人を20万人置き、
人ごとの1年に来る回数の平均（来やすさ）をガンマ分布で置く（平均0.5回、形 k=0.5）。
実際の来る回数はその平均のポアソン分布で引き、日はでたらめに選ぶ（同じ人の同じ日は1回に数える）。
延べ（人×日の数）と実人数（1回以上来た人の数）を、数える期間（1日・1か月・3か月・1年）ごとに比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 993
SRC = "架空の科学館の来場（作成者が乱数で作成、seed 993）"
DAYS = 360
WINDOWS = {"1日": 1, "1か月": 30, "3か月": 90, "1年": 360}
BASE = {"N": 200000, "mu": 0.5, "k": 0.5}
REPS = 20
KS = [0.2, 0.5, 1.0, 2.0, 5.0]
NMU = [(100000, 1.0), (200000, 0.5), (400000, 0.25)]
GRID_REPS = 5


def simulate(rng, N, mu, k):
    lam = rng.gamma(k, mu / k, N)
    n = rng.poisson(lam)
    pid = np.repeat(np.arange(N), n)
    day = rng.integers(0, DAYS, pid.size)
    key = np.unique(pid.astype(np.int64) * DAYS + day)   # 同じ人の同じ日は1回
    return lam, key // DAYS, key % DAYS


def window_stats(pid, day, w):
    """期間 w 日ごとの 延べ・実人数（期間ごとの値の合計）"""
    win = day // w
    total = pid.size
    uniq = np.unique(pid.astype(np.int64) * (DAYS // w + 1) + win).size
    nwin = DAYS // w
    return total / nwin, uniq / nwin, uniq      # 1期間あたり延べ・実人数、期間の実人数の合計


def summarize(pid, day, N, mu, k):
    out = {}
    year_uniq = np.unique(pid).size
    for name, w in WINDOWS.items():
        t, u, usum = window_stats(pid, day, w)
        out[f"ratio_{name}"] = t / u
        out[f"sum_over_year_{name}"] = usum / year_uniq
    cnt = np.bincount(pid)
    cnt = cnt[cnt > 0]
    srt = np.sort(cnt)[::-1]
    top = int(np.ceil(0.1 * cnt.size))
    out.update({"total_year": int(pid.size), "unique_year": int(year_uniq),
                "unique_year_formula": N * (1 - (k / (k + mu)) ** k),
                "share_once_pct": (cnt == 1).mean() * 100,
                "share_visits_top10pct_pct": srt[:top].sum() / srt.sum() * 100,
                "share_visits_from_once_pct": (cnt == 1).sum() / srt.sum() * 100,
                "mean_visits_per_visitor": cnt.mean()})
    return out, cnt


def main():
    t0 = time.time()
    # 1) 基本の置き方（20回）
    rows = []
    for r in range(REPS):
        rng = np.random.default_rng(SEED * 1000 + r)
        lam, pid, day = simulate(rng, **BASE)
        s, cnt = summarize(pid, day, **BASE)
        s["rep"] = r
        rows.append(s)
        if r == 0:
            months = np.zeros(BASE["N"], int)
            pm = np.unique(pid.astype(np.int64) * 12 + day // 30) // 12
            np.add.at(months, pm, 1)
            vis = np.bincount(pid, minlength=BASE["N"])
            m = vis > 0
            pd.DataFrame({"person_id": np.arange(1, BASE["N"] + 1)[m], "rate_per_year": np.round(lam[m], 4),
                          "visits_year": vis[m], "months_visited": months[m]}).to_csv(
                DATA / "visitors_example.csv", index=False)
            cnt0 = cnt
    base = pd.DataFrame(rows)
    base.round(4).to_csv(RES / "base_20reps.csv", index=False)
    bm = base.drop(columns="rep").mean()

    # 回数ごとの人と延べの割合（1回分）
    bins = list(range(1, 10)) + [10]
    labels = [str(b) for b in range(1, 10)] + ["10回以上"]
    c = np.minimum(cnt0, 10)
    freq = pd.DataFrame({"visits": labels,
                         "share_people_pct": [(c == b).mean() * 100 for b in bins],
                         "share_total_pct": [cnt0[c == b].sum() / cnt0.sum() * 100 for b in bins]}).round(3)
    freq.to_csv(RES / "visits_distribution_rep0.csv", index=False)

    # 2) 確かめ：延べの見込みを10万回にそろえた15通り（各5回）
    grid = []
    for k in KS:
        for N, mu in NMU:
            ss = []
            for r in range(GRID_REPS):
                rng = np.random.default_rng(SEED * 100000 + int(k * 10) * 1000 + int(mu * 100) * 10 + r)
                lam, pid, day = simulate(rng, N, mu, k)
                ss.append(summarize(pid, day, N, mu, k)[0])
            g = pd.DataFrame(ss).mean()
            g["k"], g["N"], g["mu"] = k, N, mu
            grid.append(g)
    grid = pd.DataFrame(grid)
    cols = ["k", "N", "mu"] + [c for c in grid.columns if c not in ("k", "N", "mu")]
    grid = grid[cols]
    grid.round(4).to_csv(RES / "sensitivity_grid.csv", index=False)

    r2 = lambda x: round(float(x), 3)
    out = {
        "setting": {**BASE, "days": DAYS, "reps": REPS},
        "base_mean": {k: r2(v) for k, v in bm.items()},
        "base_min_max": {"unique_year": [int(base.unique_year.min()), int(base.unique_year.max())],
                         "total_year": [int(base.total_year.min()), int(base.total_year.max())]},
        "unique_formula_gap_pct": r2((bm.unique_year / bm.unique_year_formula - 1) * 100),
        "grid_range": {c: [r2(grid[c].min()), r2(grid[c].max())] for c in grid.columns if c not in ("k", "N", "mu")},
        "grid_unique_year_by_k_N200k": {str(k): int(round(grid[(grid.k == k) & (grid.N == 200000)].unique_year.iloc[0]))
                                        for k in KS},
        "run_sec": None,
    }
    out["unique_year_man"] = {"base_mean": round(bm.unique_year / 10000, 2),
                              "grid_min": round(grid.unique_year.min() / 10000, 2),
                              "grid_max": round(grid.unique_year.max() / 10000, 2)}
    out["per_month_mean"] = {"total": round(float(bm.total_year / 12)), "unique": round(float(bm.total_year / 12 / bm["ratio_1か月"]))}
    out["grid_range_total_year"] = [int(grid.total_year.min()), int(grid.total_year.max())]
    out["grid_unique_formula_gap_pct_range"] = [r2(((grid.unique_year / grid.unique_year_formula) - 1).min() * 100),
                                                r2(((grid.unique_year / grid.unique_year_formula) - 1).max() * 100)]

    # 図1：期間ごとの 延べ÷実人数（k ごと、N=20万人）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = np.arange(len(WINDOWS))
    cmap = [LIGHT, BLUE, GREEN, ORANGE, GRAY]
    for k, col in zip(KS, cmap):
        g = grid[(grid.k == k) & (grid.N == 200000)].iloc[0]
        ys = [g[f"ratio_{w}"] for w in WINDOWS]
        ax.plot(xs, ys, marker="o", color=col, lw=2 if k == 0.5 else 1.3,
                label=f"k={k}" + ("（基本）" if k == 0.5 else ""))
    ax.set_xticks(xs, [f"{w}" for w in WINDOWS]); ax.set_xlabel("数える期間")
    ax.set_ylabel("延べ ÷ 実人数（1期間あたり）")
    ax.legend(frameon=False, fontsize=9, title="来やすさの散らばり（20万人が平均0.5回の場合）", title_fontsize=8.5)
    ax.set_title("同じ人の同じ日を1回と数えると、1日では延べと実人数は同じ。期間を延ばすほど離れる", fontsize=11.5)
    save(fig, "a993_window.png", SRC)

    # 図2：年の来場回数ごとの、人の割合と延べの割合（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.4
    ax.bar(np.arange(len(freq)) - w / 2, freq.share_people_pct, w, color=BLUE, label="実人数のうちの割合")
    ax.bar(np.arange(len(freq)) + w / 2, freq.share_total_pct, w, color=ORANGE, label="延べのうちの割合")
    ax.set_xticks(np.arange(len(freq)), [l.replace("10回以上", "10回\n以上") for l in freq.visits])
    ax.set_xlabel("1年に来た回数"); ax.set_ylabel("%")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"1回だけ来た人は実人数の{freq.share_people_pct.iloc[0]:.1f}%、延べでは{freq.share_total_pct.iloc[0]:.1f}%（基本の置き方、1回分）",
                 fontsize=11.5)
    save(fig, "a993_frequency.png", SRC)

    # 図3：延べの見込み10万回で、年の実人数（15通り）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.26
    for j, ((N, mu), col) in enumerate(zip(NMU, [LIGHT, BLUE, GREEN])):
        g = grid[(grid.N == N)].sort_values("k")
        ax.bar(np.arange(len(KS)) + (j - 1) * w, g.unique_year / 10000, w, color=col,
               label=f"{N // 10000}万人が平均{mu}回")
    ax.set_xticks(np.arange(len(KS)), [f"k={k}" for k in KS])
    ax.set_xlabel("来やすさの散らばり（k が小さいほど一部の人に偏る）")
    ax.set_ylabel("1年の実人数（万人）")
    ax.legend(frameon=False, fontsize=9, title="来る可能性のある人", title_fontsize=8.5)
    ax.set_title("延べはどれも約10万回。実人数は置き方で大きく変わる", fontsize=12)
    save(fig, "a993_same_total.png", SRC)

    out["run_sec"] = None   # 所要時間は環境で変わるので results には入れない
    del out["run_sec"]
    json.dump(out, open(RES / "a993_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
