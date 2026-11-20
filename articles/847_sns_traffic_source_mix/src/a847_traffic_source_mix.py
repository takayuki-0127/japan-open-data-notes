"""847 流入元の違う再生数を合わせると、何を読み違えるのか？（架空のデータ）

架空の動画チャンネル。再生がどこから来たか（流入元）を4つに分ける：
検索・おすすめ表示・外部リンク・SNSの共有。流入元ごとに「最後まで見た割合（完了率）」の水準が違う。
(A) 月の比較：翌月、どの流入元でも完了率が2ポイント上がったが、おすすめ表示からの再生が大きく増えた。
    全部を合わせた完了率は上がるか下がるか。
(B) 動画の比較：動画120本。動画ごとに「中身の良さ」（どの流入元でも完了率を同じだけ押し上げる量）を置く。
    全部を合わせた完了率で並べる場合と、流入元ごとの平均との差で並べる場合で、中身の良さの順がどれだけ当たるか。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 847
SRC = "架空の動画チャンネル（作成者が乱数で作成、seed 847）"
SOURCES = ["検索", "おすすめ表示", "外部リンク", "SNSの共有"]
RATE = np.array([0.55, 0.25, 0.45, 0.40])          # 流入元ごとの完了率の水準
N_VIDEO = 120
REPS = 300
BASE = dict(gap=1.0, q_sd=0.05, mix_conc=1.5, link=0.0, feed_mult=1.0, feed_noise=0.0)


# ---------- (A) 月の比較 ----------
def months(rng):
    v1 = np.array([40000, 30000, 15000, 15000])
    v2 = np.array([40000, 140000, 15000, 15000])
    r1, r2 = RATE, RATE + 0.02
    c1, c2 = rng.binomial(v1, r1), rng.binomial(v2, r2)
    rows = []
    for i, s in enumerate(SOURCES):
        rows.append({"source": s, "views_m1": int(v1[i]), "done_m1": int(c1[i]), "rate_m1": c1[i] / v1[i],
                     "views_m2": int(v2[i]), "done_m2": int(c2[i]), "rate_m2": c2[i] / v2[i]})
    rows.append({"source": "合計", "views_m1": int(v1.sum()), "done_m1": int(c1.sum()), "rate_m1": c1.sum() / v1.sum(),
                 "views_m2": int(v2.sum()), "done_m2": int(c2.sum()), "rate_m2": c2.sum() / v2.sum()})
    df = pd.DataFrame(rows)
    # 先月の流入元の内訳に固定して今月の完了率を合わせ直す
    w1 = v1 / v1.sum()
    fixed_m2 = float((w1 * c2 / v2).sum())
    return df, fixed_m2


# ---------- (B) 動画の比較 ----------
def make_videos(rng, gap=1.0, q_sd=0.05, mix_conc=1.5, link=0.0, feed_mult=1.0, feed_noise=0.0, n=N_VIDEO):
    """gap：流入元どうしの完了率の差の倍率（1＝基本、0.5＝差を半分）
    mix_conc：おすすめ表示の割合のばらつき（Beta(c,c)、小さいほど動画ごとに大きく違う）
    link：中身の良さとおすすめ表示の割合の結びつき（+ なら良い動画ほどおすすめ表示が多い）
    feed_mult：おすすめ表示では中身の良さが何倍効くか（1＝どの流入元でも同じ）
    feed_noise：おすすめ表示の完了率が、中身と関係なく動画ごとに振れる大きさ（標準偏差）"""
    rate = RATE.mean() + gap * (RATE - RATE.mean())
    q = rng.normal(0, q_sd, n)
    total = np.round(np.exp(rng.normal(np.log(8000), 1.0, n))).astype(int) + 50
    z = rng.normal(0, 1, n) + link * q / q_sd
    # おすすめ表示の割合：Beta(c,c) の分位点を z の順位で並べ替える
    f = np.sort(rng.beta(mix_conc, mix_conc, n))[np.argsort(np.argsort(z))]
    rest = rng.dirichlet([4, 2, 2], n)
    share = np.column_stack([rest[:, 0] * (1 - f), f, rest[:, 1] * (1 - f), rest[:, 2] * (1 - f)])
    views = np.array([rng.multinomial(t, s) for t, s in zip(total, share)])
    eff = q[:, None] * np.array([1.0, feed_mult, 1.0, 1.0])[None, :]
    eff[:, 1] += rng.normal(0, feed_noise, n) if feed_noise > 0 else 0.0
    p = np.clip(rate[None, :] + eff, 0.01, 0.99)
    done = rng.binomial(views, p)
    return q, views, done


def scores(views, done):
    overall = done.sum(1) / views.sum(1)
    src_rate = done.sum(0) / views.sum(0)                       # 流入元ごとのチャンネル全体の完了率
    adjusted = (done - views * src_rate[None, :]).sum(1) / views.sum(1)   # 流入元ごとの平均との差
    return overall, adjusted


def rank_corr(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def top_hit(score, q, k=10):
    return len(set(np.argsort(-score)[:k]) & set(np.argsort(-q)[:k])) / k


def run_many(seed, reps=REPS, **kw):
    out = []
    for r in range(reps):
        q, v, d = make_videos(np.random.default_rng(seed + r), **kw)
        o, a = scores(v, d)
        out.append((rank_corr(o, q), rank_corr(a, q), top_hit(o, q), top_hit(a, q)))
    return np.array(out)


def main():
    t0 = time.time()
    res = {"sources": SOURCES, "rate_level": RATE.tolist(), "base": BASE, "n_video": N_VIDEO, "reps": REPS,
           "top10_hit_random_baseline": round(10 / N_VIDEO, 3)}

    # (A)
    mdf, fixed_m2 = months(np.random.default_rng(SEED))
    mdf.round(4).to_csv(DATA / "channel_months.csv", index=False)
    tot = mdf[mdf.source == "合計"].iloc[0]
    res["months"] = {"overall_m1": round(float(tot.rate_m1), 4), "overall_m2": round(float(tot.rate_m2), 4),
                     "overall_m2_fixed_mix": round(fixed_m2, 4),
                     "feed_share_m1": round(30000 / 100000, 3), "feed_share_m2": round(140000 / 210000, 3),
                     "by_source": mdf.round(4).to_dict("records")}
    mdf.round(4).to_csv(RES / "months.csv", index=False)

    # (B) 1回分
    rng = np.random.default_rng(SEED + 1)
    q, v, d = make_videos(rng, **BASE)
    o, a = scores(v, d)
    feed = v[:, 1] / v.sum(1)
    vid = pd.DataFrame({"video_id": np.arange(1, N_VIDEO + 1), "quality": q,
                        **{f"views_{s}": v[:, i] for i, s in enumerate(SOURCES)},
                        **{f"done_{s}": d[:, i] for i, s in enumerate(SOURCES)},
                        "feed_share": feed, "overall_rate": o, "adjusted": a})
    vid.to_csv(DATA / "videos.csv", index=False, float_format="%.4f")
    top_o = np.argsort(-o)[:10]
    top_q = np.argsort(-q)[:10]
    res["one_run"] = {"rank_corr_overall": round(rank_corr(o, q), 3), "rank_corr_adjusted": round(rank_corr(a, q), 3),
                      "top10_hit_overall": top_hit(o, q), "top10_hit_adjusted": top_hit(a, q),
                      "feed_share_median_all": round(float(np.median(feed)), 3),
                      "feed_share_median_top10_overall": round(float(np.median(feed[top_o])), 3),
                      "feed_share_median_top10_true": round(float(np.median(feed[top_q])), 3),
                      "rank_corr_overall_vs_feed_share": round(rank_corr(o, feed), 3)}

    # (B) 300回と、置き方を変えた確かめ
    cases = [("基本（流入元の差そのまま・中身の差0.05・内訳のばらつき大）", {}),
             ("流入元どうしの差を半分", {"gap": 0.5}),
             ("流入元どうしの差なし", {"gap": 0.0}),
             ("中身の差を大きく（0.10）", {"q_sd": 0.10}),
             ("中身の差を小さく（0.02）", {"q_sd": 0.02}),
             ("内訳のばらつきを小さく", {"mix_conc": 8.0}),
             ("良い動画ほどおすすめ表示が多い", {"link": 0.5}),
             ("良い動画ほどおすすめ表示が少ない", {"link": -0.5}),
             ("おすすめ表示では中身が半分しか効かない", {"feed_mult": 0.5}),
             ("おすすめ表示の完了率が中身と別に振れる（0.05）", {"feed_noise": 0.05})]
    rows = []
    for k, (name, kw) in enumerate(cases):
        arr = run_many(SEED * 1000 + k * 1000, **{**BASE, **kw})
        rows.append({"case": name,
                     "rank_corr_overall": round(float(arr[:, 0].mean()), 3),
                     "rank_corr_adjusted": round(float(arr[:, 1].mean()), 3),
                     "top10_hit_overall": round(float(arr[:, 2].mean()), 3),
                     "top10_hit_adjusted": round(float(arr[:, 3].mean()), 3)})
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "videos_cases.csv", index=False)
    res["videos_cases"] = rob.to_dict("records")

    # 図1：月の比較
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    labels = SOURCES + ["合計"]
    x = np.arange(len(labels))
    ax.bar(x - 0.2, mdf.rate_m1 * 100, 0.4, color=LIGHT, label="先月")
    ax.bar(x + 0.2, mdf.rate_m2 * 100, 0.4, color=BLUE, label="今月")
    ax.bar(x[-1] - 0.2, mdf.rate_m1.iloc[-1] * 100, 0.4, color="#f6c3ad")
    ax.bar(x[-1] + 0.2, mdf.rate_m2.iloc[-1] * 100, 0.4, color=ORANGE)
    for i in range(len(labels)):
        ax.text(x[i] - 0.2, mdf.rate_m1.iloc[i] * 100 + 0.8, f"{mdf.rate_m1.iloc[i]*100:.1f}", ha="center", fontsize=8.5)
        ax.text(x[i] + 0.2, mdf.rate_m2.iloc[i] * 100 + 0.8, f"{mdf.rate_m2.iloc[i]*100:.1f}", ha="center", fontsize=8.5)
    sh1 = [f"{v/1000:.0f}千→{w/1000:.0f}千" for v, w in zip(mdf.views_m1, mdf.views_m2)]
    ax.set_xticks(x); ax.set_xticklabels([f"{l}\n再生 {s}" for l, s in zip(labels, sh1)], fontsize=9)
    ax.set_ylabel("最後まで見た割合（%）")
    ax.set_ylim(0, 68)
    ax.set_title("どの流入元でも上がったのに、合計では下がった")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "a847_months.png", SRC)

    # 図2：1回分の動画120本
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=False)
    for ax, sc, name in [(axes[0], o * 100, "全部を合わせた完了率（%）"), (axes[1], a * 100, "流入元ごとの平均との差（ポイント）")]:
        s = ax.scatter(q * 100, sc, c=feed, cmap="Oranges", vmin=0, vmax=1, s=22, edgecolor=GRAY, linewidth=0.3)
        ax.set_xlabel("中身の良さ（作成者が置いた値、ポイント）")
        ax.set_ylabel(name)
    axes[0].set_title(f"合わせた完了率：順位の相関 {rank_corr(o, q):.2f}", fontsize=11)
    axes[1].set_title(f"流入元をそろえる：順位の相関 {rank_corr(a, q):.2f}", fontsize=11)
    cb = fig.colorbar(s, ax=axes, shrink=0.8, pad=0.02)
    cb.set_label("おすすめ表示からの再生の割合")
    save(fig, "a847_videos.png", SRC)

    # 図3：置き方ごとの上位10本の当たり
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    y = np.arange(len(rob))
    ax.barh(y - 0.2, rob.top10_hit_overall * 100, 0.4, color=ORANGE, label="合わせた完了率で並べる")
    ax.barh(y + 0.2, rob.top10_hit_adjusted * 100, 0.4, color=BLUE, label="流入元ごとの平均との差で並べる")
    for i in range(len(rob)):
        ax.text(rob.top10_hit_overall.iloc[i] * 100 + 1, y[i] - 0.2, f"{rob.top10_hit_overall.iloc[i]*100:.0f}%", va="center", fontsize=8.5)
        ax.text(rob.top10_hit_adjusted.iloc[i] * 100 + 1, y[i] + 0.2, f"{rob.top10_hit_adjusted.iloc[i]*100:.0f}%", va="center", fontsize=8.5)
    short = [c.split("（")[0] if c.startswith("基本") else c for c in rob.case]
    ax.set_yticks(y); ax.set_yticklabels(short, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("中身の良さの上位10本に入っていた割合（300回の平均、%）")
    ax.set_title("流入元の差があるときは、そろえて比べると当たりが増える")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.4, -0.13), ncol=2, fontsize=9)
    save(fig, "a847_cases.png", SRC, y=-0.06)

    with open(RES / "a847_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"{time.time() - t0:.1f} 秒")


if __name__ == "__main__":
    main()
