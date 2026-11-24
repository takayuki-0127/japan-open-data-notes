"""1217 一度罠にかかった生き物が罠を避けるようになると、数の見込みはどちらにずれるのか？（架空のデータ）

架空のD森の種C（小さなけもの）。本当の数を作成者が置き、生け捕りの罠（捕まえて印を付けて放す）を毎晩しかける。
まだ捕まっていないものは1晩に p の見込みで捕まり、一度捕まったものは c＝p×（かかりやすさの倍率）で捕まる。
倍率が1より小さいと罠を避ける、1より大きいと罠を好む（えさを覚える）。
見込み方：①2晩の印の数え方、②毎晩同じ見込みとみなす見込み方、③初めて捕まった数の減り方から見込む見込み方。
②③は、頭数の候補ごとに捕まり方の当てはまりを計算し、いちばん当てはまる頭数を探す。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.special import gammaln
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1217
SRC = "架空のD森の種C（作成者が置いた数・捕まる見込みからの乱数、seed 1217）"
rng = np.random.default_rng(SEED)
N = 100
P = 0.3
RATIOS = [0.25, 0.5, 1.0, 1.5, 2.0]
NMAX = 3000
NGRID = np.arange(1, NMAX + 1)


def trap(rng, reps, nights, p, ratio, het=0.0, n=N):
    """reps×n×nights の捕まった記録。het は捕まりやすさの個体差（0なら全員同じ）"""
    if het > 0:
        z = rng.normal(0, het, (reps, n))
        lp = np.log(p / (1 - p)) + z
        pi = 1 / (1 + np.exp(-lp))
    else:
        pi = np.full((reps, n), p)
    ci = np.clip(pi * ratio, 0, 0.99)
    caught_before = np.zeros((reps, n), bool)
    hist = np.zeros((reps, n, nights), bool)
    for j in range(nights):
        pr = np.where(caught_before, ci, pi)
        x = rng.random((reps, n)) < pr
        hist[:, :, j] = x
        caught_before |= x
    return hist


def est_two_nights(hist):
    n1 = hist[:, :, 0].sum(1); n2 = hist[:, :, 1].sum(1); m2 = (hist[:, :, 0] & hist[:, :, 1]).sum(1)
    return (n1 + 1) * (n2 + 1) / (m2 + 1) - 1


def _best(ll, Mt):
    ll = np.where(NGRID[None, :] >= Mt[:, None], ll, -np.inf)
    i = ll.argmax(1)
    return NGRID[i].astype(float), (i == NMAX - 1)


def est_constant(hist):
    """毎晩、だれでも同じ見込みで捕まるとみなす"""
    reps, n, K = hist.shape
    Mt = hist.any(2).sum(1).astype(float)
    tot = hist.sum((1, 2)).astype(float)
    Ng = NGRID[None, :].astype(float)
    p = np.clip(tot[:, None] / (K * Ng), 1e-12, 1 - 1e-12)
    ll = gammaln(Ng + 1) - gammaln(np.maximum(Ng - Mt[:, None], 0) + 1) + tot[:, None] * np.log(p) + (K * Ng - tot[:, None]) * np.log(1 - p)
    return _best(ll, Mt)


def est_first_only(hist):
    """初めて捕まった数だけを使う（一度捕まったあとの捕まり方は見込みに使わない）"""
    reps, n, K = hist.shape
    first = np.zeros((reps, K))
    seen = np.zeros((reps, n), bool)
    for j in range(K):
        first[:, j] = (hist[:, :, j] & ~seen).sum(1)
        seen |= hist[:, :, j]
    before = np.cumsum(np.c_[np.zeros(reps), first[:, :-1]], 1)   # その晩より前に捕まった数
    Mt = first.sum(1)
    Ng = NGRID[None, :].astype(float)
    expo = K * Ng - before.sum(1)[:, None]                          # まだ捕まっていないものが罠に出会った回数
    p = np.clip(Mt[:, None] / expo, 1e-12, 1 - 1e-12)
    ll = gammaln(Ng + 1) - gammaln(np.maximum(Ng - Mt[:, None], 0) + 1) + Mt[:, None] * np.log(p) + (expo - Mt[:, None]) * np.log(1 - p)
    return _best(ll, Mt), first


def summ(x):
    r = x / N * 100
    return {"mean_pct": round(float(r.mean()), 2), "median_pct": round(float(np.median(r)), 2),
            "p10_pct": round(float(np.quantile(r, .1)), 2), "p90_pct": round(float(np.quantile(r, .9)), 2)}


def main():
    out = {}
    # ① 2晩：倍率ごと（2,000回）
    two = []
    for ratio in RATIOS:
        h = trap(rng, 2000, 2, P, ratio)
        e = est_two_nights(h)
        s = summ(e)
        s.update({"ratio": ratio, "recapture_chance": round(P * ratio, 3),
                  "marked_share_night2_pct": round(float(((h[:, :, 0] & h[:, :, 1]).sum(1) / h[:, :, 1].sum(1)).mean() * 100), 2),
                  "formula_pct": round(float((P + (1 - P) / ratio) * 100), 2)})
        two.append(s)
    tw = pd.DataFrame(two)
    tw.to_csv(RES / "two_nights.csv", index=False)
    out["two_nights"] = tw.to_dict("records")

    # ② 5晩：3つの見込み方（1,000回）
    five = []
    for ratio in RATIOS:
        h = trap(rng, 1000, 5, P, ratio)
        e1 = est_two_nights(h)
        e2, cap2 = est_constant(h)
        (e3, cap3), first = est_first_only(h)
        for meth, e, cap in [("2晩の印の数え方（1・2晩目）", e1, np.zeros(len(e1), bool)),
                             ("毎晩同じ見込みとみなす", e2, cap2), ("初めて捕まった数の減り方から", e3, cap3)]:
            s = summ(e); s.update({"ratio": ratio, "method": meth, "hit_upper_pct": round(float(cap.mean() * 100), 2),
                                   "distinct_caught_mean": round(float(h.any(2).sum(1).mean()), 2)})
            five.append(s)
        if ratio == 0.5:
            ex = h[0]
            pd.DataFrame({"animal_id": np.arange(1, N + 1), **{f"night{j+1}": ex[:, j].astype(int) for j in range(5)}}).to_csv(
                DATA / "capture_history_ratio05_example.csv", index=False)
            out["example_ratio05"] = {"first_captures_by_night": first[0].astype(int).tolist(),
                                      "recaptures_by_night": [int(ex[:, j].sum() - first[0, j]) for j in range(5)],
                                      "distinct_caught": int(ex.any(1).sum())}
    fv = pd.DataFrame(five)
    fv.to_csv(RES / "five_nights.csv", index=False)
    out["five_nights"] = fv.to_dict("records")

    # ③ 確かめ：p 4×倍率5×晩の数3×個体差2＝120通り（各200回）
    grid = []
    gr = np.random.default_rng(SEED * 7)
    for p in [0.1, 0.2, 0.3, 0.5]:
        for ratio in RATIOS:
            for K in [3, 5, 8]:
                for het in [0.0, 1.0]:
                    h = trap(gr, 200, K, p, ratio, het)
                    e2, c2 = est_constant(h)
                    (e3, c3), _ = est_first_only(h)
                    e1 = est_two_nights(h)
                    rec = {"p": p, "ratio": ratio, "nights": K, "individual_diff": "あり" if het else "なし"}
                    for key, e, c in [("two", e1, None), ("const", e2, c2), ("first", e3, c3)]:
                        rec[f"{key}_median_pct"] = round(float(np.median(e) / N * 100), 2)
                        rec[f"{key}_p10_pct"] = round(float(np.quantile(e, .1) / N * 100), 2)
                        rec[f"{key}_p90_pct"] = round(float(np.quantile(e, .9) / N * 100), 2)
                        if c is not None:
                            rec[f"{key}_hit_upper_pct"] = round(float(c.mean() * 100), 2)
                    grid.append(rec)
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid.csv", index=False)

    def rng_of(df, col):
        return [float(df[col].min()), float(df[col].max())]
    rob = {"n_settings": int(len(gd))}
    nh = gd[gd.individual_diff == "なし"]
    for lab, sub in [("shy", nh[nh.ratio < 1]), ("happy", nh[nh.ratio > 1]), ("same", nh[nh.ratio == 1])]:
        rob[f"{lab}_n"] = int(len(sub))
        for key in ["two", "const", "first"]:
            rob[f"{lab}_{key}_median_range_pct"] = rng_of(sub, f"{key}_median_pct")
    rob["shy_const_over100_share_pct"] = round(float((nh[nh.ratio < 1].const_median_pct > 100).mean() * 100), 2)
    rob["happy_const_under100_share_pct"] = round(float((nh[nh.ratio > 1].const_median_pct < 100).mean() * 100), 2)
    sub = nh[nh.p >= 0.2]
    rob["first_within10_share_p_ge_02_pct"] = round(float((sub.first_median_pct.sub(100).abs() <= 10).mean() * 100), 2)
    rob["const_within10_share_p_ge_02_pct"] = round(float((sub.const_median_pct.sub(100).abs() <= 10).mean() * 100), 2)
    rob["n_p_ge_02"] = int(len(sub))
    for lab, ss in [("shy", sub[sub.ratio < 1]), ("happy", sub[sub.ratio > 1])]:
        for key in ["two", "const", "first"]:
            rob[f"p_ge_02_{lab}_{key}_median_range_pct"] = rng_of(ss, f"{key}_median_pct")
    rob["p01_const_hit_upper_max_pct"] = float(nh[nh.p == 0.1].const_hit_upper_pct.max())
    rob["p01_two_ratio1_median_range_pct"] = rng_of(nh[(nh.p == 0.1) & (nh.ratio == 1)], "two_median_pct")
    sp = nh[nh.p == 0.1]
    rob["first_width_p01_mean_pt"] = round(float((sp.first_p90_pct - sp.first_p10_pct).mean()), 2)
    rob["const_width_p01_mean_pt"] = round(float((sp.const_p90_pct - sp.const_p10_pct).mean()), 2)
    rob["first_hit_upper_p01_max_pct"] = float(sp.first_hit_upper_pct.max())
    hh = gd[gd.individual_diff == "あり"]
    rob["het_n"] = int(len(hh))
    zz = np.random.default_rng(SEED * 11).normal(0, 1.0, 200000)
    pp = 1 / (1 + np.exp(-(np.log(0.3 / 0.7) + zz)))
    rob["het_p03_chance_p10_p90"] = [round(float(np.quantile(pp, .1)), 3), round(float(np.quantile(pp, .9)), 3)]
    rob["het_first_under100_share_pct"] = round(float((hh.first_median_pct < 100).mean() * 100), 2)
    rob["het_const_within10_share_pct"] = round(float((hh.const_median_pct.sub(100).abs() <= 10).mean() * 100), 2)
    rob["het_first_median_range_pct"] = rng_of(hh, "first_median_pct")
    rob["het_const_median_range_pct"] = rng_of(hh, "const_median_pct")
    rob["het_ratio1_first_median_range_pct"] = rng_of(hh[hh.ratio == 1], "first_median_pct")
    out["robust"] = rob
    json.dump(out, open(RES / "a1217_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：2晩の見込み
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(len(RATIOS))
    cols = [ORANGE, ORANGE, GRAY, BLUE, BLUE]
    ax.bar(xs, tw.median_pct, color=cols, width=0.6)
    ax.scatter(xs, tw.formula_pct, color=INK, marker="_", s=400, zorder=3, label="式の目安（数が多いときの値）")
    for x, v in zip(xs, tw.median_pct):
        ax.text(x, v - 4, f"{v:g}%", ha="center", va="top", fontsize=9, color="white")
    ax.axhline(100, color=INK, ls="--", lw=1)
    ax.set_xticks(xs); ax.set_xticklabels(["0.25倍\n（強く避ける）", "0.5倍", "1倍\n（変わらない）", "1.5倍", "2倍\n（好む）"])
    ax.set_xlabel("一度捕まったあとの捕まりやすさ（はじめの何倍か）"); ax.set_ylabel("見込んだ数÷本当の数（%、中央値）")
    ax.set_ylim(0, max(tw.median_pct.max(), tw.formula_pct.max()) * 1.15)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("2晩の印の数え方：罠を避けると多く、好むと少なく見込んだ")
    save(fig, "a1217_two_nights.png", SRC, y=-0.1)

    # 図2：5晩、3つの見込み方
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    meths = ["2晩の印の数え方（1・2晩目）", "毎晩同じ見込みとみなす", "初めて捕まった数の減り方から"]
    mc = [LIGHT, ORANGE, BLUE]
    for i, m in enumerate(meths):
        v = fv[fv.method == m].median_pct.values
        ax.bar(xs + (i - 1) * 0.27, v, width=0.27, color=mc[i], label=m)
    ax.axhline(100, color=INK, ls="--", lw=1)
    ax.set_xticks(xs); ax.set_xticklabels(["0.25倍", "0.5倍", "1倍", "1.5倍", "2倍"])
    ax.set_xlabel("一度捕まったあとの捕まりやすさ（はじめの何倍か）"); ax.set_ylabel("見込んだ数÷本当の数（%、中央値）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("5晩・個体差なし：初めて捕まった数だけで見込むと、倍率によらずほぼ当たった")
    save(fig, "a1217_five_nights.png", SRC)

    # 図3：確かめ（p＝0.3・5晩、個体差なし／あり）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    s3 = gd[(gd.p == 0.3) & (gd.nights == 5)]
    items = [("const", "なし", "毎晩同じ見込み・個体差なし", ORANGE), ("const", "あり", "毎晩同じ見込み・個体差あり", "#f3b394"),
             ("first", "なし", "初めて捕まった数から・個体差なし", BLUE), ("first", "あり", "初めて捕まった数から・個体差あり", LIGHT)]
    for i, (key, hd, lab, col) in enumerate(items):
        v = s3[s3.individual_diff == hd].sort_values("ratio")[f"{key}_median_pct"].values
        ax.bar(xs + (i - 1.5) * 0.2, v, width=0.2, color=col, label=lab)
    ax.axhline(100, color=INK, ls="--", lw=1)
    ax.set_xticks(xs); ax.set_xticklabels(["0.25倍", "0.5倍", "1倍", "1.5倍", "2倍"])
    ax.set_xlabel("一度捕まったあとの捕まりやすさ（はじめの0.3の何倍か、5晩、各200回）")
    ax.set_ylabel("見込んだ数÷本当の数（%、中央値）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("捕まりやすさに個体差があると、初めて捕まった数からの見込みも少なく出た")
    save(fig, "a1217_grid.png", SRC)
    print(json.dumps(out["two_nights"], ensure_ascii=False)); print(fv.to_string()); print(json.dumps(rob, ensure_ascii=False))


if __name__ == "__main__":
    main()
