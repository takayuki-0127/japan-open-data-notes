"""913 不良率の月ごとの上下は、工程の変化か偶然か？（架空のデータ）

架空の工場で、毎月同じ数の部品（基本 2,000個）を作り、外観の検査で不良を数える。
本当の不良率（基本 1.0%）を作成者が置き、月の不良の件数は二項分布で引く。
「悪くなった」と読む5つの決まりが、本当の不良率が変わらない1年で何回鳴るか（空振り）と、
本当の不良率が1.5倍に上がったとき何か月で鳴るかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 913
SRC = "架空の工場の月ごとの不良（作成者が乱数で作成、seed 913）"
RULES = ["①前月比で3割以上の悪化", "②過去12か月でいちばん高い", "③p管理図の3σの線を超えた",
         "④直近3か月の合計で3σの線を超えた", "⑤月の散らばりから引いた線を超えた"]
SHORT = ["①前月比3割", "②12か月で最高", "③p管理図3σ", "④3か月合計3σ", "⑤散らばりの線"]
T_BASE = 27            # 変化の前の月数（評価は 16〜27か月目の1年）
T_AFTER = 12           # 変化の後の月数
EVAL = slice(15, 27)   # 空振りを数える1年（16〜27か月目）


def make(rng, f, n, p, tau=0.0, ratio=1.0):
    """f 工場 × 39か月の不良件数。tau：本当の不良率の月ごとの揺れ（対数の標準偏差）。ratio：28か月目からの倍率"""
    T = T_BASE + T_AFTER
    pt = np.full((f, T), p)
    pt[:, T_BASE:] *= ratio
    if tau > 0:
        pt = pt * np.exp(rng.normal(-tau ** 2 / 2, tau, (f, T)))
    pt = np.clip(pt, 0, 1)
    d = rng.binomial(n, pt)
    return d, pt


def triggers(d, n):
    """各月（16か月目以降）で5つの決まりが鳴ったか。返り値 (rule, f, T) の真偽"""
    f, T = d.shape
    r = d / n
    out = np.zeros((5, f, T), dtype=bool)
    for t in range(15, T):
        prev = r[:, t - 1]
        out[0, :, t] = np.where(prev > 0, r[:, t] >= 1.3 * prev, d[:, t] > 0)
        out[1, :, t] = r[:, t] > r[:, t - 12:t].max(1)
        pbar = d[:, t - 12:t].sum(1) / (12 * n)
        out[2, :, t] = r[:, t] > pbar + 3 * np.sqrt(pbar * (1 - pbar) / n)
        pbar3 = d[:, t - 15:t - 3].sum(1) / (12 * n)
        r3 = d[:, t - 2:t + 1].sum(1) / (3 * n)
        out[3, :, t] = r3 > pbar3 + 3 * np.sqrt(pbar3 * (1 - pbar3) / (3 * n))
        w = r[:, t - 12:t]
        mr = np.abs(np.diff(w, axis=1)).mean(1)
        out[4, :, t] = r[:, t] > w.mean(1) + 2.66 * mr
    return out


def summarize(n, p, tau, ratio, f, seed):
    rng = np.random.default_rng(seed)
    d0, _ = make(rng, f, n, p, tau, 1.0)
    tr0 = triggers(d0, n)
    d1, _ = make(rng, f, n, p, tau, ratio)
    tr1 = triggers(d1, n)
    rows = []
    for i in range(5):
        fy = tr0[i][:, EVAL].sum(1)
        after = tr1[i][:, T_BASE:]
        hit = after.any(1)
        first = np.where(hit, after.argmax(1) + 1, np.nan)
        f3 = tr0[i][:, 15:18].any(1)
        rows.append({"rule": RULES[i], "false_per_year": round(float(fy.mean()), 2),
                     "false_per_month": round(float(fy.mean() / 12), 3),
                     "false_any_within_3": round(float(f3.mean()), 3),
                     "share_year_any_false": round(float((fy > 0).mean()), 3),
                     "detect_within_1": round(float((first <= 1).mean()), 3),
                     "detect_within_3": round(float((first <= 3).mean()), 3),
                     "detect_within_12": round(float(hit.mean()), 3),
                     "months_to_detect_median": float(np.nanmedian(first)) if hit.any() else None})
    return rows


def main():
    t0 = time.time()
    out = {}
    N0, P0 = 2000, 0.010

    # 1) 偶然だけの月の上下（本当の不良率は変わらない）。件数ごとの式と、20,000工場×12か月の数え上げ
    rng = np.random.default_rng(SEED)
    rows = []
    for n in [500, 1000, 2000, 5000, 10000, 20000]:
        d = rng.binomial(n, P0, (20000, 13))
        r = d / n
        mom = r[:, 1:] / np.where(r[:, :-1] > 0, r[:, :-1], np.nan) - 1
        yr = r[:, 1:]
        rows.append({"n_per_month": n, "expected_defects": n * P0,
                     "rel_sd_formula": round(float(np.sqrt((1 - P0) / (n * P0))), 3),
                     "rate_p10_pct": round(float(np.quantile(r, .1) * 100), 2),
                     "rate_p90_pct": round(float(np.quantile(r, .9) * 100), 2),
                     "share_mom_abs_ge_30": round(float(np.nanmean(np.abs(mom) >= 0.3)), 3),
                     "share_mom_up_ge_30": round(float(np.nanmean(mom >= 0.3)), 3),
                     "year_max_over_min_median": round(float(np.median(yr.max(1) / np.maximum(yr.min(1), 1 / n))), 2)})
    chance = pd.DataFrame(rows)
    chance.to_csv(RES / "chance_swing_by_volume.csv", index=False)
    out["chance_swing_by_volume"] = rows

    # 2) 基本の置き方（月2,000個・1.0%・揺れなし）で、5つの決まりの空振りと、1.5倍に上がったときの見つけ方
    base = summarize(N0, P0, 0.0, 1.5, 20000, SEED + 1)
    pd.DataFrame(base).to_csv(RES / "rules_base.csv", index=False)
    out["rules_base"] = base
    # ②の目安：件数の同じ月がなければ、13か月のうち今月がいちばん高い確率は1/13、1年で12/13回
    out["rule2_no_ties_per_year"] = round(12 / 13, 2)

    # 2b) 上がり方を1.2・1.5・2.0倍に変えたときの3か月以内の見つけ方（基本の件数）
    rows = []
    for ratio in [1.2, 1.5, 2.0]:
        for r in summarize(N0, P0, 0.0, ratio, 20000, SEED + 2 + int(ratio * 10)):
            rows.append({"ratio": ratio, **r})
    pd.DataFrame(rows).to_csv(RES / "rules_by_change_size.csv", index=False)
    out["rules_by_change_size"] = rows

    # 3) 確かめ：月の個数（500・2,000・10,000）×不良率（0.5・1・2%）×本当の不良率の月ごとの揺れ（0・0.15・0.3）
    rows = []
    for n in [500, 2000, 10000]:
        for p in [0.005, 0.01, 0.02]:
            for tau in [0.0, 0.15, 0.3]:
                for r in summarize(n, p, tau, 1.5, 4000, SEED * 10 + n // 100 + int(p * 1000) + int(tau * 100)):
                    rows.append({"n": n, "p": p, "tau": tau, **r})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "robust_grid.csv", index=False)
    rng_rows = []
    for i, rule in enumerate(RULES):
        g = grid[grid.rule == rule]
        g0 = g[g.tau == 0]
        gt = g[g.tau == 0.3]
        rng_rows.append({"rule": rule,
                         "false_min": float(g.false_per_year.min()), "false_max": float(g.false_per_year.max()),
                         "false_tau0_min": float(g0.false_per_year.min()), "false_tau0_max": float(g0.false_per_year.max()),
                         "false_tau03_min": float(gt.false_per_year.min()), "false_tau03_max": float(gt.false_per_year.max()),
                         "det3_min": float(g.detect_within_3.min()), "det3_max": float(g.detect_within_3.max())})
    out["robust_range"] = rng_rows
    # 揺れの大きさごと（27通りのうち各9通り）の③と⑤の空振りの中央値
    piv = grid[grid.rule.isin([RULES[2], RULES[4]])].groupby(["rule", "tau", "n"])[["false_per_year", "detect_within_3"]].median().reset_index()
    out["robust_false_by_tau_n"] = piv.to_dict("records")

    # data：1工場の39か月（本当の不良率は1.0%のまま）
    g = np.random.default_rng(SEED * 100)
    d, _ = make(g, 1, N0, P0)
    r = d[0] / N0
    dd = pd.DataFrame({"month": np.arange(1, len(r) + 1), "made": N0, "defects": d[0], "rate_pct": np.round(r * 100, 3)})
    dd["mom_pct"] = np.round((dd.rate_pct / dd.rate_pct.shift(1) - 1) * 100, 1)
    dd.to_csv(DATA / "one_factory_39months.csv", index=False)
    tr = triggers(d, N0)
    out["data_one_factory"] = {"rate_min_pct": float(dd.rate_pct.min()), "rate_max_pct": float(dd.rate_pct.max()),
                               "months_mom_up_ge_30": int((dd.mom_pct >= 30).sum()),
                               "triggers_month16_39": {SHORT[i]: int(tr[i][0, 15:].sum()) for i in range(5)}}
    json.dump(out, open(RES / "a913_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1工場の39か月（ずっと1.0%）
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.plot(dd.month, dd.rate_pct, color=BLUE, marker="o", ms=3.5, lw=1)
    ax.axhline(1.0, color=INK, lw=.8, ls="--")
    ax.text(39.8, 1.02, "本当の1.0%", fontsize=8.5, va="bottom")
    up = dd[dd.mom_pct >= 30]
    ax.scatter(up.month, up.rate_pct, s=55, facecolor="none", edgecolor=ORANGE, lw=1.4, zorder=3,
               label=f"前月比で3割以上の悪化に見えた月（{len(up)}か月）")
    ax.set_xlim(0, 44)
    ax.set_xlabel("月"); ax.set_ylabel("その月の不良率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("本当の不良率がずっと1.0%でも、月の不良率はこれだけ上下する（月2,000個）")
    save(fig, "a913_one_factory.png", SRC)

    # 図2：5つの決まりの空振りと見つけ方（基本）
    b = pd.DataFrame(base)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.8))
    y = np.arange(5)[::-1]
    axes[0].barh(y, b.false_per_year, color=GRAY)
    for i, v in enumerate(b.false_per_year):
        axes[0].text(v + .05, y[i], f"{v:.2f}回", va="center", fontsize=8.5)
    axes[0].set_yticks(y); axes[0].set_yticklabels(SHORT)
    axes[0].set_xlabel("変わらない1年で鳴った回数（平均）"); axes[0].set_xlim(0, b.false_per_year.max() * 1.35)
    axes[1].barh(y, b.detect_within_3 * 100, color=BLUE)
    for i, v in enumerate(b.detect_within_3 * 100):
        axes[1].text(v + 1, y[i], f"{v:.0f}%", va="center", fontsize=8.5)
    axes[1].set_yticks(y); axes[1].set_yticklabels([])
    axes[1].set_xlabel("1.5倍に上がって3か月以内に鳴った割合（%）"); axes[1].set_xlim(0, 115)
    fig.suptitle("よく鳴る決まりは空振りも多い（月2,000個・不良率1.0%、20,000工場）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a913_rules.png", SRC)

    # 図3：本当の不良率の月ごとの揺れと、③・⑤の空振り
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.6), sharey=True)
    for ax, rule, ttl in [(axes[0], RULES[2], "③p管理図の3σ"), (axes[1], RULES[4], "⑤月の散らばりから引いた線")]:
        sub = piv[piv.rule == rule]
        for n, c in [(500, LIGHT), (2000, BLUE), (10000, INK)]:
            s = sub[sub.n == n]
            ax.plot(s.tau, s.false_per_year, marker="o", color=c, label=f"月{n:,}個")
        ax.set_xticks([0, .15, .3]); ax.set_xlabel("本当の不良率の月ごとの揺れ（対数の標準偏差）", fontsize=10)
        ax.set_title(ttl, fontsize=11)
    axes[0].set_ylabel("変わらない1年の空振り（回）")
    axes[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("月ごとの揺れがあると、p管理図の線は個数が多いほど空振りが増える\n（不良率0.5・1・2%の3通りの中央値）", fontsize=12)
    fig.tight_layout()
    save(fig, "a913_tau.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
