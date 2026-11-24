"""1125 画素の数を縦横2倍にすると、細かさは何倍になったと言えるのか？（架空のデータ）

作成者が式で作った架空の縞の画像（白黒の明るさが波の形で変わる縞）を、
レンズのぼけ（ぼけの幅を置く）→ 画素ごとに光を集める → ざらつき（乱数）の順で写し、
見分けられる最も細かい縞を、画素の数ごとに数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1125
SRC = "架空の縞の画像（作成者が式と乱数で作成、seed 1125）"
rng = np.random.default_rng(SEED)
N0 = 1000            # 基本の画素の数（横）。縦も同じ
SUB = 16             # 1画素を細かく分ける数（いちばん画素の多い4,000画素のとき）
TH = 0.10            # 縞が見分けられるとみなすくっきり度（10%）
NOISE0 = 0.01        # 1,000画素のときの1画素のざらつき（標準偏差、明るさ0〜1）
BAND = 0.01          # くっきり度を測る帯の高さ（画像の高さの1%）


def sinc(x):
    return np.sinc(x)  # sin(pi x)/(pi x)


def mod_formula(f, n, sigma):
    """くっきり度の式：ぼけ（幅 sigma、画像の幅=1）×画素で光を集める分。f は画像の幅あたりの縞の数"""
    return np.exp(-2 * np.pi ** 2 * sigma ** 2 * f ** 2) * np.abs(sinc(f / n))


def limit_formula(n, sigma, th=TH, fmax=None):
    """見分けられる最も細かい縞（式）：くっきり度が th 以上で、画素の数の半分（それより細かい縞は粗い縞に化ける）まで"""
    fs = np.arange(1, n // 2 + 1)
    m = mod_formula(fs, n, sigma)
    ok = fs[m >= th]
    lim = float(ok.max()) if len(ok) else 0.0
    return lim


def f_at(n, sigma, level):
    """くっきり度が level に下がる縞の細かさ（画素の数の半分では止めない）"""
    fs = np.arange(1, 4 * n)
    m = mod_formula(fs, n, sigma)
    i = np.argmax(m < level)
    return float(fs[i - 1]) if i > 0 else float(fs[-1])


def capture(f, n, sigma, noise, rows, rng, phase):
    """縞（明るさ 0.5+0.5cos）を写す。細かい格子でぼかし、画素ごとに平均し、ざらつきを足す"""
    sub = SUB * 4000 // n
    m = n * sub
    x = (np.arange(m) + 0.5) / m
    scene = 0.5 + 0.5 * np.cos(2 * np.pi * f * x + phase)
    if sigma > 0:
        k = np.fft.rfftfreq(m, d=1 / m)
        scene = np.fft.irfft(np.fft.rfft(scene) * np.exp(-2 * np.pi ** 2 * sigma ** 2 * k ** 2), m)
    pix = scene.reshape(n, sub).mean(1)
    img = pix[None, :] + rng.normal(0, noise, (rows, n))
    return img


def measure_mod(img, f):
    n = img.shape[1]
    xc = (np.arange(n) + 0.5) / n
    c, s = np.cos(2 * np.pi * f * xc), np.sin(2 * np.pi * f * xc)
    y = img.mean(0) - img.mean()
    a = 2 * (y @ c) / n
    b = 2 * (y @ s) / n
    return float(np.hypot(a, b) / 0.5)


def main():
    out = {}
    sig_base = 0.5 / N0   # 基本のぼけ：1,000画素の0.5画素分
    ns = [1000, 2000, 4000]

    # 1) 基本：ぼけなし・ぼけ0.5画素分（1,000画素のとき）
    rows = []
    for sb_px in [0.0, 0.5, 1.0]:
        sg = sb_px / N0
        for n in ns:
            rows.append({"blur_base_px": sb_px, "pixels_wide": n, "pixels_total": n * n,
                         "limit_cycles": limit_formula(n, sg), "f_mod50": f_at(n, sg, 0.5),
                         "mod_at_250": round(float(mod_formula(250, n, sg)), 4),
                         "mod_at_450": round(float(mod_formula(450, n, sg)), 4)})
    base = pd.DataFrame(rows)
    for col in ["limit_cycles", "f_mod50"]:
        base[col + "_ratio_vs_1000"] = base.groupby("blur_base_px")[col].transform(lambda s: s / s.iloc[0]).round(4)
    base["pixels_total_ratio"] = (base.pixels_total / N0 ** 2).round(4)
    base.to_csv(RES / "by_pixels.csv", index=False)

    # 2) 写して確かめる（乱数のざらつき入り、式と比べる）
    sim = []
    fgrid = np.arange(25, 2001, 25)
    for n in [1000, 2000]:
        noise = NOISE0 * n / N0      # 同じ大きさの面を細かく分けると1画素の光は1/4、ざらつき（割合）は2倍と置く
        r = int(round(BAND * n))
        for f in fgrid:
            if f >= n / 2:
                continue
            img = capture(f, n, sig_base, noise, r, rng, rng.uniform(0, 2 * np.pi))
            sim.append({"pixels_wide": n, "f": int(f), "mod_sim": round(measure_mod(img, f), 4),
                        "mod_formula": round(float(mod_formula(f, n, sig_base)), 4)})
    sim = pd.DataFrame(sim)
    sim["diff"] = (sim.mod_sim - sim.mod_formula).round(4)
    sim.to_csv(RES / "sim_vs_formula.csv", index=False)
    sim_lim = {}
    for n, g in sim.groupby("pixels_wide"):
        sim_lim[str(n)] = float(g.loc[g.mod_sim >= TH, "f"].max())
    out["sim_check"] = {"max_abs_diff": round(float(sim["diff"].abs().max()), 4),
                        "limit_sim_step25": sim_lim,
                        "note": "縞の細かさは25組きざみ。画素の数の半分より細かい縞は測らない"}

    # 3) 1画素のざらつきと、1,000画素に縮めて見たときのざらつき（平らな灰色を写す）
    flat = {}
    for n in [1000, 2000, 4000]:
        noise = NOISE0 * n / N0
        img = 0.5 + rng.normal(0, noise, (400, n))
        k = n // N0
        small = img[: 400 // k * k].reshape(400 // k, k, N0, k).mean((1, 3))
        flat[str(n)] = {"pixel_sd": round(float(img.std()), 5), "shown_1000_sd": round(float(small.std()), 5)}
    out["noise_flat_gray"] = flat

    # 4) 1,000画素の画面で見る（2×2などをまとめて1画素にする）
    disp = []
    for sb_px in [0.0, 0.5, 1.0]:
        sg = sb_px / N0
        for n in ns:
            fs = np.arange(1, N0 // 2 + 1)
            m = mod_formula(fs, n, sg) * np.abs(sinc(fs / N0)) if n > N0 else mod_formula(fs, n, sg)
            lim = float(fs[m >= TH].max())
            m250 = float((mod_formula(250, n, sg) * (abs(sinc(250 / N0)) if n > N0 else 1)))
            disp.append({"blur_base_px": sb_px, "pixels_wide": n, "limit_shown_1000": lim,
                         "mod_at_250_shown_1000": round(m250, 4)})
    disp = pd.DataFrame(disp)
    disp["limit_ratio_vs_1000"] = disp.groupby("blur_base_px").limit_shown_1000.transform(lambda s: s / s.iloc[0]).round(4)
    disp["mod250_ratio_vs_1000"] = disp.groupby("blur_base_px").mod_at_250_shown_1000.transform(lambda s: s / s.iloc[0]).round(4)
    disp.to_csv(RES / "shown_1000.csv", index=False)

    # 5) 確かめ：ぼけの幅×見分けられるとみなすくっきり度×縦横の倍率
    grid = []
    for sb_px in [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        for th in [0.05, 0.10, 0.20]:
            for mult in [2, 3, 4]:
                sg = sb_px / N0
                l0 = limit_formula(N0, sg, th)
                l1 = limit_formula(N0 * mult, sg, th)
                grid.append({"blur_base_px": sb_px, "threshold": th, "side_mult": mult, "pixels_mult": mult ** 2,
                             "limit_1000": l0, "limit_mult": l1, "limit_ratio": round(l1 / l0, 4),
                             "f_mod50_ratio": round(f_at(N0 * mult, sg, 0.5) / f_at(N0, sg, 0.5), 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g2 = grid[grid.side_mult == 2]
    out["grid_side2"] = {"limit_ratio_min": float(g2.limit_ratio.min()), "limit_ratio_max": float(g2.limit_ratio.max()), "n_ratio_lt_1_1": int((g2.limit_ratio < 1.1).sum()),
                         "n_cases": int(len(g2)), "n_ratio_2": int((g2.limit_ratio >= 1.9999).sum()),
                         "n_ratio_lt_1_5": int((g2.limit_ratio < 1.5).sum()),
                         "by_blur_th10": g2[g2.threshold == 0.10].set_index("blur_base_px").limit_ratio.to_dict()}
    out["grid_all"] = {"ratio_min_by_mult": grid.groupby("side_mult").limit_ratio.min().to_dict(),
                       "ratio_max_by_mult": grid.groupby("side_mult").limit_ratio.max().to_dict()}
    out["by_pixels"] = base.to_dict("records")
    out["shown_1000"] = disp.to_dict("records")
    out["settings"] = {"N0": N0, "threshold": TH, "noise0": NOISE0, "band": BAND, "blur_base_px": 0.5}
    json.dump(out, open(RES / "a1125_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # data：例の縞（250本・450本）を1,000画素と2,000画素で写した1行分
    ex = []
    for n in [1000, 2000]:
        for f in [250, 450]:
            img = capture(f, n, sig_base, 0.0, 1, np.random.default_rng(SEED + n + f), 0.0)[0]
            for i, v in enumerate(img):
                ex.append({"pixels_wide": n, "f": f, "pixel": i, "value": round(float(v), 5)})
    ex = pd.DataFrame(ex)
    ex.to_csv(DATA / "example_rows.csv", index=False)

    # 図1：例の縞（画像の幅の左から3%分）
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 3.6), sharey=True)
    for i, n in enumerate([1000, 2000]):
        for j, f in enumerate([250, 450]):
            ax = axes[i, j]
            e = ex[(ex.pixels_wide == n) & (ex.f == f)]
            k = int(0.03 * n)
            ax.imshow(np.tile(e.value.values[:k], (6, 1)), cmap="gray", vmin=0, vmax=1, aspect="auto",
                      interpolation="nearest")
            ax.set_xticks([]); ax.set_yticks([])
            mm = mod_formula(f, n, sig_base)
            ax.set_title(f"横{n:,}画素・縞{f}組（くっきり度{mm*100:.2f}%）", fontsize=10)
    fig.suptitle("同じ縞を1,000画素と2,000画素で写す（画像の幅の3%分、ぼけ0.5画素分）", fontsize=12, y=1.04)
    save(fig, "a1125_example.png", SRC)

    # 図2：縞の細かさとくっきり度
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    fs = np.arange(1, 2001)
    for n, c in zip(ns, [GRAY, BLUE, ORANGE]):
        f = fs[fs <= n / 2]
        ax.plot(f, mod_formula(f, n, sig_base) * 100, color=c, lw=1.8, label=f"横{n:,}画素（{n*n//10000:,}万画素）")
        ax.plot([n / 2, n / 2], [0, mod_formula(n / 2, n, sig_base) * 100], color=c, lw=0.8, ls=":")
    sm = sim[sim.pixels_wide == 2000]
    ax.scatter(sm.f, sm.mod_sim * 100, s=9, color=INK, zorder=3, label="写して測った値（横2,000画素）")
    ax.axhline(TH * 100, color=GREEN, lw=1, ls="--"); ax.text(1990, TH * 100 + 2, "見分けられるとみなす10%", ha="right", color=GREEN, fontsize=9)
    ax.set_xlim(0, 2050); ax.set_ylim(0, 105)
    ax.set_xlabel("縞の細かさ（画像の幅あたりの白黒の組の数）"); ax.set_ylabel("写った縞のくっきり度（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1, 0.92))
    ax.set_title("縦横2倍でも、見分けられる縞は500組から655組までしか延びない（ぼけ0.5画素分）", fontsize=12)
    save(fig, "a1125_contrast.png", SRC)

    # 図3：ぼけの幅と、縦横2倍で見分けられる縞の伸び
    g = grid[(grid.side_mult == 2)]
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    blurs = sorted(g.blur_base_px.unique())
    w = 0.26
    for k, (th, c) in enumerate(zip([0.05, 0.10, 0.20], [LIGHT, BLUE, INK])):
        v = g[g.threshold == th].set_index("blur_base_px").limit_ratio.reindex(blurs).values
        ax.bar(np.arange(len(blurs)) + (k - 1) * w, v, w, color=c, label=f"見分けの目安{int(th*100)}%")
    ax.axhline(4, color=ORANGE, lw=1, ls="--"); ax.text(len(blurs) - 0.5, 4.05, "画素の数の倍率（4倍）", ha="right", va="bottom", color=ORANGE, fontsize=9)
    ax.axhline(2, color=GRAY, lw=1, ls=":")
    ax.set_xticks(np.arange(len(blurs))); ax.set_xticklabels([f"{b:g}" for b in blurs])
    ax.set_xlabel("レンズのぼけの幅（横1,000画素の何画素分か）"); ax.set_ylabel("見分けられる最も細かい縞の倍率")
    ax.set_ylim(0, 4.5); ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1, 0.88))
    ax.set_title("縦横2倍（画素4倍）で見分けられる縞は、ぼけが大きいほど伸びない")
    save(fig, "a1125_blur.png", SRC)
    print(json.dumps({k: out[k] for k in ["sim_check", "noise_flat_gray", "grid_side2", "grid_all"]}, ensure_ascii=False, indent=1))
    print(base.to_string()); print(disp.to_string())


if __name__ == "__main__":
    main()
