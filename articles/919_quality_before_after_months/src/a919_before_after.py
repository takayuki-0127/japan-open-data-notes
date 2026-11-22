"""919 改善の前後で不良率を比べるとき、何か月見ればよいのか？（架空のデータ）

架空の工場の1つの工程。月に N 個作り、本当の不良率は改善の前 1.0%、後 0.7%（30%減）と置く。
本当の不良率は月ごとに少し上下する（月の振れ：対数の標準偏差 s）。その月の不良の件数は二項分布で引く。
前後 k か月ずつの記録で、(1) 後のほうが低く見えるか、(2) 個数を合算した比べ方（二項の検定）、
(3) 月ごとの不良率を1点として比べる比べ方（ウェルチの t 検定）で「下がった」と言えるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 919
SRC = "架空の工場の月ごとの不良（作成者が乱数で作成、seed 919）"
P0 = 0.010
N_REP = 4000
KS = [1, 2, 3, 4, 6, 9, 12, 18, 24]


def months(rng, p, k, n, s, reps=N_REP, trend=None):
    """reps×k の不良の件数と本当の率。trend は月ごとの本当の率に掛ける倍率（長さ k）"""
    r = p * np.exp(rng.normal(-s ** 2 / 2, s, (reps, k))) if s > 0 else np.full((reps, k), p)
    if trend is not None:
        r = r * trend[None, :]
    return rng.binomial(n, np.clip(r, 0, 1)), r


def compare(rng, k, n, s, effect, trend_b=None, trend_a=None):
    xb, _ = months(rng, P0, k, n, s, trend=trend_b)
    xa, _ = months(rng, P0 * (1 - effect), k, n, s, trend=trend_a)
    pb, pa = xb.sum(1) / (n * k), xa.sum(1) / (n * k)
    pp = (xb.sum(1) + xa.sum(1)) / (2 * n * k)
    se = np.sqrt(pp * (1 - pp) * 2 / (n * k))
    z = np.where(se > 0, (pb - pa) / np.where(se > 0, se, 1), 0)
    pooled = (stats.norm.sf(np.abs(z)) * 2 < 0.05) & (pa < pb)
    if k >= 2:
        t = stats.ttest_ind(xb / n, xa / n, axis=1, equal_var=False)
        pv = np.nan_to_num(t.pvalue, nan=1.0)
        monthly = (pv < 0.05) & (pa < pb)
        mon = float(monthly.mean())
    else:
        mon = None
    red = np.where(pb > 0, 1 - pa / np.where(pb > 0, pb, 1), 0)
    return {"looked_lower": float((pa < pb).mean()), "pooled_sig": float(pooled.mean()), "monthly_sig": mon,
            "est_reduction_p10": float(np.quantile(red, .1)), "est_reduction_p50": float(np.quantile(red, .5)),
            "est_reduction_p90": float(np.quantile(red, .9))}


def needed(rows, key, th=0.8):
    for r in rows:
        if r[key] is not None and r[key] >= th:
            return r["months"]
    return None


def main():
    rng = np.random.default_rng(SEED)
    N, S, EFF = 2000, 0.2, 0.30

    # 1) 例：前12か月・後12か月（data に置く）
    xb, rb = months(rng, P0, 12, N, S, reps=1)
    xa, ra = months(rng, P0 * (1 - EFF), 12, N, S, reps=1)
    ex = pd.DataFrame({"month": np.arange(1, 25), "period": ["前"] * 12 + ["後"] * 12, "produced": N,
                       "defects": np.r_[xb[0], xa[0]], "true_rate": np.round(np.r_[rb[0], ra[0]], 6)})
    ex["rate"] = (ex.defects / ex.produced).round(5)
    ex.to_csv(DATA / "monthly_example_24.csv", index=False)
    ex_last = {f"k{k}": {"before": round(float(ex.defects[12 - k:12].sum() / (N * k)), 5),
                         "after": round(float(ex.defects[12:12 + k].sum() / (N * k)), 5)} for k in [1, 3, 12]}

    # 2) 基本の置き方で、k か月ずつ
    base, null = [], []
    for k in KS:
        base.append({"months": k, **compare(np.random.default_rng(SEED * 10 + k), k, N, S, EFF)})
        null.append({"months": k, **compare(np.random.default_rng(SEED * 20 + k), k, N, S, 0.0)})
    base_df, null_df = pd.DataFrame(base).round(4), pd.DataFrame(null).round(4)
    base_df.to_csv(RES / "base_by_months.csv", index=False)
    null_df.to_csv(RES / "no_effect_by_months.csv", index=False)

    # 3) 月の振れ s と月産 N を変えると、何か月要るか（効果30%）
    grid = []
    for s in [0.0, 0.2, 0.4]:
        for n in [500, 2000, 10000]:
            rows = [{"months": k, **compare(np.random.default_rng(SEED * 1000 + int(s * 10) * 100 + n // 100 + k), k, n, s, EFF)} for k in KS]
            nrows = [{"months": k, **compare(np.random.default_rng(SEED * 3000 + int(s * 10) * 100 + n // 100 + k), k, n, s, 0.0)} for k in [3, 6]]
            grid.append({"month_sd": s, "produced_per_month": n,
                         "months_needed_monthly80": needed(rows, "monthly_sig"),
                         "months_needed_pooled80": needed(rows, "pooled_sig"),
                         "monthly_sig_k3": rows[2]["monthly_sig"], "monthly_sig_k6": rows[4]["monthly_sig"],
                         "pooled_sig_k3": rows[2]["pooled_sig"], "pooled_sig_k6": rows[4]["pooled_sig"],
                         "no_effect_pooled_sig_k3": nrows[0]["pooled_sig"], "no_effect_pooled_sig_k6": nrows[1]["pooled_sig"],
                         "no_effect_monthly_sig_k6": nrows[1]["monthly_sig"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_months_needed.csv", index=False)

    # 4) 効果の大きさを変えると（基本の s=0.2、N=2000）
    eff = []
    for e in [0.1, 0.3, 0.5]:
        rows = [{"months": k, **compare(np.random.default_rng(SEED * 5000 + int(e * 10) * 100 + k), k, N, S, e)} for k in KS]
        eff.append({"effect": e, "months_needed_monthly80": needed(rows, "monthly_sig"),
                    "months_needed_pooled80": needed(rows, "pooled_sig"),
                    "looked_lower_k1": rows[0]["looked_lower"], "looked_lower_k3": rows[2]["looked_lower"],
                    "monthly_sig_k12": rows[KS.index(12)]["monthly_sig"]})
    eff = pd.DataFrame(eff)
    eff.to_csv(RES / "by_effect_size.csv", index=False)

    # 5) 改善の効果がなくても、本当の不良率がゆっくり下がり続けていると（年に10%）
    drift = []
    for k in [3, 6, 12]:
        mth = np.arange(-k, k)  # 改善の時点を0とした月
        tr = 0.9 ** (mth / 12)
        drift.append({"months": k, **compare(np.random.default_rng(SEED * 7000 + k), k, N, S, 0.0, tr[:k], tr[k:])})
    drift = pd.DataFrame(drift).round(4)
    drift.to_csv(RES / "drift_no_effect.csv", index=False)

    out = {"settings": {"base_rate": P0, "effect": EFF, "after_rate": P0 * (1 - EFF), "produced_per_month": N,
                        "month_sd": S, "reps": N_REP, "test_level": 0.05},
           "example_24months": ex_last,
           "base_by_months": base_df.to_dict("records"), "no_effect_by_months": null_df.to_dict("records"),
           "months_needed_base": {"monthly80": needed(base, "monthly_sig"), "pooled80": needed(base, "pooled_sig")},
           "grid_months_needed": grid.to_dict("records"),
           "grid_ranges": {"no_effect_pooled_sig_k6_min": float(grid.no_effect_pooled_sig_k6.min()),
                           "no_effect_pooled_sig_k6_max": float(grid.no_effect_pooled_sig_k6.max()),
                           "no_effect_monthly_sig_k6_min": float(grid.no_effect_monthly_sig_k6.min()),
                           "no_effect_monthly_sig_k6_max": float(grid.no_effect_monthly_sig_k6.max())},
           "by_effect_size": eff.to_dict("records"), "drift_no_effect": drift.to_dict("records")}
    json.dump(out, open(RES / "a919_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の24か月
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.bar(ex.month, ex.rate * 100, color=[LIGHT] * 12 + [BLUE] * 12)
    ax.hlines(P0 * 100, 0.5, 12.5, color=ORANGE, lw=1.6); ax.hlines(P0 * (1 - EFF) * 100, 12.5, 24.5, color=ORANGE, lw=1.6)
    ax.text(0.7, P0 * 100 + 0.03, "本当の不良率 1.0%", color=ORANGE, fontsize=9,
            bbox=dict(facecolor="white", edgecolor="none", alpha=.85, pad=1))
    ax.text(18.6, P0 * (1 - EFF) * 100 - 0.12, "本当の不良率 0.7%", color=ORANGE, fontsize=9,
            bbox=dict(facecolor="white", edgecolor="none", alpha=.85, pad=1))
    ax.axvline(12.5, color=GRAY, ls="--", lw=1); ax.text(12.7, ax.get_ylim()[1] * 0.93, "改善", color=GRAY, fontsize=9)
    ax.set_xlabel("月（1〜12が改善の前、13〜24が後）"); ax.set_ylabel("その月の不良率（%）")
    ax.set_xticks([1, 6, 12, 13, 18, 24])
    ax.set_title("月産2,000個・月の振れ0.2と置いた例：月ごとの率は改善の幅と同じくらい上下する", fontsize=11.5)
    save(fig, "a919_monthly_example.png", SRC)

    # 図2：k か月ずつ比べたとき（効果30%／効果なし）
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.0))
    ax = axs[0]
    ax.plot(base_df.months, base_df.looked_lower * 100, "o-", color=GRAY, label="後のほうが低く見えた")
    ax.plot(base_df.months, base_df.pooled_sig * 100, "s-", color=ORANGE, label="合算の検定で「下がった」")
    ax.plot(base_df.months[1:], base_df.monthly_sig[1:] * 100, "^-", color=BLUE, label="月ごとの率の検定で「下がった」")
    ax.axhline(80, color=GRAY, lw=.8, ls=":")
    ax.set_title("本当に30%下がったとき", fontsize=11); ax.set_ylim(0, 105)
    ax.set_xlabel("前後それぞれ何か月見たか"); ax.set_ylabel("割合（%、4,000回）"); ax.set_xticks(KS)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax = axs[1]
    ax.plot(null_df.months, null_df.looked_lower * 100, "o-", color=GRAY, label="後のほうが低く見えた")
    ax.plot(null_df.months, null_df.pooled_sig * 100, "s-", color=ORANGE, label="合算の検定で「下がった」")
    ax.plot(null_df.months[1:], null_df.monthly_sig[1:] * 100, "^-", color=BLUE, label="月ごとの率の検定で「下がった」")
    ax.axhline(2.5, color=GRAY, lw=.8, ls=":"); ax.text(24.2, 3.5, "2.5%", color=GRAY, fontsize=8, ha="right")
    ax.set_title("本当は変わっていないとき", fontsize=11); ax.set_ylim(0, 60)
    ax.set_xlabel("前後それぞれ何か月見たか"); ax.set_xticks(KS)
    fig.suptitle("合算の検定は早く「下がった」と言うが、変わっていないときにも言いやすい（月の振れ0.2）", fontsize=11.5)
    fig.tight_layout()
    save(fig, "a919_power_by_months.png", SRC)

    # 図3：月の振れと月産で、何か月要るか（月ごとの率の検定で80%）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = 0.26
    for i, (n, col) in enumerate([(500, LIGHT), (2000, BLUE), (10000, INK)]):
        s_ = grid[grid.produced_per_month == n]
        vals = [v if pd.notna(v) else 26 for v in s_.months_needed_monthly80]
        xs = np.arange(3) + (i - 1) * w
        ax.bar(xs, vals, w, color=col, label=f"月産{n:,}個")
        for x, v, raw in zip(xs, vals, s_.months_needed_monthly80):
            ax.text(x, v + 0.2, f"{int(raw)}" if pd.notna(raw) else "24超", ha="center", fontsize=8.5)
    ax.set_xticks(range(3)); ax.set_xticklabels(["月の振れ0（なし）", "月の振れ0.2（基本）", "月の振れ0.4"])
    ax.set_ylabel("前後それぞれの月数（8割に届いた最初）"); ax.set_ylim(0, 34)
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=3)
    ax.set_title("月の振れが大きいほど、月産を増やしても要る月数が減りにくい\n（本当に30%下がったとき、月ごとの率の検定で80%の確率に届いた月数。\n1・2・3・4・6・9・12・18・24か月を調べた中で最初に届いたもの）", fontsize=11)
    save(fig, "a919_months_needed.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
