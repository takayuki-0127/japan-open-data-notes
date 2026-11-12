"""A392 「平均から3σ離れたら外れ値」は、正規でないデータで何%を外れ値と言うのか。3つの決まりの誤報と検出を数える。
python a392_three_sigma.py      # 全部を計算し直す（約1〜2分）
"""
import json
import numpy as np, pandas as pd
from common import *
SEED = 392
SRC = "出典：架空のデータ（作成者が乱数で作成、seed 392）"
RULES = ["3σ（平均±3×標準偏差）", "四分位範囲（箱ひげ図の決まり）", "中央値±3×MAD"]
DIST = {"正規": lambda r, s: r.normal(100, 15, s), "t 分布（自由度3）": lambda r, s: 100 + 15 * r.standard_t(3, s),
        "指数": lambda r, s: r.exponential(100, s), "対数正規（σ=0.5）": lambda r, s: r.lognormal(np.log(100), 0.5, s),
        "対数正規（σ=1）": lambda r, s: r.lognormal(np.log(100), 1.0, s)}


def flags(x):
    """x：行ごとに1つの集まり。3つの決まりで外れ値とされた所を True にして返す"""
    m, s = x.mean(1, keepdims=True), x.std(1, ddof=1, keepdims=True)
    f1 = np.abs(x - m) > 3 * s
    q1, med, q3 = np.percentile(x, [25, 50, 75], axis=1, keepdims=True)
    f2 = (x < q1 - 1.5 * (q3 - q1)) | (x > q3 + 1.5 * (q3 - q1))
    mad = np.median(np.abs(x - med), axis=1, keepdims=True)
    f3 = np.abs(x - med) > 3 * 1.4826 * mad
    return [f1, f2, f3]


def false_alarm(rng, reps=4000):
    rec = []
    for dn, gen in DIST.items():
        for n in (10, 30, 100, 1000):
            x = gen(rng, (reps, n))
            for rn, f in zip(RULES, flags(x)):
                rec.append(dict(dist=dn, n=n, rule=rn, flagged_pct=100 * f.mean(), any_pct=100 * f.any(1).mean(),
                                upper_pct=100 * (f & (x > np.median(x, axis=1, keepdims=True))).mean()))
            if dn.startswith("対数正規"):
                for rn, f in zip(RULES, flags(np.log(x))):
                    rec.append(dict(dist=dn + "：対数を取ってから", n=n, rule=rn, flagged_pct=100 * f.mean(), any_pct=100 * f.any(1).mean(), upper_pct=np.nan))
    return pd.DataFrame(rec)


def detection(rng, reps=4000, n=100):
    """n 件のうち k 件を10倍にした（桁を打ち間違えた）とき、その k 件を外れ値と言えた割合"""
    rec = []
    for dn in ("正規", "対数正規（σ=0.5）", "対数正規（σ=1）"):
        for k in (1, 2, 5, 10, 15, 20):
            x = DIST[dn](rng, (reps, n)); x[:, :k] *= 10
            for rn, f in zip(RULES, flags(x)):
                rec.append(dict(dist=dn, n=n, k=k, rule=rn, detected_pct=100 * f[:, :k].mean(), all_detected_pct=100 * f[:, :k].all(1).mean(),
                                clean_flagged_pct=100 * f[:, k:].mean()))
            for rn, f in zip(RULES, flags(np.log(x))):
                rec.append(dict(dist=dn, n=n, k=k, rule=rn + "：対数を取ってから", detected_pct=100 * f[:, :k].mean(), all_detected_pct=100 * f[:, :k].all(1).mean(),
                                clean_flagged_pct=100 * f[:, k:].mean()))
    return pd.DataFrame(rec)


def small_n(rng, reps=4000):
    """件数が少ないとき：1件を1,000倍にしても 3σ で外れ値と言えるか"""
    rec = []
    for n in (5, 8, 10, 11, 12, 15, 20, 30):
        x = DIST["正規"](rng, (reps, n)); x[:, 0] *= 1000
        f = flags(x)
        rec.append(dict(n=n, max_z=(n - 1) / np.sqrt(n), **{r: 100 * g[:, 0].mean() for r, g in zip(RULES, f)}))
    return pd.DataFrame(rec)


def figures(fa, de, sm):
    C = [BLUE, ORANGE, GREEN]
    d = fa[(fa.n == 1000) & ~fa.dist.str.contains("対数を取って")]
    order = list(DIST); x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    for i, r in enumerate(RULES):
        v = [float(d[(d.dist == o) & (d.rule == r)].flagged_pct.iloc[0]) for o in order]
        ax.bar(x + (i - 1) * 0.27, v, 0.27, color=C[i], label=r)
        for a, b in zip(x, v): ax.text(a + (i - 1) * 0.27, b + 0.15, f"{b:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylabel("外れ値とされた値の割合（%）"); ax.legend(frameon=False)
    ax.set_title("何も起きていないのに外れ値とされた割合（1,000件の集まり、4,000回の平均）")
    save(fig, "a392_false_flags_by_rule.png", SRC)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for a, dn in zip(ax, ("正規", "対数正規（σ=1）")):
        for i, r in enumerate(RULES):
            g = fa[(fa.dist == dn) & (fa.rule == r)]; a.plot(range(4), g.any_pct, "o-", color=C[i], label=r)
            for j, v in enumerate(g.any_pct): a.text(j, v + 2.5, f"{v:.0f}", ha="center", fontsize=8.5, color=C[i])
        a.set_xticks(range(4)); a.set_xticklabels(["10件", "30件", "100件", "1,000件"]); a.set_title(dn); a.set_ylim(0, 110)
    ax[0].set_ylabel("少なくとも1件が外れ値とされた集まりの割合（%）"); ax[0].legend(frameon=False, fontsize=9)
    fig.suptitle("何も起きていない集まりのうち、外れ値が1件以上出る割合", y=1.02)
    save(fig, "a392_any_flag_by_n.png", SRC)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for a, dn in zip(ax, ("正規", "対数正規（σ=0.5）")):
        for i, r in enumerate(RULES):
            g = de[(de.dist == dn) & (de.rule == r)]; a.plot(range(len(g)), g.detected_pct, "o-", color=C[i], label=r)
        g = de[(de.dist == dn) & (de.rule == RULES[2] + "：対数を取ってから")]; a.plot(range(len(g)), g.detected_pct, "s--", color=GRAY, label="対数を取ってから 中央値±3×MAD")
        a.set_xticks(range(len(g))); a.set_xticklabels([f"{k}件" for k in g.k]); a.set_title(dn); a.set_xlabel("100件のうち、10倍にした件数"); a.set_ylim(-3, 108)
    ax[0].set_ylabel("10倍にした値を外れ値と言えた割合（%）"); ax[1].legend(frameon=False, fontsize=9)
    fig.suptitle("本物の誤り（10倍の桁ずれ）を見つけた割合：誤りが増えると 3σ は見つけられなくなる", y=1.02)
    save(fig, "a392_detection_masking.png", SRC)


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    fa = false_alarm(rng); de = detection(rng); sm = small_n(rng)
    fa.round(3).to_csv(RES / "false_alarm.csv", index=False); de.round(2).to_csv(RES / "detection.csv", index=False); sm.round(3).to_csv(RES / "small_n.csv", index=False)
    pd.DataFrame(DIST["対数正規（σ=1）"](np.random.default_rng(SEED + 1), 100).round(2), columns=["x"]).to_csv(DATA / "example_lognormal_100.csv", index=False)
    figures(fa, de, sm)
    g = lambda dn, n, r, c: round(float(fa[(fa.dist == dn) & (fa.n == n) & (fa.rule == r)][c].iloc[0]), 2)
    h = lambda dn, k, r, c: round(float(de[(de.dist == dn) & (de.k == k) & (de.rule == r)][c].iloc[0]), 1)
    main = {"seed": SEED, "flagged_n1000": {dn: {r: g(dn, 1000, r, "flagged_pct") for r in RULES} for dn in fa.dist.unique()},
            "any_flag": {dn: {str(n): {r: g(dn, n, r, "any_pct") for r in RULES} for n in (10, 30, 100, 1000)} for dn in ("正規", "対数正規（σ=1）")},
            "detected": {dn: {str(k): {r: h(dn, k, r, "detected_pct") for r in de.rule.unique()} for k in (1, 2, 5, 10, 15, 20)} for dn in de.dist.unique()},
            "clean_flagged_k5": {dn: {r: h(dn, 5, r, "clean_flagged_pct") for r in de.rule.unique()} for dn in de.dist.unique()},
            "small_n": sm.round(2).to_dict("records")}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(main, ensure_ascii=False, indent=1))
