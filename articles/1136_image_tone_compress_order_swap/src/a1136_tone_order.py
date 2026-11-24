"""1136 明るい所と暗い所を1枚に収める処理で、明るさの順番は入れかわるのか？（架空のデータ）

作成者が置いた架空の場面：左半分が部屋（照明の強さ1）、右半分が窓の外（照明の強さ E 倍、基本1000倍）。
両側に、白さ（反射の割合）の違う板を12枚ずつ置き、明るさ＝照明×白さ（＋細かいむら）とする。
これを画面の256段階に収める2つの処理を比べる。
 ① 全体に同じ曲線をかける（明るさの順に並べた値を、そのままなめらかに縮める）
 ② 部分ごとに明るさを合わせる（周りの明るさの平均〈ぼかした対数の明るさ〉を t 倍に縮め、周りとの差はそのまま残す）
板どうし・画素どうしの組で、本当の明るさの順と画面での順が入れかわった割合・同じ段階につぶれた割合を数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1136
SRC = "架空の部屋と窓の場面（作成者が置いた照明と板の白さからの乱数、seed 1136）"
H, W = 192, 384
PATCH = 32
REFL = [0.04, 0.06, 0.09, 0.13, 0.18, 0.25, 0.35, 0.45, 0.55, 0.7, 0.8, 0.9]
BACK = 0.3
NOISE = 0.08
BASE = {"E": 1000.0, "t": 0.2, "sigma": 32.0}
N_PIX_PAIRS = 200_000
TIE = 0.5      # 画面の値（板の平均）の差がこれ未満なら「同じ段階」と数える


def r(x, d=2):
    return round(float(x), d)


def make_scene(rng, E):
    illum = np.ones((H, W))
    illum[:, W // 2:] = E
    refl = np.full((H, W), BACK)
    patches = []
    for side, x0 in [("部屋", 0), ("窓の外", W // 2)]:
        order = rng.permutation(REFL)
        n = 0
        for gy in range(3):
            for gx in range(4):
                y = 16 + gy * (PATCH + 24)
                x = x0 + 16 + gx * (PATCH + 12)
                refl[y:y + PATCH, x:x + PATCH] = order[n]
                patches.append({"side": side, "refl": float(order[n]), "y": y, "x": x,
                                "dist_to_edge": int(abs((x + PATCH / 2) - W // 2))})
                n += 1
    lum = illum * refl * np.exp(rng.normal(0, NOISE, (H, W)))
    return lum, pd.DataFrame(patches)


def blur(img, sigma):
    rad = int(np.ceil(3 * sigma))
    xs = np.arange(-rad, rad + 1)
    w = np.exp(-0.5 * (xs / sigma) ** 2)
    w /= w.sum()
    p = np.pad(img, rad, mode="reflect")
    out = sum(wi * np.roll(p, xi, 1) for wi, xi in zip(w, xs))
    out = sum(wi * np.roll(out, xi, 0) for wi, xi in zip(w, xs))
    return out[rad:-rad, rad:-rad]


def to_code(d):
    """0〜1の画面の明るさを、256段階の値にする（暗い所に段を多く割る、2.2乗の決まり）"""
    return np.round(255 * np.clip(d, 0, 1) ** (1 / 2.2))


def global_curve(lum):
    c = np.exp(np.log(lum).mean())                    # 場面全体の明るさの目安（対数の平均）
    y = np.log1p(lum / c) / np.log1p(lum.max() / c)
    return np.round(255 * np.clip(y, 0, 1))          # 曲線の出力をそのまま256段階に


def local_adjust(lum, t, sigma):
    ll = np.log(lum)
    base = blur(ll, sigma)
    out = t * base + (ll - base)
    out = out - np.quantile(out, 0.995)              # 上の0.5%が白に届くようにそろえる
    return to_code(np.exp(out))


def patch_values(img, pt, inner=4):
    return np.array([img[y + inner:y + PATCH - inner, x + inner:x + PATCH - inner].mean() for y, x in zip(pt.y, pt.x)])


def pair_stats(true, shown, side):
    i, j = np.triu_indices(len(true), 1)
    dt, ds = true[i] - true[j], shown[i] - shown[j]
    tie = np.abs(ds) < TIE
    inv = (~tie) & (np.sign(dt) != np.sign(ds))
    cross = side[i] != side[j]
    return {"pairs": int(len(i)), "inverted_pct": r(100 * inv.mean()), "tied_pct": r(100 * tie.mean()),
            "cross_inverted_pct": r(100 * inv[cross].mean()), "within_inverted_pct": r(100 * inv[~cross].mean()),
            "cross_tied_pct": r(100 * tie[cross].mean()), "within_tied_pct": r(100 * tie[~cross].mean()),
            "cross_pairs": int(cross.sum()), "within_pairs": int((~cross).sum())}, (i, j, inv, tie, cross)


def pixel_pairs(rng, lum, shown, n=N_PIX_PAIRS):
    a = rng.integers(0, H * W, n)
    b = rng.integers(0, H * W, n)
    lt, sh = lum.ravel(), shown.ravel()
    ratio = np.maximum(lt[a], lt[b]) / np.minimum(lt[a], lt[b])
    ds = sh[a] - sh[b]
    dt = lt[a] - lt[b]
    tie = ds == 0
    inv = (~tie) & (np.sign(ds) != np.sign(dt))
    ya, xa, yb, xb = a // W, a % W, b // W, b % W
    dist = np.hypot(ya - yb, xa - xb)
    return ratio, dist, inv, tie


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    lum, pt = make_scene(rng, BASE["E"])
    g = global_curve(lum)
    l = local_adjust(lum, BASE["t"], BASE["sigma"])
    pt["true_lum"] = patch_values(lum, pt)
    pt["global_code"] = patch_values(g, pt)
    pt["local_code"] = patch_values(l, pt)
    pt.to_csv(DATA / "patches.csv", index=False, float_format="%.4f")

    sg, _ = pair_stats(pt.true_lum.to_numpy(), pt.global_code.to_numpy(), pt.side.to_numpy())
    sl, (pi, pj, pinv, ptie, pcross) = pair_stats(pt.true_lum.to_numpy(), pt.local_code.to_numpy(), pt.side.to_numpy())
    room, win = pt[pt.side == "部屋"], pt[pt.side == "窓の外"]
    spread = {"global_room_range": r(room.global_code.max() - room.global_code.min()),
              "local_room_range": r(room.local_code.max() - room.local_code.min()),
              "global_window_range": r(win.global_code.max() - win.global_code.min()),
              "local_window_range": r(win.local_code.max() - win.local_code.min()),
              "global_room_levels": int(len(np.unique(np.round(room.global_code)))),
              "local_room_levels": int(len(np.unique(np.round(room.local_code))))}
    pairs_csv = pd.DataFrame({"a": pi + 1, "b": pj + 1, "cross": pcross, "local_inverted": pinv, "local_tied": ptie})
    pairs_csv.to_csv(RES / "patch_pairs_local.csv", index=False)

    # 画素どうしの組
    rows = []
    for name, img in [("全体に同じ曲線", g), ("部分ごとに合わせる", l)]:
        ratio, dist, inv, tie = pixel_pairs(np.random.default_rng(SEED + 1), lum, img)
        for lo, hi, lab in [(1, 1.1, "1〜1.1倍"), (1.1, 2, "1.1〜2倍"), (2, 10, "2〜10倍"), (10, np.inf, "10倍以上")]:
            m = (ratio >= lo) & (ratio < hi)
            rows.append({"method": name, "by": "本当の明るさの比", "bin": lab, "pairs": int(m.sum()),
                         "inverted_pct": r(100 * inv[m].mean()), "tied_pct": r(100 * tie[m].mean())})
        for lo, hi, lab in [(0, 16, "16画素未満"), (16, 64, "16〜64画素"), (64, 192, "64〜192画素"), (192, np.inf, "192画素以上")]:
            m = (dist >= lo) & (dist < hi)
            rows.append({"method": name, "by": "2つの画素の距離", "bin": lab, "pairs": int(m.sum()),
                         "inverted_pct": r(100 * inv[m].mean()), "tied_pct": r(100 * tie[m].mean())})
        rows.append({"method": name, "by": "全体", "bin": "全体", "pairs": int(len(inv)),
                     "inverted_pct": r(100 * inv.mean()), "tied_pct": r(100 * tie.mean())})
    pix = pd.DataFrame(rows)
    pix.to_csv(RES / "pixel_pairs.csv", index=False)

    # t を変えたとき・ぼかしの広さを変えたとき（同じ場面）
    t_rows = []
    for t in [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]:
        s, _ = pair_stats(pt.true_lum.to_numpy(), patch_values(local_adjust(lum, t, BASE["sigma"]), pt), pt.side.to_numpy())
        t_rows.append({"t": t, **s})
    by_t = pd.DataFrame(t_rows)
    by_t.to_csv(RES / "by_t.csv", index=False)
    s_rows = []
    for sig in [4.0, 8.0, 16.0, 32.0, 48.0, 64.0, 96.0]:
        s, _ = pair_stats(pt.true_lum.to_numpy(), patch_values(local_adjust(lum, BASE["t"], sig), pt), pt.side.to_numpy())
        s_rows.append({"sigma": sig, **s})
    by_sigma = pd.DataFrame(s_rows)
    by_sigma.to_csv(RES / "by_sigma.csv", index=False)

    # 確かめ：E（100・1000・10000倍）× t（0.1・0.2・0.4）× ぼかしの広さ（8・32・64画素）
    grid = []
    for i, (E, t, sig) in enumerate(itertools.product([100.0, 1000.0, 10000.0], [0.1, 0.2, 0.4], [8.0, 32.0, 64.0])):
        gr = np.random.default_rng(SEED * 100 + i)
        lm, pg = make_scene(gr, E)
        tv = patch_values(lm, pg)
        sgl, _ = pair_stats(tv, patch_values(global_curve(lm), pg), pg.side.to_numpy())
        sl2, _ = pair_stats(tv, patch_values(local_adjust(lm, t, sig), pg), pg.side.to_numpy())
        grid.append({"E": E, "t": t, "sigma": sig, "global_inverted_pct": sgl["inverted_pct"],
                     "global_tied_pct": sgl["tied_pct"], "local_cross_inverted_pct": sl2["cross_inverted_pct"],
                     "local_within_inverted_pct": sl2["within_inverted_pct"], "local_tied_pct": sl2["tied_pct"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    out = {"settings": {"seed": SEED, "size": [H, W], "patches_per_side": 12, "refl": REFL, "back": BACK,
                        "noise_sd_log": NOISE, **BASE, "pixel_pairs": N_PIX_PAIRS, "tie_threshold": TIE},
           "dynamic_range": r(lum.max() / lum.min(), 0),
           "global": sg, "local": sl,
           "board_code_range": spread,
           "pixel_pairs": rows, "by_t": t_rows, "by_sigma": s_rows,
           "grid_range": {"global_inverted_max": r(grid.global_inverted_pct.max()),
                          "global_tied_min": r(grid.global_tied_pct.min()), "global_tied_max": r(grid.global_tied_pct.max()),
                          "local_cross_min": r(grid.local_cross_inverted_pct.min()),
                          "local_cross_max": r(grid.local_cross_inverted_pct.max()),
                          "local_within_min": r(grid.local_within_inverted_pct.min()),
                          "local_within_max": r(grid.local_within_inverted_pct.max()),
                          "local_cross_zero_count": int((grid.local_cross_inverted_pct == 0).sum()),
                          "local_any_inverted_count": int(((grid.local_cross_inverted_pct > 0) | (grid.local_within_inverted_pct > 0)).sum()),
                          "local_within_zero_count": int((grid.local_within_inverted_pct == 0).sum()),
                          "by_sigma": [{"sigma": sg_, "cross_min": r(gg.local_cross_inverted_pct.min()),
                                        "cross_max": r(gg.local_cross_inverted_pct.max()),
                                        "within_min": r(gg.local_within_inverted_pct.min()),
                                        "within_max": r(gg.local_within_inverted_pct.max()),
                                        "any_inverted": int(((gg.local_cross_inverted_pct > 0) | (gg.local_within_inverted_pct > 0)).sum())}
                                       for sg_, gg in grid.groupby("sigma")],
                          "global_tied_by_E": {str(int(E)): r(gg.global_tied_pct.max()) for E, gg in grid.groupby("E")}}}
    json.dump(out, open(RES / "a1136_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    figures(lum, g, l, pt, sg, sl, by_sigma, grid)
    print(json.dumps({k: v for k, v in out.items() if k not in ("pixel_pairs",)}, ensure_ascii=False, indent=1))
    print(pix.to_string())
    print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


def figures(lum, g, l, pt, sg, sl, by_sigma, grid):
    # 図1：2つの処理の画面と、入れかわった組の例
    room, win = pt[pt.side == "部屋"], pt[pt.side == "窓の外"]
    a = room.loc[room.refl.idxmax()]
    cand = win[(win.local_code < a.local_code) & (win.true_lum > a.true_lum)]
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.9))
    for ax, img, t in [(axs[0], g, "① 全体に同じ曲線"), (axs[1], l, f"② 部分ごとに合わせる（周りの明るさを{BASE['t']}倍に縮める）")]:
        ax.imshow(img, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        ax.set_title(t, fontsize=10.5)
        ax.set_xticks([]); ax.set_yticks([])
        ax.axvline(W // 2 - 0.5, color=ORANGE, lw=0.8, ls=":")
    if len(cand):
        b = cand.loc[cand.true_lum.idxmax()]
        for ax, key in [(axs[0], "global_code"), (axs[1], "local_code")]:
            for p, lab in [(a, "A"), (b, "B")]:
                ax.add_patch(plt.Rectangle((p.x - 1, p.y - 1), PATCH + 2, PATCH + 2, fill=False, ec=ORANGE, lw=1.6))
                ax.text(p.x + PATCH / 2, p.y + PATCH + 3, f"{lab}：{p[key]:.0f}", ha="center", va="top",
                        fontsize=8.5, color=ORANGE, fontweight="bold")
        fig.text(0.5, 0.0, f"本当の明るさは B（窓の外、白さ{b.refl}）が A（部屋、白さ{a.refl}）の{b.true_lum / a.true_lum:.1f}倍。"
                 f"数字は画面の値（0〜255）", ha="center", fontsize=9)
    fig.suptitle("左が部屋、右が窓の外（照明は1000倍）", fontsize=12)
    save(fig, "a1136_scene.png", SRC, y=-0.04)

    # 図2：入れかわり・同じ段階につぶれた割合
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    cats = ["部屋と窓の外の組\n入れかわり", "同じ側どうしの組\n入れかわり", "全部の組\n同じ段階につぶれた"]
    vals_g = [sg["cross_inverted_pct"], sg["within_inverted_pct"], sg["tied_pct"]]
    vals_l = [sl["cross_inverted_pct"], sl["within_inverted_pct"], sl["tied_pct"]]
    x = np.arange(3)
    for off, vals, col, lab in [(-0.18, vals_g, BLUE, "① 全体に同じ曲線"), (0.18, vals_l, ORANGE, "② 部分ごとに合わせる")]:
        ax.bar(x + off, vals, 0.36, color=col, label=lab)
        for xi, v in zip(x + off, vals):
            ax.text(xi, v + 0.4, f"{v:.2f}%", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x, cats, fontsize=9)
    ax.set_ylim(0, max(vals_g + vals_l) * 1.25 + 1)
    ax.set_ylabel("板の組のうちの割合（%）")
    ax.set_title(f"板24枚の{sg['pairs']}組で、本当の明るさの順と画面の順を比べた", fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1136_pairs.png", SRC)

    # 図3：ぼかしの広さを変えたとき、と27通り
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2))
    ax = axs[0]
    ax.plot(by_sigma.sigma, by_sigma.cross_inverted_pct, "o-", color=ORANGE, label="部屋と窓の外の組")
    ax.plot(by_sigma.sigma, by_sigma.within_inverted_pct, "s--", color=BLUE, label="同じ側どうしの組")
    ax.axvline(PATCH, color=GRAY, lw=0.8, ls=":")
    ax.text(PATCH + 1, ax.get_ylim()[1] * 0.02, "板の幅", fontsize=8, color=GRAY)
    for xx, yy in zip(by_sigma.sigma, by_sigma.cross_inverted_pct):
        if yy > 0:
            ax.text(xx, yy + 0.6, f"{yy:.2f}", fontsize=7.5, color=ORANGE, ha="center")
    ax.set_xlabel("周りの明るさを取るぼかしの広さ（画素）")
    ax.set_ylabel("入れかわった板の組（%）")
    ax.set_ylim(0, max(by_sigma.cross_inverted_pct.max(), by_sigma.within_inverted_pct.max()) * 1.25 + 1)
    ax.set_title(f"照明1000倍・t={BASE['t']}：広さで入れかわる組が変わる", fontsize=10.5)
    ax.legend(frameon=False, fontsize=8.5)
    ax = axs[1]
    cols = {8.0: BLUE, 32.0: ORANGE, 64.0: GREEN}
    for sig, gg in grid.groupby("sigma"):
        ax.scatter(gg.local_cross_inverted_pct, gg.local_within_inverted_pct, color=cols[sig], s=26,
                   label=f"ぼかしの広さ {int(sig)}画素")
    mx = max(grid.local_cross_inverted_pct.max(), grid.local_within_inverted_pct.max()) * 1.1 + 1
    ax.set_xlim(0, mx); ax.set_ylim(0, mx)
    ax.set_xlabel("部屋と窓の外の組の入れかわり（%）")
    ax.set_ylabel("同じ側どうしの組の入れかわり（%）")
    ax.set_title(f"置き方27通り（②）：入れかわりのあった置き方 {int(((grid.local_cross_inverted_pct > 0) | (grid.local_within_inverted_pct > 0)).sum())}通り", fontsize=10.5)
    ax.legend(frameon=False, fontsize=8.5)
    save(fig, "a1136_robust.png", SRC)


if __name__ == "__main__":
    main()
