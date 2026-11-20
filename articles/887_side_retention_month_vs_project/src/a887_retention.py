"""887 継続率は、月で数えるか案件で数えるかで変わるのか？（架空のデータ）

架空の副業の人の、架空の取引先。取引先ごとに「案件が終わったあと、次の案件を頼む確率 p」を置き
（取引先によって違う。取引先の平均は0.5）、案件の長さ（月）と、次の案件までの空き（月）を乱数で決める。
36か月の記録から、継続率を3通りに数えて比べる。
- 月で数える：ある月に取引のあった取引先のうち、翌月も取引のあった割合
- 案件で数える：終わった案件のうち、同じ取引先から次の案件が来た割合
- 取引先で数える：取引先のうち、2件目以上の案件が来た割合
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 887
SRC = "架空の取引先と案件（作成者が乱数で作成、seed 887）"
T = 36                       # 記録のある月数
BASE = dict(kappa=2.0, dur=2.0, gap=1.0, mean_p=0.5)


def make_projects(rng, n_client=2000, kappa=2.0, dur=2.0, gap=1.0, mean_p=0.5):
    """取引先ごとに案件を並べる。1件目の開始月は1〜36で一様。
    p：Beta(mean_p*kappa, (1-mean_p)*kappa)。kappa が大きいほど取引先どうしが似る。
    案件の長さ：1＋ポアソン(dur−1) か月。次の案件までの空き：ポアソン(gap) か月（0なら翌月から続けて始まる）。"""
    if kappa >= 1e5:
        p = np.full(n_client, mean_p)
    else:
        p = rng.beta(mean_p * kappa, (1 - mean_p) * kappa, n_client)
    rows = []
    for i in range(n_client):
        start = int(rng.integers(1, T + 1))
        k = 0
        while start <= T:
            d = 1 + rng.poisson(dur - 1)
            end = start + d - 1
            nxt = rng.random() < p[i]
            rows.append((i + 1, k + 1, start, end, nxt, p[i]))
            if not nxt:
                break
            start = end + 1 + rng.poisson(gap)
            k += 1
    df = pd.DataFrame(rows, columns=["client_id", "project_no", "start", "end", "next_ordered", "p_true"])
    return df


def measures(df, wait=6):
    """記録の窓（1〜36か月）の中で見えるものだけで数える"""
    seen = df[df.start <= T].copy()
    # 次の案件が窓の中で始まっているか（見えている「継続」）
    seen = seen.sort_values(["client_id", "project_no"])
    nxt_start = seen.groupby("client_id").start.shift(-1)
    seen["next_seen"] = nxt_start.notna() & (nxt_start <= T)
    ended = seen[seen.end <= T]
    # 月で数える
    act = set()
    for c, s, e in zip(seen.client_id, seen.start, np.minimum(seen.end, T)):
        for t in range(s, e + 1):
            act.add((c, t))
    pairs = [(c, t) for c, t in act if t < T]
    month = np.mean([(c, t + 1) in act for c, t in pairs])
    # 案件で数える（窓の中で終わった案件すべて：次がまだ来ていないものは「続かなかった」に入る）
    proj_all = ended.next_seen.mean()
    # 案件で数える（終わって wait か月以上たった案件だけ）
    old = ended[ended.end <= T - wait]
    proj_old = old.next_seen.mean()
    # 取引先で数える
    per_client = seen.groupby("client_id").project_no.max()
    client = (per_client >= 2).mean()
    first = seen[seen.project_no == 1].set_index("client_id").start
    client_old = (per_client[first <= T - 12] >= 2).mean()
    return {"month": float(month), "project_all": float(proj_all), "project_wait6": float(proj_old),
            "client_any2": float(client), "client_first_le24": float(client_old),
            "true_client_mean_p": float(seen.groupby("client_id").p_true.first().mean()),
            "true_project_weighted_p": float(ended.p_true.mean()),
            "true_project_next_ordered": float(ended.next_ordered.mean())}


def r3(x):
    if isinstance(x, dict):
        return {k: r3(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r3(v) for v in x]
    return round(float(x), 3)


LAB = {"month": "月で数える", "project_all": "案件で数える（次がまだ来ていない案件も入れる）",
       "project_wait6": "案件で数える（終わって6か月以上たった案件だけ）", "client_any2": "取引先で数える（2件目が来た割合）",
       "true_client_mean_p": "置いた答え：取引先の平均の「次を頼む確率」",
       "true_project_weighted_p": "置いた答え：案件1件あたりの「次を頼む確率」"}


def main():
    rng = np.random.default_rng(SEED)
    df = make_projects(rng, n_client=300)
    df.to_csv(DATA / "projects_300clients.csv", index=False, float_format="%.4f")
    one = measures(df)

    reps = [measures(make_projects(np.random.default_rng(SEED * 1000 + i))) for i in range(30)]
    base = {k: float(np.mean([r[k] for r in reps])) for k in reps[0]}
    base_sd = {k: float(np.std([r[k] for r in reps])) for k in reps[0]}

    # 頑健性：取引先どうしの差（kappa）・案件の長さ（dur）・空き（gap）を変える（各5回×2,000社）
    rows = []
    for kappa in [1.0, 2.0, 10.0, 1e6]:
        for dur in [1.0, 2.0, 4.0]:
            for gap in [0.0, 1.0, 3.0]:
                rs = [measures(make_projects(np.random.default_rng(SEED * 7 + i + int(np.log10(kappa) * 1000) + int(dur * 100) + int(gap * 10)),
                                             kappa=kappa, dur=dur, gap=gap)) for i in range(5)]
                row = {"kappa": kappa if kappa < 1e5 else "同じ", "dur": dur, "gap": gap}
                row.update({k: float(np.mean([r[k] for r in rs])) for k in rs[0]})
                rows.append(row)
    grid = pd.DataFrame(rows).round(3)
    grid.to_csv(RES / "robustness_grid.csv", index=False)
    ranges = {k: [float(grid[k].min()), float(grid[k].max())] for k in
              ["month", "project_all", "project_wait6", "client_any2", "true_project_weighted_p"]}
    same = grid[grid.kappa == "同じ"]
    order_month_top = float((grid.month > grid[["project_all", "project_wait6", "client_any2"]].max(1)).mean())
    rob = {"ranges_all36": ranges,
           "homogeneous_project_wait6_range": [float(same.project_wait6.min()), float(same.project_wait6.max())],
           "share_month_is_highest": order_month_top,
           "project_wait6_minus_project_weighted_p": [float((grid.project_wait6 - grid.true_project_weighted_p).min()),
                                                      float((grid.project_wait6 - grid.true_project_weighted_p).max())],
           "client_first_le24_range": [float(grid.client_first_le24.min()), float(grid.client_first_le24.max())],
           "month_by_dur_gap0_kappa2": {str(d): float(grid[(grid.kappa == 2.0) & (grid.gap == 0) & (grid.dur == d)].month.iloc[0]) for d in [1.0, 2.0, 4.0]},
           "month_by_dur_gap1_kappa2": {str(d): float(grid[(grid.kappa == 2.0) & (grid.gap == 1) & (grid.dur == d)].month.iloc[0]) for d in [1.0, 2.0, 4.0]},
           "project_wait6_by_kappa_dur2_gap1": {str(k): float(grid[(grid.kappa == k) & (grid.dur == 2.0) & (grid.gap == 1)].project_wait6.iloc[0]) for k in [1.0, 2.0, 10.0, "同じ"]},
           "client_any2_by_kappa_dur2_gap1": {str(k): float(grid[(grid.kappa == k) & (grid.dur == 2.0) & (grid.gap == 1)].client_any2.iloc[0]) for k in [1.0, 2.0, 10.0, "同じ"]}}

    # 案件の数え方を、待つ月数で変える（基本の置き方）
    waits = {}
    for w in [0, 1, 3, 6, 12]:
        rs = [measures(make_projects(np.random.default_rng(SEED * 1000 + i)), wait=w)["project_wait6"] for i in range(10)]
        waits[str(w)] = float(np.mean(rs))

    out = {"assumptions": dict(BASE, months=T), "base_30reps_2000clients": r3(base), "base_sd": r3(base_sd),
           "one_draw_300clients": r3(one), "one_draw_counts": {"clients": int(df.client_id.nunique()),
                                                                "projects_seen": int((df.start <= T).sum())},
           "project_count_by_wait_months": r3(waits), "robustness": r3(rob)}
    json.dump(out, open(RES / "a887_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pd.DataFrame({"measure": [LAB[k] for k in LAB], "value_mean": [round(base[k], 3) for k in LAB],
                  "value_sd": [round(base_sd[k], 3) for k in LAB]}).to_csv(RES / "measures_base.csv", index=False)

    # 図1：基本の置き方での4つの数え方
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    keys = list(LAB)
    vals = [base[k] * 100 for k in keys]
    cols = [BLUE, LIGHT, BLUE, ORANGE, GRAY, GRAY]
    ax.barh([LAB[k] for k in keys][::-1], vals[::-1], color=cols[::-1], height=0.6)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("継続率（%、取引先2,000社×30回の平均）")
    lo, hi = min(vals[:4]), max(vals[:4])
    ax.set_title(f"同じ記録でも、数え方で継続率は{lo:.0f}〜{hi:.0f}%に分かれる")
    save(fig, "a887_measures.png", SRC)

    # 図2：案件の長さで動く「月で数える」
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    sub = grid[(grid.kappa == 2.0)]
    for gap, cc in zip([0.0, 1.0, 3.0], [INK, BLUE, LIGHT]):
        s = sub[sub.gap == gap]
        ax.plot(s.dur, s.month * 100, marker="o", color=cc, lw=2, label=f"月で数える（空き 平均{gap:g}か月）")
    s = sub[sub.gap == 1.0]
    ax.plot(s.dur, s.project_wait6 * 100, marker="s", color=ORANGE, lw=2, ls="--", label="案件で数える（6か月以上たった案件、空き 平均1か月）")
    ax.axhline(50, color=GRAY, lw=1, ls=":"); ax.text(2.55, 45.5, "取引先の平均の「次を頼む確率」50%", color=GRAY, fontsize=8.5)
    ax.set_xticks([1, 2, 4]); ax.set_xlabel("案件の長さ（平均の月数）"); ax.set_ylabel("継続率（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("月で数えた継続率は、案件の長さと次までの空きで大きく動く")
    save(fig, "a887_by_duration.png", SRC)

    # 図3：取引先どうしの差で動く「案件で数える」と「取引先で数える」
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ks = ["1.0", "2.0", "10.0", "同じ"]
    labk = ["とても大きい", "大きい（基本）", "小さい", "差なし"]
    x = np.arange(4); w = 0.36
    pv = [rob["project_wait6_by_kappa_dur2_gap1"][k] * 100 for k in ks]
    cv = [rob["client_any2_by_kappa_dur2_gap1"][k] * 100 for k in ks]
    ax.bar(x - w / 2, pv, w * 0.92, color=BLUE, label="案件で数える（6か月以上たった案件）")
    ax.bar(x + w / 2, cv, w * 0.92, color=ORANGE, label="取引先で数える（2件目が来た割合）")
    for i in range(4):
        ax.text(x[i] - w / 2, pv[i] + 1, f"{pv[i]:.0f}%", ha="center", fontsize=8.5)
        ax.text(x[i] + w / 2, cv[i] + 1, f"{cv[i]:.0f}%", ha="center", fontsize=8.5)
    ax.axhline(50, color=GRAY, lw=1, ls=":")
    ax.set_xticks(x); ax.set_xticklabels(labk); ax.set_xlabel("取引先どうしの「次を頼む確率」の差")
    ax.set_ylabel("継続率（%）"); ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("取引先どうしの差が大きいほど、案件で数えた継続率は高く出る")
    save(fig, "a887_by_heterogeneity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
