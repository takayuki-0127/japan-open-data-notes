"""838 伸びた投稿だけ見て「伸びる型」を決めると、何が起きるのか？（架空のデータ）

架空のアカウントの2年分の投稿600本。投稿は「定番の型」と「流行に乗る型」の2つ。
再生回数は型ごとに対数正規分布（中央値と、振れの大きさを作成者が置く）。流行に乗る型は、
振れが大きく、平均は定番より低いと置く。字幕の有無（再生回数には効かないと置く）も付ける。
伸びた上位5%だけを見たときの型の割合と、全部の投稿で見た平均を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 838
SRC = "架空のアカウントの投稿（作成者が乱数で作成、seed 838）"
N_POST = 600
BASE = {"share_trend": 0.3, "med_std": 3000, "sd_std": 0.6, "med_trend": 1200, "sd_trend": 1.3, "share_sub": 0.8}


def true_mean(med, sd):
    return med * np.exp(sd ** 2 / 2)


def make_posts(rng, n=N_POST, share_trend=0.3, med_std=3000, sd_std=0.6, med_trend=1200, sd_trend=1.3, share_sub=0.8):
    trend = rng.random(n) < share_trend
    sub = rng.random(n) < share_sub                 # 字幕あり（再生回数には効かないと置く）
    lv = np.where(trend, rng.normal(np.log(med_trend), sd_trend, n), rng.normal(np.log(med_std), sd_std, n))
    return pd.DataFrame({"post_id": np.arange(1, n + 1), "type": np.where(trend, "流行に乗る型", "定番の型"),
                         "subtitle": sub.astype(int), "view": np.round(np.exp(lv)).astype(int)})


def top_share(df, frac):
    k = max(1, int(round(len(df) * frac)))
    top = df.sort_values(["view", "post_id"], ascending=[False, True]).iloc[:k]
    return float((top.type == "流行に乗る型").mean()), float(top.subtitle.mean())


def main():
    rng = np.random.default_rng(SEED)
    df = make_posts(rng, **BASE)
    df.to_csv(DATA / "posts.csv", index=False)

    tm_std, tm_trend = true_mean(BASE["med_std"], BASE["sd_std"]), true_mean(BASE["med_trend"], BASE["sd_trend"])

    # 1) 上位の切り方ごとの、流行に乗る型の割合（1,000回）
    fracs = [0.01, 0.05, 0.10, 0.25, 0.50, 1.0]
    rows, pick, mean_flip, med_flip = [], 0, 0, 0
    for r in range(1000):
        g = make_posts(np.random.default_rng(SEED * 1000 + r), **BASE)
        mm = g.groupby("type").view.agg(["mean", "median"])
        mean_flip += mm.loc["流行に乗る型", "mean"] > mm.loc["定番の型", "mean"]
        med_flip += mm.loc["流行に乗る型", "median"] > mm.loc["定番の型", "median"]
        for f in fracs:
            st, ss = top_share(g, f)
            rows.append({"rep": r, "top_frac": f, "trend_share": st, "subtitle_share": ss})
        st5, _ = top_share(g, 0.05)
        pick += st5 > (g.type == "流行に乗る型").mean()
    by_cut = pd.DataFrame(rows).groupby("top_frac").mean().drop(columns="rep").round(3).reset_index()
    by_cut.to_csv(RES / "share_by_cutoff.csv", index=False)

    # 2) 型ごとの本当の値と、1回分の見かけ
    one = df.groupby("type").view.agg(["count", "mean", "median"]).round(0)
    one["share_ge_20000"] = df.groupby("type").view.apply(lambda v: (v >= 20000).mean()).round(3)
    st5, ss5 = top_share(df, 0.05)

    # 3) 次の100本を全部「流行に乗る型」にしたら（10,000回）
    rr = np.random.default_rng(SEED * 100000)
    R = 10000
    tr = rr.random((R, 100)) < BASE["share_trend"]
    a = np.round(np.exp(np.where(tr, rr.normal(np.log(BASE["med_trend"]), BASE["sd_trend"], (R, 100)),
                                 rr.normal(np.log(BASE["med_std"]), BASE["sd_std"], (R, 100)))))
    b = np.round(np.exp(rr.normal(np.log(BASE["med_trend"]), BASE["sd_trend"], (R, 100))))
    keep = np.c_[a.sum(1), np.median(a, 1), (a >= 20000).sum(1)]
    swit = np.c_[b.sum(1), np.median(b, 1), (b >= 20000).sum(1)]
    plan = {"keep_total_mean": int(keep[:, 0].mean()), "switch_total_mean": int(swit[:, 0].mean()),
            "keep_median_of_median": int(np.median(keep[:, 1])), "switch_median_of_median": int(np.median(swit[:, 1])),
            "p_switch_total_higher": round(float((swit[:, 0] > keep[:, 0]).mean()), 3),
            "keep_hits_ge_20000": round(float(keep[:, 2].mean()), 2), "switch_hits_ge_20000": round(float(swit[:, 2].mean()), 2)}

    # 4) 確かめ：流行に乗る型の振れ・中央値を変える（各1,000回）
    rob = []
    variants = [("基本（振れ1.3・中央値1,200）", {}), ("振れ 1.0", {"sd_trend": 1.0}), ("振れ 1.6", {"sd_trend": 1.6}),
                ("中央値 800", {"med_trend": 800}), ("中央値 2,000", {"med_trend": 2000}),
                (f"平均を定番と同じにする（中央値 {round(tm_std / np.exp(1.3 ** 2 / 2)):,}）", {"med_trend": round(tm_std / np.exp(1.3 ** 2 / 2))}),
                ("流行に乗る型の本数 1割", {"share_trend": 0.1}), ("流行に乗る型の本数 5割", {"share_trend": 0.5}),
                ("振れを定番と同じ0.6（中央値1,200）", {"sd_trend": 0.6})]
    for i, (lab, ch) in enumerate(variants):
        st = {**BASE, **ch}
        sh, pk = [], 0
        for r in range(1000):
            g = make_posts(np.random.default_rng(SEED * 1000 + r if i == 0 else SEED * 10 ** 6 + i * 10000 + r), **st)
            s5, _ = top_share(g, 0.05); sh.append(s5); pk += s5 > (g.type == "流行に乗る型").mean()
        rob.append({"setting": lab, "share_all": st["share_trend"], "trend_share_top5": round(float(np.mean(sh)), 3),
                    "lift_top5": round(float(np.mean(sh)) / st["share_trend"], 2),
                    "p_pick_trend": round(pk / 1000, 3),
                    "true_mean_ratio_trend_vs_std": round(true_mean(st["med_trend"], st["sd_trend"]) /
                                                          true_mean(st["med_std"], st["sd_std"]), 3)})
    rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)

    out = {"setting": BASE, "n_post": N_POST,
           "true_mean": {"定番の型": round(tm_std), "流行に乗る型": round(tm_trend)},
           "true_median": {"定番の型": BASE["med_std"], "流行に乗る型": BASE["med_trend"]},
           "true_mean_ratio_trend_vs_std": round(tm_trend / tm_std, 3),
           "by_cutoff_1000reps": by_cut.to_dict("records"),
           "p_pick_trend_top5_1000reps": round(pick / 1000, 3),
           "p_trend_mean_higher_all_posts_1000reps": round(mean_flip / 1000, 3),
           "p_trend_median_higher_all_posts_1000reps": round(med_flip / 1000, 3),
           "one_draw": {"by_type": one.reset_index().to_dict("records"), "top5_trend_share": round(st5, 3),
                        "top5_subtitle_share": round(ss5, 3), "subtitle_share_all": round(float(df.subtitle.mean()), 3),
                        "trend_share_all": round(float((df.type == "流行に乗る型").mean()), 3)},
           "next100_10000reps": plan,
           "robust_lift_range": [float(rob.lift_top5.min()), float(rob.lift_top5.max())],
           "robust_p_pick_range": [float(rob.p_pick_trend.min()), float(rob.p_pick_trend.max())]}
    json.dump(out, open(RES / "a838_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の再生回数の分布（型ごと）と上位5%の線
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.logspace(1.5, 5.5, 50)
    for t, c in [("定番の型", BLUE), ("流行に乗る型", ORANGE)]:
        ax.hist(df.view[df.type == t], bins=bins, color=c, alpha=.6, label=t)
    cut = df.view.sort_values(ascending=False).iloc[int(N_POST * .05) - 1]
    ax.axvline(cut, color=INK, lw=1, ls="--"); ax.text(cut * 1.1, ax.get_ylim()[1] * .9, "上位5%（30本）", fontsize=9)
    ax.set_xscale("log"); ax.set_xlabel("再生回数（対数の目盛り）"); ax.set_ylabel("投稿の数")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"流行に乗る型は全体の{out['one_draw']['trend_share_all']*100:.0f}%だが、上位30本では{st5*100:.0f}%")
    save(fig, "a838_hist.png", SRC)

    # 図2：上位の切り方ごとの割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    labs = ["上位1%", "上位5%", "上位10%", "上位25%", "上位50%", "全部"]
    ax.bar(labs, by_cut.trend_share * 100, color=[ORANGE] * 5 + [GRAY])
    ax.plot(labs, by_cut.subtitle_share * 100, color=BLUE, marker="o", label="字幕ありの割合（再生回数に効かないと置いた）")
    for i, v in enumerate(by_cut.trend_share * 100):
        ax.text(i, v - 6, f"{v:.0f}%", ha="center", fontsize=9, color="white")
    ax.set_ylim(0, 100); ax.set_ylabel("割合（%、1,000回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("上位のどこまでを見るかで、流行に乗る型（オレンジ）の割合は大きく変わる")
    save(fig, "a838_by_cutoff.png", SRC)

    # 図3：次の100本の合計再生回数
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    b2 = np.linspace(min(keep[:, 0].min(), swit[:, 0].min()), np.quantile(swit[:, 0], .995), 60)
    ax.hist(keep[:, 0], bins=b2, color=BLUE, alpha=.6, label="今の混ぜ方のまま（流行3割）")
    ax.hist(swit[:, 0], bins=b2, color=ORANGE, alpha=.6, label="全部を流行に乗る型にする")
    ax.set_xlabel("次の100本の合計再生回数"); ax.set_yticks([])
    ax.ticklabel_format(axis="x", style="plain")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/10000:.0f}万"))
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"全部を流行に乗る型にすると、合計が増えるのは{plan['p_switch_total_higher']*100:.0f}%")
    save(fig, "a838_next100.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
