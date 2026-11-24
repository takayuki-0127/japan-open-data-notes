"""1202 件名を2つ試して勝った方は、次の配信でも同じだけ勝つのか？（架空のデータ）

架空の店の会員向けのお知らせのメール。1つの店の読者（基本は4,000人）を半分ずつに分け、件名Aと件名Bを送って
開封率を比べる。次の配信でも同じ2つの件名をもう一度比べる。読者ごとの開く確率と、件名の本当の効き目は作成者が置く。
分け方は「配信ごとに分け直す」と「同じ半分のまま（会員番号の奇数・偶数のように固定）」の2通り。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1202
SRC = "架空の店の会員向けメールの件名（作成者が乱数で作成、seed 1202）"
MEAN_P = 0.25                      # 読者の開く確率の平均
BASE = dict(sigma=0.05, group=2000, conc=2.0)
N_PAIRS = 10000
CHUNK = 250


def sig(x):
    return 1 / (1 + np.exp(-x))


def sim(seed, sigma, group, conc, pairs, chunk=CHUNK, keep_rows=False):
    rng = np.random.default_rng(seed)
    n = 2 * group
    a, b = MEAN_P * conc, (1 - MEAN_P) * conc
    rows = []
    for s in range(0, pairs, chunk):
        P = min(chunk, pairs - s)
        p = np.clip(rng.beta(a, b, (P, n)), 1e-4, 1 - 1e-4)
        L = np.log(p / (1 - p))
        d = rng.normal(0, sigma, P) if sigma > 0 else np.zeros(P)
        pA, pB = sig(L + d[:, None]), p
        true_pt = (pA.mean(1) - pB.mean(1)) * 100
        fixed = np.zeros((P, n), dtype=bool); fixed[:, :group] = True     # 同じ半分のまま
        out = {"true_pt": true_pt}
        for t in (1, 2):
            u = rng.random((P, n))
            oA, oB = u < pA, u < pB
            ordr = np.argsort(rng.random((P, n)), axis=1)
            resh = np.zeros((P, n), dtype=bool)
            np.put_along_axis(resh, ordr[:, :group], True, axis=1)           # 配信ごとに分け直す
            for name, g in (("resh", resh), ("fixed", fixed)):
                rA = (oA & g).sum(1) / group
                rB = (oB & ~g).sum(1) / group
                out[f"{name}{t}"] = (rA - rB) * 100
        rows.append(pd.DataFrame(out))
    return pd.concat(rows, ignore_index=True)


def summarize(df, name, big=2.0):
    d1, d2, t = df[f"{name}1"], df[f"{name}2"], df["true_pt"]
    w = np.sign(d1)
    m1, m2, mt = d1.abs(), d2 * w, t * w
    bigm = m1 >= big
    return {"margin1_mean": m1.mean(), "margin2_mean": m2.mean(), "true_margin_mean": mt.mean(),
            "keep_ratio": m2.mean() / m1.mean(), "win_again": (np.sign(d2) == w).mean(),
            "winner_truly_better": (np.sign(t) == w).mean(),
            "big_share": bigm.mean(), "big_margin1_mean": m1[bigm].mean() if bigm.any() else np.nan,
            "big_margin2_mean": m2[bigm].mean() if bigm.any() else np.nan,
            "big_true_margin_mean": mt[bigm].mean() if bigm.any() else np.nan,
            "big_win_again": (np.sign(d2[bigm]) == w[bigm]).mean() if bigm.any() else np.nan,
            "corr_d1_d2": np.corrcoef(d1, d2)[0, 1],
            "sd_d1": d1.std(), "sd_true": t.std(),
            "formula_keep_ratio": np.cov(t, d1)[0, 1] / d1.var()}


def r4(x):
    return round(float(x), 4)


def main():
    t0 = time.time()
    base = sim(SEED, pairs=N_PAIRS, **BASE)
    base.round(4).to_csv(DATA / "pairs_base.csv", index=False)
    res = {"resh": {k: r4(v) for k, v in summarize(base, "resh").items()},
           "fixed": {k: r4(v) for k, v in summarize(base, "fixed").items()}}
    # 勝ち幅の帯ごと（分け直す）
    w = np.sign(base.resh1); m1 = base.resh1.abs(); m2 = base.resh2 * w; mt = base.true_pt * w
    bands = []
    for lo, hi in [(0, 0.5), (0.5, 1), (1, 1.5), (1.5, 2), (2, 3), (3, 99)]:
        s = (m1 >= lo) & (m1 < hi)
        bands.append({"band": f"{lo}〜{hi if hi < 99 else ''}", "lo": lo, "share": r4(s.mean()),
                      "margin1_mean": r4(m1[s].mean()), "margin2_mean": r4(m2[s].mean()),
                      "true_margin_mean": r4(mt[s].mean()), "win_again": r4((np.sign(base.resh2[s]) == w[s]).mean())})
    bands = pd.DataFrame(bands)
    bands.to_csv(RES / "by_margin_band.csv", index=False)

    # 効き目のない件名どうし（本当の差0）
    null = sim(SEED + 1, sigma=0.0, group=BASE["group"], conc=BASE["conc"], pairs=6000)
    res_null = {"resh": {k: r4(v) for k, v in summarize(null, "resh").items() if "true" not in k and "formula" not in k},
                "fixed": {k: r4(v) for k, v in summarize(null, "fixed").items() if "true" not in k and "formula" not in k}}

    # 確かめ：27通り（件名の効き目の散らばり × 片側の人数 × 読者の開きやすさの散らばり）
    grid = []
    gi = 0
    for sigma in [0.02, 0.05, 0.12]:
        for group in [500, 2000, 8000]:
            for conc in [0.7, 2.0, 8.0]:
                df = sim(SEED * 10 + gi, sigma=sigma, group=group, conc=conc, pairs=400, chunk=100 if group < 8000 else 25)
                gi += 1
                rr, ff = summarize(df, "resh"), summarize(df, "fixed")
                grid.append({"sigma": sigma, "group": group, "conc": conc,
                             "keep_ratio_resh": r4(rr["keep_ratio"]), "formula_keep_ratio_resh": r4(rr["formula_keep_ratio"]),
                             "win_again_resh": r4(rr["win_again"]), "truly_better_resh": r4(rr["winner_truly_better"]),
                             "keep_ratio_fixed": r4(ff["keep_ratio"]), "win_again_fixed": r4(ff["win_again"]),
                             "margin1_resh": r4(rr["margin1_mean"]), "margin2_resh": r4(rr["margin2_mean"])})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    nul = []
    gi = 0
    for group in [500, 2000, 8000]:
        for conc in [0.7, 2.0, 8.0]:
            df = sim(SEED * 100 + gi, sigma=0.0, group=group, conc=conc, pairs=1000, chunk=100 if group < 8000 else 25)
            gi += 1
            rr, ff = summarize(df, "resh"), summarize(df, "fixed")
            nul.append({"group": group, "conc": conc, "win_again_resh": r4(rr["win_again"]),
                        "win_again_fixed": r4(ff["win_again"]), "corr_fixed": r4(ff["corr_d1_d2"]),
                        "corr_resh": r4(rr["corr_d1_d2"])})
    nul = pd.DataFrame(nul)
    nul.to_csv(RES / "null_grid.csv", index=False)
    g = {"n": len(grid)}
    for c in ["keep_ratio_resh", "win_again_resh", "truly_better_resh", "keep_ratio_fixed", "win_again_fixed"]:
        g[c + "_min"] = r4(grid[c].min()); g[c + "_max"] = r4(grid[c].max())
    g["formula_gap_absmax"] = r4((grid.keep_ratio_resh - grid.formula_keep_ratio_resh).abs().max())
    small = grid[(grid.sigma == 0.02) & (grid.group <= 2000)]
    g["small_effect_small_group_n"] = len(small)
    g["small_effect_small_group_keep_min"] = r4(small.keep_ratio_resh.min())
    g["small_effect_small_group_keep_max"] = r4(small.keep_ratio_resh.max())
    g["n_keep_ratio_resh_below1"] = int((grid.keep_ratio_resh < 1).sum())
    g["n_fixed_win_again_gt_resh"] = int((grid.win_again_fixed > grid.win_again_resh).sum())
    gn = {"n": len(nul)}
    for c in ["win_again_resh", "win_again_fixed", "corr_fixed", "corr_resh"]:
        gn[c + "_min"] = r4(nul[c].min()); gn[c + "_max"] = r4(nul[c].max())

    out = {"setting": {"mean_open_prob": MEAN_P, "pairs": N_PAIRS, **BASE},
           "base": res, "null_effect0": res_null, "grid27": g, "null_grid9": gn}
    json.dump(out, open(RES / "a1202_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回目の勝ち幅と2回目の勝ち幅（分け直す）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(bands))
    ax.bar(x - 0.27, bands.margin1_mean, width=0.27, color=GRAY, label="1回目の勝ち幅")
    ax.bar(x, bands.margin2_mean, width=0.27, color=BLUE, label="同じ件名の2回目の勝ち幅")
    ax.bar(x + 0.27, bands.true_margin_mean, width=0.27, color=ORANGE, label="置いた本当の差")
    ax.set_xticks(x, ["0〜0.5", "0.5〜1", "1〜1.5", "1.5〜2", "2〜3", "3以上"])
    ax.set_xlabel("1回目の勝ち幅の帯（ポイント）"); ax.set_ylabel("平均（ポイント）"); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("どの帯でも、2回目の勝ち幅は1回目より小さく、置いた本当の差に近かった")
    save(fig, "a1202_bands.png", SRC)

    # 図2：効き目0の件名どうしで、もう一度勝った割合（分け方2通り、人数・散らばり9通り）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(len(nul))
    ax.bar(x - 0.2, nul.win_again_resh * 100, width=0.4, color=BLUE, label="配信ごとに分け直す")
    ax.bar(x + 0.2, nul.win_again_fixed * 100, width=0.4, color=ORANGE, label="同じ半分のまま")
    ax.axhline(50, color=INK, lw=0.8, ls="--")
    ax.set_xticks(x, [f"{gp:,}人\n{'大' if c == 0.7 else ('中' if c == 2.0 else '小')}" for gp, c in zip(nul.group, nul.conc)],
                  fontsize=8.5)
    ax.set_xlabel("片側の人数 / 読者の開きやすさの散らばり")
    ax.set_ylabel("1回目の勝ちが2回目も勝った割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("効き目のない件名どうしでも、同じ半分のままだと「また勝つ」が50%を超えた")
    save(fig, "a1202_null.png", SRC, y=-0.07)

    # 図3：27通りの、2回目に残る勝ち幅の割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    lbl = {0.02: "件名の効き目の散らばり 小", 0.05: "中（基本）", 0.12: "大"}
    col = {0.02: GRAY, 0.05: BLUE, 0.12: ORANGE}
    for sg in [0.02, 0.05, 0.12]:
        s = grid[grid.sigma == sg]
        ax.scatter(s.formula_keep_ratio_resh * 100, s.keep_ratio_resh * 100, color=col[sg], s=30, label=lbl[sg])
    ax.plot([0, 100], [0, 100], color=INK, lw=0.8, ls=":")
    ax.set_xlim(0, 100); ax.set_ylim(-10, 100)
    ax.axhline(0, color=GRAY, lw=0.6)
    ax.set_xlabel("式で見込んだ、残る割合（%）"); ax.set_ylabel("2回目の勝ち幅 ÷ 1回目の勝ち幅（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("2回目に残る勝ち幅は、置き方27通りで大きく動き、式の見込みとそろった")
    save(fig, "a1202_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(bands)
    print(nul)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
