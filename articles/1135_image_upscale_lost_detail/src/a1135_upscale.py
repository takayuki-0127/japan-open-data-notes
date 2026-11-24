"""1135 小さい画像を拡大して画素の数を増やすと、失われた細かさは戻るのか？（架空のデータ）

作成者が式と乱数で作った架空の画像（①細さの違う縦縞の板、②商品の写真に見立てた板＝形の板＋細かい模様の板）を、
縦横 k 分の1に縮小し（k×k の画素の平均、256段階で保存）、4つのやり方で縦横 k 倍に拡大して元と比べる。
拡大のやり方：同じ画素を繰り返す／隣の画素を直線でつなぐ／3次の曲線でつなぐ／直線でつないでから輪郭を強める。
①では、元の周期の縞がどれだけ残ったか（残りの濃さ）と、元にない縞の濃さを数える。
②では、小さい画像では表せない細かさ（周期 2k 画素より細かい成分）が、拡大でどれだけ作られ、元とどれだけ合うかを数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1135
SRC = "架空の縞の板と架空の写真に見立てた板（作成者が式と乱数で作成、seed 1135）"
SIZE = 256
PERIODS = [2, 3, 4, 6, 8, 12, 16, 24, 32, 64]
AMP = 0.35
K = 4
METHODS = ["繰り返す", "直線でつなぐ", "3次の曲線でつなぐ", "直線＋輪郭を強める"]
SHARP = 1.0
NB = 16           # 縞の位置（位相）を変えて平均する回数
BAND_ROWS = 64    # 縞の帯1本の行数（帯ごとに別の画像として縮小・拡大する）
EDGE = 32         # 左右の端の列は数えない
GRAIN = 1.0       # 細かい模様の粒の大きさ（画素）
TEX_AMP = 0.06


def r(x, d=3):
    return round(float(x), d)


# ---- 画像を作る ----
def stripe_band(p, ph, size=SIZE, rows=BAND_ROWS):
    x = np.arange(size)
    return np.repeat(0.5 + AMP * np.sin(2 * np.pi * x[None, :] / p + ph), rows, 0)


def shape_board(rng, size=SIZE):
    """形の板：明るさの違う四角と丸、なめらかな明るさの傾き"""
    y, x = np.mgrid[0:size, 0:size] / size
    img = 0.35 + 0.25 * x + 0.1 * y
    for _ in range(10):
        cx, cy = rng.uniform(0.05, 0.8, 2)
        w, h = rng.uniform(0.08, 0.3, 2)
        img[(x > cx) & (x < cx + w) & (y > cy) & (y < cy + h)] = rng.uniform(0.15, 0.85)
    for _ in range(6):
        cx, cy, rad = rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85), rng.uniform(0.04, 0.12)
        img[(x - cx) ** 2 + (y - cy) ** 2 < rad ** 2] = rng.uniform(0.15, 0.85)
    return img


def texture_board(rng, size=SIZE, grain=GRAIN, amp=TEX_AMP):
    """細かい模様の板：布の目のような細かい粒（でたらめな値をぼかし、標準偏差 amp にそろえる）"""
    t = blur(rng.normal(0, 1, (size, size)), grain, wrap=True)
    return 0.5 + amp * t / t.std()


# ---- 縮小と拡大 ----
def down(img, k):
    h, w = img.shape
    s = img.reshape(h // k, k, w // k, k).mean((1, 3))
    return np.round(np.clip(s, 0, 1) * 255) / 255           # 256段階で保存


def resize_axis(a, k, kind, axis):
    a = np.moveaxis(a, axis, -1)
    n = a.shape[-1]
    pos = (np.arange(n * k) + 0.5) / k - 0.5        # 拡大後の画素の中心（小さい画像の座標）
    i0 = np.floor(pos).astype(int)
    t = pos - i0
    if kind == "繰り返す":
        out = a[..., np.clip(np.floor(pos + 0.5).astype(int), 0, n - 1)]
    elif kind == "直線":
        out = a[..., np.clip(i0, 0, n - 1)] * (1 - t) + a[..., np.clip(i0 + 1, 0, n - 1)] * t
    else:  # 3次の曲線（となりの4点を通るなめらかな曲線）
        out = 0
        for m in (-1, 0, 1, 2):
            d = np.abs(t - m)
            w = np.where(d <= 1, 1.5 * d ** 3 - 2.5 * d ** 2 + 1,
                         np.where(d < 2, -0.5 * d ** 3 + 2.5 * d ** 2 - 4 * d + 2, 0))
            out = out + a[..., np.clip(i0 + m, 0, n - 1)] * w
    return np.moveaxis(out, -1, axis)


def blur(img, sigma, wrap=False):
    rad = int(np.ceil(3 * sigma))
    xs = np.arange(-rad, rad + 1)
    w = np.exp(-0.5 * (xs / sigma) ** 2)
    w /= w.sum()
    p = img if wrap else np.pad(img, rad, mode="reflect")
    out = sum(wi * np.roll(p, xi, 1) for wi, xi in zip(w, xs))
    out = sum(wi * np.roll(out, xi, 0) for wi, xi in zip(w, xs))
    return out if wrap else out[rad:-rad, rad:-rad]


def up(small, k, method, sharp=SHARP):
    kind = {"繰り返す": "繰り返す", "3次の曲線でつなぐ": "3次"}.get(method, "直線")
    u = resize_axis(resize_axis(small, k, kind, 0), k, kind, 1)
    if method == "直線＋輪郭を強める":
        u = u + sharp * (u - blur(u, 0.6 * k))
    return np.clip(u, 0, 1)


# ---- 数える ----
def stripe_measure(img, p):
    """元の周期 p の成分の濃さ（振幅）と、それ以外の揺れ（元にない縞）の濃さ。元の縞の濃さを1とする"""
    xx = np.arange(img.shape[1])[EDGE:-EDGE]
    row = img[img.shape[0] // 2, EDGE:-EDGE]
    X = np.column_stack([np.ones_like(xx, dtype=float), np.cos(2 * np.pi * xx / p), np.sin(2 * np.pi * xx / p)])
    coef, *_ = np.linalg.lstsq(X, row, rcond=None)
    amp = np.hypot(coef[1], coef[2])
    false_amp = np.sqrt(2) * (row - X @ coef).std()
    return amp / AMP, false_amp / AMP


def stripes(k, method, sharp, rng, nb=NB):
    rows = []
    for p in PERIODS:
        kept, false = [], []
        for _ in range(nb):
            b = stripe_band(p, rng.uniform(0, 2 * np.pi))
            a, f = stripe_measure(up(down(b, k), k, method, sharp), p)
            kept.append(a)
            false.append(f)
        zone = "表せない" if p < 2 * k else ("ちょうど境目" if p == 2 * k else "表せる")
        rows.append({"k": k, "method": method, "period": p, "zone": zone,
                     "kept": r(np.mean(kept)), "false": r(np.mean(false)),
                     "down_only_formula": r(abs(np.sinc(k / p))) if p > 2 * k else None})
    return rows


def high_band(img, k):
    """小さい画像では表せない細かさ：縦か横の周期が 2k 画素より細かい成分"""
    F = np.fft.fft2(img - img.mean())
    f = np.fft.fftfreq(img.shape[0])
    mask = (np.abs(f)[:, None] > 1 / (2 * k)) | (np.abs(f)[None, :] > 1 / (2 * k))
    return np.real(np.fft.ifft2(F * mask))


def detail_measure(orig, k, method, sharp=SHARP):
    u = up(down(orig, k), k, method, sharp)
    ho, hu = high_band(orig, k), high_band(u, k)
    made = hu.std() / ho.std()                                   # 作られた細かさの量（元を1）
    corr = (ho * hu).sum() / np.sqrt((ho ** 2).sum() * (hu ** 2).sum()) if hu.std() > 0 else 0.0
    back = 1 - ((ho - hu) ** 2).sum() / (ho ** 2).sum()           # 戻った割合（1で全部戻る、0以下は戻らない）
    gx, gy = np.diff(u, axis=1), np.diff(u, axis=0)
    ox, oy = np.diff(orig, axis=1), np.diff(orig, axis=0)
    sharpness = np.sqrt(((gx ** 2).mean() + (gy ** 2).mean()) / ((ox ** 2).mean() + (oy ** 2).mean()))
    return {"back": float(back), "made": float(made), "match": float(corr), "sharpness": float(sharpness),
            "mean_abs_diff": float(np.abs(u - orig).mean())}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    shp = shape_board(rng)
    tex = texture_board(rng)
    photo = np.clip(shp + tex - 0.5, 0, 1)
    pd.DataFrame(np.round(photo, 4)).to_csv(DATA / "photo_board.csv", index=False, header=False)
    pd.DataFrame(np.round(shp, 4)).to_csv(DATA / "shape_board.csv", index=False, header=False)
    pd.DataFrame(np.round(tex, 4)).to_csv(DATA / "texture_board.csv", index=False, header=False)

    # 1) 縞：k=4、4つのやり方（位相を16回変えて平均）
    st = []
    for m in METHODS:
        st += stripes(K, m, SHARP, np.random.default_rng(SEED + 1))
    st = pd.DataFrame(st)
    st.to_csv(RES / "stripes_k4.csv", index=False)

    # 2) 写真に見立てた板：形の板・細かい模様の板・合わせた板
    det = []
    for name, img in [("形の板", shp), ("細かい模様の板", tex), ("合わせた板", photo)]:
        for m in METHODS:
            d = detail_measure(img, K, m)
            det.append({"board": name, "method": m, **{kk: r(v, 4 if kk == "mean_abs_diff" else 3) for kk, v in d.items()}})
    det = pd.DataFrame(det)
    det.to_csv(RES / "detail_k4.csv", index=False)

    # 3) 確かめ：縮小の倍率 k（2・4・8）× 輪郭を強める強さ（0.5・1・2）× 細かい模様の粒（0.5・0.75・1画素）
    grid = []
    for i, (k, sh, gr) in enumerate(itertools.product([2, 4, 8], [0.5, 1.0, 2.0], [0.5, 0.75, 1.0])):
        g = np.random.default_rng(SEED * 100 + i)
        shp_g = shape_board(g)
        tex_g = texture_board(g, grain=gr)
        sts = pd.DataFrame([row for m in METHODS for row in stripes(k, m, sh, g, nb=4)])
        row = {"k": k, "sharp": sh, "grain": gr,
               "beyond_kept_max": r(sts[sts.zone == "表せない"].kept.max()),
               "beyond_false_max": r(sts[sts.zone == "表せない"].false.max()),
               "within_kept_min": r(sts[sts.zone == "表せる"].kept.min()),
               "within_kept_max_sharp": r(sts[(sts.zone == "表せる") & (sts.method == METHODS[3])].kept.max())}
        for name, img in [("shape", shp_g), ("texture", tex_g)]:
            for m, key in zip(METHODS, ["repeat", "linear", "cubic", "sharp"]):
                d = detail_measure(img, k, m, sh)
                row[f"{name}_{key}_back"] = r(d["back"])
                row[f"{name}_{key}_match"] = r(d["match"])
                row[f"{name}_{key}_made"] = r(d["made"])
                row[f"{name}_{key}_sharpness"] = r(d["sharpness"])
        grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    keys = ["repeat", "linear", "cubic", "sharp"]
    tex_match = grid[[f"texture_{k}_match" for k in keys]]
    shp_match = grid[[f"shape_{k}_match" for k in keys]]
    tex_back = grid[[f"texture_{k}_back" for k in keys]]
    shp_back = grid[[f"shape_{k}_back" for k in keys]]
    out = {"settings": {"seed": SEED, "size": SIZE, "k": K, "periods": PERIODS, "stripe_amp": AMP, "sharp": SHARP,
                        "phases": NB, "grid_phases": 4, "grain": GRAIN, "texture_sd": TEX_AMP},
           "pixels": {"orig": SIZE * SIZE, "small": (SIZE // K) ** 2, "up": SIZE * SIZE},
           "stripes_k4": st.to_dict("records"),
           "stripes_k4_beyond_kept_max": r(st[st.zone == "表せない"].kept.max()),
           "detail_k4": det.to_dict("records"),
           "grid_range": {
               "beyond_kept_max": r(grid.beyond_kept_max.max()),
               "beyond_false_max": r(grid.beyond_false_max.max()),
               "within_kept_max_sharp": r(grid.within_kept_max_sharp.max()),
               "texture_match_min": r(tex_match.min().min()), "texture_match_max": r(tex_match.max().max()),
               "shape_match_min": r(shp_match.min().min()), "shape_match_max": r(shp_match.max().max()),
               "texture_back_min": r(tex_back.min().min()), "texture_back_max": r(tex_back.max().max()),
               "shape_back_min": r(shp_back.min().min()), "shape_back_max": r(shp_back.max().max()),
               "texture_sharp_back_min": r(grid.texture_sharp_back.min()), "texture_sharp_back_max": r(grid.texture_sharp_back.max()),
               "texture_sharp_back_below_linear": int((grid.texture_sharp_back < grid.texture_linear_back).sum()),
               "back_below_minus1_count": int((grid[[c for c in grid.columns if c.endswith("_back")]] < -1).sum().sum()),
               "repeat_back_negative_count": int((grid[["shape_repeat_back", "texture_repeat_back"]] < 0).sum().sum()),
               "shape_sharp_sharpness_min": r(grid.shape_sharp_sharpness.min()),
               "shape_sharp_sharpness_max": r(grid.shape_sharp_sharpness.max()),
               "shape_linear_sharpness_min": r(grid.shape_linear_sharpness.min()),
               "shape_linear_sharpness_max": r(grid.shape_linear_sharpness.max()),
               "shape_sharp_over_linear_match": int((grid.shape_sharp_match > grid.shape_linear_match).sum()),
               "shape_sharp_back_over_linear": int((grid.shape_sharp_back > grid.shape_linear_back).sum()),
               "texture_sharp_back_over_linear": int((grid.texture_sharp_back > grid.texture_linear_back).sum()),
               "shape_sharp_sharper_than_linear": int((grid.shape_sharp_sharpness > grid.shape_linear_sharpness).sum()),
               "within_kept_min": r(grid.within_kept_min.min())}}
    json.dump(out, open(RES / "a1135_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    figures(st, det, grid, shp, tex, photo)
    print(st.to_string())
    print(det.to_string())
    print(json.dumps(out["grid_range"], ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


def figures(st, det, grid, shp, tex, photo):
    g = np.random.default_rng(SEED + 7)
    board = np.vstack([stripe_band(p, g.uniform(0, 2 * np.pi), rows=24) for p in PERIODS])
    board = np.vstack([board, np.full((SIZE - board.shape[0], SIZE), 0.5)])
    small = down(board, K)
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.4))
    for ax, (t, im) in zip(axs, [("元（256×256画素）", board), (f"縮小（{SIZE // K}×{SIZE // K}画素）", small),
                                 ("3次の曲線でつないで拡大（256×256画素）", up(small, K, "3次の曲線でつなぐ"))]):
        ax.imshow(im, cmap="gray", vmin=0, vmax=1, interpolation="nearest", extent=(0, SIZE, SIZE, 0))
        ax.set_title(t, fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    for i, p in enumerate(PERIODS):
        axs[0].text(-4, i * 24 + 12, f"{p}", ha="right", va="center", fontsize=8)
    axs[0].text(-4, -3, "周期", ha="right", va="bottom", fontsize=8)
    fig.suptitle("縦横4分の1に縮小して戻すと、周期8画素より細い縞は消えるか、別の縞に化けた", fontsize=12)
    save(fig, "a1135_stripes_image.png", SRC)

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    cols = {"繰り返す": GRAY, "直線でつなぐ": BLUE, "3次の曲線でつなぐ": GREEN, "直線＋輪郭を強める": ORANGE}
    xs = np.arange(len(PERIODS))
    for m in METHODS:
        s = st[st.method == m]
        ax.plot(xs, s.kept, "o-", color=cols[m], label=f"{m}：元の縞の残り")
    s = st[st.method == "3次の曲線でつなぐ"]
    ax.plot(xs, s.false, "x:", color=GREEN, label="3次の曲線でつなぐ：元にない縞の濃さ")
    ax.axvspan(-0.45, PERIODS.index(2 * K) - 0.5, color=LIGHT, alpha=0.35, lw=0)
    ax.text(0, 1.17, "縦横4分の1の画像では表せない細さ", fontsize=8.5, color=INK)
    ax.axhline(1, color=GRAY, lw=0.8)
    ax.set_xticks(xs, [str(p) for p in PERIODS])
    ax.set_xlabel("縞の周期（元の画素）")
    ax.set_ylabel("元の縞の濃さを1とした大きさ")
    ax.set_ylim(0, 1.25)
    ax.set_title(f"表せない細さの縞は、どのやり方でも元の{st[st.zone == '表せない'].kept.max():.3f}倍までしか戻らなかった（縦横4分の1）", fontsize=10.5)
    ax.legend(frameon=False, fontsize=7.6, loc="center right")
    save(fig, "a1135_kept_by_period.png", SRC)

    fig, axs = plt.subplots(1, 3, figsize=(12, 4.3), gridspec_kw={"width_ratios": [1, 1, 1.35], "wspace": 0.35})
    crop = (slice(100, 164), slice(100, 164))
    axs[0].imshow(photo[crop], cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    axs[0].set_title("元（64×64画素を切り出し）", fontsize=10)
    axs[1].imshow(up(down(photo, K), K, "直線＋輪郭を強める")[crop], cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    axs[1].set_title("縦横4分の1→輪郭を強めて拡大", fontsize=10)
    for a in axs[:2]:
        a.set_xticks([]); a.set_yticks([])
    ax = axs[2]
    keys = ["repeat", "linear", "cubic", "sharp"]
    for j, (name, lab, col) in enumerate([("shape", "形の板", BLUE), ("texture", "細かい模様の板", ORANGE)]):
        for i, kk in enumerate(keys):
            v = grid[f"{name}_{kk}_back"].clip(lower=-1)
            xx = i + (j - 0.5) * 0.3 + np.linspace(-0.08, 0.08, len(v))
            ax.scatter(xx, v, color=col, s=10, label=lab if i == 0 else None)
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xticks(range(4), ["繰り返す", "直線", "3次の曲線", "輪郭を強める"], fontsize=8.5)
    ax.set_ylabel("表せない細かさの戻った割合")
    ax.set_ylim(-1.08, 1)
    n_low = int((grid[[c for c in grid.columns if c.endswith("_back")]] < -1).sum().sum())
    if n_low:
        ax.text(3.45, -1.04, f"−1より下の{n_low}点は−1に置いた", ha="right", va="bottom", fontsize=7.5, color=GRAY)
    ax.set_title("置き方27通り（1で全部戻る、0以下は戻らない）", fontsize=9.5)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("拡大で戻った細かさは、どのやり方・置き方でも一部だけだった", fontsize=12)
    save(fig, "a1135_photo.png", SRC)


if __name__ == "__main__":
    main()
