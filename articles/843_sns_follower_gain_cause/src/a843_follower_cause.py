"""843 フォロワーが増えた日の、本当の原因の投稿はどれか？（架空のデータ）

架空の SNS アカウントの180日。投稿ごとに「本当に連れてきたフォロワーの数」を置き、
その人数は投稿の日から何日かかけて少しずつ届く（半分になるまでの日数 h）。
日ごとのフォロワーの増加は、普段の増加（投稿と関係なく1日20人）＋届いた分。
「その日の増加を、その日の投稿の成果と読む」などの読み方で、本当に効いた投稿をどれだけ当てられるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import nnls
from scipy.stats import spearmanr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 843
SRC = "架空の SNS アカウント（作成者が乱数で作成、seed 843）"
DAYS = 180
LAGS = 14          # 投稿から14日（当日〜13日後）まで届く
BASE = 20.0        # 普段の増加（1日あたり）
MEDIAN_F = 30.0    # 1投稿が連れてくる人数の中央値
SIGMA_F = 1.0      # その散らばり（対数の標準偏差）
METHODS = ["その日の増加", "次の投稿までの増加", "届き方を置いて分ける"]


def lag_weights(h):
    w = 0.5 ** (np.arange(LAGS) / h)
    return w / w.sum()


def make_account(rng, h=1.5, p_post=0.5):
    post_days = np.flatnonzero(rng.random(DAYS) < p_post)
    f = np.exp(rng.normal(np.log(MEDIAN_F), SIGMA_F, len(post_days)))
    w = lag_weights(h)
    X = np.zeros((DAYS, len(post_days)))          # X[d, i]：投稿 i が d 日目に届ける割合
    for i, t in enumerate(post_days):
        k = np.arange(LAGS)
        ok = t + k < DAYS
        X[t + k[ok], i] = w[ok]
    contrib = X * f[None, :]                       # 投稿ごとの、日ごとの届く人数（期待値）
    same = np.zeros(DAYS)
    for i, t in enumerate(post_days):
        same[t] = contrib[t, i]
    lam = BASE + contrib.sum(1)
    gain = rng.poisson(lam)
    return post_days, f, X, contrib, same, gain


def estimates(post_days, gain, h_assumed):
    # 1) その日の増加：投稿した日の増加をそのまま、その投稿の成果とする
    e1 = gain[post_days].astype(float)
    # 2) 次の投稿までの増加：投稿の日から次の投稿の前日までの増加を合計し、普段の増加（1日20人、作成者が教えた値）を引く
    ends = np.r_[post_days[1:], DAYS]
    e2 = np.array([gain[s:e].sum() - BASE * (e - s) for s, e in zip(post_days, ends)], float)
    # 3) 届き方を置いて分ける：届き方の形（半減の日数）を置き、日ごとの増加を投稿ごとに分ける（非負の最小二乗、普段の増加も一緒に見積もる）
    w = lag_weights(h_assumed)
    X = np.zeros((DAYS, len(post_days)))
    for i, t in enumerate(post_days):
        k = np.arange(LAGS)
        ok = t + k < DAYS
        X[t + k[ok], i] = w[ok]
    A = np.c_[X, np.ones(DAYS)]
    coef, _ = nnls(A, gain.astype(float))
    e3 = coef[:-1]
    return {"その日の増加": e1, "次の投稿までの増加": e2, "届き方を置いて分ける": e3}, coef[-1]


def score(f, est, tail_cut):
    """最後の13日の投稿は届き切らないので、当たりの数え方からは外す"""
    keep = tail_cut
    ft, et = f[keep], est[keep]
    top_t = set(np.argsort(-ft)[:10]); top_e = set(np.argsort(-et)[:10])
    return {"spearman": float(spearmanr(ft, et)[0]), "top1": float(np.argmax(ft) == np.argmax(et)),
            "top10": len(top_t & top_e) / 10}


def run(rng, h=1.5, p_post=0.5, h_assumed=None):
    post_days, f, X, contrib, same, gain = make_account(rng, h, p_post)
    est, base_hat = estimates(post_days, gain, h if h_assumed is None else h_assumed)
    keep = post_days < DAYS - LAGS + 1
    out = {m: score(f, est[m], keep) for m in METHODS}
    # いちばん増えた日（届き切る前の最後の13日は外す）
    lam = BASE + contrib.sum(1)
    d = int(np.argmax(gain[:DAYS - LAGS + 1]))
    big = {"posted": float(d in set(post_days)), "share_base": BASE / lam[d], "share_same": same[d] / lam[d],
           "share_earlier": (contrib[d].sum() - same[d]) / lam[d]}
    if d in set(post_days):
        i = int(np.flatnonzero(post_days == d)[0])
        big["same_is_true_top"] = float(i == int(np.argmax(np.where(keep, f, -1))))
    return out, big, base_hat, (post_days, f, contrib, same, gain, est)


def main():
    rng = np.random.default_rng(SEED)
    # 1回分（data に置く）
    _, big1, base1, (post_days, f, contrib, same, gain, est) = run(rng)
    lam = BASE + contrib.sum(1)
    daily = pd.DataFrame({"day": np.arange(1, DAYS + 1), "gain": gain, "posted": np.isin(np.arange(DAYS), post_days).astype(int),
                          "exp_base": BASE, "exp_same_day_post": same, "exp_earlier_posts": contrib.sum(1) - same})
    daily.to_csv(DATA / "daily.csv", index=False, float_format="%.3f")
    posts = pd.DataFrame({"post_id": np.arange(1, len(post_days) + 1), "day": post_days + 1, "true_followers": f,
                          "est_same_day": est["その日の増加"], "est_until_next": est["次の投稿までの増加"],
                          "est_split": est["届き方を置いて分ける"]})
    posts.to_csv(DATA / "posts.csv", index=False, float_format="%.3f")

    # 2) 基本の置き方で300回
    rows, bigs, bases = [], [], []
    for r in range(300):
        o, b, bh, _ = run(np.random.default_rng(SEED * 1000 + r))
        for m in METHODS:
            rows.append({"rep": r, "method": m, **o[m]})
        bigs.append(b); bases.append(bh)
    sim = pd.DataFrame(rows)
    summ = sim.groupby("method", sort=False).mean(numeric_only=True).drop(columns="rep").round(3)
    summ.to_csv(RES / "methods.csv")
    bg = pd.DataFrame(bigs)
    big = {"posted_share": round(float(bg.posted.mean()), 3),
           "share_base": round(float(bg.share_base.mean()), 3), "share_same": round(float(bg.share_same.mean()), 3),
           "share_earlier": round(float(bg.share_earlier.mean()), 3),
           "same_is_true_top_given_posted": round(float(bg.same_is_true_top.dropna().mean()), 3)}

    # 3) 確かめ：届き方（半減の日数）と投稿の頻度を変える。分ける方法は、正しい形と、1.5日と決め打ちした形の両方
    sens = []
    for h in [0.5, 1.5, 4.0]:
        for p in [0.3, 0.5, 0.8]:
            acc = {m: [] for m in METHODS + ["届き方を1.5日と決め打ち"]}
            for r in range(100):
                s = SEED * 10 + r + int(h * 1000) + int(p * 100000)
                o, _, _, _ = run(np.random.default_rng(s), h, p)
                for m in METHODS:
                    acc[m].append(o[m]["top10"])
                o2, _, _, _ = run(np.random.default_rng(s), h, p, h_assumed=1.5)
                acc["届き方を1.5日と決め打ち"].append(o2["届き方を置いて分ける"]["top10"])
            sens.append({"half_life": h, "p_post": p, **{m: round(float(np.mean(v)), 3) for m, v in acc.items()}})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    w = lag_weights(1.5)
    out = {"setting": {"days": DAYS, "base_per_day": BASE, "median_followers_per_post": MEDIAN_F,
                       "sigma_log": SIGMA_F, "half_life_days": 1.5, "p_post": 0.5,
                       "share_day0": round(float(w[0]), 3), "share_day0_2": round(float(w[:3].sum()), 3)},
           "methods_300reps": summ.reset_index().to_dict("records"), "biggest_day_300reps": big,
           "base_hat_mean": round(float(np.mean(bases)), 2),
           "sensitivity_top10": sens.to_dict("records"),
           "one_draw": {"n_posts": int(len(post_days)), "biggest_day": int(np.argmax(gain[:DAYS - LAGS + 1]) + 1),
                        "biggest_gain": int(gain[:DAYS - LAGS + 1].max()),
                        "biggest_day_posted": bool(big1["posted"]),
                        "biggest_day_share_same": round(float(big1["share_same"]), 3),
                        "biggest_day_share_earlier": round(float(big1["share_earlier"]), 3)}}
    json.dump(out, open(RES / "a843_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の60日の増加の内訳（期待値）
    sl = slice(60, 120)
    dd = daily.iloc[sl]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = dd.day.values
    ax.bar(x, dd.exp_base, color=GRAY, alpha=.6, width=.85, label="普段の増加")
    ax.bar(x, dd.exp_same_day_post, bottom=dd.exp_base, color=ORANGE, width=.85, label="その日の投稿から")
    ax.bar(x, dd.exp_earlier_posts, bottom=dd.exp_base + dd.exp_same_day_post, color=BLUE, width=.85,
           label="前の日までの投稿から")
    ax.plot(x, dd.gain, "o", color=INK, ms=3, label="実際の増加")
    pd_ = dd[dd.posted == 1]
    ax.plot(pd_.day, np.full(len(pd_), -6), "^", color=ORANGE, ms=4, clip_on=False)
    ax.set_ylim(-8, dd.gain.max() * 1.2)
    ax.set_xlabel("日（▲は投稿した日）"); ax.set_ylabel("フォロワーの増加（人）")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left")
    ax.set_title("ある日の増加には、前の日までの投稿の分も混ざっている（61〜120日目）")
    save(fig, "a843_daily.png", SRC)

    # 図2：読み方ごとの当たり
    s = summ.reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.barh(s.method[::-1], s.top10[::-1] * 100, color=[GREEN, LIGHT, GRAY])
    for i, (v, rho) in enumerate(zip(s.top10[::-1] * 100, s.spearman[::-1])):
        ax.text(v + 1, i, f"{v:.0f}%（順位の相関 {rho:.2f}）", va="center", fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("上位10本のうち、本当の上位10本に入っていた割合（%、300回の平均）")
    ax.set_title("その日の増加で選ぶより、届き方を置いて分けたほうが当たる（届き方1.5日）")
    save(fig, "a843_methods.png", SRC, y=-0.06)

    # 図3：届き方の速さを変えると（投稿は2日に1本）
    t = sens[sens.p_post == 0.5]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for m, c, ls in [("その日の増加", GRAY, "-"), ("次の投稿までの増加", BLUE, "-"),
                     ("届き方を置いて分ける", GREEN, "-"), ("届き方を1.5日と決め打ち", GREEN, "--")]:
        ax.plot(t.half_life, t[m] * 100, ls, marker="o", color=c, label=m)
    ax.set_xticks([0.5, 1.5, 4.0]); ax.set_xticklabels(["0.5日（すぐ届く）", "1.5日（基本）", "4日（ゆっくり届く）"])
    ax.set_xlabel("投稿が連れてくる人の半分が届くまでの日数"); ax.set_ylim(0, 100)
    ax.set_ylabel("上位10本の当たり（%）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("ゆっくり届くほど、その日の増加では当たらなくなる（投稿は2日に1本）")
    save(fig, "a843_halflife.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
