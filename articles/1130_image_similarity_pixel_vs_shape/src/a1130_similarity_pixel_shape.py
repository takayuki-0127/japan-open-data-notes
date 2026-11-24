"""1130 2枚の画像の「似ている度合い」は、画素ごとの差で測るか形で測るかで、似た組の順位がどう変わるのか？（架空のデータ）

架空の商品の写真に見立てた白黒の画像（48×48画素）を、商品30点×6枚作る。
  元の画像：明るい背景に、商品に見立てた四角・丸の板を1〜3枚置き、細かい模様を足したもの
  同じ商品の別の写り（5種類）：明るさ違い（+25）、濃淡の幅違い（0.7倍）、2画素ずれ、ぼかし（3×3）、粒（標準偏差12）
180枚の全部の組（16,110組）のうち、同じ商品の組（450組）が「本当に似ている組」。
似ている度合いを2つの物差しで数え、似ている順の上位450組に同じ商品の組がどれだけ入るか、
どの写りの組がどこに並ぶかを数える。
  ①画素の差：同じ位置の画素の差の二乗平均の平方根（小さいほど似ている）
  ②形の似ている度合い：7×7画素の窓ごとに、明るさ・濃淡の幅・濃淡の並び（相関）の3つの近さを掛け合わせ、窓で平均した値（1に近いほど似ている）
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1130
SRC = "架空の商品の写真に見立てた白黒の画像（作成者が式と乱数で作成、seed 1130）"
S = 48
N_PROD = 30
KINDS = ["元", "明るさ違い", "濃淡の幅違い", "2画素ずれ", "ぼかし", "粒"]
BASE = {"win": 7, "bright": 25, "noise": 12.0, "contrast": 0.7, "shift": 2}
C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
GRID_WIN = [5, 7, 11]
GRID_BRIGHT = [10, 25, 40]
GRID_NOISE = [6.0, 12.0, 24.0]


def r(x, d=2):
    return round(float(x), d)


def make_product(rng):
    y, x = np.mgrid[0:S, 0:S].astype(float)
    bg = rng.uniform(205, 245)
    img = np.full((S, S), bg)
    for _ in range(rng.integers(1, 4)):
        v = rng.uniform(40, 190)
        if rng.random() < 0.5:
            x0, y0 = rng.integers(4, S - 16, 2); w, h = rng.integers(6, 22, 2)
            img[y0:y0 + h, x0:x0 + w] = v
        else:
            cx, cy = rng.uniform(10, S - 10, 2); rr = rng.uniform(4, 11)
            img[(x - cx) ** 2 + (y - cy) ** 2 < rr ** 2] = v
    # 商品の表面の細かい模様（板の上だけ）
    tex = rng.normal(0, 6, (S, S))
    img = np.where(img < bg - 1, img + tex, img)
    return np.clip(img, 0, 255), bg


def box_mean(a, w):
    """最後の2軸を w×w の窓で平均（窓が画像からはみ出さない所だけ）"""
    c = np.cumsum(np.cumsum(a, axis=-1), axis=-2)
    c = np.pad(c, [(0, 0)] * (a.ndim - 2) + [(1, 0), (1, 0)])
    return (c[..., w:, w:] - c[..., :-w, w:] - c[..., w:, :-w] + c[..., :-w, :-w]) / (w * w)


def variants(img, bg, rng, bright, noise, contrast, shift):
    out = [img.copy()]
    out.append(np.clip(img + bright, 0, 255))
    m = img.mean()
    out.append(np.clip(m + (img - m) * contrast, 0, 255))
    sh = np.full((S, S), bg); sh[shift:, shift:] = img[:-shift, :-shift]
    out.append(sh)
    p = np.pad(img, 1, mode="edge")
    out.append(sum(p[i:i + S, j:j + S] for i in range(3) for j in range(3)) / 9)
    out.append(np.clip(img + rng.normal(0, noise, (S, S)), 0, 255))
    return [np.round(o) for o in out]


def make_set(rng, bright, noise, contrast=BASE["contrast"], shift=BASE["shift"]):
    imgs, prod, kind = [], [], []
    for pidx in range(N_PROD):
        img, bg = make_product(rng)
        for k, v in enumerate(variants(img, bg, rng, bright, noise, contrast, shift)):
            imgs.append(v); prod.append(pidx); kind.append(k)
    return np.array(imgs), np.array(prod), np.array(kind)


def measures(imgs, win):
    n = len(imgs)
    flat = imgs.reshape(n, -1)
    sq = (flat ** 2).sum(1)
    d2 = (sq[:, None] + sq[None, :] - 2 * flat @ flat.T) / flat.shape[1]
    pix = np.sqrt(np.maximum(d2, 0))
    mu = box_mean(imgs, win)
    var = box_mean(imgs ** 2, win) - mu ** 2
    shape = np.ones((n, n))
    for i in range(n - 1):
        cov = box_mean(imgs[i][None] * imgs[i + 1:], win) - mu[i][None] * mu[i + 1:]
        num = (2 * mu[i][None] * mu[i + 1:] + C1) * (2 * cov + C2)
        den = (mu[i][None] ** 2 + mu[i + 1:] ** 2 + C1) * (var[i][None] + var[i + 1:] + C2)
        v = (num / den).mean(axis=(1, 2))
        shape[i, i + 1:] = v; shape[i + 1:, i] = v
    return pix, shape


def rank_desc(x):
    return pd.Series(x).rank(ascending=False, method="first").values


def analyze(imgs, prod, kind, win):
    pix, shape = measures(imgs, win)
    iu = np.triu_indices(len(imgs), 1)
    i, j = iu
    same = prod[i] == prod[j]
    K = int(same.sum())
    sp = -pix[iu]; ss = shape[iu]
    rp, rs = rank_desc(sp), rank_desc(ss)
    top_p, top_s = rp <= K, rs <= K
    # 同じ商品の組を「元」と別の写りの組に絞って、写りの種類ごとに
    by_kind = {}
    for k in range(1, len(KINDS)):
        m = same & (((kind[i] == 0) & (kind[j] == k)) | ((kind[j] == 0) & (kind[i] == k)))
        by_kind[KINDS[k]] = {
            "n": int(m.sum()),
            "top_pixel": r(top_p[m].mean() * 100, 1), "top_shape": r(top_s[m].mean() * 100, 1),
            "median_rank_pixel": int(np.median(rp[m])), "median_rank_shape": int(np.median(rs[m])),
        }
    diff_top_p = top_p & ~same
    out = {
        "n_images": int(len(imgs)), "n_pairs": int(len(sp)), "K": K,
        "precision_pixel": r((top_p & same).sum() / K * 100, 1),
        "precision_shape": r((top_s & same).sum() / K * 100, 1),
        "overlap_top": int((top_p & top_s).sum()),
        "rank_corr_all": r(np.corrcoef(rp, rs)[0, 1], 3),
        "n_diff_in_top_pixel": int(diff_top_p.sum()), "n_diff_in_top_shape": int((top_s & ~same).sum()),
        "by_kind": by_kind,
    }
    return out, pix, shape, (i, j, same, rp, rs)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    imgs, prod, kind = make_set(rng, BASE["bright"], BASE["noise"])
    base, pix, shape, (i, j, same, rp, rs) = analyze(imgs, prod, kind, BASE["win"])

    # 上位450組に入った「別の商品の組」の背景の割合（背景＝元の画像で背景と同じ値の画素）
    bg_share = np.array([(np.abs(imgs[p * 6] - np.median(imgs[p * 6])) < 1).mean() for p in range(N_PROD)])
    K = base["K"]
    dt = (rp <= K) & ~same
    base["bg_share_all_products"] = r(bg_share.mean() * 100, 1)
    base["bg_share_diff_top_pixel"] = r(((bg_share[prod[i[dt]]] + bg_share[prod[j[dt]]]) / 2).mean() * 100, 1) if dt.any() else None
    dts = (rs <= K) & ~same
    base["bg_share_diff_top_shape"] = r(((bg_share[prod[i[dts]]] + bg_share[prod[j[dts]]]) / 2).mean() * 100, 1) if dts.any() else None
    # 別の商品の組で、画素の差でいちばん似ていた組
    diff_idx = np.where(~same)[0]
    best_diff = diff_idx[np.argmin(rp[diff_idx])]
    base["best_diff_pair_pixel"] = {"rank_pixel": int(rp[best_diff]), "rank_shape": int(rs[best_diff]),
                                   "pixel": r(pix[i[best_diff], j[best_diff]]),
                                   "shape": r(shape[i[best_diff], j[best_diff]], 3)}

    # 例の商品（商品A＝0番）：元の画像と別の写り・画素の差でいちばん近い別の商品
    a0 = 0
    other = [x for x in range(len(imgs)) if prod[x] != 0]
    near = other[int(np.argmin(pix[a0, other]))]
    base["example_product_A"] = {KINDS[k]: {"pixel": r(pix[a0, k]), "shape": r(shape[a0, k], 3)} for k in range(1, 6)}
    base["example_product_A"]["別の商品（画素の差でいちばん近い）"] = {"pixel": r(pix[a0, near]), "shape": r(shape[a0, near], 3)}
    # 作りの確かめ：同じ画像どうしなら画素の差0・形1
    sp_, ss_ = measures(np.array([imgs[0], imgs[0]]), BASE["win"])
    base["self_check"] = {"pixel": r(sp_[0, 1], 6), "shape": r(ss_[0, 1], 6)}

    pairs = pd.DataFrame({"img_a": i, "img_b": j, "prod_a": prod[i], "prod_b": prod[j],
                          "kind_a": [KINDS[k] for k in kind[i]], "kind_b": [KINDS[k] for k in kind[j]],
                          "same_product": same.astype(int), "pixel_diff": pix[i, j].round(3),
                          "shape_sim": shape[i, j].round(4), "rank_pixel": rp.astype(int), "rank_shape": rs.astype(int)})
    pairs.to_csv(DATA / "pairs.csv", index=False)

    # 確かめ：27通り
    grid = []
    for w, b, nz in itertools.product(GRID_WIN, GRID_BRIGHT, GRID_NOISE):
        g_imgs, g_prod, g_kind = make_set(np.random.default_rng([SEED, w, b, int(nz)]), b, nz)
        o, *_ = analyze(g_imgs, g_prod, g_kind, w)
        row = {"win": w, "bright": b, "noise": nz, "precision_pixel": o["precision_pixel"],
               "precision_shape": o["precision_shape"], "overlap_top": o["overlap_top"],
               "rank_corr_all": o["rank_corr_all"]}
        for k, v in o["by_kind"].items():
            row[f"top_pixel_{k}"] = v["top_pixel"]; row[f"top_shape_{k}"] = v["top_shape"]
        grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gsum = {c: [r(grid[c].min(), 3), r(grid[c].max(), 3)] for c in grid.columns if c not in ("win", "bright", "noise")}
    gsum["n_shape_better"] = int((grid.precision_shape > grid.precision_pixel).sum())
    gsum["n"] = int(len(grid))
    gsum["n_shape_better_by_win"] = {str(w): int((grid[grid.win == w].precision_shape > grid[grid.win == w].precision_pixel).sum())
                                     for w in GRID_WIN}
    gsum["n_shape_better_by_bright"] = {str(b): int((grid[grid.bright == b].precision_shape > grid[grid.bright == b].precision_pixel).sum())
                                        for b in GRID_BRIGHT}

    res = {"base": BASE, "image_size": S, "n_products": N_PROD, "kinds": KINDS, "result": base,
           "grid": {"win": GRID_WIN, "bright": GRID_BRIGHT, "noise": GRID_NOISE, "summary": gsum}}
    pd.DataFrame([{"kind": k, **v} for k, v in base["by_kind"].items()]).to_csv(RES / "by_kind.csv", index=False)

    # ---------- 図1：例の商品 ----------
    p0 = 0
    fig, axes = plt.subplots(2, 4, figsize=(10.5, 6.2))
    ex = [(p0 * 6 + k, KINDS[k]) for k in range(6)]
    # 画素の差で、商品0の元の画像にいちばん近かった別の商品
    a0 = p0 * 6
    other = [x for x in range(len(imgs)) if prod[x] != p0]
    near = other[int(np.argmin(pix[a0, other]))]
    ex.append((near, "別の商品（画素の差で\nいちばん近い）"))
    for ax in axes.ravel():
        ax.axis("off")
    for ax, (idx, name) in zip(axes.ravel(), ex):
        ax.imshow(imgs[idx], cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        if idx == a0:
            ax.set_title("商品Aの元の画像", fontsize=10)
        else:
            lab = name if prod[idx] != p0 else f"商品Aの{name}"
            ax.set_title(f"{lab}\n画素の差 {pix[a0, idx]:.1f}・形 {shape[a0, idx]:.3f}", fontsize=9.5)
    fig.suptitle("元の画像と比べた2つの物差し（画素の差は小さいほど、形は1に近いほど似ている）", fontsize=11.5)
    fig.tight_layout()
    save(fig, "a1130_example.png", SRC)

    # ---------- 図2：写りの種類ごとの上位450組入り ----------
    bk = pd.DataFrame([{"kind": k, **v} for k, v in base["by_kind"].items()])
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(bk))
    b1 = ax.bar(x - 0.2, bk.top_pixel, 0.4, color=ORANGE, label="①画素の差")
    b2 = ax.bar(x + 0.2, bk.top_shape, 0.4, color=BLUE, label="②形の似ている度合い")
    for bars in (b1, b2):
        for bb in bars:
            ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 1.5, f"{bb.get_height():.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(bk.kind)
    ax.set_ylim(0, 125); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("似ている上位450組に入った割合（%）")
    ax.set_title(f"元の画像と別の写りの組（各30組）：上位450組に入ったか（全16,110組の中で）", fontsize=11.5)
    ax.legend(fontsize=9, loc="upper center", ncol=2); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    save(fig, "a1130_by_kind.png", SRC)

    # ---------- 図3：27通り ----------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    xs = np.arange(len(grid))
    axes[0].plot(xs, grid.precision_pixel, "o", color=ORANGE, label="①画素の差")
    axes[0].plot(xs, grid.precision_shape, "o", color=BLUE, label="②形の似ている度合い")
    axes[0].set_ylim(0, 100); axes[0].set_xticks([])
    axes[0].set_xlabel("置き方27通り（窓の大きさ×明るさの違い×粒の強さ）")
    axes[0].set_ylabel("上位450組のうち同じ商品の組（%）")
    axes[0].set_title(f"形のほうが高かったのは{gsum['n_shape_better']}/27通り")
    axes[0].legend(fontsize=9); axes[0].grid(alpha=0.3)
    axes[1].bar(xs, grid.overlap_top, color=GRAY)
    axes[1].set_ylim(0, 450); axes[1].set_xticks([])
    axes[1].set_xlabel("置き方27通り")
    axes[1].set_ylabel("2つの物差しの上位450組の重なり（組）")
    axes[1].set_title(f"上位450組の重なりは{gsum['overlap_top'][0]:.0f}〜{gsum['overlap_top'][1]:.0f}組")
    for ax in axes:
        ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    save(fig, "a1130_robust.png", SRC)

    with open(RES / "a1130_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
