"""1127 画素を間引いて縮小すると、細い縞はどんな模様に化けるのか？（架空のデータ）

作成者が式で描いた架空の縞の画像（布の縞に見立てたもの。横2,000画素、明るさ 0.5+0.5cos の縞）を、
①間引く（k画素ごとに1画素を取る）、②k×k画素ずつ平均する、③ぼかしてから間引く、の3つで 1/k に縮め、
縮めた画像に出る縞の細かさとくっきり度を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1127
SRC = "架空の縞の画像（作成者が式と乱数で作成、seed 1127）"
rng = np.random.default_rng(SEED)
N = 2000          # 元の横の画素の数
K = 4             # 1/4 に縮める
TH = 0.10         # 縞が見えるとみなすくっきり度
METHODS = ["間引く", "まとめて平均", "ぼかしてから間引く"]


def gauss_blur(row, sigma):
    m = len(row)
    k = np.fft.rfftfreq(m, d=1.0)
    return np.fft.irfft(np.fft.rfft(row) * np.exp(-2 * np.pi ** 2 * sigma ** 2 * k ** 2), m)


def shrink(row, method, k, offset, sigma_mult=0.5):
    if method == "間引く":
        return row[offset::k]
    if method == "まとめて平均":
        r = np.roll(row, -offset)
        return r.reshape(-1, k).mean(1)
    return gauss_blur(row, sigma_mult * k)[offset::k]


def peak(small):
    """縮めた画像の縞：いちばん強い細かさ（画像の幅あたりの組の数）と、くっきり度（元の縞の振れ0.5を100%）"""
    n = len(small)
    sp = np.abs(np.fft.rfft(small - small.mean())) * 2 / n
    i = int(np.argmax(sp[1:]) + 1)
    amp = sp[i] if i < n / 2 else sp[i] / 2
    return i, float(amp / 0.5)


def alias_formula(f, n_small):
    r = f % n_small
    return int(min(r, n_small - r))


def one(f, method, k, rng, sigma_mult=0.5, n=N):
    x = np.arange(n)
    row = 0.5 + 0.5 * np.cos(2 * np.pi * f * x / n + rng.uniform(0, 2 * np.pi))
    small = shrink(row, method, k, int(rng.integers(0, k)), sigma_mult)
    return small


def main():
    out = {}
    ns = N // K   # 縮めた横の画素の数 500、見分けられる縞は250組まで
    # 1) 縞の細かさごと（10〜1,000組、各20回）
    rows = []
    for f in range(10, N // 2 + 1, 10):
        for m in METHODS:
            res = [peak(one(f, m, K, rng)) for _ in range(20)]
            fa = [r[0] for r in res]; am = [r[1] for r in res]
            rows.append({"f": f, "method": m, "f_seen": int(np.median(fa)), "f_alias_formula": alias_formula(f, ns),
                         "contrast": round(float(np.mean(am)), 4), "contrast_min": round(float(np.min(am)), 4),
                         "contrast_max": round(float(np.max(am)), 4)})
    byf = pd.DataFrame(rows)
    byf.to_csv(RES / "by_stripe.csv", index=False)
    above = byf[byf.f > ns / 2]
    below = byf[byf.f < ns / 2]
    summ = []
    for m in METHODS:
        a, b = above[above.method == m], below[below.method == m]
        summ.append({"method": m,
                     "false_ge10_share": round(float((a.contrast >= TH).mean()), 4),
                     "false_contrast_mean": round(float(a.contrast.mean()), 4),
                     "false_contrast_max": round(float(a.contrast.max()), 4),
                     "keep_f100": float(b[b.f == 100].contrast.iloc[0]),
                     "keep_f200": float(b[b.f == 200].contrast.iloc[0]),
                     "keep_f240": float(b[b.f == 240].contrast.iloc[0]),
                     "seen_matches_formula_share": round(float((a.f_seen == a.f_alias_formula).mean()), 4)})
    summ = pd.DataFrame(summ)
    summ.to_csv(RES / "by_method.csv", index=False)

    # 2) 例：900組の縞 → ?、480組 → ?、500組（縮めた画素の数ちょうど）→ 無地
    ex = {}
    for f in [300, 480, 700, 900]:
        ex[str(f)] = {"alias_formula": alias_formula(f, ns),
                      "seen": {m: int(byf[(byf.f == f) & (byf.method == m)].f_seen.iloc[0]) for m in METHODS},
                      "contrast": {m: float(byf[(byf.f == f) & (byf.method == m)].contrast.iloc[0]) for m in METHODS}}
    # 500組：間引く位置とはじまりのずれで、無地の明るさが変わる
    flat = []
    for r in range(2000):
        ph = rng.uniform(0, 2 * np.pi); off = int(rng.integers(0, K))
        x = np.arange(N)
        row = 0.5 + 0.5 * np.cos(2 * np.pi * 500 * x / N + ph)
        s = row[off::K]
        flat.append({"rep": r, "mean": float(s.mean()), "sd": float(s.std()),
                     "box_mean": float(shrink(row, "まとめて平均", K, off).mean())})
    flat = pd.DataFrame(flat)
    ex["500"] = {"thin_mean_min": round(float(flat["mean"].min()), 4), "thin_mean_max": round(float(flat["mean"].max()), 4),
                 "thin_within_sd_max": round(float(flat.sd.max()), 6),
                 "thin_mean_outside_0.25_0.75_share": round(float(((flat["mean"] < 0.25) | (flat["mean"] > 0.75)).mean()), 4),
                 "box_mean_min": round(float(flat.box_mean.min()), 4), "box_mean_max": round(float(flat.box_mean.max()), 4)}
    out["examples"] = ex

    # 3) 斜めの縞（2次元）：向きが変わる
    H = W = 400; k2 = 4
    yy, xx = np.mgrid[0:H, 0:W]
    ang = np.deg2rad(30); fr = 170   # 画像の幅あたり170組、向き30度
    fx, fy = fr * np.cos(ang), fr * np.sin(ang)
    fx, fy = round(fx), round(fy)
    img = 0.5 + 0.5 * np.cos(2 * np.pi * (fx * xx + fy * yy) / W)
    sm = img[::k2, ::k2]
    sp = np.abs(np.fft.fft2(sm - sm.mean()))
    sp[0, 0] = 0
    iy, ix = np.unravel_index(np.argmax(sp), sp.shape)
    n2 = W // k2
    ax_ = ix if ix <= n2 / 2 else ix - n2; ay_ = iy if iy <= n2 / 2 else iy - n2
    if ax_ < 0 or (ax_ == 0 and ay_ < 0):
        ax_, ay_ = -ax_, -ay_
    out["slanted"] = {"orig_fx": fx, "orig_fy": fy, "orig_freq": round(float(np.hypot(fx, fy)), 2),
                      "orig_angle_deg": round(float(np.degrees(np.arctan2(fy, fx))), 1),
                      "seen_fx": int(ax_), "seen_fy": int(ay_), "seen_freq": round(float(np.hypot(ax_, ay_)), 2),
                      "seen_angle_deg": round(float(np.degrees(np.arctan2(ay_, ax_))), 1)}

    # 4) 確かめ：縮める割合×ぼかしの強さ
    grid = []
    for k in [2, 3, 4, 8]:
        nn = N if N % k == 0 else 1998
        n_small = nn // k
        for meth, sm_ in [("間引く", 0), ("まとめて平均", 0), ("ぼかしてから間引く", 0.25), ("ぼかしてから間引く", 0.5),
                          ("ぼかしてから間引く", 0.75)]:
            r2 = np.random.default_rng(SEED + k * 10 + int(sm_ * 100))
            fa, fb = [], []
            for f in range(10, nn // 2 + 1, 10):
                cs = [peak(one(f, meth, k, r2, sm_, nn))[1] for _ in range(5)]
                (fa if f > n_small / 2 else fb).append((f, float(np.mean(cs))))
            fa, fb = np.array(fa), np.array(fb)
            keep08 = fb[np.argmin(np.abs(fb[:, 0] - 0.8 * n_small / 2)), 1]
            grid.append({"k": k, "method": meth, "sigma_mult": sm_, "false_ge10_share": round(float((fa[:, 1] >= TH).mean()), 4),
                         "false_contrast_max": round(float(fa[:, 1].max()), 4), "keep_at_0.8_limit": round(float(keep08), 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid_range"] = {m: {"false_ge10_min": float(g.false_ge10_share.min()), "false_ge10_max": float(g.false_ge10_share.max()),
                             "keep08_min": float(g["keep_at_0.8_limit"].min()),
                             "keep08_max": float(g["keep_at_0.8_limit"].max())}
                         for m, g in grid.groupby(["method", "sigma_mult"], sort=False)
                         for m in [f"{m[0]}（{m[1]}）"]}
    out["by_method"] = summ.to_dict("records")
    out["settings"] = {"N": N, "K": K, "small_pixels": ns, "limit_cycles_small": ns // 2, "threshold": TH,
                       "blur_sigma_px": 0.5 * K}
    json.dump(out, open(RES / "a1127_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # data：例の縞（900組）の元の1行と縮めた1行
    r3 = np.random.default_rng(SEED + 900)
    row = 0.5 + 0.5 * np.cos(2 * np.pi * 900 * np.arange(N) / N)
    d = [{"which": "元", "pixel": i, "value": round(float(v), 5)} for i, v in enumerate(row)]
    for m in METHODS:
        d += [{"which": m, "pixel": i, "value": round(float(v), 5)} for i, v in enumerate(shrink(row, m, K, 0))]
    pd.DataFrame(d).to_csv(DATA / "stripe900_rows.csv", index=False)

    # 図1：同心円の縞（細かさが外ほど増す）を縮める
    S = 800
    yy, xx = np.mgrid[0:S, 0:S] - S / 2
    zone = 0.5 + 0.5 * np.cos(np.pi * (xx ** 2 + yy ** 2) / S * 0.6)   # 外の角でも1画素あたり0.42組（元の画像の限界0.5組より粗い）
    fig, axes = plt.subplots(1, 4, figsize=(8.4, 2.9))
    small_imgs = [zone[::K, ::K], zone.reshape(S // K, K, S // K, K).mean((1, 3)),
                  np.real(np.fft.ifft2(np.fft.fft2(zone) * np.exp(-2 * np.pi ** 2 * (0.5 * K) ** 2 *
                          (np.fft.fftfreq(S)[:, None] ** 2 + np.fft.fftfreq(S)[None, :] ** 2))))[::K, ::K]]
    for ax, im, t in zip(axes, [zone[S // 2 - 200:S // 2, S // 2:S // 2 + 200]] + small_imgs, ["元（中心から右上の200×200画素）", "間引く", "まとめて平均", "ぼかして間引く"]):
        ax.imshow(im, cmap="gray", vmin=0, vmax=1, interpolation="nearest"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(t, fontsize=9.5)
    fig.suptitle("外ほど細かくなる同心円の縞（800×800画素）を1/4（200×200画素）に縮める：間引くと外側に偽の輪が出る", fontsize=12, y=1.03)
    save(fig, "a1127_rings.png", SRC)

    # 図2：元の縞の細かさと、縮めた画像に見える縞の細かさ・くっきり度
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8))
    for m, c in zip(METHODS, [ORANGE, BLUE, GREEN]):
        g = byf[byf.method == m]
        axes[1].plot(g.f, g.contrast * 100, color=c, lw=1.6, label=m)
    g = byf[byf.method == "間引く"]
    axes[0].plot(g.f, g.f_seen, color=ORANGE, lw=1.6)
    axes[0].plot([0, 250], [0, 250], color=GRAY, lw=0.8, ls=":")
    axes[0].set_xlabel("元の縞の細かさ（組の数）"); axes[0].set_ylabel("縮めた画像に見える縞の細かさ")
    axes[0].set_title("間引くと、細かい縞は粗い縞に化ける", fontsize=11); axes[0].set_ylim(0, 270)
    for ax in axes:
        ax.axvline(ns / 2, color=GRAY, lw=0.8, ls="--")
    axes[0].text(ns / 2 + 15, 262, "縮めた画像の限界（250組）", fontsize=8.5, color=GRAY, va="top")
    axes[1].axhline(TH * 100, color=INK, lw=0.8, ls=":")
    axes[1].set_xlabel("元の縞の細かさ（組の数）"); axes[1].set_ylabel("縮めた画像の縞のくっきり度（%）")
    axes[1].set_ylim(0, 105); axes[1].legend(frameon=False, fontsize=8.5, loc="upper right", bbox_to_anchor=(1, 0.93))
    axes[1].set_title("250組より右は、すべて偽の縞", fontsize=11)
    fig.tight_layout()
    save(fig, "a1127_alias.png", SRC)

    # 図3：偽の縞が出た割合と、残すべき縞のくっきり度
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    xs = np.arange(3); w = 0.38
    ax.bar(xs - w / 2, summ.false_ge10_share * 100, w, color=ORANGE, label="偽の縞（くっきり度10%以上）が出た割合")
    ax.bar(xs + w / 2, summ.keep_f200 * 100, w, color=BLUE, label="残すべき200組の縞のくっきり度")
    for i in range(3):
        ax.text(i - w / 2, summ.false_ge10_share[i] * 100 + 1.5, f"{summ.false_ge10_share[i]*100:.2f}%", ha="center", fontsize=9)
        ax.text(i + w / 2, summ.keep_f200[i] * 100 + 1.5, f"{summ.keep_f200[i]*100:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels(METHODS); ax.set_ylim(0, 118); ax.set_ylabel("%")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("1/4に縮めたとき：偽の縞を消すほど、残すべき縞も薄くなる", fontsize=12)
    save(fig, "a1127_tradeoff.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(summ.to_string()); print(grid.to_string())


if __name__ == "__main__":
    main()
