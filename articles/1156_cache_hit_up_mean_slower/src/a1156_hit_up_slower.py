"""1156 当たり率が上がったのに、平均の応答が遅くなるのはどんなときか？（架空のデータ）

作成者が置いた架空のアプリの、1万種類のデータへの問い合わせ。よく使われるものへの偏りは、順位 k の使われやすさが k の −0.9 乗に比例すると置いた。
データごとに、元のデータを取りに行く時間（中央値）が違う。中央値は80msを中心に対数の標準偏差1.0で散らばり、
使われにくいものほど時間がかかる向きに相関0.5で結び付けた（順位の対数と、時間の対数の相関）。
手元の置き場所（キャッシュ）には500種類まで置ける。当たったときの時間は中央値2ms・対数の標準偏差0.3、
外れたときはそのデータの中央値・対数の標準偏差0.5（どちらも対数で正規の形）。
(1) しくみ1「外れの中身が入れかわる」：置くものの選び方を2つ比べる
    A：前の期間（20万件）の記録で、回数の多い順に500種類を置く
    B：前の期間の記録で、回数×取りに行く時間の平均 の大きい順に500種類を置く
    次の期間（100万件）の当たり率と平均の応答を数える
(2) しくみ2「当たったときが遅くなる」：置き場所を大きくするかわりに当たったときの時間が延びるとき、平均が遅くなる境目（式）を出し、乱数で照らす
(3) 確かめ：偏り×取りに行く時間の散らばり×相関×置ける数 の 54通りで（1）を数える
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1156
SRC = "架空のアプリの問い合わせ（作成者が置いた使われやすさと時間の分布からの乱数、seed 1156）"
N_ITEMS = 10_000
S = 0.9
FETCH_MED, FETCH_SD, RHO = 80.0, 1.0, 0.5
REQ_SD = 0.5
HIT_MED, HIT_SIG = 2.0, 0.3
K = 500
N_LEARN, N_EVAL = 200_000, 1_000_000
G_S = [0.7, 0.9, 1.1]
G_SD = [0.5, 1.0, 1.5]
G_RHO = [-0.5, 0.0, 0.5]
G_K = [100, 1000]
N_G_EVAL = 300_000


def r(x, d=4):
    return round(float(x), d)


def make_items(rng, s, sd, rho):
    k = np.arange(1, N_ITEMS + 1)
    p = k ** (-s)
    p /= p.sum()
    lr = np.log(k)
    zr = (lr - lr.mean()) / lr.std()
    z = rho * zr + np.sqrt(1 - rho ** 2) * rng.standard_normal(N_ITEMS)
    med = FETCH_MED * np.exp(sd * z)
    # 置いた順位と並びが同じにならないように、データの番号をでたらめに振る
    perm = rng.permutation(N_ITEMS)
    return p[perm], med[perm], k[perm]


def run(rng, p, med, rank, n_learn, n_eval, slots):
    learn = rng.choice(N_ITEMS, n_learn, p=p)
    cnt = np.bincount(learn, minlength=N_ITEMS)
    fmean = med * np.exp(REQ_SD ** 2 / 2)          # 取りに行く時間の平均（記録から分かると置いた）
    tie = rng.random(N_ITEMS) * 1e-9
    a = np.argsort(-(cnt + tie))[:slots]
    b = np.argsort(-(cnt * fmean + tie))[:slots]
    ev = rng.choice(N_ITEMS, n_eval, p=p)
    t_hit = rng.lognormal(np.log(HIT_MED), HIT_SIG, n_eval)
    t_miss = rng.lognormal(np.log(med[ev]), REQ_SD)
    res = {}
    for name, keep in (("A", a), ("B", b)):
        inc = np.zeros(N_ITEMS, bool)
        inc[keep] = True
        hit = inc[ev]
        t = np.where(hit, t_hit, t_miss)
        res[name] = {"hit_rate_pct": r(hit.mean() * 100, 3), "mean_ms": r(t.mean(), 3),
                     "mean_hit_ms": r(t[hit].mean(), 3), "mean_miss_ms": r(t[~hit].mean(), 3),
                     "miss_part_ms": r(t[~hit].sum() / n_eval, 3),
                     "p99_ms": r(np.quantile(t, 0.99), 2), "median_ms": r(np.median(t), 3),
                     "origin_per_1000": r((~hit).mean() * 1000, 2),
                     "kept_fetch_mean_ms_avg": r(fmean[keep].mean(), 2),
                     "kept_popularity_rank_median": r(np.median(rank[keep]), 1)}
    return res, a, b, fmean


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setting": {"items": N_ITEMS, "popularity_power": S, "fetch_median_center_ms": FETCH_MED,
                       "fetch_median_logsd": FETCH_SD, "corr_rank_vs_fetch": RHO, "request_logsd": REQ_SD,
                       "hit_median_ms": HIT_MED, "hit_logsd": HIT_SIG, "slots": K,
                       "learn_requests": N_LEARN, "eval_requests": N_EVAL}}

    # (1)
    p, med, kk = make_items(rng, S, FETCH_SD, RHO)
    res, a, b, fmean = run(rng, p, med, kk, N_LEARN, N_EVAL, K)
    out["policy"] = res
    A, B = res["A"], res["B"]
    out["policy_diff"] = {"hit_pt_A_minus_B": r(A["hit_rate_pct"] - B["hit_rate_pct"], 3),
                          "mean_ratio_A_over_B": r(A["mean_ms"] / B["mean_ms"], 3),
                          "mean_pct_A_vs_B": r((A["mean_ms"] / B["mean_ms"] - 1) * 100, 2),
                          "miss_mean_ratio_A_over_B": r(A["mean_miss_ms"] / B["mean_miss_ms"], 3),
                          "overlap_items": int(len(np.intersect1d(a, b))),
                          "origin_ratio_B_over_A": r(B["origin_per_1000"] / A["origin_per_1000"], 3)}
    pc = pd.DataFrame([{"setting": k, **v} for k, v in res.items()])
    pc.to_csv(RES / "policy_compare.csv", index=False)
    inA = np.zeros(N_ITEMS, int); inA[a] = 1
    inB = np.zeros(N_ITEMS, int); inB[b] = 1
    pd.DataFrame({"item_id": np.arange(N_ITEMS), "popularity_rank": kk, "share_pct": np.round(p * 100, 6),
                  "fetch_mean_ms": np.round(fmean, 3), "kept_A": inA, "kept_B": inB}).to_csv(
        DATA / "items.csv", index=False)

    # (2) しくみ2：境目（式）
    mh = HIT_MED * np.exp(HIT_SIG ** 2 / 2)
    # 1149 と同じ置き方（外れの平均90.65ms）で式を書く
    mm0 = 80.0 * np.exp(0.5 ** 2 / 2)
    br = []
    for h1 in (0.80, 0.90, 0.95):
        for dh in (0.02, 0.05):
            h2 = h1 + dh
            t2 = (h1 * mh + dh * mm0) / h2
            br.append({"hit_from_pct": r(h1 * 100, 1), "hit_to_pct": r(h2 * 100, 1),
                       "hit_ms_before": r(mh, 3), "miss_ms": r(mm0, 2),
                       "break_even_hit_ms": r(t2, 2), "break_even_ratio": r(t2 / mh, 2)})
    br = pd.DataFrame(br)
    br.to_csv(RES / "break_even.csv", index=False)
    out["break_even"] = br.to_dict("records")
    # 乱数で照らす：90%→95%、当たったときの平均を2.09msから 6ms・7ms・8ms に
    chk = []
    nn = 1_000_000
    for h, hm in ((0.90, HIT_MED), (0.95, 6.0 / np.exp(HIT_SIG ** 2 / 2)), (0.95, 7.0 / np.exp(HIT_SIG ** 2 / 2)),
                  (0.95, 8.0 / np.exp(HIT_SIG ** 2 / 2))):
        hit = rng.random(nn) < h
        t = np.where(hit, rng.lognormal(np.log(hm), HIT_SIG, nn), rng.lognormal(np.log(80.0), 0.5, nn))
        chk.append({"hit_rate_pct": r(h * 100, 1), "hit_mean_ms_set": r(hm * np.exp(HIT_SIG ** 2 / 2), 2),
                    "mean_formula_ms": r(h * hm * np.exp(HIT_SIG ** 2 / 2) + (1 - h) * mm0, 3),
                    "mean_sim_ms": r(t.mean(), 3)})
    out["slow_hit_check"] = chk
    pd.DataFrame(chk).to_csv(RES / "slow_hit_check.csv", index=False)

    # (3) 確かめ
    gr = []
    for s in G_S:
        for sd in G_SD:
            for rho in G_RHO:
                for kk_ in G_K:
                    p_, med_, rank_ = make_items(rng, s, sd, rho)
                    res_, _, _, _ = run(rng, p_, med_, rank_, N_LEARN, N_G_EVAL, kk_)
                    gr.append({"popularity_power": s, "fetch_logsd": sd, "corr_rank_vs_fetch": rho, "slots": kk_,
                               "hit_A": res_["A"]["hit_rate_pct"], "hit_B": res_["B"]["hit_rate_pct"],
                               "mean_A": res_["A"]["mean_ms"], "mean_B": res_["B"]["mean_ms"],
                               "hit_pt_A_minus_B": r(res_["A"]["hit_rate_pct"] - res_["B"]["hit_rate_pct"], 3),
                               "mean_pct_A_vs_B": r((res_["A"]["mean_ms"] / res_["B"]["mean_ms"] - 1) * 100, 2)})
    gr = pd.DataFrame(gr)
    gr.to_csv(RES / "grid.csv", index=False)
    both = gr[(gr.hit_pt_A_minus_B > 0) & (gr.mean_pct_A_vs_B > 0)]
    out["grid"] = {"n": len(gr),
                   "A_hit_higher": int((gr.hit_pt_A_minus_B > 0).sum()),
                   "A_hit_higher_and_slower": len(both),
                   "hit_pt_range": [float(gr.hit_pt_A_minus_B.min()), float(gr.hit_pt_A_minus_B.max())],
                   "mean_pct_range": [float(gr.mean_pct_A_vs_B.min()), float(gr.mean_pct_A_vs_B.max())],
                   "by_rho_mean_pct": {str(k): [float(v.min()), float(v.max())]
                                       for k, v in gr.groupby("corr_rank_vs_fetch").mean_pct_A_vs_B},
                   "by_sd_mean_pct": {str(k): [float(v.min()), float(v.max())]
                                      for k, v in gr.groupby("fetch_logsd").mean_pct_A_vs_B},
                   "by_rho_hit_pt": {str(k): [float(v.min()), float(v.max())]
                                     for k, v in gr.groupby("corr_rank_vs_fetch").hit_pt_A_minus_B}}

    # 図1：A と B
    fig, axs = plt.subplots(1, 2, figsize=(8, 4.2))
    for ax, key, lab, fmt in ((axs[0], "hit_rate_pct", "当たり率（%）", "{:g}%"),
                              (axs[1], "mean_ms", "平均の応答時間（ms）", "{:g}ms")):
        v = [A[key], B[key]]
        ax.bar([0, 1], v, color=[ORANGE, BLUE], width=0.6)
        for i, x in enumerate(v):
            ax.text(i, x * 1.02, fmt.format(x), ha="center", fontsize=9.5)
        ax.set_xticks([0, 1], ["A：回数の多い順", "B：回数×時間の順"])
        ax.set_ylim(0, max(v) * 1.18)
        ax.set_title(lab, fontsize=11.5)
    fig.suptitle("当たり率はAが高く、平均の応答はAが遅い（置ける数500・100万件）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a1156_policy.png", SRC)

    # 図2：境目（式）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    hs = np.linspace(0.0, 12.0, 241)
    for h1, h2, col, dx, dy, ha in ((0.90, 0.92, GRAY, 0.25, -9, "left"), (0.90, 0.95, BLUE, 0.0, 4, "center"),
                                    (0.95, 0.97, ORANGE, -0.25, 6, "right")):
        base = h1 * mh + (1 - h1) * mm0
        ax.plot(hs, (h2 * hs + (1 - h2) * mm0) / base * 100 - 100, color=col,
                label=f"当たり率 {h1 * 100:g}% → {h2 * 100:g}%")
        t2 = (h1 * mh + (h2 - h1) * mm0) / h2
        ax.plot([t2], [0], "o", color=col)
        ax.text(t2 + dx, dy, f"{t2:.2f}ms", color=col, fontsize=8.5, ha=ha)
    ax.axhline(0, color=INK, lw=0.8)
    ax.axvline(mh, color=GRAY, lw=0.8, ls=":")
    ax.text(mh - 0.1, 95, f"もとの当たり\n{mh:.2f}ms", fontsize=8.5, color=GRAY, ha="right")
    ax.set_xlabel("当たり率を上げたあとの、当たったときの平均（ms）")
    ax.set_ylabel("平均の応答時間の変化（%）")
    ax.set_title("当たったときが遅くなると、どこで平均が遅くなるか（式どおり）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    save(fig, "a1156_break_even.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7, 4.4))
    mk = {-0.5: ("^", GREEN, "相関 −0.5（使われにくいほど速い）"), 0.0: ("s", GRAY, "相関 0"),
          0.5: ("o", ORANGE, "相関 0.5（使われにくいほど遅い）")}
    for rho, (m, col, lab) in mk.items():
        s_ = gr[gr.corr_rank_vs_fetch == rho]
        ax.scatter(s_.hit_pt_A_minus_B, s_.mean_pct_A_vs_B, marker=m, color=col, s=30, label=lab, zorder=3)
    ax.axhline(0, color=INK, lw=0.8)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("当たり率の差 A − B（ポイント）")
    ax.set_ylabel("平均の応答時間 A が B より遅い分（%）")
    ax.set_title(f"置き方を変えた{len(gr)}通り（各30万件）")
    ax.set_xlim(-2, 55)
    ax.set_ylim(-3, 85)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "a1156_grid.png", SRC)

    (RES / "a1156_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:9000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
