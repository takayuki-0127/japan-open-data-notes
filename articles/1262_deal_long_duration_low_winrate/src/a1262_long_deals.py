"""1262 長引いた商談ほど受注率が低いのは、長引いたせいか、もともと決まりにくい商談だからか？（架空のデータ）

架空の会社の法人向けの商談。商談ごとに「決まりやすさ」（見えない値）を置き、
1日ごとに取れる・取れないが決まる確率を作成者が置く。
  S0 違いだけ：決まりにくい商談ほど、決まるのが遅く、取れにくい。長引くこと自体は何も変えない
  S1 長引いたせいだけ：どの商談も同じ。始まってからの日数がたつほど、1日に取れる確率が下がる
  S2 両方
の3つで、決まるまでの日数ごとの受注率、最初の見込みの点で分けたときの差、
商談に関係なくでたらめに入る「先方の決裁待ち」（60日）があった商談となかった商談の差を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1262
SRC = "架空の会社の商談（作成者が乱数で作成、seed 1262）"
H0 = 1 / 60          # 1日に決まる確率（決まりやすさ0の商談、日数がたつ前）
LIMIT = 365          # 動き出してから365日で決まらなければ取れなかったとする
PAUSE, PAUSE_SHARE = 60, 0.2
N, REPS, GRID_REPS = 2000, 200, 40
SCORE_SD = 0.7       # 最初の見込みの点の誤差（決まりやすさ＋誤差）
BANDS = [(0, 30), (31, 60), (61, 90), (91, 180), (181, 425)]
BAND_LABELS = ["30日以内", "31〜60日", "61〜90日", "91〜180日", "181日以上"]
# 名前：(g 決まりやすさで速さが変わる強さ, a 取れる割合の切片, b 決まりやすさで取れる割合が変わる強さ, k 日数がたつと取れる確率が下がる強さ)
SCEN = {"S0": (0.8, -1.35, 1.2, 0.0), "S1": (0.0, -0.5, 0.0, 0.9), "S2": (0.4, -0.85, 0.6, 0.45)}
SCEN_NAME = {"S0": "違いだけ", "S1": "長引いたせいだけ", "S2": "両方"}


def simulate(rng, n, g, a, b, k, pause_share=PAUSE_SHARE, pause_mode="random", score_sd=SCORE_SD):
    z = rng.standard_normal(n)
    if pause_mode == "random":
        paused = rng.random(n) < pause_share
    elif pause_mode == "all":
        paused = np.ones(n, bool)
    elif pause_mode == "none":
        paused = np.zeros(n, bool)
    else:  # 決まりにくい商談ほど決裁待ちになりやすい
        paused = rng.random(n) < 1 / (1 + np.exp(-(-1.55 - 0.8 * z)))
    start = np.where(paused, PAUSE, 0)
    h = H0 * np.exp(g * z)
    pi = 1 / (1 + np.exp(-(a + b * z)))
    hw0, hl = h * pi, h * (1 - pi)
    dec = np.full(n, -1)
    won = np.zeros(n, bool)
    open_ = np.ones(n, bool)
    for t in range(PAUSE + LIMIT):
        act = open_ & (t >= start) & (t < start + LIMIT)
        if not act.any():
            continue
        hw = hw0 * np.exp(-k * t / 90)
        u = rng.random(n)
        w = act & (u < hw)
        l = act & ~w & (u < hw + hl)
        won |= w
        dec[w | l] = t
        open_ &= ~(w | l)
    dec = np.where(open_, start + LIMIT, dec)
    score = z + rng.normal(0, score_sd, n) if score_sd > 0 else z.copy()
    return pd.DataFrame({"z": z, "score": score, "paused": paused, "days": dec, "won": won})


def band_rates(df):
    out = []
    for (lo, hi), lab in zip(BANDS, BAND_LABELS):
        m = (df.days >= lo) & (df.days <= hi)
        out.append((lab, df.won[m].mean() * 100 if m.any() else np.nan, m.mean() * 100,
                    df.paused[m].mean() * 100 if m.any() else np.nan))
    return out


def gaps(df):
    """30日以内に決まった商談と181日以上かかった商談の受注率の差（そのまま／最初の見込みの点の5段で分けて重み付け）"""
    short, long_ = df.days <= 30, df.days >= 181
    naive = (df.won[short].mean() - df.won[long_].mean()) * 100
    q = pd.qcut(df.score, 5, labels=False)
    diffs, wts = [], []
    for s in range(5):
        m = q == s
        if (m & short).sum() >= 5 and (m & long_).sum() >= 5:
            diffs.append(df.won[m & short].mean() - df.won[m & long_].mean())
            wts.append(m.sum())
    strat = float(np.average(diffs, weights=wts) * 100)
    pause_diff = (df.won[df.paused].mean() - df.won[~df.paused].mean()) * 100
    return naive, strat, pause_diff


def true_pause_effect(rng, params, n=200000):
    a = simulate(rng, n, *params, pause_mode="all")
    b = simulate(rng, n, *params, pause_mode="none")
    return (a.won.mean() - b.won.mean()) * 100


def run(rng, params, reps, **kw):
    rows, bands = [], []
    for r in range(reps):
        df = simulate(rng, N, *params, **kw)
        nv, st, pdiff = gaps(df)
        rows.append(dict(rep=r, win=df.won.mean() * 100, naive_gap=nv, strat_gap=st, pause_diff=pdiff,
                         median_days=float(np.median(df.days))))
        for lab, wr, sh, ps in band_rates(df):
            bands.append(dict(rep=r, band=lab, win=wr, share=sh, paused=ps))
    return pd.DataFrame(rows), pd.DataFrame(bands)


def summ(x):
    return dict(mean=round(float(x.mean()), 2), p10=round(float(x.quantile(0.1)), 2), p90=round(float(x.quantile(0.9)), 2))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    main_rows, band_rows, out_s = [], [], {}
    for key, params in SCEN.items():
        reps, bands = run(rng, params, REPS)
        te = true_pause_effect(rng, params)
        reps.assign(scenario=key).round(3).to_csv(RES / f"reps_{key}.csv", index=False)
        bm = bands.groupby("band", sort=False)[["win", "share", "paused"]].mean()
        for lab in BAND_LABELS:
            band_rows.append(dict(scenario=key, scenario_name=SCEN_NAME[key], band=lab,
                                  win_rate=round(float(bm.loc[lab, "win"]), 2), share_of_deals=round(float(bm.loc[lab, "share"]), 2),
                                  paused_share=round(float(bm.loc[lab, "paused"]), 2)))
        out_s[key] = {"name": SCEN_NAME[key], "win_rate": summ(reps.win), "median_days": summ(reps.median_days),
                      "naive_gap": summ(reps.naive_gap), "strat_gap": summ(reps.strat_gap),
                      "pause_diff": summ(reps.pause_diff), "true_pause_effect": round(te, 2),
                      "pause_diff_negative_pct": round(float((reps.pause_diff < 0).mean() * 100), 1)}
        main_rows.append(dict(scenario=key, scenario_name=SCEN_NAME[key], win_rate=out_s[key]["win_rate"]["mean"],
                              naive_gap=out_s[key]["naive_gap"]["mean"], strat_gap=out_s[key]["strat_gap"]["mean"],
                              pause_diff=out_s[key]["pause_diff"]["mean"], pause_diff_p10=out_s[key]["pause_diff"]["p10"],
                              pause_diff_p90=out_s[key]["pause_diff"]["p90"], true_pause_effect=round(te, 2)))
    bands_df = pd.DataFrame(band_rows)
    bands_df.to_csv(RES / "win_by_days.csv", index=False)
    main_df = pd.DataFrame(main_rows)
    main_df.to_csv(RES / "scenario_summary.csv", index=False)

    # 最初の見込みの点の誤差を変える（S0）
    noise_rows = []
    for sd in [0.0, 0.35, 0.7, 1.4]:
        reps, _ = run(rng, SCEN["S0"], GRID_REPS, score_sd=sd)
        noise_rows.append(dict(score_sd=sd, naive_gap=round(reps.naive_gap.mean(), 2), strat_gap=round(reps.strat_gap.mean(), 2)))
    noise_df = pd.DataFrame(noise_rows)
    noise_df.to_csv(RES / "score_noise_S0.csv", index=False)

    # 決まりにくい商談ほど決裁待ちになりやすいとき（S0、本当は待ちの効き目なし）
    reps_nr, _ = run(rng, SCEN["S0"], REPS, pause_mode="tilted")
    te_nr = true_pause_effect(rng, SCEN["S0"])
    nonrandom = {"pause_diff": summ(reps_nr.pause_diff), "true_pause_effect": round(te_nr, 2),
                 "paused_share": None}
    chk = simulate(np.random.default_rng(SEED + 7), 200000, *SCEN["S0"], pause_mode="tilted")
    nonrandom["paused_share"] = round(float(chk.paused.mean() * 100), 2)
    nonrandom["paused_mean_z"] = round(float(chk.z[chk.paused].mean()), 3)

    # 確かめ：違いの強さ × 長引いたせいの強さ（9通り）
    grid = []
    for scale in [0.5, 1.0, 1.5]:
        for k in [0.0, 0.45, 0.9]:
            g, a, b, _ = SCEN["S0"]
            params = (g * scale, a, b * scale, k)
            reps, _ = run(rng, params, GRID_REPS)
            te = true_pause_effect(rng, params, n=100000)
            grid.append(dict(difference_scale=scale, decay_k=k, win_rate=round(reps.win.mean(), 2),
                             naive_gap=round(reps.naive_gap.mean(), 2), strat_gap=round(reps.strat_gap.mean(), 2),
                             pause_diff=round(reps.pause_diff.mean(), 2),
                             pause_diff_p10=round(reps.pause_diff.quantile(0.1), 2),
                             pause_diff_p90=round(reps.pause_diff.quantile(0.9), 2), true_pause_effect=round(te, 2)))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # データ：S0 と S1 の1回分
    for key in ["S0", "S1"]:
        df = simulate(np.random.default_rng(SEED + 1), N, *SCEN[key])
        df.assign(deal_id=np.arange(1, N + 1), paused=df.paused.astype(int), won=df.won.astype(int),
                  z=df.z.round(3), score=df.score.round(3))[["deal_id", "z", "score", "paused", "days", "won"]].to_csv(
            DATA / f"deals_{key}_one_rep.csv", index=False)

    out = {
        "settings": {"deals_per_rep": N, "reps": REPS, "grid_reps": GRID_REPS, "base_daily_decide": round(H0, 5),
                     "limit_days": LIMIT, "pause_days": PAUSE, "pause_share": PAUSE_SHARE, "score_sd": SCORE_SD,
                     "scenarios": {k: dict(zip(["g_speed", "a_win", "b_win", "k_decay"], v)) for k, v in SCEN.items()},
                     "seed": SEED},
        "scenarios": out_s,
        "win_by_days": band_rows,
        "score_noise_S0": noise_rows,
        "nonrandom_pause_S0": nonrandom,
        "grid_range": {c: [float(grid[c].min()), float(grid[c].max())] for c in
                       ["win_rate", "naive_gap", "strat_gap", "pause_diff", "true_pause_effect"]},
        "grid_max_abs_pause_diff_minus_true": round(float((grid.pause_diff - grid.true_pause_effect).abs().max()), 2),
    }

    # 図1：決まるまでの日数ごとの受注率（3つの置き方）
    fig, ax = plt.subplots(figsize=(7.4, 4))
    x = np.arange(len(BAND_LABELS)); w = 0.26
    for i, (key, col) in enumerate(zip(["S0", "S1", "S2"], [BLUE, ORANGE, GREEN])):
        d = bands_df[bands_df.scenario == key]
        bars = ax.bar(x + (i - 1) * w, d.win_rate, w, color=col, label=f"{key} {SCEN_NAME[key]}")
        for bb in bars:
            ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 0.5, f"{bb.get_height():.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(BAND_LABELS)
    ax.set_xlabel("始まってから決まるまでの日数"); ax.set_ylabel("受注率（%）"); ax.set_ylim(0, 45)
    ax.set_title("どちらの仕組みでも、長引いた商談ほど受注率が低く見える")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1262_win_by_days.png", SRC + "。200回の平均。数字は小数1けた（results は2けた）", y=-0.03)

    # 図2：3つの見方の比べ
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.8), sharey=False)
    items = [("naive_gap", "そのまま\n（30日以内−181日以上）"), ("strat_gap", "最初の見込みの点の5段の中で\n（30日以内−181日以上）"),
             ("pause_diff", "決裁待ちあり−なし\n（本当の差は灰色の線）")]
    for ax, (col, ttl) in zip(axes, items):
        vals = main_df[col].values
        bars = ax.bar(range(3), vals, color=[BLUE, ORANGE, GREEN], width=0.6)
        ax.axhline(0, color=INK, lw=0.8)
        for j, bb in enumerate(bars):
            v = vals[j]
            ax.text(bb.get_x() + bb.get_width() / 2, v + (0.6 if v >= 0 else -0.6), f"{v:.2f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8.5)
        if col == "pause_diff":
            for j, te in enumerate(main_df.true_pause_effect.values):
                ax.hlines(te, j - 0.35, j + 0.35, color=GRAY, lw=2.5)
        ax.set_xticks(range(3)); ax.set_xticklabels([f"{k}\n{SCEN_NAME[k]}" for k in main_df.scenario], fontsize=8.5)
        ax.set_title(ttl, fontsize=10.5)
    lo = min(main_df[[c for c, _ in items]].min().min(), main_df.true_pause_effect.min()) - 4
    hi = main_df[[c for c, _ in items]].max().max() + 5
    for ax in axes:
        ax.set_ylim(lo, hi)
    axes[0].set_ylabel("受注率の差（ポイント）")
    fig.suptitle("本当の効き目に合ったのは、でたらめに入る決裁待ちの比べだけ", fontsize=12.5, y=1.03)
    save(fig, "a1262_three_views.png", SRC + "。200回の平均。最初の見込みの点は決まりやすさ＋誤差（標準偏差0.7）", y=-0.03)

    # 図3：9通りの確かめ（決裁待ちの差と本当の効き目）
    fig, ax = plt.subplots(figsize=(7.2, 4))
    lab = [f"違い×{r.difference_scale:g}\n下がり{r.decay_k:g}" for r in grid.itertuples()]
    xx = np.arange(len(grid))
    ax.bar(xx - 0.2, grid.naive_gap, 0.4, color=BLUE, label="そのままの差（30日以内−181日以上）")
    ax.bar(xx + 0.2, -grid.pause_diff, 0.4, color=GREEN, label="決裁待ちなし−あり")
    ax.scatter(xx + 0.2, -grid.true_pause_effect, color=INK, marker="_", s=200, zorder=3, label="決裁待ちで本当に下がる分")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xx); ax.set_xticklabels(lab, fontsize=7.5)
    ax.set_ylabel("受注率の差（ポイント）")
    ax.set_title("そのままの差はいつも大きく、決裁待ちの差は本当の効き目に沿った")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_ylim(min(0, (-grid.pause_diff).min()) - 2, grid.naive_gap.max() * 1.35)
    save(fig, "a1262_grid.png", SRC + "。違い×は決まりやすさの違いの強さ、下がりは日数がたつと取れる確率が下がる強さ。各40回", y=-0.03)

    json.dump(out, open(RES / "a1262_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(main_df.to_string()); print(grid.to_string()); print(noise_df.to_string())
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
