"""809 星3.9と4.0の境目で、選ばれ方はどれだけ変わるのか？（架空のデータ）

架空の店3,000軒。店ごとに「本当の満足度」（来た人全員が星を付けたときの平均）を置き、
口コミの件数は 5〜500件（対数で一様）。表示する星は、見かけの平均を小数第1位で四捨五入したもの。
客は同じジャンルの店10軒を見比べて1軒を選ぶ。客の一部は「星4.0以上」に絞ってから選ぶ。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 809
SRC = "架空の店と客（作成者が乱数で作成、seed 809）"
rng = np.random.default_rng(SEED)
N_SHOP = 3000
STARS = np.arange(1, 6)
BETA = 2.0       # 表示の星が1つ上がると、選ばれやすさが e^2 ≒ 7.4倍（0.1上がると約1.22倍）
FILTER = 0.3     # 「星4.0以上」に絞ってから選ぶ客の割合
N_SET, SET_SIZE = 20000, 10


def star_probs(mu):
    """平均が mu になる1〜5の分布（801 と同じ作り方）"""
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / 0.9) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def draw_mean(rng, true, n):
    p = star_probs(true)
    # 件数 n の星の合計は多項分布から引ける
    cnt = np.array([rng.multinomial(k, pi) for k, pi in zip(n, p)])
    return (cnt * STARS).sum(1) / n


def shown(mean):
    """小数第1位で四捨五入（3.95 → 4.0）"""
    return np.floor(mean * 10 + 0.5 + 1e-9) / 10


def make_shops(rng, n=N_SHOP):
    true = np.clip(rng.normal(3.9, 0.35, n), 2.5, 4.8)
    n_rev = np.round(np.exp(rng.uniform(np.log(5), np.log(500), n))).astype(int)
    mean = draw_mean(rng, true, n_rev)
    return pd.DataFrame({"shop_id": np.arange(1, n + 1), "true": true, "n": n_rev, "mean": mean, "shown": shown(mean)})


def visit_share(rng, shown_star, f=FILTER, beta=BETA):
    """10軒を見比べる客を N_SET 組。店ごとに「見せられた回数あたりの選ばれた割合」を返す"""
    n = len(shown_star)
    sets = np.array([rng.choice(n, SET_SIZE, replace=False) for _ in range(N_SET)])
    s = shown_star[sets]
    w = np.exp(beta * (s - 4))
    p_all = w / w.sum(1, keepdims=True)
    wf = w * (s >= 4.0 - 1e-9)
    has = wf.sum(1, keepdims=True) > 0
    p_f = np.where(has, wf / np.where(has, wf.sum(1, keepdims=True), 1), p_all)
    p = (1 - f) * p_all + f * p_f
    chosen = np.bincount(sets.ravel(), weights=p.ravel(), minlength=n)
    seen = np.bincount(sets.ravel(), minlength=n)
    return chosen / np.maximum(seen, 1) * SET_SIZE  # 1 = 平均どおり


def by_shown(df, col="visit"):
    g = df.groupby("shown").agg(shops=("shop_id", "size"), true_mean=("true", "mean"), visit=(col, "mean"))
    return g


def main():
    df = make_shops(rng)
    df["visit"] = visit_share(np.random.default_rng(SEED + 1), df["shown"].values)
    df.round(4).to_csv(DATA / "shops.csv", index=False, float_format="%.4f")
    g = by_shown(df)
    g[(g.index >= 3.4) & (g.index <= 4.6)].round(3).to_csv(RES / "by_shown_star.csv")

    def ratio(a, b):
        return round(float(g.loc[a, "visit"] / g.loc[b, "visit"]), 3)

    jump = {"visit_4_0_over_3_9": ratio(4.0, 3.9), "visit_4_3_over_4_2": ratio(4.3, 4.2),
            "visit_3_8_over_3_7": ratio(3.8, 3.7),
            "true_3_9": round(float(g.loc[3.9, "true_mean"]), 3), "true_4_0": round(float(g.loc[4.0, "true_mean"]), 3),
            "true_diff": round(float(g.loc[4.0, "true_mean"] - g.loc[3.9, "true_mean"]), 3)}
    a, b = df[df.shown == 3.9], df[df.shown == 4.0]
    i, j = rng.choice(len(a), 50000), rng.choice(len(b), 50000)
    jump["P_3_9_truly_better"] = round(float((a["true"].values[i] > b["true"].values[j]).mean()), 3)
    jump["count_3_9"], jump["count_4_0"] = int(len(a)), int(len(b))
    jump["n_median_3_9"], jump["n_median_4_0"] = float(a.n.median()), float(b.n.median())

    # 2) 本当の満足度4.0ちょうどの店が「3.9以下」と表示される割合（件数ごと、2万回）
    r2 = np.random.default_rng(SEED + 2)
    flip = {}
    for k in [10, 30, 100, 300, 1000]:
        p = star_probs(np.array([4.0]))[0]
        m = (r2.multinomial(k, p, size=20000) * STARS).sum(1) / k
        flip[k] = {"share_shown_le_3_9": round(float((shown(m) <= 3.9).mean()), 3),
                   "share_shown_ge_4_0": round(float((shown(m) >= 4.0).mean()), 3)}
    # 本当4.0の店で、表示が3.9以下と4.0以上の店の選ばれ方
    t40 = df[df["true"].between(3.95, 4.05)]
    lo_v, hi_v = t40[t40.shown <= 3.9].visit.mean(), t40[t40.shown >= 4.0].visit.mean()
    same_true = {"count": int(len(t40)), "share_shown_le_3_9": round(float((t40.shown <= 3.9).mean()), 3),
                 "visit_shown_le_3_9": round(float(lo_v), 3), "visit_shown_ge_4_0": round(float(hi_v), 3),
                 "ratio": round(float(hi_v / lo_v), 3)}

    # 3) 確かめ：絞り込む客の割合 f と、星への敏感さ beta を変える
    sens = []
    for f in [0.0, 0.15, 0.3, 0.5]:
        for beta in [1.0, 2.0, 3.0]:
            v = visit_share(np.random.default_rng(SEED + 3), df["shown"].values, f, beta)
            gg = df.assign(v=v).groupby("shown").v.mean()
            sens.append({"filter_share": f, "beta": beta, "visit_4_0_over_3_9": round(float(gg[4.0] / gg[3.9]), 3),
                         "visit_4_3_over_4_2": round(float(gg[4.3] / gg[4.2]), 3)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"settings": {"shops": N_SHOP, "beta": BETA, "filter_share": FILTER, "choice_sets": N_SET,
                        "set_size": SET_SIZE},
           "jump_at_4_0": jump, "flip_true_4_0_by_n": flip, "true_3_95_to_4_05": same_true,
           "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a809_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：表示の星ごとの選ばれ方と本当の満足度
    gp = g[(g.index >= 3.4) & (g.index <= 4.5)]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(gp))
    ax.bar(x, gp.visit, color=[ORANGE if s >= 4.0 else BLUE for s in gp.index])
    ax.set_xticks(x); ax.set_xticklabels([f"{s:.1f}" for s in gp.index])
    ax.set_xlabel("表示の星"); ax.set_ylabel("選ばれやすさ（1＝平均）")
    for xi, (v, t) in enumerate(zip(gp.visit, gp.true_mean)):
        ax.text(xi, v + 0.03, f"{t:.2f}", ha="center", fontsize=8, color=INK)
    ax.text(0, gp.visit.max() * 0.95, "棒の上の数字：本当の満足度の平均", fontsize=9, color=GRAY)
    ax.set_title(f"表示3.9→4.0で選ばれやすさは{jump['visit_4_0_over_3_9']:.2f}倍、本当の差は{jump['true_diff']:.2f}")
    save(fig, "a809_jump.png", SRC)

    # 図2：本当の満足度と表示（境目の近く）
    near = df[df["true"].between(3.7, 4.3)]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    jit = np.random.default_rng(SEED + 9).uniform(-0.02, 0.02, len(near))
    col = np.where(near.shown >= 4.0, ORANGE, BLUE)
    ax.scatter(near["true"], near.shown + jit, c=col, s=8, alpha=.5, lw=0)
    ax.axhline(3.95, color=GRAY, lw=1, ls="--"); ax.axvline(4.0, color=GRAY, lw=1, ls=":")
    ax.text(3.71, 4.9, "橙＝表示4.0以上、青＝表示3.9以下", fontsize=9, color=INK)
    ax.set_xlabel("本当の満足度"); ax.set_ylabel("表示の星（重なりを避けて少しずらした）")
    ax.set_title("本当の満足度が同じでも、表示は3.9にも4.0にもなる")
    save(fig, "a809_scatter.png", SRC)

    # 図3：本当4.0の店が3.9以下と表示される割合（件数ごと）
    ks = list(flip.keys())
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    vals = [flip[k]["share_shown_le_3_9"] * 100 for k in ks]
    ax.bar([f"{k}件" for k in ks], vals, color=BLUE)
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
    ax.set_ylim(0, 60); ax.set_xlabel("口コミの件数"); ax.set_ylabel("「3.9以下」と表示される割合（%）")
    ax.set_title("本当の満足度4.0ちょうどの店が、3.9以下と表示される割合")
    save(fig, "a809_flip.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
