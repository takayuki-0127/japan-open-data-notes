"""812 「4.5以上」で絞り込むと、良い店は何%外れるのか？（架空のデータ）

架空の店に「本当の満足度」を置き、本当の満足度4.3以上を「良い店」とする。
見かけの星の平均で「4.5以上」に絞り込んだとき、良い店がどれだけ残り、どれだけ外れるかを数える。
店の作り方（本当の満足度・件数・1件の星）は 801 と同じ（本当の満足度の範囲の外は引き直す）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 812
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 812）"
STARS = np.arange(1, 6)
N_SHOP = 20000
REPS = 10                 # 2万軒を10回（計20万軒）
GOOD = 4.3                # 「良い店」：本当の満足度4.3以上
BANDS = [(1, 4, "1〜4件"), (5, 19, "5〜19件"), (20, 99, "20〜99件"), (100, 1000, "100件以上")]


def star_probs(mu):
    """平均が mu になる1〜5の分布（801 と同じ）"""
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / 0.9) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def true_sat(rng, n, spread, clip=False):
    """本当の満足度：平均3.9の正規分布。2.5〜4.8の外は引き直す"""
    x = rng.normal(3.9, spread, n)
    if clip:  # 確かめ用：801 と同じ「切る」置き方
        return np.clip(x, 2.5, 4.8)
    bad = (x < 2.5) | (x > 4.8)
    while bad.any():
        x[bad] = rng.normal(3.9, spread, bad.sum())
        bad = (x < 2.5) | (x > 4.8)
    return x


def make_shops(rng, n, spread=0.35, nmax=1000, clip=False):
    true = true_sat(rng, n, spread, clip)
    n_rev = np.round(np.exp(rng.uniform(0, np.log(nmax), n))).astype(int)
    cnt = rng.multinomial(n_rev, star_probs(true))
    obs = (cnt * STARS).sum(1) / n_rev
    return pd.DataFrame({"true": true, "n": n_rev, "mean": obs})


def filt(df, th, min_n=1, good=GOOD):
    g = df.true >= good
    p = (df["mean"] >= th) & (df.n >= min_n)
    return {"pass_shops": int(p.sum()), "good_shops": int(g.sum()),
            "good_kept": round(float((g & p).sum() / g.sum()), 3),          # 良い店のうち残った割合
            "good_missed": round(float((g & ~p).sum() / g.sum()), 3),      # 良い店のうち外れた割合
            "pass_good_share": round(float((g & p).sum() / max(p.sum(), 1)), 3),  # 残った店のうち良い店の割合
            "pass_below_4_0": round(float(((df.true < 4.0) & p).sum() / max(p.sum(), 1)), 3),
            "pass_n_le_4": round(float(((df.n <= 4) & p).sum() / max(p.sum(), 1)), 3)}


def many(seed_base, spread=0.35, nmax=1000, clip=False):
    return pd.concat([make_shops(np.random.default_rng(seed_base + r), N_SHOP, spread, nmax, clip) for r in range(REPS)],
                     ignore_index=True)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    df1 = make_shops(rng, N_SHOP)
    d = df1.copy(); d.insert(0, "shop_id", np.arange(1, N_SHOP + 1))
    d.to_csv(DATA / "shops.csv", index=False, float_format="%.4f")

    df = many(SEED * 100)
    base = filt(df, 4.5)

    # 1) 件数の帯ごと：良い店が4.5以上に残る割合と、残った店の中身
    bands = []
    p = df["mean"] >= 4.5; g = df.true >= GOOD
    for lo, hi, lab in BANDS:
        b = df.n.between(lo, hi)
        bands.append({"band": lab, "good_shops": int((g & b).sum()),
                      "good_kept": round(float((g & b & p).sum() / (g & b).sum()), 3),
                      "share_of_pass_list": round(float((b & p).sum() / p.sum()), 3),
                      "pass_good_share": round(float((g & b & p).sum() / max((b & p).sum(), 1)), 3)})
    pd.DataFrame(bands).to_csv(RES / "by_count_band.csv", index=False)

    # 2) 絞り込み方を変える
    rules = []
    for lab, th, mn in [("3.5以上", 3.5, 1), ("4.0以上", 4.0, 1), ("4.3以上", 4.3, 1), ("4.5以上", 4.5, 1),
                        ("4.0以上かつ20件以上", 4.0, 20), ("4.3以上かつ20件以上", 4.3, 20), ("4.5以上かつ20件以上", 4.5, 20)]:
        rules.append({"rule": lab, **filt(df, th, mn)})
    pd.DataFrame(rules).to_csv(RES / "filter_rules.csv", index=False)

    # 3) しきい値を動かす（件数の条件なし・20件以上）
    ths = np.round(np.arange(3.6, 4.91, 0.05), 2)
    sweep = {"th": ths.tolist(),
             "all_kept": [filt(df, t)["good_kept"] for t in ths], "all_good_share": [filt(df, t)["pass_good_share"] for t in ths],
             "n20_kept": [filt(df, t, 20)["good_kept"] for t in ths], "n20_good_share": [filt(df, t, 20)["pass_good_share"] for t in ths]}

    # 4) 本当の満足度と件数ごとに、4.5以上に入る確率
    tgrid = np.round(np.arange(3.5, 4.81, 0.05), 2)
    curve = {}
    for k in [3, 20, 100, 500]:
        pr = star_probs(tgrid)
        curve[str(k)] = [round(float(((rng.multinomial(k, pr[i], size=20000) * STARS).sum(1) / k >= 4.5).mean()), 3)
                         for i in range(len(tgrid))]
    pt = {k: {"true_4_4": v[list(tgrid).index(4.4)], "true_4_6": v[list(tgrid).index(4.6)],
              "true_4_0": v[list(tgrid).index(4.0)]} for k, v in curve.items()}

    # 5) 確かめ：「良い店」の線・店どうしの差・件数の上限を変える
    robust = {}
    for lab, gd, sp, nm in [("基本（良い店4.3以上・差0.35・件数1〜1,000件）", 4.3, 0.35, 1000),
                            ("良い店を4.2以上", 4.2, 0.35, 1000), ("良い店を4.4以上", 4.4, 0.35, 1000),
                            ("店どうしの差0.2", 4.3, 0.2, 1000), ("店どうしの差0.5", 4.3, 0.5, 1000),
                            ("件数1〜100件", 4.3, 0.35, 100)]:
        dd = df if lab.startswith("基本") else many(SEED * 1000 + int(gd * 10) + int(sp * 100) + nm, sp, nm)
        a, b = filt(dd, 4.5, 1, gd), filt(dd, 4.5, 20, gd)
        robust[lab] = {"good_share_of_shops": round(float((dd.true >= gd).mean()), 3),
                       "4.5以上": {k: a[k] for k in ["good_kept", "good_missed", "pass_good_share"]},
                       "4.5以上かつ20件以上": {k: b[k] for k in ["good_kept", "good_missed", "pass_good_share"]}}

    # 確かめ：801 と同じく2.5〜4.8の外を「切る」置き方
    dc = many(SEED * 300, clip=True)
    a = filt(dc, 4.5)
    clip_chk = {"good_share_of_shops": round(float((dc.true >= GOOD).mean()), 3),
                "share_true_at_4_8": round(float((dc.true >= 4.8).mean()), 4),
                "4.5以上": {k: a[k] for k in ["good_kept", "good_missed", "pass_good_share"]}}
    out = {"shops": int(len(df)), "good_share_of_shops": round(float(g.mean()), 3), "filter_4_5": base,
           "by_count_band": bands, "filter_rules": rules, "pass_prob_by_true_and_n": pt, "robustness": robust,
           "one_draw_20000": filt(df1, 4.5), "clip_like_801": clip_chk}
    json.dump(out, open(RES / "a812_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pd.DataFrame({"true": tgrid, **{f"n{k}": v for k, v in curve.items()}}).to_csv(RES / "pass_prob_curve.csv", index=False)
    pd.DataFrame(sweep).to_csv(RES / "threshold_sweep.csv", index=False)

    # 図1：本当の満足度と件数ごとに、「4.5以上」に入る確率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for k, col in zip(["3", "20", "100", "500"], [ORANGE, LIGHT, BLUE, INK]):
        ax.plot(tgrid, np.array(curve[k]) * 100, color=col, lw=2, label=f"口コミ{k}件")
    ax.axvspan(GOOD, 4.8, color=GREEN, alpha=.08); ax.text(4.62, 30, "良い店\n（本当の満足度\n4.3以上）", color=GREEN, fontsize=9, va="top")
    ax.axvline(4.5, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("本当の満足度"); ax.set_ylabel("見かけの平均が4.5以上になる確率（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("件数の多い良い店ほど、「4.5以上」から外れる")
    save(fig, "a812_pass_prob.png", SRC)

    # 図2：件数の帯ごと、良い店が残る割合と、残った店の内訳
    bd = pd.DataFrame(bands)
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.8))
    axs[0].barh(bd.band[::-1], bd.good_kept[::-1] * 100, color=GREEN)
    for i, v in enumerate(bd.good_kept[::-1] * 100):
        axs[0].text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    axs[0].set_xlim(0, 100); axs[0].set_xlabel("良い店のうち残った割合（%）"); axs[0].set_title("良い店は残るか", fontsize=11)
    axs[1].barh(bd.band[::-1], bd.share_of_pass_list[::-1] * 100, color=BLUE)
    for i, v in enumerate(bd.share_of_pass_list[::-1] * 100):
        axs[1].text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    axs[1].set_xlim(0, 100); axs[1].set_xlabel("「4.5以上」に残った店の内訳（%）"); axs[1].set_title("残った店はどの件数か", fontsize=11)
    axs[1].set_yticklabels([])
    fig.suptitle("「4.5以上」の一覧は、件数の少ない店で埋まる", fontsize=13)
    fig.tight_layout()
    save(fig, "a812_bands.png", SRC)

    # 図3：しきい値を動かしたとき、良い店が残る割合と、一覧の中の良い店の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(ths, np.array(sweep["all_kept"]) * 100, color=GREEN, lw=2, label="良い店のうち残った割合（件数の条件なし）")
    ax.plot(ths, np.array(sweep["all_good_share"]) * 100, color=BLUE, lw=2, label="残った店のうち良い店の割合（件数の条件なし）")
    ax.plot(ths, np.array(sweep["n20_kept"]) * 100, color=GREEN, lw=2, ls="--", label="良い店のうち残った割合（20件以上）")
    ax.plot(ths, np.array(sweep["n20_good_share"]) * 100, color=BLUE, lw=2, ls="--", label="残った店のうち良い店の割合（20件以上）")
    ax.axvline(4.5, color=GRAY, lw=.8, ls=":"); ax.text(4.51, 3, "4.5", color=GRAY, fontsize=9)
    ax.set_xlabel("絞り込みの線（見かけの星の平均がこの値以上）"); ax.set_ylabel("%"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    ax.set_title("件数の条件がないと、一覧の中の良い店は6割ほどで止まる")
    save(fig, "a812_sweep.png", SRC, y=-0.2)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
