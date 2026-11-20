"""821 色の順番と強さで、どの数字が目立つかは変わるのか？（架空のデータ）

架空の会社の12店×12か月の売上を、色の濃さで表す表（ヒートマップ）にする。
「目立ちやすさ」を、背景の色との明るさの差（CIELAB の L*、0＝黒〜100＝白）で測ると置き、
色の並び（明るい→暗い・暗い→明るい・虹色）と背景（白・黒）で、いちばん目立つ数字が大きい数字かを数える。
人に見せて確かめた実験ではなく、明るさの差を目立ちやすさの代わりに使う置き方である。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.patches import Rectangle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 821
SRC = "架空の会社の店別・月別売上（作成者が乱数で作成、seed 821）"
N_STORE, N_MONTH, TOPK, N_REP = 12, 12, 10, 200
PALETTES = [("Blues", "明るい→暗い（青の濃淡）"), ("viridis", "暗い→明るい（紫→黄）"), ("jet", "虹色（青→赤）")]
BGS = {"white": 100.0, "black": 0.0}


def srgb_to_lab(rgb):
    rgb = np.asarray(rgb, float)[..., :3]
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def make_sales(rng, store_sd=0.4):
    store = np.exp(rng.normal(0, store_sd, N_STORE))
    month = 1 + 0.15 * np.sin(2 * np.pi * (np.arange(N_MONTH) - 3) / 12)
    return np.round(1000 * store[:, None] * month[None, :] * np.exp(rng.normal(0, 0.1, (N_STORE, N_MONTH))))


def salience(v, cmap, bg, vmin=None, kind="L"):
    vmin = v.min() if vmin is None else vmin
    x = np.clip((v - vmin) / (v.max() - vmin), 0, 1)
    lab = srgb_to_lab(colormaps[cmap](x))
    if kind == "L":
        return np.abs(lab[..., 0] - BGS[bg])
    bg_lab = np.array([BGS[bg], 0, 0])
    return np.sqrt(((lab - bg_lab) ** 2).sum(-1))


def spearman(a, b):
    ra = pd.Series(a.ravel()).rank().values; rb = pd.Series(b.ravel()).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def topk_overlap(v, s, k=TOPK):
    fv, fs = v.ravel(), s.ravel()
    top_v = set(np.argsort(-fv, kind="stable")[:k]); top_s = set(np.argsort(-fs, kind="stable")[:k])
    return len(top_v & top_s) / k


def most_salient_pct(v, s):
    """いちばん目立つ1マスが、数字の大きい順で上から何%の位置か（0%＝最大、100%＝最小）"""
    fv, fs = v.ravel(), s.ravel()
    i = int(np.argmax(fs))
    return float((fv > fv[i]).sum() / (len(fv) - 1))


def main():
    rng = np.random.default_rng(SEED)
    v0 = make_sales(rng)
    pd.DataFrame(v0.astype(int), index=[f"店{i+1}" for i in range(N_STORE)],
                 columns=[f"{m+1}月" for m in range(N_MONTH)]).to_csv(DATA / "sales.csv")

    # 0) 色の並びごとの明るさ（理屈の値）
    xs = np.linspace(0, 1, 101)
    prof = {p: srgb_to_lab(colormaps[p](xs))[:, 0] for p, _ in PALETTES}
    prof_rows = pd.DataFrame({"pos": xs, **{p: np.round(prof[p], 2) for p in prof}})
    prof_rows.to_csv(RES / "lightness_profile.csv", index=False)
    lt = {p: {"L_min_value": round(float(prof[p][0]), 1), "L_max_value": round(float(prof[p][-1]), 1),
              "L_lightest": round(float(prof[p].max()), 1), "pos_lightest": float(xs[int(prof[p].argmax())]),
              "L_darkest": round(float(prof[p].min()), 1), "pos_darkest": float(xs[int(prof[p].argmin())])}
          for p in prof}

    # 1) 200回の売上の表で、目立つマスと大きい数字の合い方
    rows = []
    for r in range(N_REP):
        v = make_sales(np.random.default_rng(SEED * 1000 + r))
        for p, _ in PALETTES:
            for bg in BGS:
                for kind in ["L", "dE"]:
                    s = salience(v, p, bg, kind=kind)
                    rows.append({"rep": r, "palette": p, "bg": bg, "measure": kind,
                                 "spearman": spearman(v, s), "top10_overlap": topk_overlap(v, s),
                                 "most_salient_rank_pct": most_salient_pct(v, s)})
    sim = pd.DataFrame(rows)
    summ = sim.groupby(["measure", "bg", "palette"], sort=False)[["spearman", "top10_overlap", "most_salient_rank_pct"]] \
        .mean().round(3).reset_index()
    summ.to_csv(RES / "by_palette.csv", index=False)

    # 1b) 確かめ：店どうしの差の大きさ（数字の散らばり方）を変えると、虹色はどうなるか
    spread = {}
    for sd in [0.2, 0.4, 0.8]:
        rr = []
        for r in range(N_REP):
            v = make_sales(np.random.default_rng(SEED * 77 + r + int(sd * 10) * 10000), sd)
            for bg in BGS:
                sl = salience(v, "jet", bg)
                rr.append({"bg": bg, "top10_overlap": topk_overlap(v, sl), "most_salient_rank_pct": most_salient_pct(v, sl)})
        spread[str(sd)] = pd.DataFrame(rr).groupby("bg").mean().round(3).to_dict("index")

    # 2) 色の強さ：青の濃淡で、色の範囲を0から始めるか、最小値から始めるか（白い背景）
    strength = []
    for r in range(N_REP):
        v = make_sales(np.random.default_rng(SEED * 1000 + r))
        for name, vmin in [("最小値から", None), ("0から", 0.0)]:
            s = salience(v, "Blues", "white", vmin=vmin)
            strength.append({"vmin": name, "dark_share": float((s >= 50).mean()),
                             "gap_top_median": float(s.max() - np.median(s)),
                             "sal_min": float(s.min()), "sal_max": float(s.max())})
    strength = pd.DataFrame(strength).groupby("vmin", sort=False).mean().round(3).reset_index()
    strength.to_csv(RES / "blues_vmin.csv", index=False)

    # 3) 棒グラフの既定の10色（matplotlib の tab10）の明るさ
    from matplotlib.colors import to_hex
    cyc = [to_hex(c) for c in colormaps["tab10"].colors]
    lab10 = srgb_to_lab(np.array(colormaps["tab10"].colors))
    tab10 = [{"order": i + 1, "color": c, "L": round(float(l), 1), "sal_white": round(100 - float(l), 1)}
             for i, (c, l) in enumerate(zip(cyc, lab10[:, 0]))]

    one = {p: {"spearman_white": round(spearman(v0, salience(v0, p, "white")), 3),
               "top10_overlap_white": topk_overlap(v0, salience(v0, p, "white"))} for p, _ in PALETTES}
    out = {"setting": {"stores": N_STORE, "months": N_MONTH, "topk": TOPK, "reps": N_REP,
                       "salience": "背景との L* の差（確かめで Lab の距離 ΔE）", "bg_L": BGS},
           "lightness": lt, "by_palette_200reps": summ.to_dict("records"),
           "blues_vmin_200reps": strength.to_dict("records"), "jet_by_store_sd_200reps": spread, "tab10": tab10, "one_draw": one}
    json.dump(out, open(RES / "a821_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ売上の表を3つの色の並びで（白い背景）
    top3 = np.argsort(-v0.ravel(), kind="stable")[:3]
    fig, axs = plt.subplots(1, 3, figsize=(10.2, 3.9))
    for ax, (p, lab) in zip(axs, PALETTES):
        ax.imshow(v0, cmap=p, aspect="auto")
        for k in top3:
            i, j = divmod(int(k), N_MONTH)
            ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False, ec=ORANGE, lw=2))
        ax.set_xticks(range(0, 12, 3)); ax.set_xticklabels([f"{m+1}月" for m in range(0, 12, 3)], fontsize=8)
        ax.set_yticks(range(0, 12, 3)); ax.set_yticklabels([f"店{i+1}" for i in range(0, 12, 3)], fontsize=8)
        ax.set_title(f"{lab}\n上位10マスと目立つ10マスの重なり {one[p]['top10_overlap_white']*100:.0f}%", fontsize=10)
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.suptitle("同じ売上の表でも、色の並びで目立つマスが変わる（橙の枠：売上の上位3マス）", fontsize=12)
    fig.tight_layout()
    save(fig, "a821_heatmaps.png", SRC)

    # 図2：色の並びごとの明るさ
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for (p, lab), col in zip(PALETTES, [BLUE, GREEN, ORANGE]):
        ax.plot(xs * 100, prof[p], color=col, lw=2, label=lab)
    ax.axhline(100, color=GRAY, lw=.8, ls="--"); ax.text(99, 101.5, "白い背景の明るさ", fontsize=8, color=GRAY, ha="right")
    ax.set_xlabel("数字の位置（0＝表の最小、100＝表の最大）"); ax.set_ylabel("色の明るさ L*（0＝黒、100＝白）")
    ax.set_ylim(0, 108); ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.6, 0.02))
    ax.set_title("白い背景では、明るさが背景から遠い（暗い）色ほど目立つと置いた", fontsize=11)
    save(fig, "a821_lightness.png", SRC)

    # 図3：上位10マスと目立つ10マスの重なり（白・黒の背景）
    s = summ[summ.measure == "L"]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    w = .38
    for k, (bg, col, lab) in enumerate([("white", BLUE, "白い背景"), ("black", INK, "黒い背景")]):
        vals = [float(s[(s.bg == bg) & (s.palette == p)].top10_overlap.iloc[0]) * 100 for p, _ in PALETTES]
        x = np.arange(len(PALETTES)) + (k - .5) * w
        ax.bar(x, vals, w, color=col, label=lab)
        for xi, vi in zip(x, vals):
            ax.text(xi, vi + 2, f"{vi:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(range(len(PALETTES))); ax.set_xticklabels([l for _, l in PALETTES], fontsize=9)
    ax.set_ylabel("上位10マスと目立つ10マスの重なり（%）"); ax.set_ylim(0, 130)
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
    ax.set_title("同じ色の並びでも、背景の色で「目立つ数字」が逆になる（200回の平均）", fontsize=11)
    save(fig, "a821_overlap.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
