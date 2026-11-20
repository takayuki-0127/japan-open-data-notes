"""845 同じ内容を2回投稿したときの差は、偶然でどこまで出るのか？（架空のデータ）

架空の動画アカウント。1本の再生数は、内容の本当の強さ（q）× その回の運（対数で標準偏差0.6）× まれなバズ（3%で3〜20倍）
の分だけ見込まれ、実際の回数はそのまわりで散らばる（ポアソン）。運とバズは投稿ごとに独立。
同じ内容（q が同じ）を2回投稿したときの差と、本当に2割強い内容を何本ずつ比べれば見分けられるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 845
SRC = "架空の動画アカウントの投稿（作成者が乱数で作成、seed 845）"
BASEV = 5000       # 本当の強さ1の内容の、運が中くらいのときの再生数
SIGMA = 0.6        # その回の運（対数の標準偏差）
P_BUZZ = 0.03      # バズの起きる確率
BUZZ = (3, 20)     # バズの倍率（対数で一様）
KS = [1, 2, 3, 5, 10, 20, 40]


def views(rng, q, size, sigma=SIGMA, p_buzz=P_BUZZ):
    luck = np.exp(rng.normal(0, sigma, size))
    buzz = np.where(rng.random(size) < p_buzz, np.exp(rng.uniform(np.log(BUZZ[0]), np.log(BUZZ[1]), size)), 1.0)
    return rng.poisson(BASEV * q * luck * buzz)


def pair_stats(rng, n=200000, sigma=SIGMA, p_buzz=P_BUZZ):
    v = views(rng, 1.0, (n, 2), sigma, p_buzz).astype(float)
    ratio = v.max(1) / np.maximum(v.min(1), 1)
    return ratio, v, {"median_ratio": round(float(np.median(ratio)), 3),
                      "p_ge_1_5": round(float((ratio >= 1.5).mean()), 3), "p_ge_2": round(float((ratio >= 2).mean()), 3),
                      "p_ge_3": round(float((ratio >= 3).mean()), 3), "p95_ratio": round(float(np.quantile(ratio, .95)), 3)}


def ab(rng, k, lift=0.2, n=20000, sigma=SIGMA, p_buzz=P_BUZZ):
    """強さ1（A）と強さ1+lift（B）を k 本ずつ。平均・中央値で B が上に出た割合と、A が1.3倍以上に見えた割合"""
    a = views(rng, 1.0, (n, k), sigma, p_buzz).astype(float)
    b = views(rng, 1.0 + lift, (n, k), sigma, p_buzz).astype(float)
    out = {}
    for name, f in [("平均", np.mean), ("中央値", np.median)]:
        fa, fb = f(a, 1), f(b, 1)
        out[name] = {"p_correct": round(float((fb > fa).mean()), 3),
                     "p_wrong_by_1_3x": round(float((fa >= 1.3 * fb).mean()), 3)}
    return out


def main():
    rng = np.random.default_rng(SEED)
    # 1) 同じ内容を2回
    ratio, v, base = pair_stats(rng)
    pd.DataFrame({"pair_id": np.arange(1, 1001), "views_1": v[:1000, 0].astype(int), "views_2": v[:1000, 1].astype(int)}) \
        .to_csv(DATA / "same_content_pairs.csv", index=False)
    # バズなしの場合（運だけ）
    _, _, nobuzz = pair_stats(np.random.default_rng(SEED + 1), p_buzz=0.0)

    # 2) 2割強い内容を k 本ずつ
    rows = []
    for k in KS:
        r = ab(np.random.default_rng(SEED * 100 + k), k)
        for m in r:
            rows.append({"k": k, "method": m, **r[m]})
    abdf = pd.DataFrame(rows)
    abdf.to_csv(RES / "ab_by_k.csv", index=False)
    # 5割強い内容でも
    rows50 = []
    for k in KS:
        r = ab(np.random.default_rng(SEED * 200 + k), k, lift=0.5)
        rows50.append({"k": k, "p_correct_median": r["中央値"]["p_correct"], "p_correct_mean": r["平均"]["p_correct"]})

    # 3) 確かめ：運の大きさとバズの確率を変える
    sens = []
    for sg in [0.3, 0.6, 0.9]:
        for pb in [0.0, 0.03, 0.1]:
            s0 = SEED * 10 + int(sg * 10) * 7 + int(pb * 100)
            _, _, ps = pair_stats(np.random.default_rng(s0), 100000, sg, pb)
            r1 = ab(np.random.default_rng(s0 + 1), 1, n=10000, sigma=sg, p_buzz=pb)
            r5 = ab(np.random.default_rng(s0 + 2), 5, n=10000, sigma=sg, p_buzz=pb)
            r20 = ab(np.random.default_rng(s0 + 3), 20, n=10000, sigma=sg, p_buzz=pb)
            sens.append({"sigma": sg, "p_buzz": pb, **ps, "p_correct_k1": r1["中央値"]["p_correct"],
                         "p_correct_k5_median": r5["中央値"]["p_correct"], "p_correct_k5_mean": r5["平均"]["p_correct"],
                         "p_correct_k20_median": r20["中央値"]["p_correct"]})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"setting": {"base_views": BASEV, "sigma_log": SIGMA, "p_buzz": P_BUZZ, "buzz_multiplier": list(BUZZ)},
           "same_content_twice": base, "same_content_twice_no_buzz": nobuzz,
           "ab_lift20": abdf.to_dict("records"), "ab_lift50": rows50, "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a845_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ内容2回の、多いほう÷少ないほう
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    lr = np.log2(np.clip(ratio, 1, 64))
    ax.hist(lr, bins=np.linspace(0, 5, 51), color=BLUE, alpha=.75, weights=np.full(len(lr), 100 / len(lr)))
    for x, lab in [(np.log2(2), "2倍"), (np.log2(base["p95_ratio"]), f"95%はこの内側（{base['p95_ratio']:.1f}倍）")]:
        ax.axvline(x, color=ORANGE, lw=1.2, ls="--")
        ax.text(x + 0.05, ax.get_ylim()[1] * 0.9, lab, color=ORANGE, fontsize=9)
    ticks = [1, 1.5, 2, 3, 5, 10, 20]
    ax.set_xticks(np.log2(ticks)); ax.set_xticklabels([f"{t:g}倍" for t in ticks])
    ax.set_xlim(0, 5)
    ax.set_xlabel("同じ内容の2回の再生数：多いほう ÷ 少ないほう（対数の目盛り）"); ax.set_ylabel("割合（%）")
    ax.set_title(f"同じ内容でも、{base['p_ge_2']*100:.0f}%は2倍以上の差になる（20万組）")
    save(fig, "a845_ratio.png", SRC)

    # 図2：2割強い内容を k 本ずつ比べたとき
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for m, c in [("平均", GRAY), ("中央値", BLUE)]:
        t = abdf[abdf.method == m]
        ax.plot(t.k, t.p_correct * 100, marker="o", color=c, label=f"再生数の{m}で比べる")
    ax.axhline(50, color=INK, lw=.8, ls=":"); ax.text(42, 50.5, "当てずっぽう", va="bottom", ha="right", fontsize=8.5)
    ax.axhline(80, color=ORANGE, lw=.8, ls="--"); ax.text(42, 80.5, "8割", va="bottom", ha="right", fontsize=8.5, color=ORANGE)
    ax.set_xscale("log"); ax.set_xticks(KS); ax.set_xticklabels([str(k) for k in KS])
    ax.set_xlabel("比べる本数（それぞれ k 本）"); ax.set_ylabel("本当に強いほうが上に出た割合（%）")
    ax.set_ylim(40, 100); ax.legend(frameon=False, fontsize=9, loc="upper left")
    p1 = abdf[(abdf.k == 1) & (abdf.method == "中央値")].p_correct.iloc[0]
    ax.set_title(f"2割強い内容でも、1本ずつ比べると当たるのは{p1*100:.0f}%")
    save(fig, "a845_ab.png", SRC)

    # 図3：確かめ（2倍以上の差になる割合）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(3)
    for j, (pb, c) in enumerate([(0.0, LIGHT), (0.03, BLUE), (0.1, ORANGE)]):
        t = sens[sens.p_buzz == pb].sort_values("sigma")
        ax.bar(x + (j - 1) * .26, t.p_ge_2 * 100, .25, color=c, label=f"バズの確率 {pb*100:.0f}%")
        for xi, vv in zip(x + (j - 1) * .26, t.p_ge_2 * 100):
            ax.text(xi, vv + 1, f"{vv:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(["運の揺れ 0.3", "0.6（基本）", "0.9"])
    ax.set_ylabel("同じ内容2回で2倍以上の差になる割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("運の揺れが大きいほど、同じ内容でも差が開く")
    save(fig, "a845_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
