"""808 5段階と10段階と「おすすめ度0〜10」で、同じ満足度はどう見えるのか？（架空のデータ）

架空の店2,000軒。店ごとに「本当の満足度」（来た人全員の満足度の平均、100点満点）を置く。
1店につき200人が、同じ満足度のまま3つの聞き方（星1〜5・10段階1〜10・おすすめ度0〜10）に答える。
答えの目盛りへの当てはめ方（区切り）は作成者が置いた。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 808
SRC = "架空の店と回答（作成者が乱数で作成、seed 808）"
rng = np.random.default_rng(SEED)
N_SHOP, N_RESP = 2000, 200

# 区切り（満足度がこの値以上なら1段上がる）。基本は「人の答え方のくせ」を入れたもの
CUTS_BASE = {
    # 星：75点で星5。上の段を付けやすい
    "star5": [30, 45, 60, 75],
    # 10段階：10は95点以上、9は88点以上。上の段を付けにくい
    "ten": [20, 30, 40, 50, 60, 70, 80, 88, 95],
    # おすすめ度0〜10：満足度より厳しく、9は89点以上
    "rec": [17, 26, 35, 44, 53, 62, 71, 80, 89, 98],
}
# 確かめ用：くせのない等間隔の区切り
CUTS_EVEN = {
    "star5": [20, 40, 60, 80],
    "ten": [10, 20, 30, 40, 50, 60, 70, 80, 90],
    "rec": [100 / 11 * k for k in range(1, 11)],
}
LOW = {"star5": 1, "ten": 1, "rec": 0}


def answer(s, cuts, key):
    return LOW[key] + np.searchsorted(np.asarray(cuts[key]), s, side="right")


def nps(rec):
    """推奨者（9〜10）の割合 − 批判者（0〜6）の割合（%）"""
    return 100 * ((rec >= 9).mean(axis=-1) - (rec <= 6).mean(axis=-1))


def make_shops(rng, cuts, n=N_SHOP, k=N_RESP):
    mu = rng.normal(70, 8, n)
    sd = rng.uniform(8, 22, n)  # 店ごとの「人による満足度の散らばり」
    s = np.clip(mu[:, None] + sd[:, None] * rng.standard_normal((n, k)), 0, 100)
    st, te, re = (answer(s, cuts, key) for key in ["star5", "ten", "rec"])
    return pd.DataFrame({"shop_id": np.arange(1, n + 1), "true": s.mean(1), "spread": sd,
                         "star5_mean": st.mean(1), "ten_mean": te.mean(1),
                         "rec_mean": re.mean(1), "nps": nps(re)})


def topk_overlap(df, col, k=20):
    return len(set(df.nlargest(k, "true").shop_id) & set(df.nlargest(k, col).shop_id)) / k


def summarize(df):
    lin = (df.star5_mean - 1) * 9 / 4 + 1  # 1〜5を1〜10に直線で引き伸ばす
    return {
        "star5_mean_avg": round(float(df.star5_mean.mean()), 3),
        "ten_mean_avg": round(float(df.ten_mean.mean()), 3),
        "star5_x2_avg": round(float((df.star5_mean * 2).mean()), 3),
        "gap_x2_minus_ten": round(float((df.star5_mean * 2 - df.ten_mean).mean()), 3),
        "gap_linear_minus_ten": round(float((lin - df.ten_mean).mean()), 3),
        "rec_mean_avg": round(float(df.rec_mean.mean()), 3),
        "nps_avg": round(float(df.nps.mean()), 1),
        "share_star_ge_4": round(float((df.star5_mean >= 4).mean()), 3),
        "share_ten_ge_8": round(float((df.ten_mean >= 8).mean()), 3),
        "share_nps_gt_0": round(float((df.nps > 0).mean()), 3),
        "spearman_star_ten": round(float(df.star5_mean.rank().corr(df.ten_mean.rank())), 3),
        "spearman_star_nps": round(float(df.star5_mean.rank().corr(df.nps.rank())), 3),
        "top20_overlap_true": {c: topk_overlap(df, c) for c in ["star5_mean", "ten_mean", "nps"]},
    }


def main():
    df = make_shops(rng, CUTS_BASE)
    df.round(4).to_csv(DATA / "shops.csv", index=False, float_format="%.4f")
    base = summarize(df)

    # 1) 1軒の例：本当の満足度70点・散らばり15点の店に200人
    ex = np.clip(70 + 15 * np.random.default_rng(SEED + 1).standard_normal(N_RESP), 0, 100)
    ex_ans = {key: answer(ex, CUTS_BASE, key) for key in ["star5", "ten", "rec"]}
    example = {"true": round(float(ex.mean()), 2), "star5_mean": round(float(ex_ans["star5"].mean()), 2),
               "ten_mean": round(float(ex_ans["ten"].mean()), 2), "rec_mean": round(float(ex_ans["rec"].mean()), 2),
               "nps": round(float(nps(ex_ans["rec"])), 1),
               "star5_share_4_5": round(float((ex_ans["star5"] >= 4).mean()), 3),
               "ten_share_9_10": round(float((ex_ans["ten"] >= 9).mean()), 3),
               "rec_promoter": round(float((ex_ans["rec"] >= 9).mean()), 3),
               "rec_detractor": round(float((ex_ans["rec"] <= 6).mean()), 3)}

    # 2) 星の平均が同じくらい（3.95〜4.05）の店で、NPS はどれだけ違うか
    same = df[df.star5_mean.between(3.95, 4.05)]
    lo, hi = same.spread.quantile([.25, .75])
    same_star = {"count": int(len(same)), "nps_min": round(float(same.nps.min()), 1),
                 "nps_max": round(float(same.nps.max()), 1),
                 "nps_p10": round(float(same.nps.quantile(.1)), 1), "nps_p90": round(float(same.nps.quantile(.9)), 1),
                 "nps_small_spread": round(float(same[same.spread <= lo].nps.mean()), 1),
                 "nps_large_spread": round(float(same[same.spread >= hi].nps.mean()), 1),
                 "spread_q25": round(float(lo), 1), "spread_q75": round(float(hi), 1)}

    # 3) 回答の人数ごとの振れ（本当の満足度70点・散らばり15点の店を2万回）
    noise = {}
    r3 = np.random.default_rng(SEED + 3)
    for k in [30, 100, 300]:
        s = np.clip(70 + 15 * r3.standard_normal((20000, k)), 0, 100)
        st, re = answer(s, CUTS_BASE, "star5"), answer(s, CUTS_BASE, "rec")
        noise[k] = {"star5_sd": round(float(st.mean(1).std()), 3), "nps_sd": round(float(nps(re).std()), 2)}
    # 店どうしの差に比べた振れの大きさ（店どうしの標準偏差で割る）
    noise_rel = {k: {"star5": round(v["star5_sd"] / float(df.star5_mean.std()), 3),
                     "nps": round(v["nps_sd"] / float(df.nps.std()), 3)} for k, v in noise.items()}

    # 4) 確かめ：区切りを等間隔（くせなし）にすると
    even = summarize(make_shops(np.random.default_rng(SEED + 4), CUTS_EVEN))

    # 5) 確かめ：店ごとの散らばりを全店15点にそろえると、星とNPSの順位は近づくか
    r5 = np.random.default_rng(SEED + 5)
    mu = r5.normal(70, 8, N_SHOP)
    s = np.clip(mu[:, None] + 15 * r5.standard_normal((N_SHOP, N_RESP)), 0, 100)
    d5 = pd.DataFrame({"shop_id": np.arange(1, N_SHOP + 1), "true": s.mean(1),
                       "star5_mean": answer(s, CUTS_BASE, "star5").mean(1),
                       "nps": nps(answer(s, CUTS_BASE, "rec"))})
    fixed = {"spearman_star_nps": round(float(d5.star5_mean.rank().corr(d5.nps.rank())), 3),
             "top20_overlap_true": {c: topk_overlap(d5, c) for c in ["star5_mean", "nps"]}}

    out = {"cuts_base": CUTS_BASE, "example_shop": example, "base": base, "same_star_4_0": same_star,
           "noise_by_n": noise, "noise_relative_to_shop_sd": noise_rel,
           "robust_even_cuts": even, "robust_fixed_spread": fixed}
    json.dump(out, open(RES / "a808_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pd.DataFrame([{"setting": "基本（答え方のくせあり）", **{k: v for k, v in base.items() if k != "top20_overlap_true"}},
                  {"setting": "区切りを等間隔", **{k: v for k, v in even.items() if k != "top20_overlap_true"}}]
                 ).to_csv(RES / "scale_summary.csv", index=False)

    # 図1：同じ200人の答え（3つの聞き方）
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4), sharey=True)
    for ax, key, title, xs in [(axes[0], "star5", "星1〜5", range(1, 6)), (axes[1], "ten", "10段階1〜10", range(1, 11)),
                               (axes[2], "rec", "おすすめ度0〜10", range(0, 11))]:
        cnt = np.array([(ex_ans[key] == x).mean() * 100 for x in xs])
        col = [BLUE] * len(cnt)
        if key == "rec":
            col = [ORANGE if x <= 6 else (GREEN if x >= 9 else GRAY) for x in xs]
        ax.bar(list(xs), cnt, color=col)
        ax.set_title(title, fontsize=11); ax.set_xticks(list(xs))
    axes[0].set_ylabel("回答の割合（%）")
    axes[0].text(1, 52, f"平均 {example['star5_mean']:.2f}", fontsize=9)
    axes[1].text(1, 52, f"平均 {example['ten_mean']:.2f}", fontsize=9)
    axes[2].text(0, 52, f"NPS {example['nps']:.0f}", fontsize=9)
    axes[2].text(0, 46, "橙＝批判者（0〜6）\n緑＝推奨者（9〜10）", fontsize=8, color=INK, va="top")
    axes[0].set_ylim(0, 58)
    fig.suptitle("同じ200人（満足度の平均70点）が、3つの聞き方に答えると", fontsize=13, y=1.02)
    save(fig, "a808_example.png", SRC)

    # 図2：星の平均と10段階の平均（店2,000軒）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df.star5_mean, df.ten_mean, s=6, color=BLUE, alpha=.4, lw=0, label="店（10段階の平均）")
    xs = np.linspace(df.star5_mean.min(), df.star5_mean.max(), 50)
    ax.plot(xs, xs * 2, color=ORANGE, lw=1.5, label="星の平均×2")
    ax.plot(xs, (xs - 1) * 9 / 4 + 1, color=GRAY, lw=1.5, ls="--", label="1〜5を1〜10に引き伸ばし")
    ax.set_xlabel("星1〜5の平均"); ax.set_ylabel("10段階1〜10の平均")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"星の平均×2は、10段階の平均より{base['gap_x2_minus_ten']:.2f}点高い（置いた答え方のくせのもと。等間隔なら{even['gap_x2_minus_ten']:.2f}点）", fontsize=11)
    save(fig, "a808_convert.png", SRC)

    # 図3：星の平均と NPS（散らばりで色分け）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    sc = ax.scatter(df.star5_mean, df.nps, c=df.spread, cmap="viridis", s=7, alpha=.7, lw=0)
    cb = fig.colorbar(sc, ax=ax); cb.set_label("人による満足度の散らばり（点）")
    ax.axvspan(3.95, 4.05, color=ORANGE, alpha=.15)
    ax.set_xlabel("星1〜5の平均"); ax.set_ylabel("NPS（推奨者% − 批判者%）")
    ax.set_title(f"星の平均が4.0前後の店でも、NPSは{same_star['nps_p10']:.0f}〜{same_star['nps_p90']:.0f}（10〜90%）に散らばる")
    save(fig, "a808_nps.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
