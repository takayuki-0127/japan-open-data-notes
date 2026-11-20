"""803 書く人は、とても満足した人と不満な人に偏る。書かなかった人の満足度は？（架空のデータ）

架空の店400軒・1軒あたり来た人3,000人。来た人全員に「付けるとしたら何点か」（本当の星）を置き、
口コミを書くかどうかは、その人の星で確率が変わる（とても満足した人と不満な人ほど書きやすい）。
来た人全員の平均（正しい答え）・口コミの平均・書かなかった人の平均を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 803
SRC = "架空の店と来た人・口コミ（作成者が乱数で作成、seed 803）"
rng = np.random.default_rng(SEED)
N_SHOP, N_VISIT = 400, 3000
STARS = np.arange(1, 6)
CURVES = {  # 星1〜5の人が口コミを書く確率
    "両端ほど書く（基本）": [0.10, 0.05, 0.02, 0.04, 0.10],
    "満足した人ほど書く": [0.02, 0.02, 0.03, 0.05, 0.10],
    "不満な人ほど書く": [0.12, 0.08, 0.04, 0.03, 0.03],
    "だれでも同じ（偏りなし）": [0.05, 0.05, 0.05, 0.05, 0.05],
}
BASE = "両端ほど書く（基本）"


def star_probs(mu, width=0.9):
    """平均が mu になる1〜5の山形の分布"""
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / width) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def make_shops(rng, n=N_SHOP):
    mu = np.clip(rng.normal(3.6, 0.4, n), 2.3, 4.7)
    visit = np.array([rng.multinomial(N_VISIT, p) for p in star_probs(mu)])
    return mu, visit


def write(rng, visit, rates):
    """星ごとに、書く人を二項分布で引く。rates は (5,) か (店数,5)"""
    r = np.broadcast_to(np.asarray(rates, float), visit.shape)
    return rng.binomial(visit, r)


def means(c):
    n = c.sum(1)
    return (c * STARS).sum(1) / np.maximum(n, 1), n


def spearman(a, b):
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def summarize(visit, post):
    vm, _ = means(visit)
    pm, pn = means(post)
    nm, _ = means(visit - post)
    slope = float(np.polyfit(vm, pm, 1)[0])
    return {"visitor_mean_avg": round(float(vm.mean()), 3), "posted_mean_avg": round(float(pm.mean()), 3),
            "nonwriter_mean_avg": round(float(nm.mean()), 3),
            "posted_minus_nonwriter_avg": round(float((pm - nm).mean()), 3),
            "bias_avg": round(float((pm - vm).mean()), 3), "abs_bias_avg": round(float(np.abs(pm - vm).mean()), 3),
            "share_abs_bias_ge_0_2": round(float((np.abs(pm - vm) >= 0.2).mean()), 3),
            "nonwriter_minus_visitor_max": round(float(np.abs(nm - vm).max()), 3),
            "slope_posted_on_visitor": round(slope, 2), "spearman": round(spearman(vm, pm), 3),
            "posts_per_shop_median": float(np.median(pn)), "write_rate": round(float(pn.sum() / visit.sum()), 3)}


def main():
    mu, visit = make_shops(rng)
    post = write(rng, visit, CURVES[BASE])
    vm, _ = means(visit); pm, pn = means(post); nm, _ = means(visit - post)
    d = pd.DataFrame({"shop_id": np.arange(1, N_SHOP + 1)})
    for s in STARS:
        d[f"visit{s}"] = visit[:, s - 1]
    for s in STARS:
        d[f"post{s}"] = post[:, s - 1]
    d.to_csv(DATA / "shops.csv", index=False)
    pd.DataFrame({"star": STARS, **{k: v for k, v in CURVES.items()}}).to_csv(DATA / "write_rates.csv", index=False)

    # 1) 来た人全体と口コミの星の分布
    vs, ps = visit.sum(0), post.sum(0)
    dist = {"visitors": [round(float(x), 3) for x in vs / vs.sum()], "posts": [round(float(x), 3) for x in ps / ps.sum()]}

    # 2) 基本の置き方での、店ごとのずれ
    base = summarize(visit, post)
    # 本当の平均の上位・下位で分けたずれ
    hi, lo = vm >= np.quantile(vm, .8), vm <= np.quantile(vm, .2)
    by_tier = {"top20pct": {"visitor": round(float(vm[hi].mean()), 3), "posted": round(float(pm[hi].mean()), 3),
                            "nonwriter": round(float(nm[hi].mean()), 3)},
               "bottom20pct": {"visitor": round(float(vm[lo].mean()), 3), "posted": round(float(pm[lo].mean()), 3),
                               "nonwriter": round(float(nm[lo].mean()), 3)}}
    # 星3の人：来た人と口コミでの割合
    share3 = {"visitors": dist["visitors"][2], "posts": dist["posts"][2]}

    # 3) 確かめ：書き方の偏りを変える（店を作り直して20回の平均）
    sens = {}
    for name, rates in CURVES.items():
        rows = []
        for r in range(20):
            g = np.random.default_rng(SEED * 100 + r)
            _, v = make_shops(g)
            pw = write(g, v, rates)
            row = summarize(v, pw)
            # 本当の平均の上位2割・下位2割の店での、口コミの平均−来た人全員の平均（傾きが1からずれる理由を見る）
            a, _ = means(v); b, _ = means(pw)
            row["bias_top20"] = float((b - a)[a >= np.quantile(a, .8)].mean())
            row["bias_bottom20"] = float((b - a)[a <= np.quantile(a, .2)].mean())
            rows.append(row)
        sens[name] = {k: round(float(np.mean([x[k] for x in rows])), 3) + 0.0 for k in
                      ("bias_avg", "abs_bias_avg", "share_abs_bias_ge_0_2", "slope_posted_on_visitor", "spearman",
                       "bias_top20", "bias_bottom20")}
    pd.DataFrame(sens).T.to_csv(RES / "robustness.csv")

    # 4) 店ごとに書かれ方が違う：3割の店は来た人全員に声をかけ、だれでも同じ5%が書く
    mixed = []
    for r in range(20):
        g = np.random.default_rng(SEED * 1000 + r)
        _, v = make_shops(g)
        ask = g.random(N_SHOP) < 0.3
        rates = np.where(ask[:, None], np.array(CURVES["だれでも同じ（偏りなし）"])[None, :],
                         np.array(CURVES[BASE])[None, :])
        p = write(g, v, rates)
        a, _ = means(v); b, _ = means(p)
        ra, rb = pd.Series(a).rank(ascending=False), pd.Series(b).rank(ascending=False)
        top_a = (a >= np.quantile(a, .75))
        mixed.append({"spearman": spearman(a, b),
                      "ask_rank_change": float((rb - ra)[ask & top_a].mean()),
                      "noask_rank_change": float((rb - ra)[~ask & top_a].mean())})
    mix = {k: round(float(np.mean([x[k] for x in mixed])), 2) for k in mixed[0]}

    out = {"n_shops": N_SHOP, "visitors_per_shop": N_VISIT, "share_by_star": dist, "share_star3": share3, "base": base, "by_tier": by_tier,
           "robustness_20reps": sens, "mixed_30pct_ask_all_20reps": mix}
    json.dump(out, open(RES / "a803_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：来た人全体と口コミの星の分布
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = np.arange(5)
    ax.bar(x - 0.2, np.array(dist["visitors"]) * 100, 0.4, color=GRAY, label="来た人全員（正しい答え）")
    ax.bar(x + 0.2, np.array(dist["posts"]) * 100, 0.4, color=BLUE, label="口コミを書いた人")
    for i in range(5):
        ax.text(i - 0.2, dist["visitors"][i] * 100 + 0.8, f"{dist['visitors'][i]*100:.0f}%", ha="center", fontsize=8.5)
        ax.text(i + 0.2, dist["posts"][i] * 100 + 0.8, f"{dist['posts'][i]*100:.0f}%", ha="center", fontsize=8.5,
                color=BLUE)
    ax.set_xticks(x, [f"星{s}" for s in STARS]); ax.set_ylabel("割合（%）")
    ax.set_ylim(0, max(dist["visitors"] + dist["posts"]) * 100 * 1.2)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("口コミでは星3の人が減り、星1と星5の人が増える（店400軒の合計）")
    save(fig, "a803_dist.png", SRC)

    # 図2：来た人全員の平均と口コミの平均
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(vm, pm, s=9, color=BLUE, alpha=.5, lw=0, label="口コミの平均")
    ax.scatter(vm, nm, s=9, color=ORANGE, alpha=.5, lw=0, label="書かなかった人の平均")
    lim = [min(vm.min(), pm.min()) - .1, max(vm.max(), pm.max()) + .1]
    ax.plot(lim, lim, color=GRAY, lw=1, ls="--"); ax.text(lim[1], lim[1] - 1.0, "点線：ずれなし", color=GRAY,
                                                          fontsize=9, ha="right")
    ax.set_xlabel("来た人全員の平均（正しい答え）"); ax.set_ylabel("平均")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"口コミの平均は、店どうしの差を{base['slope_posted_on_visitor']:.2f}倍に広げて見せる")
    save(fig, "a803_scatter.png", SRC)

    # 図3：書き方の偏りごとの、平均のずれ
    s = pd.DataFrame(sens).T
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.barh(s.index[::-1], s.abs_bias_avg[::-1], color=[GRAY, ORANGE, LIGHT, BLUE])
    for i, (v, sp) in enumerate(zip(s.abs_bias_avg[::-1], s.share_abs_bias_ge_0_2[::-1])):
        ax.text(v + .005, i, f"{v:.2f}（0.2以上ずれた店 {sp*100:.0f}%）", va="center", fontsize=9)
    ax.set_xlim(0, s.abs_bias_avg.max() * 1.9)
    ax.set_xlabel("口コミの平均と来た人全員の平均のずれ（店ごとの絶対値の平均、20回の平均）")
    ax.set_title("だれが書くかの偏りで、口コミの平均のずれ方が変わる")
    save(fig, "a803_curves.png", SRC, y=-0.05)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
