"""969 空欄を除いて平均すると、何がずれるのか？（架空のデータ）

架空の店の会員アンケート（会員5,000人、全員が提出）。「この1か月の来店回数」の欄に空欄がある。
会員の種類（アプリ会員60%・カード会員40%）は会員の台帳で全員分かる。
本当の来店回数は作成者が全員分置く（アプリ会員 平均4.5回、カード会員 平均2.0回、負の二項分布）。
空欄の出方を4つ置き、どれも空欄は全体の30%にそろえる：
  ① でたらめに空欄
  ② 会員の種類で空欄（カード会員ほど空欄。種類ごとの空欄の割合は③と同じにそろえる）
  ③ 来店の少ない人ほど空欄
  ④ 来店の多い人ほど空欄
数え方は2つ：(a) 空欄を除いて平均、(b) 種類ごとに空欄を除いて平均し、台帳の種類の割合で合わせる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 969
SRC = "架空の店の会員アンケート（作成者が乱数で作成、seed 969）"
N = 5000
REPS = 300
P_CARD = 0.4
MU = {"app": 4.5, "card": 2.0}
K_DISP = 2.0          # 負の二項分布の形（小さいほど散らばる）
RATE = 0.30           # 空欄の割合
STRENGTH = 1.2        # ③④の結びつきの強さ（log(1+回数) あたりのロジットの傾き）
MECH = ["①でたらめ", "②会員の種類で", "③少ない人ほど", "④多い人ほど"]
TRUE_MEAN = (1 - P_CARD) * MU["app"] + P_CARD * MU["card"]


def make_members(rng, n=N, mus=None):
    mus = mus or MU
    card = rng.random(n) < P_CARD
    mu = np.where(card, mus["card"], mus["app"])
    lam = rng.gamma(K_DISP, mu / K_DISP)
    y = rng.poisson(lam)
    return card, y


def logistic(x):
    return 1 / (1 + np.exp(-x))


def calib_a(sign, b, rate, mus=None, rng_seed=SEED * 7):
    """③④：空欄の確率 logistic(a + sign*b*log(1+y)) の平均が rate になる a を大きな標本で決める"""
    rng = np.random.default_rng(rng_seed)
    card, y = make_members(rng, 400000, mus)
    z = sign * b * np.log1p(y)
    lo, hi = -15.0, 15.0
    for _ in range(60):
        a = (lo + hi) / 2
        if logistic(a + z).mean() > rate:
            hi = a
        else:
            lo = a
    a = (lo + hi) / 2
    p = logistic(a + z)
    return a, float(p[card].mean()), float(p[~card].mean())


def blank_probs(mech, card, y, prm):
    if mech == 0:
        return np.full(len(y), prm["rate"])
    if mech == 1:
        return np.where(card, prm["p_card"], prm["p_app"])
    if mech == 2:
        return logistic(prm["a_low"] - prm["b"] * np.log1p(y))
    return logistic(prm["a_high"] + prm["b"] * np.log1p(y))


def params(rate=RATE, b=STRENGTH, mus=None):
    a_low, pc, pa = calib_a(-1, b, rate, mus)
    a_high, _, _ = calib_a(+1, b, rate, mus)
    return {"rate": rate, "b": b, "a_low": a_low, "a_high": a_high, "p_card": pc, "p_app": pa}


def estimate(card, y, blank):
    obs = ~blank
    e_drop = y[obs].mean()
    s_drop = (y[obs] >= 4).mean()
    w_card = card.mean()                                   # 台帳で分かる種類の割合
    m_c, m_a = y[obs & card].mean(), y[obs & ~card].mean()
    s_c, s_a = (y[obs & card] >= 4).mean(), (y[obs & ~card] >= 4).mean()
    return {"mean_drop": e_drop, "mean_weighted": w_card * m_c + (1 - w_card) * m_a,
            "share4_drop": s_drop, "share4_weighted": w_card * s_c + (1 - w_card) * s_a,
            "mean_true": y.mean(), "share4_true": (y >= 4).mean(),
            "blank_rate": blank.mean(), "blank_rate_card": blank[card].mean(), "blank_rate_app": blank[~card].mean(),
            "card_share_blank": card[blank].mean(), "card_share_answered": card[obs].mean()}


def run(seed0, reps, mech, prm, n=N, mus=None):
    rows = []
    for r in range(reps):
        rng = np.random.default_rng(seed0 + r)
        card, y = make_members(rng, n, mus)
        blank = rng.random(n) < blank_probs(mech, card, y, prm)
        rows.append(estimate(card, y, blank))
    d = pd.DataFrame(rows)
    for k in ["mean", "share4"]:
        for m in ["drop", "weighted"]:
            d[f"{k}_{m}_bias_pct"] = (d[f"{k}_{m}"] / d[f"{k}_true"] - 1) * 100
            d[f"{k}_{m}_bias_pt"] = (d[f"{k}_{m}"] - d[f"{k}_true"]) * 100
    return d


def pct(v):
    return "±0.0%" if abs(v) < 0.05 else f"{v:+.1f}%"


def r4(x):
    return round(float(x), 4)


def main():
    t0 = time.time()
    prm = params()
    res = {"setting": {"members": N, "reps": REPS, "card_share": P_CARD, "mean_visits_app": MU["app"],
                       "mean_visits_card": MU["card"], "nb_shape": K_DISP, "blank_rate": RATE, "strength_b": STRENGTH,
                       "true_mean_formula": TRUE_MEAN,
                       "calibrated": {k: r4(v) for k, v in prm.items()}}}

    # 1) 例の会員5,000人（data）
    rng = np.random.default_rng(SEED)
    card, y = make_members(rng)
    ex = pd.DataFrame({"member_id": np.arange(1, N + 1), "kind": np.where(card, "card", "app"), "true_visits": y})
    for i, m in enumerate(["blank_random", "blank_by_kind", "blank_low_visits", "blank_high_visits"]):
        ex[m] = (rng.random(N) < blank_probs(i, card, y, prm)).astype(int)
    ex.to_csv(DATA / "members_example.csv", index=False)

    # 2) 4つの空欄の出方（300回）
    main_rows, sims = [], {}
    for i, name in enumerate(MECH):
        d = run(SEED * 1000 + i * 10000, REPS, i, prm)
        sims[name] = d
        row = {"mechanism": name}
        for c in ["mean_true", "mean_drop", "mean_weighted", "share4_true", "share4_drop", "share4_weighted",
                  "mean_drop_bias_pct", "mean_weighted_bias_pct", "share4_drop_bias_pt", "share4_weighted_bias_pt",
                  "blank_rate", "blank_rate_card", "blank_rate_app", "card_share_blank", "card_share_answered"]:
            row[c] = r4(d[c].mean())
        row["mean_drop_bias_pct_p10"] = r4(d.mean_drop_bias_pct.quantile(.1))
        row["mean_drop_bias_pct_p90"] = r4(d.mean_drop_bias_pct.quantile(.9))
        row["mean_weighted_bias_pct_p10"] = r4(d.mean_weighted_bias_pct.quantile(.1))
        row["mean_weighted_bias_pct_p90"] = r4(d.mean_weighted_bias_pct.quantile(.9))
        main_rows.append(row)
    main_df = pd.DataFrame(main_rows)
    main_df.to_csv(RES / "mechanisms.csv", index=False)
    res["mechanisms"] = main_rows

    # 式どおりの確かめ：②で空欄を除いた平均（種類の割合が空欄でずれる分だけ）
    wc, wa = P_CARD * (1 - prm["p_card"]), (1 - P_CARD) * (1 - prm["p_app"])
    f_mean = (wc * MU["card"] + wa * MU["app"]) / (wc + wa)
    res["formula_mech2_mean_drop"] = r4(f_mean)
    res["formula_mech2_mean_drop_bias_pct"] = r4((f_mean / TRUE_MEAN - 1) * 100)

    # 3) 会員の数を変えても（③、各300回）
    size_rows = []
    for j, n in enumerate([500, 5000, 50000]):
        d = run(SEED * 3000 + j * 10000, REPS, 2, prm, n=n)
        size_rows.append({"members": n, "mean_drop_bias_pct": r4(d.mean_drop_bias_pct.mean()),
                          "mean_drop_bias_pct_sd": r4(d.mean_drop_bias_pct.std()),
                          "mean_weighted_bias_pct": r4(d.mean_weighted_bias_pct.mean()),
                          "mean_weighted_bias_pct_sd": r4(d.mean_weighted_bias_pct.std()),
                          "share_runs_weighted_within_1pct": r4((d.mean_weighted_bias_pct.abs() < 1).mean())})
        dm = run(SEED * 3500 + j * 10000, REPS, 0, prm, n=n)
        size_rows[-1]["mech1_mean_drop_bias_pct_sd"] = r4(dm.mean_drop_bias_pct.std())
        size_rows[-1]["mech1_share_runs_within_1pct"] = r4((dm.mean_drop_bias_pct.abs() < 1).mean())
    pd.DataFrame(size_rows).to_csv(RES / "sample_size.csv", index=False)
    res["sample_size"] = size_rows

    # 4) 確かめ：空欄の割合 × 結びつきの強さ（③④）、種類の差（②）、各100回
    grid, k = [], 0
    for rate in [0.1, 0.3, 0.5]:
        for b in [0.6, 1.2, 2.4]:
            p2 = params(rate, b)
            for i in [1, 2, 3]:
                d = run(SEED * 5000 + k * 1000, 100, i, p2)
                k += 1
                grid.append({"mechanism": MECH[i], "blank_rate": rate, "strength_b": b,
                             "blank_rate_card": r4(d.blank_rate_card.mean()), "blank_rate_app": r4(d.blank_rate_app.mean()),
                             "mean_drop_bias_pct": r4(d.mean_drop_bias_pct.mean()),
                             "mean_weighted_bias_pct": r4(d.mean_weighted_bias_pct.mean()),
                             "share4_drop_bias_pt": r4(d.share4_drop_bias_pt.mean()),
                             "share4_weighted_bias_pt": r4(d.share4_weighted_bias_pt.mean())})
    # 種類どうしの差（カード会員の平均回数）を変える（空欄30%・強さ1.2）
    for mc in [1.0, 3.5, 4.5]:
        mus = {"app": MU["app"], "card": mc}
        p2 = params(RATE, STRENGTH, mus)
        for i in [1, 2, 3]:
            d = run(SEED * 6000 + k * 1000, 100, i, p2, mus=mus)
            k += 1
            grid.append({"mechanism": MECH[i], "blank_rate": RATE, "strength_b": STRENGTH, "mean_visits_card": mc,
                         "blank_rate_card": r4(d.blank_rate_card.mean()), "blank_rate_app": r4(d.blank_rate_app.mean()),
                         "mean_drop_bias_pct": r4(d.mean_drop_bias_pct.mean()),
                         "mean_weighted_bias_pct": r4(d.mean_weighted_bias_pct.mean()),
                         "share4_drop_bias_pt": r4(d.share4_drop_bias_pt.mean()),
                         "share4_weighted_bias_pt": r4(d.share4_weighted_bias_pt.mean())})
    grid = pd.DataFrame(grid)
    grid["mean_visits_card"] = grid["mean_visits_card"].fillna(MU["card"])
    grid = grid[["mechanism", "blank_rate", "strength_b", "mean_visits_card"] + [c for c in grid.columns if c not in
                ("mechanism", "blank_rate", "strength_b", "mean_visits_card")]]
    grid.to_csv(RES / "robustness.csv", index=False)
    gv = grid[(grid.mean_visits_card != MU["card"]) & (grid.mechanism == MECH[2])]
    g2, g3, g4 = (grid[(grid.mechanism == MECH[i]) & (grid.mean_visits_card == MU["card"])] for i in [1, 2, 3])
    res["robustness"] = {
        "combos": int(len(grid)),
        "mech2_weighted_bias_pct_abs_max": r4(g2.mean_weighted_bias_pct.abs().max()),
        "mech2_drop_bias_pct_range": [r4(g2.mean_drop_bias_pct.min()), r4(g2.mean_drop_bias_pct.max())],
        "mech3_drop_bias_pct_range": [r4(g3.mean_drop_bias_pct.min()), r4(g3.mean_drop_bias_pct.max())],
        "mech3_weighted_bias_pct_range": [r4(g3.mean_weighted_bias_pct.min()), r4(g3.mean_weighted_bias_pct.max())],
        "mech4_drop_bias_pct_range": [r4(g4.mean_drop_bias_pct.min()), r4(g4.mean_drop_bias_pct.max())],
        "mech4_weighted_bias_pct_range": [r4(g4.mean_weighted_bias_pct.min()), r4(g4.mean_weighted_bias_pct.max())],
        "mech3_by_card_mean": [{"mean_visits_card": float(r.mean_visits_card), "drop": float(r.mean_drop_bias_pct),
                                "weighted": float(r.mean_weighted_bias_pct),
                                "left_share": r4(r.mean_weighted_bias_pct / r.mean_drop_bias_pct)} for r in gv.itertuples()],
        "mech2_weighted_bias_pct_abs_max_all": r4(grid[grid.mechanism == MECH[1]].mean_weighted_bias_pct.abs().max()),
        "mech3_weighted_left_share_of_drop_range_all12": [
            r4((grid[grid.mechanism == MECH[2]].mean_weighted_bias_pct / grid[grid.mechanism == MECH[2]].mean_drop_bias_pct).min()),
            r4((grid[grid.mechanism == MECH[2]].mean_weighted_bias_pct / grid[grid.mechanism == MECH[2]].mean_drop_bias_pct).max())],
        "mech3_weighted_left_share_of_drop_range": [r4((g3.mean_weighted_bias_pct / g3.mean_drop_bias_pct).min()),
                                                    r4((g3.mean_weighted_bias_pct / g3.mean_drop_bias_pct).max())],
    }
    m = {r["mechanism"]: r for r in main_rows}
    res["mech3_weighted_left_share_of_drop"] = r4(m[MECH[2]]["mean_weighted_bias_pct"] / m[MECH[2]]["mean_drop_bias_pct"])

    # 図1：4つの出方で、空欄を除いた平均のずれ
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    x = np.arange(4)
    v1 = [m[n]["mean_drop_bias_pct"] for n in MECH]
    v2 = [m[n]["mean_weighted_bias_pct"] for n in MECH]
    b1 = ax.bar(x - 0.2, v1, 0.38, color=ORANGE, label="(a) 空欄を除いて平均")
    b2 = ax.bar(x + 0.2, v2, 0.38, color=BLUE, label="(b) 種類ごとに除いて、台帳の割合で合わせる")
    for bars in [b1, b2]:
        for bb in bars:
            v = bb.get_height()
            ax.text(bb.get_x() + bb.get_width() / 2, v + (0.6 if v >= 0 else -0.6), pct(v),
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([n + "\n空欄" for n in MECH])
    ax.set_ylabel("全員の本当の平均とのずれ（%）")
    lim = max(abs(min(v1 + v2)), abs(max(v1 + v2))) * 1.35
    ax.set_ylim(-lim, lim)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    ax.set_title("空欄はどれも30%。ずれるかどうかは、だれが空欄にするかで決まる", fontsize=12)
    save(fig, "a969_bias_by_mechanism.png", SRC + "。会員5,000人を300回作り直した平均")

    # 図2：表から見える欠け方（種類ごとの空欄の割合）は②と③で同じ。直したあとのずれは違う
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
    ax = axes[0]
    for j, (n, c) in enumerate([(MECH[1], GREEN), (MECH[2], ORANGE)]):
        vals = [m[n]["blank_rate_app"] * 100, m[n]["blank_rate_card"] * 100]
        bb = ax.bar(np.arange(2) + (j - 0.5) * 0.38, vals, 0.36, color=c, label=n + "空欄")
        for b_, v in zip(bb, vals):
            ax.text(b_.get_x() + b_.get_width() / 2, v + 0.8, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["アプリ会員", "カード会員"])
    ax.set_ylabel("空欄の割合（%）"); ax.set_ylim(0, 60)
    ax.set_title("表から見える：種類ごとの空欄の割合", fontsize=11)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    ax = axes[1]
    vals = [m[MECH[1]]["mean_weighted_bias_pct"], m[MECH[2]]["mean_weighted_bias_pct"]]
    bb = ax.bar([0, 1], vals, 0.5, color=[GREEN, ORANGE])
    for b_, v in zip(bb, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, v + (0.4 if v >= 0 else -0.4), pct(v), ha="center",
                va="bottom" if v >= 0 else "top", fontsize=10)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks([0, 1]); ax.set_xticklabels([MECH[1] + "空欄", MECH[2] + "空欄"])
    ax.set_ylabel("(b) で直したあとのずれ（%）"); ax.set_ylim(-2, max(vals) * 1.4 + 1)
    ax.set_title("見えない：種類で直したあとのずれ", fontsize=11)
    fig.suptitle("表で見える欠け方が同じでも、種類で直して消えるずれと残るずれがある", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a969_looks_same.png", SRC + "。会員5,000人を300回作り直した平均")

    # 図3：確かめ（③④、空欄の割合×強さ）
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.5), sharey=True)
    for ax, g, name in [(axes[0], g3, MECH[2]), (axes[1], g4, MECH[3])]:
        for b, c, mk in [(0.6, LIGHT, "o"), (1.2, BLUE, "s"), (2.4, INK, "^")]:
            d = g[g.strength_b == b].sort_values("blank_rate")
            ax.plot(d.blank_rate * 100, d.mean_drop_bias_pct, marker=mk, color=c, label=f"強さ {b}（除いて平均）")
            ax.plot(d.blank_rate * 100, d.mean_weighted_bias_pct, marker=mk, color=c, ls="--", alpha=0.8)
        ax.axhline(0, color=GRAY, lw=0.8)
        ax.set_xticks([10, 30, 50]); ax.set_xlabel("空欄の割合（%）")
        ax.set_title(name + "空欄", fontsize=11)
    axes[0].set_ylabel("全員の本当の平均とのずれ（%）")
    axes[0].legend(fontsize=8.5, frameon=False, loc="lower left")
    fig.suptitle("空欄が多いほど、結びつきが強いほどずれる（実線：除いて平均、点線：種類で直したあと）", fontsize=12)
    fig.tight_layout()
    save(fig, "a969_robustness.png", SRC + "。各100回の平均。強さは log(1＋回数) あたりのロジットの傾き")

    res["run_sec"] = round(time.time() - t0, 1)
    with open(RES / "a969_main.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if k != "run_sec"}, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
