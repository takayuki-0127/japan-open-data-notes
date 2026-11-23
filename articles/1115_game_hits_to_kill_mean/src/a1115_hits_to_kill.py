"""1115 平均のダメージで敵の体力を割って「何回で倒せるか」を出すと、実際の回数とどれだけずれるのか？（架空のデータ）

作成者が置いた架空のゲームの数値。1回のダメージ＝攻撃力×（0.9〜1.1の一様な振れ）×（会心なら会心の倍率）。
基本は攻撃力1,000・会心率20%・会心の倍率1.5倍（1回の平均1,100）、敵の体力10,000。
(1) 「体力÷平均」の見込み（9.09回）と、20万回倒したときの実際の回数（平均・真ん中・90%の位置・分布）を比べる
(2) 最後の1回であふれたダメージと、回数×平均＝体力＋あふれの関係を確かめる
(3) 同じ敵を10体続けて倒したときの合計の回数と、「合計の体力÷平均」の見込み
(4) 確かめ：1回の平均を1,100にそろえたまま振れ方を変えた4通り×敵の体力5通りの20通り
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1115
SRC = "架空のゲームの数値（作成者が置いた攻撃力・会心率・敵の体力からの乱数、seed 1115）"
LO, HI = 0.9, 1.1
MEAN = 1100.0
HP = 10000.0
FIGHTS = 200000
GRID_FIGHTS = 50000
SERIES = 10
# 1回の平均を1,100にそろえた振れ方（会心率, 会心の倍率）
STYLES = {"振れ±10%だけ（会心なし）": (0.0, 1.0), "基本（会心20%・1.5倍）": (0.20, 1.5),
          "会心10%・3倍": (0.10, 3.0), "会心50%・2倍": (0.50, 2.0)}
HPS = [2000.0, 5000.0, 10000.0, 20000.0, 50000.0]


def r(x, d=4):
    return round(float(x), d)


def atk_for(crit, mult):
    return MEAN / (1 + crit * (mult - 1))


def fight(rng, n, hp, crit, mult, chunk=20000):
    """n 回倒す。倒すまでの回数と、最後の1回であふれたダメージを返す"""
    atk = atk_for(crit, mult)
    kmax = int(np.ceil(hp / (atk * LO))) + 1
    hits, over = [], []
    for s in range(0, n, chunk):
        k = min(chunk, n - s)
        d = atk * rng.uniform(LO, HI, (k, kmax))
        d = np.where(rng.random((k, kmax)) < crit, d * mult, d)
        cs = d.cumsum(1)
        h = (cs < hp).sum(1) + 1
        hits.append(h)
        over.append(cs[np.arange(k), h - 1] - hp)
    return np.concatenate(hits), np.concatenate(over)


def summarize(h, over, hp):
    est = hp / MEAN
    ce = int(np.ceil(est))
    return {"hp": hp, "estimate_hp_over_mean": r(est), "estimate_ceil": ce,
            "mean_hits": r(h.mean()), "median_hits": r(np.median(h)), "p10_hits": r(np.quantile(h, 0.1)),
            "p90_hits": r(np.quantile(h, 0.9)), "min_hits": int(h.min()), "max_hits": int(h.max()),
            "gap_mean_minus_estimate": r(h.mean() - est), "gap_ratio_pct": round((h.mean() / est - 1) * 100, 2),
            "within_floor_estimate_pct": round((h <= np.floor(est)).mean() * 100, 2),
            "within_ceil_estimate_pct": round((h <= ce).mean() * 100, 2),
            "more_than_ceil_pct": round((h > ce).mean() * 100, 2),
            "mean_overkill": r(over.mean(), 2), "mean_overkill_in_hits": r(over.mean() / MEAN),
            "check_mean_hits_times_mean": r(h.mean() * MEAN, 1), "check_hp_plus_overkill": r(hp + over.mean(), 1)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setting": {"mean_damage": MEAN, "hp": HP, "spread": [LO, HI], "fights": FIGHTS,
                       "base_attack": r(atk_for(0.2, 1.5), 2), "base_crit": 0.2, "base_mult": 1.5}}

    # (1)(2) 基本
    h, over = fight(rng, FIGHTS, HP, 0.20, 1.5)
    out["base"] = summarize(h, over, HP)
    dist = pd.Series(h).value_counts().sort_index()
    dist = pd.DataFrame({"hits": dist.index, "fights": dist.values, "share_pct": np.round(dist.values / FIGHTS * 100, 2)})
    dist.to_csv(RES / "base_hits_dist.csv", index=False)
    out["base_dist"] = dist.to_dict("records")
    pd.DataFrame({"fight": np.arange(1, 2001), "hits": h[:2000], "overkill": np.round(over[:2000], 1)}).to_csv(
        DATA / "fights_first2000.csv", index=False)

    # (3) 10体続けて
    tot = np.zeros(FIGHTS // 10, dtype=int)
    for _ in range(SERIES):
        hh, _o = fight(rng, FIGHTS // 10, HP, 0.20, 1.5)
        tot += hh
    est_total = SERIES * HP / MEAN
    out["series10"] = {"enemies": SERIES, "runs": FIGHTS // 10, "total_hp": SERIES * HP, "estimate_total_hp_over_mean": r(est_total),
                       "estimate_total_ceil": int(np.ceil(est_total)),
                       "mean_total_hits": r(tot.mean()), "gap": r(tot.mean() - est_total),
                       "estimate_ceil_each_times10": int(SERIES * np.ceil(HP / MEAN)),
                       "within_estimate_ceil_total_pct": round((tot <= np.ceil(est_total)).mean() * 100, 2),
                       "within_ceil_each_times10_pct": round((tot <= SERIES * np.ceil(HP / MEAN)).mean() * 100, 2),
                       "p10": r(np.quantile(tot, 0.1)), "p90": r(np.quantile(tot, 0.9))}

    # (4) 20通り
    gr = []
    for name, (c, m) in STYLES.items():
        for hp in HPS:
            g_rng = np.random.default_rng([SEED, int(c * 100), int(m * 10), int(hp)])
            hh, oo = fight(g_rng, GRID_FIGHTS, hp, c, m)
            s = summarize(hh, oo, hp)
            gr.append({"style": name, "crit_pct": round(c * 100), "crit_mult": m, "attack": r(atk_for(c, m), 2), **s})
    gr = pd.DataFrame(gr)
    gr.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {
        "n": len(gr), "fights_each": GRID_FIGHTS,
        "gap_range": [float(gr.gap_mean_minus_estimate.min()), float(gr.gap_mean_minus_estimate.max())],
        "gap_ratio_pct_range": [float(gr.gap_ratio_pct.min()), float(gr.gap_ratio_pct.max())],
        "mean_above_estimate_count": int((gr.gap_mean_minus_estimate > 0).sum()),
        "overkill_in_hits_range": [float(gr.mean_overkill_in_hits.min()), float(gr.mean_overkill_in_hits.max())],
        "within_floor_range": [float(gr.within_floor_estimate_pct.min()), float(gr.within_floor_estimate_pct.max())],
    }

    # 図1：基本の回数の分布
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar(dist.hits, dist.share_pct, color=BLUE, width=0.7)
    for x, v in zip(dist.hits, dist.share_pct):
        if v >= 0.5:
            ax.text(x, v + 0.8, f"{v}%", ha="center", fontsize=8.5)
    est = HP / MEAN
    ax.axvline(est, color=ORANGE, ls="--", lw=1.5)
    ax.text(est - 0.1, dist.share_pct.max() * 1.08, f"体力÷平均\n{r(est)}回", color=ORANGE, ha="right", fontsize=9)
    ax.axvline(h.mean(), color=INK, ls=":", lw=1.5)
    ax.text(h.mean() + 0.1, dist.share_pct.max() * 1.08, f"実際の平均\n{r(h.mean())}回", color=INK, ha="left", fontsize=9)
    ax.set_ylim(0, dist.share_pct.max() * 1.3)
    ax.set_xticks(dist.hits)
    ax.set_xlabel("倒すまでに打った回数")
    ax.set_ylabel("割合（%）")
    ax.set_title("体力10,000・1回の平均1,100で、倒すまでの回数（20万回）")
    save(fig, "a1115_dist.png", SRC)

    # 図2：体力÷平均と、実際の平均とのずれ（回）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for (name, _), col in zip(STYLES.items(), [GRAY, BLUE, ORANGE, GREEN]):
        s = gr[gr["style"] == name]
        ax.plot(s.estimate_hp_over_mean, s.gap_mean_minus_estimate, marker="o", color=col, label=name)
    ax.set_xscale("log")
    xt = [r(x / MEAN) for x in HPS]
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticks(xt, [f"{x}" for x in xt])
    ax.set_ylim(0, gr.gap_mean_minus_estimate.max() * 1.25)
    ax.set_xlabel("体力÷平均（見込みの回数）")
    ax.set_ylabel("実際の平均の回数−見込み（回）")
    ax.set_title("見込みより多くかかった回数（20通り、各5万回）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1115_gap.png", SRC)

    # 図3：見込みの回数（切り捨て）以内に倒せた割合
    fig, ax = plt.subplots(figsize=(7, 4.2))
    xs = np.arange(len(HPS))
    w = 0.2
    for i, ((name, _), col) in enumerate(zip(STYLES.items(), [GRAY, BLUE, ORANGE, GREEN])):
        s = gr[gr["style"] == name]
        ax.bar(xs + (i - 1.5) * w, s.within_ceil_estimate_pct, w, color=col, label=name)
    ax.set_xticks(xs, [f"体力{int(hp):,}\n（見込み{r(hp / MEAN)}回）" for hp in HPS], fontsize=8.5)
    ax.set_ylim(0, 130)
    ax.set_ylabel("見込みを切り上げた回数以内に倒せた割合（%）")
    ax.set_title("「体力÷平均」を切り上げた回数で倒せた割合")
    ax.legend(frameon=False, fontsize=8, loc="upper center", ncol=2)
    save(fig, "a1115_within.png", SRC)

    (RES / "a1115_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "base_dist"}, ensure_ascii=False, indent=1))
    print(dist)
    print(gr[["style", "hp", "estimate_hp_over_mean", "mean_hits", "gap_mean_minus_estimate", "gap_ratio_pct",
              "within_floor_estimate_pct", "within_ceil_estimate_pct", "p90_hits", "mean_overkill_in_hits"]].to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
