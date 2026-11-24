"""1154 置いておく時間を長くすると、当たり率が上がる分と、古いデータを返す割合が増える分はどう釣り合うのか？（架空のデータ）

作成者が置いた架空のアプリのデータ2,000件。r番目に人気のデータへの問い合わせの割合は 1÷r^0.9 に比例、
問い合わせは全体で毎秒5件（でたらめな時刻に来る）、24時間ぶん。元のデータは、1件ずつ平均1時間に1回、でたらめな時刻に書きかわる。
置き場所（キャッシュ）は大きさの上限なし。外れたら元のデータを取ってきて置き、置いてから T 秒たつまでは置いたものを返す（当たり）。
当たりで返したものが、取ってきたあとに元で書きかわっていたら「古いデータを返した」と数える。
(1) T＝10秒〜6時間の9通りで、当たり率・古いデータを返した割合（全部の問い合わせのうち／当たりのうち）を数え、式と照らす
    式（1件ごと、問い合わせの頻度 λ・書きかわりの頻度 μ）：当たり率 λT÷(1＋λT)、
    古い割合 λ×(T−(1−e^(−μT))÷μ)÷(1＋λT)。全体は問い合わせの割合で重みを付けて足す
(2) T を1段長くするごとに、当たり率が上がる分と古い割合が増える分の比を出す
(3) 古いデータを返したとき、元が書きかわってから何秒たっていたか
(4) 人気の上位20件だけ平均10分に1回書きかわると置いた場合
(5) 確かめ（式で出す。15分→30分の比と、古い割合が初めて1%を超える置いておく時間）：書きかわりの間隔（10分・1時間・6時間）×偏り（0.6・0.9・1.2）×問い合わせの多さ（毎秒0.5・5・50件）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1154
SRC = "架空のアプリへの問い合わせと元のデータの書きかわり（作成者が置いた頻度からの乱数、seed 1154）"
N_ITEMS, ALPHA, RATE, HOURS = 2_000, 0.9, 5.0, 24
UPD = 3600.0
TS = [10, 30, 60, 300, 900, 1800, 3600, 10800, 21600]
TNAME = {10: "10秒", 30: "30秒", 60: "1分", 300: "5分", 900: "15分", 1800: "30分", 3600: "1時間", 10800: "3時間", 21600: "6時間"}
HOT_N, HOT_UPD = 20, 600.0
G_UPD = [600.0, 3600.0, 21600.0]
G_A = [0.6, 0.9, 1.2]
G_RATE = [0.5, 5.0, 50.0]


def r(x, d=4):
    return round(float(x), d)


def probs(n, a):
    p = 1.0 / np.arange(1, n + 1) ** a
    return p / p.sum()


def formula(p, rate, mu, T):
    lam = rate * p
    hit = lam * T / (1 + lam * T)
    stale = lam * (T - (1 - np.exp(-mu * T)) / mu) / (1 + lam * T)
    return float((p * hit).sum()), float((p * stale).sum())


def make_world(rng, p, rate, mu, dur):
    n_req = rng.poisson(rate * dur)
    t = np.sort(rng.random(n_req) * dur)
    it = rng.choice(len(p), size=n_req, p=p)
    reqs = [[] for _ in range(len(p))]
    for ti, ii in zip(t.tolist(), it.tolist()):
        reqs[ii].append(ti)
    upds = []
    for i in range(len(p)):
        k = rng.poisson(mu[i] * dur)
        upds.append(np.sort(rng.random(k) * dur))
    return reqs, upds, n_req


def simulate(reqs, upds, T):
    n = hits = stale = 0
    ages = []
    for times, up in zip(reqs, upds):
        if not times:
            continue
        tarr = np.array(times)
        fetch = np.empty(len(times))
        hit = np.zeros(len(times), dtype=bool)
        f = -1e18
        for j, tt in enumerate(times):
            if tt - f < T:
                hit[j] = True
            else:
                f = tt
            fetch[j] = f
        # 取ってきたあと、返すまでに書きかわったか
        a = np.searchsorted(up, fetch, side="right")
        b = np.searchsorted(up, tarr, side="right")
        st = hit & (b > a)
        n += len(times)
        hits += int(hit.sum())
        stale += int(st.sum())
        if st.any():
            first_up = up[a[st]]
            ages.append(tarr[st] - first_up)
    ages = np.concatenate(ages) if ages else np.array([])
    return n, hits, stale, ages


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    dur = HOURS * 3600.0
    p = probs(N_ITEMS, ALPHA)
    out = {"setup": {"n_items": N_ITEMS, "alpha": ALPHA, "rate_per_sec": RATE, "hours": HOURS, "update_mean_sec": UPD,
                     "hot_n": HOT_N, "hot_update_mean_sec": HOT_UPD, "seed": SEED}}
    worlds = {}
    mu_base = np.full(N_ITEMS, 1 / UPD)
    mu_hot = mu_base.copy()
    mu_hot[:HOT_N] = 1 / HOT_UPD
    rows = []
    age_rows = []
    for case, mu in [("base", mu_base), ("hot", mu_hot)]:
        reqs, upds, n_req = make_world(rng, p, RATE, mu, dur)
        if case == "base":
            out["setup"]["n_requests"] = int(n_req)
            # data：上位5件の問い合わせ時刻と書きかわり時刻（最初の1時間）
            recs = []
            for i in range(5):
                recs += [{"item_rank": i + 1, "kind": "問い合わせ", "t_sec": round(x, 3)} for x in reqs[i] if x < 3600]
                recs += [{"item_rank": i + 1, "kind": "書きかわり", "t_sec": round(float(x), 3)} for x in upds[i] if x < 3600]
            pd.DataFrame(recs).sort_values(["item_rank", "t_sec"]).to_csv(DATA / "top5_first_hour.csv", index=False)
        for T in TS:
            n, h, s, ages = simulate(reqs, upds, T)
            fh, fs = formula(p, RATE, mu, T)
            rows.append({"case": case, "keep_sec": T, "keep": TNAME[T], "hit_rate": r(h / n), "stale_of_all": r(s / n),
                         "stale_of_hits": r(s / h) if h else None, "hit_formula": r(fh), "stale_formula": r(fs),
                         "stale_age_median_sec": r(np.median(ages), 1) if len(ages) else None,
                         "stale_age_mean_sec": r(ages.mean(), 1) if len(ages) else None,
                         "stale_age_median_over_keep": r(np.median(ages) / T, 3) if len(ages) else None,
                         "stale_age_p90_sec": r(np.quantile(ages, 0.9), 1) if len(ages) else None})
    df = pd.DataFrame(rows)
    # (2) 1段ごとの増え方
    steps = []
    for case in ["base", "hot"]:
        s = df[df.case == case].reset_index(drop=True)
        for k in range(1, len(s)):
            dh = s.hit_rate[k] - s.hit_rate[k - 1]
            ds = s.stale_of_all[k] - s.stale_of_all[k - 1]
            dhf = s.hit_formula[k] - s.hit_formula[k - 1]
            dsf = s.stale_formula[k] - s.stale_formula[k - 1]
            steps.append({"case": case, "from": s.keep[k - 1], "to": s.keep[k], "hit_up_pt": r(dh * 100, 2),
                          "stale_up_pt": r(ds * 100, 2), "stale_per_hit": r(ds / dh, 3) if dh > 0 else None,
                          "stale_per_hit_formula": r(dsf / dhf, 3)})
    df.to_csv(RES / "by_keep.csv", index=False)
    st = pd.DataFrame(steps)
    st.to_csv(RES / "steps.csv", index=False)
    out["by_keep"] = rows
    out["steps"] = steps
    b = df[df.case == "base"]
    out["max_abs_diff_sim_formula_pt"] = {"hit": r((b.hit_rate - b.hit_formula).abs().max() * 100, 3),
                                          "stale": r((b.stale_of_all - b.stale_formula).abs().max() * 100, 3)}
    # 置く時間を1分→1時間の60倍にしたときの倍率
    g1, g60 = b[b.keep_sec == 60].iloc[0], b[b.keep_sec == 3600].iloc[0]
    out["min1_to_hour1"] = {"hit_1min": g1.hit_rate, "hit_1h": g60.hit_rate, "stale_1min": g1.stale_of_all, "stale_1h": g60.stale_of_all,
                            "miss_ratio_1h_over_1min": r((1 - g60.hit_rate) / (1 - g1.hit_rate), 3),
                            "stale_ratio_1h_over_1min": r(g60.stale_of_all / g1.stale_of_all, 2)}
    # 上位1件（いちばん人気）の古い割合（式）
    lam1 = RATE * p[0]
    out["top1_stale_formula"] = {TNAME[T]: r(lam1 * (T - (1 - np.exp(-T / UPD)) * UPD) / (1 + lam1 * T)) for T in TS}
    out["top1_requests_per_sec"] = r(lam1, 3)

    # (5) 確かめ（式）
    grows = []
    for upd in G_UPD:
        for a in G_A:
            pp = probs(N_ITEMS, a)
            for rate in G_RATE:
                vals = [formula(pp, rate, np.full(N_ITEMS, 1 / upd), T) for T in TS]
                hs = [v[0] for v in vals]
                ss = [v[1] for v in vals]
                over1 = [TNAME[T] for T, sv in zip(TS, ss) if sv > 0.01]
                k5, k15, k30 = TS.index(300), TS.index(900), TS.index(1800)
                grows.append({"update_mean_sec": upd, "alpha": a, "rate_per_sec": rate,
                              "hit_5min": r(hs[k5]), "hit_30min": r(hs[k30]), "stale_5min": r(ss[k5]), "stale_30min": r(ss[k30]),
                              "hit_15min": r(hs[k15]), "stale_15min": r(ss[k15]),
                              "stale_per_hit_15to30min": r((ss[k30] - ss[k15]) / (hs[k30] - hs[k15]), 3),
                              "first_keep_stale_over_1pct": over1[0] if over1 else "なし",
                              "hit_at_that_keep": r(hs[TS.index([T for T in TS if TNAME[T] == over1[0]][0])]) if over1 else None})
    g = pd.DataFrame(grows)
    g.to_csv(RES / "grid_formula.csv", index=False)
    out["grid_summary"] = {"n_cases": int(len(g)),
                           "stale_per_hit_15to30min_range": [r(g.stale_per_hit_15to30min.min(), 3), r(g.stale_per_hit_15to30min.max(), 3)],
                           "stale_per_hit_15to30min_over1": f"{int((g.stale_per_hit_15to30min > 1).sum())}/{len(g)}",
                           "first_keep_over_1pct_counts": g.first_keep_stale_over_1pct.value_counts().to_dict(),
                           "stale_30min_range": [r(g.stale_30min.min()), r(g.stale_30min.max())],
                           "hit_30min_range": [r(g.hit_30min.min()), r(g.hit_30min.max())]}

    # 図1：当たり率と古い割合
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    xs = np.arange(len(TS))
    ax.plot(xs, b.hit_rate * 100, marker="o", color=BLUE, label="当たり率")
    ax.plot(xs, b.stale_of_all * 100, marker="o", color=ORANGE, label="古いデータを返した割合（全部の問い合わせのうち）")
    ax.plot(xs, b.stale_of_hits * 100, marker="o", color=ORANGE, ls="--", alpha=0.6, label="古いデータを返した割合（当たりのうち）")
    ax.plot(xs, b.hit_formula * 100, ls="none", marker="x", color=INK, ms=6, label="式の値")
    ax.plot(xs, b.stale_formula * 100, ls="none", marker="x", color=INK, ms=6)
    for x, v in zip(xs, b.hit_rate):
        ax.text(x, v * 100 + 2.5, f"{v*100:.2f}", ha="center", fontsize=7.2, color=BLUE)
    for x, v in zip(xs, b.stale_of_all):
        if v >= 0.01:
            ax.text(x + 0.12, v * 100 - 5.5, f"{v*100:.2f}", ha="left", fontsize=7.2, color=ORANGE)
    ax.set_xticks(xs)
    ax.set_xticklabels([TNAME[T] for T in TS])
    ax.set_ylim(0, 106)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("置いておく時間（元のデータは1件ずつ平均1時間に1回書きかわる）")
    ax.set_ylabel("%")
    ax.set_title("置いておく時間を長くしたときの当たり率と、古いデータを返した割合")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    save(fig, "a1154_by_keep.png", SRC)

    # 図2：1段ごとの比
    sb = st[st.case == "base"]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    xs2 = np.arange(len(sb))
    ax.bar(xs2, sb.stale_per_hit, color=ORANGE)
    for x, v in zip(xs2, sb.stale_per_hit):
        ax.text(x, v + 0.05, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(xs2)
    ax.set_xticklabels([f"{a}→\n{c}" for a, c in zip(sb["from"], sb["to"])], fontsize=8.5)
    ax.set_ylim(0, max(sb.stale_per_hit) * 1.15)
    ax.set_xlabel("置いておく時間を1段長くしたとき")
    ax.set_ylabel("古い割合の増え÷当たり率の上がり")
    ax.set_title("長くするほど、当たりが1ポイント増えるごとに増える古いデータが多くなる")
    save(fig, "a1154_steps.png", SRC, y=-0.07)

    # 図3：上位20件が速く書きかわるとき
    hb = df[df.case == "hot"]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    w = 0.38
    ax.bar(xs - w / 2, b.stale_of_all * 100, width=w, color=LIGHT, label="どのデータも平均1時間に1回書きかわる")
    ax.bar(xs + w / 2, hb.stale_of_all * 100, width=w, color=ORANGE, label="人気の上位20件だけ平均10分に1回")
    for x, v in zip(xs + w / 2, hb.stale_of_all):
        ax.text(x, v * 100 + 1, f"{v*100:.2f}", ha="center", fontsize=7)
    ax.set_xticks(xs)
    ax.set_xticklabels([TNAME[T] for T in TS])
    ax.set_ylim(0, 100)
    ax.set_xlabel("置いておく時間")
    ax.set_ylabel("古いデータを返した割合（全部のうち、%）")
    ax.set_title("よく使われるデータほど速く書きかわると、古い割合が大きく増える")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1154_hot.png", SRC)

    (RES / "a1154_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
