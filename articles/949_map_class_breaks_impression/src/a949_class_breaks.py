"""949 色分けの区切り（等間隔・同じ件数）で、地図の印象はどう変わるのか？（架空のデータ）

架空の町を20×20の格子（400区域）に分け、区域ごとの「架空の店の1か月の来店者数（その区域に住む人）」を
5段階の色で塗る。区切り方は3つ：等間隔（最小〜最大を同じ幅に）、同じ件数（各段に同じ区域数）、対数で等間隔。
本当の来店者数（平均）は作成者が置き、実際の数はそれを平均にしたポアソン分布から引く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 949
SRC = "架空の町の区域と店の来店者数（作成者が乱数で作成、seed 949）"
G = 20
K = 5
SIGMA = 0.8       # 区域どうしの差（対数の標準偏差）
MEDIAN = 50
EAST_UP = 1.2     # 2か月目、東半分だけ本当の来店者数を1.2倍にする
REPS = 200
SCHEMES = ["等間隔", "同じ件数", "対数で等間隔"]


def smooth_field(rng):
    z = rng.normal(0, 1, (G + 6, G + 6))
    for _ in range(3):
        z = (z + np.roll(z, 1, 0) + np.roll(z, -1, 0) + np.roll(z, 1, 1) + np.roll(z, -1, 1)) / 5
    z = z[3:-3, 3:-3]
    return ((z - z.mean()) / z.std()).ravel()


def make_month1(rng, sigma=SIGMA):
    mu = MEDIAN * np.exp(sigma * smooth_field(rng))
    return mu, rng.poisson(mu)


def breaks(v, scheme, k=K):
    v = v.astype(float)
    if scheme == "等間隔":
        return np.linspace(v.min(), v.max(), k + 1)[1:-1]
    if scheme == "同じ件数":
        return np.quantile(v, np.arange(1, k) / k)
    lv = np.log(np.maximum(v, 1))
    return np.exp(np.linspace(lv.min(), lv.max(), k + 1)[1:-1])


def classify(v, br):
    return np.searchsorted(br, v.astype(float), side="right")


def neighbor_pairs():
    idx = np.arange(G * G).reshape(G, G)
    a = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
    b = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
    return a, b


PA, PB = neighbor_pairs()
EAST = (np.arange(G * G) % G) >= G // 2


def one_rep(rng, sigma=SIGMA, k=K):
    mu, v1 = make_month1(rng, sigma)
    mu2 = mu * np.where(EAST, EAST_UP, 1.0)
    v2 = rng.poisson(mu2)
    lo, hi = np.minimum(v1[PA], v1[PB]), np.maximum(v1[PA], v1[PB])
    ratio = hi / np.maximum(lo, 1)
    small = ratio < 1.1
    large = ratio >= 2
    out = {}
    for sc in SCHEMES:
        br1 = breaks(v1, sc, k)
        c1 = classify(v1, br1)
        c2_re = classify(v2, breaks(v2, sc, k))
        c2_fix = classify(v2, br1)
        cnt = np.bincount(c1, minlength=k) / len(c1)
        d = {"top_share": cnt[-1], "bottom_share": cnt[0],
             "small_diff_diff_color": float((c1[PA] != c1[PB])[small].mean()) if small.any() else np.nan,
             "large_diff_same_color": float((c1[PA] == c1[PB])[large].mean()) if large.any() else np.nan,
             "west_lighter_recomputed": float((c2_re < c1)[~EAST].mean()),
             "west_darker_recomputed": float((c2_re > c1)[~EAST].mean()),
             "east_darker_recomputed": float((c2_re > c1)[EAST].mean()),
             "west_lighter_fixed": float((c2_fix < c1)[~EAST].mean()),
             "west_darker_fixed": float((c2_fix > c1)[~EAST].mean()),
             "east_darker_fixed": float((c2_fix > c1)[EAST].mean()),
             "west_net_lighter_recomputed": float((c2_re < c1)[~EAST].mean() - (c2_re > c1)[~EAST].mean()),
             "west_net_lighter_fixed": float((c2_fix < c1)[~EAST].mean() - (c2_fix > c1)[~EAST].mean())}
        for key, val in d.items():
            out[f"{sc}|{key}"] = val
    out["share_pairs_small"] = small.mean()
    out["share_pairs_large"] = large.mean()
    return out, (mu, v1, v2)


def to_table(s):
    rows = []
    for sc in SCHEMES:
        r = {"scheme": sc}
        for key in s.index:
            if key.startswith(sc + "|"):
                r[key.split("|")[1]] = round(float(s[key]), 4)
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    # 1回分の町
    _, (mu, v1, v2) = one_rep(np.random.default_rng(SEED))
    df = pd.DataFrame({"row": np.arange(G * G) // G, "col": np.arange(G * G) % G, "east": EAST.astype(int),
                       "true_mean_month1": mu, "visitors_month1": v1, "visitors_month2": v2})
    one = {"min": int(v1.min()), "median": float(np.median(v1)), "max": int(v1.max()),
           "mean": round(float(v1.mean()), 1)}
    for sc in SCHEMES:
        br = breaks(v1, sc)
        df[f"class_{sc}"] = classify(v1, br) + 1
        one[f"breaks_{sc}"] = [round(float(b), 1) for b in br]
        one[f"counts_{sc}"] = np.bincount(classify(v1, br), minlength=K).tolist()
    df.to_csv(DATA / "town_example.csv", index=False, float_format="%.3f")

    sim = pd.DataFrame([one_rep(np.random.default_rng(SEED * 1000 + r))[0] for r in range(REPS)])
    s = sim.mean()
    tab = to_table(s)
    tab.to_csv(RES / "schemes_200reps.csv", index=False)

    # 確かめ：区域どうしの差 sigma × 段の数 k（9通り、各50回）
    sens = []
    for sg in [0.4, 0.8, 1.2]:
        for k in [4, 5, 7]:
            ss = pd.DataFrame([one_rep(np.random.default_rng(SEED * 7000 + int(sg * 10) * 100 + k * 1000 + r), sg, k)[0]
                               for r in range(50)]).mean()
            t = to_table(ss)
            for _, row in t.iterrows():
                d = {"sigma": sg, "k": k}
                d.update(row.to_dict())
                sens.append(d)
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_grid.csv", index=False)

    def rng_of(sc, col):
        x = sens[sens.scheme == sc][col]
        return [round(float(x.min()), 4), round(float(x.max()), 4)]

    out = {"setup": {"grid": f"{G}x{G}", "areas": G * G, "classes": K, "sigma_log": SIGMA, "median_mean": MEDIAN,
                     "east_up_month2": EAST_UP, "reps": REPS, "neighbor_pairs": int(len(PA))},
           "one_town": one,
           "mean_over_200": {"by_scheme": tab.to_dict("records"),
                             "share_pairs_small_ratio_lt_1_1": round(float(s.share_pairs_small), 4),
                             "share_pairs_large_ratio_ge_2": round(float(s.share_pairs_large), 4)},
           "sensitivity_ranges": {sc: {c: rng_of(sc, c) for c in ["top_share", "bottom_share", "small_diff_diff_color",
                                                                   "large_diff_same_color", "west_lighter_recomputed",
                                                                   "west_lighter_fixed", "east_darker_fixed",
                                                                   "west_net_lighter_recomputed", "west_net_lighter_fixed"]}
                                  for sc in SCHEMES}}
    json.dump(out, open(RES / "a949_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ数字を3つの区切りで塗った地図
    cmap = ListedColormap(plt.get_cmap("Blues")(np.linspace(0.12, 0.95, K)))
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.3))
    for ax, sc in zip(axes, SCHEMES):
        c = df[f"class_{sc}"].values.reshape(G, G)
        ax.imshow(c, cmap=cmap, vmin=.5, vmax=K + .5)
        ax.set_xticks([]); ax.set_yticks([])
        br = one[f"breaks_{sc}"]
        edges = [one["min"]] + br + [one["max"]]
        cnt = one[f"counts_{sc}"]
        ax.set_title(f"{sc}", fontsize=12)
        lab = "\n".join([f"段{i + 1}：{edges[i]:.0f}〜{edges[i + 1]:.0f}人（{cnt[i]}区域）" for i in range(K)][::-1])
        ax.text(0, -0.04, lab, transform=ax.transAxes, va="top", fontsize=8.5)
    fig.suptitle("同じ400区域の来店者数でも、区切り方で濃い区域の数が変わる（1回分の町、5段階、段5がいちばん濃い）", fontsize=12.5, y=1.0)
    save(fig, "a949_maps.png", SRC, y=-0.03)

    # 図2：差の小さい隣どうしが別の色／差の大きい隣どうしが同じ色
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xs = np.arange(3); w = .36
    a = tab.small_diff_diff_color.values * 100
    b = tab.large_diff_same_color.values * 100
    ax.bar(xs - w / 2, a, w, color=ORANGE, label="差が1割未満の隣どうしが、別の色")
    ax.bar(xs + w / 2, b, w, color=BLUE, label="2倍以上違う隣どうしが、同じ色")
    for x, v in zip(xs - w / 2, a):
        ax.text(x, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9)
    for x, v in zip(xs + w / 2, b):
        ax.text(x, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels(SCHEMES); ax.set_ylim(0, 100); ax.set_ylabel("%（200回の町の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("隣り合う区域の色の違いは、値の違いと合わないことがある")
    save(fig, "a949_neighbors.png", SRC)

    # 図3：2か月目（東半分だけ1.2倍）で、西半分の区域の色が変わった割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    w = .2
    items = [(-1.5 * w, "west_lighter_recomputed", ORANGE, "作り直す：1段以上薄く"),
             (-0.5 * w, "west_darker_recomputed", LIGHT, "作り直す：1段以上濃く"),
             (0.5 * w, "west_lighter_fixed", GRAY, "1か月目の区切りのまま：薄く"),
             (1.5 * w, "west_darker_fixed", "#d6d5d0", "1か月目の区切りのまま：濃く")]
    for off, col, c, lab in items:
        v = tab[col].values * 100
        ax.bar(xs + off, v, w, color=c, label=lab)
        for x, vv in zip(xs + off, v):
            ax.text(x, vv + .8, f"{vv:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels(SCHEMES); ax.set_ylim(0, 40)
    ax.set_ylabel("西半分の区域のうち（%、200回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("本当は変わらない西半分も、区切りを作り直すと薄く塗られやすい")
    save(fig, "a949_month2.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
