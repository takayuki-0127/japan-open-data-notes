"""470 めったに起きない出来事の予測は、正解率で測るとどれだけ良く見えるか（架空の予測データ、seed 470）"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *

SEED = 470
SRC = "架空の予測データ（作成者が乱数で作成、seed 470）"
PIS = [0.001, 0.005, 0.01, 0.05, 0.10]
DS = {"見分ける力なし（AUC 0.50）": 0.0, "弱い（AUC 0.76）": 1.0, "中くらい（AUC 0.92）": 2.0, "強い（AUC 0.98）": 3.0}
Phi, Phic, Pinv = stats.norm.cdf, stats.norm.sf, stats.norm.ppf


def metrics(pi, d, c):
    """点数は、起きなかった人が N(0,1)、起きた人が N(d,1)。点数が c より大きければ「起きる」と答える"""
    tpr, fpr = Phic(c - d), Phic(c)
    flagged = pi * tpr + (1 - pi) * fpr
    return dict(正解率=(pi * tpr + (1 - pi) * (1 - fpr)) * 100, 当てた割合=tpr * 100, 空振りの割合=fpr * 100,
                的中率=(pi * tpr / flagged * 100) if flagged > 0 else np.nan, 起きると答えた割合=flagged * 100)


def cut_half(pi, d):
    """起きる確率が50%を超えたら「起きる」と答えるときの境目（点数）"""
    return np.inf if d == 0 else d / 2 + np.log((1 - pi) / pi) / d


def cut_top(pi, d, share=0.10):
    """点数の上位 share を「起きる」と答えるときの境目"""
    lo, hi = -10.0, 15.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if pi * Phic(mid - d) + (1 - pi) * Phic(mid) > share: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def cut_recall(d, target=0.8): return d - Pinv(target)          # 起きた人の target を当てる境目


def grid():
    rows = []
    for pi in PIS:
        rows.append(dict(起きる割合=pi * 100, モデル="全部「起きない」と答える", AUC=np.nan, 決め方="—", 正解率=(1 - pi) * 100, 当てた割合=0.0, 空振りの割合=0.0, 的中率=np.nan, 起きると答えた割合=0.0))
        for name, d in DS.items():
            auc = Phi(d / np.sqrt(2))
            for rule, c in [("確率50%を超えたら", cut_half(pi, d)), ("上位1割を", cut_top(pi, d)), ("起きた人の8割を当てる", cut_recall(d))]:
                m = metrics(pi, d, c)
                rows.append(dict(起きる割合=pi * 100, モデル=name, AUC=round(auc, 3), 決め方=rule, **{k: (round(v, 2) if v == v else v) for k, v in m.items()}))
    return pd.DataFrame(rows)


def sweep(pi=0.01, d=2.0):
    rows = []
    for c in np.linspace(-1, 6, 141):
        m = metrics(pi, d, c); rows.append(dict(境目=round(c, 2), **{k: round(v, 4) for k, v in m.items()},
                                                 千人あたりの見逃し=round(pi * (1 - m["当てた割合"] / 100) * 1000, 3), 千人あたりの空振り=round((1 - pi) * m["空振りの割合"] / 100 * 1000, 3)))
    return pd.DataFrame(rows)


def noise(rng, pi, d, n, rep=2000):
    """n 人の確かめ用データで測ったときの振れ（上位1割を「起きる」と答える）"""
    acc, rec, auc, pos = [], [], [], []
    c = cut_top(pi, d)
    for _ in range(rep):
        y = rng.random(n) < pi; s = rng.normal(0, 1, n) + d * y
        pred = s > c; k = y.sum(); pos.append(k)
        acc.append(np.mean(pred == y) * 100); rec.append(pred[y].mean() * 100 if k else np.nan)
        if k and k < n:
            r = stats.rankdata(s); auc.append((r[y].sum() - k * (k + 1) / 2) / (k * (n - k)))
        else: auc.append(np.nan)
    return dict(起きる割合=pi * 100, 人数=n, 起きた人の平均=round(np.mean(pos), 1), 正解率_標準偏差=round(np.nanstd(acc), 2), 当てた割合_平均=round(np.nanmean(rec), 1),
                当てた割合_標準偏差=round(np.nanstd(rec), 1), AUC_標準偏差=round(np.nanstd(auc), 3), 起きた人が0人の割合=round(np.mean(np.array(pos) == 0) * 100, 1))


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    g = grid(); g.to_csv(RES / "metrics_grid.csv", index=False)
    sw = sweep(); sw.to_csv(RES / "threshold_sweep.csv", index=False)
    nz = pd.DataFrame([noise(rng, pi, 2.0, n) for pi in (0.001, 0.01, 0.05) for n in (1000, 10000, 100000)]); nz.to_csv(RES / "test_set_noise.csv", index=False)
    # 式の確かめ：100万人の乱数
    y = rng.random(1_000_000) < 0.01; s = rng.normal(0, 1, y.size) + 2.0 * y; c = cut_top(0.01, 2.0); pred = s > c
    chk = dict(正解率_乱数=round(np.mean(pred == y) * 100, 2), 正解率_式=round(metrics(0.01, 2.0, c)["正解率"], 2), 当てた割合_乱数=round(pred[y].mean() * 100, 1), 当てた割合_式=round(metrics(0.01, 2.0, c)["当てた割合"], 1))
    pd.DataFrame({"起きたか": y[:300].astype(int), "点数": np.round(s[:300], 3)}).to_csv(DATA / "example_scores.csv", index=False)
    # 正解率で「全部起きない」に負ける組み合わせ
    base = g[g.モデル == "全部「起きない」と答える"].set_index("起きる割合").正解率
    m = g[g.モデル != "全部「起きない」と答える"].copy(); m["全部起きないとの差"] = m.正解率 - m.起きる割合.map(base)
    m.to_csv(RES / "vs_all_negative.csv", index=False)
    useful = m[m.モデル != "見分ける力なし（AUC 0.50）"]
    lose = useful[useful.全部起きないとの差 < -1e-9]
    cnt = dict(組み合わせ=len(useful), 正解率で負ける=len(lose), 確率50で負ける=int((useful[useful.決め方 == "確率50%を超えたら"].全部起きないとの差 < -1e-9).sum()),
               確率50の最大の上回り=round(float(useful[useful.決め方 == "確率50%を超えたら"].全部起きないとの差.max()), 2))

    # 図1：正解率
    fig, ax = plt.subplots(figsize=(8.6, 4.3)); x = np.arange(len(PIS)); w = 0.2
    ser = [("全部「起きない」と答える", "—", GRAY, "全部「起きない」と答える"), ("中くらい（AUC 0.92）", "確率50%を超えたら", LIGHT, "AUC 0.92：確率50%を超えたら「起きる」"),
           ("中くらい（AUC 0.92）", "上位1割を", BLUE, "AUC 0.92：上位1割を「起きる」"), ("中くらい（AUC 0.92）", "起きた人の8割を当てる", ORANGE, "AUC 0.92：起きた人の8割を当てる")]
    for i, (mo, ru, col, lab) in enumerate(ser):
        d = g[(g.モデル == mo) & (g.決め方 == ru)]; b = ax.bar(x + (i - 1.5) * w, d.正解率, w, color=col, label=lab)
        for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.15, f"{r.get_height():.1f}", ha="center", fontsize=7.5, rotation=90)
    ax.set_xticks(x); ax.set_xticklabels([f"{p*100:g}%" for p in PIS]); ax.set_ylim(80, 104); ax.set_xlabel("出来事が起きる割合"); ax.set_ylabel("正解率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2); ax.set_title("正解率で比べると")
    save(fig, "a470_accuracy.png", SRC + "。式の値", y=-0.14)
    # 図2：起きる割合1%での物差し
    fig, ax = plt.subplots(figsize=(9, 4.3)); d1 = g[g.起きる割合 == 1.0]
    labs = ["正解率", "当てた割合", "的中率"]; x = np.arange(3); w = 0.16
    ser = [("全部「起きない」と答える", "—", GRAY, "全部「起きない」"), ("見分ける力なし（AUC 0.50）", "上位1割を", "#d8d7d2", "AUC 0.50：上位1割"),
           ("弱い（AUC 0.76）", "上位1割を", LIGHT, "AUC 0.76：上位1割"), ("中くらい（AUC 0.92）", "上位1割を", BLUE, "AUC 0.92：上位1割"), ("強い（AUC 0.98）", "上位1割を", ORANGE, "AUC 0.98：上位1割")]
    for i, (mo, ru, col, lab) in enumerate(ser):
        r_ = d1[(d1.モデル == mo) & (d1.決め方 == ru)].iloc[0]; v = [r_.正解率, r_.当てた割合, 0 if r_.的中率 != r_.的中率 else r_.的中率]
        b = ax.bar(x + (i - 2) * w, v, w, color=col, label=lab)
        for r, val in zip(b, v): ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1, f"{val:.0f}" if val >= 10 else f"{val:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(["正解率", "起きた人のうち当てた割合", "「起きる」と答えた中で\n本当に起きた割合"]); ax.set_ylabel("%"); ax.set_ylim(0, 128)
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper right"); ax.set_title("同じ予測を3つの物差しで測ると（起きる割合1%）")
    save(fig, "a470_metrics_side_by_side.png", SRC + "。式の値")
    # 図3：境目を動かす
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    ax.plot(sw.起きると答えた割合, sw.正解率, color=GRAY, label="正解率"); ax.plot(sw.起きると答えた割合, sw.当てた割合, color=BLUE, label="起きた人のうち当てた割合")
    ax.plot(sw.起きると答えた割合, sw.的中率, color=ORANGE, label="「起きる」と答えた中で本当に起きた割合")
    ax.set_xscale("log"); ax.set_xlim(0.05, 60); ax.set_xticks([0.1, 1, 10, 50]); ax.set_xticklabels(["0.1", "1", "10", "50"]); ax.set_xlabel("「起きる」と答えた割合（%、対数の目盛り）"); ax.set_ylabel("%")
    ax.set_ylim(-3, 140); ax.set_yticks([0, 20, 40, 60, 80, 100]); ax.legend(frameon=False, fontsize=8.5, loc="upper left"); ax.set_title("境目を動かしたとき（AUC 0.92、起きる割合1%）", fontsize=11)
    ax = axes[1]
    ax.plot(sw.起きると答えた割合, sw.千人あたりの見逃し, color=BLUE, label="見逃し（起きたのに「起きない」）"); ax.plot(sw.起きると答えた割合, sw.千人あたりの空振り, color=ORANGE, label="空振り（起きないのに「起きる」）")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.05, 60); ax.set_ylim(0.05, 600); ax.set_xticks([0.1, 1, 10, 50]); ax.set_xticklabels(["0.1", "1", "10", "50"])
    ax.set_yticks([0.1, 1, 10, 100]); ax.set_yticklabels(["0.1", "1", "10", "100"]); ax.set_xlabel("「起きる」と答えた割合（%、対数の目盛り）"); ax.set_ylabel("1,000人あたりの人数（対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5); ax.set_title("見逃しと空振り", fontsize=11)
    save(fig, "a470_threshold_sweep.png", SRC + "。式の値")

    main = {"count": cnt, "check": chk, "pi1": g[g.起きる割合 == 1.0].to_dict("records"), "noise": nz.to_dict("records")}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    pd.set_option("display.width", 250)
    print(g.to_string()); print(cnt, chk); print(nz.to_string())
    for sh in (0.1, 0.5, 1, 2, 5, 10, 20):
        r = sw.iloc[(sw.起きると答えた割合 - sh).abs().argmin()]; print(r.to_dict())
