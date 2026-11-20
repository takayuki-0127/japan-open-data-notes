"""861 「どちらでもない」を入れると、賛成の割合は何ポイント動くのか？（架空のデータ）

架空の会社の社員1,000人に「会議を午前中にまとめる案」への賛否を聞く。
半分（500人）には「賛成・反対」の2択、残り半分（500人）には「賛成・どちらでもない・反対」の3択で聞く。
社員ごとに「本当の気持ち」x（正なら賛成寄り）を置き、答えるときのぶれ e を足した y = x + e で答えが決まる。
  2択：y + a > 0 なら賛成（a は、2択で迷った人が賛成に寄るくせ。基本は 0）
  3択：|y| < t なら「どちらでもない」、y >= t なら賛成、y <= -t なら反対（t は迷う幅。基本は 0.5）
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 861
SRC = "架空の社員アンケート（作成者が乱数で作成、seed 861）"
N = 1000          # 1回の調査の人数（2択500人・3択500人）
REPS = 2000       # 調査を作り直す回数
MU, SD, NOISE, T, A = 0.2, 1.0, 0.5, 0.5, 0.0


def survey(rng, reps, n=N, mu=MU, t=T, a=A):
    """reps 回分の調査。前半 n/2 人が2択、後半 n/2 人が3択"""
    x = rng.normal(mu, SD, (reps, n))
    y = x + rng.normal(0, NOISE, (reps, n))
    h = n // 2
    y2, y3 = y[:, :h], y[:, h:]
    yes2 = (y2 + a > 0).mean(1)
    yes3 = (y3 >= t).sum(1); no3 = (y3 <= -t).sum(1); mid3 = h - yes3 - no3
    return {"true_yes": (x > 0).mean(1), "yes2": yes2, "yes3": yes3 / h, "mid3": mid3 / h, "no3": no3 / h,
            "yes3_excl": yes3 / np.maximum(yes3 + no3, 1)}


def q(v):
    return {"mean": round(float(np.mean(v)), 4), "p10": round(float(np.quantile(v, .1)), 4),
            "p90": round(float(np.quantile(v, .9)), 4)}


def main():
    rng = np.random.default_rng(SEED)

    # 1回分の調査（data）
    x = rng.normal(MU, SD, N); y = x + rng.normal(0, NOISE, N)
    form = np.where(np.arange(N) < N // 2, "2択", "3択")
    ans = np.where(form == "2択", np.where(y + A > 0, "賛成", "反対"),
                   np.where(y >= T, "賛成", np.where(y <= -T, "反対", "どちらでもない")))
    one = pd.DataFrame({"id": np.arange(1, N + 1), "form": form, "true_lean": x.round(4), "answer": ans})
    one.to_csv(DATA / "respondents.csv", index=False)
    o2, o3 = one[one.form == "2択"], one[one.form == "3択"]
    one_res = {"true_yes": round(float((one.true_lean > 0).mean()), 4),
               "yes2": round(float((o2.answer == "賛成").mean()), 4),
               "yes3": round(float((o3.answer == "賛成").mean()), 4),
               "mid3": round(float((o3.answer == "どちらでもない").mean()), 4),
               "yes3_excl": round(float((o3.answer == "賛成").sum() / (o3.answer != "どちらでもない").sum()), 4)}

    # 2) 2,000回の調査
    s = survey(rng, REPS)
    diff = s["yes2"] - s["yes3"]
    reps = pd.DataFrame({k: np.round(v, 4) for k, v in s.items()})
    reps["diff_points"] = np.round(diff * 100, 2)
    summ = {k: q(v) for k, v in s.items()}
    summ["diff_points"] = q(diff * 100)
    summ["excl_minus_yes2_points"] = q((s["yes3_excl"] - s["yes2"]) * 100)
    summ["share_reps_yes3_below_half"] = round(float((s["yes3"] < .5).mean()), 4)
    summ["share_reps_yes2_above_half"] = round(float((s["yes2"] > .5).mean()), 4)

    # 3) どちらでもないを選んだ人は、本当はどんな人か（3択に答えた20万人をまとめて）
    xb = rng.normal(MU, SD, 200000); yb = xb + rng.normal(0, NOISE, 200000)
    mid = np.abs(yb) < T
    who = {"mid_share": round(float(mid.mean()), 4),
           "mid_true_lean_mean": round(float(xb[mid].mean()), 4),
           "mid_true_lean_abs_lt_05": round(float((np.abs(xb[mid]) < .5).mean()), 4),
           "mid_true_yes_share": round(float((xb[mid] > 0).mean()), 4),
           "mid_would_yes_in_2choice": round(float((yb[mid] + A > 0).mean()), 4),
           "nonmid_abs_lt_05": round(float((np.abs(xb[~mid]) < .5).mean()), 4)}
    who["decomp_points"] = round(who["mid_share"] * who["mid_would_yes_in_2choice"] * 100, 2)

    # 4) 確かめ：迷う幅 t・会社全体の傾き mu・2択で賛成に寄るくせ a を変える（各500回）
    rows = []
    for a in [0.0, 0.2]:
        for mu in [-0.2, 0.0, 0.2, 0.5]:
            for t in [0.25, 0.5, 0.75, 1.0]:
                r = survey(np.random.default_rng(SEED * 100 + int(t * 100) + int((mu + 1) * 1000) + int(a * 10000)),
                           500, mu=mu, t=t, a=a)
                rows.append({"a": a, "mu": mu, "t": t, "true_yes": round(float(r["true_yes"].mean()), 4),
                             "yes2": round(float(r["yes2"].mean()), 4), "yes3": round(float(r["yes3"].mean()), 4),
                             "mid3": round(float(r["mid3"].mean()), 4),
                             "yes3_excl": round(float(r["yes3_excl"].mean()), 4),
                             "diff_points": round(float((r["yes2"] - r["yes3"]).mean() * 100), 2),
                             "excl_minus_yes2_points": round(float((r["yes3_excl"] - r["yes2"]).mean() * 100), 2)})
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness.csv", index=False)
    a0 = rob[rob.a == 0]
    robs = {"diff_points_min": float(rob.diff_points.min()), "diff_points_max": float(rob.diff_points.max()),
            "mid3_min": float(rob.mid3.min()), "mid3_max": float(rob.mid3.max()),
            "a0_diff_min": float(a0.diff_points.min()), "a0_diff_max": float(a0.diff_points.max()),
            "a0_mu02_diff_by_t": a0[a0.mu == 0.2].set_index("t").diff_points.to_dict(),
            "a0_mu02_mid_by_t": a0[a0.mu == 0.2].set_index("t").mid3.to_dict(),
            "a0_t05_diff_by_mu": a0[a0.t == 0.5].set_index("mu").diff_points.to_dict(),
            "a0_t05_excl_minus_yes2_by_mu": a0[a0.t == 0.5].set_index("mu").excl_minus_yes2_points.to_dict(),
            "a02_mu02_t05": rob[(rob.a == 0.2) & (rob.mu == 0.2) & (rob.t == 0.5)].iloc[0].to_dict(),
            "excl_sign_same_as_majority": bool((np.sign(a0.excl_minus_yes2_points[a0.mu != 0]) ==
                                                np.sign(a0.mu[a0.mu != 0])).all()),
            "a0_mu0_excl_abs_max": float(a0[a0.mu == 0].excl_minus_yes2_points.abs().max())}

    out = {"setting": {"N": N, "per_form": N // 2, "reps": REPS, "mu": MU, "sd": SD, "noise": NOISE, "t": T, "a": A},
           "one_survey": one_res, "reps_summary": summ, "who_picks_middle": who, "robustness": robs}
    json.dump(out, open(RES / "a861_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    reps.describe().round(4).to_csv(RES / "reps_describe.csv")

    # 図1：4つの数え方
    lab = ["本当に賛成寄りの人\n（作成者が置いた正解）", "2択の「賛成」", "3択の「賛成」\n（3択の全員が分母）",
           "3択の「賛成」\n（どちらでもないを除く）"]
    keys = ["true_yes", "yes2", "yes3", "yes3_excl"]
    m = [summ[k]["mean"] * 100 for k in keys]
    lo = [m[i] - summ[k]["p10"] * 100 for i, k in enumerate(keys)]
    hi = [summ[k]["p90"] * 100 - m[i] for i, k in enumerate(keys)]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    yy = np.arange(4)[::-1]
    ax.barh(yy, m, color=[GRAY, BLUE, ORANGE, LIGHT], xerr=[lo, hi], error_kw={"ecolor": INK, "lw": 1, "capsize": 3})
    for i, v, h_ in zip(yy, m, hi):
        ax.text(v + h_ + 1.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(lab, fontsize=9); ax.set_xlim(0, 100)
    ax.axvline(50, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("賛成の割合（%、2,000回の平均。線は10〜90%の範囲）")
    ax.set_title(f"「どちらでもない」を入れると、賛成は{summ['diff_points']['mean']:.1f}ポイント下がった")
    save(fig, "a861_four_counts.png", SRC)

    # 図2：本当の気持ちと3択の答え
    bins = np.linspace(-3.2, 3.6, 69)
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.hist([xb[yb >= T], xb[mid], xb[yb <= -T]], bins=bins, stacked=True, color=[BLUE, GRAY, ORANGE],
            label=["賛成と答えた", "どちらでもないと答えた", "反対と答えた"])
    ax.axvline(0, color=INK, lw=.8)
    ax.set_xlabel("本当の気持ち（作成者が置いた値。0より左が反対寄り、右が賛成寄り）"); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title(f"「どちらでもない」は0の近くの人。その{who['mid_true_yes_share']*100:.0f}%は本当は賛成寄りだった")
    save(fig, "a861_who_middle.png", SRC)

    # 図3：確かめ（どちらでもないの割合と、下がったポイント）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cols = {-0.2: ORANGE, 0.0: GRAY, 0.2: BLUE, 0.5: GREEN}
    for mu, g in rob.groupby("mu"):
        for a, mk in [(0.0, "o"), (0.2, "^")]:
            gg = g[g.a == a]
            ax.scatter(gg.mid3 * 100, gg.diff_points, color=cols[mu], marker=mk, s=34,
                       label=f"全体の傾き{mu:+.1f}" + ("" if a == 0 else "・2択で賛成に寄るくせあり"))
    ax.set_xlabel("3択で「どちらでもない」を選んだ割合（%）"); ax.set_ylabel("2択の賛成 − 3択の賛成（ポイント）")
    h, l = ax.get_legend_handles_labels()
    ax.legend(h, l, frameon=False, fontsize=7.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    ax.set_title("下がる幅は、「どちらでもない」の多さと、2択で賛成に寄るくせで決まる（32通り）", fontsize=11.5)
    save(fig, "a861_robustness.png", SRC, y=-0.25)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
