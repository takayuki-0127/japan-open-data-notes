"""1126 色の値をそのまま平均して混ぜた色は、なぜ暗く濁って見えるのか？（架空のデータ）

色は「画面用の色の値」（0〜1。暗い所に段を多く割り振るため、光の量を約2.2乗の形で縮めて記録した値）で
持つと置く。2色を混ぜるとき、①色の値をそのまま平均する、②値をいったん光の量に戻して平均し、値に戻す、
の2つを比べ、見た明るさ・鮮やかさの物差し（作成者が置いた一般的な式）で差を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1126
SRC = "架空の色の板と縞の画像（作成者が式と乱数で作成、seed 1126）"
rng = np.random.default_rng(SEED)
WY = np.array([0.2126, 0.7152, 0.0722])                 # 光の量から明るさへの重み
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = M.sum(1)


def to_light(v, g="std"):
    v = np.clip(v, 0, 1)
    if g == "std":
        return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return v ** g


def to_value(l, g="std"):
    l = np.clip(l, 0, 1)
    if g == "std":
        return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)
    return l ** (1 / g)


def look(v, g="std"):
    """色の値 → 見た明るさ（0〜100）・鮮やかさ・色合いの角度"""
    lin = to_light(v, g)
    xyz = lin @ M.T / WHITE
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d * d) + 4 / 29)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1]); b = 200 * (f[..., 1] - f[..., 2])
    return L, np.hypot(a, b), np.degrees(np.arctan2(b, a)) % 360, a, b


def mix(c1, c2, w=0.5, g="std"):
    by_value = (1 - w) * c1 + w * c2
    by_light = to_value((1 - w) * to_light(c1, g) + w * to_light(c2, g), g)
    return by_value, by_light


def pair_stats(c1, c2, w=0.5, g="std"):
    v, l = mix(c1, c2, w, g)
    Lv, Cv, Hv, av, bv = look(v, g); Ll, Cl, Hl, al, bl = look(l, g)
    Yv, Yl = to_light(v, g) @ WY, to_light(l, g) @ WY
    L1, _, _, a1, b1 = look(c1, g); L2, _, _, a2, b2 = look(c2, g)
    dE12 = np.sqrt((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)
    return pd.DataFrame({"dL": Lv - Ll, "dC": Cv - Cl, "Yratio": Yv / np.maximum(Yl, 1e-9), "dE12": dE12,
                         "darker": Lv < Ll - 1e-9, "duller": Cv < Cl - 1e-9})


def main():
    out = {}
    # 1) 白と黒、赤と緑、などの例（50%ずつ）
    ex_pairs = {"白と黒": ([1, 1, 1], [0, 0, 0]), "赤と緑": ([1, 0, 0], [0, 1, 0]), "赤と青": ([1, 0, 0], [0, 0, 1]),
                "黄と青": ([1, 1, 0], [0, 0, 1]), "橙と水色": ([1, 0.5, 0], [0, 0.7, 1]), "灰50と灰60": ([.5, .5, .5], [.6, .6, .6])}
    ex = []
    for name, (a, b) in ex_pairs.items():
        a, b = np.array(a, float), np.array(b, float)
        v, l = mix(a, b)
        Lv, Cv, *_ = look(v); Ll, Cl, *_ = look(l)
        ex.append({"pair": name, "value_mix_255": "/".join(str(int(round(x * 255))) for x in v),
                   "light_mix_255": "/".join(str(int(round(x * 255))) for x in l),
                   "L_value_mix": round(float(Lv), 1), "L_light_mix": round(float(Ll), 1),
                   "C_value_mix": round(float(Cv), 1), "C_light_mix": round(float(Cl), 1),
                   "light_share_value_mix": round(float(to_light(v) @ WY), 4),
                   "light_share_light_mix": round(float(to_light(l) @ WY), 4)})
    ex = pd.DataFrame(ex)
    ex.to_csv(RES / "example_pairs.csv", index=False)

    # 2) 架空の色の板：でたらめな2色の組 20,000組
    n = 20000
    c1, c2 = rng.uniform(0, 1, (n, 3)), rng.uniform(0, 1, (n, 3))
    st = pair_stats(c1, c2)
    bins = [0, 10, 25, 50, 75, 300]
    lab = ["0〜10", "10〜25", "25〜50", "50〜75", "75以上"]
    st["dE_bin"] = pd.cut(st.dE12, bins, labels=lab, right=False)
    byb = st.groupby("dE_bin", observed=True).agg(pairs=("dL", "size"), dL_mean=("dL", "mean"), dL_min=("dL", "min"),
                                                  dC_mean=("dC", "mean"), duller_share=("duller", "mean"),
                                                  Yratio_mean=("Yratio", "mean")).round(4).reset_index()
    byb.to_csv(RES / "by_color_difference.csv", index=False)
    out["random_pairs"] = {"pairs": n, "darker_share": round(float(st.darker.mean()), 4),
                           "not_lighter_share": round(float((st.dL <= 1e-9).mean()), 4),
                           "dL_mean": round(float(st.dL.mean()), 3), "dL_p10": round(float(st.dL.quantile(.1)), 3),
                           "dL_min": round(float(st.dL.min()), 3), "dC_mean": round(float(st.dC.mean()), 3),
                           "duller_share": round(float(st.duller.mean()), 4),
                           "Yratio_mean": round(float(st.Yratio.mean()), 4),
                           "dL_le_minus5_share": round(float((st.dL <= -5).mean()), 4)}
    pd.DataFrame({"r1": c1[:200, 0], "g1": c1[:200, 1], "b1": c1[:200, 2], "r2": c2[:200, 0], "g2": c2[:200, 1],
                  "b2": c2[:200, 2]}).round(4).to_csv(DATA / "color_pairs_first200.csv", index=False)

    # 3) 縞の布に見立てた画像を4×4画素ずつまとめて縮める
    H, W = 64, 128
    yy, xx = np.mgrid[0:H, 0:W]
    stripes = {"白黒の1画素の縞": (np.array([1, 1, 1.]), np.array([0, 0, 0.])),
               "赤緑の1画素の縞": (np.array([0.9, 0.1, 0.1]), np.array([0.1, 0.7, 0.2])),
               "紺と黄の1画素の縞": (np.array([0.1, 0.15, 0.45]), np.array([0.95, 0.85, 0.2]))}
    shr = []
    imgs = {}
    for name, (a, b) in stripes.items():
        img = np.where((xx % 2 == 0)[..., None], a, b)
        sv = img.reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3))
        sl = to_value(to_light(img).reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3)))
        Lv, Cv, *_ = look(sv[0, 0]); Ll, Cl, *_ = look(sl[0, 0])
        shr.append({"stripe": name, "L_value_shrink": round(float(Lv), 1), "L_light_shrink": round(float(Ll), 1),
                    "C_value_shrink": round(float(Cv), 1), "C_light_shrink": round(float(Cl), 1),
                    "value_shrink_255": "/".join(str(int(round(x * 255))) for x in sv[0, 0]),
                    "light_shrink_255": "/".join(str(int(round(x * 255))) for x in sl[0, 0])})
        imgs[name] = (img, sv, sl)
    shr = pd.DataFrame(shr)
    shr.to_csv(RES / "stripe_shrink.csv", index=False)

    # 4) 赤から緑へのなめらかな境目（混ぜる割合0〜1）
    w = np.linspace(0, 1, 101)
    a, b = np.array([1, 0, 0.]), np.array([0, 1, 0.])
    gv = (1 - w)[:, None] * a + w[:, None] * b
    gl = to_value((1 - w)[:, None] * to_light(a) + w[:, None] * to_light(b))
    Lgv, Cgv, *_ = look(gv); Lgl, Cgl, *_ = look(gl)
    grad = pd.DataFrame({"w": w, "L_value": Lgv, "L_light": Lgl, "C_value": Cgv, "C_light": Cgl}).round(3)
    grad.to_csv(DATA / "red_green_edge.csv", index=False)
    out["red_green_edge"] = {"L_value_min": round(float(Lgv.min()), 1), "w_at_min": float(w[np.argmin(Lgv)]),
                             "L_light_min": round(float(Lgl.min()), 1), "L_red": round(float(Lgv[0]), 1),
                             "L_green": round(float(Lgv[-1]), 1)}

    # 5) 確かめ：値と光の量の関係（乗数）×色の選び方×混ぜる割合
    grid = []
    dists = {"でたらめ（0〜1）": (0, 1), "淡い色（0.6〜1）": (0.6, 1), "暗い色（0〜0.4）": (0, 0.4), "強い色（各色0か1寄り）": None}
    for g in ["std", 1.8, 2.2, 2.6]:
        for dn, rgv in dists.items():
            r = np.random.default_rng(SEED + 7)
            if rgv is None:
                p1 = np.clip(np.round(r.uniform(0, 1, (5000, 3))) + r.normal(0, 0.08, (5000, 3)), 0, 1)
                p2 = np.clip(np.round(r.uniform(0, 1, (5000, 3))) + r.normal(0, 0.08, (5000, 3)), 0, 1)
            else:
                p1, p2 = r.uniform(*rgv, (5000, 3)), r.uniform(*rgv, (5000, 3))
            for wt in [0.25, 0.5, 0.75]:
                s = pair_stats(p1, p2, wt, g)
                grid.append({"curve": "一般的な式（約2.2乗）" if g == "std" else f"{g}乗", "colors": dn, "w": wt,
                             "dL_mean": round(float(s.dL.mean()), 3), "dL_p10": round(float(s.dL.quantile(.1)), 3),
                             "darker_or_same_share": round(float((s.dL <= 1e-9).mean()), 4),
                             "duller_share": round(float(s.duller.mean()), 4), "dC_mean": round(float(s.dC.mean()), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"cases": int(len(grid)), "dL_mean_min": float(grid.dL_mean.min()), "dL_mean_max": float(grid.dL_mean.max()),
                   "darker_or_same_min": float(grid.darker_or_same_share.min()),
                   "duller_share_min": float(grid.duller_share.min()), "duller_share_max": float(grid.duller_share.max()),
                   "dL_mean_w50_by_curve": grid[(grid.w == 0.5) & (grid.colors == "でたらめ（0〜1）")].set_index("curve").dL_mean.to_dict(),
                   "dL_mean_w50_by_colors": grid[(grid.w == 0.5) & (grid.curve == "一般的な式（約2.2乗）")].set_index("colors").dL_mean.to_dict()}
    out["example_pairs"] = ex.to_dict("records")
    out["by_color_difference"] = byb.to_dict("records")
    out["stripe_shrink"] = shr.to_dict("records")
    json.dump(out, open(RES / "a1126_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：縞を縮めた色
    fig, axes = plt.subplots(3, 3, figsize=(7.4, 5.0))
    for i, (name, (img, sv, sl)) in enumerate(imgs.items()):
        r = shr.iloc[i]
        for j, (im, t) in enumerate([(img[:, :32], f"{name}（拡大）"), (sv, f"値で平均（明るさ{r.L_value_shrink}）"),
                                     (sl, f"光で平均（明るさ{r.L_light_shrink}）")]):
            ax = axes[i, j]; ax.imshow(np.clip(im, 0, 1), interpolation="nearest", aspect="auto")
            ax.set_xticks([]); ax.set_yticks([]); ax.set_title(t, fontsize=9.5)
    fig.suptitle("細い縞を4×4画素ずつまとめて縮めると、値で平均した色は暗い（明るさは0〜100）", fontsize=12, y=1.02)
    save(fig, "a1126_stripes.png", SRC)

    # 図2：赤→緑の境目の明るさ
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    ax.plot(w * 100, Lgv, color=ORANGE, lw=2, label="色の値をそのまま混ぜる")
    ax.plot(w * 100, Lgl, color=BLUE, lw=2, label="光の量に戻して混ぜる")
    ax.imshow(gv[None, :, :], extent=[0, 100, 3, 9], aspect="auto")
    ax.imshow(gl[None, :, :], extent=[0, 100, 11, 17], aspect="auto")
    ax.text(101, 6, "値", fontsize=9, va="center"); ax.text(101, 14, "光", fontsize=9, va="center")
    ax.set_ylim(0, 100); ax.set_xlim(0, 104)
    ax.set_xlabel("緑を混ぜる割合（%）"); ax.set_ylabel("見た明るさ（0〜100）")
    ax.legend(frameon=False, fontsize=9, loc="upper center")
    ax.set_title(f"赤から緑への境目：値で混ぜると真ん中が明るさ{out['red_green_edge']['L_value_min']}まで沈む")
    save(fig, "a1126_edge.png", SRC)

    # 図3：2色の差の大きさごとの暗くなり方
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    ax.bar(byb.dE_bin.astype(str), -byb.dL_mean, color=BLUE)
    for i, v in enumerate(-byb.dL_mean):
        ax.text(i, v + 0.2, f"{round(v, 4)}", ha="center", fontsize=9)
    ax.set_xlabel("混ぜる2色の見た目の差（明るさと色みの距離）"); ax.set_ylabel("値で混ぜた色が暗くなった分（平均）")
    ax.set_ylim(0, max(-byb.dL_mean) * 1.2)
    ax.set_title("離れた2色を混ぜるほど、値で混ぜた色は暗くなる（でたらめな2色×20,000組）", fontsize=12)
    save(fig, "a1126_by_difference.png", SRC)
    print(json.dumps({k: out[k] for k in ["random_pairs", "red_green_edge", "grid"]}, ensure_ascii=False, indent=1))
    print(ex.to_string()); print(byb.to_string()); print(shr.to_string())


if __name__ == "__main__":
    main()
