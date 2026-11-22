"""932 2回目の受験の合格率が高いのは、なぜなのか？（架空のデータ）

架空の社内資格試験（100問・1問1点・合格点60点で固定）。1回目に落ちた人の一部が、次の回にもう一度受ける。
受け直すかどうかは1回目の点で決まり（合格点に近いほど受け直しやすい）、受け直す人は実力が少し伸びると置く。
2回目の人の合格率が1回目の人より高く見えるのは、(1) 受け直す人の選ばれ方、(2) 1回目の点がたまたま低く出た分が戻ること、
(3) 実力の伸び、のどれによるかを、同じ人で置き方だけを変えて分ける。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 932
SRC = "架空の社内資格試験（作成者が乱数で作成、seed 932）"
ITEMS, CUT, MEAN, DAY = 100, 60, 55.0, 3.0
BASE = {"sd": 13.0, "b": 0.25, "gain": 5.0}
R59 = 0.70           # 59点で落ちた人が受け直す確率
GAIN_SD = 2.0        # 伸びの人ごとの散らばり（点）
N_BASE = 2_000_000
N_GRID = 400_000


def ab(mean, sd):
    k = mean * (1 - mean) / sd ** 2 - 1
    return mean * k, (1 - mean) * k


def sit(rng, p):
    q = np.clip(p + rng.normal(0, DAY / 100, p.shape), 0, 1)
    return rng.binomial(ITEMS, q)


def retake_prob(x, b):
    """1回目の点 x で落ちた人が受け直す確率。59点で R59、1点下がるごとにロジットで b ずつ下がる"""
    a = np.log(R59 / (1 - R59))
    return 1 / (1 + np.exp(-(a + b * (x - (CUT - 1)))))


def run(seed, n, sd, b, gain, everyone=False, detail=False):
    """同じ seed なら、1回目・受け直しの乱数・2回目の乱数は置き方によらず同じものを使う"""
    r1, r2, r3 = (np.random.default_rng([seed, k]) for k in (1, 2, 3))
    a_, b_ = ab(MEAN / 100, sd / 100)
    p = r1.beta(a_, b_, n)
    x1 = sit(r1, p)
    fail = x1 < CUT
    u = r2.random(n)
    retake = fail & ((u < retake_prob(x1, b)) if not everyone else True)
    g = np.clip(gain + r3.normal(0, GAIN_SD, n), 0, None) if gain > 0 else np.zeros(n)
    p2 = np.clip(p + g / 100, 0, 1)
    x2 = sit(r3, p2)
    o = {"sd": sd, "b": b, "gain": gain, "everyone_retakes": everyone,
         "first_pass_rate": float((~fail).mean()), "retake_share_of_failers": float(retake.sum() / fail.sum()),
         "second_pass_rate": float((x2[retake] >= CUT).mean()),
         "retaker_first_score_mean": float(x1[retake].mean()), "retaker_true_mean": float(p[retake].mean() * 100),
         "retaker_true_ge_cut": float((p[retake] * 100 >= CUT).mean()),
         "retaker_true_minus_first_score": float(p[retake].mean() * 100 - x1[retake].mean()),
         "failer_true_mean": float(p[fail].mean() * 100), "nonretaker_true_mean": float(p[fail & ~retake].mean() * 100)}
    o["diff_second_minus_first_pt"] = (o["second_pass_rate"] - o["first_pass_rate"]) * 100
    if detail:
        return o, p, x1, retake, x2
    return o


def main():
    t0 = time.time()
    # 1) 基本の置き方と、同じ人で置き方だけを変えた4通り
    base, p, x1, retake, x2 = run(SEED, N_BASE, **BASE, detail=True)
    steps = [
        ("落ちた人全員が受け直す・伸びなし", run(SEED, N_BASE, BASE["sd"], BASE["b"], 0.0, everyone=True)),
        ("合格点に近い人ほど受け直す・伸びなし", run(SEED, N_BASE, BASE["sd"], BASE["b"], 0.0)),
        (f"落ちた人全員が受け直す・伸び{BASE['gain']:.0f}点", run(SEED, N_BASE, BASE["sd"], BASE["b"], BASE["gain"], everyone=True)),
        (f"合格点に近い人ほど受け直す・伸び{BASE['gain']:.0f}点（基本）", base),
    ]
    dec = pd.DataFrame([{"case": c, **o} for c, o in steps]).round(4)
    dec.to_csv(RES / "decomposition.csv", index=False)
    first = base["first_pass_rate"]
    s_all0, s_sel0, s_all2, s_sel2 = [o["second_pass_rate"] for _, o in steps]

    # 2) 1回目の点ごとの、受け直す割合と2回目の合格率（基本）
    rows = []
    for lo, hi in [(0, 39), (40, 44), (45, 49), (50, 54), (55, 57), (58, 59)]:
        m = (x1 >= lo) & (x1 <= hi)
        mr = m & retake
        rows.append({"first_score": f"{lo}-{hi}", "n": int(m.sum()), "retake_share": mr.sum() / m.sum(),
                     "true_mean": p[m].mean() * 100, "second_pass_rate_retakers": (x2[mr] >= CUT).mean()})
    by_band = pd.DataFrame(rows).round(4)
    by_band.to_csv(RES / "by_first_score.csv", index=False)

    # 3) 確かめ：受け直しの選ばれ方 b × 伸び × 人どうしの実力の差（45通り、各40万人）
    grid = []
    for i, sd in enumerate([8.0, 13.0, 18.0]):
        for j, b in enumerate([0.0, 0.06, 0.12, 0.25, 0.5]):
            for k, gain in enumerate([0.0, 2.0, 5.0]):
                grid.append(run(SEED * 100 + i * 15 + j * 3 + k, N_GRID, sd, b, gain))
    grid = pd.DataFrame(grid).round(4)
    grid.to_csv(RES / "robustness.csv", index=False)

    # data：最初の5,000人
    pd.DataFrame({"person": np.arange(1, 5001), "true_pts": np.round(p[:5000] * 100, 2), "first_score": x1[:5000],
                  "retake": retake[:5000].astype(int),
                  "second_score": np.where(retake[:5000], x2[:5000], -1)}).to_csv(DATA / "exam_sample_5000.csv", index=False)

    rnd = lambda d: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}
    g0 = grid[grid.gain == 0]
    out = {"settings": {"items": ITEMS, "cut": CUT, "mean_pts": MEAN, "day_pts": DAY, **BASE, "retake_prob_at_59": R59,
                        "gain_sd": GAIN_SD, "n_people": N_BASE, "n_grid": N_GRID, "seed": SEED,
                        "retake_prob_at": {str(s): round(float(retake_prob(np.array(s), BASE["b"])), 4) for s in [59, 55, 50, 45, 40, 30]}},
           "base": rnd(base),
           "decomposition": {"first_pass_rate": round(first, 4), "all_retake_no_gain": round(s_all0, 4),
                             "selected_no_gain": round(s_sel0, 4), "all_retake_gain": round(s_all2, 4),
                             "selected_gain_base": round(s_sel2, 4),
                             "selection_effect_pt": round((s_sel0 - s_all0) * 100, 2),
                             "gain_effect_pt_given_selection": round((s_sel2 - s_sel0) * 100, 2),
                             "base_minus_all0_pt": round((s_sel2 - s_all0) * 100, 2),
                             "first_timers_true_mean": round(float(p.mean() * 100), 4),
                             "gain_share_of_base_minus_all0": round((s_sel2 - s_sel0) / (s_sel2 - s_all0), 4)},
           "grid45_ranges": {"diff_second_minus_first_pt": [float(grid.diff_second_minus_first_pt.min()),
                                                             float(grid.diff_second_minus_first_pt.max())],
                             "diff_when_gain0": [float(g0.diff_second_minus_first_pt.min()), float(g0.diff_second_minus_first_pt.max())],
                             "n_higher_when_gain0": int((g0.diff_second_minus_first_pt > 0).sum()), "n_gain0": int(len(g0)),
                             "n_higher_all": int((grid.diff_second_minus_first_pt > 0).sum()),
                             "n_higher_by_gain": {str(gn): int((grid[grid.gain == gn].diff_second_minus_first_pt > 0).sum())
                                                  for gn in [0.0, 2.0, 5.0]},
                             "higher_when_gain0_cases": g0[g0.diff_second_minus_first_pt > 0][["sd", "b", "diff_second_minus_first_pt"]].to_dict("records"),
                             "lower_when_gain5_cases": grid[(grid.gain == 5) & (grid.diff_second_minus_first_pt < 0)][["sd", "b", "diff_second_minus_first_pt"]].to_dict("records"),
                             "retaker_true_minus_first_score": [float(grid.retaker_true_minus_first_score.min()), float(grid.retaker_true_minus_first_score.max())],
                             "b0_abs_retaker_minus_nonretaker_true_max": float(
                                 (grid[grid.b == 0].retaker_true_mean - grid[grid.b == 0].nonretaker_true_mean).abs().max()),
                             "retaker_true_ge_cut": [float(grid.retaker_true_ge_cut.min()), float(grid.retaker_true_ge_cut.max())]}}
    json.dump(out, open(RES / "a932_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

    # 図1：分けて見る
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    labels = ["1回目の\n全員", "落ちた人全員が\n受け直す\n伸びなし", "合格点に近い人\nほど受け直す\n伸びなし",
              f"合格点に近い人\nほど受け直す\n伸び{BASE['gain']:.0f}点（基本）"]
    vals = np.array([first, s_all0, s_sel0, s_sel2]) * 100
    ax.bar(range(4), vals, color=[GRAY, LIGHT, BLUE, ORANGE], width=.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.8, f"{v:.1f}%", ha="center", fontsize=10)
    ax.axhline(first * 100, color=GRAY, lw=.8, ls=":")
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("合格率（%）"); ax.set_ylim(0, max(vals) + 8)
    ax.set_title("2回目の合格率を、選ばれ方と伸びに分ける（同じ200万人）", fontsize=11.5)
    save(fig, "a932_decomposition.png", SRC)

    # 図2：1回目の点ごと
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 3.8))
    xs = range(len(by_band))
    axs[0].bar(xs, by_band.retake_share * 100, color=BLUE, width=.6)
    axs[0].set_ylabel("受け直した割合（%）"); axs[0].set_ylim(0, 100)
    axs[0].set_title("合格点に近い人ほど受け直す（置いた決まり）", fontsize=10.5)
    axs[1].bar(xs, by_band.second_pass_rate_retakers * 100, color=ORANGE, width=.6)
    axs[1].axhline(first * 100, color=GRAY, lw=.8, ls=":")
    axs[1].text(-0.4, first * 100 + 1.5, f"1回目の全員 {first*100:.1f}%", ha="left", fontsize=8.5, color=GRAY)
    axs[1].set_ylabel("受け直した人の2回目の合格率（%）"); axs[1].set_ylim(0, 100)
    axs[1].set_title("合格点に近かった人ほど2回目に受かる", fontsize=10.5)
    for ax in axs:
        ax.set_xticks(list(xs)); ax.set_xticklabels([s.replace("-", "〜") for s in by_band.first_score], fontsize=8.5)
        ax.set_xlabel("1回目の点")
    fig.tight_layout()
    save(fig, "a932_by_first_score.png", SRC)

    # 図3：確かめ（選ばれ方の強さ × 伸び）
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.8), sharey=True)
    for ax, sd in zip(axs, [8.0, 13.0, 18.0]):
        for gain, col in [(0.0, BLUE), (2.0, ORANGE), (5.0, GREEN)]:
            s = grid[(grid.sd == sd) & (grid.gain == gain)].sort_values("b")
            ax.plot(s.b, s.diff_second_minus_first_pt, "o-", color=col, label=f"伸び {gain:.0f}点")
        ax.axhline(0, color=GRAY, lw=.8)
        ax.set_title(f"実力の標準偏差 {sd:.0f}点", fontsize=10.5)
        ax.set_xlabel("受け直しの選ばれ方の強さ b"); ax.set_xticks([0, 0.12, 0.25, 0.5])
    axs[0].set_ylabel("2回目の合格率 − 1回目の合格率（ポイント）")
    axs[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("b は1回目の点で受け直す人が偏る強さ。b=0 は点によらず7割が受け直す（各40万人）", fontsize=11)
    fig.tight_layout()
    save(fig, "a932_robustness.png", SRC)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
