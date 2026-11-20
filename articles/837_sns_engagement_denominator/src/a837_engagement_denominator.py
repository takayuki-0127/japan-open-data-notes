"""837 反応率の分母（フォロワー・表示・再生）で、良い投稿は入れ替わるのか？（架空のデータ）

架空のアカウントの1年分の投稿300本。投稿ごとに「本当の反応のしやすさ」
（見た人が反応する確率）を作成者が置き、表示・再生・反応の数を乱数で作る。
反応の数を4つの分母（今のフォロワー数・投稿時のフォロワー数・表示回数・再生回数）で割り、
上位20本がどれだけ入れ替わるか、本当に反応されやすい上位20本にどれだけ当たるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 837
SRC = "架空のアカウントの投稿（作成者が乱数で作成、seed 837）"
N_POST = 300
K = 20
DENOMS = [("今のフォロワー数", "rate_now_follower"), ("投稿時のフォロワー数", "rate_follower"),
          ("表示回数", "rate_impression"), ("再生回数", "rate_view")]
BASE = {"spread": 0.8, "rho": 0.3, "ctr_sd": 0.4, "growth": 2.5}


def make_posts(rng, spread=0.8, rho=0.3, ctr_sd=0.4, growth=2.5, n=N_POST):
    day = np.sort(rng.integers(0, 365, n))
    follower = np.round(8000 * growth ** (day / 365)).astype(int)        # 投稿時のフォロワー数
    now_follower = int(round(8000 * growth))                              # 1年後（今）のフォロワー数
    lq = rng.normal(np.log(0.04), 0.35, n)                               # 本当の反応のしやすさ（対数）
    q = np.clip(np.exp(lq), 0.002, 0.3)
    zq = (lq - lq.mean()) / lq.std()
    boost = spread * (rho * zq + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, n))  # おすすめに載るかの振れ
    reach = np.clip(0.3 * np.exp(boost), 0.005, 20)
    imp = rng.poisson(follower * reach)
    ctr = np.clip(np.exp(rng.normal(np.log(0.25), ctr_sd, n)), 0.01, 0.9)  # サムネイル・冒頭で決まる再生の割合
    view = rng.binomial(imp, ctr)
    react = rng.binomial(view, q)
    df = pd.DataFrame({"post_id": np.arange(1, n + 1), "day": day, "follower": follower, "true_q": q,
                       "impression": imp, "view": view, "reaction": react})
    df["rate_now_follower"] = df.reaction / now_follower
    df["rate_follower"] = df.reaction / df.follower
    df["rate_impression"] = df.reaction / df.impression.clip(lower=1)
    df["rate_view"] = df.reaction / df.view.clip(lower=1)
    return df


def top_ids(df, col, k=K):
    return set(df.sort_values([col, "post_id"], ascending=[False, True]).post_id.iloc[:k])


def evaluate(df):
    tops = {c: top_ids(df, c) for _, c in DENOMS}
    tops["reaction"] = top_ids(df, "reaction")
    true_top = top_ids(df, "true_q")
    hit = {c: len(tops[c] & true_top) / K for c in tops}
    cols = [c for _, c in DENOMS]
    ov = {f"{a}|{b}": len(tops[a] & tops[b]) for i, a in enumerate(cols) for b in cols[i + 1:]}
    all4 = len(set.intersection(*[tops[c] for c in cols]))
    early = {c: float((df.set_index("post_id").loc[list(tops[c]), "day"] < 182).mean()) for c in cols}
    return hit, ov, all4, early


def run(setting, reps, seed0):
    H, O, A, E = [], [], [], []
    for r in range(reps):
        h, o, a, e = evaluate(make_posts(np.random.default_rng(seed0 + r), **setting))
        H.append(h); O.append(o); A.append(a); E.append(e)
    return pd.DataFrame(H).mean(), pd.DataFrame(O).mean(), float(np.mean(A)), pd.DataFrame(E).mean(), A


def main():
    rng = np.random.default_rng(SEED)
    df = make_posts(rng, **BASE)
    df.round(6).to_csv(DATA / "posts.csv", index=False)

    # 1) 基本の置き方で200回
    hit, ov, all4, early, all4_list = run(BASE, 200, SEED * 1000)
    name = dict((c, j) for j, c in DENOMS); name["reaction"] = "反応の数そのまま"
    hit_tab = pd.DataFrame({"denominator": [name[c] for c in hit.index], "hit20": hit.values.round(3),
                            "top20_early_half_share": [round(float(early.get(c, np.nan)), 3) for c in hit.index]})
    hit_tab.to_csv(RES / "hit_by_denominator.csv", index=False)
    ov_tab = pd.DataFrame([{"a": name[k.split("|")[0]], "b": name[k.split("|")[1]], "overlap20": round(float(v), 2)}
                           for k, v in ov.items()])
    ov_tab.to_csv(RES / "overlap_pairs.csv", index=False)

    # 2) 確かめ：置き方を変える（各200回）
    rob = []
    variants = [("基本", {}), ("おすすめの振れ 小（0.4）", {"spread": 0.4}), ("おすすめの振れ 大（1.2）", {"spread": 1.2}),
                ("おすすめが中身に沿う度合い 0", {"rho": 0.0}), ("おすすめが中身に沿う度合い 0.6", {"rho": 0.6}),
                ("再生の割合の散らばり 小（0.2）", {"ctr_sd": 0.2}), ("再生の割合の散らばり 大（0.6）", {"ctr_sd": 0.6}),
                ("フォロワーの伸び なし（1倍）", {"growth": 1.0}), ("フォロワーの伸び 4倍", {"growth": 4.0})]
    for i, (lab, ch) in enumerate(variants):
        st = dict(BASE); st.update(ch)
        h, o, a, e, _ = run(st, 200, SEED * 1000 if i == 0 else SEED * 100000 + i * 1000)
        rob.append({"setting": lab, "overlap_follower_view": round(float(o["rate_follower|rate_view"]), 2),
                    "overlap_impression_view": round(float(o["rate_impression|rate_view"]), 2),
                    "overlap_now_vs_follower": round(float(o["rate_now_follower|rate_follower"]), 2),
                    "all4_common": round(a, 2),
                    "hit_now_follower": round(float(h["rate_now_follower"]), 3),
                    "hit_follower": round(float(h["rate_follower"]), 3),
                    "hit_impression": round(float(h["rate_impression"]), 3), "hit_view": round(float(h["rate_view"]), 3),
                    "early_share_now_follower": round(float(e["rate_now_follower"]), 3)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    # 1回分（data/posts.csv）
    h1, o1, a1, e1 = evaluate(df)
    one = {"median_impression": int(df.impression.median()), "median_view": int(df.view.median()),
           "median_reaction": int(df.reaction.median()),
           "follower_first": int(df.follower.iloc[0]), "follower_last_post": int(df.follower.iloc[-1]),
           "follower_now": int(round(8000 * BASE["growth"])),
           "all4_common": a1, "overlap": {k: int(v) for k, v in o1.items()},
           "hit": {k: round(v, 3) for k, v in h1.items()},
           "spearman_follower_view": round(float(df.rate_follower.rank().corr(df.rate_view.rank())), 3),
           "spearman_impression_view": round(float(df.rate_impression.rank().corr(df.rate_view.rank())), 3)}
    out = {"setting": BASE, "n_post": N_POST, "k": K, "reps": 200,
           "hit20_mean": {name[k]: round(float(v), 3) for k, v in hit.items()},
           "overlap20_mean": {f"{name[k.split('|')[0]]}×{name[k.split('|')[1]]}": round(float(v), 2) for k, v in ov.items()},
           "all4_common_mean": round(all4, 2), "all4_common_min": int(min(all4_list)), "all4_common_max": int(max(all4_list)),
           "top20_early_half_share": {name[k]: round(float(v), 3) for k, v in early.items()},
           "robust_all4_range": [float(rob.all4_common.min()), float(rob.all4_common.max())],
           "robust_overlap_follower_view_range": [float(rob.overlap_follower_view.min()), float(rob.overlap_follower_view.max())],
           "robust_hit_view_range": [float(rob.hit_view.min()), float(rob.hit_view.max())],
           "robust_hit_follower_range": [float(rob.hit_follower.min()), float(rob.hit_follower.max())],
           "one_draw": one}
    json.dump(out, open(RES / "a837_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：投稿時のフォロワー数で割った率と、再生回数で割った率（1回分）の順位
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    rf = df.rate_follower.rank(ascending=False, method="first"); rv = df.rate_view.rank(ascending=False, method="first")
    tt = df.post_id.isin(top_ids(df, "true_q"))
    ax.scatter(rf[~tt], rv[~tt], s=9, color=LIGHT, lw=0, label="そのほかの投稿")
    ax.scatter(rf[tt], rv[tt], s=22, color=ORANGE, lw=0, label="本当に反応されやすい上位20本")
    ax.axvline(K + .5, color=GRAY, lw=.8, ls="--"); ax.axhline(K + .5, color=GRAY, lw=.8, ls="--")
    ax.set_xlim(0, N_POST + 5); ax.set_ylim(N_POST + 5, 0); ax.set_xlim(N_POST + 5, 0)
    ax.set_xlabel("フォロワー数（投稿時）で割った反応率の順位（右ほど上位）")
    ax.set_ylabel("再生回数で割った反応率の順位（上ほど上位）")
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.set_title(f"同じ300本でも、分母を変えると順位が入れ替わる（両方で上位20本は{o1['rate_follower|rate_view']}本）")
    save(fig, "a837_rank_scatter.png", SRC)

    # 図2：分母ごとの当たり
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    t = hit_tab.iloc[::-1]
    col = [BLUE if "再生" in d else GRAY for d in t.denominator]
    ax.barh(t.denominator, t.hit20 * 100, color=col)
    for i, v in enumerate(t.hit20 * 100):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("上位20本のうち、本当に反応されやすい上位20本に入っていた割合（%、200回の平均）")
    ax.set_title("「見た人が反応したか」を知りたいなら、分母は再生回数が近い")
    save(fig, "a837_hit.png", SRC)

    # 図3：確かめ（4つの分母で共通する上位の本数）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    r = rob.iloc[::-1]
    ax.barh(r.setting, r.all4_common, color=[BLUE if s == "基本" else LIGHT for s in r.setting])
    for i, v in enumerate(r.all4_common):
        ax.text(v + .2, i, f"{v:.1f}本", va="center", fontsize=9)
    ax.set_xlim(0, 20); ax.set_xlabel("4つの分母のどれでも上位20本に入った投稿の数（200回の平均）")
    ax.set_title("置き方を変えても、4つの分母で共通する上位はわずか")
    save(fig, "a837_robust.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
