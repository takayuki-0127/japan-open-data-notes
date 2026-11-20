"""849 作業ごとの見積もりを足すと、全体の見積もりは何%足りなくなるのか？（架空のデータ）

架空のプロジェクト（作業10個を順に行う）。作業ごとに「半々で終わる日数」（中央値）を見積もりとして置き、
実際の日数は右に長い対数正規分布（中央値＝見積もり、ばらつき sigma）から引く。
見積もりは作業ごとには正しい（どの作業も見積もり以内に終わる確率は50%）。それを足した合計が、全体ではどれだけ足りないかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 849
SRC = "架空のプロジェクトの作業日数（作成者が乱数で作成、seed 849）"
rng = np.random.default_rng(SEED)
N_RUN = 200_000
SIGMA = 0.5
MED40 = rng.integers(2, 11, 40).astype(float)  # 40個の作業の見積もり（日）。先頭10個が基本のプロジェクト


def draw_lognormal(rng, med, sigma, n_run, rho=0.0):
    """中央値 med・ばらつき sigma の対数正規。rho は作業どうしの共通の振れ（全部が一緒に延びる度合い）"""
    k = len(med)
    z_common = rng.standard_normal((n_run, 1))
    z_own = rng.standard_normal((n_run, k))
    z = np.sqrt(rho) * z_common + np.sqrt(1 - rho) * z_own
    return med[None, :] * np.exp(sigma * z)


def draw_gamma(rng, med, sigma, n_run):
    """ガンマ分布。ばらつきの大きさ（変動係数）を対数正規（sigma）と同じにし、中央値を見積もりに合わせる"""
    cv = np.sqrt(np.exp(sigma ** 2) - 1)
    shape = 1 / cv ** 2
    base_med = np.median(np.random.default_rng(SEED + 1).gamma(shape, 1.0, 2_000_000))
    return rng.gamma(shape, 1.0, (n_run, len(med))) / base_med * med[None, :]


def summarize(x, est):
    tot = x.sum(1)
    s = est.sum()
    return {"sum_est": round(float(s), 2),
            "p_total_within_sum": round(float((tot <= s).mean()), 4),
            "mean_overrun_pct": round(float((tot.mean() / s - 1) * 100), 2),
            "median_overrun_pct": round(float((np.median(tot) / s - 1) * 100), 2),
            "p80_overrun_pct": round(float((np.quantile(tot, .8) / s - 1) * 100), 2),
            "p90_overrun_pct": round(float((np.quantile(tot, .9) / s - 1) * 100), 2)}


def main():
    t0 = time.time()
    est = MED40[:10]
    x = draw_lognormal(rng, est, SIGMA, N_RUN)
    tot = x.sum(1)
    base = summarize(x, est)
    base["per_task_p_within_est"] = [round(float(v), 4) for v in (x <= est[None, :]).mean(0)]
    base["p_all_tasks_within"] = round(float((x <= est[None, :]).all(1).mean()), 5)
    base["mean_tasks_over"] = round(float((x > est[None, :]).sum(1).mean()), 3)
    base["total_mean"] = round(float(tot.mean()), 2)
    base["total_median"] = round(float(np.median(tot)), 2)
    base["total_p80"] = round(float(np.quantile(tot, .8)), 2)
    base["total_p90"] = round(float(np.quantile(tot, .9)), 2)
    base["theory_mean_overrun_pct"] = round(float((np.exp(SIGMA ** 2 / 2) - 1) * 100), 2)
    # 遅れの合計と早まりの合計（日）
    d = x - est[None, :]
    base["mean_late_days_sum"] = round(float(np.clip(d, 0, None).sum(1).mean()), 2)
    base["mean_early_days_sum"] = round(float(np.clip(-d, 0, None).sum(1).mean()), 2)

    pd.DataFrame({"task_id": np.arange(1, 11), "estimate_days": est.astype(int), "sigma": SIGMA}).to_csv(
        DATA / "tasks.csv", index=False)
    runs = pd.DataFrame(np.round(x[:1000], 2), columns=[f"t{i}" for i in range(1, 11)])
    runs.insert(0, "run", np.arange(1, 1001))
    runs["total"] = runs[[f"t{i}" for i in range(1, 11)]].sum(1).round(2)
    runs.to_csv(DATA / "runs.csv", index=False)

    # 作業の数 × ばらつき
    rows = []
    for sg in [0.3, 0.5, 0.8]:
        for n in [1, 2, 3, 5, 10, 20, 40]:
            e = MED40[:n]
            xx = draw_lognormal(np.random.default_rng(SEED * 100 + n + int(sg * 10)), e, sg, N_RUN)
            r = summarize(xx, e)
            rows.append({"sigma": sg, "n_tasks": n, **r})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "by_n_sigma.csv", index=False)

    # 確かめ：置き方を変える（作業10個）
    rob = []
    for rho in [0.0, 0.2, 0.5, 0.8, 1.0]:
        xx = draw_lognormal(np.random.default_rng(SEED * 10 + int(rho * 10)), est, SIGMA, N_RUN, rho)
        rob.append({"case": f"共通の振れ rho={rho}", "kind": "rho", "value": rho, **summarize(xx, est)})
    for sg in [0.3, 0.8]:
        xx = draw_lognormal(np.random.default_rng(SEED * 20 + int(sg * 10)), est, sg, N_RUN)
        rob.append({"case": f"ばらつき sigma={sg}", "kind": "sigma", "value": sg, **summarize(xx, est)})
    xx = draw_gamma(np.random.default_rng(SEED * 30), est, SIGMA, N_RUN)
    rob.append({"case": "分布をガンマに（ばらつきは同じ）", "kind": "shape", "value": 0, **summarize(xx, est)})
    xx = draw_lognormal(np.random.default_rng(SEED * 40), np.full(10, est.mean()), SIGMA, N_RUN)
    rob.append({"case": "作業の大きさをそろえる（各6.1日前後）", "kind": "equal", "value": 0,
                **summarize(xx, np.full(10, est.mean()))})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"base_10tasks_sigma0_5": base, "by_n_sigma": grid.to_dict("records"),
           "robustness": rob.to_dict("records"),
           "range_p_within_sum_robustness": [round(float(rob.p_total_within_sum.min()), 4),
                                              round(float(rob.p_total_within_sum.max()), 4)],
           "range_mean_overrun_robustness": [round(float(rob.mean_overrun_pct.min()), 2),
                                             round(float(rob.mean_overrun_pct.max()), 2)]}
    json.dump(out, open(RES / "a849_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：合計日数の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.hist(tot, bins=np.linspace(30, 130, 101), color=LIGHT, density=True)
    s = est.sum()
    for v, lab, c in [(s, f"見積もりの合計 {s:.0f}日", ORANGE), (np.median(tot), f"半々で終わる日 {np.median(tot):.1f}日", BLUE),
                      (np.quantile(tot, .8), f"8割で終わる日 {np.quantile(tot, .8):.1f}日", INK)]:
        ax.axvline(v, color=c, lw=1.4, ls="--")
    ax.text(s - 1, ax.get_ylim()[1] * .92, f"見積もりの合計\n{s:.0f}日", color=ORANGE, ha="right", fontsize=9, bbox=dict(fc="white", ec="none", pad=1))
    ax.text(np.median(tot) + 1, ax.get_ylim()[1] * .80, f"半々で終わる日\n{np.median(tot):.1f}日", color=BLUE, fontsize=9, bbox=dict(fc="white", ec="none", pad=1))
    ax.text(np.quantile(tot, .8) + 1, ax.get_ylim()[1] * .62, f"8割で終わる日\n{np.quantile(tot, .8):.1f}日", color=INK, fontsize=9, bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xlabel("10個の作業を終えるまでの合計日数"); ax.set_yticks([])
    ax.set_title(f"見積もりの合計以内に終わる確率は{base['p_total_within_sum']*100:.0f}%（各作業は50%で見積もり以内）")
    save(fig, "a849_total_hist.png", SRC)

    # 図2：作業の数と、合計以内に終わる確率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for sg, c in [(0.3, LIGHT), (0.5, BLUE), (0.8, ORANGE)]:
        g = grid[grid.sigma == sg]
        ax.plot(g.n_tasks, g.p_total_within_sum * 100, "o-", color=c, label=f"ばらつき sigma={sg}")
    ax.axhline(50, color=GRAY, lw=1, ls=":"); ax.text(41, 51, "50%", color=GRAY, fontsize=9, ha="right")
    ax.set_xscale("log"); ax.set_xticks([1, 2, 3, 5, 10, 20, 40]); ax.set_xticklabels(["1", "2", "3", "5", "10", "20", "40"])
    ax.set_xlabel("作業の数（対数の目盛り）"); ax.set_ylabel("見積もりの合計以内に終わる確率（%）"); ax.set_ylim(0, 60)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("作業が増えるほど、見積もりの合計では間に合わなくなる")
    save(fig, "a849_by_n.png", SRC)

    # 図3：共通の振れ
    rr = rob[rob.kind == "rho"]
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.6))
    lab = [f"{v:.1f}" for v in rr.value]
    axs[0].bar(lab, rr.p_total_within_sum * 100, color=BLUE)
    for i, v in enumerate(rr.p_total_within_sum * 100):
        axs[0].text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
    axs[0].set_ylim(0, 60); axs[0].set_xlabel("共通の振れ rho"); axs[0].set_title("合計以内に終わる確率", fontsize=11)
    axs[1].bar(lab, rr.mean_overrun_pct, color=GRAY, label="平均")
    axs[1].plot(lab, rr.p90_overrun_pct, "o-", color=ORANGE, label="1割の確率でこれ以上")
    for i, v in enumerate(rr.p90_overrun_pct):
        axs[1].text(i, v + 5, f"+{v:.0f}%", ha="center", fontsize=9, color=ORANGE)
    for i, v in enumerate(rr.mean_overrun_pct):
        axs[1].text(i, v / 2, f"+{v:.0f}%", ha="center", va="center", fontsize=8, color="white")
    axs[1].set_ylim(0, 110); axs[1].set_xlabel("共通の振れ rho"); axs[1].set_title("見積もりの合計からの超過（%）", fontsize=11)
    axs[1].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("全部の作業が一緒に延びやすいと、平均の超過は同じでも大きく外れる回が増える", fontsize=12)
    fig.tight_layout()
    save(fig, "a849_corr.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
