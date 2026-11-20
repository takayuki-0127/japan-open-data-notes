"""846 ハッシュタグの「効果」は、付けた投稿の選ばれ方で決まるのか？（架空のデータ）

架空のアカウントの投稿2,000本。投稿ごとに「中身の強さ」を置き、再生数はおもに中身の強さで決まる。
ハッシュタグの本当の効果は基本 0（付けても再生数は変わらない）と置く。
投稿する人は中身の強さを見積もり（見積もりには誤差がある）、自信のある投稿の上位4割にタグを付ける。
このとき「タグ付きの再生数は、付けない投稿の何倍か」を、素朴な比べ方・ジャンルをそろえた比べ方・
無作為に付けた比べ方で数え、本当の効果（1.00倍）とのずれを見る。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 846
SRC = "架空のアカウントの投稿（作成者が乱数で作成、seed 846）"
N_POST = 2000
REPS = 300
GENRE_MEAN = np.array([-0.5, 0.0, 0.5])   # ジャンル3つの中身の強さの平均
BASE = dict(judge_sd=1.0, tag_rate=0.4, beta=0.8, tau=0.0, noise=0.6, mode="上位に付ける")


def make_posts(rng, judge_sd=1.0, tag_rate=0.4, beta=0.8, tau=0.0, noise=0.6, mode="上位に付ける", n=N_POST):
    genre = rng.integers(0, 3, n)
    q = GENRE_MEAN[genre] + rng.normal(0, np.sqrt(1 - 1 / 6), n)   # 全体の標準偏差はおよそ1
    if mode == "無作為に付ける":
        tag = rng.random(n) < tag_rate
    else:
        s = q + rng.normal(0, judge_sd, n)            # 投稿する人の見積もり
        if mode == "上位に付ける":
            tag = s > np.quantile(s, 1 - tag_rate)
        else:                                          # 弱そうな投稿にタグで底上げを狙う
            tag = s < np.quantile(s, tag_rate)
    logv = np.log(1000) + beta * q + tau * tag + rng.normal(0, noise, n)
    views = np.maximum(1, np.round(np.exp(logv))).astype(int)
    return pd.DataFrame({"post_id": np.arange(1, n + 1), "genre": np.array(list("ABC"))[genre],
                         "strength": q, "tag": tag.astype(int), "views": views})


def naive(df):
    v, t = df["views"].to_numpy(), df["tag"].to_numpy() == 1
    return float(np.median(v[t]) / np.median(v[~t]))


def by_genre(df):
    """ジャンルごとに中央値の比を出し、投稿数で重みを付けて（対数で）平均する"""
    v, t, g = df["views"].to_numpy(), df["tag"].to_numpy() == 1, df["genre"].to_numpy()
    num, den = 0.0, 0.0
    for k in "ABC":
        m = g == k
        a, b = v[m & t], v[m & ~t]
        if len(a) < 5 or len(b) < 5:
            continue
        w = int(m.sum())
        num += w * np.log(np.median(a) / np.median(b))
        den += w
    return float(np.exp(num / den))


def run_many(rng_seed, reps=REPS, **kw):
    out = []
    for r in range(reps):
        df = make_posts(np.random.default_rng(rng_seed + r), **kw)
        out.append((naive(df), by_genre(df)))
    return np.array(out)


def main():
    t0 = time.time()
    res = {"base": BASE, "n_post": N_POST, "reps": REPS}

    # 1) 1回分（基本の置き方）
    df = make_posts(np.random.default_rng(SEED), **BASE)
    df.to_csv(DATA / "posts.csv", index=False, float_format="%.4f")
    t, u = df[df.tag == 1], df[df.tag == 0]
    res["one_run"] = {"n_tag": int(len(t)), "n_untag": int(len(u)),
                      "median_tag": float(t.views.median()), "median_untag": float(u.views.median()),
                      "ratio_naive": round(naive(df), 3), "ratio_by_genre": round(by_genre(df), 3),
                      "strength_mean_tag": round(float(t.strength.mean()), 3),
                      "strength_mean_untag": round(float(u.strength.mean()), 3),
                      "top100_tag_share": round(float(df.nlargest(100, "views").tag.mean()), 3)}

    # 2) 比べ方ごと（300回）
    base_arr = run_many(SEED * 1000, **BASE)
    rand_arr = run_many(SEED * 1000 + 50000, **{**BASE, "mode": "無作為に付ける"})
    methods = pd.DataFrame({
        "素朴に比べる": base_arr[:, 0],
        "ジャンルをそろえる": base_arr[:, 1],
        "無作為に付けて比べる": rand_arr[:, 0]})
    summ = methods.describe(percentiles=[0.05, 0.5, 0.95]).T[["mean", "5%", "50%", "95%"]].round(3)
    summ.columns = ["mean", "p05", "median", "p95"]
    summ.index.name = "method"
    summ.to_csv(RES / "methods.csv")
    res["methods"] = summ.reset_index().to_dict("records")
    res["share_naive_over_1_2"] = round(float((base_arr[:, 0] > 1.2).mean()), 3)
    res["share_random_over_1_2"] = round(float((rand_arr[:, 0] > 1.2).mean()), 3)

    # 3) 見積もりの正確さを変える（各300回）。本当の効果0
    rows = []
    for k, sd in enumerate([0.25, 0.5, 1.0, 2.0, 4.0]):
        for mode in ["上位に付ける", "下位に付ける"]:
            a = run_many(SEED * 1000 + 100000 + k * 1000 + (500 if mode == "下位に付ける" else 0),
                         **{**BASE, "judge_sd": sd, "mode": mode})
            rows.append({"mode": mode, "judge_sd": sd, "ratio_naive_median": round(float(np.median(a[:, 0])), 3),
                         "ratio_by_genre_median": round(float(np.median(a[:, 1])), 3)})
    a = run_many(SEED * 1000 + 50000, **{**BASE, "mode": "無作為に付ける"})
    rows.append({"mode": "無作為に付ける", "judge_sd": float("nan"),
                 "ratio_naive_median": round(float(np.median(a[:, 0])), 3),
                 "ratio_by_genre_median": round(float(np.median(a[:, 1])), 3)})
    judge = pd.DataFrame(rows)
    judge.to_csv(RES / "judge_accuracy.csv", index=False)
    res["judge_accuracy"] = judge.to_dict("records")

    # 4) 確かめ：ほかの置き方（各300回）
    rows = []
    cases = [("基本（効果0・上位4割・見積もり誤差1・中身の効き0.8）", {}),
             ("本当の効果 +10%", {"tau": np.log(1.10)}),
             ("本当の効果 −10%", {"tau": np.log(0.90)}),
             ("タグを付ける割合 2割", {"tag_rate": 0.2}),
             ("タグを付ける割合 6割", {"tag_rate": 0.6}),
             ("中身が再生数に効く強さ 0.4", {"beta": 0.4}),
             ("中身が再生数に効く強さ 1.2", {"beta": 1.2}),
             ("再生数のたまたまの振れ 0.3", {"noise": 0.3}),
             ("再生数のたまたまの振れ 1.0", {"noise": 1.0})]
    for k, (name, kw) in enumerate(cases):
        p = {**BASE, **kw}
        a = run_many(SEED * 1000 + 200000 + k * 1000, **p)
        r = run_many(SEED * 1000 + 300000 + k * 1000, **{**p, "mode": "無作為に付ける"})
        rows.append({"case": name, "true_ratio": round(float(np.exp(p["tau"])), 3),
                     "naive_median": round(float(np.median(a[:, 0])), 3),
                     "by_genre_median": round(float(np.median(a[:, 1])), 3),
                     "random_median": round(float(np.median(r[:, 0])), 3)})
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness.csv", index=False)
    res["robustness"] = rob.to_dict("records")

    # 図1：1回分の再生数の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bins = np.logspace(np.log10(df.views.min()), np.log10(df.views.max()), 40)
    ax.hist(u.views, bins=bins, color=LIGHT, label=f"タグなし（{len(u):,}本）")
    ax.hist(t.views, bins=bins, color=ORANGE, alpha=0.75, label=f"タグ付き（{len(t):,}本）")
    ax.set_xscale("log")
    ax.axvline(u.views.median(), color=BLUE, lw=1.5, ls="--")
    ax.axvline(t.views.median(), color=ORANGE, lw=1.5, ls="--")
    ax.text(u.views.median(), ax.get_ylim()[1] * 0.80, f"中央値 {u.views.median():,.0f} ", color=BLUE, fontsize=9, ha="right", va="top")
    ax.text(t.views.median(), ax.get_ylim()[1] * 0.72, f" 中央値 {t.views.median():,.0f}", color=ORANGE, fontsize=9, ha="left", va="top")
    ax.set_xlabel("1本の再生数（対数の目盛り）")
    ax.set_ylabel("投稿の本数")
    ax.set_title(f"タグの本当の効果は0なのに、タグ付きは{naive(df):.2f}倍に見える（1回分）")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "a846_views.png", SRC)

    # 図2：見積もりの正確さと見かけの効果
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for mode, c in [("上位に付ける", ORANGE), ("下位に付ける", BLUE)]:
        j = judge[judge["mode"] == mode]
        ax.plot(j.judge_sd, j.ratio_naive_median, "o-", color=c, label=("自信のある投稿4割に付ける" if mode == "上位に付ける" else "自信のない投稿4割に付ける（底上げ狙い）"))
    rv = judge[judge["mode"] == "無作為に付ける"].ratio_naive_median.iloc[0]
    ax.axhline(1.0, color=INK, lw=1)
    ax.axhline(rv, color=GREEN, lw=1.5, ls="--")
    ax.text(4.0, rv, f"無作為に付けた場合 {rv:.2f}倍", color=GREEN, fontsize=9, ha="right", va="bottom")
    ax.set_xscale("log", base=2)
    ax.set_xticks([0.25, 0.5, 1, 2, 4]); ax.set_xticklabels(["0.25\n（よく分かる）", "0.5", "1\n（基本）", "2", "4\n（ほぼ分からない）"])
    ax.set_xlabel("投稿する人の見積もりの誤差（標準偏差）")
    ax.set_ylabel("タグ付き÷タグなし（再生数の中央値）")
    ax.set_title("本当の効果0でも、見かけの効果は付け方で上にも下にも出る")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a846_judge.png", SRC, y=-0.06)

    # 図3：比べ方ごとの300回の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cols = list(methods.columns)
    parts = ax.boxplot([methods[c] for c in cols], vert=False, widths=0.5, patch_artist=True,
                       medianprops=dict(color=INK), showfliers=False, whis=(5, 95))
    for patch, c in zip(parts["boxes"], [ORANGE, LIGHT, GREEN]):
        patch.set_facecolor(c)
    ax.set_yticks(range(1, 4)); ax.set_yticklabels(cols)
    ax.axvline(1.0, color=INK, lw=1, ls="--")
    ax.text(1.0, 3.45, " 本当の効果（1.00倍）", fontsize=9, va="bottom")
    ax.invert_yaxis()
    ax.set_xlabel("タグ付き÷タグなし（再生数の中央値、300回。箱は25〜75%、ひげは5〜95%）")
    ax.set_title("ジャンルをそろえても、ずれは少ししか減らない")
    save(fig, "a846_methods.png", SRC)

    with open(RES / "a846_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"{time.time() - t0:.1f} 秒")


if __name__ == "__main__":
    main()
