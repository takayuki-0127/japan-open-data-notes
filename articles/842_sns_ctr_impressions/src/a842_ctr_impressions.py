"""842 表示が増えると、クリック率は下がって見えるのか？（架空のデータ）

架空のSNSアカウント（フォロワー1万人）の投稿300本。投稿ごとに「本当の引きの強さ」a を置く
（同じ相手に見せたときのクリックのしやすさの倍率。対数で平均0・標準偏差0.35）。
投稿は3つの相手に表示される：フォロワー（ふだんのクリック率6%）、おすすめで近い興味の人（2.5%）、
おすすめで遠い興味の人（1%）。フォロワーへの表示は1本あたり約3,000回。おすすめへの表示は、
引きの強い投稿ほど大きく広がる（近い人へは a の3乗、遠い人へは a の5乗に比例、ゆらぎあり）。
クリック数は「表示回数 × 相手ごとのクリック率 × a」の二項分布から引く。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 842
SRC = "架空のSNSアカウントの投稿（作成者が乱数で作成、seed 842）"
N_POST = 300
LAYERS = ["フォロワー", "近い興味", "遠い興味"]
BASE_CTR = (0.06, 0.025, 0.01)
SPREAD = (3, 5)
A_SIG = 0.35
TOP = 30
METRICS = ["全体のクリック率", "フォロワーだけのクリック率", "相手の内訳でそろえたクリック率"]


def make_posts(rng, n=N_POST, base=BASE_CTR, spread=SPREAD, a_sig=A_SIG):
    a = np.exp(rng.normal(0, a_sig, n))
    imp_f = np.round(3000 * rng.uniform(0.8, 1.2, n)).astype(int)
    imp_n = np.round(3000 * a ** spread[0] * np.exp(rng.normal(0, 0.5, n))).astype(int)
    imp_d = np.round(3000 * a ** spread[1] * np.exp(rng.normal(0, 0.7, n))).astype(int)
    imps = np.stack([imp_f, imp_n, imp_d], 1)
    p = np.clip(np.array(base)[None, :] * a[:, None], 0, 1)
    clicks = rng.binomial(imps, p)
    df = pd.DataFrame({"post_id": np.arange(1, n + 1), "true_appeal": a})
    for j, k in enumerate(["follower", "near", "far"]):
        df[f"imp_{k}"] = imps[:, j]; df[f"click_{k}"] = clicks[:, j]
    return df


def add_metrics(df):
    imp = df[["imp_follower", "imp_near", "imp_far"]].values
    clk = df[["click_follower", "click_near", "click_far"]].values
    df["impressions"] = imp.sum(1); df["clicks"] = clk.sum(1)
    df["全体のクリック率"] = df.clicks / df.impressions
    df["フォロワーだけのクリック率"] = clk[:, 0] / imp[:, 0]
    # アカウント全体の相手ごとのクリック率（手元で数えられる値）から、内訳どおりなら何回クリックされるかを出して比べる
    layer_rate = clk.sum(0) / imp.sum(0)
    expected = (imp * layer_rate[None, :]).sum(1)
    df["相手の内訳でそろえたクリック率"] = df.clicks / expected
    return df, layer_rate


def evaluate(df):
    top_true = set(df.nlargest(TOP, "true_appeal").post_id)
    out = {"spearman_impressions_vs_ctr": round(float(df.impressions.rank().corr(df["全体のクリック率"].rank())), 3),
           "spearman_impressions_vs_true": round(float(df.impressions.rank().corr(df.true_appeal.rank())), 3)}
    for k in METRICS:
        top = df.nlargest(TOP, k)
        out[k] = {"spearman_with_true": round(float(df[k].rank().corr(df.true_appeal.rank())), 3),
                  "top30_hit": round(len(top_true & set(top.post_id)) / TOP, 3),
                  "top30_median_impressions": float(top.impressions.median())}
    return out


def main():
    rng = np.random.default_rng(SEED)
    df, layer_rate = add_metrics(make_posts(rng))
    df.round(5).to_csv(DATA / "posts.csv", index=False)
    base = evaluate(df)
    base["layer_rate_all_posts"] = {k: round(float(v), 4) for k, v in zip(LAYERS, layer_rate)}

    # 表示回数の帯ごと
    df["imp_band"] = pd.qcut(df.impressions, 5, labels=["少ない5分の1", "2", "3", "4", "多い5分の1"])
    band = df.groupby("imp_band", observed=True).agg(posts=("post_id", "size"), impressions_median=("impressions", "median"),
                                                     ctr_overall=("全体のクリック率", "mean"),
                                                     ctr_follower=("フォロワーだけのクリック率", "mean"),
                                                     true_appeal_mean=("true_appeal", "mean"),
                                                     share_follower_imp=("imp_follower", lambda s: 0)).drop(columns="share_follower_imp")
    band["share_follower_imp"] = df.groupby("imp_band", observed=True).apply(lambda g: g.imp_follower.sum() / g.impressions.sum())
    band = band.round(4)
    band.to_csv(RES / "by_impression_band.csv")

    # 例の2本：表示のいちばん多い投稿と、表示が中央くらいの投稿
    # 表示が多い上位1割の投稿のうち、表示回数がその中の真ん中の投稿
    top10 = df[df.impressions >= df.impressions.quantile(0.9)].sort_values("impressions")
    big = top10.iloc[len(top10) // 2]
    mid = df.iloc[(df.impressions - df.impressions.median()).abs().argsort().iloc[0]]
    def post_row(r):
        d = {"post_id": int(r.post_id), "true_appeal": round(float(r.true_appeal), 3), "impressions": int(r.impressions),
             "ctr_overall": round(float(r["全体のクリック率"]), 4)}
        for k, lab in zip(["follower", "near", "far"], LAYERS):
            d[lab] = {"imp": int(r[f"imp_{k}"]), "ctr": round(float(r[f"click_{k}"] / r[f"imp_{k}"]), 4) if r[f"imp_{k}"] > 0 else None}
        return d
    pair = {"most_shown": post_row(big), "median_shown": post_row(mid)}
    pair["higher_in_every_layer"] = bool(all(pair["most_shown"][l]["ctr"] > pair["median_shown"][l]["ctr"] for l in LAYERS))

    # 作り直しの幅（50回）
    reps = []
    for r in range(50):
        e = evaluate(add_metrics(make_posts(np.random.default_rng(SEED * 100 + r)))[0])
        row = {"rep": r, "rho_imp_ctr": e["spearman_impressions_vs_ctr"]}
        for k in METRICS:
            row[k] = e[k]["top30_hit"]
        reps.append(row)
    reps = pd.DataFrame(reps)
    rep_sum = {"rho_imp_ctr_mean": round(float(reps.rho_imp_ctr.mean()), 3),
               "rho_imp_ctr_min": round(float(reps.rho_imp_ctr.min()), 3), "rho_imp_ctr_max": round(float(reps.rho_imp_ctr.max()), 3)}
    for k in METRICS:
        rep_sum[k] = {"hit_mean": round(float(reps[k].mean()), 3), "hit_p10": round(float(reps[k].quantile(.1)), 3),
                      "hit_p90": round(float(reps[k].quantile(.9)), 3)}
    reps.to_csv(RES / "repeat_50.csv", index=False)

    # 確かめ：置き方を変える（各50回の平均）
    settings = [("基本（6%・2.5%・1%、広がり3乗・5乗）", dict()),
                ("相手の差を小さく（6%・4.5%・3.5%）", dict(base=(0.06, 0.045, 0.035))),
                ("相手の差なし（どこでも6%）", dict(base=(0.06, 0.06, 0.06))),
                ("広がりを弱く（1乗・2乗）", dict(spread=(1, 2))),
                ("引きの強さの差を小さく（0.2）", dict(a_sig=0.2))]
    rob = []
    for i, (name, kw) in enumerate(settings):
        rr = []
        for r in range(50):
            e = evaluate(add_metrics(make_posts(np.random.default_rng(SEED * 1000 + i * 100 + r), **kw))[0])
            rr.append([e["spearman_impressions_vs_ctr"]] + [e[k]["top30_hit"] for k in METRICS])
        rr = np.array(rr).mean(0)
        rob.append({"setting": name, "rho_imp_ctr": round(float(rr[0]), 3),
                    **{f"hit_{k}": round(float(v), 3) for k, v in zip(METRICS, rr[1:])}})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    base["band_top_vs_bottom"] = {"true_appeal_ratio": round(float(band.true_appeal_mean.iloc[-1] / band.true_appeal_mean.iloc[0]), 2),
                                  "ctr_overall_bottom": float(band.ctr_overall.iloc[0]), "ctr_overall_top": float(band.ctr_overall.iloc[-1]),
                                  "ctr_follower_bottom": float(band.ctr_follower.iloc[0]), "ctr_follower_top": float(band.ctr_follower.iloc[-1])}
    out = {"base_300_posts": base, "by_impression_band": band.reset_index().astype({"imp_band": str}).to_dict("records"),
           "example_pair": pair, "repeat_50": rep_sum, "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a842_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：表示回数と全体のクリック率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    sc = ax.scatter(df.impressions, df["全体のクリック率"] * 100, c=np.log(df.true_appeal), cmap="coolwarm", s=12, lw=0,
                    vmin=-0.8, vmax=0.8)
    cb = fig.colorbar(sc, ax=ax, pad=0.01); cb.set_label("本当の引きの強さ（赤ほど強い）"); cb.set_ticks([])
    ax.set_xscale("log"); ax.set_xlabel("表示回数（対数の目盛り）"); ax.set_ylabel("全体のクリック率（%）")
    ax.set_title("引きの強い（赤い）投稿ほど表示は多いが、クリック率は高く出ない", fontsize=12)
    save(fig, "a842_scatter.png", SRC)

    # 図2：例の2本の、相手ごとのクリック率と表示の内訳
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.8), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    x = np.arange(4); w = 0.38
    lab4 = LAYERS + ["全体"]
    v_big = [pair["most_shown"][l]["ctr"] * 100 for l in LAYERS] + [pair["most_shown"]["ctr_overall"] * 100]
    v_mid = [pair["median_shown"][l]["ctr"] * 100 for l in LAYERS] + [pair["median_shown"]["ctr_overall"] * 100]
    ax.bar(x - w / 2, v_big, w, color=ORANGE, label="表示が上位1割の投稿")
    ax.bar(x + w / 2, v_mid, w, color=BLUE, label="表示が中くらいの投稿")
    for i in range(4):
        ax.text(x[i] - w / 2, v_big[i] + 0.15, f"{v_big[i]:.1f}", ha="center", fontsize=8)
        ax.text(x[i] + w / 2, v_mid[i] + 0.15, f"{v_mid[i]:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(lab4); ax.set_ylabel("クリック率（%）")
    ax.legend(frameon=False, fontsize=8, loc="upper right"); ax.set_title("相手ごとのクリック率", fontsize=11)
    ax = axes[1]
    for j, (key, c) in enumerate([("median_shown", BLUE), ("most_shown", ORANGE)]):
        imp = np.array([pair[key][l]["imp"] for l in LAYERS], float)
        share = imp / imp.sum() * 100
        left = 0
        for s, col in zip(share, [INK, GRAY, LIGHT]):
            ax.barh(j, s, left=left, color=col, height=0.5)
            if s > 7:
                ax.text(left + s / 2, j, f"{s:.0f}%", ha="center", va="center", fontsize=8, color="white" if col == INK else INK)
            left += s
    ax.set_yticks([0, 1]); ax.set_yticklabels(["中くらい", "上位1割"]); ax.set_xlim(0, 100)
    ax.set_xlabel("表示の内訳（%）")
    from matplotlib.patches import Patch
    ax.legend([Patch(color=c) for c in [INK, GRAY, LIGHT]], LAYERS, frameon=False, fontsize=8, loc="upper center",
              bbox_to_anchor=(0.5, -0.2), ncol=3)
    ax.set_title("表示の内訳", fontsize=11)
    fig.suptitle("どの相手でも上なのに、全体のクリック率は下になる", fontsize=13, y=1.06)
    save(fig, "a842_pair.png", SRC, y=-0.13)

    # 図3：指標ごとの上位30本の当たり（50回の平均）
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    vals = [rep_sum[k]["hit_mean"] * 100 for k in METRICS]
    ax.barh(METRICS[::-1], vals[::-1], color=[GREEN, BLUE, GRAY][::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("上位30本のうち、本当の上位30本に入っていた割合（%、50回の平均）")
    ax.set_title("全体のクリック率の順では、引きの強い投稿が当たりにくい")
    save(fig, "a842_metrics.png", SRC, y=-0.05)
    print(json.dumps({k: out[k] for k in ["base_300_posts", "example_pair", "repeat_50"]}, ensure_ascii=False, indent=1))
    print(band); print(rob.to_string())


if __name__ == "__main__":
    main()
