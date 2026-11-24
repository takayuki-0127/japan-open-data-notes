"""1201 長く開いていない人に送るのをやめて開封率が上がったのは、メールが良くなったからなのか？（架空のデータ）

架空の店の会員2万人に、週1通のお知らせのメールを送る。会員は「読んでいる人」（1通を開く確率は人ごとに違う）と
「読んでいない人」の2つの状態を行き来する。一部の人は、開いても開封が記録されない（クリックしたときだけ記録される）。
52週目の終わりに「最後に開封が記録されてから N 日たった人」に送るのをやめ、その後の12週の数字を、送り続けた場合と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1201
SRC = "架空の店の会員向けメール（作成者が乱数で作成、seed 1201）"
N = 20000
W_BEFORE, W_AFTER = 52, 12
A_BETA, B_BETA = 1.2, 2.8       # 読んでいる人の1通を開く確率の分布（平均0.3）
P_DORM_OPEN = 0.01              # 読んでいない人が1通を開く確率
DORM0 = 0.4                     # はじめに読んでいない人の割合
TO_DORM = 0.005                 # 読んでいる人が1週で読まなくなる確率
CLICK = 0.12                    # 開いた人がクリックする確率
HOLD = 0.1                      # 止める人のうち、送り続けて様子を見る人の割合（確かめ用）
BASE = dict(q=0.15, back=0.005, mult=1.0, cut_weeks=26)


def run(seed, q, back, mult, cut_weeks, n=N, keep_detail=False):
    rng = np.random.default_rng(seed)
    r = rng.beta(A_BETA, B_BETA, n)
    dorm = rng.random(n) < DORM0
    silent = rng.random(n) < q
    last = np.full(n, -10 ** 6)                     # 最後に開封が記録された週
    rec_hist = np.zeros((W_BEFORE + W_AFTER, n), dtype=bool)
    true_hist = np.zeros_like(rec_hist)
    click_hist = np.zeros_like(rec_hist)
    for t in range(W_BEFORE + W_AFTER):
        if t > 0:
            u = rng.random(n)
            dorm = np.where(dorm, u >= back, u < TO_DORM)
        m = mult if t >= W_BEFORE else 1.0
        p = np.where(dorm, P_DORM_OPEN, np.minimum(r * m, 1.0))
        op = rng.random(n) < p
        ck = op & (rng.random(n) < CLICK)
        rec = op & (~silent | ck)
        true_hist[t], click_hist[t], rec_hist[t] = op, ck, rec
        if t == W_BEFORE - 1:
            weeks_since = (W_BEFORE - 1) - np.where(rec_hist[:W_BEFORE].any(0),
                                                    W_BEFORE - 1 - np.argmax(rec_hist[:W_BEFORE][::-1], 0), -10 ** 6)
            stop = weeks_since >= cut_weeks
            hold = stop & (rng.random(n) < HOLD)
            active_at_cut = ~dorm
    keep = ~stop
    bef = slice(W_BEFORE - 12, W_BEFORE)
    aft = slice(W_BEFORE, W_BEFORE + W_AFTER)
    # 送り続けた場合（全員）
    rate_before = rec_hist[bef].mean()
    rate_after_all = rec_hist[aft].mean()
    rate_after_kept = rec_hist[aft][:, keep].mean()
    # 送り続けて様子を見た人から、全員に送ったときの値を見積もる
    est_all = (rec_hist[aft][:, keep].sum() + rec_hist[aft][:, hold].sum() / HOLD) / (W_AFTER * (keep.sum() + hold.sum() / HOLD))
    out = {
        "stopped_share": stop.mean(),
        "rate_before_all": rate_before,
        "rate_after_kept": rate_after_kept,
        "rate_after_all": rate_after_all,
        "rise_pt": (rate_after_kept - rate_before) * 100,
        "rise_from_denominator_pt": (rate_after_kept - rate_after_all) * 100,
        "rise_from_change_pt": (rate_after_all - rate_before) * 100,
        "kept_before_rate": rec_hist[bef][:, keep].mean(),
        "kept_change_pt": (rate_after_kept - rec_hist[bef][:, keep].mean()) * 100,
        "est_all_from_hold": est_all,
        "est_change_pt": (est_all - rate_before) * 100,
        # 1通あたりの合計（送り続けた場合を1とする）
        "rec_opens_ratio": rec_hist[aft][:, keep].sum() / rec_hist[aft].sum(),
        "true_opens_ratio": true_hist[aft][:, keep].sum() / true_hist[aft].sum(),
        "clicks_ratio": click_hist[aft][:, keep].sum() / click_hist[aft].sum(),
        "sent_ratio": keep.mean(),
        # 止めた人の中身
        "stopped_active_share": active_at_cut[stop].mean() if stop.any() else np.nan,
        "stopped_silent_share": silent[stop].mean() if stop.any() else np.nan,
        "stopped_with_true_open_after": true_hist[aft][:, stop].any(0).mean() if stop.any() else np.nan,
        "stopped_with_click_after": click_hist[aft][:, stop].any(0).mean() if stop.any() else np.nan,
        "silent_share_all": silent.mean(),
    }
    if keep_detail:
        weekly = pd.DataFrame({"week": np.arange(1, W_BEFORE + W_AFTER + 1),
                               "rec_rate_all": rec_hist.mean(1),
                               "rec_rate_kept": rec_hist[:, keep].mean(1),
                               "true_rate_all": true_hist.mean(1),
                               "clicks_all": click_hist.sum(1), "clicks_kept": click_hist[:, keep].sum(1)})
        members = pd.DataFrame({"member_id": np.arange(1, n + 1), "open_prob_when_reading": r.round(4),
                                "reading_at_cut": active_at_cut.astype(int), "open_not_recorded": silent.astype(int),
                                "weeks_since_recorded_open_at_cut": np.minimum(weeks_since, 999),
                                "stopped": stop.astype(int)})
        return out, weekly, members
    return out


def r4(x):
    return round(float(x), 4)


def main():
    t0 = time.time()
    base, weekly, members = run(SEED, keep_detail=True, **BASE)
    weekly.to_csv(RES / "weekly_base.csv", index=False, float_format="%.6f")
    members.to_csv(DATA / "members.csv", index=False)
    base = {k: r4(v) for k, v in base.items()}

    worse = {k: r4(v) for k, v in run(SEED + 1, **{**BASE, "mult": 0.9}).items()}

    # 止める区切り（90・180・365日）
    cuts = []
    for days, wk in [(90, 13), (180, 26), (365, 52)]:
        o = run(SEED, **{**BASE, "cut_weeks": wk})
        cuts.append({"cut_days": days, **{k: r4(v) for k, v in o.items()}})
    cuts = pd.DataFrame(cuts)
    cuts.to_csv(RES / "by_cutoff.csv", index=False)

    # 確かめ：27通り（記録されない人の割合 × 戻ってくる確率 × メールの良さの変化）
    grid = []
    gi = 0
    for q in [0.0, 0.15, 0.3]:
        for back in [0.0, 0.005, 0.02]:
            for mult in [0.9, 1.0, 1.1]:
                o = run(SEED * 10 + gi, q=q, back=back, mult=mult, cut_weeks=26, n=10000)
                gi += 1
                grid.append({"q": q, "back": back, "mult": mult, **{k: r4(v) for k, v in o.items()}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g = {"n": len(grid)}
    for c in ["rise_pt", "rise_from_denominator_pt", "rise_from_change_pt", "clicks_ratio", "true_opens_ratio",
              "stopped_active_share", "stopped_with_click_after", "kept_change_pt", "est_change_pt"]:
        g[c + "_min"] = r4(grid[c].min()); g[c + "_max"] = r4(grid[c].max())
    w = grid[grid.mult == 0.9]
    g["worse_n"] = len(w)
    g["worse_n_rise_positive"] = int((w.rise_pt > 0).sum())
    g["worse_rise_min"] = r4(w.rise_pt.min()); g["worse_rise_max"] = r4(w.rise_pt.max())
    g["n_kept_change_negative_when_same"] = int((grid[grid.mult == 1.0].kept_change_pt < 0).sum())
    same = grid[grid.mult == 1.0]
    g["mult1.0_kept_change_min"] = r4(same.kept_change_pt.min()); g["mult1.0_kept_change_max"] = r4(same.kept_change_pt.max())
    for bk in [0.0, 0.005, 0.02]:
        s2 = grid[grid.back == bk]
        g[f"back{bk}_stopped_active_min"] = r4(s2.stopped_active_share.min())
        g[f"back{bk}_stopped_active_max"] = r4(s2.stopped_active_share.max())
    g["est_minus_true_change_absmax_pt"] = r4((grid.est_change_pt - grid.rise_from_change_pt).abs().max())
    for mm in [0.9, 1.0, 1.1]:
        s = grid[grid.mult == mm]
        g[f"mult{mm}_true_change_min"] = r4(s.rise_from_change_pt.min())
        g[f"mult{mm}_true_change_max"] = r4(s.rise_from_change_pt.max())
        g[f"mult{mm}_est_change_min"] = r4(s.est_change_pt.min())
        g[f"mult{mm}_est_change_max"] = r4(s.est_change_pt.max())

    out = {"setting": {"members": N, "weeks_before": W_BEFORE, "weeks_after": W_AFTER, "open_prob_mean_reading": 0.3,
                       "open_prob_dormant": P_DORM_OPEN, "dormant_at_start": DORM0, "to_dormant_per_week": TO_DORM,
                       "click_given_open": CLICK, "hold_share": HOLD, **BASE},
           "base_180days": base, "worse_mail_0_9": worse, "grid27": g}
    json.dump(out, open(RES / "a1201_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：週ごとの記録された開封率
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    wk = weekly.week
    ax.plot(wk, weekly.rec_rate_all * 100, color=GRAY, lw=1.6, label="全員に送り続けた場合（同じ乱数）")
    ax.plot(wk[wk > W_BEFORE], weekly.rec_rate_kept[wk > W_BEFORE] * 100, color=BLUE, lw=2,
            label="180日開封の記録がない人に送るのをやめた場合")
    ax.plot(wk[wk <= W_BEFORE], weekly.rec_rate_all[wk <= W_BEFORE] * 100, color=INK, lw=1.6)
    ax.axvline(W_BEFORE + 0.5, color=ORANGE, ls="--", lw=1)
    ax.text(W_BEFORE + 0.8, 3, "送る相手を\n絞った週", color=ORANGE, fontsize=8.5)
    ax.set_ylim(0, None); ax.set_xlabel("週"); ax.set_ylabel("記録された開封率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("メールの良さは変えていないのに、開封率は相手を絞った週から上がった")
    save(fig, "a1201_weekly.png", SRC)

    # 図2：区切りごとの 開封率の上がり と 1通あたりのクリックの合計
    fig, ax = plt.subplots(1, 2, figsize=(8.2, 3.8))
    x = np.arange(len(cuts)); lab = [f"{d}日" for d in cuts.cut_days]
    ax[0].bar(x, cuts.rise_pt, color=BLUE, width=.55)
    for i, v in enumerate(cuts.rise_pt):
        ax[0].text(i, v + 0.3, f"+{v:.2f}", ha="center", fontsize=9)
    ax[0].set_xticks(x, lab); ax[0].set_ylim(0, max(cuts.rise_pt) * 1.25)
    ax[0].set_ylabel("開封率の上がり（ポイント）"); ax[0].set_title("記録された開封率", fontsize=11)
    ax[1].bar(x, cuts.clicks_ratio * 100, color=ORANGE, width=.55)
    for i, v in enumerate(cuts.clicks_ratio * 100):
        ax[1].text(i, v + 1.5, f"{v:.2f}%", ha="center", fontsize=9)
    ax[1].set_xticks(x, lab); ax[1].set_ylim(0, 110)
    ax[1].set_ylabel("送り続けた場合を100%とした合計"); ax[1].set_title("クリックの合計", fontsize=11)
    fig.supxlabel("送るのをやめる区切り（最後の開封の記録からの日数）", fontsize=10)
    fig.suptitle("区切りを短くするほど開封率は上がり、クリックの合計は減った", fontsize=13)
    fig.tight_layout()
    save(fig, "a1201_cutoff.png", SRC)

    # 図3：27通りの、見かけの上がりと本当の変化
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    col = {0.9: ORANGE, 1.0: GRAY, 1.1: GREEN}
    lbl = {0.9: "開く確率を0.9倍（悪くなった）", 1.0: "変えない", 1.1: "1.1倍（良くなった）"}
    for mm in [0.9, 1.0, 1.1]:
        s = grid[grid.mult == mm]
        ax.scatter(s.rise_from_change_pt, s.rise_pt, color=col[mm], s=30, label=lbl[mm])
    lo = min(grid.rise_from_change_pt.min(), 0) - 1; hi = grid.rise_pt.max() + 1
    ax.plot([lo, hi], [lo, hi], color=INK, lw=0.8, ls=":")
    ax.text(hi - 0.3, hi - 5.5, "2つが同じなら\n点はこの線に乗る", ha="right", fontsize=8, color=INK)
    ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
    ax.set_xlabel("全員に送り続けた場合の、開封率の変化（ポイント）")
    ax.set_ylabel("絞った後 − 前の開封率（ポイント）")
    ax.legend(frameon=False, fontsize=8.5, loc="center right")
    ax.set_title("27通りのすべてで、相手を絞った後の開封率は上がって見えた")
    save(fig, "a1201_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(cuts.T)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
