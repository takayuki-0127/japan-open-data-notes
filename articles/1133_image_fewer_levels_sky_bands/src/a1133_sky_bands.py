"""1133 色の段階を減らして保存すると、なめらかな空の明るさにどれだけ段ができるのか？（架空のデータ）

作成者が式と乱数で作った架空の空の画像（明るさだけ、縦1,000×横200画素、上から下へなめらかに明るくなる）を、
明るさの段階の数（256・64・32・16段階）に丸めて保存し、段の数・段の幅・1段の高さ・本当の明るさとのずれを数える。
丸める前に細かいざらつき（1段の幅の一様な乱数）を足す保存のしかたとも比べる。
「離れて見たときのずれ」は、作成者が置いた見え方（縦横15画素の正方形の中をならして見る）でならした明るさと、本当の明るさの差の最大で数える。
明るさは0〜1で表し、段階の数が L なら 0, 1/(L−1), 2/(L−1), … 1 のどれかに丸める。結果のずれは255倍して0〜255の目盛り（256段階の1段＝1）で書く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1133
SRC = "架空の空の画像（作成者が式と乱数で作成、seed 1133）"
H, W = 1000, 200
N_SKY = 100
LEVELS = [256, 64, 32, 16]
BLUR = 15
GRID_NOISE = [0.0, 0.002, 0.008]       # もとの空のざらつき（写真のざらつきに見立てた、標準偏差）
GRID_BLUR = [5, 15, 45]
GRID_SKY = 30                          # 確かめは各30枚
SPAN_RULE = "上端0.45〜0.65、明るさの幅0.2〜0.4、曲がり方0.8〜1.5の一様な乱数"


def r(x, d=4):
    return round(float(x), d)


def make_sky(rng, noise=0.0):
    top = rng.uniform(0.45, 0.65)
    span = rng.uniform(0.2, 0.4)
    p = rng.uniform(0.8, 1.5)
    y = (np.arange(H) + 0.5) / H
    prof = top + span * y ** p
    img = np.repeat(prof[:, None], W, axis=1)
    if noise > 0:
        img = img + rng.normal(0, noise, img.shape)
    return img, prof, span


def quantize(img, L, rng=None):
    q = L - 1
    v = img * q
    if rng is not None:
        v = v + rng.uniform(-0.5, 0.5, img.shape)
    return np.clip(np.round(v), 0, q) / q


def box(img, k):
    """縦横 k 画素の正方形でならす（端は内側だけを使う）"""
    c = np.cumsum(np.cumsum(np.pad(img, ((1, 0), (1, 0))), 0), 1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def measure(q, prof, k):
    true_img = np.repeat(prof[:, None], W, axis=1)
    mid = q[:, W // 2]
    levels = np.unique(mid)
    # 中央の列で、値が変わる所の数＋1（ざらつきがあると細かく入れかわるので、別に数える）
    changes = int(np.sum(mid[1:] != mid[:-1]))
    rmse = float(np.sqrt(np.mean((q - true_img) ** 2)))
    bq = box(q, k)
    bt = box(true_img, k)
    blur_dev = float(np.max(np.abs(bq - bt)))
    blur_rmse = float(np.sqrt(np.mean((bq - bt) ** 2)))
    return {"n_levels_used": len(levels), "changes_mid_column": changes, "rmse": rmse,
            "blur_max_dev": blur_dev, "blur_rmse": blur_rmse}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    example = None
    for i in range(N_SKY):
        img, prof, span = make_sky(rng)
        for L in LEVELS:
            for dith in [False, True]:
                q = quantize(img, L, rng if dith else None)
                m = measure(q, prof, BLUR)
                step = 1 / (L - 1)
                rows.append({"sky": i + 1, "span": round(span, 4), "levels": L, "dither": int(dith), "step": step,
                             "band_width_px": H / m["n_levels_used"] if not dith else np.nan, **m})
        if i == 0:
            example = (img, prof)
    df = pd.DataFrame(rows)
    out = df.copy()
    for c in ["step", "band_width_px", "rmse", "blur_max_dev", "blur_rmse"]:
        out[c] = out[c].round(6)
    out.to_csv(DATA / "skies_measured.csv", index=False)

    # 主な表（100枚の平均）
    tab = []
    for L in LEVELS:
        a = df[(df.levels == L) & (df.dither == 0)]
        b = df[(df.levels == L) & (df.dither == 1)]
        step = 1 / (L - 1)
        tab.append({"levels": L, "step_255": r(255 * step, 3), "n_bands_mean": r(a.n_levels_used.mean(), 1),
                    "n_bands_formula_mean": r((a.span * (L - 1)).mean() + 1, 1),
                    "band_width_px_mean": r(a.band_width_px.mean(), 1),
                    "band_width_px_min": r(a.band_width_px.min(), 1), "band_width_px_max": r(a.band_width_px.max(), 1),
                    "rmse_plain_255": r(255 * a.rmse.mean(), 3), "rmse_formula_255": r(255 * step / np.sqrt(12), 3),
                    "rmse_dither_255": r(255 * b.rmse.mean(), 3), "rmse_dither_formula_255": r(255 * step / np.sqrt(6), 3),
                    "blur_max_dev_plain_255": r(255 * a.blur_max_dev.mean(), 3), "blur_max_dev_dither_255": r(255 * b.blur_max_dev.mean(), 3),
                    "blur_max_dev_ratio": r(b.blur_max_dev.mean() / a.blur_max_dev.mean(), 3),
                    "blur_max_dev_plain_in_steps": r(a.blur_max_dev.mean() / step, 3),
                    "blur_max_dev_dither_in_steps": r(b.blur_max_dev.mean() / step, 3),
                    "changes_mid_plain": r(a.changes_mid_column.mean(), 1), "changes_mid_dither": r(b.changes_mid_column.mean(), 1)})
    tb = pd.DataFrame(tab)
    tb.to_csv(RES / "levels_base.csv", index=False)

    # 確かめ：もとの空のざらつき×ならす幅×段階の数（各30枚）
    grng = np.random.default_rng(SEED + 1)
    grid = []
    for noise in GRID_NOISE:
        skies = [make_sky(grng, noise) for _ in range(GRID_SKY)]
        for L in LEVELS:
            qs_plain = [quantize(s[0], L) for s in skies]
            qs_dith = [quantize(s[0], L, grng) for s in skies]
            for k in GRID_BLUR:
                a = [measure(q, s[1], k)["blur_max_dev"] for q, s in zip(qs_plain, skies)]
                b = [measure(q, s[1], k)["blur_max_dev"] for q, s in zip(qs_dith, skies)]
                # 丸めない（ざらつきだけ）の対照
                c = [float(np.max(np.abs(box(s[0], k) - box(np.repeat(s[1][:, None], W, 1), k)))) for s in skies] if L == LEVELS[0] else None
                rec = {"noise_sd": noise, "noise_sd_255": r(255 * noise, 2), "levels": L, "blur_px": k,
                       "blur_max_dev_plain_255": r(255 * np.mean(a), 3), "blur_max_dev_dither_255": r(255 * np.mean(b), 3),
                       "ratio_dither_to_plain": r(np.mean(b) / np.mean(a), 3),
                       "plain_in_steps": r(np.mean(a) * (L - 1), 3), "dither_in_steps": r(np.mean(b) * (L - 1), 3)}
                if c is not None:
                    rec["no_rounding_blur_max_dev_255"] = r(255 * np.mean(c), 3)
                grid.append(rec)
    gdf = pd.DataFrame(grid)
    gdf.to_csv(RES / "grid.csv", index=False)

    # 範囲
    def rng_of(sub, col):
        return [r(sub[col].min(), 3), r(sub[col].max(), 3)]
    g_ratio = {f"{L}": rng_of(gdf[gdf.levels == L], "ratio_dither_to_plain") for L in LEVELS}
    g_plain_steps = {f"noise{n}": rng_of(gdf[gdf.noise_sd == n], "plain_in_steps") for n in GRID_NOISE}
    g_dither_steps = {f"noise{n}": rng_of(gdf[gdf.noise_sd == n], "dither_in_steps") for n in GRID_NOISE}
    noisy_8bit = gdf[(gdf.levels == 256)][["noise_sd", "blur_px", "blur_max_dev_plain_255", "blur_max_dev_dither_255", "ratio_dither_to_plain", "no_rounding_blur_max_dev_255"]]

    main_json = {
        "settings": {"height": H, "width": W, "skies": N_SKY, "sky_rule": SPAN_RULE, "levels": LEVELS, "blur_px": BLUR,
                     "dither": "丸める前に、1段の幅の一様な乱数（−0.5段〜+0.5段）を画素ごとに足す",
                     "grid_noise_sd": GRID_NOISE, "grid_blur_px": GRID_BLUR, "grid_skies": GRID_SKY},
        "levels_base": tab,
        "grid_ratio_dither_to_plain_by_levels": g_ratio,
        "grid_ratio_dither_to_plain_by_blur": {f"{k}px": rng_of(gdf[gdf.blur_px == k], "ratio_dither_to_plain") for k in GRID_BLUR},
        "grid_ratio_dither_to_plain_by_noise": {f"noise{n}": rng_of(gdf[gdf.noise_sd == n], "ratio_dither_to_plain") for n in GRID_NOISE},
        "grid_plain_in_steps_by_noise": g_plain_steps,
        "grid_dither_in_steps_by_noise": g_dither_steps,
        "grid_256_levels": noisy_8bit.to_dict("records"),
        "grid_ratio_all_below_1": bool((gdf.ratio_dither_to_plain < 1).all()),
        "grid_ratio_max": r(gdf.ratio_dither_to_plain.max(), 3),
    }
    with open(RES / "a1133_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # ---- 図1：空の例（段階の数×ざらつきの有無） ----
    img, prof = example
    erng = np.random.default_rng(SEED + 2)
    fig, axs = plt.subplots(2, 4, figsize=(9.6, 6.2))
    for j, L in enumerate(LEVELS):
        for i, dith in enumerate([False, True]):
            q = quantize(img, L, erng if dith else None)
            ax = axs[i, j]
            ax.imshow(q[:, :120], cmap="gray", vmin=0.35, vmax=1.0, aspect="auto", interpolation="nearest")
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(False)
            ax.set_title(f"{L}段階" + ("\n丸める前にざらつきを足す" if dith else "\nそのまま丸める"), fontsize=9)
    fig.suptitle("同じ空（1枚目、縦1,000画素）を段階の数を変えて保存（明るさを強めて表示）", fontsize=11)
    save(fig, "a1133_example.png", "出典：" + SRC)

    # ---- 図2：ならして見た明るさの縦の変化（64段階） ----
    L = 64
    q0 = quantize(img, L)
    q1 = quantize(img, L, np.random.default_rng(SEED + 3))
    k = BLUR
    yy = np.arange(k // 2, H - k // 2)
    bt = box(np.repeat(prof[:, None], W, 1), k)[:, W // 2 - k // 2]
    b0 = box(q0, k)[:, W // 2 - k // 2]
    b1 = box(q1, k)[:, W // 2 - k // 2]
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    sl = (yy >= 300) & (yy <= 460)
    ax.plot(yy[sl], (b0 - bt)[sl] * (L - 1), color=BLUE, lw=1.8, label="そのまま丸める")
    ax.plot(yy[sl], (b1 - bt)[sl] * (L - 1), color=ORANGE, lw=1.4, label="丸める前にざらつきを足す")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xlabel("上からの位置（画素、300〜460画素目を拡大）")
    ax.set_ylabel("ならした明るさ − 本当の明るさ（段）")
    ax.set_title(f"{L}段階・{k}画素でならして見たときのずれ（1枚目の空）")
    ax.set_ylim(-0.45, 0.6)
    ax.legend(fontsize=9, frameon=False, loc="upper center", ncol=2)
    save(fig, "a1133_profile.png", "出典：" + SRC)

    # ---- 図3：段階の数ごとの、ならして見たずれの最大（そのまま／ざらつき） ----
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xs = np.arange(len(LEVELS)); w = 0.36
    v0 = [t["blur_max_dev_plain_255"] for t in tab]
    v1 = [t["blur_max_dev_dither_255"] for t in tab]
    ax.bar(xs - w / 2, v0, w, color=BLUE, label="そのまま丸める")
    ax.bar(xs + w / 2, v1, w, color=ORANGE, label="丸める前にざらつきを足す")
    for x, y in zip(xs - w / 2, v0):
        ax.text(x, y + 0.1, f"{y:.3f}", ha="center", va="bottom", fontsize=8)
    for x, y in zip(xs + w / 2, v1):
        ax.text(x, y + 0.1, f"{y:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels([f"{L}段階" for L in LEVELS])
    ax.set_ylim(0, None)
    ax.set_ylabel("ならして見たずれの最大（0〜255の目盛り）")
    ax.set_title(f"{BLUR}画素でならして見たときの、本当の明るさとのずれ（100枚の平均）", fontsize=11.5)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    save(fig, "a1133_blur_dev.png", "出典：" + SRC)

    print(tb.to_string())
    print(json.dumps({k2: main_json[k2] for k2 in ["grid_ratio_dither_to_plain_by_levels", "grid_plain_in_steps_by_noise", "grid_dither_in_steps_by_noise", "grid_ratio_all_below_1", "grid_ratio_max"]}, ensure_ascii=False))
    print(noisy_8bit.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
