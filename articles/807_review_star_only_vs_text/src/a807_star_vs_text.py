"""807 星だけの人と、文章も書いた人で、平均はどれだけ違うのか？（架空のデータ）

星を付けた人のうち、文章も書くかどうかは星によって変わると置く（不満な人ほど文章を書きやすい）。
正しい答えは「星を付けた人全員の平均」。文章付きの口コミだけ・星だけの口コミだけで平均を出すと、
どれだけずれるか、店の並びはどれだけ変わるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 807
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 807）"
STARS = np.arange(1, 6)
N_SHOP, REPS = 2000, 100
# 星ごとに「文章も書く」確率（作成者が置いた前提）
PATTERNS = {
    "基本（低い星で多く、星5でやや多い）": [0.70, 0.60, 0.35, 0.25, 0.30],
    "低い星ほど多い": [0.70, 0.55, 0.40, 0.30, 0.20],
    "高い星ほど多い": [0.20, 0.25, 0.30, 0.40, 0.50],
    "星で差がない（確かめ）": [0.35, 0.35, 0.35, 0.35, 0.35],
}
BASE = list(PATTERNS)[0]


def star_probs(mu):
    """平均が mu になる1〜5の分布（801 と同じ作り方）"""
    mu = np.atleast_1d(np.asarray(mu, float))
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / 0.9) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def exact(mu, pt):
    """本当の満足度 mu の店で、全員・星だけ・文章付きの平均（乱数なしの計算）"""
    p = star_probs(mu); pt = np.asarray(pt)
    pw, po = p * pt, p * (1 - pt)
    return {"all": (p * STARS).sum(1), "text": (pw * STARS).sum(1) / pw.sum(1),
            "star_only": (po * STARS).sum(1) / po.sum(1), "text_share": pw.sum(1),
            "low_share_all": p[:, :2].sum(1), "low_share_text": pw[:, :2].sum(1) / pw.sum(1)}


def make_shops(rng, pt, n=N_SHOP):
    true = np.clip(rng.normal(3.9, 0.35, n), 2.5, 4.8)
    n_rate = np.round(np.exp(rng.uniform(np.log(20), np.log(1000), n))).astype(int)
    P = star_probs(true)
    cnt = np.array([rng.multinomial(k, pi) for k, pi in zip(n_rate, P)])
    txt = rng.binomial(cnt, np.asarray(pt)[None, :])
    oth = cnt - txt
    f = lambda c: (c @ STARS) / np.maximum(c.sum(1), 1)
    return pd.DataFrame({"shop_id": np.arange(1, n + 1), "true": true, "n_all": cnt.sum(1), "n_text": txt.sum(1),
                         "mean_all": f(cnt), "mean_text": f(txt), "mean_star_only": f(oth)})


def top_hit(df, col, k=20):
    t = set(df.nlargest(k, "true").shop_id)
    return len(t & set(df.nlargest(k, col).shop_id)) / k


def main():
    rng = np.random.default_rng(SEED)

    # 1) 本当の満足度ごとの平均（乱数なしの計算）
    levels = np.array([3.0, 3.5, 4.0, 4.2, 4.5])
    e = exact(levels, PATTERNS[BASE])
    lev = pd.DataFrame({"true": levels, **{k: np.round(v, 3) for k, v in e.items()}})
    lev["gap_text_minus_all"] = (lev["text"] - lev["all"]).round(3)
    lev["gap_star_only_minus_text"] = (lev["star_only"] - lev["text"]).round(3)
    lev.to_csv(RES / "by_true_level.csv", index=False)

    # 2) 店2,000軒（1回分）と100回の繰り返し
    df = make_shops(rng, PATTERNS[BASE])
    df.to_csv(DATA / "shops.csv", index=False, float_format="%.4f")
    slope = lambda d, c: float(np.polyfit(d["true"], d[c], 1)[0])
    rows = []
    for name, pt in PATTERNS.items():
        for rep in range(REPS):
            g = make_shops(np.random.default_rng(SEED * 1000 + rep), pt)
            rows.append({"pattern": name, "rep": rep,
                         "gap_text_mean": float((g.mean_text - g.mean_all).mean()),
                         "gap_star_only_mean": float((g.mean_star_only - g.mean_all).mean()),
                         "share_text_lower_0_3": float((g.mean_text <= g.mean_all - 0.3).mean()),
                         "top20_all": top_hit(g, "mean_all"), "top20_text": top_hit(g, "mean_text"),
                         "top20_star_only": top_hit(g, "mean_star_only"),
                         "spearman_text": float(g[["true", "mean_text"]].rank().corr().iloc[0, 1]),
                         "spearman_all": float(g[["true", "mean_all"]].rank().corr().iloc[0, 1]),
                         "slope_text": slope(g, "mean_text"), "slope_all": slope(g, "mean_all")})
    sim = pd.DataFrame(rows)
    summ = sim.groupby("pattern", sort=False).mean(numeric_only=True).drop(columns="rep").round(3)
    summ.to_csv(RES / "patterns.csv")

    one = {"text_share_of_ratings": round(float(df.n_text.sum() / df.n_all.sum()), 3),
           "gap_text_mean": round(float((df.mean_text - df.mean_all).mean()), 3),
           "gap_star_only_mean": round(float((df.mean_star_only - df.mean_all).mean()), 3),
           "top20_text_n_median": float(df.nlargest(20, "mean_text").n_text.median()),
           "top20_all_n_median": float(df.nlargest(20, "mean_all").n_all.median())}
    out = {"text_prob_by_star": PATTERNS, "by_true_level_base": lev.to_dict("records"),
           "patterns_100reps": summ.reset_index().to_dict("records"), "one_draw": one}
    json.dump(out, open(RES / "a807_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：本当の満足度3.5の店の、星の内訳（全員・星だけ・文章付き）
    p = star_probs(3.5)[0]; pt = np.array(PATTERNS[BASE])
    shares = {"星を付けた人全員": p, "星だけの人": p * (1 - pt) / (p * (1 - pt)).sum(),
              "文章も書いた人": p * pt / (p * pt).sum()}
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = 0.27
    for j, ((lab, sh), c) in enumerate(zip(shares.items(), [GRAY, BLUE, ORANGE])):
        x = STARS + (j - 1) * w
        avg = (sh * STARS).sum()
        ax.bar(x, sh * 100, width=w, color=c, label=f"{lab}（平均 {avg:.2f}）")
    ax.set_xticks(STARS); ax.set_xticklabels([f"星{s}" for s in STARS])
    ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("本当の満足度3.5の店：文章付きの口コミだけ読むと、低い星が多く見える")
    save(fig, "a807_breakdown.png", SRC)

    # 図2：本当の満足度と、3つの平均
    grid = np.linspace(2.8, 4.7, 40)
    eg = exact(grid, PATTERNS[BASE])
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(grid, eg["all"], color=GRAY, lw=2, label="星を付けた人全員（正しい答え）")
    ax.plot(grid, eg["star_only"], color=BLUE, lw=1.6, label="星だけの人")
    ax.plot(grid, eg["text"], color=ORANGE, lw=1.6, label="文章も書いた人")
    ax.set_xlabel("店の本当の満足度"); ax.set_ylabel("平均の星")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("文章付きの平均は、本当の満足度が低い店ほど大きく下にずれる")
    save(fig, "a807_by_level.png", SRC)

    # 図3：書く確率の置き方を変えると（100回の平均）
    s = summ.reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    col = [ORANGE if v < 0 else BLUE for v in s.gap_text_mean]
    ax.barh(["文章を書く確率：" + t for t in s.pattern[::-1]], s.gap_text_mean[::-1], color=col[::-1])
    for i, v in enumerate(s.gap_text_mean[::-1]):
        ax.text(v + (0.01 if v >= 0 else -0.01), i, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
    ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-0.4, 0.3)
    ax.set_xlabel("文章付きの平均 − 全員の平均（店2,000軒の平均、100回の平均）")
    ax.set_title("ずれの向きと大きさは、どの星の人が文章を書きやすいかで決まる")
    save(fig, "a807_patterns.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
