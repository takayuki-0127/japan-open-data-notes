"""801 星4.8（5件）と星4.3（500件）は、どちらが良い店か？（架空のデータ）

架空の店2,000軒。店ごとに「本当の満足度」（来た人全員が星を付けたときの平均）を置き、
口コミの件数は店ごとに 1〜1,000件（対数で一様）。1件の星は、本当の満足度に応じた1〜5の分布から引く。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 801
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 801）"
rng = np.random.default_rng(SEED)
N_SHOP = 2000
STARS = np.arange(1, 6)


def star_probs(mu):
    """平均が mu になる1〜5の分布（離散の正規に近い形、ばらつき一定）"""
    w = np.exp(-0.5 * ((STARS[None, :] - mu[:, None]) / 0.9) ** 2)
    p = w / w.sum(1, keepdims=True)
    # 平均を mu に合わせるため、mu をずらして数回合わせ直す
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / 0.9) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def make_shops(rng, n=N_SHOP, spread=0.35):
    true = np.clip(rng.normal(3.9, spread, n), 2.5, 4.8)
    n_rev = np.round(np.exp(rng.uniform(0, np.log(1000), n))).astype(int)
    p = star_probs(true)
    obs = np.array([rng.choice(STARS, size=k, p=pi).mean() for k, pi in zip(n_rev, p)])
    return pd.DataFrame({"shop_id": np.arange(1, n + 1), "true": true, "n": n_rev, "mean": obs})


def bayes_avg(df, m):
    """件数 m 件分の全体平均を足して割る（ベイズ平均）"""
    c = df["mean"].mul(df["n"]).sum() / df["n"].sum()
    return (df["mean"] * df["n"] + c * m) / (df["n"] + m), c


def precision_at(df, score, k=20):
    top_true = set(df.nlargest(k, "true").shop_id)
    top = df.loc[score.sort_values(ascending=False).index[:k], "shop_id"]
    return len(top_true & set(top)) / k


def main():
    df = make_shops(rng)
    df.to_csv(DATA / "shops.csv", index=False, float_format="%.4f")

    # 1) 並べ方ごとの上位20の当たり（店を作り直して200回）
    rows = []
    for r in range(200):
        g = make_shops(np.random.default_rng(SEED * 1000 + r))
        for name, sc in [("平均の星そのまま", g["mean"]),
                         ("件数で寄せる（m=10）", bayes_avg(g, 10)[0]),
                         ("件数で寄せる（m=30）", bayes_avg(g, 30)[0]),
                         ("件数で寄せる（m=100）", bayes_avg(g, 100)[0]),
                         ("件数の多い順", g["n"].astype(float))]:
            top = sc.sort_values(ascending=False).index[:20]
            rows.append({"rep": r, "method": name, "precision20": precision_at(g, sc),
                         "top20_median_n": float(g.loc[top, "n"].median()),
                         "top20_true_mean": float(g.loc[top, "true"].mean())})
    sim = pd.DataFrame(rows)
    summ = sim.groupby("method", sort=False).mean(numeric_only=True).drop(columns="rep").round(3)
    summ.to_csv(RES / "ranking_methods.csv")

    # 2) 星4.8（5件）と星4.3（500件）：見かけが同じ店どうしの本当の満足度
    big = []
    for r in range(40):
        g = make_shops(np.random.default_rng(SEED * 10 + r), 20000)
        big.append(g)
    big = pd.concat(big, ignore_index=True)
    a = big[(big.n.between(4, 6)) & (big["mean"] >= 4.7)]
    b = big[(big.n.between(400, 600)) & (big["mean"].between(4.25, 4.35))]
    pair = rng.choice(len(a), 20000), rng.choice(len(b), 20000)
    p_a_better = float((a["true"].values[pair[0]] > b["true"].values[pair[1]]).mean())
    res2 = {"A_count": int(len(a)), "B_count": int(len(b)),
            "A_true_mean": round(float(a["true"].mean()), 3), "A_true_p10": round(float(a["true"].quantile(.1)), 3),
            "A_true_p90": round(float(a["true"].quantile(.9)), 3),
            "B_true_mean": round(float(b["true"].mean()), 3), "B_true_p10": round(float(b["true"].quantile(.1)), 3),
            "B_true_p90": round(float(b["true"].quantile(.9)), 3), "P_A_better": round(p_a_better, 3)}

    # 2b) 店どうしの本当の差の大きさ（spread）を変えると
    sens = {}
    for sp in [0.2, 0.35, 0.5]:
        bb = pd.concat([make_shops(np.random.default_rng(SEED * 7 + r + int(sp * 100)), 20000, sp) for r in range(40)],
                       ignore_index=True)
        aa = bb[(bb.n.between(4, 6)) & (bb["mean"] >= 4.7)]
        cc = bb[(bb.n.between(400, 600)) & (bb["mean"].between(4.25, 4.35))]
        i, j = rng.choice(len(aa), 20000), rng.choice(len(cc), 20000)
        sens[str(sp)] = {"A_true_mean": round(float(aa["true"].mean()), 3),
                         "P_A_better": round(float((aa["true"].values[i] > cc["true"].values[j]).mean()), 3)}
    res2["by_spread"] = sens

    # 3) 件数ごとの見かけの平均の振れ（本当4.0の店）
    sd = {}
    for k in [1, 3, 5, 10, 30, 100, 500]:
        p = star_probs(np.array([4.0]))[0]
        m = rng.choice(STARS, size=(20000, k), p=p).mean(1)
        sd[k] = {"sd": round(float(m.std()), 3), "share_ge_4_5": round(float((m >= 4.5).mean()), 3)}

    # 1回分の店（data/shops.csv）での上位20
    b30, c = bayes_avg(df, 30)
    top_raw = df.loc[df["mean"].sort_values(ascending=False).index[:20]]
    one = {"overall_mean": round(float(c), 3), "raw_top20_n_le_5": int((top_raw.n <= 5).sum()),
           "raw_top20_precision": precision_at(df, df["mean"]), "bayes30_top20_precision": precision_at(df, b30)}

    out = {"ranking_methods_200reps": summ.reset_index().to_dict("records"), "pair_4_8_vs_4_3": res2,
           "sd_by_n_true4": sd, "one_draw": one}
    json.dump(out, open(RES / "a801_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：件数と見かけの平均（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df.n, df["mean"], s=7, color=BLUE, alpha=.45, lw=0)
    ax.set_xscale("log"); ax.set_xlabel("口コミの件数（対数の目盛り）"); ax.set_ylabel("見かけの星の平均")
    ax.axhline(4.5, color=ORANGE, lw=1, ls="--"); ax.text(1.05, 4.53, "星4.5", color=ORANGE, fontsize=9)
    ax.set_title("件数が少ない店ほど、星の平均は上にも下にも振れる（店2,000軒）")
    save(fig, "a801_scatter.png", SRC)

    # 図2：並べ方ごとの上位20の当たり
    s = summ.reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    col = [GRAY, BLUE, LIGHT, LIGHT, GRAY]
    ax.barh(s.method[::-1], s.precision20[::-1] * 100, color=col[::-1])
    for i, v in enumerate(s.precision20[::-1] * 100):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_xlabel("上位20軒のうち、本当の上位20軒に入っていた割合（%、200回の平均）"); ax.set_xlim(0, 100)
    ax.set_title("平均の星そのままより、件数で寄せた並べ方のほうが当たる")
    save(fig, "a801_precision.png", SRC)

    # 図3：4.8（5件）と4.3（500件）の本当の満足度
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bins = np.linspace(2.8, 4.85, 42)
    ax.hist(a["true"], bins=bins, color=ORANGE, alpha=.6, density=True, label="見かけ 星4.7以上・5件前後")
    ax.hist(b["true"], bins=bins, color=BLUE, alpha=.6, density=True, label="見かけ 星4.3・500件前後")
    ax.set_xlabel("本当の満足度（全員が星を付けたときの平均）"); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"5件前後で星4.7以上の店が、500件前後で星4.3の店より本当に良い確率は{p_a_better*100:.0f}%")
    save(fig, "a801_pair.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
