"""1175 前回の倍率を見て申し込む人が増えたり減ったりすると、倍率はどこに落ち着くのか？（架空のデータ）

作成者が置いた架空の料理講座の抽選（毎回の枠100、同じ顔ぶれの申し込みうる人2,000人、1人1口、80回くり返す）。
- 倍率を見ない人（40%）：毎回10%の確率で申し込む（乱数）
- 倍率を見る人（60%）：前回の倍率から読む当たる見込み（枠÷申し込み、100%まで）が、その人の「申し込む見込みの下限」以上なら申し込む。
  下限は人ごとに決まっていて、一様に散らばる。散らばりの幅を3通り置く：広い（0〜50%）・中（10〜30%）・狭い（18〜22%）
- 1回目は「前回の倍率2倍」を見たとする。倍率＝申し込んだ人÷枠
- 見る手がかりを2通り：前回の倍率だけ／前3回の倍率の平均
(1) 基本（見る人60%）で、幅3通り×手がかり2通り、各200通りの乱数で80回くり返し、41〜80回目の倍率の平均・散らばり・空いた枠を数える
(2) 落ち着く先の式：申し込みの見込みが「その倍率から読む見込み」と同じ倍率を生む点（行って帰って同じになる倍率）
(3) 確かめ：見る人の割合（30・60・90%）×幅3通り×手がかり2通り＝18通り（各50通りの乱数）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1175
SRC = "架空の料理講座の抽選（作成者が置いた申し込みの決まりからの乱数、seed 1175）"
SEATS = 100
POOL = 2000
P_NOWATCH = 0.10
WIDTHS = {"広い": (0.0, 0.5), "中": (0.1, 0.3), "狭い": (0.18, 0.22)}
CUES = {"前回": 1, "前3回の平均": 3}
ROUNDS, KEEP_FROM = 80, 40
START_RATIO = 2.0
R_BASE, R_GRID = 200, 50
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def make_thresholds(rng, n_watch, lo, hi):
    return np.sort(rng.uniform(lo, hi, n_watch))


def expected_n(ratio, n_watch, n_no, lo, hi):
    q = min(1.0, 1.0 / ratio) if ratio > 0 else 1.0
    f = 1.0 if hi == lo else np.clip((q - lo) / (hi - lo), 0, 1)
    return n_no * P_NOWATCH + n_watch * f


def fixed_ratio(n_watch, n_no, lo, hi):
    """倍率 x から読んだ見込みで申し込む人の見込み÷枠 が x と同じになる点（二分法）"""
    g = lambda x: expected_n(x, n_watch, n_no, lo, hi) / SEATS - x
    a, b = 1e-6, POOL / SEATS + 1
    for _ in range(200):
        m = (a + b) / 2
        if g(m) > 0:
            a = m
        else:
            b = m
    return (a + b) / 2


def simulate(rng, watch_share, width, cue, runs):
    n_watch = int(round(POOL * watch_share))
    n_no = POOL - n_watch
    lo, hi = WIDTHS[width]
    k = CUES[cue]
    out = np.zeros((runs, ROUNDS))
    for j in range(runs):
        th = make_thresholds(rng, n_watch, lo, hi)
        hist = [START_RATIO]
        for t in range(ROUNDS):
            seen = np.mean(hist[-k:])
            q = min(1.0, 1.0 / seen)
            n = int(np.searchsorted(th, q, side="right")) + int(rng.binomial(n_no, P_NOWATCH))
            ratio = n / SEATS
            out[j, t] = ratio
            hist.append(ratio)
    fx = fixed_ratio(n_watch, n_no, lo, hi)
    e = 1e-4
    slope = (expected_n(fx + e, n_watch, n_no, lo, hi) - expected_n(fx - e, n_watch, n_no, lo, hi)) / SEATS / (2 * e)
    return out, (fx, slope)


def summarize(ratios, fs):
    fx, slope = fs
    tail = ratios[:, KEEP_FROM:]
    win = np.minimum(1, 1 / np.maximum(tail, 1e-9))
    return {"fixed_ratio": r(fx, 3), "slope_at_fixed": r(slope, 3), "mean_ratio": r(tail.mean(), 3),
            "median_ratio": r(np.median(tail), 3),
            "sd_ratio": r(tail.std(axis=1).mean(), 3),
            "mean_abs_change": r(np.abs(np.diff(tail, axis=1)).mean(), 3),
            "ratio_p10": r(np.percentile(tail, 10), 3), "ratio_p90": r(np.percentile(tail, 90), 3),
            "under1_pct": r((tail < 1).mean() * 100, 2),
            "empty_seats_mean": r(np.maximum(0, SEATS - tail * SEATS).mean(), 2),
            "applicants_win_pct": r((SEATS * np.minimum(1, tail)).sum() / (tail * SEATS).sum() * 100, 2),
            "win_pct_fixed": r(min(1, 1 / fx) * 100, 2),
            "seats_used_pct": r(np.minimum(1, tail).mean() * 100, 2)}


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"seats": SEATS, "pool": POOL, "watch_share": 0.6, "no_watch_apply": P_NOWATCH,
                       "widths": {k: list(v) for k, v in WIDTHS.items()}, "rounds": ROUNDS, "kept_rounds": f"{KEEP_FROM + 1}-{ROUNDS}",
                       "start_ratio": START_RATIO, "runs": R_BASE}}
    base_rows, series = [], {}
    for cue in CUES:
        for w in WIDTHS:
            rat, fx = simulate(rng, 0.6, w, cue, R_BASE)
            series[(cue, w)] = rat[0]
            base_rows.append({"cue": cue, "width": w, **summarize(rat, fx)})
        print("base", cue, round(time.time() - T0, 1), flush=True)
    base = pd.DataFrame(base_rows)
    base.to_csv(RES / "base.csv", index=False)
    out["base"] = base_rows
    pd.DataFrame({"round": np.arange(1, ROUNDS + 1),
                  **{f"ratio_{c}_{w}": series[(c, w)] for c in CUES for w in WIDTHS}}).to_csv(
        DATA / "ratio_series_example.csv", index=False)

    def pick(c, w):
        return base[(base.cue == c) & (base.width == w)].iloc[0]
    out["headline"] = {f"{c}_{w}": {k: pick(c, w)[k] for k in ["fixed_ratio", "mean_ratio", "sd_ratio", "ratio_p10", "ratio_p90", "under1_pct", "empty_seats_mean"]}
                       for c in CUES for w in WIDTHS}
    out["headline"]["all_watchers_apply_ratio"] = r((POOL * 0.4 * P_NOWATCH + POOL * 0.6) / SEATS, 3)
    out["headline"]["no_watchers_apply_ratio"] = r(POOL * 0.4 * P_NOWATCH / SEATS, 3)

    # (3) 18通り
    grows = []
    for h in [0.3, 0.6, 0.9]:
        for w in WIDTHS:
            for cue in CUES:
                rat, fx = simulate(rng, h, w, cue, R_GRID)
                grows.append({"watch_share": h, "width": w, "cue": cue, **summarize(rat, fx)})
        print("grid", h, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    g1 = grid[grid.cue == "前回"]
    g3 = grid[grid.cue == "前3回の平均"]
    out["grid"] = {"settings": len(grid),
                   "mean_minus_fixed_min": r((grid.mean_ratio - grid.fixed_ratio).min(), 3),
                   "mean_minus_fixed_max": r((grid.mean_ratio - grid.fixed_ratio).max(), 3),
                   "fixed_ratio_min": r(grid.fixed_ratio.min(), 3), "fixed_ratio_max": r(grid.fixed_ratio.max(), 3),
                   "sd_prev_min": r(g1.sd_ratio.min(), 3), "sd_prev_max": r(g1.sd_ratio.max(), 3),
                   "sd_avg3_min": r(g3.sd_ratio.min(), 3), "sd_avg3_max": r(g3.sd_ratio.max(), 3),
                   "swing_settings_prev": int((g1.sd_ratio >= 0.5).sum()),
                   "swing_settings_avg3": int((g3.sd_ratio >= 0.5).sum()),
                   "under1_max_pct": r(grid.under1_pct.max(), 2),
                   "settled_rows": int((grid.sd_ratio < 0.5).sum()),
                   "settled_max_abs_mean_minus_fixed": r((grid[grid.sd_ratio < 0.5].mean_ratio - grid[grid.sd_ratio < 0.5].fixed_ratio).abs().max(), 3),
                   "prev_settled_slope_abs_max": r(g1[g1.sd_ratio < 0.5].slope_at_fixed.abs().max(), 3),
                   "prev_swing_slope_abs_min": r(g1[g1.sd_ratio >= 0.5].slope_at_fixed.abs().min(), 3)}

    # 図1：80回の倍率（1通りの乱数、見る人60%）
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4), sharey=True)
    cols = {"広い": GRAY, "中": BLUE}
    rr = np.arange(1, ROUNDS + 1)
    for ax, cue in zip(axes, CUES):
        for w in ["広い", "中"]:
            ax.plot(rr, series[(cue, w)], color=cols[w], lw=1.2,
                    label=f"下限の幅：{w}（{int(WIDTHS[w][0]*100)}〜{int(WIDTHS[w][1]*100)}%）、式の落ち着く先{pick(cue, w).fixed_ratio:g}倍")
        ax.axhline(1, color=INK, lw=0.8, ls=":")
        ax.set_ylim(0, 15)
        ax.set_xlabel("回")
        ax.set_title(f"{cue}の倍率を見る", fontsize=11)
        ax.legend(frameon=False, fontsize=8, loc="upper right")
    axes[0].set_ylabel("倍率（申し込み÷枠）")
    fig.suptitle("下限の幅が中のとき、前回だけを見ると倍率は落ち着かず、上下に行き来した", y=1.02, fontsize=12)
    save(fig, "a1175_series.png", SRC)

    # 図2：前回の倍率と今回の倍率（中の幅）
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    xs = np.linspace(0.5, 14, 400)
    lo, hi = WIDTHS["中"]
    ys = [expected_n(x, 1200, 800, lo, hi) / SEATS for x in xs]
    ax.plot(xs, ys, color=BLUE, lw=1.6, label="前回の倍率から見込まれる今回の倍率（中の幅）")
    ax.plot([0, 14], [0, 14], color=GRAY, lw=1, ls="--", label="前回＝今回")
    s = series[("前回", "中")]
    ax.scatter(s[:-1][KEEP_FROM:], s[1:][KEEP_FROM:], color=ORANGE, s=14, zorder=3, label="1通りの乱数の41〜80回目（前回→今回）")
    fx = pick("前回", "中").fixed_ratio
    ax.scatter([fx], [fx], color=INK, s=30, zorder=4, label=f"式の落ち着く先 {fx:g}倍")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 14)
    ax.set_xlabel("前回の倍率")
    ax.set_ylabel("今回の倍率")
    ax.set_title("落ち着く先の近くで、今回は前回と逆向きに大きく動く", fontsize=12)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    save(fig, "a1175_map.png", SRC)

    # 図3：18通りの散らばり
    fig, ax = plt.subplots(figsize=(10, 4.6))
    labels, x = [], np.arange(9)
    v1, v3 = [], []
    for h in [0.3, 0.6, 0.9]:
        for w in WIDTHS:
            labels.append(f"{int(h*100)}%\n{w}")
            v1.append(grid[(grid.watch_share == h) & (grid.width == w) & (grid.cue == "前回")].sd_ratio.iloc[0])
            v3.append(grid[(grid.watch_share == h) & (grid.width == w) & (grid.cue == "前3回の平均")].sd_ratio.iloc[0])
    ax.bar(x - 0.2, v1, width=0.4, color=BLUE, label="前回の倍率を見る")
    ax.bar(x + 0.2, v3, width=0.4, color=GREEN, label="前3回の倍率の平均を見る")
    for i in range(9):
        ax.text(i - 0.2, v1[i] + 0.05, f"{v1[i]:g}", ha="center", fontsize=7)
        ax.text(i + 0.2, v3[i] + 0.05, f"{v3[i]:g}", ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_xlabel("倍率を見る人の割合／下限の幅")
    ax.set_ylabel("41〜80回目の倍率の散らばり（標準偏差）")
    ax.set_ylim(0, max(v1 + v3) * 1.18)
    ax.set_title("18通り：倍率の振れは、見る人の割合・下限の幅・見る手がかりで変わった", fontsize=12)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1175_grid.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1175_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
