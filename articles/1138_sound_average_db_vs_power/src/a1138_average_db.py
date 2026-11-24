"""1138 何曲かの音の大きさをデシベルのまま平均すると、音の強さで平均した値とどれだけずれるのか？（架空のデータ）

作成者が乱数で作った架空のアルバム（12曲）の曲ごとの大きさ（dB）を、
①dBの値をそのまま足して曲数で割る、②音の強さ（10^(dB/10)）に戻して平均し、dBに直す、
③②を曲の長さで重みづけする（つなげた波形を測った値と同じ）、の3つで平均し、ずれを数える。
大きさの dB は、作成者が置いた基準の強さを0dBとした値（−14dB前後）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1138
SRC = "架空のアルバムと曲の大きさ（作成者が乱数で作成、seed 1138）"
N_ALB = 2000
N_SONG = 12
MU = -14.0
SIGMA = 3.0
LEN_MIN, LEN_MAX = 120, 300   # 曲の長さ（秒）
SR_CHECK = 1000               # 波形で確かめるときの1秒あたりの点の数
N_CHECK = 100
SIGMAS = [1, 3, 6, 10]
NS = [5, 12, 50]
SHAPES = ["左右対称", "静かな曲がときどき入る"]


def r(x, d=3):
    return round(float(x), d)


def to_pow(L):
    return 10 ** (np.asarray(L) / 10)


def to_db(p):
    return 10 * np.log10(p)


def three(L, w):
    a = L.mean(axis=-1)
    b = to_db(to_pow(L).mean(axis=-1))
    c = to_db((to_pow(L) * w).sum(axis=-1) / w.sum(axis=-1))
    return a, b, c


def draw(rng, n_alb, n, sigma, shape):
    if shape == SHAPES[0]:
        L = MU + sigma * rng.standard_normal((n_alb, n))
    else:
        # 9割は σ の左右対称、1割は15dB静かな曲（ばらつきは同じ）
        L = MU + sigma * rng.standard_normal((n_alb, n)) - 15.0 * (rng.random((n_alb, n)) < 0.1)
    w = rng.uniform(LEN_MIN, LEN_MAX, (n_alb, n))
    return L, w


def q(a, p):
    return float(np.quantile(a, p))


def main():
    rng = np.random.default_rng(SEED)
    out = {"settings": {"albums": N_ALB, "songs": N_SONG, "mean_level_db": MU, "sigma_db": SIGMA,
                        "song_length_sec": [LEN_MIN, LEN_MAX], "seed": SEED}}

    # ---- 基本：σ3dB・12曲・左右対称 ----
    L, w = draw(rng, N_ALB, N_SONG, SIGMA, SHAPES[0])
    a, b, c = three(L, w)
    gap_ab, gap_ac = b - a, c - a
    alb = pd.DataFrame({"album": np.arange(N_ALB), "sd_of_songs_db": np.round(L.std(axis=1), 3),
                        "db_average": np.round(a, 3), "power_average": np.round(b, 3), "length_weighted_power_average": np.round(c, 3),
                        "gap_power_minus_db": np.round(gap_ab, 3)})
    alb.to_csv(DATA / "albums.csv", index=False)
    songs = pd.DataFrame({"album": np.repeat(np.arange(N_ALB), N_SONG), "song": np.tile(np.arange(1, N_SONG + 1), N_ALB),
                          "level_db": np.round(L.ravel(), 3), "length_sec": np.round(w.ravel(), 1)})
    songs.to_csv(DATA / "songs.csv", index=False)
    formula = SIGMA ** 2 * np.log(10) / 20
    out["base"] = {"gap_power_minus_db_mean": r(np.mean(gap_ab)), "gap_p05": r(q(gap_ab, .05)), "gap_p95": r(q(gap_ab, .95)),
                   "gap_min": r(gap_ab.min()), "gap_max": r(gap_ab.max()),
                   "gap_length_weighted_mean": r(np.mean(gap_ac)), "gap_length_weighted_p05": r(q(gap_ac, .05)),
                   "gap_length_weighted_p95": r(q(gap_ac, .95)),
                   "share_db_average_lower": r(np.mean(a < b), 4),
                   "formula_sigma2_ln10_over_20": r(formula), "coef_ln10_over_20": r(np.log(10) / 20), "formula_with_12songs": r(formula * (N_SONG - 1) / N_SONG),
                   "corr_gap_vs_song_sd": r(np.corrcoef(L.std(axis=1), gap_ab)[0, 1], 3)}

    # ---- 波形で確かめる：つなげた波形の大きさは③と同じになるか ----
    diffs = []
    for i in range(N_CHECK):
        parts = []
        for j in range(N_SONG):
            nn = int(round(w[i, j] * SR_CHECK))
            x = rng.standard_normal(nn)
            x *= np.sqrt(to_pow(L[i, j]) / np.mean(x ** 2))
            parts.append(x)
        wave = np.concatenate(parts)
        meas = to_db(np.mean(wave ** 2))
        wn = np.array([len(p) for p in parts], float)
        diffs.append({"album": i, "measured_db": r(meas, 4), "length_weighted_power_average": r(three(L[i], wn)[2], 4),
                      "db_average": r(a[i], 4), "diff_measured_minus_weighted": r(meas - three(L[i], wn)[2], 6)})
    dfw = pd.DataFrame(diffs)
    dfw.to_csv(RES / "waveform_check.csv", index=False)
    out["waveform_check"] = {"albums": N_CHECK, "max_abs_diff_to_length_weighted": r(dfw.diff_measured_minus_weighted.abs().max(), 6),
                             "mean_measured_minus_db_average": r((dfw.measured_db - dfw.db_average).mean(), 3)}

    # ---- 例：静かな曲が1曲あるアルバム ----
    ex_L = np.array([-12.5, -13.2, -14.0, -13.6, -12.8, -14.4, -13.0, -14.1, -13.5, -12.9, -13.8, -30.0])
    ex_w = np.array([210, 235, 198, 260, 224, 189, 247, 215, 230, 205, 240, 60.0])
    ea, eb, ec = three(ex_L, ex_w)
    ea11, eb11, ec11 = three(ex_L[:11], ex_w[:11])
    out["example_quiet_song"] = {"levels_db": ex_L.tolist(), "lengths_sec": ex_w.tolist(),
                                 "db_average": r(ea), "power_average": r(eb), "length_weighted": r(ec),
                                 "db_average_without_quiet": r(ea11), "power_average_without_quiet": r(eb11),
                                 "drop_db_average": r(ea11 - ea), "drop_power_average": r(eb11 - eb),
                                 "length_weighted_without_quiet": r(ec11), "drop_length_weighted": r(ec11 - ec)}

    # ---- 1曲の中の1秒ごとの大きさ（静かな前奏と、強弱のある部分） ----
    secs = []
    for k in range(200):
        n_sec = 240
        sec_L = np.empty(n_sec)
        # 前奏10〜30秒は−35dB前後、そのあとは8秒ごとの区間で−20〜−8dB、1秒ごとの振れ1.5dB
        intro = rng.integers(10, 31)
        sec_L[:intro] = -35 + 1.5 * rng.standard_normal(intro)
        blocks = rng.uniform(-20, -8, n_sec // 8 + 1)
        body = np.repeat(blocks, 8)[: n_sec - intro] + 1.5 * rng.standard_normal(n_sec - intro)
        sec_L[intro:] = body
        aa = sec_L.mean()
        bb = to_db(to_pow(sec_L).mean())
        aa2 = sec_L[intro:].mean()
        bb2 = to_db(to_pow(sec_L[intro:]).mean())
        secs.append({"song": k, "intro_sec": int(intro), "db_average": r(aa), "power_average": r(bb), "gap": r(bb - aa),
                     "gap_without_intro": r(bb2 - aa2)})
    dfs = pd.DataFrame(secs)
    dfs.to_csv(RES / "within_song.csv", index=False)
    out["within_song"] = {"songs": 200, "gap_mean": r(dfs.gap.mean()), "gap_p05": r(q(dfs.gap, .05)), "gap_p95": r(q(dfs.gap, .95)),
                          "gap_without_intro_mean": r(dfs.gap_without_intro.mean())}

    # ---- アルバムどうしの比べ：どちらが大きいかが入れかわるか ----
    sig_each = rng.uniform(1, 6, N_ALB)
    L2 = MU + sig_each[:, None] * rng.standard_normal((N_ALB, N_SONG))
    w2 = rng.uniform(LEN_MIN, LEN_MAX, (N_ALB, N_SONG))
    a2, b2, c2 = three(L2, w2)
    i1 = rng.integers(0, N_ALB, 20000)
    i2 = rng.integers(0, N_ALB, 20000)
    keep = i1 != i2
    i1, i2 = i1[keep], i2[keep]
    flip = np.sign(a2[i1] - a2[i2]) != np.sign(c2[i1] - c2[i2])
    flip_eq = np.sign(a2[i1] - a2[i2]) != np.sign(b2[i1] - b2[i2])
    close = np.abs(a2[i1] - a2[i2]) < 1.0
    gap_rank = c2 - a2
    out["pairs"] = {"album_sigma_range_db": [1, 6], "pairs": int(keep.sum()), "share_order_flipped": r(flip.mean(), 4),
                    "share_order_flipped_vs_equal_weight_power": r(flip_eq.mean(), 4),
                    "share_flipped_vs_equal_weight_when_within_1db": r(flip_eq[np.abs(a2[i1] - a2[i2]) < 1.0].mean(), 4),
                    "share_flipped_when_db_average_within_1db": r(flip[close].mean(), 4),
                    "pairs_within_1db": int(close.sum()),
                    "gap_mean": r(gap_rank.mean()), "gap_min": r(gap_rank.min()), "gap_max": r(gap_rank.max())}

    # ---- 確かめ：ばらつき×曲数×形 ----
    grid = []
    for shape in SHAPES:
        for s in SIGMAS:
            for n in NS:
                Lg, wg = draw(rng, 1000, n, s, shape)
                ag, bg, cg = three(Lg, wg)
                g = bg - ag
                grid.append({"shape": shape, "sigma_db": s, "songs": n, "gap_mean": r(g.mean()), "gap_p05": r(q(g, .05)),
                             "gap_p95": r(q(g, .95)), "length_weighted_gap_mean": r((cg - ag).mean()),
                             "formula_normal": r(s ** 2 * np.log(10) / 20 * (n - 1) / n) if shape == SHAPES[0] else None})
    dg = pd.DataFrame(grid)
    dg.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"cases": len(grid), "gap_mean_min": r(dg.gap_mean.min()), "gap_mean_max": r(dg.gap_mean.max()),
                   "all_positive": bool((dg.gap_p05 > 0).all())}
    for shape in SHAPES:
        s = dg[dg["shape"] == shape]
        out["grid"][shape] = {"gap_mean_min": r(s.gap_mean.min()), "gap_mean_max": r(s.gap_mean.max())}
    nor = dg[dg["shape"] == SHAPES[0]]
    out["grid"]["max_abs_diff_to_formula_normal"] = r((nor.gap_mean - nor.formula_normal).abs().max())
    small = nor[nor.sigma_db <= 3]
    out["grid"]["max_abs_diff_to_formula_sigma_le3"] = r((small.gap_mean - small.formula_normal).abs().max())

    summ = pd.DataFrame([
        {"case": "基本（12曲・ばらつき3dB）2,000枚の平均", "db_average": r(a.mean()), "power_average": r(b.mean()),
         "length_weighted": r(c.mean()), "gap_power_minus_db": r(gap_ab.mean())},
        {"case": "例：静かな曲が1曲ある", "db_average": r(ea), "power_average": r(eb), "length_weighted": r(ec), "gap_power_minus_db": r(eb - ea)},
        {"case": "1曲の中の1秒ごと（200曲の平均）", "db_average": r(dfs.db_average.mean()), "power_average": r(dfs.power_average.mean()),
         "length_weighted": None, "gap_power_minus_db": r(dfs.gap.mean())},
    ])
    summ.to_csv(RES / "summary.csv", index=False)
    with open(RES / "a1138_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)

    # ---- 図 ----
    # 図1：ばらつきとずれ（左右対称、12曲）と式
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for shape, col, mk in [(SHAPES[0], BLUE, "o"), (SHAPES[1], ORANGE, "s")]:
        s = dg[(dg["shape"] == shape) & (dg.songs == 12)]
        ax.errorbar(s.sigma_db, s.gap_mean, yerr=[s.gap_mean - s.gap_p05, s.gap_p95 - s.gap_mean], fmt=mk + "-", color=col,
                    capsize=3, label=f"{shape}（12曲、1,000枚の平均と5〜95%）")
        for x, y in zip(s.sigma_db, s.gap_mean):
            if shape == SHAPES[0]:
                ax.text(x + 0.25, y - 0.15, f"{y:.3f}", color=col, fontsize=8.5, va="top", ha="left")
            else:
                ax.text(x - 0.25, y + 0.15, f"{y:.3f}", color=col, fontsize=8.5, va="bottom", ha="right")
    xs = np.linspace(0, 10.5, 100)
    ax.plot(xs, xs ** 2 * np.log(10) / 20 * 11 / 12, color=GRAY, ls="--", lw=1, label="式（ばらつき²×0.115×11/12）")
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, None)
    ax.set_xlabel("曲ごとの大きさのばらつき（標準偏差、dB）")
    ax.set_ylabel("強さで平均 − dBのまま平均（dB）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("dBのまま平均すると、強さで平均した値より低く出る\n（ずれは曲どうしのばらつきの2乗でふくらむ）")
    save(fig, "a1138_gap_sigma.png", SRC)

    # 図2：例のアルバム（静かな曲が1曲）で、11曲から下がった分
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    labs = ["dBのまま平均", "強さで平均", "長さで重みを付けて\n強さで平均（つなげて測った値）"]
    drops = [ea11 - ea, eb11 - eb, ec11 - ec]
    xs = np.arange(3)
    ax.bar(xs, drops, width=0.55, color=[ORANGE, BLUE, BLUE])
    for x, v, v11, v12 in zip(xs, drops, [ea11, eb11, ec11], [ea, eb, ec]):
        ax.text(x, v + 0.03, f"{v:.3f}dB下がった\n（{v11:.3f} → {v12:.3f}）", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylabel("静かな曲を足して下がった分（dB）")
    ax.set_ylim(0, 1.8)
    ax.set_title("−30dBの静かな曲（60秒）を11曲に足すと\ndBのまま平均だけが大きく下がる")
    save(fig, "a1138_example.png", SRC)

    # 図3：アルバムごとの dB平均 と 強さ（長さ重み）平均
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    sc = ax.scatter(a2, c2, c=sig_each, cmap="Blues", s=6, vmin=0, vmax=6)
    lo, hi = min(a2.min(), c2.min()) - 0.5, max(a2.max(), c2.max()) + 0.5
    ax.plot([lo, hi], [lo, hi], color=GRAY, lw=1, ls="--")
    ax.text(hi - 0.3, hi - 3.5, "同じ値の線", color=GRAY, ha="right", va="top", fontsize=9)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("アルバムの中の曲のばらつき（dB）")
    ax.set_xlabel("dBのまま平均（dB）")
    ax.set_ylabel("長さで重みを付けて強さで平均（dB）")
    ax.set_title(f"どちらのアルバムが大きいかは、ペアの{flip.mean()*100:.2f}%で入れかわった\n（ばらつきの大きいアルバムほど線の上に離れる）")
    save(fig, "a1138_albums.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(dg.to_string())


if __name__ == "__main__":
    main()
