"""1152 よく使われるものへの偏りが大きいときと小さいときで、同じ大きさの置き場所の効き目はどれだけ違うのか？（架空のデータ）

作成者が置いた架空のアプリのデータ1万件への問い合わせの列。r番目に人気のデータが選ばれる確率は 1÷r^a に比例すると置いた
（a を「偏り」と呼ぶ。a が大きいほど、よく使われるものへの偏りが大きい）。置き場所（キャッシュ）は件数で数え、
いっぱいになったら、最後に使われてからいちばん長くたったものを捨てる。
(1) 置き場所を全体の1%（100件）に決め、偏り a＝0.5〜1.3 の9通りで当たり率を数える。
    人気の上位100件をずっと置いたときの当たり率（式：上位100件の確率の合計）と比べる
(2) 偏り1.0・1%の当たり率と同じ当たり率に、偏りごとに何件の置き場所が要るかを数える
(3) 偏りの大きい流れ（a＝1.2）と小さい流れ（a＝0.6）を、1つの置き場所に半分ずつ混ぜる
(4) 確かめ：データの件数（1,000・1万・10万）×置き場所の割合（0.3%・1%・3%）×偏り（0.6・1.0・1.2）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1152
SRC = "架空のアプリへの問い合わせ（作成者が置いた人気の偏りからの乱数、seed 1152）"
N_ITEMS = 10_000
CAP = 100
ALPHAS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
WARM, MEAS = 50_000, 200_000
SIZE_ALPHAS = [0.6, 0.8, 1.0, 1.2]
SIZES = [6, 12, 25, 50, 100, 200, 400, 800, 1600, 3200, 6400]
MIX_HI, MIX_LO = 1.2, 0.6
GRID_N = [1_000, 10_000, 100_000]
GRID_FRAC = [0.003, 0.01, 0.03]
GRID_A = [0.6, 1.0, 1.2]


def r(x, d=4):
    return round(float(x), d)


def probs(n, a):
    p = 1.0 / np.arange(1, n + 1) ** a
    return p / p.sum()


def stream(rng, p, n):
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    return np.searchsorted(cdf, rng.random(n), side="right")


def recent_hits(seq, cap):
    """当たったかどうかの列（True/False）を返す"""
    c = {}
    out = []
    for x in seq.tolist():
        if x in c:
            del c[x]
            c[x] = None
            out.append(True)
        else:
            c[x] = None
            if len(c) > cap:
                del c[next(iter(c))]
            out.append(False)
    return np.array(out)


def recent_rate(seq, cap):
    return float(recent_hits(seq, cap)[WARM:].mean())


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setup": {"n_items": N_ITEMS, "cap": CAP, "cap_share": CAP / N_ITEMS, "warm": WARM, "meas": MEAS, "seed": SEED}}

    # (1) 偏りごとの当たり率（置き場所1%）
    rows = []
    for a in ALPHAS:
        p = probs(N_ITEMS, a)
        seq = stream(rng, p, WARM + MEAS)
        h = recent_rate(seq, CAP)
        ideal = float(p[:CAP].sum())
        rows.append({"alpha": a, "hit_rate": r(h), "top_cap_share_formula": r(ideal),
                     "hit_over_top": r(h / ideal), "miss_per_10000": r((1 - h) * 10000, 1),
                     "top10pct_share": r(p[:N_ITEMS // 10].sum())})
    by_a = pd.DataFrame(rows)
    by_a.to_csv(RES / "by_alpha.csv", index=False)
    out["by_alpha"] = rows
    h_lo = by_a.loc[by_a.alpha == 0.6, "hit_rate"].item()
    h_hi = by_a.loc[by_a.alpha == 1.2, "hit_rate"].item()
    m_lo = by_a.loc[by_a.alpha == 0.6, "miss_per_10000"].item()
    m_hi = by_a.loc[by_a.alpha == 1.2, "miss_per_10000"].item()
    out["hit_ratio_12_over_06"] = r(h_hi / h_lo, 3)
    out["miss_ratio_06_over_12"] = r(m_lo / m_hi, 3)

    # (2) 同じ当たり率に要る大きさ
    target = by_a.loc[by_a.alpha == 1.0, "hit_rate"].item()
    srows, need = [], []
    for a in SIZE_ALPHAS:
        p = probs(N_ITEMS, a)
        seq = stream(rng, p, WARM + MEAS)
        hs = []
        for cap in SIZES:
            h = recent_rate(seq, cap)
            hs.append(h)
            srows.append({"alpha": a, "cap": cap, "cap_share": cap / N_ITEMS, "hit_rate": r(h),
                          "top_cap_share_formula": r(p[:cap].sum())})
        hs = np.array(hs)
        # 対数の大きさで直線に補う
        if hs[-1] < target:
            n_need = None
        elif hs[0] >= target:
            n_need = SIZES[0]
        else:
            k = int(np.argmax(hs >= target))
            x0, x1 = np.log(SIZES[k - 1]), np.log(SIZES[k])
            n_need = float(np.exp(x0 + (target - hs[k - 1]) / (hs[k] - hs[k - 1]) * (x1 - x0)))
        need.append({"alpha": a, "target_hit": r(target), "cap_needed": None if n_need is None else round(n_need),
                     "cap_needed_share": None if n_need is None else r(n_need / N_ITEMS),
                     "times_of_100": None if n_need is None else r(n_need / CAP, 2)})
    pd.DataFrame(srows).to_csv(RES / "by_size.csv", index=False)
    pd.DataFrame(need).to_csv(RES / "size_needed.csv", index=False)
    out["size_needed"] = need

    # (3) 偏りの大きい流れと小さい流れを混ぜる（データは別々の5,000件ずつ）
    half = N_ITEMS // 2
    pA, pB = probs(half, MIX_HI), probs(half, MIX_LO)
    nA = WARM + MEAS
    sA = stream(rng, pA, nA)
    sB = stream(rng, pB, nA) + half
    isA = rng.random(nA) < 0.5
    mix = np.where(isA, sA, sB)
    hm = recent_hits(mix, CAP)
    meas = np.arange(nA) >= WARM
    mixr = {
        "share_A": 0.5, "alpha_A": MIX_HI, "alpha_B": MIX_LO, "items_each": half,
        "shared_A": r(hm[meas & isA].mean()), "shared_B": r(hm[meas & ~isA].mean()), "shared_all": r(hm[meas].mean()),
        "alone100_A": r(recent_rate(sA, CAP)), "alone100_B": r(recent_rate(sB, CAP)),
        "alone50_A": r(recent_rate(sA, CAP // 2)), "alone50_B": r(recent_rate(sB, CAP // 2)),
    }
    mixr["split50_all"] = r((mixr["alone50_A"] + mixr["alone50_B"]) / 2)
    mixr["mean_of_alone100"] = r((mixr["alone100_A"] + mixr["alone100_B"]) / 2)
    # 置き場所の中身：測る期間に、100件のうち平均何件を偏り0.6の流れのデータが占めたか
    # あわせて、偏り0.6のデータが置き場所にいる間に一度も当たらずに捨てられた割合
    c, used = {}, {}
    wasted_B = total_B = 0
    nb = 0
    occ_sum = 0
    for i, x in enumerate(mix.tolist()):
        if x in c:
            del c[x]
            c[x] = None
            used[x] = True
        else:
            c[x] = None
            used[x] = False
            nb += (x >= half)
            if len(c) > CAP:
                y = next(iter(c))
                del c[y]
                nb -= (y >= half)
                if i >= WARM and y >= half:
                    total_B += 1
                    wasted_B += (not used[y])
        if i >= WARM:
            occ_sum += nb
    mixr["slots_B_mean"] = r(occ_sum / MEAS, 2)
    mixr["B_evicted_unused_share"] = r(wasted_B / total_B)
    out["mix"] = mixr
    # 混ぜる割合を変える
    mrows = []
    for shA in [0.2, 0.5, 0.8]:
        isA2 = isA if shA == 0.5 else rng.random(nA) < shA
        mix2 = np.where(isA2, sA, sB)
        hm2 = recent_hits(mix2, CAP)
        mrows.append({"share_A": shA, "shared_A": r(hm2[meas & isA2].mean()), "shared_B": r(hm2[meas & ~isA2].mean()),
                      "shared_all": r(hm2[meas].mean()), "alone100_A": mixr["alone100_A"]})
    pd.DataFrame(mrows).to_csv(RES / "mix_share.csv", index=False)
    out["mix_share"] = mrows

    # (4) 確かめ
    grows = []
    for n in GRID_N:
        for fr in GRID_FRAC:
            cap = int(round(n * fr))
            for a in GRID_A:
                p = probs(n, a)
                seq = stream(rng, p, WARM + MEAS)
                h = recent_rate(seq, cap)
                ideal = float(p[:cap].sum())
                grows.append({"n_items": n, "cap_share": fr, "cap": cap, "alpha": a, "hit_rate": r(h),
                              "top_cap_share_formula": r(ideal), "hit_over_top": r(h / ideal)})
    g = pd.DataFrame(grows)
    g.to_csv(RES / "grid.csv", index=False)
    piv = g.pivot_table(index=["n_items", "cap_share"], columns="alpha", values="hit_rate").reset_index()
    piv["ratio_12_06"] = piv[1.2] / piv[0.6]
    out["grid_summary"] = {
        "hit_06_range": [r(g[g.alpha == 0.6].hit_rate.min()), r(g[g.alpha == 0.6].hit_rate.max())],
        "hit_10_range": [r(g[g.alpha == 1.0].hit_rate.min()), r(g[g.alpha == 1.0].hit_rate.max())],
        "hit_12_range": [r(g[g.alpha == 1.2].hit_rate.min()), r(g[g.alpha == 1.2].hit_rate.max())],
        "ratio_12_06_range": [r(piv.ratio_12_06.min(), 3), r(piv.ratio_12_06.max(), 3)],
        "hit_over_top_06_range": [r(g[g.alpha == 0.6].hit_over_top.min()), r(g[g.alpha == 0.6].hit_over_top.max())],
        "hit_over_top_12_range": [r(g[g.alpha == 1.2].hit_over_top.min()), r(g[g.alpha == 1.2].hit_over_top.max())],
        "order_kept_all": bool(((piv[0.6] < piv[1.0]) & (piv[1.0] < piv[1.2])).all()),
        "n_cases": int(len(piv)),
    }

    # data：偏り0.6と1.2の問い合わせの先頭2万件
    p06, p12 = probs(N_ITEMS, 0.6), probs(N_ITEMS, 1.2)
    d = pd.DataFrame({"i": np.arange(20000), "item_alpha06": stream(np.random.default_rng(SEED + 1), p06, 20000) + 1,
                      "item_alpha12": stream(np.random.default_rng(SEED + 2), p12, 20000) + 1})
    d.to_csv(DATA / "requests_sample.csv", index=False)
    pd.DataFrame({"rank": np.arange(1, N_ITEMS + 1), "p_alpha06": np.round(p06, 8), "p_alpha10": np.round(probs(N_ITEMS, 1.0), 8),
                  "p_alpha12": np.round(p12, 8)}).to_csv(DATA / "popularity.csv", index=False)

    # 図1：偏りごとの当たり率
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.bar(by_a.alpha - 0.022, by_a.hit_rate * 100, width=0.042, color=BLUE, label="使われてから最も長くたったものを捨てる置き場所（乱数で数えた）")
    ax.bar(by_a.alpha + 0.022, by_a.top_cap_share_formula * 100, width=0.042, color=LIGHT, label="人気の上位100件をずっと置いた（式）")
    for x, y in zip(by_a.alpha, by_a.hit_rate):
        ax.text(x - 0.022, y * 100 + 1, f"{y*100:.2f}", ha="center", fontsize=6.8, color=INK)
    ax.set_ylim(0, 100)
    ax.set_xticks(by_a.alpha)
    ax.set_xlabel("偏り a（r番目に人気のデータの選ばれやすさ ∝ 1÷r^a）")
    ax.set_ylabel("当たり率（%）")
    ax.set_title("同じ置き場所（1万件のうち100件）でも、当たり率は偏りで大きく変わる")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1152_by_alpha.png", SRC)

    # 図2：同じ当たり率に要る大きさ
    sz = pd.DataFrame(srows)
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = {0.6: ORANGE, 0.8: GRAY, 1.0: BLUE, 1.2: GREEN}
    for a in SIZE_ALPHAS:
        s = sz[sz.alpha == a]
        ax.plot(s.cap, s.hit_rate * 100, marker="o", color=cols[a], label=f"偏り {a}")
    ax.axhline(target * 100, color=INK, lw=0.8, ls="--")
    ax.text(SIZES[0], target * 100 + 1.5, f"偏り1.0・100件の当たり率 {target*100:.2f}%", fontsize=8, color=INK)
    ax.set_xscale("log")
    ax.set_xticks(SIZES)
    ax.set_xticklabels([str(s) for s in SIZES])
    ax.set_ylim(0, 100)
    ax.set_xlabel("置き場所の大きさ（件、データは全部で1万件）")
    ax.set_ylabel("当たり率（%）")
    ax.set_title("同じ当たり率に届くのに要る置き場所の大きさ")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1152_size_needed.png", SRC)

    # 図3：混ぜたとき
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    labels = ["偏り1.2の流れ", "偏り0.6の流れ"]
    alone = [mixr["alone100_A"], mixr["alone100_B"]]
    shared = [mixr["shared_A"], mixr["shared_B"]]
    x = np.arange(2)
    ax.bar(x - 0.18, np.array(alone) * 100, width=0.34, color=LIGHT, label="その流れだけで100件を使う")
    ax.bar(x + 0.18, np.array(shared) * 100, width=0.34, color=BLUE, label="2つの流れを半分ずつ混ぜて100件を分け合う")
    for xi, v in zip(x - 0.18, alone):
        ax.text(xi, v * 100 + 1, f"{v*100:.2f}", ha="center", fontsize=8.5)
    for xi, v in zip(x + 0.18, shared):
        ax.text(xi, v * 100 + 1, f"{v*100:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("その流れの当たり率（%）")
    ax.set_title("偏りの小さい流れと混ぜると、偏りの大きい流れの当たり率が下がる")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1152_mix.png", SRC)

    (RES / "a1152_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
