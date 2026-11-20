"""802 星の分布はJの字になる。平均で「普通」の多さは見えるのか？（架空のデータ）

架空の店1,000軒。店ごとに「本当の星の分布」（来た人全員が星を付けたときの1〜5の割合）を置く。
本当の分布は「ふつうの山」と「両極端（星1か星5）」を混ぜたもの。両極端の割合（偏り）は店ごとに違う。
両極端の中の星5と星1の比は、店の平均が変わらないように決める。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 802
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 802）"
rng = np.random.default_rng(SEED)
N_SHOP = 1000
STARS = np.arange(1, 6)


def star_probs(mu, width=0.8):
    """平均が mu になる1〜5の山形の分布"""
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / width) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def true_dist(mu, w):
    """ふつうの山（1-w）と両極端（w）を混ぜる。両極端の中の星5の割合は (mu-1)/4 にして平均を mu に保つ"""
    theta = (mu - 1) / 4
    ext = np.zeros((len(mu), 5))
    ext[:, 0], ext[:, 4] = 1 - theta, theta
    return (1 - w)[:, None] * star_probs(mu) + w[:, None] * ext


def make_shops(rng, n=N_SHOP, w_max=0.6, w_link=False):
    mu = np.clip(rng.normal(3.9, 0.45, n), 2.5, 4.8)
    if w_link:  # 評価の低い店ほど両極端になりやすい
        w = np.clip(w_max * (4.8 - mu) / 2.3 + rng.normal(0, 0.08, n), 0, w_max)
    else:
        w = rng.uniform(0, w_max, n)
    p = true_dist(mu, w)
    n_rev = np.round(np.exp(rng.uniform(np.log(30), np.log(1000), n))).astype(int)
    cnt = np.array([rng.multinomial(k, pi) for k, pi in zip(n_rev, p)])
    obs = cnt / n_rev[:, None]
    df = pd.DataFrame({"shop_id": np.arange(1, n + 1), "n": n_rev, "polar": w,
                       "true_mean": (p * STARS).sum(1), "mean": (obs * STARS).sum(1)})
    for s in STARS:
        df[f"true_p{s}"] = p[:, s - 1]
    for s in STARS:
        df[f"cnt{s}"] = cnt[:, s - 1]
    df["true_mid"] = df[["true_p2", "true_p3", "true_p4"]].sum(1)
    df["true_low"] = df[["true_p1", "true_p2"]].sum(1)
    df["sd"] = np.sqrt((obs * (STARS[None, :] - df["mean"].values[:, None]) ** 2).sum(1))
    df["obs_low"] = obs[:, 0] + obs[:, 1]
    return df


def r2(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return float(1 - ((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def band_stats(df, lo=3.9, hi=4.1):
    b = df[df["mean"].between(lo, hi)]
    q = lambda s, a: round(float(s.quantile(a)), 3)
    return {"count": int(len(b)),
            "mid_p10": q(b.true_mid, .1), "mid_p90": q(b.true_mid, .9),
            "mid_min": round(float(b.true_mid.min()), 3), "mid_max": round(float(b.true_mid.max()), 3),
            "p1_p10": q(b.true_p1, .1), "p1_p90": q(b.true_p1, .9),
            "p3_p10": q(b.true_p3, .1), "p3_p90": q(b.true_p3, .9)}


def fit_stats(df):
    return {"r2_mid_by_mean": round(r2(df.true_mid.values, [df["mean"].values]), 3),
            "r2_mid_by_mean_sd": round(r2(df.true_mid.values, [df["mean"].values, df["sd"].values]), 3),
            "r2_low_by_mean": round(r2(df.true_low.values, [df["mean"].values]), 3),
            "r2_low_by_obs_low": round(r2(df.true_low.values, [df["obs_low"].values]), 3)}


def main():
    df = make_shops(rng)
    df.drop(columns=[c for c in df.columns if c.startswith("true_p") or c in ("true_mid", "true_low", "sd", "obs_low")]
            ).to_csv(DATA / "shops.csv", index=False, float_format="%.4f")

    # 1) 口コミ全部を合わせた星の分布（Jの字）
    tot = df[[f"cnt{s}" for s in STARS]].sum()
    agg = {int(s): round(float(tot.iloc[s - 1] / tot.sum()), 3) for s in STARS}

    # 2) 見かけの平均が3.9〜4.1の店の中で、本当の「普通（星2〜4）」の割合はどれだけ違うか
    band = band_stats(df)
    fit = fit_stats(df)

    # 3) 同じ平均4.0前後で、両極端の度合いがいちばん小さい店と大きい店（口コミ300件以上）
    c = df[df["mean"].between(3.95, 4.05) & (df.n >= 300)]
    lo_shop, hi_shop = c.loc[c.polar.idxmin()], c.loc[c.polar.idxmax()]
    pair = {}
    for k, r in [("calm", lo_shop), ("polar", hi_shop)]:
        o = np.array([r[f"cnt{s}"] for s in STARS]) / r.n
        pair[k] = {"shop_id": int(r.shop_id), "n": int(r.n), "mean": round(float(r["mean"]), 2),
                   "obs_share": [round(float(v), 3) for v in o],
                   "obs_mid": round(float(o[1:4].sum()), 3), "true_mid": round(float(r.true_mid), 3)}

    # 4) 確かめ：両極端の度合いの幅と、平均との結びつきを変える（店を作り直して20回の平均）
    sens = {}
    for name, kw in [("w_max=0.3", {"w_max": 0.3}), ("w_max=0.6（基本）", {"w_max": 0.6}),
                     ("w_max=0.9", {"w_max": 0.9}), ("評価の低い店ほど両極端", {"w_max": 0.6, "w_link": True})]:
        rows = []
        for r in range(20):
            g = make_shops(np.random.default_rng(SEED * 100 + r), 2000, **kw)
            b = band_stats(g); f = fit_stats(g)
            rows.append({**{k: b[k] for k in ("mid_p10", "mid_p90")}, **f})
        sens[name] = {k: round(float(np.mean([x[k] for x in rows])), 3) for k in rows[0]}
    pd.DataFrame(sens).T.to_csv(RES / "robustness.csv")

    out = {"total_reviews": int(tot.sum()), "aggregate_share_by_star": agg, "band_mean_3_9_to_4_1": band, "fit_all_shops": fit,
           "pair_same_mean_4_0": pair, "robustness_20reps": sens}
    json.dump(out, open(RES / "a802_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：口コミ全部の星の分布
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    v = [agg[s] * 100 for s in STARS]
    ax.bar([f"星{s}" for s in STARS], v, color=[ORANGE, GRAY, GRAY, LIGHT, BLUE])
    for i, x in enumerate(v):
        ax.text(i, x + 1, f"{x:.0f}%", ha="center", fontsize=10)
    ax.set_ylabel("口コミ全体に占める割合（%）"); ax.set_ylim(0, max(v) * 1.2)
    ax.set_title(f"店1,000軒の口コミを合わせると、星の分布はJの字になる（{int(tot.sum()):,}件）")
    save(fig, "a802_jshape.png", SRC)

    # 図2：同じ平均4.0の2軒
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6), sharey=True)
    for ax, (k, lab, col) in zip(axes, [("calm", "店A", BLUE), ("polar", "店B", ORANGE)]):
        s = pair[k]
        ax.bar([f"星{x}" for x in STARS], np.array(s["obs_share"]) * 100, color=col)
        for i, x in enumerate(s["obs_share"]):
            ax.text(i, x * 100 + 1, f"{x*100:.0f}%", ha="center", fontsize=9)
        ax.set_title(f"{lab}：平均{s['mean']:.2f}・{s['n']}件\n星2〜4は{s['obs_mid']*100:.0f}%", fontsize=11)
    axes[0].set_ylabel("その店の口コミに占める割合（%）")
    fig.suptitle("平均がほぼ同じでも、「普通」の多さはこれだけ違う", y=1.04, fontsize=13)
    save(fig, "a802_pair.png", SRC)

    # 図3：見かけの平均と本当の「普通」の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df["mean"], df.true_mid * 100, s=7, color=BLUE, alpha=.45, lw=0)
    ax.axvspan(3.9, 4.1, color=ORANGE, alpha=.12)
    ax.text(3.92, 5, f"平均3.9〜4.1の店：\n星2〜4は{band['mid_p10']*100:.0f}〜{band['mid_p90']*100:.0f}%\n（10〜90%の範囲）",
            fontsize=9, color=ORANGE)
    ax.set_xlabel("見かけの星の平均"); ax.set_ylabel("本当の「普通」（星2〜4）の割合（%）")
    ax.set_ylim(0, 100)
    ax.set_title("平均が同じ帯の中で、「普通」の割合は上下に大きく散らばる")
    save(fig, "a802_scatter.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
