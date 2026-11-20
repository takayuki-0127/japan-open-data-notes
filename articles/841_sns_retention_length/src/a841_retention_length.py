"""841 長い動画と短い動画の維持率は、そのまま比べられるのか？（架空のデータ）

架空の動画アカウントの動画400本。長さは15秒〜20分（対数で一様）、見た人は1本300〜3,000人（対数で一様）。
見た人は、最初の3秒で25%が離れる。残りの人は3秒のあと、一定の離れやすさ（1分あたりの離れる率 λ）で離れ、
動画が終われば見終わる。λ が動画の「本当の引きつける力」（小さいほど良い）で、長さとは関係なく作成者が置く
（1分あたり0.25を中心に、対数の標準偏差0.4）。
維持率（平均の視聴秒数 ÷ 動画の長さ）・平均の視聴秒数・30秒時点で見ている割合・離れる率の推定で、
本当の力の順がどれだけ当たるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 841
SRC = "架空の動画アカウントの視聴記録（作成者が乱数で作成、seed 841）"
N_VID = 400
BOUNCE, BOUNCE_SEC = 0.25, 3.0
LAM_MED, LAM_SIG = 0.25, 0.4   # 1分あたり
TOP = 40
METRICS = ["維持率", "平均の視聴秒数", "30秒時点で見ている割合", "離れる率の推定"]


def watch_times(rng, n, L, lam, bounce=BOUNCE, shape=1.0):
    """1本の動画の視聴秒数。shape<1 は、はじめほど離れやすい形（ワイブル）"""
    b = rng.random(n) < bounce
    if shape == 1.0:
        t = rng.exponential(60.0 / lam, n)
    else:
        # 平均の離れるまでの時間が 60/lam になるよう尺度を合わせる
        from math import gamma
        scale = (60.0 / lam) / gamma(1 + 1 / shape)
        t = scale * rng.weibull(shape, n)
    w = np.where(b, rng.uniform(0, BOUNCE_SEC, n), BOUNCE_SEC + t)
    return np.minimum(w, L)


def measure(w, L):
    keep = w >= BOUNCE_SEC
    wk = w[keep] - BOUNCE_SEC
    left = (w[keep] < L).sum()
    lam_hat = left / max(wk.sum() / 60.0, 1e-9)
    return {"維持率": w.mean() / L, "平均の視聴秒数": w.mean(),
            "30秒時点で見ている割合": (w >= 30).mean() if L >= 30 else np.nan,
            "離れる率の推定": -lam_hat}  # 大きいほど良い向きにそろえる


def make_videos(rng, n=N_VID, shape=1.0, long_better=0.0, bounce_var=False):
    L = np.exp(rng.uniform(np.log(15), np.log(1200), n))
    viewers = np.round(np.exp(rng.uniform(np.log(300), np.log(3000), n))).astype(int)
    lam = np.exp(rng.normal(np.log(LAM_MED), LAM_SIG, n) - long_better * (np.log(L) - np.log(L).mean()))
    bounce = rng.uniform(0.10, 0.40, n) if bounce_var else np.full(n, BOUNCE)
    rows = []
    for i in range(n):
        w = watch_times(rng, viewers[i], L[i], lam[i], bounce[i], shape)
        m = measure(w, L[i])
        rows.append({"video_id": i + 1, "length_sec": L[i], "viewers": viewers[i], "true_leave_per_min": lam[i], **m})
    return pd.DataFrame(rows)


def evaluate(df):
    true_score = -df.true_leave_per_min
    top_true = set(df.loc[true_score.sort_values(ascending=False).index[:TOP], "video_id"])
    out = {}
    for k in METRICS:
        s = df[k]
        ok = s.notna()
        rho = float(pd.Series(true_score[ok]).rank().corr(s[ok].rank()))
        top = df.loc[s[ok].sort_values(ascending=False).index[:TOP]]
        out[k] = {"spearman_with_true": round(rho, 3),
                  "top40_hit": round(len(top_true & set(top.video_id)) / TOP, 3),
                  "top40_median_length_sec": round(float(top.length_sec.median()), 1),
                  "top40_share_under_60s": round(float((top.length_sec < 60).mean()), 3),
                  "n_videos_used": int(ok.sum())}
    out["all_share_under_60s"] = round(float((df.length_sec < 60).mean()), 3)
    out["true_top40_median_length_sec"] = round(float(df[df.video_id.isin(top_true)].length_sec.median()), 1)
    return out


def retention_formula(L, lam, bounce=BOUNCE):
    """一定の離れやすさのときの維持率（式）。L は秒、lam は1分あたり"""
    L = np.asarray(L, float)
    a = lam / 60.0
    head = np.minimum(L, BOUNCE_SEC)
    rest = np.clip(L - BOUNCE_SEC, 0, None)
    stay = (1 - np.exp(-a * rest)) / a
    mean_w = bounce * np.where(L >= BOUNCE_SEC, BOUNCE_SEC / 2, L / 2) + (1 - bounce) * (head + stay)
    return mean_w / L


def main():
    rng = np.random.default_rng(SEED)
    df = make_videos(rng)
    df.round(5).to_csv(DATA / "videos.csv", index=False)
    base = evaluate(df)
    df["length_band"] = pd.cut(df.length_sec, [0, 60, 180, 600, 1201], labels=["1分未満", "1〜3分", "3〜10分", "10〜20分"])
    band = df.groupby("length_band", observed=True).agg(videos=("video_id", "size"),
                                                         retention_mean=("維持率", "mean"),
                                                         watch_sec_mean=("平均の視聴秒数", "mean"),
                                                         true_leave_mean=("true_leave_per_min", "mean")).round(4)
    band.to_csv(RES / "by_length_band.csv")

    # 同じ力（λ=0.25/分）で、長さだけ変えた維持率（式）
    lengths = [15, 30, 60, 180, 600, 1200]
    same = {str(L): round(float(retention_formula(L, LAM_MED)), 3) for L in lengths}
    # 例の2本：30秒で離れやすい動画（λ=0.40）と、10分で離れにくい動画（λ=0.15）
    pair = {"short_30s_lam0_40": {"retention": round(float(retention_formula(30, 0.40)), 3),
                                  "watch_sec": round(float(retention_formula(30, 0.40) * 30), 1)},
            "long_600s_lam0_15": {"retention": round(float(retention_formula(600, 0.15)), 3),
                                  "watch_sec": round(float(retention_formula(600, 0.15) * 600), 1)}}
    t = np.linspace(0, 600, 601)
    surv = lambda lam, L: np.where(t <= L, np.where(t < BOUNCE_SEC, 1 - BOUNCE * t / BOUNCE_SEC,
                                                    (1 - BOUNCE) * np.exp(-lam / 60 * (t - BOUNCE_SEC))), np.nan)
    pair["at_30s_short"] = round(float((1 - BOUNCE) * np.exp(-0.40 / 60 * 27)), 3)
    pair["at_30s_long"] = round(float((1 - BOUNCE) * np.exp(-0.15 / 60 * 27)), 3)

    # 確かめ：置き方を変える
    rob = []
    settings = [("基本", dict()), ("はじめほど離れやすい形（ワイブル0.7）", dict(shape=0.7)),
                ("長い動画ほど本当に良い", dict(long_better=0.3)), ("最初の3秒の離れ方が動画ごとに10〜40%", dict(bounce_var=True))]
    for i, (name, kw) in enumerate(settings):
        e = base if i == 0 else evaluate(make_videos(np.random.default_rng(SEED * 10 + i), **kw))
        for k in METRICS:
            rob.append({"setting": name, "metric": k, **e[k]})
    # 作り直しの幅（基本の置き方で50回）
    reps = []
    for r in range(50):
        e = evaluate(make_videos(np.random.default_rng(SEED * 100 + r)))
        for k in METRICS:
            reps.append({"rep": r, "metric": k, "top40_hit": e[k]["top40_hit"], "spearman": e[k]["spearman_with_true"]})
    reps = pd.DataFrame(reps)
    rep_sum = reps.groupby("metric", sort=False).agg(hit_mean=("top40_hit", "mean"), hit_p10=("top40_hit", lambda x: x.quantile(.1)),
                                                     hit_p90=("top40_hit", lambda x: x.quantile(.9)),
                                                     spearman_mean=("spearman", "mean")).round(3).reindex(METRICS)
    rep_sum.to_csv(RES / "repeat_50.csv")
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"base_400_videos": base, "by_length_band": band.reset_index().astype({"length_band": str}).to_dict("records"),
           "same_power_retention_by_length": same, "example_pair": pair,
           "repeat_50": rep_sum.reset_index().to_dict("records"), "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a841_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：長さと維持率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    q = df.true_leave_per_min
    lo, hi = q.quantile(1 / 3), q.quantile(2 / 3)
    for mask, c, lab in [(q <= lo, GREEN, "本当に離れにくい3分の1"), ((q > lo) & (q < hi), GRAY, "まんなかの3分の1"),
                         (q >= hi, ORANGE, "本当に離れやすい3分の1")]:
        ax.scatter(df.length_sec[mask], df["維持率"][mask] * 100, s=10, color=c, alpha=.7, lw=0, label=lab)
    xs = np.exp(np.linspace(np.log(15), np.log(1200), 100))
    ax.plot(xs, retention_formula(xs, LAM_MED) * 100, color=INK, lw=1.2, label="同じ力（1分あたり0.25）の式")
    ax.set_xscale("log"); ax.set_xticks([15, 30, 60, 180, 600, 1200]); ax.set_xticklabels(["15秒", "30秒", "1分", "3分", "10分", "20分"])
    ax.set_ylim(0, 100); ax.set_xlabel("動画の長さ（対数の目盛り）"); ax.set_ylabel("維持率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("力が同じでも、長い動画ほど維持率は低く出る（動画400本）")
    save(fig, "a841_length.png", SRC)

    # 図2：例の2本の「まだ見ている人の割合」
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(t, surv(0.40, 30) * 100, color=ORANGE, lw=2, label=f"30秒・離れやすい（維持率{pair['short_30s_lam0_40']['retention']*100:.0f}%）")
    ax.plot(t, surv(0.15, 600) * 100, color=BLUE, lw=2, label=f"10分・離れにくい（維持率{pair['long_600s_lam0_15']['retention']*100:.0f}%）")
    ax.axvline(30, color=GRAY, ls="--", lw=1)
    ax.set_xscale("symlog", linthresh=30); ax.set_xticks([0, 10, 20, 30, 60, 180, 600]); ax.set_xticklabels(["0", "10", "20", "30", "60", "180", "600"])
    ax.set_xlim(0, 600); ax.set_ylim(0, 100); ax.set_xlabel("動画の始まりからの秒数（30秒より先は対数の目盛り）"); ax.set_ylabel("まだ見ている人の割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("30秒の時点では、10分の動画のほうが多くの人が見ている")
    save(fig, "a841_pair.png", SRC)

    # 図3：指標ごとの上位40本の当たり（50回の平均）
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    labs = ["維持率", "平均の視聴秒数", "30秒時点で見ている割合\n（30秒以上の動画だけ）", "離れる率の推定"]
    vals = rep_sum.hit_mean.values * 100
    ax.barh(labs[::-1], vals[::-1], color=[GREEN, BLUE, GRAY, ORANGE][::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("上位40本のうち、本当の上位40本に入っていた割合（%、50回の平均）")
    ax.set_title("維持率の順では、本当に引きつける動画は当たりにくい")
    save(fig, "a841_metrics.png", SRC, y=-0.05)
    print(json.dumps({k: out[k] for k in ["base_400_videos", "same_power_retention_by_length", "example_pair", "repeat_50"]},
                     ensure_ascii=False, indent=1))
    print(band); print(rob.to_string())


if __name__ == "__main__":
    main()
